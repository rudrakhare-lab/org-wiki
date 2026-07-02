"""Tests for backend.jira_retriever._v2_search's ticket normalization and
bucket-routing logic.

Regression coverage for a whole-branch review finding: _v2_search hardcoded
every v2 ticket into buckets["LATEST"] regardless of the per-ticket `bucket`
tag that timeline.apply_timeline() computes upstream. preflight.py's
format_jira_buckets_for_seed() renders from the top-level `buckets` dict, so
this silently hid Historical/Stale-open evidence from the LLM.

Also covers a latent type bug: updated_at may be a real datetime object
(psycopg maps timestamptz -> datetime), and naive `[:10]` slicing on it
raises TypeError.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from unittest.mock import patch

import pytest


@dataclass
class _FakeRetrievalResult:
    """Mirrors backend.retrieval.v2.gate.RetrievalResult's shape."""
    tickets: list[dict]
    confidence: str = "High"
    abstain: bool = False
    message: str = "fake evidence"
    diagnostics: dict = field(default_factory=dict)


def _patch_pipeline_search(monkeypatch, tickets, message="fake evidence"):
    """Monkeypatch backend.retrieval.v2.pipeline.search (imported as `_p`
    inside _v2_search) to return a fake RetrievalResult-like object."""
    import backend.retrieval.v2.pipeline as pipeline_mod

    fake_result = _FakeRetrievalResult(tickets=tickets, message=message)

    def _fake_search(question, *, functional_area=None, limit=10):
        return fake_result

    monkeypatch.setattr(pipeline_mod, "search", _fake_search)
    return fake_result


def _ticket(key, bucket=None, **overrides):
    t = {
        "key": key,
        "summary": f"summary for {key}",
        "status_category": "done",
        "priority": "P2",
        "updated_at": "2026-06-01",
        "resolved_at": None,
        "comment_count": 1,
    }
    if bucket is not None:
        t["bucket"] = bucket
    t.update(overrides)
    return t


class TestBucketRouting:
    def test_latest_ticket_routes_to_latest(self, monkeypatch):
        _patch_pipeline_search(monkeypatch, [_ticket("PB-1", bucket="latest")])
        from backend.jira_retriever import _v2_search

        out = _v2_search("some question")

        assert [t["key"] for t in out["buckets"]["LATEST"]] == ["PB-1"]
        assert out["buckets"]["HISTORICAL"] == []
        assert out["buckets"]["STALE-OPEN"] == []

    def test_historical_ticket_routes_to_historical(self, monkeypatch):
        _patch_pipeline_search(monkeypatch, [_ticket("PB-2", bucket="historical")])
        from backend.jira_retriever import _v2_search

        out = _v2_search("some question")

        assert [t["key"] for t in out["buckets"]["HISTORICAL"]] == ["PB-2"]
        assert out["buckets"]["LATEST"] == []
        assert out["buckets"]["STALE-OPEN"] == []

    def test_stale_open_ticket_routes_to_stale_open(self, monkeypatch):
        _patch_pipeline_search(monkeypatch, [_ticket("PB-3", bucket="stale_open")])
        from backend.jira_retriever import _v2_search

        out = _v2_search("some question")

        assert [t["key"] for t in out["buckets"]["STALE-OPEN"]] == ["PB-3"]
        assert out["buckets"]["LATEST"] == []
        assert out["buckets"]["HISTORICAL"] == []

    def test_mixed_bucket_list_splits_correctly(self, monkeypatch):
        """The test that would have caught the original bug: three tickets,
        one of each bucket, must NOT all land in LATEST."""
        tickets = [
            _ticket("PB-10", bucket="latest"),
            _ticket("PB-11", bucket="historical"),
            _ticket("PB-12", bucket="stale_open"),
        ]
        _patch_pipeline_search(monkeypatch, tickets)
        from backend.jira_retriever import _v2_search

        out = _v2_search("some question")

        assert [t["key"] for t in out["buckets"]["LATEST"]] == ["PB-10"]
        assert [t["key"] for t in out["buckets"]["HISTORICAL"]] == ["PB-11"]
        assert [t["key"] for t in out["buckets"]["STALE-OPEN"]] == ["PB-12"]

    def test_missing_bucket_field_defaults_to_latest(self, monkeypatch):
        _patch_pipeline_search(monkeypatch, [_ticket("PB-20", bucket=None)])
        from backend.jira_retriever import _v2_search

        out = _v2_search("some question")

        assert out["rows"][0]["bucket"] == "latest"
        assert [t["key"] for t in out["buckets"]["LATEST"]] == ["PB-20"]
        assert out["buckets"]["HISTORICAL"] == []
        assert out["buckets"]["STALE-OPEN"] == []


