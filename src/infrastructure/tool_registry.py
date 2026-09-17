"""Registry tool cho chatbot -- nap dong tu MCP server luc app khoi dong (xem src/main.py).

1 agent duy nhat dung toan bo tool, khong phan nhom theo module -- mo rong nghiep vu moi chi can
them tool o MCP server, khong can dung vao registry nay.
"""


class ToolRegistry:
    # Khong nap tool "thoigian_hientai" -- ngay hien tai duoc tiem thang vao system message moi
    # lan goi (xem src/utils/time_context.py), dang tin cay hon de LLM tu quyet dinh goi tool.
    _EXCLUDED_PREFIXES = ("thoigian_",)

    def __init__(self) -> None:
        self._tools: list = []

    @property
    def tools(self) -> list:
        return self._tools

    def set_tools(self, tools: list) -> None:
        """Nap toan bo tool discover duoc tu MCP server, tru cac tool bi loai tru tuong minh."""
        self._tools = [tool for tool in tools if not tool.name.startswith(self._EXCLUDED_PREFIXES)]


tool_registry = ToolRegistry()

__all__ = ["ToolRegistry", "tool_registry"]
