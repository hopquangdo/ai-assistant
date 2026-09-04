"""Connection + auth config for a single MCP server."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from dqh.ai_core.adapters.settings import Settings, get_settings


@dataclass(frozen=True)
class MCPServerConfig:
    """Everything needed to reach one MCP server.

    The auth header is built as ``{auth_header}: {auth_scheme} {api_key}`` and is
    only sent when ``api_key`` is set. An empty ``auth_scheme`` sends the raw key
    (e.g. header ``X-API-Key``).
    """

    url: str
    api_key: str = ""
    auth_header: str = "Authorization"
    auth_scheme: str = "Bearer"
    transport: str = "streamable_http"
    timeout: float | None = 30.0
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_settings(cls, settings: Settings | None = None, **overrides: Any) -> "MCPServerConfig":
        """Build from ``MCP_*`` settings/env; keyword ``overrides`` win."""
        s = settings or get_settings()
        cfg = cls(
            url=overrides.pop("url", s.mcp_server_url),
            api_key=overrides.pop("api_key", s.mcp_api_key),
            auth_header=overrides.pop("auth_header", s.mcp_auth_header),
            auth_scheme=overrides.pop("auth_scheme", s.mcp_auth_scheme),
            transport=overrides.pop("transport", s.mcp_transport),
            timeout=overrides.pop("timeout", s.mcp_timeout),
            extra=overrides.pop("extra", {}),
        )
        if overrides:
            raise TypeError(f"MCPServerConfig.from_settings: tham số lạ {', '.join(overrides)}")
        return cfg

    @property
    def headers(self) -> dict[str, str]:
        if not self.api_key:
            return {}
        value = f"{self.auth_scheme} {self.api_key}".strip() if self.auth_scheme else self.api_key
        return {self.auth_header: value}

    def to_connection(self) -> dict[str, Any]:
        """The dict shape ``MultiServerMCPClient`` expects for this server."""
        if not str(self.url).strip():
            raise RuntimeError("Thiếu MCP_SERVER_URL — bắt buộc để kết nối MCP server.")
        conn: dict[str, Any] = {"url": self.url, "transport": self.transport}
        if self.headers:
            conn["headers"] = self.headers
        if self.timeout is not None:
            conn["timeout"] = self.timeout
        conn.update(self.extra)
        return conn


__all__ = ["MCPServerConfig"]
