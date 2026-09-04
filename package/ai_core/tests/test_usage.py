import logging
from types import SimpleNamespace

from dqh.ai_core import Usage, UsageTracker, price_for


def _llm_result(input_tokens: int, output_tokens: int, cache_read: int = 0):
    msg = SimpleNamespace(usage_metadata={
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "input_token_details": {"cache_read": cache_read},
    })
    gen = SimpleNamespace(message=msg)
    return SimpleNamespace(generations=[[gen]], llm_output={})


def test_price_lookup_matches_substring_longest_first():
    assert price_for("anthropic:claude-sonnet-5") == (3.00, 15.00)
    assert price_for("gpt-4o-mini-2024") == (0.15, 0.60)
    assert price_for("something-unknown") == (0.0, 0.0)


def test_tracker_accumulates_tokens_cost_and_calls():
    u = Usage(model="claude-sonnet-5")
    t = UsageTracker(u)

    t.on_llm_end(_llm_result(1000, 500, cache_read=200))
    t.on_tool_start({"name": "inspect"}, "{}")
    t.on_tool_end("ok")
    t.on_llm_end(_llm_result(2000, 100))

    assert u.llm_calls == 2
    assert u.tool_calls == 1
    assert u.input_tokens == 3000
    assert u.output_tokens == 600
    assert u.cache_read_tokens == 200
    assert u.total_tokens == 3600
    # 200 of the 3000 input tokens are cache reads, billed at the cached rate
    expected = (2800 * 3 + 200 * 0.30 + 600 * 15) / 1_000_000
    assert round(u.cost_usd, 6) == round(expected, 6)


def test_tracker_falls_back_to_llm_output_token_usage():
    u = Usage(model="x")
    t = UsageTracker(u)
    res = SimpleNamespace(generations=[[]],
                          llm_output={"token_usage": {"prompt_tokens": 10, "completion_tokens": 4}})
    t.on_llm_end(res)
    assert (u.input_tokens, u.output_tokens) == (10, 4)


def test_on_step_hook_receives_events():
    events = []
    t = UsageTracker(Usage(model="x"), on_step=events.append)
    t.on_tool_start({"name": "foo"}, "bar")
    assert events and events[0]["event"] == "tool_start" and events[0]["tool"] == "foo"


def test_usage_to_dict_roundtrips_numbers():
    u = Usage(model="claude-haiku-4-5", input_tokens=100, output_tokens=50, llm_calls=1)
    d = u.to_dict()
    assert d["total_tokens"] == 150
    assert d["cost_usd"] == round((100 * 0.8 + 50 * 4.0) / 1_000_000, 6)
