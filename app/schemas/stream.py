"""Schema dùng chung cho mọi event trong luồng xử lý chatbot."""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class StreamEventName(StrEnum):
    """Ten custom event noi bo (dispatch_custom_event) — dung chung cho moi node
    thay vi moi node tu bja chuoi rieng. Event tu dqh.ai_core (ToolStartEvent,
    TokenEvent, ...) va SSE name o chat.py khong thuoc pham vi enum nay."""

    RESPONSE_START = "response.start"
    RESPONSE_DELTA = "response.delta"
    RESPONSE_COMPLETED = "response.completed"


class StreamEvent(BaseModel):
    """Envelope thống nhất cho custom event nội bộ và SSE event public."""

    name: str
    payload: dict[str, Any] = Field(default_factory=dict)