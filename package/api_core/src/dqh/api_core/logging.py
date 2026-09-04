"""Make the request-id show up in *every* log line, not just the access log.

``RequestIdMiddleware`` publishes the correlation id on a ContextVar; this filter
copies it onto each :class:`logging.LogRecord` as ``record.request_id`` so a
formatter can reference ``%(request_id)s``. Records emitted outside a request get
``"-"``.

    from dqh.api_core.logging import install_request_id_log_filter, DEFAULT_FORMAT
    logging.basicConfig(format=DEFAULT_FORMAT, ...)
    install_request_id_log_filter()
"""
from __future__ import annotations

import logging

from dqh.api_core.types import current_request_id

#: Drop-in ``logging.basicConfig(format=...)`` value that includes the id.
DEFAULT_FORMAT = "%(asctime)s %(levelname)s [%(request_id)s] %(name)s %(message)s"


class RequestIdLogFilter(logging.Filter):
    """Inject ``request_id`` (from the ContextVar) onto every record it sees."""

    def filter(self, record: logging.LogRecord) -> bool:
        if not getattr(record, "request_id", None):
            record.request_id = current_request_id() or "-"
        return True


def install_request_id_log_filter(*, root: bool = True) -> RequestIdLogFilter:
    """Attach :class:`RequestIdLogFilter` to every current root handler.

    A filter on the *logger* only sees records that logger emits directly, so we
    attach to the handlers instead — those see records propagated from all child
    loggers (``dqh.ai_core``, ``chatbot.*``, ``uvicorn.*`` …).
    """
    flt = RequestIdLogFilter()
    if root:
        handlers = logging.getLogger().handlers
        for handler in handlers:
            handler.addFilter(flt)
    return flt


__all__ = ["RequestIdLogFilter", "install_request_id_log_filter", "DEFAULT_FORMAT"]
