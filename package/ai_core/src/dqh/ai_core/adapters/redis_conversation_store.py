"""``RedisConversationStore`` — ``ConversationStore`` trên Redis.

Store NHẬN client ``redis.asyncio.Redis`` đã dựng sẵn — không tự tạo / đóng connection,
không đọc host/credentials. ``ai_core`` chỉ định nghĩa key scheme + serialize; app sở hữu client.

    import redis.asyncio as redis
    store = RedisConversationStore(redis.from_url(url), prefix="chatbot", ttl_seconds=7 * 86400)

Key scheme (``{prefix}`` mặc định ``aicore:conv``):
    {prefix}:msg:{thread_id}    string  — JSON list message
    {prefix}:meta:{thread_id}   hash    — field -> JSON value
    {prefix}:threads            zset    — member=thread_id, score=updated_at (epoch) → list_threads
"""
from __future__ import annotations

import json
import time
from typing import Any, Sequence

from langchain_core.messages import BaseMessage

from dqh.ai_core.core.conversation.store import ConversationStore, deserialize_messages, serialize_messages

__all__ = ["RedisConversationStore"]


class RedisConversationStore(ConversationStore):
    """``client``: instance ``redis.asyncio.Redis`` (decode_responses tùy ý). ``append`` dùng mặc định của base."""

    def __init__(self, client: Any, *, prefix: str = "aicore:conv", ttl_seconds: int | None = None) -> None:
        self._r = client
        self._prefix = prefix.rstrip(":")
        self._ttl = ttl_seconds

    # -- keys ---------------------------------------------------------------

    def _msg_key(self, thread_id: str) -> str:
        return f"{self._prefix}:msg:{thread_id}"

    def _meta_key(self, thread_id: str) -> str:
        return f"{self._prefix}:meta:{thread_id}"

    @property
    def _index_key(self) -> str:
        return f"{self._prefix}:threads"

    # -- ConversationStore ------------------------------------------------

    async def load(self, thread_id: str) -> list[BaseMessage]:
        raw = await self._r.get(self._msg_key(thread_id))
        return deserialize_messages(json.loads(raw)) if raw else []

    async def replace(self, thread_id: str, messages: Sequence[BaseMessage]) -> None:
        await self._r.set(self._msg_key(thread_id), json.dumps(serialize_messages(messages), ensure_ascii=False))
        await self._after_write(thread_id, touch_meta=False)

    async def get_meta(self, thread_id: str, key: str, default: Any = None) -> Any:
        raw = await self._r.hget(self._meta_key(thread_id), key)
        return json.loads(raw) if raw is not None else default

    async def set_meta(self, thread_id: str, key: str, value: Any) -> None:
        await self._r.hset(self._meta_key(thread_id), key, json.dumps(value, ensure_ascii=False))
        await self._after_write(thread_id)

    async def clear(self, thread_id: str) -> None:
        await self._r.delete(self._msg_key(thread_id), self._meta_key(thread_id))
        await self._r.zrem(self._index_key, thread_id)

    async def list_threads(self, *, limit: int = 100) -> list[str]:
        ids = await self._r.zrevrange(self._index_key, 0, max(limit - 1, 0))
        return [i.decode() if isinstance(i, bytes) else i for i in ids]

    # -- nội bộ -----------------------------------------------------------

    async def _after_write(self, thread_id: str, *, touch_meta: bool = True) -> None:
        await self._r.zadd(self._index_key, {thread_id: time.time()})
        if self._ttl:
            await self._r.expire(self._msg_key(thread_id), self._ttl)
            if touch_meta:
                await self._r.expire(self._meta_key(thread_id), self._ttl)
