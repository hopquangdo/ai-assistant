"""Khai bÃ¡o FastAPI app vÃ  Ä‘Äƒng kÃ½ cÃ¡c router cho dá»‹ch vá»¥ chatbot."""

from contextlib import asynccontextmanager
import asyncio
import logging
import sys

from fastapi import FastAPI

if sys.platform == "win32":
    # psycopg (checkpointer Postgres) khong chay duoc o che do async tren ProactorEventLoop
    # mac dinh cua Windows -- phai chuyen sang SelectorEventLoop.
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from dqh.ai_core import load_mcp_tools
from dqh.svc_core.transports.http.fastapi import create_app

from src.agents.orchestrator import warmup_agent
from app.api.routes import router as api_router
from src.core.logging import configure_logging
from src.core.config import get_settings
from src.infrastructure.mcp_auth import McpUserAuth
from src.infrastructure.memory.client import checkpointer_factory
from src.infrastructure.message_queue.client import redis_client_factory
from src.infrastructure.tool_registry import tool_registry

configure_logging()
logger = logging.getLogger("chatbot.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Náº¡p tool tá»« MCP server 1 láº§n khi app khá»Ÿi Ä‘á»™ng."""
    try:
        tools = await load_mcp_tools(settings=get_settings(), extra={"auth": McpUserAuth()})
        tool_registry.set_tools(tools)
        logger.info(f"mcp tools loaded: count={len(tool_registry.tools)} names={sorted(t.name for t in tool_registry.tools)}")
    except Exception:
        logger.exception("failed to load mcp tools at startup")
    # Náº¡p sáºµn model + graph + má»Ÿ connection pool tá»›i LLM Ä‘á»ƒ request Ä‘áº§u tiÃªn khÃ´ng dÃ­nh cold start.
    await warmup_agent()
    yield
    await checkpointer_factory.close()
    await redis_client_factory.close()


app = create_app(
    title="Contract Chatbot",
    lifespan=lifespan,
    cors_origins=["http://localhost:3000"],
    routers=[api_router],
    router_prefix="/api",
)


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run("src.main:app", host=settings.app_host, port=settings.app_port, reload=True)

