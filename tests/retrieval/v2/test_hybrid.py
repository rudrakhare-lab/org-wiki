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


def test_build_base_sql_omits_dense_c_when_flag_off():
    from backend.retrieval.v2.hybrid import _build_base_sql
    sql = _build_base_sql(comments_enabled=False)
    assert "dense_c" not in sql
    assert "comments_embedding" not in sql


def test_build_base_sql_flag_off_is_byte_identical_to_base_sql():
    """Zero-risk guarantee: when the flag is off, the emitted SQL (after filter
    interpolation) must be byte-identical to today's prod SQL. This is the
    strictest constraint in the plan — prod runs with the flag off today."""
    from backend.retrieval.v2.hybrid import _build_base_sql, _BASE_SQL
    off_sql = _build_base_sql(comments_enabled=False).format(
        filter_sql_lex="", filter_sql_dense="",
    )
    prod_sql = _BASE_SQL.format(filter_sql_lex="", filter_sql_dense="")
    assert off_sql == prod_sql


def test_build_base_sql_includes_dense_c_when_flag_on():
    from backend.retrieval.v2.hybrid import _build_base_sql
    sql = _build_base_sql(comments_enabled=True)
    assert "dense_c AS" in sql
    assert "comments_embedding IS NOT NULL" in sql
    # The UNION ALL block must include the dense_c source.
    assert "SELECT key, dense_c_rnk" in sql or "SELECT key, rnk FROM dense_c" in sql


def test_hybrid_search_reads_env_flag(monkeypatch):
    """hybrid_search picks up CONWO_RETRIEVAL_V2_COMMENTS at call time."""
    from backend.retrieval.v2 import hybrid
    captured_sql = []

    class FakeCur:
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def execute(self, sql, params): captured_sql.append(sql)
        def fetchall(self): return []
    class FakeConn:
        def cursor(self, **k): return FakeCur()

    monkeypatch.setenv("CONWO_RETRIEVAL_V2_COMMENTS", "on")
    hybrid.hybrid_search(FakeConn(), ["q"], [[0.0]*768], {}, limit=5)
    assert any("dense_c" in s for s in captured_sql)

    captured_sql.clear()
    monkeypatch.setenv("CONWO_RETRIEVAL_V2_COMMENTS", "off")
    hybrid.hybrid_search(FakeConn(), ["q"], [[0.0]*768], {}, limit=5)
    assert not any("dense_c" in s for s in captured_sql)


def test_hybrid_search_with_comments_flag_on_handles_prod_realistic_row_types(monkeypatch):
    """Prod-realistic fixture (plan Revision 2 mandate): ISO-string dates,
    decimal.Decimal fused_score (what SUM(1.0/(k+rnk)) actually returns from
    Postgres), and comment_count present. Exercised with the dense_c CTE
    enabled to confirm the third RRF source doesn't introduce any new
    SQL-boundary type assumptions on the Python side."""
    from decimal import Decimal
    from backend.retrieval.v2 import hybrid

    fake_rows = [
        {"key": "TS-1", "fused_score": Decimal("0.0421"),
         "updated_at": "2026-06-20T10:00:00+00:00",
         "resolved_at": "2026-06-21T10:00:00+00:00",
         "status_category": "done", "comment_count": 3},
    ]

    class FakeCur:
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def execute(self, *a, **k): pass
        def fetchall(self): return fake_rows
    class FakeConn:
        def cursor(self, **k): return FakeCur()

    monkeypatch.setenv("CONWO_RETRIEVAL_V2_COMMENTS", "on")
    # Must not raise on Decimal fused_score + ISO-string dates + comment_count present.
    out = hybrid.hybrid_search(FakeConn(), ["q"], [[0.0] * 768], {}, limit=5)
    assert out[0]["key"] == "TS-1"
    assert out[0]["comment_count"] == 3
    # bucket/timeline_score attached proves apply_timeline consumed the Decimal
    # fused_score + string dates without crashing (the real prod-boundary risk).
    assert "bucket" in out[0] and "timeline_score" in out[0]


def test_hybrid_search_casts_fused_score_to_float():
    """Regression: the dict literal used to spread **r AFTER the explicit
    float() cast, so the raw decimal.Decimal from Postgres (numeric SUM in
    the fused CTE) silently overwrote the cast. Latent-safe only because
    timeline.py re-casts in its sort key — any future consumer doing direct
    arithmetic would hit the PR #43 outage class again."""
    from decimal import Decimal
    from backend.retrieval.v2 import hybrid

    fake_rows = [
        {"key": "TS-1", "fused_score": Decimal("0.0163"),
         "summary": "s", "status_category": "done", "priority": "P2",
         "updated_at": "2026-06-01T00:00:00+00:00", "resolved_at": None,
         "comment_count": 0},
    ]

    class FakeCur:
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def execute(self, *a, **k): pass
        def fetchall(self): return fake_rows
    class FakeConn:
        def cursor(self, **k): return FakeCur()

    out = hybrid.hybrid_search(FakeConn(), ["q"], [[0.0] * 768], {}, limit=5)
    assert isinstance(out[0]["fused_score"], float)


def test_comments_flag_defaults_on(monkeypatch):
    """CONWO_RETRIEVAL_V2_COMMENTS defaults ON in code (deliberate: avoids a
    devops env change at deploy). The env var remains as a kill switch."""
    monkeypatch.delenv("CONWO_RETRIEVAL_V2_COMMENTS", raising=False)
    from backend.retrieval.v2 import hybrid

    captured = {}

    class FakeCur:
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def execute(self, sql, params=None): captured["sql"] = sql
        def fetchall(self): return []
    class FakeConn:
        def cursor(self, **k): return FakeCur()

    hybrid.hybrid_search(FakeConn(), ["q"], [[0.0] * 768], {}, limit=5)
    assert "dense_c" in captured["sql"]
