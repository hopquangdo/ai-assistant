"""Nạp prompt cho chatbot (1 agent duy nhất)."""

from pathlib import Path

from app.utils.text import load_text_file

PROMPT_DIR = Path(__file__).resolve().parent

AGENT_PROMPT = load_text_file(PROMPT_DIR / "agent.txt")

__all__ = ["AGENT_PROMPT"]
