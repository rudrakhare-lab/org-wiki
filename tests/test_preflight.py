"""Tests for backend.preflight.build_seed_message — specifically the G03
summary-plumbing change. Operational-context block coverage stays in
tests/test_operational_context.py.
"""
from __future__ import annotations

from backend.preflight import PreflightBundle, build_seed_message


def _empty_bundle() -> PreflightBundle:
    """A bundle with no seed evidence — keeps the rendered message short."""
    return PreflightBundle()


def test_build_seed_message_with_summary_prepends_block():
    summary = (
        "- User scoped query to .com server, BUID genpactindia-GInd.\n"
        "- OTP issue narrowed to office-level overrides.\n"
        "- Referenced TS-12345 and kioskRequireOTPBeforeRegister.\n"
        "- Default value is false at BUID level.\n"
        "- Open question: which OFFICEIDs have the override."
    )
    out = build_seed_message(
        question="What now?",
        scope_line=".com server | BUID: genpactindia-GInd",
        bundle=_empty_bundle(),
        summary=summary,
    )
    # The block heading must be present
    assert "**Prior conversation summary** (older turns compacted):" in out
    # All five bullets must be present
    for bullet in (
        "User scoped query",
        "OTP issue narrowed",
        "TS-12345",
        "Default value is false",
        "which OFFICEIDs have the override",
    ):
        assert bullet in out
    # Summary appears AFTER Question/Scope and BEFORE the pre-fetched evidence
    summary_pos = out.find("**Prior conversation summary**")
    question_pos = out.find("**Question:**")
    evidence_pos = out.find("## Pre-fetched wiki evidence")
    assert 0 < question_pos < summary_pos < evidence_pos


def test_build_seed_message_without_summary_omits_block():
    out = build_seed_message(
        question="What now?",
        scope_line=".com server",
        bundle=_empty_bundle(),
        summary="",
    )
    assert "**Prior conversation summary**" not in out


def test_build_seed_message_whitespace_only_summary_omits_block():
    """A summary that's just whitespace should be treated as no summary."""
    out = build_seed_message(
        question="What?",
        scope_line=".com",
        bundle=_empty_bundle(),
        summary="   \n\t  ",
    )
    assert "**Prior conversation summary**" not in out
