"""Measure wall-clock handler time and expose it as ``X-Response-Time`` (ms)."""
from __future__ import annotations

import time

from starlette.types import ASGIApp, Message, Receive, Scope, Send

HEADER = b"x-response-time"


class TimingMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start = time.perf_counter()

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                elapsed_ms = (time.perf_counter() - start) * 1000
                headers = list(message.get("headers", []))
                headers.append((HEADER, f"{elapsed_ms:.1f}".encode()))
                message["headers"] = headers
                scope["state"] = {**scope.get("state", {}), "elapsed_ms": elapsed_ms}
            await send(message)

        await self.app(scope, receive, send_wrapper)


__all__ = ["TimingMiddleware"]
