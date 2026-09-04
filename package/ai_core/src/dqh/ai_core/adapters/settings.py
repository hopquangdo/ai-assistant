from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

#: Default model for :func:`dqh.ai_core.get_chat_model` when passed a bare provider string.
DEFAULT_MODEL = "anthropic:claude-sonnet-5"


def _find_env_file() -> Path | None:
    """Nearest ``.env`` walking up from the cwd (pydantic-settings only checks cwd)."""
    cwd = Path.cwd()
    return next((p / ".env" for p in [cwd, *cwd.parents] if (p / ".env").is_file()), None)


class Settings(BaseSettings):
    """Process-wide config, read from the environment (and the nearest ``.env``).

    Field names map to upper-case env vars (``llm_model_name`` -> ``LLM_MODEL_NAME``).
    Provider-native aliases are accepted where it helps. Subclass this in an app to
    add fields; :func:`dqh.ai_core.get_chat_model` still consumes it.
    """

    model_config = SettingsConfigDict(env_file_encoding="utf-8", extra="ignore")

    llm_model_name: str = Field(default="", validation_alias="LLM_MODEL_NAME")
    llm_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("LLM_API_KEY", "OPENROUTER_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"),
    )
    llm_base_url: str = Field(default="", validation_alias=AliasChoices("LLM_BASE_URL", "BASE_URL"))
    llm_temperature: float = 0.0
    llm_max_tokens: int | None = None

    # MCP (optional) — consumed by dqh.ai_core.adapters.mcp.load_mcp_tools. Auth header is built as
    # ``{mcp_auth_header}: {mcp_auth_scheme} {mcp_api_key}`` and only sent when the key is set.
    mcp_server_url: str = Field(default="", validation_alias=AliasChoices("MCP_SERVER_URL", "MCP_URL"))
    mcp_api_key: str = Field(default="", validation_alias=AliasChoices("MCP_API_KEY", "MCP_TOKEN"))
    mcp_auth_header: str = Field(default="Authorization", validation_alias="MCP_AUTH_HEADER")
    mcp_auth_scheme: str = Field(default="Bearer", validation_alias="MCP_AUTH_SCHEME")
    mcp_transport: str = Field(default="streamable_http", validation_alias="MCP_TRANSPORT")
    mcp_timeout: float = Field(default=30.0, validation_alias="MCP_TIMEOUT")


@lru_cache
def get_settings(*, use_dotenv: bool = True) -> Settings:
    """Cached :class:`Settings`. ``use_dotenv=False`` reads the environment only.

    Call ``get_settings.cache_clear()`` in tests after mutating the environment.
    """
    return Settings(_env_file=_find_env_file() if use_dotenv else None)
