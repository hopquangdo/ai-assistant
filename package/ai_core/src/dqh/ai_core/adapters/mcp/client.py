"""Discover LangChain tools from MCP server(s).

Thin wrapper over ``langchain-mcp-adapters``' ``MultiServerMCPClient``: holds a
``{name: MCPServerConfig}`` map and returns stock LangChain ``BaseTool`` objects,
ready to hand to :class:`dqh.ai_core.Agent`.

    from dqh.ai_core import MCPClient, load_mcp_tools

    tools = await load_mcp_tools()                          # from env / .env (MCP_*)
    tools = await load_mcp_tools(url="http://x/mcp", api_key="secret")

    client = MCPClient.from_settings()                      # or build one and reuse it
    tools = await client.get_tools()

Requires the ``mcp`` extra::  pip install "dqh-ai-core[mcp]"
"""
from __future__ import annotations

import logging
from typing import Any

from langchain_core.tools import BaseTool

from dqh.ai_core.adapters.settings import Settings
from dqh.ai_core.adapters.mcp.config import MCPServerConfig

logger = logging.getLogger("dqh.ai_core")


class MCPClient:
    """A set of named MCP servers you can discover tools from."""

    def __init__(self, servers: dict[str, MCPServerConfig]) -> None:
        if not servers:
            raise ValueError("MCPClient cần ít nhất 1 server.")
        self.servers = servers

    @classmethod
    def from_settings(
        cls,
        settings: Settings | None = None,
        *,
        name: str = "backend",
        **overrides: Any,
    ) -> "MCPClient":
        """Single server built from ``MCP_*`` settings/env (``overrides`` win)."""
        return cls({name: MCPServerConfig.from_settings(settings, **overrides)})

    @property
    def connections(self) -> dict[str, dict[str, Any]]:
        return {name: cfg.to_connection() for name, cfg in self.servers.items()}

    async def get_tools(self) -> list[BaseTool]:
        """Connect to every server and return the union of their tools."""
        from langchain_mcp_adapters.client import MultiServerMCPClient

        tools = await MultiServerMCPClient(self.connections).get_tools()
        logger.info("mcp tools discovered: servers=%s count=%d", list(self.servers), len(tools))
        return tools


async def load_mcp_tools(*, settings: Settings | None = None, **overrides: Any) -> list[BaseTool]:
    """Convenience: build an :class:`MCPClient` from settings/env, return its tools."""
    return await MCPClient.from_settings(settings, **overrides).get_tools()


__all__ = ["MCPClient", "load_mcp_tools"]
