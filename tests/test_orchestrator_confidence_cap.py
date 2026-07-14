from backend.orchestrator import _cap_confidence_by_retrieval


def _result(retrieval_conf):
    return {"confidence": retrieval_conf} if retrieval_conf else {}


def test_caps_answer_to_lower_retrieval_confidence():
    assert _cap_confidence_by_retrieval("High", _result("Medium")) == "Medium"


def test_does_not_raise_confidence():
    assert _cap_confidence_by_retrieval("Low", _result("High")) == "Low"


def test_abstain_and_missing_are_left_to_phase2():
    assert _cap_confidence_by_retrieval("High", _result("Abstain")) == "High"
    assert _cap_confidence_by_retrieval("High", _result(None)) == "High"
    assert _cap_confidence_by_retrieval("High", None) == "High"


def test_cap_disabled_by_kill_switch(monkeypatch):
    monkeypatch.setenv("CONWO_CONF_CAP", "off")
    assert _cap_confidence_by_retrieval("High", {"confidence": "Low"}) == "High"
