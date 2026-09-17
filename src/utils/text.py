"""Đọc file văn bản và trả về nội dung dưới dạng chuỗi."""

from pathlib import Path


def load_text_file(path: Path) -> str:
    """Đọc file văn bản UTF-8 và trả về nội dung."""
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"Không tìm thấy file prompt: {path}")

    return path.read_text(encoding="utf-8").strip()


def load_prompt(name: str | None = None, prompt_dir: Path | None = None) -> str:
    """Load a prompt from the shared agents/prompts package."""
    directory = prompt_dir or Path(__file__).resolve().parents[1] / "agents" / "prompts"
    if name is None:
        name = "prompt"
    prompt_name = Path(name).stem
    prompt_name = {
        "select": "node_select",
        "response": "node_response",
        "chart": "node_chart",
        "chart_decision": "node_chart_decision",
        "suggestion": "node_suggestion",
    }.get(prompt_name, prompt_name)
    for suffix in (".md", ".txt"):
        path = directory / f"{prompt_name}{suffix}"
        if path.is_file():
            return load_text_file(path)
    raise FileNotFoundError(f"Không tìm thấy prompt '{name}' trong {directory}")
