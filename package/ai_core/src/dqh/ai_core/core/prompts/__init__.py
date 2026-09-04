"""dqh.ai_core.core.prompts — nạp & quản lý prompt theo file, có version + render biến."""
from dqh.ai_core.core.prompts.registry import PromptNotFound, PromptRegistry

__all__ = ["PromptRegistry", "PromptNotFound"]
