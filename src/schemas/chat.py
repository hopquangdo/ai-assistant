"""Định nghĩa schema request/response cho API chatbot."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from src.schemas.common import PageResponse


class ChatMessageItem(BaseModel):
    """Tin nhắn chuẩn hóa để trả về client."""

    role: str
    content: str


class ChatRequest(BaseModel):
    """Schema cho payload chat từ client."""

    message: str
    session_id: Optional[str] = None
    model: Optional[str] = None


class ChatResponse(BaseModel):
    """Schema cho phản hồi chat trả về client."""

    reply: str
    session_id: Optional[str] = None
    suggestions: list[str] = Field(default_factory=list)
    charts: list[dict] = Field(default_factory=list)
    usage: dict = Field(default_factory=dict)


class ConversationResponse(BaseModel):
    """DTO trả về conversation kèm lịch sử và chart."""

    session_id: str
    messages: list[ChatMessageItem] = Field(default_factory=list)
    charts: list[dict] = Field(default_factory=list)
    updated_at: Optional[datetime] = None


class MessagePageResponse(PageResponse[ChatMessageItem]):
    """DTO trả về tin nhắn theo trang."""

    session_id: str


class ChatStreamResponse(BaseModel):
    """Thông tin dùng để kết nối tới luồng SSE đã khởi tạo."""

    stream_id: str
    session_id: str
