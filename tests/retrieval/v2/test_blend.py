import os
from backend.retrieval.v2.blend import blend_scores, enabled, weights


def _cand(key, fused, timeline):
    return {"key": key, "fused_score": fused, "timeline_score": timeline}


def test_blend_lets_recency_and_fusion_reorder_equal_rerank(monkeypatch):
    monkeypatch.delenv("CONWO_RANK_BLEND", raising=False)
    # Two candidates with identical rerank prob; B is far more recent + higher fusion.
    a = _cand("A", fused=0.01, timeline=0.10)
    b = _cand("B", fused=0.05, timeline=0.95)
    out = blend_scores([(a, 0.6), (b, 0.6)])
    assert [c["key"] for c, _ in out] == ["B", "A"]      # recency+fusion breaks the tie
    assert all("blend_score" in c and "reranker_score" in c for c, _ in out)


def test_blend_scores_stay_in_unit_range(monkeypatch):
    monkeypatch.delenv("CONWO_RANK_BLEND", raising=False)
    out = blend_scores([(_cand("A", 0.05, 1.0), 1.0), (_cand("B", 0.0, 0.05), 0.0)])
    for _, s in out:
        assert 0.0 <= s <= 1.0


def test_missing_fields_default_zero_no_crash(monkeypatch):
    monkeypatch.delenv("CONWO_RANK_BLEND", raising=False)
    out = blend_scores([({"key": "A"}, 0.7)])           # no fused_score / timeline_score
    assert out[0][0]["reranker_score"] == 0.7


def test_disabled_is_identity_order(monkeypatch):
    monkeypatch.setenv("CONWO_RANK_BLEND", "off")
    a = _cand("A", fused=0.9, timeline=0.9)             # would win under blend
    b = _cand("B", fused=0.0, timeline=0.0)
    out = blend_scores([(b, 0.9), (a, 0.1)])            # but B has higher rerank
    assert [c["key"] for c, _ in out] == ["B", "A"]
    assert out[0][0]["blend_score"] == 0.9              # identity: blend == rerank


def test_weights_env_override(monkeypatch):
    monkeypatch.setenv("CONWO_RANK_W_RERANK", "1.0")
    monkeypatch.setenv("CONWO_RANK_W_TIMELINE", "0.0")
    monkeypatch.setenv("CONWO_RANK_W_FUSED", "0.0")
    assert weights() == (1.0, 0.0, 0.0)
