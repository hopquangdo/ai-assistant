from typing import Any, TypedDict


class ToolCall(TypedDict):
    name: str
    args: dict[str, Any]
    id: str
