"""Unit tests for the RRF fusion logic (the SQL is exercised by the integration
test in Task 14; here we test the in-memory fusion across sub-queries)."""


def test_rrf_fuse_combines_two_lists_by_rank():
    from backend.retrieval.v2.hybrid import _rrf_fuse
    a = [{"key": "TS-1", "fused_score": 0.04}, {"key": "TS-2", "fused_score": 0.03}]
    b = [{"key": "TS-2", "fused_score": 0.04}, {"key": "TS-3", "fused_score": 0.03}]
    out = _rrf_fuse([a, b])
    keys = [c["key"] for c in out]
    assert "TS-2" in keys and "TS-1" in keys and "TS-3" in keys
    # TS-2 appears in both → highest fused score
    assert out[0]["key"] == "TS-2"


def test_rrf_fuse_dedupes_same_key():
    from backend.retrieval.v2.hybrid import _rrf_fuse
    a = [{"key": "TS-1", "fused_score": 0.04}]
    b = [{"key": "TS-1", "fused_score": 0.03}]
    out = _rrf_fuse([a, b])
    assert len(out) == 1 and out[0]["key"] == "TS-1"


def test_filters_apply_functional_area_when_set():
    from backend.retrieval.v2.hybrid import _build_filters_sql
    sql, params = _build_filters_sql({"functional_area": "WP-admin"})
    assert "functional_area = %(fa)s" in sql
    assert params == {"fa": "WP-admin"}


def test_filters_apply_resolved_after_when_set():
    from backend.retrieval.v2.hybrid import _build_filters_sql
    sql, params = _build_filters_sql({"resolved_after": "2026-04-01"})
    assert "resolved_at >= %(resolved_after)s" in sql


def test_filters_empty_when_no_filters():
    from backend.retrieval.v2.hybrid import _build_filters_sql
    sql, params = _build_filters_sql({})
    assert sql == "" and params == {}


def test_hybrid_search_result_carries_bucket_and_timeline_score():
    """Verify hybrid_search wires timeline.apply_timeline into the return path.

    Reverse the input row order (TS-old first) to force apply_timeline to actually
    re-sort by fused_score × timeline_score. Uses a hand-rolled FakeConn/FakeCur
    to inject the fake fusion result — we're testing the plumbing, not the SQL
    (SQL is covered by test_e2e_integration).
    """
    from datetime import datetime, timezone, timedelta
    from backend.retrieval.v2 import hybrid

    now = datetime.now(timezone.utc)
    fake_rows = [
        {"key": "TS-old", "fused_score": 0.03,
         "updated_at": now - timedelta(days=800), "resolved_at": None,
         "status_category": "indeterminate", "comment_count": 0},
        {"key": "TS-recent", "fused_score": 0.03,
         "updated_at": now - timedelta(days=10), "resolved_at": None,
         "status_category": "indeterminate", "comment_count": 0},
    ]

    class FakeCur:
        def __init__(self): self._rows = None
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def execute(self, *a, **k): self._rows = list(fake_rows)
        def fetchall(self): return self._rows
    class FakeConn:
        def cursor(self, **k): return FakeCur()

    out = hybrid.hybrid_search(FakeConn(), ["q"], [[0.0]*768], {}, limit=10)
    keys = [r["key"] for r in out]
    for r in out:
        assert "bucket" in r
        assert "timeline_score" in r
    # Same fused_score, but apply_timeline must re-sort to put recent first.
    assert keys[0] == "TS-recent"


def test_base_sql_selects_comment_count():
    """comment_count must be selected — timeline.assign_bucket's substantive-
    resolution branch (resolved + comment_count>=2 -> latest) reads it, but
    was silently always None because this column was missing from the SELECT."""
    from backend.retrieval.v2.hybrid import _BASE_SQL
    assert "comment_count" in _BASE_SQL


def test_hybrid_search_passes_through_comment_count():
    """End-to-end: a fake row with comment_count reaches the returned candidate
    dict, and apply_timeline's substantive-resolution override actually fires."""
    from datetime import datetime, timezone, timedelta
    from backend.retrieval.v2 import hybrid

    now = datetime.now(timezone.utc)
    fake_rows = [
        {"key": "TS-old-but-substantive", "fused_score": 0.03,
         "updated_at": now - timedelta(days=800),
         "resolved_at": now - timedelta(days=800),
         "status_category": "done", "comment_count": 5},
    ]

    class FakeCur:
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def execute(self, *a, **k): pass
        def fetchall(self): return fake_rows
    class FakeConn:
        def cursor(self, **k): return FakeCur()

    out = hybrid.hybrid_search(FakeConn(), ["q"], [[0.0] * 768], {}, limit=5)
    assert out[0]["comment_count"] == 5
    # Substantive-resolution override: resolved + comment_count>=2 -> latest,
    # even though updated_at/resolved_at are 800 days old.
    assert out[0]["bucket"] == "latest"
