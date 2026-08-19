"""Cơ chế lưu trữ memory đơn giản cho chatbot."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from langchain_core.messages import AIMessage, ToolMessage

from app.schemas.graph import GraphState


def sanitize_tool_call_history(messages: list) -> list:
    """Loại bỏ mọi AIMessage(tool_calls=...) không có đủ ToolMessage phản hồi đi kèm ngay sau nó.

    Lịch sử lưu trong memory có thể bị hỏng nếu 1 lượt chat trước đó bị lỗi giữa chừng (exception,
    timeout MCP, hoặc bug ở tầng SSE gom message không đủ) — khi đó gửi thẳng lại cho OpenAI sẽ bị
    từ chối với lỗi 400 "tool_calls must be followed by tool messages". Hàm này chạy trước mỗi lượt
    gọi model để dọn sạch phần lịch sử hỏng đó, tránh phải restart server/tạo session mới thủ công.
    """
    result: list = []
    i = 0
    n = len(messages)
    while i < n:
        message = messages[i]
        tool_calls = getattr(message, "tool_calls", None)
        if isinstance(message, AIMessage) and tool_calls:
            expected_ids = {call.get("id") for call in tool_calls if call.get("id")}
            collected: list = []
            found_ids: set = set()
            j = i + 1
            while j < n and isinstance(messages[j], ToolMessage):
                collected.append(messages[j])
                found_ids.add(messages[j].tool_call_id)
                j += 1
            if expected_ids and expected_ids.issubset(found_ids):
                result.append(message)
                result.extend(collected)
            # thiếu tool response -> bỏ luôn AIMessage này + các ToolMessage lẻ đã thu được
            i = j
            continue
        result.append(message)
        i += 1
    return result


class MemoryManager:
    """Quản lý memory theo session_id cho chatbot."""

    def __init__(self) -> None:
        self._store: dict[str, dict[str, Any]] = defaultdict(dict)

    def get(self, session_id: str) -> dict[str, Any]:
        """Lấy memory hiện tại cho một session."""
        return self._store[session_id]

    def set(self, session_id: str, key: str, value: Any) -> None:
        """Lưu một giá trị memory vào session."""
        self._store[session_id][key] = value

    def update(self, session_id: str, data: dict[str, Any]) -> None:
        """Cập nhật nhiều giá trị memory cho một session."""
        self._store[session_id].update(data)

    def clear(self, session_id: str) -> None:
        """Xóa toàn bộ memory cho một session."""
        if session_id in self._store:
            del self._store[session_id]


memory_manager = MemoryManager()
