from unittest.mock import patch, MagicMock
from backend.retrieval.v2.rewrite import RewriteResult
from backend.retrieval.v2.gate import RetrievalResult


def test_pipeline_calls_rewrite_embed_hybrid_links_rerank_gate_in_order(monkeypatch):
    from backend.retrieval.v2 import pipeline
    order: list[str] = []
    monkeypatch.setattr(pipeline, "rewrite",
        lambda q: order.append("rewrite") or RewriteResult(sub_queries=["q1"]))
    monkeypatch.setattr(pipeline, "embed_query",
        lambda q: order.append("embed") or [0.0]*768)
    monkeypatch.setattr(pipeline, "hybrid_search",
        lambda *a, **k: order.append("hybrid") or [{"key":"TS-1","summary":"x",
            "description_text":"","comments_text":"","status_category":"done",
            "priority":"P1","updated_at":"2026-01-01","resolved_at":None,
            "functional_area":"A","links_json":"[]","fused_score":1.0}])
    monkeypatch.setattr(pipeline, "expand_links",
        lambda c, cands: order.append("expand") or cands)
    monkeypatch.setattr(pipeline, "rerank_score",
        lambda q, cands: order.append("rerank") or [(cands[0], 0.9)])
    monkeypatch.setattr(pipeline, "gate_apply",
        lambda scored: order.append("gate") or RetrievalResult(
            tickets=[{"key":"TS-1","reranker_score":0.9}],
            confidence="High", abstain=False,
            message="ok", diagnostics={"top_score":0.9,"candidate_count":1}))
    monkeypatch.setattr(pipeline, "get_conn", lambda: MagicMock())
    r = pipeline.search("what is X?")
    assert r.confidence == "High"
    assert order == ["rewrite","embed","hybrid","expand","rerank","gate"]
