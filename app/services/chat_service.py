"""Business logic tầng service cho luồng chat — build lịch sử hội thoại, lưu memory, gợi ý
followup. Tách khỏi app/api/routes/chat.py để route chỉ còn lo HTTP/SSE, không biết chi tiết
memory/agent."""

from app.memory.service import memory_manager, sanitize_tool_call_history

__all__ = ["build_messages", "persist_turn"]


def build_messages(session_id: str, user_message: str) -> list:
    """Ghép lịch sử đã lưu (đã dọn AIMessage(tool_calls) hỏng) với tin nhắn mới của user."""
    session_memory = memory_manager.get(session_id)
    history = sanitize_tool_call_history(session_memory.get("messages", []))
    return history + [{"role": "user", "content": user_message}]


def persist_turn(session_id: str, messages: list, new_messages: list, charts: list[dict] | None = None) -> None:
    """Lưu toàn bộ trace (tool call/tool result/câu trả lời) của 1 lượt vào memory phiên, để lượt
    sau còn số liệu gốc làm căn cứ."""
    if new_messages:
        memory_manager.update(
            session_id,
            {"messages": messages + new_messages, "charts": charts or []},
        )

