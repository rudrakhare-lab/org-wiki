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
