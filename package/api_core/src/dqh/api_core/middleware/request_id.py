"""Assign every request a correlation id and echo it back.

Reads an inbound ``X-Request-ID`` (so a gateway/nginx id is preserved) or mints a
uuid4, publishes it on :data:`dqh.api_core.types.request_id_ctx`, and sets the
same header on the response.
"""
from __future__ import annotations

import uuid

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from dqh.api_core.types import request_id_ctx

HEADER = "x-request-id"


class RequestIdMiddleware:
    def __init__(self, app: ASGIApp, *, header: str = HEADER) -> None:
        self.app = app
        self.header = header.lower()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers") or [])
        incoming = headers.get(self.header.encode())
        rid = incoming.decode() if incoming else uuid.uuid4().hex
        token = request_id_ctx.set(rid)

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                raw = [
                    (k, v)
                    for (k, v) in message.get("headers", [])
                    if k.lower() != self.header.encode()
                ]
                raw.append((self.header.encode(), rid.encode()))
                message["headers"] = raw
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            request_id_ctx.reset(token)


__all__ = ["RequestIdMiddleware", "HEADER"]
