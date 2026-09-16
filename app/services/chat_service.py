"""Business logic tầng service cho luồng chat — build lịch sử hội thoại, lưu memory, gợi ý
followup. Tách khỏi app/api/routes/chat.py để route chỉ còn lo HTTP/SSE, không biết chi tiết
memory/agent."""

import asyncio
from typing import ClassVar

from dqh.ai_core import DoneEvent, ErrorEvent, MessageEvent, TokenEvent, ToolEndEvent, ToolStartEvent
from dqh.svc_core.transports.sse import sse as _sse

from app.agents.orchestrator import (
    ChartEvent,
    ChartPendingEvent,
    SuggestionsEvent,
    UsageEvent,
    run_agent_stream,
)
from app.api.dependencies import tool_preview
from app.core.logging import get_logger
from app.memory.service import memory_manager, sanitize_tool_call_history
from app.schemas.stream import StreamEvent, StreamEventName

__all__ = ["ChatService", "chat_service", "build_messages", "consume_stream", "create_stream", "persist_turn", "produce_chat_stream"]

logger = get_logger("services.chat")


class ChatService:
    _stream_queues: ClassVar[dict[str, asyncio.Queue[str | None]]] = {}

    def build_messages(self, session_id: str, user_message: str) -> list:
        """Ghép lịch sử đã lưu (đã dọn AIMessage(tool_calls) hỏng) với tin nhắn mới của user."""
        session_memory = memory_manager.get(session_id)
        history = sanitize_tool_call_history(session_memory.get("messages", []))
        return history + [{"role": "user", "content": user_message}]

    def persist_turn(self, session_id: str, messages: list, new_messages: list, charts: list[dict] | None = None) -> None:
        """Lưu toàn bộ trace (tool call/tool result/câu trả lời) của 1 lượt vào memory phiên, để lượt
        sau còn số liệu gốc làm căn cứ."""
        if new_messages:
            memory_manager.update(
                session_id,
                {"messages": messages + new_messages, "charts": charts or []},
            )

    def create_stream(self, stream_id: str) -> None:
        self._stream_queues[stream_id] = asyncio.Queue()

    def consume_stream(self, stream_id: str) -> asyncio.Queue[str | None] | None:
        return self._stream_queues.pop(stream_id, None)

    async def produce_chat_stream(
        self,
        stream_id: str,
        session_id: str,
        messages: list,
        model: str | None,
    ) -> None:
        """Chạy agent nền, chuyển event thành SSE frame và lưu kết quả lượt chat."""
        queue = self._stream_queues[stream_id]

        async def publish(event: StreamEvent) -> None:
            await queue.put(_sse(event.name, event.payload))

        try:
            await self._run_chat_stream(publish, session_id, messages, model)
        except Exception:
            logger.exception("chat stream failed", extra={"stream_id": stream_id, "session_id": session_id})
            await publish(StreamEvent(name="error", payload={"message": "Đã có lỗi xảy ra, vui lòng thử lại."}))
        finally:
            await queue.put(None)

    async def _run_chat_stream(self, publish, session_id: str, messages: list, model: str | None) -> None:
        logger.info("chat stream request", extra={"session_id": session_id, "user_message": messages[-1]})

        new_messages: list = []
        final_content = ""
        usage: dict = {}
        charts: list[dict] = []

        async for event in run_agent_stream(messages, model):
            match event:
                case ToolStartEvent(name=name, args=args):
                    await publish(StreamEvent(name="status", payload={
                        "node": name, "type": "SEARCHING", "module": name,
                        "args": tool_preview(args, 1000),
                    }))
                case ToolEndEvent(name=name, output=output):
                    preview = tool_preview(output)
                    logger.info("tool result", extra={"session_id": session_id, "tool": name, "result": preview})
                    await publish(StreamEvent(name="tool_result", payload={"tool": name, "output": preview}))
                case TokenEvent(text=text):
                    await publish(StreamEvent(name="token", payload={"content": text}))
                case StreamEvent(name=event_name) if event_name == StreamEventName.RESPONSE_START:
                    await publish(StreamEvent(
                        name="status",
                        payload={"node": "response", "type": "ANALYZING_DATA", "module": "response", "args": ""},
                    ))
                case MessageEvent(message=message):
                    new_messages.append(message)
                case ErrorEvent(message=message, recoverable=recoverable):
                    logger.warning("agent stream error: %s (recoverable=%s)", message, recoverable)
                    if not recoverable:
                        await publish(StreamEvent(name="error", payload={"message": message}))
                        return
                case DoneEvent(messages=stream_messages, text=text):
                    new_messages = stream_messages or new_messages
                    final_content = text
                case UsageEvent(usage=usage_payload):
                    usage = usage_payload
                case ChartEvent(payload=payload):
                    charts.append(payload)
                case ChartPendingEvent():
                    await publish(StreamEvent(name="chart_pending", payload={"pending": True}))
                case SuggestionsEvent(suggestions=items):
                    if items:
                        await publish(StreamEvent(name="suggestions", payload={"suggestions": items}))

        final_content = final_content or "Xin lỗi, tôi chưa có câu trả lời."
        self.persist_turn(session_id, messages, new_messages, charts)

        logger.info("chat stream response", extra={"session_id": session_id, "reply": final_content})
        await publish(StreamEvent(name="done", payload={"reply": final_content, "session_id": session_id}))
        await publish(StreamEvent(name="usage", payload=usage))
        for chart in charts:
            await publish(StreamEvent(name="chart", payload=chart))


chat_service = ChatService()

build_messages = chat_service.build_messages
persist_turn = chat_service.persist_turn
create_stream = chat_service.create_stream
consume_stream = chat_service.consume_stream
produce_chat_stream = chat_service.produce_chat_stream

