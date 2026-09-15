"""Khai báo FastAPI app và đăng ký các router cho dịch vụ chatbot."""

from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI

from dqh.ai_core import load_mcp_tools
from dqh.svc_core.transports.http.fastapi import create_app

from app.agent import warmup_agent
from app.routes import router
from app.logging import configure_logging
from app.settings import get_settings
from app.tools import ALL_TOOLS, set_tools

configure_logging()
logger = logging.getLogger("chatbot.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Nạp tool từ MCP server 1 lần khi app khởi động."""
    try:
        tools = await load_mcp_tools(settings=get_settings())
        set_tools(tools)
        logger.info(f"mcp tools loaded: count={len(ALL_TOOLS)} names={sorted(t.name for t in ALL_TOOLS)}")
    except Exception:
        logger.exception("failed to load mcp tools at startup")
    # Nạp sẵn model + graph + mở connection pool tới LLM để request đầu tiên không dính cold start.
    await warmup_agent()
    yield


app = create_app(
    title="Contract Chatbot",
    lifespan=lifespan,
    cors_origins=["http://localhost:3000"],
    routers=[router],
    router_prefix="/api/v1",
)


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run("app.main:app", host=settings.app_host, port=settings.app_port, reload=True)
