"""Schema dùng chung cho mọi event trong luồng xử lý chatbot."""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class StreamEventName(StrEnum):
    """Ten custom event noi bo (dispatch_custom_event) — generic theo PHASE, dung
    chung cho moi node thay vi moi node tu bja ten rieng (vi du "react.tools_start").
    Node phat sinh tu ghi ro minh la ai qua payload["node"], khong qua ten event.
    Event tu dqh.ai_core (ToolStartEvent, TokenEvent, ...) va SSE name o chat.py
    khong thuoc pham vi enum nay."""

    NODE_START = "node.start"
    NODE_DELTA = "node.delta"
    NODE_COMPLETED = "node.completed"

    TOOL_START = "tool.start"


class StreamEvent(BaseModel):
    """Envelope thống nhất cho custom event nội bộ và SSE event public."""

    name: str
    payload: dict[str, Any] = Field(default_factory=dict)