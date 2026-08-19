from langchain_mcp_adapters.client import MultiServerMCPClient

from app.config.settings import get_settings


def _build_client() -> MultiServerMCPClient:
    settings = get_settings()
    return MultiServerMCPClient(
        {
            "backend": {
                "url": settings.mcp_server_url,
                "transport": "streamable_http",
            }
        }
    )


async def load_all_tools() -> list:
    """Discover toàn bộ tool từ MCP server (gọi 1 lần lúc app khởi động)."""
    client = _build_client()
    return await client.get_tools()
