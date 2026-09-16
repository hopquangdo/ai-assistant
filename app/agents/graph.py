"""Lap graph: clarify -> react -> response -> genchart."""

from functools import lru_cache

from langgraph.graph import END, START, StateGraph

from app.agents.nodes.clarify import ClarifyNode
from app.agents.nodes.genchart import GenChartNode
from app.agents.nodes.react import ReActNode
from app.agents.nodes.response import ResponseNode
from app.agents.nodes.suggestion import SuggestionNode
from app.agents.routing import route_after_clarify, route_after_react, route_after_response
from app.agents.state import OrchestratorState
from app.tools.registry import ALL_TOOLS


class ChatGraph:
    def __init__(self):
        self.clarify = ClarifyNode(ALL_TOOLS)
        self.react = ReActNode(ALL_TOOLS)
        self.response = ResponseNode()
        self.genchart = GenChartNode()
        self.suggestion = SuggestionNode()

    def build(self):
        builder = StateGraph(OrchestratorState)
        builder.add_node(self.clarify.name, self.clarify)
        builder.add_node(self.react.name, self.react)
        builder.add_node(self.response.name, self.response)
        builder.add_node(self.genchart.name, self.genchart)
        builder.add_node(self.suggestion.name, self.suggestion)
        builder.add_edge(START, self.clarify.name)
        builder.add_conditional_edges(
            self.clarify.name,
            route_after_clarify,
            {
                self.react.name: self.react.name,
                END: END,
            },
        )
        builder.add_conditional_edges(
            self.react.name,
            route_after_react,
            {self.response.name: self.response.name, END: END},
        )
        builder.add_conditional_edges(
            self.response.name,
            route_after_response,
            {
                self.genchart.name: self.genchart.name,
                self.suggestion.name: self.suggestion.name,
            },
        )
        builder.add_edge(self.genchart.name, self.suggestion.name)
        builder.add_edge(self.suggestion.name, END)
        return builder.compile()


@lru_cache
def get_orchestrator_graph():
    return ChatGraph().build()
