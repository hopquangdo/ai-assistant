from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages


class OrchestratorState(TypedDict, total=False):
    messages: Annotated[list, add_messages]
    recursion_hit: bool
    clarification_needed: bool
    needs_react: bool
    should_generate_chart: bool
    charts: list[dict]
    suggestions: list[str]
    # Rieng cua ReActNode -- xem src/agents/nodes/react/state.py (ReActState) de biet node nao
    # duoc phep doc/ghi 2 field nay qua input_schema.
    tool_calls_history: list[dict]
    react_iterations: int
