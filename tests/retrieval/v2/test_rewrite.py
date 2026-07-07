from unittest.mock import patch, MagicMock
import json

def test_rewrite_returns_subqueries_for_compound_question():
    from backend.retrieval.v2 import rewrite
    payload = {
        "sub_queries": ["meal booking bugs Q2", "overnight scan bug status"],
        "expansions": {"OTP": ["one-time password"]},
        "filters": {"module": "meal-management"},
        "intent": "DEBUGGING",
    }
    fake = MagicMock()
    fake.messages.create.return_value = MagicMock(
        content=[MagicMock(text=json.dumps(payload))]
    )
    with patch.object(rewrite, "_client", fake):
        r = rewrite.rewrite("what broke in meal booking and is overnight scan fixed?")
    assert r.sub_queries == ["meal booking bugs Q2", "overnight scan bug status"]
    assert r.intent == "DEBUGGING"
    assert r.filters["module"] == "meal-management"

def test_rewrite_falls_back_to_question_on_parse_failure():
    from backend.retrieval.v2 import rewrite
    fake = MagicMock()
    fake.messages.create.return_value = MagicMock(content=[MagicMock(text="not-json")])
    with patch.object(rewrite, "_client", fake):
        r = rewrite.rewrite("how does login work?")
    assert r.sub_queries == ["how does login work?"]
    assert r.intent == "GENERAL"

def test_rewrite_caches_identical_questions_for_5_minutes(monkeypatch):
    from backend.retrieval.v2 import rewrite
    fake = MagicMock()
    payload = {"sub_queries":["q"], "expansions":{}, "filters":{}, "intent":"GENERAL"}
    fake.messages.create.return_value = MagicMock(content=[MagicMock(text=json.dumps(payload))])
    with patch.object(rewrite, "_client", fake):
        rewrite._cache.clear()
        rewrite.rewrite("same question?")
        rewrite.rewrite("same question?")
    assert fake.messages.create.call_count == 1


# --- rewrite hardening — never-raise fallback, fence stripping, bounded cache ---
from backend.retrieval.v2 import rewrite as rw


def test_api_exception_falls_back_to_question(monkeypatch):
    class Boom:
        def create(self, **kw):
            raise RuntimeError("rate limited")
    monkeypatch.setattr(rw, "_client_messages", lambda: Boom())
    out = rw.rewrite("why does OTP fail?")
    assert out.sub_queries == ["why does OTP fail?"]
    assert out.intent == "GENERAL"


def test_fenced_json_is_parsed(monkeypatch):
    fenced = '```json\n{"sub_queries": ["a", "b"], "intent": "DEBUGGING"}\n```'
    monkeypatch.setattr(rw, "_raw_completion", lambda q: fenced)
    out = rw._call_claude("q")
    assert out.sub_queries == ["a", "b"] and out.intent == "DEBUGGING"


def test_cache_is_bounded(monkeypatch):
    monkeypatch.setattr(rw, "_raw_completion",
                        lambda q: '{"sub_queries": ["x"]}')
    rw._cache.clear()
    for i in range(rw._CACHE_MAX + 50):
        rw.rewrite(f"question {i}")
    assert len(rw._cache) <= rw._CACHE_MAX
