"""``Memory`` — facade gộp store + embedder + extract + recall của long-term memory.

    mem = Memory(InMemoryMemoryStore(), embedder=my_embedder, llm=my_llm)
    await mem.remember("user:42", conversation_messages)     # rút fact + lưu (có embedding nếu có embedder)
    snippets = await mem.recall("user:42", "câu hỏi mới")     # list[str] để chèn vào ContextBuilder.memory(...)
"""
from __future__ import annotations

from typing import Sequence

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage

from dqh.ai_core.core.memory.embedder import Embedder
from dqh.ai_core.core.memory.extract import extract_memories
from dqh.ai_core.core.memory.models import MemoryItem
from dqh.ai_core.core.memory.store import MemoryStore

__all__ = ["Memory"]


class Memory:
    def __init__(
        self,
        store: MemoryStore,
        *,
        embedder: Embedder | None = None,
        llm: BaseChatModel | None = None,
    ) -> None:
        self.store = store
        self._embedder = embedder
        self._llm = llm

    async def add(self, namespace: str, item: MemoryItem) -> None:
        emb = (await self._embedder.embed([item.text]))[0] if self._embedder else None
        await self.store.put(namespace, item, embedding=emb)

    async def remember(self, namespace: str, messages: Sequence[BaseMessage], **extract_kwargs) -> list[MemoryItem]:
        """Rút fact đáng nhớ từ hội thoại (cần ``llm``), lưu từng cái, trả về danh sách đã lưu."""
        if self._llm is None:
            raise RuntimeError("Memory.remember cần 'llm' — truyền vào constructor.")
        existing = [it.text for it in await self.store.list(namespace, limit=50)]
        items = await extract_memories(self._llm, messages, existing=existing, **extract_kwargs)
        for it in items:
            await self.add(namespace, it)
        return items

    async def recall(self, namespace: str, query: str, *, limit: int = 5) -> list[str]:
        """Top-``limit`` ghi nhớ liên quan tới ``query`` -> list câu (để chèn vào prompt)."""
        emb = (await self._embedder.embed([query]))[0] if self._embedder else None
        items = await self.store.search(namespace, query, limit=limit, embedding=emb)
        return [it.text for it in items]

    async def forget(self, namespace: str, key: str) -> None:
        await self.store.delete(namespace, key)
