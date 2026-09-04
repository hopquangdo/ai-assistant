"""dqh.ai_core.core.memory — ghi nhớ DÀI HẠN, xuyên phiên (fact, sở thích, tóm tắt tích luỹ).

    models         MemoryItem
    store          MemoryStore (ABC): put / get / delete / list / search
    inmemory_store InMemoryMemoryStore — keyword; cosine nếu có embedding
    embedder       Embedder (Protocol) — app tiêm để search ngữ nghĩa
    extract        extract_memories() — LLM rút fact đáng nhớ từ hội thoại
    facade         Memory — remember() / recall() / add() / forget()

Lịch sử của 1 phiên (ngắn hạn) -> xem ``dqh.ai_core.core.conversation``.
Backend vector (pgvector/Qdrant/…) là INFRA: app viết impl ``MemoryStore`` tiêm vào ``Memory``.
"""
from dqh.ai_core.core.memory.embedder import Embedder
from dqh.ai_core.core.memory.extract import extract_memories
from dqh.ai_core.core.memory.facade import Memory
from dqh.ai_core.core.memory.inmemory_store import InMemoryMemoryStore
from dqh.ai_core.core.memory.models import MemoryItem
from dqh.ai_core.core.memory.store import MemoryStore

__all__ = [
    "Memory",
    "MemoryItem",
    "MemoryStore",
    "InMemoryMemoryStore",
    "Embedder",
    "extract_memories",
]
