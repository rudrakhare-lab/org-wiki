"""Tests for backend.conversation_compactor (G03).

Real-shape mocked tests — the mocked Anthropic response uses a realistic
5-bullet summary (not a placeholder) so the test exercises the same parsing
path the production code will hit. The no-API-key fallback is tested
explicitly as the most important failure mode.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import backend.conversation_compactor as cc


# ── should_refresh ─────────────────────────────────────────────────────────────

def test_should_refresh_no_messages():
    assert cc.should_refresh(0, None) is False


def test_should_refresh_under_recent_window():
    # 8 messages all fit in the 12-message recent window → nothing to summarize
    assert cc.should_refresh(8, None) is False


def test_should_refresh_first_time_over_window():
    # 14 messages, no prior compaction → refresh
    assert cc.should_refresh(14, None) is True


def test_should_refresh_within_threshold_after_compaction():
    # Compacted at 14, now at 18 — only 4 new messages, threshold is 6
    assert cc.should_refresh(18, 14) is False


def test_should_refresh_after_threshold_crossed():
    # Compacted at 14, now at 20 — 6 new messages, threshold met
    assert cc.should_refresh(20, 14) is True


# ── messages_to_summarize ──────────────────────────────────────────────────────

def test_messages_to_summarize_returns_old_slice():
    msgs = [{"role": "user", "content": f"m{i}"} for i in range(20)]
    old = cc.messages_to_summarize(msgs)
    assert len(old) == 8  # 20 - 12 recent
    assert old[0]["content"] == "m0"
    assert old[-1]["content"] == "m7"


def test_messages_to_summarize_empty_when_under_window():
    msgs = [{"role": "user", "content": f"m{i}"} for i in range(8)]
    assert cc.messages_to_summarize(msgs) == []


# ── summarize_old_turns ────────────────────────────────────────────────────────

# Realistic 5-bullet summary shape (NOT a placeholder) — what the actual model
# would emit per the production system prompt.
_REAL_SHAPE_SUMMARY = """- User is investigating visitor-management OTP behavior on .com server, BUID genpactindia-GInd.
- Issue is scoped to specific offices, not all under the BUID — office-level overrides suspected.
- User confirmed OTP is configured at default=false; effective value matches default at BUID level.
- Referenced ticket TS-12345 (office-specific override fix) and config kioskRequireOTPBeforeRegister.
- Open question: which OFFICEIDs have the override and what value is set there."""


def _mock_anthropic_response(text: str) -> MagicMock:
    """Build a mock that mimics Anthropic SDK's Message.content shape."""
    block = MagicMock()
    block.text = text
    resp = MagicMock()
    resp.content = [block]
    return resp


def test_summarize_old_turns_calls_anthropic_with_correct_args(monkeypatch):
    """Verify the production path: API key from resolve_api_key, claude-haiku-4-5
    model, system prompt, max_tokens=300, returns the real-shape summary text."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-test")
    mock_client = MagicMock()
    mock_client.messages.create.return_value = _mock_anthropic_response(_REAL_SHAPE_SUMMARY)

    with patch("anthropic.Anthropic", return_value=mock_client) as mock_ctor:
        result = cc.summarize_old_turns([
            {"role": "user", "content": "Initial question about OTP behavior on .com"},
            {"role": "assistant", "content": "Need server confirmation. Which server?"},
            {"role": "user", "content": "It's .com, BUID genpactindia-GInd."},
            {"role": "assistant", "content": "Default is false at BUID level."},
        ])

    # Returns the real-shape summary, stripped
    assert result == _REAL_SHAPE_SUMMARY.strip()
    assert "genpactindia-GInd" in result
    assert result.count("\n- ") == 4  # 5 bullets, 4 newline-separated

    # Verify constructor call args — api_key set, timeout=30 (G33)
    ctor_kwargs = mock_ctor.call_args.kwargs
    assert ctor_kwargs["api_key"] == "fake-key-for-test"
    assert ctor_kwargs["timeout"] == 30.0
    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert call_kwargs["model"] == "claude-haiku-4-5"
    assert call_kwargs["max_tokens"] == 300
    # System prompt mentions the 5-bullet structure
    assert "5 bullets" in call_kwargs["system"]
    # User message contains the conversation text
    assert "Initial question about OTP" in call_kwargs["messages"][0]["content"]


def test_summarize_old_turns_returns_empty_when_no_api_key(monkeypatch):
    """THE LOAD-BEARING FALLBACK: when resolve_api_key raises (no key configured
    anywhere), the function returns "" WITHOUT calling Anthropic. The caller in
    orchestrator.load_conversation_summary uses the empty result as a signal to
    skip compaction and fall back to plain truncation. Documented in module
    docstring."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(
        "backend.conversation_compactor.resolve_api_key",
        lambda *a, **kw: (_ for _ in ()).throw(ValueError("no key")),
        raising=False,
    )
    # Patch the import path used inside the function (lazy import)
    with patch("backend.config.resolve_api_key", side_effect=ValueError("no key")):
        with patch("anthropic.Anthropic") as mock_ctor:
            result = cc.summarize_old_turns([
                {"role": "user", "content": "any content"},
            ])

    assert result == ""
    assert mock_ctor.call_count == 0  # Anthropic was never even instantiated


def test_summarize_old_turns_returns_empty_when_anthropic_raises(monkeypatch):
    """Anthropic API errors (rate limit, network, etc.) must not block the query.
    Function swallows the exception and returns "" — caller falls back to whatever
    summary already existed (or plain truncation)."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-test")
    mock_client = MagicMock()
    mock_client.messages.create.side_effect = RuntimeError("rate_limit_exceeded")

    with patch("anthropic.Anthropic", return_value=mock_client):
        result = cc.summarize_old_turns([
            {"role": "user", "content": "any content"},
        ])

    assert result == ""


def test_summarize_old_turns_returns_empty_on_timeout(monkeypatch):
    """G33: explicit 30s timeout on the Anthropic call. A TimeoutError must
    bubble back as an empty summary — caller falls back to truncation. Pre-G33
    the SDK default ~10min could have blocked the query."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-test")
    mock_client = MagicMock()
    mock_client.messages.create.side_effect = TimeoutError("read timed out")

    with patch("anthropic.Anthropic", return_value=mock_client) as mock_ctor:
        result = cc.summarize_old_turns([
            {"role": "user", "content": "any content"},
        ])

    assert result == ""
    # Verify the Anthropic client was constructed with the explicit timeout —
    # this is the load-bearing behavior change for G33.
    call_kwargs = mock_ctor.call_args.kwargs
    assert call_kwargs.get("timeout") == 30.0


def test_summarize_old_turns_empty_input_returns_empty():
    """Empty messages list → empty summary, no API call."""
    with patch("anthropic.Anthropic") as mock_ctor:
        assert cc.summarize_old_turns([]) == ""
    assert mock_ctor.call_count == 0


def test_format_messages_truncates_per_message():
    """A single huge message should be truncated to MAX_MESSAGE_CHARS in the
    formatted output."""
    big_content = "x" * 2000
    formatted = cc._format_messages_for_summary([
        {"role": "user", "content": big_content},
    ])
    assert "[truncated]" in formatted
    assert len(formatted) < 2000  # capped to MAX_MESSAGE_CHARS + small prefix


def test_format_messages_total_cap():
    """Many medium messages summing past MAX_INPUT_CHARS should be truncated
    with an explicit "[earlier turns omitted]" marker."""
    msgs = [{"role": "user", "content": "x" * 400} for _ in range(200)]
    formatted = cc._format_messages_for_summary(msgs)
    assert "[earlier turns omitted due to size]" in formatted
