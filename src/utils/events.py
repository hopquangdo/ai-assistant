"""Tiá»‡n Ã­ch phÃ¡t custom event cho LangChain/LangGraph callbacks."""

from langchain_core.callbacks.manager import adispatch_custom_event
from langchain_core.runnables import RunnableConfig

from src.schemas.stream import StreamEvent


async def dispatch_custom_event(
    event: StreamEvent,
    config: RunnableConfig,
) -> None:
    """PhÃ¡t má»™t custom event theo cÃ¹ng contract callback cá»§a LangChain."""
    await adispatch_custom_event(event.name, event.payload, config=config)
