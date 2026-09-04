"""``ConversationStore`` — hợp đồng lưu lịch sử hội thoại + metadata theo ``thread_id``.

ABC: impl PHẢI kế thừa và hiện thực các ``@abstractmethod``. Base cấp sẵn ``append`` mặc định
(= ``load`` + ``replace``) — backend nào làm nối hiệu quả hơn thì override.

``serialize_messages`` / ``deserialize_messages``: mọi impl backend dùng chung để đổi
``list[BaseMessage]`` <-> JSON (định dạng ổn định ``messages_to_dict`` của langchain).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Iterable, Sequence

from langchain_core.messages import BaseMessage, messages_from_dict, messages_to_dict

__all__ = ["ConversationStore", "serialize_messages", "deserialize_messages"]


class ConversationStore(ABC):
    @abstractmethod
    async def load(self, thread_id: str) -> list[BaseMessage]:
        """Toàn bộ message của thread (rỗng nếu chưa có)."""

    @abstractmethod
    async def replace(self, thread_id: str, messages: Sequence[BaseMessage]) -> None:
        """Ghi đè toàn bộ message của thread."""

    async def append(self, thread_id: str, messages: Sequence[BaseMessage]) -> None:
        """Nối thêm message vào cuối thread. Mặc định: load + replace (không nguyên tử).

        Backend hỗ trợ nối nguyên tử (vd jsonb ``||``) nên override cho hiệu quả/an toàn hơn.
        """
        current = await self.load(thread_id)
        await self.replace(thread_id, [*current, *messages])

    @abstractmethod
    async def get_meta(self, thread_id: str, key: str, default: Any = None) -> Any:
        """Đọc 1 giá trị metadata (vd 'title', 'suggestions')."""

    @abstractmethod
    async def set_meta(self, thread_id: str, key: str, value: Any) -> None:
        """Ghi 1 giá trị metadata."""

    @abstractmethod
    async def clear(self, thread_id: str) -> None:
        """Xoá sạch message + metadata của thread."""

    @abstractmethod
    async def list_threads(self, *, limit: int = 100) -> list[str]:
        """Danh sách thread_id, mới cập nhật nhất trước."""


def serialize_messages(messages: Iterable[BaseMessage]) -> list[dict]:
    """``list[BaseMessage]`` -> ``list[dict]`` JSON-safe (langchain ``messages_to_dict``)."""
    return messages_to_dict(list(messages))


def deserialize_messages(raw: Iterable[dict]) -> list[BaseMessage]:
    """Nghịch đảo :func:`serialize_messages`."""
    return messages_from_dict(list(raw))
