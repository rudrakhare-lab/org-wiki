"""Per-query cost footer: cost_for_trace is fail-open, config rate parses safely,
and QueryResponse carries the cost fields."""
import importlib


def test_cost_for_trace_none_for_missing_id():
    from backend import trace_store
    assert trace_store.cost_for_trace(None) is None
    assert trace_store.cost_for_trace("") is None


def test_cost_for_trace_fail_open_on_unknown_trace():
    # An unknown trace id must not raise — returns a dict with cost_usd None, or None.
    from backend import trace_store
    result = trace_store.cost_for_trace("does-not-exist-trace-id")
    assert result is None or result.get("cost_usd") in (None, 0, 0.0)


def test_usd_inr_rate_default_and_override(monkeypatch):
    import backend.config as config
    monkeypatch.delenv("CONWO_USD_INR", raising=False)
    importlib.reload(config)
    assert config.CONWO_USD_INR == 88.0
    monkeypatch.setenv("CONWO_USD_INR", "90.5")
    importlib.reload(config)
    assert config.CONWO_USD_INR == 90.5
    # Malformed value falls back to the default, never crashes import.
    monkeypatch.setenv("CONWO_USD_INR", "not-a-number")
    importlib.reload(config)
    assert config.CONWO_USD_INR == 88.0
    monkeypatch.delenv("CONWO_USD_INR", raising=False)
    importlib.reload(config)


def test_query_response_has_cost_fields():
    from backend.api import QueryResponse
    r = QueryResponse(answer_id="a", answer_text="t", confidence="High",
                      sources={}, retrieval={})
    assert r.cost_usd == 0.0
    assert r.cost_inr == 0.0
