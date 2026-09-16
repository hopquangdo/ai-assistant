from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import SettingsConfigDict

from dqh.ai_core import Settings as AiCoreSettings


class Settings(AiCoreSettings):
    """Config toàn tiến trình — kế thừa dqh.ai_core.Settings (các field llm_* + logic dựng
    chat model) và bổ sung phần riêng của chatbot (MCP, host/port)."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # MCP — các field mcp_* kế thừa từ dqh.ai_core.Settings. Override default cho backend Java này:
    # McpApiKeyFilter yêu cầu header "X-API-Key" chứa khóa thô (không có prefix "Bearer").
    mcp_server_url: str = "http://localhost:8080/mcp"
    mcp_auth_header: str = "X-API-Key"
    mcp_auth_scheme: str = ""

    # App
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    log_level: str = "INFO"

    # Gợi ý câu hỏi tiếp theo sau mỗi câu trả lời (1 lần gọi LLM nhẹ, xem app/followups.py).
    enable_followups: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
