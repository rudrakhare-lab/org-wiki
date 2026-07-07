"""Inline no-source-no-fact — mechanical set-membership, gates before ship."""
from backend.citation_check import verify_citations


def test_cited_and_retrieved_is_ok():
    r = verify_citations(
        "Per `modules/desk-management.md#overview` and TS-1234 …",
        wiki_anchors={"modules/desk-management.md#overview"},
        jira_keys={"TS-1234"})
    assert set(r.cited_ok) == {"modules/desk-management.md#overview", "TS-1234"}
    assert r.cited_unverified == [] and r.confidence_capped is False


def test_cited_but_never_retrieved_is_flagged():
    r = verify_citations("As documented in `modules/ghost.md` and PB-9999.",
                         wiki_anchors=set(), jira_keys={"TS-1"})
    assert "modules/ghost.md" in r.cited_unverified
    assert "PB-9999" in r.cited_unverified
    assert r.confidence_capped is True


def test_page_level_citation_matches_section_anchor_evidence():
    r = verify_citations("See `modules/a.md`.",
                         wiki_anchors={"modules/a.md#overview"}, jira_keys=set())
    assert r.cited_unverified == []   # page-level cite covered by section evidence


def test_extract_confidence_unknown_not_medium():
    from backend.orchestrator import _extract_confidence
    assert _extract_confidence("no confidence line here") == "Unknown"


# ── Orchestrator inline gate + honest sources (spec §5.9) ────────────────────

from types import SimpleNamespace


def _fake_bundle(anchors=(), jira_latest=(), config_evidence=""):
    chunks = [SimpleNamespace(anchor=a) for a in anchors]
    return SimpleNamespace(
        seed_wiki_chunks=chunks, seed_wiki=[], config_evidence=config_evidence,
        seed_jira={"buckets": {"LATEST": [{"key": k} for k in jira_latest]}})


def test_verify_and_gate_caps_high_when_citation_unretrieved():
    from backend.orchestrator import _verify_and_gate
    bundle = _fake_bundle(anchors=["modules/desk-management.md#overview"])
    answer = "Per `modules/ghost.md` this is fixed. Confidence: High"
    new_answer, conf, report = _verify_and_gate(answer, "High", bundle, [])
    assert conf == "Medium"                       # capped
    assert "⚠️ Unverified citations" in new_answer
    assert "modules/ghost.md" in report.cited_unverified


def test_verify_and_gate_keeps_high_when_all_cited_retrieved():
    from backend.orchestrator import _verify_and_gate
    bundle = _fake_bundle(anchors=["modules/desk-management.md#overview"],
                          jira_latest=["TS-1234"])
    answer = "See `modules/desk-management.md#overview` and TS-1234. Confidence: High"
    new_answer, conf, report = _verify_and_gate(answer, "High", bundle, [])
    assert conf == "High" and "⚠️" not in new_answer
    assert report.cited_unverified == []


def test_verify_and_gate_accepts_config_page_from_config_evidence():
    """A CONFIGURATION answer citing a configs/<slug>.md page that B4 surfaced
    in config_evidence must be verified — not spuriously capped (cross-task
    B4×B6 integration, final-review Important)."""
    from backend.orchestrator import _verify_and_gate
    bundle = _fake_bundle(
        config_evidence="- `roomBookingBuffer` — type ... → `configs/meeting-rooms.md`")
    answer = "See `configs/meeting-rooms.md` for the buffer setting. Confidence: High"
    new_answer, conf, report = _verify_and_gate(answer, "High", bundle, [])
    assert conf == "High" and "⚠️" not in new_answer
    assert "configs/meeting-rooms.md" not in report.cited_unverified


def test_verify_and_gate_counts_tool_fetched_evidence():
    from backend.orchestrator import _verify_and_gate
    bundle = _fake_bundle()
    trace = [{"tool_name": "jira_get_ticket", "input": {"key": "PB-77"}},
             {"tool_name": "wiki_read_page", "input": {"path": "wiki/modules/sso.md"}}]
    answer = "Fixed in PB-77, see `modules/sso.md`. Confidence: High"
    _, conf, report = _verify_and_gate(answer, "High", bundle, trace)
    assert conf == "High" and report.cited_unverified == []


def test_honest_sources_splits_cited_ok():
    from backend.orchestrator import _honest_sources
    from backend.citation_check import CitationReport
    rep = CitationReport(cited_ok=["modules/a.md#x", "TS-99", "PB-10"])
    src = _honest_sources(rep, "no configs here")
    assert src.wiki_pages == ["modules/a.md#x"]
    assert set(src.jira_keys) == {"TS-99", "PB-10"}


def test_extract_pms_configs_rejects_lowercase_words():
    from backend.orchestrator import _extract_pms_configs
    out = _extract_pms_configs(
        "the `description` and `conversation` fields vs `roomBookingBuffer` "
        "and `VISITOR:kioskRequireOTP`")
    assert "roomBookingBuffer" in out
    assert "VISITOR:kioskRequireOTP" in out
    assert "description" not in out and "conversation" not in out


def test_honest_sources_pms_grounded_in_config_evidence():
    """A camelCase token in the answer is a PMS source ONLY if it was actually
    surfaced in the preflight config_evidence block — a hallucinated but
    well-formed token is not promoted (spec §5.9 honesty guarantee)."""
    from backend.orchestrator import _honest_sources
    from backend.citation_check import CitationReport
    rep = CitationReport(cited_ok=[])
    answer = "Set `roomBookingBuffer` and also `fakeConfigName` to fix this."
    config_evidence = "## Config properties detected\n- `roomBookingBuffer` — ..."
    src = _honest_sources(rep, answer, config_evidence)
    assert src.pms_configs == ["roomBookingBuffer"]        # grounded, kept
    assert "fakeConfigName" not in src.pms_configs          # never retrieved, dropped


def test_honest_sources_no_pms_when_no_config_evidence():
    from backend.orchestrator import _honest_sources
    from backend.citation_check import CitationReport
    src = _honest_sources(CitationReport(cited_ok=[]),
                          "mentions `roomBookingBuffer`", config_evidence="")
    assert src.pms_configs == []   # nothing retrieved from the config KB


def test_honest_sources_pms_no_camelcase_prefix_false_positive():
    """A shorter camelCase token that is only a PREFIX of a retrieved config
    must not be spuriously grounded (backtick-delimited match)."""
    from backend.orchestrator import _honest_sources
    from backend.citation_check import CitationReport
    # answer cites `roomBooking`; config_evidence only has `roomBookingBuffer`
    src = _honest_sources(CitationReport(cited_ok=[]),
                          "check `roomBooking` behavior",
                          config_evidence="- `roomBookingBuffer` — desc")
    assert src.pms_configs == []   # prefix ≠ grounded