class TestDateNormalization:
    def test_datetime_object_updated_at_becomes_date_string(self, monkeypatch):
        dt = datetime(2026, 5, 17, 13, 45, 0)
        _patch_pipeline_search(
            monkeypatch, [_ticket("PB-30", bucket="latest", updated_at=dt)]
        )
        from backend.jira_retriever import _v2_search

        # Must not raise TypeError on datetime slicing.
        out = _v2_search("some question")

        assert out["rows"][0]["updated"] == "2026-05-17"

    def test_none_updated_at_becomes_question_mark(self, monkeypatch):
        _patch_pipeline_search(
            monkeypatch, [_ticket("PB-31", bucket="latest", updated_at=None)]
        )
        from backend.jira_retriever import _v2_search

        out = _v2_search("some question")

        assert out["rows"][0]["updated"] == "?"

    def test_none_resolved_at_stays_none(self, monkeypatch):
        _patch_pipeline_search(
            monkeypatch, [_ticket("PB-32", bucket="latest", resolved_at=None)]
        )
        from backend.jira_retriever import _v2_search

        out = _v2_search("some question")

        assert out["rows"][0]["resolved"] is None

    def test_datetime_object_resolved_at_becomes_date_string(self, monkeypatch):
        dt = datetime(2026, 1, 2, 9, 0, 0)
        _patch_pipeline_search(
            monkeypatch, [_ticket("PB-33", bucket="latest", resolved_at=dt)]
        )
        from backend.jira_retriever import _v2_search

        out = _v2_search("some question")

        assert out["rows"][0]["resolved"] == "2026-01-02"


# ── _v2_by_module tests — confidence-floor parity with _v1_by_module ──────────

def _fake_candidate(key, **overrides):
    base = {
        "key": key, "summary": "s", "status_category": "done",
        "priority": "P2", "bucket": "latest",
        "updated_at": None, "resolved_at": None,
    }
    base.update(overrides)
    return base


def test_v2_by_module_excludes_untagged_tickets(monkeypatch):
    """A semantically-similar but untagged ticket must NOT appear in the
    result — mirrors _v1_by_module's ticket_module_tags JOIN guarantee."""
    from backend import jira_retriever

    candidates = [_fake_candidate("TS-1"), _fake_candidate("TS-2")]
    monkeypatch.setattr(
        "backend.retrieval.v2.pipeline.by_module",
        lambda module_slug, query, limit: candidates,
    )

    class FakeConn:
        def __enter__(self): return self
        def __exit__(self, *a): pass

    with patch.object(jira_retriever.db, "connection", return_value=FakeConn()):
        with patch.object(
            jira_retriever, "_fetch_modules_for_keys",
            return_value={"TS-1": [{"slug": "desk-management", "confidence": 0.8}]},
            # TS-2 absent -> not tagged to any module at the required floor
        ):
            out = jira_retriever._v2_by_module("desk-management", "booking", limit=5)

    keys = [t["key"] for t in out]
    assert keys == ["TS-1"]


def test_v2_by_module_enriches_with_module_confidence_and_modules(monkeypatch):
    from backend import jira_retriever

    candidates = [_fake_candidate("TS-1")]
    monkeypatch.setattr(
        "backend.retrieval.v2.pipeline.by_module",
        lambda module_slug, query, limit: candidates,
    )

    class FakeConn:
        def __enter__(self): return self
        def __exit__(self, *a): pass

    with patch.object(jira_retriever.db, "connection", return_value=FakeConn()):
        with patch.object(
            jira_retriever, "_fetch_modules_for_keys",
            return_value={"TS-1": [{"slug": "desk-management", "confidence": 0.9}]},
        ):
            out = jira_retriever._v2_by_module("desk-management", "booking", limit=5)

    assert out[0]["module_confidence"] == 0.9
    assert out[0]["modules"] == [{"slug": "desk-management", "confidence": 0.9}]
    assert "updated" in out[0]
    assert "resolved" in out[0]


