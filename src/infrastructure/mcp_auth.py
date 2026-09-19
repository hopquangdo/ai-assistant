"""httpx auth for MCP connections: adds the current turn's user token to every MCP request.

Tools are loaded once at startup (no token: only tools/list), but each tool call opens its own MCP
session through the connection config, so the header is resolved per request from the ContextVar.
The X-API-Key that identifies this service is configured separately (MCP_API_KEY)."""

from collections.abc import Generator

import httpx

from src.core.request_context import mcp_token_var


class McpUserAuth(httpx.Auth):
    def auth_flow(self, request: httpx.Request) -> Generator[httpx.Request, httpx.Response, None]:
        token = mcp_token_var.get()
        if token:
            request.headers["Authorization"] = f"Bearer {token}"
        yield request


__all__ = ["McpUserAuth"]
