"""Quan ly 1 luot chat dang chay + stream event:

User message -> ChatStreamService -> Orchestrator/LangGraph -> RedisStreamQueue -> SSE

Queue dua tren Redis (khong con la dict asyncio.Queue trong tien trinh) de producer
(POST /chat/stream) va consumer (GET /chat/stream/{id}) co the o 2 process/worker khac nhau.

ChatStreamService khong biet gi ve cach conversation duoc luu -- doc lich su/ghi trace deu
uy quyen cho ConversationService."""

import asyncio
import uuid

from dqh.ai_core import DoneEvent, ErrorEvent, MessageEvent, TokenEvent, ToolEndEvent, ToolStartEvent
from dqh.svc_core.transports.sse import sse as _sse

from app.api.dependencies import tool_preview
from src.agents.orchestrator import (
    ChartEvent,
    ChartPendingEvent,
    SuggestionsEvent,
    UsageEvent,
    run_agent_stream,
)
from src.core.logging import get_logger
from src.infrastructure.message_queue.client import redis_client_factory
from src.infrastructure.message_queue.queue import RedisStreamQueue
from src.schemas.stream import StreamEvent, StreamEventName
from src.services.conversation_service import conversation_service

logger = get_logger("services.chat_stream")


class ChatStreamService:
    """StreamManager cho 1 luot chat: tao hang doi SSE tren Redis, chay agent nen, dich event."""

    async def create_chat_stream(
        self, session_id: str, user_message: str, model: str | None, user_id: str
    ) -> str:
        """Luu tin nhan user xuong DB roi tao stream_id va chay agent nen. Route chi can goi
        method nay roi tra ve stream_id -- khong biet gi ve task ben trong.

        Tin nhan user duoc luu (persist_turn kieu cu da bo) NGAY tai day, truoc khi agent
        chay -- GET conversation/messages sau do thay ngay tin nhan nay du bot chua tra loi
        xong hay client da ngat ket noi SSE.

        Chi gui CAU HOI MOI cho graph (khong tu ghep lai full history nua) -- lich su hoi
        thoai do checkpointer Postgres (thread_id=session_id) tu nho, tranh tinh trang 2 noi
        cung luu history roi cong don vao nhau lam messages phinh to moi luot.

        claim_session tu choi neu session_id da thuoc ve user khac (khong cho doat quyen
        hoi thoai bang cach doan/truyen session_id cua nguoi khac)."""
        await conversation_service.claim_session(session_id, user_id)
        run_id = str(uuid.uuid4())
        await conversation_service.save_user_message(session_id, run_id, user_message)

        stream_id = str(uuid.uuid4())
        queue = RedisStreamQueue(redis_client_factory.get(), stream_id)
        await queue.open()
        await queue.set_owner(user_id)
        logger.info("chat stream created", extra={"stream_id": stream_id, "session_id": session_id})
        asyncio.create_task(
            self._produce(queue, stream_id, session_id, run_id, user_message, model),
            name=f"chat-stream-{stream_id}",
        )
        return stream_id

    async def subscribe_chat_stream(self, stream_id: str, user_id: str) -> RedisStreamQueue | None:
        """Tra None (-> 404 o route) neu stream khong ton tai HOAC thuoc ve user khac --
        khong phan biet 2 truong hop nay de tranh lo stream co ton tai hay khong."""
        queue = RedisStreamQueue(redis_client_factory.get(), stream_id)
        if not await queue.exists():
            return None
        owner = await queue.owner()
        if owner is not None and owner != user_id:
            logger.warning(
                "chat stream ownership denied", extra={"stream_id": stream_id, "user_id": user_id}
            )
            return None
        return queue

    async def _produce(
        self,
        queue: RedisStreamQueue,
        stream_id: str,
        session_id: str,
        run_id: str,
        user_message: str,
        model: str | None,
    ) -> None:
        """Chay agent nen, chuyen event thanh SSE frame va luu ket qua luot chat."""

        async def publish(event: StreamEvent) -> None:
            await queue.put(_sse(event.name, event.payload))

        try:
            await self._run(publish, session_id, run_id, user_message, model)
        except Exception:
            logger.exception("chat stream failed", extra={"stream_id": stream_id, "session_id": session_id})
            await publish(StreamEvent(name="error", payload={"message": "Da co loi xay ra, vui long thu lai."}))
        finally:
            await queue.close()

    async def _run(self, publish, session_id: str, run_id: str, user_message: str, model: str | None) -> None:
        logger.info(
            "chat stream request session_id=%s message_preview=%r",
            session_id,
            user_message[:200],
        )

        # Input cho graph chi la cau hoi moi -- checkpointer (thread_id=session_id) chiu trach
        # nhiem nho lai toan bo history truoc do trong state cua graph.
        messages = [{"role": "user", "content": user_message}]
        new_messages: list = []
        final_content = ""
        usage: dict = {}
        charts: list[dict] = []

        async for event in run_agent_stream(messages, model, thread_id=session_id):
            match event:
                case ToolStartEvent():
                    # Bo qua status SEARCHING don le o day: node da tu ban TOOL_START theo
                    # batch (1 hoac nhieu tool chay song song) ngay truoc khi goi tool, ban
                    # them o day se tao buoc trung tren UI.
                    pass
                case ToolEndEvent(name=name, output=output):
                    preview = tool_preview(output)
                    logger.info("tool result", extra={"session_id": session_id, "tool": name, "result": preview})
                    await publish(StreamEvent(name="tool_result", payload={"tool": name, "output": preview}))
                case TokenEvent(text=text):
                    await publish(StreamEvent(name="token", payload={"content": text}))
                case StreamEvent(name=event_name, payload=payload) if event_name == StreamEventName.NODE_START:
                    node_name = payload.get("node", "")
                    await publish(StreamEvent(
                        name="status",
                        payload={"node": node_name, "type": "ANALYZING_DATA", "module": node_name, "args": ""},
                    ))
                case StreamEvent(name=event_name, payload=payload) if event_name == StreamEventName.TOOL_START:
                    node_name = payload.get("node", "")
                    tools = payload.get("tools", [])
                    logger.info(
                        "%s running tools in parallel session_id=%s tools=%s",
                        node_name,
                        session_id,
                        [tool["name"] for tool in tools],
                    )
                    await publish(StreamEvent(
                        name="status",
                        payload={
                            "node": node_name,
                            "type": "PARALLEL_TOOLS",
                            "module": node_name,
                            "tools": [
                                {"name": tool["name"], "args": tool_preview(tool.get("args"), 1000)}
                                for tool in tools
                            ],
                        },
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

        final_content = final_content or "Xin loi, toi chua co cau tra loi."
        await conversation_service.save_assistant_turn(session_id, run_id, final_content, charts)

        logger.info(
            "chat stream response session_id=%s reply_length=%d message_count=%d chart_count=%d",
            session_id,
            len(final_content),
            len(new_messages),
            len(charts),
        )
        await publish(StreamEvent(name="done", payload={"reply": final_content, "session_id": session_id}))
        await publish(StreamEvent(name="usage", payload=usage))
        for chart in charts:
            await publish(StreamEvent(name="chart", payload=chart))


chat_stream_service = ChatStreamService()

__all__ = ["ChatStreamService", "chat_stream_service"]
