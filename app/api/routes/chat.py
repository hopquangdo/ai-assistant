"""Route chat (không streaming + SSE streaming).

Chỉ lo HTTP/SSE binding — logic nghiệp vụ nằm ở app/agents/orchestrator.py (agent) và
app/services/chat_service.py (memory/followups)."""

import asyncio
import uuid

from fastapi import APIRouter, HTTPException

from dqh.ai_core import DoneEvent, ErrorEvent, MessageEvent, TokenEvent, ToolEndEvent, ToolStartEvent
from dqh.svc_core.transports.sse import SSEResponse, sse as _sse

from app.agents.orchestrator import (
    ChartEvent,
    ChartPendingEvent,
    SuggestionsEvent,
    UsageEvent,
    run_agent,
    run_agent_stream,
)
from app.api.dependencies import tool_preview, validate_model
from app.core.logging import get_logger
from app.schemas.chat import ChatRequest, ChatResponse, ChatStreamResponse
from app.schemas.stream import StreamEvent, StreamEventName
from app.services import chat_service

router = APIRouter()
logger = get_logger("api.routes")
_stream_queues: dict[str, asyncio.Queue[str | None]] = {}


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Nhận tin nhắn từ client, giữ memory phiên và trả về câu trả lời."""
    session_id = request.session_id or str(uuid.uuid4())
    messages = chat_service.build_messages(session_id, request.message)

    logger.info("chat request", extra={"session_id": session_id, "user_message": request.message})

    model = validate_model(request.model)
    try:
        new_messages, charts, suggestions, usage = await run_agent(messages, model=model)
    except Exception:
        logger.exception("chat failed", extra={"session_id": session_id})
        raise HTTPException(status_code=500, detail="Đã có lỗi xảy ra, vui lòng thử lại.")

    last_message = new_messages[-1]
    content = last_message.content if hasattr(last_message, "content") else last_message["content"]

    chat_service.persist_turn(session_id, messages, new_messages, charts)
    logger.info("chat response", extra={"session_id": session_id, "reply": content})

    return ChatResponse(
        reply=content,
        session_id=session_id,
        suggestions=suggestions,
        charts=charts,
        usage=usage,
    )


@router.post("/chat/stream", response_model=ChatStreamResponse)
async def create_chat_stream(request: ChatRequest) -> ChatStreamResponse:
    """Khởi tạo agent stream và trả về ID để client kết nối SSE bằng GET."""
    model = validate_model(request.model)
    session_id = request.session_id or str(uuid.uuid4())
    messages = chat_service.build_messages(session_id, request.message)
    stream_id = str(uuid.uuid4())
    _stream_queues[stream_id] = asyncio.Queue()

    logger.info("chat stream created", extra={"stream_id": stream_id, "session_id": session_id})
    asyncio.create_task(
        _produce_chat_stream(stream_id, session_id, messages, model),
        name=f"chat-stream-{stream_id}",
    )
    return ChatStreamResponse(stream_id=stream_id, session_id=session_id)


async def _produce_chat_stream(
    stream_id: str, session_id: str, messages: list, model: str | None,
) -> None:
    """Chạy agent nền và đẩy từng SSE frame vào queue của stream."""
    queue = _stream_queues[stream_id]

    async def publish(event: StreamEvent) -> None:
        await queue.put(_sse(event.name, event.payload))

    try:
        await _run_chat_stream(publish, session_id, messages, model)
    except Exception:
        logger.exception("chat stream failed", extra={"stream_id": stream_id, "session_id": session_id})
        await publish(StreamEvent(name="error", payload={"message": "Đã có lỗi xảy ra, vui lòng thử lại."}))
    finally:
        await queue.put(None)


async def _run_chat_stream(publish, session_id: str, messages: list, model: str | None) -> None:
    """Dịch event từ orchestrator thành SSE frame và lưu kết quả của lượt chat."""
    logger.info("chat stream request", extra={"session_id": session_id, "user_message": messages[-1]})

    new_messages: list = []
    final_content = ""
    usage: dict = {}
    charts: list[dict] = []
    suggestions: list[str] = []

    async for ev in run_agent_stream(messages, model):
        match ev:
            # Mỗi tool -> 1 bước riêng để người dùng thấy đang tra cứu cái gì.
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
            case ErrorEvent(message=msg, recoverable=recoverable):
                logger.warning("agent stream error: %s (recoverable=%s)", msg, recoverable)
                if not recoverable:
                    await publish(StreamEvent(name="error", payload={"message": msg}))
                    return
            case DoneEvent(messages=msgs, text=text):
                new_messages = msgs or new_messages
                final_content = text
            case UsageEvent(usage=usage_payload):
                usage = usage_payload
            case ChartEvent(payload=payload):
                charts.append(payload)
            case ChartPendingEvent():
                await publish(StreamEvent(name="chart_pending", payload={"pending": True}))
            case SuggestionsEvent(suggestions=items):
                suggestions = items
                if items:
                    await publish(StreamEvent(name="suggestions", payload={"suggestions": items}))

    final_content = final_content or "Xin lỗi, tôi chưa có câu trả lời."
    chat_service.persist_turn(session_id, messages, new_messages, charts)

    logger.info("chat stream response", extra={"session_id": session_id, "reply": final_content})
    await publish(StreamEvent(name="done", payload={"reply": final_content, "session_id": session_id}))
    await publish(StreamEvent(name="usage", payload=usage))
    for chart in charts:
        await publish(StreamEvent(name="chart", payload=chart))



@router.get("/chat/stream/{stream_id}")
async def get_chat_stream(stream_id: str) -> SSEResponse:
    """Kết nối tới stream đã tạo và phát các SSE frame theo thứ tự."""
    queue = _stream_queues.pop(stream_id, None)
    if queue is None:
        raise HTTPException(status_code=404, detail="Stream không tồn tại hoặc đã được tiêu thụ.")

    async def event_generator():
        while (frame := await queue.get()) is not None:
            yield frame

    return SSEResponse(event_generator())
