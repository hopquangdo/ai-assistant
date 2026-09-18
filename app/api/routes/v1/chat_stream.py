"""HTTP/SSE bindings for active chat streams."""

import uuid

from fastapi import APIRouter, Depends, HTTPException

from dqh.svc_core.transports.sse import SSEResponse

from app.api.dependencies import validate_model
from src.security.auth import Principal, get_current_principal
from src.schemas.chat import ChatRequest, ChatStreamResponse
from src.services import chat_stream_service

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/stream", response_model=ChatStreamResponse)
async def create_chat_stream(
    request: ChatRequest, principal: Principal = Depends(get_current_principal)
) -> ChatStreamResponse:
    """Create an agent stream and return its ID for the SSE GET request."""
    model = validate_model(request.model)
    session_id = request.session_id or str(uuid.uuid4())
    stream_id = await chat_stream_service.create_chat_stream(
        session_id, request.message, model, principal.user_id
    )
    return ChatStreamResponse(stream_id=stream_id, session_id=session_id)


@router.get("/stream/{stream_id}")
async def get_chat_stream(
    stream_id: str, principal: Principal = Depends(get_current_principal)
) -> SSEResponse:
    """Subscribe to an active stream and yield its SSE frames."""
    queue = await chat_stream_service.subscribe_chat_stream(stream_id, principal.user_id)
    if queue is None:
        raise HTTPException(status_code=404, detail="Stream không tồn tại hoặc đã được tiêu thụ.")

    async def event_generator():
        while (frame := await queue.get()) is not None:
            yield frame

    return SSEResponse(event_generator())
