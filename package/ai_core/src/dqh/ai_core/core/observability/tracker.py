"""Token usage + cost tracking and per-step logging for agent runs.

LangChain already reports per-call token counts on ``AIMessage.usage_metadata``.
:class:`UsageTracker` is a callback handler that sums those into a :class:`Usage`
and logs every LLM / tool step through the ``dqh.ai_core`` logger.

    from dqh.ai_core import Agent, Usage, UsageTracker

    agent = Agent.create(tools, system=...)
    await agent.run("...", track=True)
    print(agent.usage.summary())        # -> "... · 3 llm · 5 tool · 1200+800 tok · $0.0156"

Nothing is logged unless the host configures logging, e.g.::

    logging.getLogger("dqh.ai_core").setLevel(logging.INFO)
"""
from __future__ import annotations

import logging
import time
from typing import Any, Callable

from langchain_core.callbacks import BaseCallbackHandler

from dqh.ai_core.core.observability.model import Usage
from dqh.ai_core.core.observability.utils import _clip

logger = logging.getLogger("dqh.ai_core")



class UsageTracker(BaseCallbackHandler):
    """Callback handler: tally tokens/cost and log each LLM / tool step.

    Pass via ``config={"callbacks": [tracker]}`` (``Agent.run(track=True)`` does
    this for you). ``on_step`` optionally receives a structured dict per event.
    """

    def __init__(
        self,
        usage: Usage | None = None,
        *,
        on_step: Callable[[dict], None] | None = None,
        log: logging.Logger | None = None,
    ) -> None:
        self.usage = usage if usage is not None else Usage()
        self._on_step = on_step
        self._log = log or logger
        self._summary_logged = False
        self._t0: dict[Any, float] = {}       # run_id -> perf_counter() at start
        self._run_start: float | None = None  # first activity, for the wall-clock total
        self._llm_ms = 0.0                     # cumulative time spent inside LLM calls
        self._tool_ms = 0.0                    # cumulative time spent inside tool calls

    def _mark_start(self, run_id: Any) -> None:
        now = time.perf_counter()
        self._t0[run_id] = now
        if self._run_start is None:
            self._run_start = now

    def _elapsed_ms(self, run_id: Any) -> float | None:
        t = self._t0.pop(run_id, None)
        return round((time.perf_counter() - t) * 1000, 1) if t is not None else None

    # -- LLM ---------------------------------------------------------------
    def on_llm_start(self, serialized: Any, prompts: Any, *, run_id: Any = None, **_: Any) -> None:
        self._mark_start(run_id)

    # chat models emit on_chat_model_start, not on_llm_start
    def on_chat_model_start(self, serialized: Any, messages: Any, *, run_id: Any = None, **_: Any) -> None:
        self._mark_start(run_id)

    def on_llm_end(self, response: Any, *, run_id: Any = None, **_: Any) -> None:
        elapsed_ms = self._elapsed_ms(run_id)
        if elapsed_ms is not None:
            self._llm_ms += elapsed_ms
        self.usage.llm_calls += 1
        got_in = got_out = got_cache = 0
        for batch in getattr(response, "generations", []) or []:
            for gen in batch:
                msg = getattr(gen, "message", None)
                um = getattr(msg, "usage_metadata", None) or {}
                got_in += um.get("input_tokens", 0) or 0
                got_out += um.get("output_tokens", 0) or 0
                details = um.get("input_token_details") or {}
                got_cache += details.get("cache_read", 0) or 0
        # fall back to llm_output usage (older providers)
        if not (got_in or got_out):
            tu = (getattr(response, "llm_output", None) or {}).get("token_usage", {}) or {}
            got_in = tu.get("prompt_tokens", 0) or 0
            got_out = tu.get("completion_tokens", 0) or 0
        self.usage.input_tokens += got_in
        self.usage.output_tokens += got_out
        self.usage.cache_read_tokens += got_cache
        self._emit(
            "llm",
            model=self.usage.model or "?",
            call=self.usage.llm_calls,
            elapsed_ms=elapsed_ms,
            tokens_in=got_in,
            tokens_out=got_out,
            cache_read=got_cache,
            cum_in=self.usage.input_tokens,
            cum_out=self.usage.output_tokens,
            cum_cache=self.usage.cache_read_tokens,
            cum_tool_calls=self.usage.tool_calls,
            total_cost_usd=round(self.usage.cost_usd, 6),
            total_cost_vnd=round(self.usage.cost_vnd, 2),
        )

    # -- agent lifecycle -------------------------------------------------
    def on_chain_end(self, outputs: Any, **kw: Any) -> None:
        # parent_run_id is None => the outermost graph run just finished.
        if kw.get("parent_run_id") is None:
            self.log_summary()

    def on_chain_error(self, error: BaseException, **kw: Any) -> None:
        if kw.get("parent_run_id") is None:
            self.log_summary(error=f"{type(error).__name__}: {error}")

    def log_summary(self, *, error: str | None = None) -> None:
        """Emit ONE line with the full cost/token total for the whole run.

        Called automatically when the top-level graph run ends; safe to call
        manually too (it only logs once per tracker)."""
        if self._summary_logged:
            return
        self._summary_logged = True
        wall_ms = (
            round((time.perf_counter() - self._run_start) * 1000, 1)
            if self._run_start is not None
            else None
        )
        llm_ms = round(self._llm_ms, 1)
        tool_ms = round(self._tool_ms, 1)
        other_ms = round(wall_ms - llm_ms - tool_ms, 1) if wall_ms is not None else None
        fields: dict[str, Any] = {
            "model": self.usage.model or "?",
            "llm_calls": self.usage.llm_calls,
            "tool_calls": self.usage.tool_calls,
            "wall_ms": wall_ms,
            "llm_ms": llm_ms,
            "tool_ms": tool_ms,
            "other_ms": other_ms,
            "tokens_in": self.usage.input_tokens,
            "tokens_out": self.usage.output_tokens,
            "cache_read": self.usage.cache_read_tokens,
            "total_tokens": self.usage.total_tokens,
            "total_cost_usd": round(self.usage.cost_usd, 6),
            "total_cost_vnd": round(self.usage.cost_vnd, 2),
        }
        if error:
            fields["error"] = error
        self._emit("usage", level=logging.WARNING if error else logging.INFO, **fields)

    # -- tools -----------------------------------------------------------
    def on_tool_start(self, serialized: dict | None, input_str: str, *, run_id: Any = None, **_: Any) -> None:
        self.usage.tool_calls += 1
        self._mark_start(run_id)
        name = (serialized or {}).get("name", "?")
        self._emit("tool_start", tool=name, args=_clip(input_str))

    def on_tool_end(self, output: Any, *, run_id: Any = None, **_: Any) -> None:
        elapsed_ms = self._elapsed_ms(run_id)
        if elapsed_ms is not None:
            self._tool_ms += elapsed_ms
        self._emit("tool_end", elapsed_ms=elapsed_ms, output=_clip(str(output)))

    def on_tool_error(self, error: BaseException, **_: Any) -> None:
        self._emit("tool_error", error=f"{type(error).__name__}: {error}", level=logging.WARNING)

    # -- internal ------------------------------------------------------
    def _emit(self, event: str, *, level: int = logging.INFO, **fields: Any) -> None:
        self._log.log(level, "%s %s", event,
                      " ".join(f"{k}={v}" for k, v in fields.items()))
        if self._on_step:
            self._on_step({"event": event, **fields})
