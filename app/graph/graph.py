"""Định nghĩa đồ thị cho chatbot — 1 agent duy nhất, không routing/orchestrator/responder riêng."""

from functools import lru_cache
import logging

from langgraph.graph import END, StateGraph

from app.agents.base import agent_node
from app.graph.state import GraphState

logger = logging.getLogger("chatbot.graph")


def build_graph():
    """Xây dựng và trả về workflow graph cho chatbot: 1 node "agent" duy nhất, nạp toàn bộ tool."""
    workflow = StateGraph(GraphState)

    workflow.add_node("agent", agent_node)
    workflow.set_entry_point("agent")
    workflow.add_edge("agent", END)

    logger.info("Graph built")
    return workflow.compile()


@lru_cache
def get_graph():
    """Lưu cache graph và trả về graph đã build."""
    return build_graph()
