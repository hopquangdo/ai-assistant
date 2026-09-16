"""Tiện ích phát custom event cho LangChain/LangGraph callbacks."""

from langchain_core.callbacks.manager import adispatch_custom_event
from langchain_core.runnables import RunnableConfig

from app.schemas.stream import StreamEvent


async def dispatch_custom_event(
    event: StreamEvent,
    config: RunnableConfig,
) -> None:
    """Phát một custom event theo cùng contract callback của LangChain."""
    await adispatch_custom_event(event.name, event.payload, config=config)