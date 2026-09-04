"""Server-Sent Events helpers.

    from dqh.api_core.streaming import sse, SSEResponse

    async def gen():
        yield sse("token", {"content": "hi"})
        yield sse("done", {"ok": True})

    return SSEResponse(gen())

:func:`sse` formats one ``event:``/``data:`` frame (JSON, UTF-8 kept as-is).
:class:`SSEResponse` is a ``StreamingResponse`` with the headers that stop
nginx / dev proxies from buffering the stream.
"""
from __future__ import annotations

import json
from collections.abc import AsyncIterable
from typing import Any

from starlette.responses import StreamingResponse

SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "X-Accel-Buffering": "no",
    "Connection": "keep-alive",
}


def sse(event: str, data: Any = None, *, id: str | None = None, retry: int | None = None) -> str:
    """Format a single SSE frame. ``data`` is JSON-encoded unless it is a str."""
    lines: list[str] = []
    if id is not None:
        lines.append(f"id: {id}")
    if retry is not None:
        lines.append(f"retry: {retry}")
    lines.append(f"event: {event}")
    payload = data if isinstance(data, str) else json.dumps(data, ensure_ascii=False, default=str)
    for line in payload.split("\n"):
        lines.append(f"data: {line}")
    return "\n".join(lines) + "\n\n"


class SSEResponse(StreamingResponse):
    def __init__(self, content: AsyncIterable[str], **kwargs: Any) -> None:
        headers = {**SSE_HEADERS, **(kwargs.pop("headers", None) or {})}
        super().__init__(content, media_type="text/event-stream", headers=headers, **kwargs)


__all__ = ["sse", "SSEResponse", "SSE_HEADERS"]
