"""Co che luu tru memory don gian cho chatbot (in-process, theo session_id)."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from langchain_core.messages import AIMessage, ToolMessage


def sanitize_tool_call_history(messages: list) -> list:
    """Loai bo moi AIMessage(tool_calls=...) khong co du ToolMessage phan hoi di kem ngay sau no.

    Lich su luu trong memory co the bi hong neu 1 luot chat truoc do bi loi giua chung (exception,
    timeout MCP, hoac bug o tang SSE gom message khong du) -- khi do gui thang lai cho OpenAI se bi
    tu choi voi loi 400 "tool_calls must be followed by tool messages". Ham nay chay truoc moi luot
    goi model de don sach phan lich su hong do, tranh phai restart server/tao session moi thu cong.
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
            # thieu tool response -> bo luon AIMessage nay + cac ToolMessage le da thu duoc
            i = j
            continue
        result.append(message)
        i += 1
    return result


class MemoryStore:
    """Quan ly memory theo session_id cho chatbot."""

    def __init__(self) -> None:
        self._store: dict[str, dict[str, Any]] = defaultdict(dict)

    def get(self, session_id: str) -> dict[str, Any]:
        """Lay memory hien tai cho mot session."""
        return self._store[session_id]

    def set(self, session_id: str, key: str, value: Any) -> None:
        """Luu mot gia tri memory vao session."""
        self._store[session_id][key] = value

    def update(self, session_id: str, data: dict[str, Any]) -> None:
        """Cap nhat nhieu gia tri memory cho mot session."""
        self._store[session_id].update(data)

    def clear(self, session_id: str) -> None:
        """Xoa toan bo memory cho mot session."""
        if session_id in self._store:
            del self._store[session_id]


memory_store = MemoryStore()

__all__ = ["MemoryStore", "memory_store", "sanitize_tool_call_history"]
