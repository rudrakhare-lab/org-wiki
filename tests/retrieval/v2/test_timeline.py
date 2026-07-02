"""Unit tests for the timeline module (pure functions over candidate dicts)."""
from datetime import datetime, timedelta, timezone


def _now():
    return datetime(2026, 7, 2, tzinfo=timezone.utc)


def _row(days_ago_updated=0, days_ago_resolved=None,
         status_category="done", comment_count=0):
    now = _now()
    updated = now - timedelta(days=days_ago_updated)
    resolved = now - timedelta(days=days_ago_resolved) if days_ago_resolved is not None else None
    return {
        "updated_at": updated,
        "resolved_at": resolved,
        "status_category": status_category,
        "comment_count": comment_count,
    }


def test_assign_bucket_within_180d_is_latest(monkeypatch):
    from backend.retrieval.v2 import timeline
    monkeypatch.setattr(timeline, "_utcnow", _now)
    assert timeline.assign_bucket(_row(days_ago_updated=30)) == "latest"


def test_assign_bucket_boundary_179d_is_latest(monkeypatch):
    from backend.retrieval.v2 import timeline
    monkeypatch.setattr(timeline, "_utcnow", _now)
    assert timeline.assign_bucket(_row(days_ago_updated=179)) == "latest"


def test_assign_bucket_boundary_181d_is_historical(monkeypatch):
    from backend.retrieval.v2 import timeline
    monkeypatch.setattr(timeline, "_utcnow", _now)
    r = _row(days_ago_updated=181, status_category="done", days_ago_resolved=181)
    assert timeline.assign_bucket(r) == "historical"


def test_assign_bucket_substantive_resolution_beats_age(monkeypatch):
    from backend.retrieval.v2 import timeline
    monkeypatch.setattr(timeline, "_utcnow", _now)
    r = _row(days_ago_updated=800, days_ago_resolved=800,
             status_category="done", comment_count=3)
    assert timeline.assign_bucket(r) == "latest"


def test_assign_bucket_stale_open(monkeypatch):
    from backend.retrieval.v2 import timeline
    monkeypatch.setattr(timeline, "_utcnow", _now)
    r = _row(days_ago_updated=300, status_category="new")
    assert timeline.assign_bucket(r) == "stale_open"


def test_timeline_score_monotonic_recent_higher(monkeypatch):
    from backend.retrieval.v2 import timeline
    monkeypatch.setattr(timeline, "_utcnow", _now)
    new = _row(days_ago_updated=1, days_ago_resolved=1, status_category="done")
    old = _row(days_ago_updated=365, days_ago_resolved=365, status_category="done")
    assert timeline.timeline_score(new) > timeline.timeline_score(old)


def test_timeline_score_status_tier_ordering(monkeypatch):
    from backend.retrieval.v2 import timeline
    monkeypatch.setattr(timeline, "_utcnow", _now)
    done_res = _row(days_ago_updated=30, days_ago_resolved=30, status_category="done")
    done     = _row(days_ago_updated=30, status_category="done")
    indet    = _row(days_ago_updated=30, status_category="indeterminate")
    new      = _row(days_ago_updated=30, status_category="new")
    assert (timeline.timeline_score(done_res) > timeline.timeline_score(done)
            > timeline.timeline_score(indet) > timeline.timeline_score(new))


def test_timeline_score_has_floor(monkeypatch):
    from backend.retrieval.v2 import timeline
    monkeypatch.setattr(timeline, "_utcnow", _now)
    ancient = _row(days_ago_updated=5000, status_category="new")
    assert timeline.timeline_score(ancient) >= 0.05
