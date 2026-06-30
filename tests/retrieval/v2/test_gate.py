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
