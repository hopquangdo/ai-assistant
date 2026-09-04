import json
from pathlib import Path

def _load_price_table() -> dict[str, dict[str, float]]:
    """Đọc ``model_prices.json`` — đi ngược cây thư mục tìm ``data/model_prices.json``.

    Bắt cả wheel đã cài (``dqh/ai_core/data/``) lẫn source checkout (``package/ai_core/data/``).
    """
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "data" / "model_prices.json"
        if candidate.is_file():
            return json.loads(candidate.read_text(encoding="utf-8"))
    raise FileNotFoundError(
        f"model_prices.json not found (walked up from {here})"
    )


_DATA = _load_price_table()

#: USD per 1M tokens per model: ``{"input", "cached_input", "output"}``. Loaded
#: from ``data/model_prices.json`` (edit that file to add endpoints). Keys are
#: matched as substrings of the resolved model name, longest key first.
PRICE_TABLE: dict[str, dict[str, float]] = _DATA["prices"]

#: USD -> VND conversion rate (``usd_to_vnd`` in ``model_prices.json``).
USD_TO_VND: float = float(_DATA.get("usd_to_vnd", 0) or 0)


def usd_to_vnd(usd: float) -> float:
    """Convert a USD amount to VND using :data:`USD_TO_VND` (``0`` if unset)."""
    return usd * USD_TO_VND

#: Back-compat view: ``{model: (input, output)}`` USD per 1M tokens.
PRICES: dict[str, tuple[float, float]] = {
    k: (v["input"], v["output"]) for k, v in PRICE_TABLE.items()
}


def _price_entry(model: str) -> dict[str, float]:
    for key in sorted(PRICE_TABLE, key=len, reverse=True):
        if key in model:
            return PRICE_TABLE[key]
    return {"input": 0.0, "cached_input": 0.0, "output": 0.0}


def price_for(model: str) -> tuple[float, float]:
    """(input, output) USD per 1M tokens for ``model`` — ``(0, 0)`` if unknown."""
    e = _price_entry(model)
    return (e["input"], e["output"])


def cached_price_for(model: str) -> float:
    """USD per 1M cached (prompt-cache read) input tokens — ``0`` if unknown."""
    return _price_entry(model).get("cached_input", 0.0)

