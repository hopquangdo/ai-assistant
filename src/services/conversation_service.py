"""Quan ly conversation (session) + lich su message -- khong biet gi ve streaming/agent.

Duoc ChatStreamService goi de doc lich su truoc khi chay 1 luot, va ghi lai trace sau khi
luot do chay xong."""

from typing import Any

from langchain_core.messages import AIMessage, ToolMessage

from src.infrastructure.memory.store import memory_store


def _sanitize_tool_call_history(messages: list) -> list:
    """Loai bo AIMessage co tool call nhung thieu ToolMessage phan hoi."""
    result: list = []
    index = 0
    while index < len(messages):
        message = messages[index]
        tool_calls = getattr(message, "tool_calls", None)
        if isinstance(message, AIMessage) and tool_calls:
            expected_ids = {call.get("id") for call in tool_calls if call.get("id")}
            collected: list = []
            found_ids: set = set()
            next_index = index + 1
            while next_index < len(messages) and isinstance(messages[next_index], ToolMessage):
                collected.append(messages[next_index])
                found_ids.add(messages[next_index].tool_call_id)
                next_index += 1
            if expected_ids and expected_ids.issubset(found_ids):
                result.append(message)
                result.extend(collected)
            index = next_index
            continue
        result.append(message)
        index += 1
    return result


def _normalize_message_payload(message: Any) -> dict[str, str]:
    if isinstance(message, dict):
        role = message.get("role") or message.get("type") or "user"
        content = message.get("content", "")
    else:
        role = getattr(message, "type", None) or getattr(message, "role", None) or "user"
        content = getattr(message, "content", "") or ""

    role_name = str(role).lower()
    if role_name in {"human", "user"}:
        normalized_role = "user"
    elif role_name in {"ai", "assistant"}:
        normalized_role = "assistant"
    elif role_name == "tool":
        normalized_role = "tool"
    else:
        normalized_role = "user" if role_name == "" else role_name

    return {"role": normalized_role, "content": str(content or "")}


class ConversationService:
    """CRUD conversation/session + message history (goc luu tru: MemoryStore in-process)."""

    def create_conversation(self, session_id: str) -> None:
        """Dam bao 1 entry conversation ton tai cho session_id (no-op neu da co)."""
        memory_store.get(session_id)

    def delete_conversation(self, session_id: str) -> None:
        memory_store.clear(session_id)

    def clear_messages(self, session_id: str) -> None:
        memory_store.update(session_id, {"messages": []})

    def get_messages(self, session_id: str) -> list[dict[str, str]]:
        """Lay lich su tin nhan da luu cua mot session."""
        session_memory = memory_store.get(session_id)
        history = session_memory.get("messages", [])
        return [_normalize_message_payload(message) for message in history]

    def get_message_page(self, session_id: str, page: int = 1, limit: int = 20) -> dict[str, Any]:
        """Lay danh sach message da luu theo trang."""
        if page < 1:
            page = 1
        if limit < 1:
            limit = 20

        messages = self.get_messages(session_id)
        total = len(messages)
        total_pages = (total + limit - 1) // limit if total else 0
        safe_page = min(page, total_pages if total_pages else 1)
        start = (safe_page - 1) * limit
        end = start + limit
        page_items = messages[start:end]

        return {
            "session_id": session_id,
            "page": safe_page,
            "limit": limit,
            "total": total,
            "total_pages": total_pages,
            "items": page_items,
            "has_prev": safe_page > 1,
            "has_next": safe_page < total_pages,
        }

    def get_conversation(self, session_id: str) -> dict[str, Any]:
        """Lay du lieu conversation cung toan bo tin nhan va chart."""
        session_memory = memory_store.get(session_id)
        return {
            "session_id": session_id,
            "messages": self.get_messages(session_id),
            "charts": session_memory.get("charts", []),
            "updated_at": session_memory.get("updated_at"),
        }

    def build_messages(self, session_id: str, user_message: str) -> list:
        """Ghep lich su da luu (da don AIMessage(tool_calls) hong) voi tin nhan moi cua user."""
        session_memory = memory_store.get(session_id)
        history = _sanitize_tool_call_history(session_memory.get("messages", []))
        return history + [{"role": "user", "content": user_message}]

    def persist_turn(self, session_id: str, messages: list, new_messages: list, charts: list[dict] | None = None) -> None:
        """Luu toan bo trace (tool call/tool result/cau tra loi) cua 1 luot vao memory phien, de
        luot sau con so lieu goc lam can cu."""
        if new_messages:
            memory_store.update(
                session_id,
                {"messages": messages + new_messages, "charts": charts or []},
            )


conversation_service = ConversationService()

__all__ = ["ConversationService", "conversation_service"]
