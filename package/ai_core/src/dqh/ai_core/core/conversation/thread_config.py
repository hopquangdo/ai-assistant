"""``thread_config`` — dựng ``RunnableConfig`` cho 1 thread khi chạy graph có checkpointer."""
from __future__ import annotations

from typing import Any

from langchain_core.runnables import RunnableConfig

__all__ = ["thread_config"]


def thread_config(thread_id: str, **extra: Any) -> RunnableConfig:
    """``{"configurable": {"thread_id": thread_id, **extra}}``.

    LangGraph checkpointer nạp/lưu state theo ``thread_id`` này. ``extra`` để nhét thêm khoá
    ``configurable`` khác (vd ``checkpoint_ns``, ``user_id``).
    """
    return {"configurable": {"thread_id": thread_id, **extra}}
