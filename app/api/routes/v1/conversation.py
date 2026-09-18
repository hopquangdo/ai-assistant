"""HTTP bindings for conversation history."""

from fastapi import APIRouter, Depends, Query

from src.security.auth import Principal, get_current_principal
from src.schemas.chat import (
    ConversationCreateResponse,
    ConversationPageResponse,
    ConversationResponse,
    MessagePageResponse,
)
from src.services import conversation_service

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/conversations", response_model=ConversationCreateResponse)
async def create_conversation(
    principal: Principal = Depends(get_current_principal),
) -> ConversationCreateResponse:
    """Tạo một conversation mới và trả về session_id, dùng để FE điều hướng sang
    /chat/{session_id} trước khi gửi tin nhắn đầu tiên qua POST /chat/stream."""
    return ConversationCreateResponse(**await conversation_service.create_new_conversation(principal.user_id))


@router.get("/conversations", response_model=ConversationPageResponse)
async def list_conversations(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    principal: Principal = Depends(get_current_principal),
) -> ConversationPageResponse:
    """List các conversation của người dùng hiện tại theo trang, mới nhất trước."""
    return ConversationPageResponse(
        **await conversation_service.list_conversations(principal.user_id, page=page, limit=limit)
    )


@router.get("/conversation/{session_id}", response_model=ConversationResponse)
async def get_conversation(
    session_id: str, principal: Principal = Depends(get_current_principal)
) -> ConversationResponse:
    """Get the conversation stored for a session (chỉ nếu thuộc về người dùng hiện tại)."""
    return ConversationResponse(**await conversation_service.get_conversation(session_id, principal.user_id))


@router.get("/messages/{session_id}", response_model=MessagePageResponse)
async def get_messages(
    session_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    order: str = Query("asc", pattern="^(asc|desc)$"),
    principal: Principal = Depends(get_current_principal),
) -> MessagePageResponse:
    """Get a paginated message list for a session.

    order=desc: page 1 la batch tin nhan MOI NHAT -- dung cho UI chat load lich su
    theo kieu "cuon len tai them", tranh phai tai toan bo hoi thoai dai.
    """
    payload = await conversation_service.get_message_page(
        session_id, principal.user_id, page=page, limit=limit, order=order
    )
    return MessagePageResponse(**payload)
