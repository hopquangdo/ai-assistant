"""HTTP bindings for conversation history."""

from fastapi import APIRouter, Query

from src.schemas.chat import ConversationResponse, MessagePageResponse
from src.services import conversation_service

router = APIRouter(prefix="/chat", tags=["chat"])


@router.get("/conversation/{session_id}", response_model=ConversationResponse)
async def get_conversation(session_id: str) -> ConversationResponse:
    """Get the conversation stored for a session."""
    return ConversationResponse(**conversation_service.get_conversation(session_id))


@router.get("/messages/{session_id}", response_model=MessagePageResponse)
async def get_messages(
    session_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
) -> MessagePageResponse:
    """Get a paginated message list for a session."""
    payload = conversation_service.get_message_page(session_id, page=page, limit=limit)
    return MessagePageResponse(**payload)
