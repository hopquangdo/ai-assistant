"""A ready-made health router.

    from dqh.api_core.health import health_router
    app.include_router(health_router())                       # GET /health
    app.include_router(health_router(checks={"mcp": ping}))   # runs checks, 503 on failure

Each check is a zero-arg callable (sync or async); it passes unless it raises or
returns a falsy value.
"""
from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable, Mapping
from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse

Check = Callable[[], Any | Awaitable[Any]]


def health_router(
    *,
    path: str = "/health",
    checks: Mapping[str, Check] | None = None,
    tags: list[str] | None = None,
) -> APIRouter:
    router = APIRouter(tags=tags or ["health"])
    checks = dict(checks or {})

    @router.get(path)
    async def health() -> JSONResponse:
        results: dict[str, str] = {}
        healthy = True
        for name, check in checks.items():
            try:
                out = check()
                if inspect.isawaitable(out):
                    out = await out
                ok = out is None or bool(out)
                results[name] = "ok" if ok else "fail"
                healthy = healthy and ok
            except Exception as exc:  # noqa: BLE001 - report, don't crash the probe
                results[name] = f"fail: {type(exc).__name__}"
                healthy = False
        body: dict[str, Any] = {"status": "ok" if healthy else "degraded"}
        if results:
            body["checks"] = results
        return JSONResponse(status_code=200 if healthy else 503, content=body)

    return router


__all__ = ["health_router", "Check"]
