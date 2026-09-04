"""``AgentTask`` (đầu vào) và ``AgentOutcome`` (đầu ra) cho agent chạy theo hàng đợi / stream."""
from __future__ import annotations

import time
import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["AgentTask", "AgentOutcome"]


class AgentTask(BaseModel):
    """1 yêu cầu cho agent, lấy từ Kafka / queue / stream / bất kỳ ``TaskSource`` nào."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    input: str
    thread_id: str | None = None
    """Nối với Conversation/memory. None -> mỗi task là 1 hội thoại độc lập (dùng ``id``)."""
    reply_to: str | None = None
    """Đích trả kết quả (topic / callback). ``OutcomeSink`` của app tự diễn giải."""
    metadata: dict[str, Any] = Field(default_factory=dict)
    raw: Any = Field(default=None, repr=False, exclude=True)
    """Handle gốc của message (để ``TaskSource.ack``/``nack``). Không serialize."""
    received_at: float = Field(default_factory=time.time)


class AgentOutcome(BaseModel):
    """Kết quả sau khi agent xử lý xong 1 ``AgentTask``."""

    task_id: str
    thread_id: str | None = None
    reply_to: str | None = None
    reply: str = ""
    new_messages: list[dict] = Field(default_factory=list)
    """Message mới sinh ra, đã serialize (``dqh.ai_core.core.memory.serialize_messages``)."""
    usage: dict | None = None
    error: str | None = None
    finished_at: float = Field(default_factory=time.time)

    @property
    def ok(self) -> bool:
        return self.error is None
