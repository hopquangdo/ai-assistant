"""Định nghĩa schema request/response cho API chatbot."""

from typing import Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Schema cho payload chat từ Backend."""

    message: str
    session_id: Optional[str] = None
    model: Optional[str] = None


class ChatResponse(BaseModel):
    """Schema cho phản hồi chat."""

    reply: str
    session_id: Optional[str] = None
    suggestions: list[str] = Field(default_factory=list)
    charts: list[dict] = Field(default_factory=list)
    usage: dict = Field(default_factory=dict)


class ChatStreamResponse(BaseModel):
    """Thông tin dùng để kết nối tới luồng SSE đã khởi tạo."""

    stream_id: str
    session_id: str
