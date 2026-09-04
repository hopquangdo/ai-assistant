"""Chuẩn hoá event stream của ``Agent`` — biến ``graph.astream_events`` (LangGraph, nhiều loại
event thô) thành 1 chuỗi event đã gõ kiểu, đã gom message, đã xử lý recursion-limit.

    async for ev in agent.astream("Câu hỏi..."):
        match ev:
            case TokenEvent(text=t):            ...   # token câu trả lời cuối
            case ToolStartEvent(name=n, args=a): ...
            case ToolEndEvent(name=n, output=o): ...
            case DoneEvent(messages=msgs, text=final): ...
            case ErrorEvent(message=m):         ...
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Sequence

from langchain_core.messages import AIMessage, BaseMessage
from langgraph.errors import GraphRecursionError

__all__ = [
    "AgentEvent",
    "TokenEvent",
    "ToolStartEvent",
    "ToolEndEvent",
    "MessageEvent",
    "DoneEvent",
    "ErrorEvent",
    "stream_agent",
]

# Node của create_react_agent sinh message thật: "agent" (AIMessage) / "tools" (ToolMessage).
_CAPTURE_NODES = frozenset({"agent", "tools"})


@dataclass(frozen=True)
class AgentEvent:
    """Lớp cha — dùng để type hint / isinstance."""


@dataclass(frozen=True)
class TokenEvent(AgentEvent):
    text: str


@dataclass(frozen=True)
class ToolStartEvent(AgentEvent):
    name: str
    args: Any
    run_id: str = ""


@dataclass(frozen=True)
class ToolEndEvent(AgentEvent):
    name: str
    output: Any
    run_id: str = ""


@dataclass(frozen=True)
class MessageEvent(AgentEvent):
    """1 message hoàn chỉnh vừa sinh ra (AIMessage tool-call, ToolMessage, hoặc câu trả lời)."""

    message: BaseMessage


@dataclass(frozen=True)
class DoneEvent(AgentEvent):
    """Kết thúc lượt. ``messages`` = toàn bộ message MỚI; ``text`` = nội dung câu trả lời cuối."""

    messages: list[BaseMessage] = field(default_factory=list)
    text: str = ""


@dataclass(frozen=True)
class ErrorEvent(AgentEvent):
    message: str
    recoverable: bool = False


def _content_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "".join(p.get("text", "") if isinstance(p, dict) else str(p) for p in value)
    return str(value or "")


async def stream_agent(
    graph: Any,
    inputs: dict,
    *,
    config: dict | None = None,
    recursion_fallback: str = "",
) -> AsyncIterator[AgentEvent]:
    """Chạy ``graph.astream_events`` và phát ``AgentEvent`` đã chuẩn hoá.

    - ``inputs``: state đầu vào, thường ``{"messages": [...]}``.
    - ``config``: RunnableConfig (đặt ``recursion_limit``, ``callbacks``… ở đây).
    - Chạm ``recursion_limit`` -> ``ErrorEvent(recoverable=True)`` + ``DoneEvent`` với
      ``recursion_fallback`` (nếu có), KHÔNG raise.
    """
    new_messages: list[BaseMessage] = []
    reply_text = ""
    seen_ids: set[int] = set()

    try:
        async for event in graph.astream_events(inputs, version="v2", config=config):
            kind = event.get("event")
            data = event.get("data") or {}
            node = (event.get("metadata") or {}).get("langgraph_node")

            if kind == "on_tool_start":
                yield ToolStartEvent(name=event.get("name") or "tool", args=data.get("input"),
                                     run_id=str(event.get("run_id") or ""))

            elif kind == "on_tool_end":
                yield ToolEndEvent(name=event.get("name") or "tool", output=data.get("output"),
                                   run_id=str(event.get("run_id") or ""))

            elif kind == "on_chat_model_stream" and node == "agent":
                piece = _content_text(getattr(data.get("chunk"), "content", ""))
                if piece:
                    reply_text += piece
                    yield TokenEvent(text=piece)

            elif kind == "on_chain_end" and node in _CAPTURE_NODES:
                out = data.get("output")
                msgs = out.get("messages") if isinstance(out, dict) else None
                for m in msgs or []:
                    if id(m) in seen_ids:
                        continue
                    seen_ids.add(id(m))
                    new_messages.append(m)
                    yield MessageEvent(message=m)

    except GraphRecursionError:
        yield ErrorEvent(message="Đã đạt giới hạn số bước xử lý.", recoverable=True)
        if recursion_fallback:
            fb = AIMessage(content=recursion_fallback)
            new_messages.append(fb)
            yield DoneEvent(messages=new_messages, text=recursion_fallback)
        return

    if not reply_text and new_messages:
        reply_text = _content_text(getattr(new_messages[-1], "content", ""))
    yield DoneEvent(messages=new_messages, text=reply_text)
