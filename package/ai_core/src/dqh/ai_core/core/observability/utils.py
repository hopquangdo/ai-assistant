from typing import Any


def model_name_of(model: Any) -> str:
    """Best-effort human name of a LangChain chat model."""
    for attr in ("model_name", "model", "model_id", "deployment_name"):
        val = getattr(model, attr, None)
        if isinstance(val, str) and val:
            return val
    return type(model).__name__


def _clip(s: str, n: int = 200) -> str:
    s = " ".join(str(s).split())
    return s if len(s) <= n else s[:n] + " …"
