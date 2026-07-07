"""Config evidence — detection, dependency chain, cycle safety."""
from backend import config_evidence as ce


def test_detects_backticked_and_camelcase_names():
    known = {"roomBookingBuffer", "enableRoomBooking", "kioskRequireOTP"}
    q = "why is `roomBookingBuffer` ignored when enableRoomBooking is on?"
    assert set(ce.detect_config_properties(q, known)) == {
        "roomBookingBuffer", "enableRoomBooking"}


def test_detection_ignores_unknown_tokens():
    assert ce.detect_config_properties("some camelCase word", {"realProp"}) == []


def test_dependency_chain_two_levels_cycle_safe(monkeypatch):
    rows = {
        "a": {"property": "a", "description": "A", "service": "VISITOR",
              "dependent_configs": ["b"]},
        "b": {"property": "b", "description": "B", "service": "VISITOR",
              "dependent_configs": ["a"]},  # cycle
    }
    monkeypatch.setattr(ce, "lookup_property", lambda n: rows.get(n))
    monkeypatch.setattr(ce, "_known_names", lambda: set(rows))
    block = ce.build_config_evidence("what is `a`?", max_depth=2)
    assert "`a`" in block and "`b`" in block
    assert block.count("`a`") >= 1            # no infinite loop
    assert "configs/" in block                 # anchored


def test_no_detection_returns_empty(monkeypatch):
    monkeypatch.setattr(ce, "_known_names", lambda: {"x"})
    assert ce.build_config_evidence("how do I book a desk?") == ""
