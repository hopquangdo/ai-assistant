from dataclasses import dataclass

from dqh.ai_core.core.observability.pricing import cached_price_for, price_for, usd_to_vnd


@dataclass
class Usage:
    model: str = ""
    llm_calls: int = 0
    tool_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    @property
    def cost_usd(self) -> float:
        p_in, p_out = price_for(self.model)
        p_cached = cached_price_for(self.model)
        cached = min(self.cache_read_tokens, self.input_tokens)
        fresh_in = self.input_tokens - cached
        return (
            fresh_in * p_in + cached * p_cached + self.output_tokens * p_out
        ) / 1_000_000

    @property
    def cost_vnd(self) -> float:
        """``cost_usd`` converted to VND (0 if no rate configured)."""
        return usd_to_vnd(self.cost_usd)

    def add(self, other: "Usage") -> "Usage":
        """Accumulate another Usage into this one (keeps this ``model``)."""
        self.llm_calls += other.llm_calls
        self.tool_calls += other.tool_calls
        self.input_tokens += other.input_tokens
        self.output_tokens += other.output_tokens
        self.cache_read_tokens += other.cache_read_tokens
        self.model = self.model or other.model
        return self

    def summary(self) -> str:
        cache = f" ({self.cache_read_tokens} cache)" if self.cache_read_tokens else ""
        return (
            f"{self.model or '?'} · {self.llm_calls} llm · {self.tool_calls} tool · "
            f"{self.input_tokens}+{self.output_tokens} tok{cache} · ${self.cost_usd:.4f}"
            f" (~{self.cost_vnd:,.0f} VND)"
        )

    def to_dict(self) -> dict:
        return {
            "model": self.model,
            "llm_calls": self.llm_calls,
            "tool_calls": self.tool_calls,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cache_read_tokens": self.cache_read_tokens,
            "total_tokens": self.total_tokens,
            "cost_usd": round(self.cost_usd, 6),
            "cost_vnd": round(self.cost_vnd, 2),
        }