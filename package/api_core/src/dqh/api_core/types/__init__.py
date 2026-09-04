"""Shared primitives for :mod:`dqh.api_core`.

Currently just the request-id context: a :class:`~contextvars.ContextVar` set by
``RequestIdMiddleware`` and read anywhere downstream (loggers, error handlers,
response envelopes) without threading the value through call signatures.
"""
from __future__ import annotations

from contextvars import ContextVar

#: Correlation id for the request currently being handled (``""`` outside a request).
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")


def current_request_id() -> str:
    """Return the id of the in-flight request, or ``""`` if there is none."""
    return request_id_ctx.get()


__all__ = ["request_id_ctx", "current_request_id"]
