"""Chay graph va dich LangGraph events thanh event cho HTTP/SSE."""

from dataclasses import dataclass
import logging
import time
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage

from dqh.ai_core import DoneEvent, ErrorEvent, MessageEvent, TokenEvent, ToolEndEvent, ToolStartEvent, Usage, UsageTracker

from app.agents.graph import get_orchestrator_graph
from app.core.config import get_settings
from app.core.constants import RECURSION_LIMIT_FALLBACK_TEXT
from app.llm.client import get_chat_model
from app.schemas.stream import StreamEvent, StreamEventName
from app.utils.time_context import current_date_system_message

logger = logging.getLogger("chatbot.agent")


@dataclass(frozen=True)
class UsageEvent:
    usage: dict


@dataclass(frozen=True)
class ChartEvent:
    payload: dict


@dataclass(frozen=True)
class ChartPendingEvent:
    pass


@dataclass(frozen=True)
class SuggestionsEvent:
    suggestions: list[str]


async def warmup_agent() -> None:
    t0 = time.perf_counter()
    try:
        get_orchestrator_graph()
        await get_chat_model().ainvoke([current_date_system_message()])
        logger.info("agent warmup done in %.0fms", (time.perf_counter() - t0) * 1000)
    except Exception:
        logger.warning("agent warmup failed; request will retry", exc_info=True)


def _content_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(block.get("text", "") if isinstance(block, dict) else str(block) for block in content)
    return str(content or "")


def _model_of(config: dict) -> str | None:
    return (config.get("configurable") or {}).get("model")


def _build_input_messages(messages: list) -> list:
    return [current_date_system_message(), *messages]


async def run_agent_stream(messages: list, model: str | None = None):
    """Stream tool status, response tokens, final reply, chart and usage."""
    graph = get_orchestrator_graph()
    usage = Usage(model=model or get_settings().llm_model_name)
    tracker = UsageTracker(usage)
    input_messages = _build_input_messages(messages)
    config = {
        "configurable": {"model": model} if model else {},
        "callbacks": [tracker],
    }
    new_messages: list[BaseMessage] = []
    charts: list[dict] = []
    reply_text = ""
    recursion_hit = False
    done_emitted = False
    chart_pending_emitted = False
    seen_ids: set[int] = set()

    try:
        async for event in graph.astream_events({"messages": input_messages}, version="v2", config=config):
            kind = event.get("event")
            data = event.get("data") or {}
            metadata = event.get("metadata") or {}
            node = metadata.get("langgraph_node")

            if kind == "on_tool_start":
                yield ToolStartEvent(
                    name=event.get("name") or "tool",
                    args=data.get("input"),
                    run_id=str(event.get("run_id") or ""),
                )
            elif kind == "on_tool_end":
                yield ToolEndEvent(
                    name=event.get("name") or "tool",
                    output=data.get("output"),
                    run_id=str(event.get("run_id") or ""),
                )
            elif kind == "on_custom_event":
                stream_event = StreamEvent(
                    name=str(event.get("name") or ""),
                    payload=data if isinstance(data, dict) else {},
                )
                if stream_event.name == StreamEventName.RESPONSE_START:
                    yield StreamEvent(name=StreamEventName.RESPONSE_START, payload={})
                elif stream_event.name == StreamEventName.RESPONSE_DELTA:
                    piece = _content_text(stream_event.payload.get("content"))
                    if piece:
                        reply_text += piece
                        yield TokenEvent(text=piece)
                elif stream_event.name == StreamEventName.RESPONSE_COMPLETED:
                    reply_text = _content_text(stream_event.payload.get("answer"))
                    yield DoneEvent(messages=list(new_messages), text=reply_text)
                    done_emitted = True
                    if stream_event.payload.get("should_generate_chart") and not chart_pending_emitted:
                        yield ChartPendingEvent()
                        chart_pending_emitted = True
            elif kind == "on_chain_start" and node == "genchart":
                if not chart_pending_emitted:
                    yield ChartPendingEvent()
                    chart_pending_emitted = True
            elif kind == "on_chain_end" and (
                node in {"react", "agent", "tools", "response"}
                or isinstance(data.get("output"), dict)
                and "should_generate_chart" in data["output"]
            ):
                output = data.get("output")
                if not isinstance(output, dict):
                    continue
                recursion_hit = recursion_hit or bool(output.get("recursion_hit"))
                for message in output.get("messages") or []:
                    if id(message) not in seen_ids:
                        seen_ids.add(id(message))
                        new_messages.append(message)
                        yield MessageEvent(message=message)
                if "should_generate_chart" in output and output.get("messages"):
                    response_text = _content_text(getattr(output["messages"][-1], "content", ""))
                    if response_text:
                        reply_text = response_text
                if node == "response" and not done_emitted:
                    if not reply_text and new_messages:
                        reply_text = _content_text(getattr(new_messages[-1], "content", ""))
                        if reply_text:
                            yield TokenEvent(text=reply_text)
                    yield DoneEvent(messages=list(new_messages), text=reply_text)
                    done_emitted = True
            elif kind == "on_chain_end" and node == "genchart":
                output = data.get("output")
                if isinstance(output, dict):
                    charts = output.get("charts") or []
            elif kind == "on_chain_end" and node == "suggestion":
                output = data.get("output")
                if isinstance(output, dict):
                    yield SuggestionsEvent(suggestions=output.get("suggestions") or [])
    except Exception:
        logger.exception("agent graph failed")
        tracker.log_summary(error="agent graph failed")
        yield ErrorEvent(message="Đã có lỗi xảy ra, vui lòng thử lại.", recoverable=False)
        return

    if not reply_text and new_messages:
        reply_text = _content_text(getattr(new_messages[-1], "content", ""))
    if recursion_hit and not reply_text:
        reply_text = RECURSION_LIMIT_FALLBACK_TEXT
        new_messages.append(AIMessage(content=reply_text))
    if not done_emitted:
        yield DoneEvent(messages=new_messages, text=reply_text)
    for chart in charts:
        yield ChartEvent(payload=chart)
    tracker.log_summary()
    yield UsageEvent(usage=usage.to_dict())


async def run_agent(messages: list, model: str | None = None) -> tuple[list, list[dict], list[str], dict]:
    new_messages: list = []
    charts: list[dict] = []
    suggestions: list[str] = []
    usage: dict = {}
    async for event in run_agent_stream(messages, model):
        if isinstance(event, ErrorEvent) and not event.recoverable:
            raise RuntimeError(event.message)
        if isinstance(event, DoneEvent):
            new_messages = event.messages
        elif isinstance(event, ChartEvent):
            charts.append(event.payload)
        elif isinstance(event, SuggestionsEvent):
            suggestions = event.suggestions
        elif isinstance(event, UsageEvent):
            usage = event.usage
    return new_messages, charts, suggestions, usage
