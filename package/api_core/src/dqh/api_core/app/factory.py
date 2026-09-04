"""``create_app`` — a FastAPI instance wired with the api_core defaults.

    from dqh.api_core import create_app

    app = create_app(
        title="Contract Chatbot",
        routers=[chat_router],
        cors_origins=["http://localhost:3000"],
        lifespan=lifespan,
        health_checks={"mcp": ping_mcp},
    )

You get: the request-id / timing / access-log middleware, the ``ApiResponse``
exception handlers, and a ``/health`` endpoint. Everything is opt-out via kwargs.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any

from fastapi import APIRouter, FastAPI

from dqh.api_core.errors import install_exception_handlers
from dqh.api_core.health import Check, health_router
from dqh.api_core.middleware import install_middleware


def create_app(
    *,
    title: str = "dqh.api_core app",
    version: str = "0.1.0",
    routers: Sequence[APIRouter] = (),
    router_prefix: str = "",
    cors_origins: Sequence[str] | None = None,
    lifespan: Callable[[FastAPI], Any] | None = None,
    exception_handlers: bool = True,
    access_log: bool = True,
    timing: bool = True,
    health: bool = True,
    health_path: str = "/health",
    health_checks: Mapping[str, Check] | None = None,
    **fastapi_kwargs: Any,
) -> FastAPI:
    app = FastAPI(title=title, version=version, lifespan=lifespan, **fastapi_kwargs)

    install_middleware(
        app,
        cors_origins=cors_origins,
        access_log=access_log,
        timing=timing,
    )
    if exception_handlers:
        install_exception_handlers(app)
    if health:
        app.include_router(health_router(path=health_path, checks=health_checks))
    for router in routers:
        app.include_router(router, prefix=router_prefix)

    return app


__all__ = ["create_app"]
