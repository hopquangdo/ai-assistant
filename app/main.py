"""Khai báo FastAPI app và đăng ký các router cho dịch vụ chatbot."""

from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI

from dqh.svc_core.http.adapters.fastapi import create_app

from app.agent import warmup_agent
from app.routes import router
from app.logging import configure_logging
from app.mcp_client import load_all_tools
from app.tools import ALL_TOOLS, set_tools

configure_logging()
logger = logging.getLogger("chatbot.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Nạp tool từ MCP server 1 lần khi app khởi động."""
    try:
        tools = await load_all_tools()
        set_tools(tools)
        logger.info(f"mcp tools loaded: count={len(ALL_TOOLS)} names={sorted(t.name for t in ALL_TOOLS)}")
    except Exception:
        logger.exception("failed to load mcp tools at startup")
    # Nạp sẵn model + graph + mở connection pool tới LLM để request đầu tiên không dính cold start.
    await warmup_agent()
    yield


# create_app (dqh.svc_core) lo sẵn: middleware request-id / timing / access-log,
# exception handler trả về envelope ApiResponse, và endpoint /health không version hoá
# (alias cho Docker HEALTHCHECK / LB / k8s).
#
# Frontend gọi thẳng chatbot (bỏ qua Next.js rewrite proxy) cho endpoint streaming —
# rewrite proxy của Next.js dev server buffer response, phá luồng SSE thời gian thực.
#
# Prefix /api/v1 khớp quy ước versioning của backend (mọi controller Spring đều /api/v1/...)
# — nginx route /api/v1/chat[/stream] thẳng vào chatbot mà không cần strip/rewrite path.
app = create_app(
    title="Contract Chatbot",
    lifespan=lifespan,
    cors_origins=["http://localhost:3000"],
    routers=[router],
    router_prefix="/api/v1",
)


if __name__ == "__main__":
    import uvicorn

    from app.settings import get_settings

    settings = get_settings()
    uvicorn.run("app.main:app", host=settings.app_host, port=settings.app_port, reload=True)
