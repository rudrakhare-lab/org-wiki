"""Tests for backend.orchestrator helpers.

Focused unit tests for _inject_answer_id (G06 feedback-prompt closure).
Full run_deep is integration-tested via the eval set; this file covers the
substitution + fallback logic directly so we don't need to mock the LLM.
"""
from __future__ import annotations

import re

from backend.orchestrator import _inject_answer_id


def test_inject_substitutes_placeholder():
    """Happy path: model emits the placeholder, we swap in the real id."""
    raw = (
        "**Answer:** Foo.\n\n"
        "**Sources:** —\n\n"
        "---\n"
        "**Review this answer:** Score 1–5.\n"
        "**Answer ID:** `<ANSWER_ID>`\n"
        "If score ≤3, tell me what was wrong."
    )
    out = _inject_answer_id(raw, "abc123def456")
    assert "<ANSWER_ID>" not in out
    assert "**Answer ID:** `abc123def456`" in out
    # No duplicate synthetic block tacked on
    assert out.count("**Answer ID:**") == 1


def test_inject_appends_synthetic_block_when_model_omits_both():
    """Fallback: model dropped the placeholder AND the literal marker.

    The synthetic block must match the happy-path 3-line template exactly so
    the user-facing UX is identical regardless of whether the model followed
    the template.
    """
    raw = "**Answer:** Foo.\n\n**Sources:** —"
    out = _inject_answer_id(raw, "abc123def456")
    # All three lines of the unified template must be present
    assert "**Review this answer:** Score 1–5 (5 = fully correct)." in out
    assert "**Answer ID:** `abc123def456`" in out
    assert "If score ≤3, tell me what was wrong or what the answer should have said." in out
    # Block is separated by `---` like the happy path
    assert "---\n**Review this answer:**" in out
    # Original answer preserved
    assert out.startswith("**Answer:** Foo.")
    # No duplicate markers
    assert out.count("**Answer ID:**") == 1


def test_inject_no_double_block_when_model_emitted_marker_without_placeholder():
    """If the model emitted **Answer ID:** literally (with a wrong id or no
    placeholder), don't tack on a second synthetic block."""
    raw = (
        "**Answer:** Foo.\n\n"
        "---\n"
        "**Answer ID:** `model-made-this-up`\n"
    )
    out = _inject_answer_id(raw, "abc123def456")
    # No synthetic addition
    assert out.count("**Answer ID:**") == 1
    # The real id is NOT injected because there was no placeholder to find —
    # this is a deliberate design choice (don't second-guess the model's literal output).
    assert "abc123def456" not in out


def test_inject_replaces_all_placeholders():
    """If the model accidentally emits the placeholder twice, replace both."""
    raw = "Refer to <ANSWER_ID> later. **Answer ID:** `<ANSWER_ID>`"
    out = _inject_answer_id(raw, "abc123def456")
    assert "<ANSWER_ID>" not in out
    assert out.count("abc123def456") == 2


def test_inject_preserves_realistic_id_format():
    """The real answer_id is a 12-char sha1 prefix (lowercase hex). Verify
    the rendered output contains exactly that format."""
    raw = "**Answer ID:** `<ANSWER_ID>`"
    out = _inject_answer_id(raw, "a1b2c3d4e5f6")
    # 12 hex chars, backtick-wrapped after the marker
    assert re.search(r"\*\*Answer ID:\*\*\s*`[a-f0-9]{12}`", out)


# ── G29 integration test: run_single_shot wires the same substitution ─────────

def test_run_single_shot_substitutes_answer_id_in_returned_text(monkeypatch, tmp_path):
    """End-to-end check that the claude-code path (run_single_shot) applies
    the same prepare_answer_id → _inject_answer_id → log_answer sequence as
    run_deep (G06 + G29).

    Mocks every external dependency (provider, retrievers, log_answer) so
    we don't hit network, SQLite, or the real wiki. Asserts the final
    answer_text contains a 12-hex-char Answer ID in place of the placeholder.
    """
    from unittest.mock import MagicMock, patch
    from backend import orchestrator

    # Mock wiki and Jira retrieval to return empty results
    monkeypatch.setattr(orchestrator.wiki_retriever, "search", lambda *a, **kw: [])
    monkeypatch.setattr(
        orchestrator.jira_retriever,
        "search",
        lambda *a, **kw: {
            "markdown": "(no results)",
            "rows": [],
            "buckets": {"LATEST": [], "HISTORICAL": []},
            "keywords": [],
        },
    )

    # Mock the provider so we can inject a fake raw_answer
    mock_provider = MagicMock()
    mock_provider.generate.return_value = MagicMock(
        ok=True,
        raw_answer=(
            "**Answer:** Test.\n\n"
            "**Confidence:** Medium\n\n"
            "**Sources:** —\n\n"
            "---\n"
            "**Answer ID:** `<ANSWER_ID>`\n"
        ),
        error="",
    )
    monkeypatch.setattr(orchestrator, "_select_provider", lambda mode, key: mock_provider)

    # Mock log_answer to avoid touching the real JSONL — returns a stable id
    fake_id = "abc123def456"
    with patch.object(orchestrator, "log_answer", return_value=fake_id) as mock_log:
        with patch.object(
            orchestrator,
            "prepare_answer_id",
            return_value=(fake_id, "2026-05-22T12:00:00Z"),
        ):
            result = orchestrator.run_single_shot(
                question="Test question",
                mode="api",
                claude_api_key="fake-key",
            )

    # The returned answer_text must have the placeholder replaced by the real id
    assert "<ANSWER_ID>" not in result.answer_text
    assert f"**Answer ID:** `{fake_id}`" in result.answer_text
    assert result.answer_id == fake_id
    # log_answer was called with the substituted text + pre-computed id
    call_kwargs = mock_log.call_args.kwargs
    assert call_kwargs["answer_id"] == fake_id
    assert f"`{fake_id}`" in call_kwargs["answer_text"]
    assert "<ANSWER_ID>" not in call_kwargs["answer_text"]
