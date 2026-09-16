from langgraph.graph import END

from app.agents.state import OrchestratorState


def route_after_react(state: OrchestratorState) -> str:
    return END if state.get("recursion_hit") else "response"


def route_after_clarify(state: OrchestratorState) -> str:
    if state.get("clarification_needed"):
        return END
    return "react" if state.get("needs_react", True) else END


def route_after_response(state: OrchestratorState) -> str:
    return "genchart" if state.get("should_generate_chart") else "suggestion"


__all__ = ["route_after_react", "route_after_clarify", "route_after_response"]
