"""Khai báo FastAPI app và đăng ký các router cho dịch vụ chatbot."""

from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.logging import configure_logging
from app.mcp.client import load_all_tools
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
    yield


app = FastAPI(title="Contract Chatbot", lifespan=lifespan)

# Frontend gọi thẳng chatbot (bỏ qua Next.js rewrite proxy) cho endpoint streaming —
# rewrite proxy của Next.js dev server buffer response, phá luồng SSE thời gian thực.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["POST", "GET"],
    allow_headers=["Content-Type"],
)

# Khớp quy ước versioning của backend (mọi controller Spring đều /api/v1/...) — nginx route
# /api/v1/chat[/stream] thẳng vào chatbot mà không cần strip/rewrite path.
app.include_router(router, prefix="/api/v1")


@app.get("/health")
def health_root() -> dict[str, str]:
    """Alias không version hoá — dùng cho Docker HEALTHCHECK/health check hạ tầng (LB, k8s...)."""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    from app.config.settings import get_settings

    settings = get_settings()
    uvicorn.run("app.main:app", host=settings.app_host, port=settings.app_port, reload=True)
