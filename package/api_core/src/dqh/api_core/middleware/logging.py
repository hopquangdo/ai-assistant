"""One structured log line per request: method, path, status, duration.

Nothing is emitted unless the host configures logging, e.g.::

    logging.getLogger("dqh.api_core").setLevel(logging.INFO)
"""
from __future__ import annotations

import logging
import time

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from dqh.api_core.types import current_request_id

logger = logging.getLogger("dqh.api_core.access")


class RequestLoggingMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start = time.perf_counter()
        status_code = 500

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.info(
                "%s %s -> %s (%.1fms)",
                scope.get("method", "?"),
                scope.get("path", "?"),
                status_code,
                elapsed_ms,
                extra={"request_id": current_request_id(), "status": status_code},
            )


__all__ = ["RequestLoggingMiddleware"]
