"""Cấu hình logging và tạo logger chung cho chatbot."""

import logging

from app.config.settings import get_settings


def configure_logging() -> None:
    """Khởi tạo cấu hình logging cho ứng dụng."""
    settings = get_settings()
    log_level = settings.log_level.upper()
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        force=True,
    )


def get_logger(name: str = "chatbot") -> logging.Logger:
    """Trả về logger theo tên module."""
    return logging.getLogger(name)
