"""HTTP/SSE bindings for the chatbot.

Chỉ lo HTTP/SSE binding — logic nghiệp vụ nằm ở app/agents/orchestrator.py (agent) và
app/services/chat_service.py (memory/followups)."""

import asyncio
import uuid

from fastapi import APIRouter, HTTPException

from dqh.svc_core.transports.sse import SSEResponse

from app.api.dependencies import validate_model
from app.core.logging import get_logger
from app.schemas.chat import ChatRequest, ChatStreamResponse
from app.services import chat_service

router = APIRouter(prefix="/chat", tags=["chat"])
logger = get_logger("api.routes")


@router.post("/stream", response_model=ChatStreamResponse)
async def create_chat_stream(request: ChatRequest) -> ChatStreamResponse:
    """Khởi tạo agent stream và trả về ID để client kết nối SSE bằng GET."""
    model = validate_model(request.model)
    session_id = request.session_id or str(uuid.uuid4())
    messages = chat_service.build_messages(session_id, request.message)
    stream_id = str(uuid.uuid4())
    chat_service.create_stream(stream_id)

    logger.info("chat stream created", extra={"stream_id": stream_id, "session_id": session_id})
    asyncio.create_task(
        chat_service.produce_chat_stream(stream_id, session_id, messages, model),
        name=f"chat-stream-{stream_id}",
    )
    return ChatStreamResponse(stream_id=stream_id, session_id=session_id)


@router.get("/stream/{stream_id}")
async def get_chat_stream(stream_id: str) -> SSEResponse:
    """Kết nối tới stream đã tạo và phát các SSE frame theo thứ tự."""
    queue = chat_service.consume_stream(stream_id)
    if queue is None:
        raise HTTPException(status_code=404, detail="Stream không tồn tại hoặc đã được tiêu thụ.")

    async def event_generator():
        while (frame := await queue.get()) is not None:
            yield frame

    return SSEResponse(event_generator())
