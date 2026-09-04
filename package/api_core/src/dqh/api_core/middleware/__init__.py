"""Pure-ASGI middleware and a one-call installer.

    from dqh.api_core.middleware import install_middleware
    install_middleware(app)                 # request-id + timing + access log
    install_middleware(app, cors_origins=["http://localhost:3000"])

Order matters: request-id is added last so it runs first and the id is available
to everything below it.
"""
from __future__ import annotations

from collections.abc import Sequence

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from dqh.api_core.middleware.logging import RequestLoggingMiddleware
from dqh.api_core.middleware.request_id import RequestIdMiddleware
from dqh.api_core.middleware.timing import TimingMiddleware


def install_middleware(
    app: FastAPI,
    *,
    cors_origins: Sequence[str] | None = None,
    access_log: bool = True,
    timing: bool = True,
) -> None:
    if access_log:
        app.add_middleware(RequestLoggingMiddleware)
    if timing:
        app.add_middleware(TimingMiddleware)
    if cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(cors_origins),
            allow_methods=["*"],
            allow_headers=["*"],
        )
    # added last => outermost => runs first
    app.add_middleware(RequestIdMiddleware)


__all__ = [
    "install_middleware",
    "RequestIdMiddleware",
    "TimingMiddleware",
    "RequestLoggingMiddleware",
]
