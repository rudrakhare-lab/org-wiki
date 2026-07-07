"""Hybrid chunk search — SQL shape, RRF fusion, prod-realistic types."""
from decimal import Decimal
from backend.retrieval.wiki_v2 import search as ws


def test_chunk_sql_has_lex_dense_and_agent_filter():
    assert "search_tsv @@" in ws._CHUNK_SQL
    assert "embedding <=>" in ws._CHUNK_SQL
    assert "agent_id = %(agent_id)s" in ws._CHUNK_SQL
    assert "embedding IS NOT NULL" in ws._CHUNK_SQL


def test_expand_terms_appended_to_lex_query():
    q = ws._lex_query("kiosk OTP", {"OTP": ["one-time password"]})
    assert "kiosk OTP" in q and "one-time password" in q and " OR " in q


def _fake_conn(rows_per_call):
    calls = {"n": 0}
    class FakeCur:
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def execute(self, *a, **k): pass
        def fetchall(self):
            rows = rows_per_call[min(calls["n"], len(rows_per_call) - 1)]
            calls["n"] += 1
            return rows
    class FakeConn:
        def cursor(self, **k): return FakeCur()
    return FakeConn()


def _row(cid, path, score):
    # prod-realistic: Decimal fused score, ISO-string date
    return {"id": cid, "page_path": path, "section_anchor": "s",
            "section_title": "S", "page_type": "module", "chunk_index": 0,
            "chunk_text": "t", "last_updated": "2026-06-01",
            "fused_score": Decimal(str(score))}


def test_rrf_fuses_across_sub_queries_and_casts_float():
    conn = _fake_conn([
        [_row(1, "modules/a.md", 0.03), _row(2, "modules/b.md", 0.02)],
        [_row(2, "modules/b.md", 0.04), _row(3, "modules/c.md", 0.01)],
    ])
    out = ws.hybrid_chunks(conn, ["q1", "q2"], [[0.0] * 768] * 2, "conwo")
    ids = [r["id"] for r in out]
    assert ids[0] == 2                      # appears in both sub-queries → fused highest
    assert all(isinstance(r["fused_score"], float) for r in out)


def test_empty_results_return_empty_list():
    conn = _fake_conn([[]])
    assert ws.hybrid_chunks(conn, ["q"], [[0.0] * 768], "conwo") == []
