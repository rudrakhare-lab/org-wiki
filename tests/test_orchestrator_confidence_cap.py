from types import SimpleNamespace
from backend.orchestrator import _cap_confidence_by_retrieval


def _bundle(retrieval_conf):
    return SimpleNamespace(seed_jira={"confidence": retrieval_conf} if retrieval_conf else {})


def test_caps_answer_to_lower_retrieval_confidence():
    assert _cap_confidence_by_retrieval("High", _bundle("Medium")) == "Medium"


def test_does_not_raise_confidence():
    assert _cap_confidence_by_retrieval("Low", _bundle("High")) == "Low"


def test_abstain_and_missing_are_left_to_phase2():
    assert _cap_confidence_by_retrieval("High", _bundle("Abstain")) == "High"
    assert _cap_confidence_by_retrieval("High", _bundle(None)) == "High"
