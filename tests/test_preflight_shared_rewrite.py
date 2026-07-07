"""Shared rewrite — computed once in preflight, consumed by both pillars."""
from backend.retrieval.v2.rewrite import RewriteResult


def test_pipeline_search_uses_passed_rewrite(monkeypatch):
    from backend.retrieval.v2 import pipeline
    calls = []
    monkeypatch.setattr(pipeline, "rewrite",
                        lambda q: calls.append(q) or RewriteResult([q]))
    monkeypatch.setattr(pipeline, "embed_query", lambda q: [0.0] * 768)
    monkeypatch.setattr(pipeline, "hybrid_search", lambda *a, **k: [])
    monkeypatch.setattr(pipeline, "gate_apply", lambda s: s)

    class C:
        def __enter__(self): return self
        def __exit__(self, *a): pass
    monkeypatch.setattr(pipeline, "connection", lambda: C())

    rr = RewriteResult(sub_queries=["pre-computed"])
    pipeline.search("q", rewrite_result=rr)
    assert calls == []          # rewrite() NOT called — passed result used

    pipeline.search("q")        # back-compat: no result passed
    assert calls == ["q"]


def test_preflight_computes_rewrite_once(monkeypatch):
    from backend import preflight
    calls = []
    monkeypatch.setattr(preflight, "rewrite",
                        lambda q: calls.append(q) or RewriteResult([q]))
    # run_preflight is heavy; assert via the seam the bundle setter uses:
    rr = preflight._compute_rewrite("question text")
    assert calls == ["question text"] and rr.sub_queries == ["question text"]
