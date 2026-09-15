"""Cấu hình logging và tạo logger chung cho chatbot."""

import logging

from dqh.svc_core.middleware.logging import DEFAULT_FORMAT, install_request_id_log_filter

from app.settings import get_settings


def configure_logging() -> None:
    """Khởi tạo cấu hình logging cho ứng dụng.

    Dùng format của dqh.svc_core (có ``[%(request_id)s]``) và gắn filter bơm
    request_id từ ContextVar vào MỌI log record (kể cả dqh.ai_core, uvicorn…),
    nhờ đó mọi dòng log trong 1 request đều có cùng correlation id."""
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
    """Trả về logger theo tên module."""
    return logging.getLogger(name)
