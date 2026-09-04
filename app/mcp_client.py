"""Nạp tool từ MCP server backend Java — mỏng, uỷ quyền cho dqh.ai_core.

Cấu hình qua biến môi trường (xem app/settings.py + dqh.ai_core.Settings):
    MCP_SERVER_URL   URL endpoint MCP (vd http://localhost:8080/mcp)
    MCP_API_KEY      khóa auth — phải khớp APP_MCP_API_KEY ở backend
    MCP_AUTH_HEADER  tên header (backend này: X-API-Key — đã set default trong app/settings.py)
    MCP_AUTH_SCHEME  prefix giá trị header (backend này: rỗng — gửi khóa thô)
"""

from dqh.ai_core import load_mcp_tools

from app.settings import get_settings


async def load_all_tools() -> list:
    """Discover toàn bộ tool từ MCP server (gọi 1 lần lúc app khởi động)."""
    # Truyền Settings của app (đã override header/scheme cho backend Java) thay vì để
    # dqh.ai_core tự đọc base Settings.
    return await load_mcp_tools(settings=get_settings())
