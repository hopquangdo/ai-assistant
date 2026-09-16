from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages


class OrchestratorState(TypedDict, total=False):
    messages: Annotated[list, add_messages]
    recursion_hit: bool
    should_generate_chart: bool
    charts: list[dict]
    suggestions: list[str]
