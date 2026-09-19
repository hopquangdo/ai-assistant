"""Per-chat-turn context shared with code that has no access to the request (MCP calls, tool cache).

Set at the start of a turn (ChatStreamService._produce, which runs in its own asyncio task, so the
values never leak between turns) and read wherever the acting user matters.
"""

from contextvars import ContextVar

# Short-lived token issued by the backend for this turn; forwarded to MCP so tools run as the user.
mcp_token_var: ContextVar[str | None] = ContextVar("mcp_token", default=None)
# User the turn runs for; part of the tool cache key so users never share cached tool results.
user_id_var: ContextVar[str | None] = ContextVar("user_id", default=None)

__all__ = ["mcp_token_var", "user_id_var"]