def test_v2_by_module_modules_field_is_full_tag_list_not_just_the_match(monkeypatch):
    """A ticket tagged to multiple modules must carry ALL of them in `modules`,
    not just the entry matching the queried module_slug. A regression that
    narrowed `modules` down to `[match]` would have passed the single-tag
    test above but silently broken preflight.py's cross-module rendering."""
    from backend import jira_retriever

    candidates = [_fake_candidate("TS-1")]
    monkeypatch.setattr(
        "backend.retrieval.v2.pipeline.by_module",
        lambda module_slug, query, limit: candidates,
    )
    full_tag_list = [
        {"slug": "desk-management", "confidence": 0.9},
        {"slug": "parking-management", "confidence": 0.6},
    ]

    class FakeConn:
        def __enter__(self): return self
        def __exit__(self, *a): pass

    with patch.object(jira_retriever.db, "connection", return_value=FakeConn()):
        with patch.object(
            jira_retriever, "_fetch_modules_for_keys",
            return_value={"TS-1": full_tag_list},
        ):
            out = jira_retriever._v2_by_module("desk-management", "booking", limit=5)

    assert out[0]["modules"] == full_tag_list
    assert out[0]["module_confidence"] == 0.9


def test_v2_by_module_respects_limit_after_filtering(monkeypatch):
    from backend import jira_retriever

    candidates = [_fake_candidate(f"TS-{i}") for i in range(10)]
    monkeypatch.setattr(
        "backend.retrieval.v2.pipeline.by_module",
        lambda module_slug, query, limit: candidates,
    )

    class FakeConn:
        def __enter__(self): return self
        def __exit__(self, *a): pass

    tagged = {f"TS-{i}": [{"slug": "desk-management", "confidence": 0.7}] for i in range(10)}
    with patch.object(jira_retriever.db, "connection", return_value=FakeConn()):
        with patch.object(jira_retriever, "_fetch_modules_for_keys", return_value=tagged):
            out = jira_retriever._v2_by_module("desk-management", "booking", limit=3)

    assert len(out) == 3


def test_v2_by_module_empty_candidates_returns_empty(monkeypatch):
    from backend import jira_retriever
    monkeypatch.setattr(
        "backend.retrieval.v2.pipeline.by_module",
        lambda module_slug, query, limit: [],
    )
    out = jira_retriever._v2_by_module("desk-management", "booking", limit=5)
    assert out == []


def _md_ticket(key, bucket, **overrides):
    base = {
        "key": key, "bucket": bucket, "summary": "does a thing",
        "status_category": "done", "priority": "P2",
        "updated": "2026-06-01", "resolved": None, "comment_count": 1,
    }
    base.update(overrides)
    return base


def test_render_v2_markdown_always_shows_latest_and_historical():
    from backend.jira_retriever import _render_v2_markdown
    tickets = [_md_ticket("TS-1", "latest"), _md_ticket("TS-2", "historical")]
    md = _render_v2_markdown(tickets, confidence="High", message="strong evidence")
    assert "**Latest evidence**" in md
    assert "**Historical evidence**" in md
    assert "TS-1" in md
    assert "TS-2" in md


def test_render_v2_markdown_omits_stale_section_by_default():
    from backend.jira_retriever import _render_v2_markdown
    tickets = [_md_ticket("TS-3", "stale_open")]
    md = _render_v2_markdown(tickets, confidence="Low", message="weak")
    assert "Stale-open" not in md


def test_render_v2_markdown_includes_stale_section_when_requested():
    from backend.jira_retriever import _render_v2_markdown
    tickets = [_md_ticket("TS-3", "stale_open")]
    md = _render_v2_markdown(tickets, confidence="Low", message="weak", include_stale=True)
    assert "**Stale-open**" in md
    assert "TS-3" in md


def test_render_v2_markdown_includes_confidence_header():
    from backend.jira_retriever import _render_v2_markdown
    md = _render_v2_markdown([], confidence="Medium", message="moderate evidence")
    assert "Medium" in md
    assert "moderate evidence" in md


def test_v2_search_markdown_field_uses_renderer(monkeypatch):
    """_v2_search's returned dict must use _render_v2_markdown, not the bare
    gate message, for its 'markdown' field."""
    from backend import jira_retriever
    from dataclasses import dataclass, field

    @dataclass
    class _FakeResult:
        tickets: list
        confidence: str = "High"
        abstain: bool = False
        message: str = "strong evidence"
        diagnostics: dict = field(default_factory=dict)

    fake_result = _FakeResult(tickets=[
        {"key": "TS-1", "summary": "s", "status_category": "done", "priority": "P1",
         "bucket": "latest", "updated_at": None, "resolved_at": None, "comment_count": 0},
    ])
    monkeypatch.setattr(
        "backend.retrieval.v2.pipeline.search",
        lambda question, **kw: fake_result,
    )
    out = jira_retriever._v2_search("some question")
    assert "**Latest evidence**" in out["markdown"]
    assert out["markdown"] != fake_result.message
