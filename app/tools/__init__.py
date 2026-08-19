"""Registry tool cho chatbot — nạp động từ MCP server lúc app khởi động (xem app/main.py).

1 agent duy nhất dùng toàn bộ tool, không phân nhóm theo module — mở rộng nghiệp vụ mới chỉ cần
thêm tool ở MCP server, không cần đụng vào registry này.
"""

ALL_TOOLS: list = []

# Không nạp tool "thoigian_hientai" — ngày hiện tại được tiêm thẳng vào system message mỗi lần gọi
# (xem app/utils/time_context.py), đáng tin cậy hơn để LLM tự quyết định gọi tool.
_EXCLUDED_PREFIXES = ("thoigian_",)


def set_tools(tools: list) -> None:
    """Nạp toàn bộ tool discover được từ MCP server, trừ các tool bị loại trừ tường minh."""
    ALL_TOOLS[:] = [tool for tool in tools if not tool.name.startswith(_EXCLUDED_PREFIXES)]


__all__ = ["ALL_TOOLS", "set_tools"]
