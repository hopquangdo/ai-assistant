from __future__ import annotations

from typing import Any

from src.models.chat_entity import ChatConversationEntity, ChatMessageEntity
from src.infrastructure.memory.store import memory_store


class ChatRepository:
    """Repository nhẹ cho session memory hiện tại."""

    def get_messages(self, session_id: str) -> list[ChatMessageEntity]:
        session_memory = memory_store.get(session_id)
        history = session_memory.get("messages", [])
        result: list[ChatMessageEntity] = []
        for message in history:
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
            result.append(ChatMessageEntity(role=normalized_role, content=str(content or "")))
        return result

    def get_conversation(self, session_id: str) -> ChatConversationEntity:
        session_memory = memory_store.get(session_id)
        return ChatConversationEntity(
            session_id=session_id,
            messages=self.get_messages(session_id),
            charts=session_memory.get("charts", []),
            updated_at=session_memory.get("updated_at"),
        )

    def get_message_page(self, session_id: str, page: int = 1, limit: int = 20) -> dict[str, Any]:
        messages = self.get_messages(session_id)
        total = len(messages)
        total_pages = (total + limit - 1) // limit if total else 0
        safe_page = min(page, total_pages if total_pages else 1)
        start = (safe_page - 1) * limit
        end = start + limit
        items = messages[start:end]
        return {
            "session_id": session_id,
            "page": safe_page,
            "limit": limit,
            "total": total,
            "total_pages": total_pages,
            "items": [
                {"role": item.role, "content": item.content}
                for item in items
            ],
            "has_prev": safe_page > 1,
            "has_next": safe_page < total_pages,
        }


chat_repository = ChatRepository()
