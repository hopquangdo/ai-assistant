"""State rieng cua ReActNode -- khai bao qua input_schema khi add_node() de node nay chi
thay (va chi phu thuoc vao) dung nhung field lien quan toi vong lap tool-call, khong dinh
tram vao charts/suggestions/should_generate_chart cua cac node khac trong OrchestratorState."""

from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages


class ReActState(TypedDict, total=False):
    messages: Annotated[list, add_messages]
    recursion_hit: bool
    # Lich su cac lan goi tool trong toan bo thread (khong chi 1 lan chay node) -- de debug/log
    # va lam nen cho cache tool-result sau nay (xem thao luan cache theo tool_name+args).
    tool_calls_history: list[dict]
    # So vong LLM->tool da chay cong don qua cac lan invoke node nay trong cung 1 thread.
    react_iterations: int


__all__ = ["ReActState"]
