from backend import agent_provisioning as ap


def test_slugify():
    assert ap.slugify("Legal") == "legal"
    assert ap.slugify("HR Policies & Ops") == "hr-policies-ops"


def test_accent_is_deterministic_hex():
    a1 = ap.accent_for_slug("legal")
    a2 = ap.accent_for_slug("legal")
    assert a1 == a2 and a1.startswith("#") and len(a1) == 7
    assert ap.accent_for_slug("finance") != a1   # different slug → different hue


def test_identity_fallback_when_no_llm(monkeypatch):
    # Force the LLM path to fail → deterministic template fallback.
    monkeypatch.setattr(ap, "_llm_identity", lambda name: None)
    out = ap.generate_identity("Legal")
    assert "Legal" in out and "knowledge base" in out.lower()
