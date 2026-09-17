"""Lap graph: clarify -> react -> response -> genchart."""

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph

from src.infrastructure.memory.client import checkpointer_factory
from src.agents.nodes.clarify import ClarifyNode
from src.agents.nodes.genchart import GenChartNode
from src.agents.nodes.react import ReActNode
from src.agents.nodes.react.state import ReActState
from src.agents.nodes.response import ResponseNode
from src.agents.nodes.suggestion import SuggestionNode
from src.agents.routing import route_after_clarify, route_after_react, route_after_response
from src.agents.state import OrchestratorState
from src.infrastructure.tool_registry import tool_registry


class ChatGraph:
    def __init__(self):
        self.clarify = ClarifyNode(tool_registry.tools)
        self.react = ReActNode(tool_registry.tools)
        self.response = ResponseNode()
        self.genchart = GenChartNode()
        self.suggestion = SuggestionNode()

    def build(self, checkpointer: BaseCheckpointSaver | None = None):
        builder = StateGraph(OrchestratorState)
        builder.add_node(self.clarify.name, self.clarify)
        builder.add_node(self.react.name, self.react, input_schema=ReActState)
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
        return builder.compile(checkpointer=checkpointer)


_graph = None


async def get_orchestrator_graph():
    """Build 1 láº§n, cache trong module (khÃ´ng dÃ¹ng lru_cache vÃ¬ pháº£i await checkpointer)."""
    global _graph
    if _graph is None:
        checkpointer = await checkpointer_factory.get()
        _graph = ChatGraph().build(checkpointer)
    return _graph

