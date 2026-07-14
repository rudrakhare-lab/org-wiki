def _scored(*pairs):
    return [({"key": k, "summary": "s", "functional_area": fa}, score)
            for k, fa, score in pairs]

def test_abstain_when_top_below_threshold():
    from backend.retrieval.v2 import gate
    r = gate.apply(_scored(("TS-1","A",0.3), ("TS-2","A",0.2)))
    assert r.abstain is True
    assert r.confidence == "Abstain"
    assert "couldn't find" in r.message.lower()

def test_high_when_top_score_strong_and_top3_agree():
    from backend.retrieval.v2 import gate
    r = gate.apply(_scored(("TS-1","A",0.9),("TS-2","A",0.85),("TS-3","A",0.8)))
    assert r.confidence == "High"
    assert r.abstain is False

def test_medium_when_top_strong_but_top3_disagree():
    from backend.retrieval.v2 import gate
    r = gate.apply(_scored(("TS-1","A",0.9),("TS-2","B",0.85),("TS-3","C",0.8)))
    assert r.confidence == "Medium"
    assert r.abstain is False

def test_low_when_single_source_above_abstain():
    from backend.retrieval.v2 import gate
    r = gate.apply(_scored(("TS-1","A",0.6)))
    assert r.confidence == "Low"
    assert r.abstain is False
    assert "single-source" in r.message.lower()

def test_diagnostics_includes_top_score_and_count():
    from backend.retrieval.v2 import gate
    r = gate.apply(_scored(("TS-1","A",0.9),("TS-2","A",0.85)))
    assert r.diagnostics["top_score"] == 0.9
    assert r.diagnostics["candidate_count"] == 2


def _scored_with_buckets(*items):
    """items: (key, functional_area, bucket, score)"""
    return [({"key": k, "summary": "s", "functional_area": fa, "bucket": b}, s)
            for k, fa, b, s in items]


def test_gate_downgrades_high_to_medium_when_top3_all_historical():
    from backend.retrieval.v2 import gate
    r = gate.apply(_scored_with_buckets(
        ("TS-1", "A", "historical", 0.9),
        ("TS-2", "A", "historical", 0.85),
        ("TS-3", "A", "historical", 0.8),
    ))
    assert r.confidence == "Medium"
    assert "historical" in r.message.lower()


def test_gate_downgrades_medium_to_low_when_top3_all_historical():
    from backend.retrieval.v2 import gate
    r = gate.apply(_scored_with_buckets(
        ("TS-1", "A", "historical", 0.65),
        ("TS-2", "A", "historical", 0.60),
        ("TS-3", "A", "historical", 0.55),
    ))
    assert r.confidence == "Low"


def test_gate_downgrades_high_to_low_when_top3_all_stale_open():
    from backend.retrieval.v2 import gate
    r = gate.apply(_scored_with_buckets(
        ("TS-1", "A", "stale_open", 0.9),
        ("TS-2", "A", "stale_open", 0.85),
        ("TS-3", "A", "stale_open", 0.8),
    ))
    assert r.confidence == "Low"
    assert "stale" in r.message.lower()


def test_gate_no_downgrade_when_top3_mixed_buckets():
    from backend.retrieval.v2 import gate
    r = gate.apply(_scored_with_buckets(
        ("TS-1", "A", "latest",     0.9),
        ("TS-2", "A", "historical", 0.85),
        ("TS-3", "A", "latest",     0.8),
    ))
    assert r.confidence == "High"


def test_gate_diagnostics_includes_bucket_counts():
    from backend.retrieval.v2 import gate
    r = gate.apply(_scored_with_buckets(
        ("TS-1", "A", "latest",     0.9),
        ("TS-2", "A", "historical", 0.85),
        ("TS-3", "A", "latest",     0.8),
    ))
    assert r.diagnostics["bucket_counts"] == {"latest": 2, "historical": 1, "stale_open": 0}


from backend.retrieval.v2.gate import apply


def _c(key, fa=None, bucket="latest"):
    return {"key": key, "functional_area": fa, "bucket": bucket}


def test_abstain_uses_reranker_not_blend():
    # Top candidate is semantically weak (reranker 0.30 < 0.5 abstain) but its
    # blend was boosted to 0.72 by recency+fusion. Must STILL abstain — recency
    # cannot rescue an irrelevant ticket past the semantic floor.
    weak = {**_c("A"), "reranker_score": 0.30}
    scored = [(weak, 0.72)]
    r = apply(scored)
    assert r.abstain is True


def test_confidence_tier_uses_blend_score():
    # Reranker 0.55 (would be Medium band alone) but blend 0.80 >= HIGH; with
    # agreeing top-3 → High.
    top3 = [
        ({**_c("A", fa="WF-empexp"), "reranker_score": 0.55}, 0.80),
        ({**_c("B", fa="WF-empexp"), "reranker_score": 0.52}, 0.75),
        ({**_c("C", fa="WF-empexp"), "reranker_score": 0.50}, 0.72),
    ]
    r = apply(top3)
    assert r.abstain is False and r.confidence == "High"


def test_gate_preserves_true_reranker_score_and_adds_rank_score():
    c = {**_c("A"), "reranker_score": 0.61}
    r = apply([(c, 0.80)])
    t = r.tickets[0]
    assert t["reranker_score"] == 0.61     # true reranker preserved, not clobbered by blend
    assert t["rank_score"] == 0.80          # blend value exposed for downstream/debug


def test_no_abstain_when_a_lower_slot_candidate_clears_floor():
    # Blend-sorted: a marginal-but-recent ticket at slot 0 (reranker 0.45 < abstain),
    # a strong-but-old ticket displaced to slot 1 (reranker 0.90). Must NOT abstain —
    # the semantic floor is cleared by SOME candidate.
    marginal = {**_c("W", fa="WF-empexp"), "reranker_score": 0.45}
    strong   = {**_c("S", fa="WF-empexp"), "reranker_score": 0.90}
    r = apply([(marginal, 0.725), (strong, 0.54)])   # already blend-sorted
    assert r.abstain is False
    assert {t["key"] for t in r.tickets} == {"W", "S"}
