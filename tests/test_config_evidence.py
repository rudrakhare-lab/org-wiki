"""Config evidence — detection, dependency chain, cycle safety, real anchors."""
from pathlib import Path

import pytest

from backend import config_evidence as ce

_WIKI_CONFIGS = Path(__file__).resolve().parents[1] / "wiki" / "configs"


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


@pytest.mark.parametrize(
    "service,slug", sorted(ce._SERVICE_TO_CONFIG_SLUG.items()))
def test_service_anchor_targets_real_config_page(service, slug):
    """Pin the service→slug table to reality: every anchor generated for a
    real catalog service must point at a file that exists in wiki/configs/.
    Fails loudly if a config page is renamed or removed."""
    anchor = ce._config_anchor(service)
    assert anchor == f"configs/{slug}.md"
    assert (_WIKI_CONFIGS / f"{slug}.md").is_file(), (
        f"anchor {anchor} for service {service} points at a missing wiki page")


def test_anchor_unknown_service_falls_back_to_naive_transform():
    assert ce._config_anchor("FUTURE_NEW_SERVICE") == "configs/future-new-service.md"
    assert ce._config_anchor("") == "configs/"
