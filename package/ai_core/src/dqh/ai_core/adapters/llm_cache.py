"""Cache response LLM — bọc mỏng ``langchain_core.globals.set_llm_cache``.

Cache là process-global (LangChain quyết vậy): mọi model dùng chung. Backend TIÊM VÀO —
``ai_core`` không giữ client. Không truyền gì -> ``InMemoryCache``.

    from dqh.ai_core.adapters.llm_cache import install_cache
    install_cache()                         # RAM, exact-match
    install_cache(SQLiteCache(".cache.db")) # langchain_community
    install_cache(RedisSemanticCache(...))  # semantic — client redis do app dựng

    with cache_disabled():                  # tạm tắt trong 1 khối
        ...
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from langchain_core.caches import BaseCache, InMemoryCache
from langchain_core.globals import get_llm_cache, set_llm_cache

__all__ = ["BaseCache", "InMemoryCache", "install_cache", "clear_cache", "cache_disabled"]


def install_cache(cache: BaseCache | None = None) -> BaseCache:
    """Bật cache global. ``cache=None`` -> ``InMemoryCache``. Trả về cache đang dùng."""
    resolved = cache or InMemoryCache()
    set_llm_cache(resolved)
    return resolved


def clear_cache() -> None:
    """Xoá sạch entry (nếu backend hỗ trợ ``.clear()``)."""
    current = get_llm_cache()
    if current is not None and hasattr(current, "clear"):
        current.clear()


@contextmanager
def cache_disabled() -> Iterator[None]:
    """Tạm tắt cache trong khối ``with`` rồi khôi phục."""
    previous = get_llm_cache()
    set_llm_cache(None)
    try:
        yield
    finally:
        set_llm_cache(previous)
