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
