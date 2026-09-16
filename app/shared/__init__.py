"""Các tiện ích dùng chung giữa các tầng của chatbot."""

from app.shared.events import dispatch_custom_event

__all__ = ["dispatch_custom_event"]