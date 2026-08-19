"""Định nghĩa schema trạng thái đồ thị cho chatbot."""

from typing import Annotated, Optional, TypedDict

from langgraph.graph.message import add_messages


class GraphState(TypedDict, total=False):
    """Schema state dùng trong StateGraph của chatbot."""

    messages: Annotated[list, add_messages]
    user_id: Optional[str]
    role: Optional[str]
    error: Optional[dict]
