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
