from typing import Protocol, runtime_checkable

from langchain_core.runnables import RunnableConfig


@runtime_checkable
class Node(Protocol):
    async def __call__(self, state: dict, config: RunnableConfig) -> dict: ...