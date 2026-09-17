"""Cac ham thuan tuy xu ly AIMessage, khong phu thuoc node cu the."""

from langchain_core.messages import AIMessage


def strip_trailing_placeholder(messages: list) -> list:
    if messages and isinstance(messages[-1], AIMessage) and not messages[-1].tool_calls:
        return messages[:-1]
    return messages
