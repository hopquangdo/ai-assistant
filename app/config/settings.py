from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # LLM
    llm_provider: str = "openrouter"
    llm_model: str = "openai/gpt-4o-mini"
    llm_api_key: str = Field(default="", validation_alias="OPENROUTER_API_KEY")
    llm_base_url: str = Field(default="https://openrouter.ai/api/v1", validation_alias="BASE_URL")
    llm_temperature: float = 0.0
    llm_max_tokens: int = 4096

    # MCP
    mcp_server_url: str = "http://localhost:8080/mcp"

    # App
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()
