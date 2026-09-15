"""Định nghĩa schema request/response cho API chatbot."""

from typing import Optional

from pydantic import BaseModel


class ChatRequest(BaseModel):
    """Schema cho payload chat từ client."""

    message: str
    session_id: Optional[str] = None
    model: Optional[str] = None


class ChatResponse(BaseModel):
    """Schema cho phản hồi chat trả về client."""

    reply: str
    session_id: Optional[str] = None
    suggestions: list[str] = []
