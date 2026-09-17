"""Cáº¥u hÃ¬nh logging vÃ  táº¡o logger chung cho chatbot."""

import logging

from dqh.svc_core.middleware.logging import DEFAULT_FORMAT, install_request_id_log_filter

from src.core.config import get_settings


def configure_logging() -> None:
    """Khá»Ÿi táº¡o cáº¥u hÃ¬nh logging cho á»©ng dá»¥ng.

    DÃ¹ng format cá»§a dqh.svc_core (cÃ³ ``[%(request_id)s]``) vÃ  gáº¯n filter bÆ¡m
    request_id tá»« ContextVar vÃ o Má»ŒI log record (ká»ƒ cáº£ dqh.ai_core, uvicornâ€¦),
    nhá» Ä‘Ã³ má»i dÃ²ng log trong 1 request Ä‘á»u cÃ³ cÃ¹ng correlation id."""
    settings = get_settings()
    log_level = settings.log_level.upper()
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format=DEFAULT_FORMAT,
        datefmt="%Y-%m-%d %H:%M:%S",
        force=True,
    )
    install_request_id_log_filter()


def get_logger(name: str = "chatbot") -> logging.Logger:
    """Tráº£ vá» logger theo tÃªn module."""
    return logging.getLogger(name)

