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


def test_apply_timeline_attaches_bucket_and_score(monkeypatch):
    from backend.retrieval.v2 import timeline
    monkeypatch.setattr(timeline, "_utcnow", _now)
    cands = [
        {"key": "TS-1", "fused_score": 0.04, **_row(days_ago_updated=10)},
        {"key": "TS-2", "fused_score": 0.03, **_row(days_ago_updated=800)},
    ]
    out = timeline.apply_timeline(cands)
    assert out is cands  # in-place mutation; same list returned
    for c in out:
        assert "bucket" in c and "timeline_score" in c


def test_apply_timeline_sorts_by_fused_times_timeline(monkeypatch):
    from backend.retrieval.v2 import timeline
    monkeypatch.setattr(timeline, "_utcnow", _now)
    cands = [
        # Same fused_score, but TS-old is ancient.
        {"key": "TS-old",    "fused_score": 0.04, **_row(days_ago_updated=800)},
        {"key": "TS-recent", "fused_score": 0.04, **_row(days_ago_updated=1)},
    ]
    out = timeline.apply_timeline(cands)
    assert out[0]["key"] == "TS-recent"


def test_bucket_counts_aggregates_labels():
    from backend.retrieval.v2 import timeline
    cands = [
        {"bucket": "latest"},
        {"bucket": "latest"},
        {"bucket": "historical"},
        {"bucket": "stale_open"},
    ]
    counts = timeline.bucket_counts(cands)
    assert counts == {"latest": 2, "historical": 1, "stale_open": 1}


# ── Regression: production crash — updated_at/resolved_at arrived as ISO
# strings instead of datetime objects, and _days_since unconditionally
# accessed dt.tzinfo, raising AttributeError on every /query request that
# reached this path. ─────────────────────────────────────────────────────

def test_days_since_accepts_iso_string_with_offset(monkeypatch):
    from backend.retrieval.v2 import timeline
    monkeypatch.setattr(timeline, "_utcnow", _now)
    row = {"updated_at": "2026-06-02T00:00:00+00:00", "resolved_at": None,
           "status_category": "done", "comment_count": 0}
    # Reproduces the exact production crash path (assign_bucket -> _days_since).
    assert timeline.assign_bucket(row) == "latest"


def test_days_since_accepts_iso_string_with_z_suffix(monkeypatch):
    from backend.retrieval.v2 import timeline
    monkeypatch.setattr(timeline, "_utcnow", _now)
    row = {"updated_at": "2026-06-02T00:00:00Z", "resolved_at": None,
           "status_category": "done", "comment_count": 0}
    assert timeline.assign_bucket(row) == "latest"


def test_days_since_accepts_date_only_string(monkeypatch):
    from backend.retrieval.v2 import timeline
    monkeypatch.setattr(timeline, "_utcnow", _now)
    row = {"updated_at": "2026-06-02", "resolved_at": None,
           "status_category": "done", "comment_count": 0}
    assert timeline.assign_bucket(row) == "latest"


def test_days_since_unparseable_string_treated_as_absent(monkeypatch):
    """Malformed date strings must not crash — fail-open like a missing date."""
    from backend.retrieval.v2 import timeline
    monkeypatch.setattr(timeline, "_utcnow", _now)
    row = {"updated_at": "not-a-date", "resolved_at": None,
           "status_category": "done", "comment_count": 0}
    # Neither updated_at nor resolved_at parse -> falls through to HISTORICAL,
    # not a crash.
    assert timeline.assign_bucket(row) == "historical"


def test_timeline_score_accepts_iso_string(monkeypatch):
    from backend.retrieval.v2 import timeline
    monkeypatch.setattr(timeline, "_utcnow", _now)
    row = {"updated_at": "2026-06-02T00:00:00+00:00", "resolved_at": None,
           "status_category": "done"}
    score = timeline.timeline_score(row)
    assert 0.05 <= score <= 1.0


def test_apply_timeline_end_to_end_with_string_dates(monkeypatch):
    """The exact production call path: apply_timeline -> assign_bucket ->
    _days_since, fed candidates whose dates are strings, as hybrid_search's
    real-world rows apparently are in at least one deployment."""
    from backend.retrieval.v2 import timeline
    monkeypatch.setattr(timeline, "_utcnow", _now)
    cands = [
        {"key": "TS-1", "fused_score": 0.04,
         "updated_at": "2026-06-02T00:00:00+00:00", "resolved_at": None,
         "status_category": "done", "comment_count": 0},
    ]
    out = timeline.apply_timeline(cands)
    assert out[0]["bucket"] == "latest"
