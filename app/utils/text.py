"""Đọc file văn bản và trả về nội dung dưới dạng chuỗi."""

from pathlib import Path


def load_text_file(path: Path) -> str:
    """Đọc file văn bản UTF-8 và trả về nội dung."""
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"Không tìm thấy file prompt: {path}")

    return path.read_text(encoding="utf-8").strip()
