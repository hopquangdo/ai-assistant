"""Lap graph 3 node: react -> response -> genchart."""

from functools import lru_cache

from langgraph.graph import END, START, StateGraph

from app.agents.nodes.genchart import GenChartNode
from app.agents.nodes.react import ReActNode
from app.agents.nodes.response import ResponseNode
from app.agents.nodes.suggestion import SuggestionNode
from app.agents.state import OrchestratorState
from app.tools.registry import ALL_TOOLS


def _route_after_react(state: OrchestratorState) -> str:
    return END if state.get("recursion_hit") else "response"


def _route_after_response(state: OrchestratorState) -> str:
    return "genchart" if state.get("should_generate_chart") else "suggestion"


class ChatGraph:
    def __init__(self):
        self.react = ReActNode(ALL_TOOLS)
        self.response = ResponseNode()
        self.genchart = GenChartNode()
        self.suggestion = SuggestionNode()

    def build(self):
        builder = StateGraph(OrchestratorState)
        builder.add_node("react", self.react)
        builder.add_node("response", self.response)
        builder.add_node("genchart", self.genchart)
        builder.add_node("suggestion", self.suggestion)
        builder.add_edge(START, "react")
        builder.add_conditional_edges("react", _route_after_react, {"response": "response", END: END})
        builder.add_conditional_edges(
            "response",
            _route_after_response,
            {"genchart": "genchart", "suggestion": "suggestion"},
        )
        builder.add_edge("genchart", "suggestion")
        builder.add_edge("suggestion", END)
        return builder.compile()


@lru_cache
def get_orchestrator_graph():
    return ChatGraph().build()
