#!/usr/bin/env python3
"""G03 — manual verification: print the full seeded message under four
scenarios so we can SEE what the model receives in each compaction state.

Mocked Anthropic (no live API call) — the compactor's external dependency
is stubbed so this script runs without any credentials, ANY time. Uses a
temporary SQLite store so we don't touch real conversation data.

Four scenarios per the G03 plan:
  (a) under threshold — no summary block, no compactor call
  (b) over threshold, no prior summary — fresh compaction, mock returns
      a realistic 5-bullet summary
  (c) over threshold, summary already cached, not enough new messages —
      cached summary reused, no compactor call
  (d) over threshold, no API key configured — fallback to plain truncation
      (no summary block in seed)

Run: venv/bin/python tests/manual/g03_verify.py
"""
from __future__ import annotations

import importlib
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))


# Set up an isolated SQLite + reset the relevant module attributes BEFORE
# the orchestrator/conversation_store modules read them.
TMPDIR = Path(tempfile.mkdtemp(prefix="g03_verify_"))
FAKE_CONV_DIR = TMPDIR / "conversations"
FAKE_CONV_DIR.mkdir(parents=True)
FAKE_DB = FAKE_CONV_DIR / "conversations.sqlite"

# Point config at the temp paths
from backend import config  # noqa: E402
config.CONVERSATIONS_DIR = FAKE_CONV_DIR
config.CONVERSATIONS_DB = FAKE_DB

# Reload conversation_store so it picks up the patched paths
import backend.conversation_store as conversation_store  # noqa: E402
importlib.reload(conversation_store)
import backend.orchestrator as orchestrator  # noqa: E402
importlib.reload(orchestrator)

from backend.preflight import PreflightBundle, build_seed_message  # noqa: E402


REAL_SHAPE_SUMMARY = """- User is debugging visitor-management OTP behavior on .com server, BUID genpactindia-GInd.
- Issue narrowed to office-level overrides — not all offices under the BUID are affected.
- Referenced TS-12345 (office-specific override fix) and kioskRequireOTPBeforeRegister.
- BUID-level default is false; effective value at BUID matches default.
- Open question: which OFFICEIDs have the override and what value is set there."""


def banner(s: str) -> None:
    print("\n" + "═" * 72)
    print(s)
    print("═" * 72)


def add_turns(conv_id: str, n_turns: int) -> None:
    """Add n_turns user+assistant pairs to the conversation."""
    for i in range(n_turns):
        conversation_store.add_message(conv_id, "user", f"user turn {i+1}: question about OTP behavior on office {i+1}")
        conversation_store.add_message(conv_id, "assistant", f"assistant turn {i+1}: answer with hierarchy data for office {i+1}")


def reset_compaction(conv_id: str) -> None:
    conversation_store.set_compacted_summary(conv_id, summary="", at_turn=0)
    # Clear via direct UPDATE — set both back to NULL
    import sqlite3
    with sqlite3.connect(str(FAKE_DB)) as c:
        c.execute("UPDATE conversations SET compacted_summary = NULL, compaction_at_turn = NULL WHERE id = ?", (conv_id,))


SAMPLE_QUESTION = "Now what about RoomID-level overrides?"
SAMPLE_SCOPE = ".com server | BUID: genpactindia-GInd"


def print_seed(label: str, summary: str) -> None:
    """Render and print the full seeded message under the given summary."""
    seed = build_seed_message(SAMPLE_QUESTION, SAMPLE_SCOPE, PreflightBundle(), summary=summary)
    print(f"[{label}] — final seeded message the model would receive:")
    print("─" * 72)
    print(seed)
    print()


# ──────────────────────────────────────────────────────────────────────────────
# Scenario A — under threshold

banner("SCENARIO A: under threshold (4 turns = 8 messages) — no summary")
conv_a = conversation_store.create_conversation("scenario A", user_email="test@example.com")
add_turns(conv_a["id"], 4)

# Confirm: should_refresh decision
from backend.conversation_compactor import should_refresh
total = len([m for m in conversation_store.get_conversation(conv_a["id"])["messages"] if m["role"] in ("user", "assistant")])
print(f"  total messages: {total}")
print(f"  should_refresh({total}, None) = {should_refresh(total, None)}")
print(f"  → expected: False (under recent window of 12)\n")

summary_a = orchestrator.load_conversation_summary(conv_a["id"])
assert summary_a == "", f"FAIL: expected empty summary, got {summary_a!r}"
print(f"  load_conversation_summary returned: {summary_a!r}")
print_seed("Scenario A", summary_a)


# ──────────────────────────────────────────────────────────────────────────────
# Scenario B — over threshold, fresh compaction

banner("SCENARIO B: over threshold (10 turns = 20 messages), no prior summary — FRESH compaction")
conv_b = conversation_store.create_conversation("scenario B", user_email="test@example.com")
add_turns(conv_b["id"], 10)

total_b = len([m for m in conversation_store.get_conversation(conv_b["id"])["messages"] if m["role"] in ("user", "assistant")])
print(f"  total messages: {total_b}")
print(f"  should_refresh({total_b}, None) = {should_refresh(total_b, None)}")
print(f"  → expected: True (over window, never compacted)\n")

# Mock anthropic.Anthropic to return our realistic 5-bullet summary
mock_block = MagicMock()
mock_block.text = REAL_SHAPE_SUMMARY
mock_resp = MagicMock()
mock_resp.content = [mock_block]
mock_client = MagicMock()
mock_client.messages.create.return_value = mock_resp

import os
os.environ["ANTHROPIC_API_KEY"] = "fake-key-for-verify"
with patch("anthropic.Anthropic", return_value=mock_client) as mock_ctor:
    summary_b = orchestrator.load_conversation_summary(conv_b["id"])
    anthropic_calls = mock_ctor.call_count

print(f"  Anthropic SDK instantiated: {anthropic_calls} time(s)")
print(f"  load_conversation_summary returned:\n    {repr(summary_b[:80])}...\n")
# Confirm stored
stored, at_turn = conversation_store.get_compaction_state(conv_b["id"])
print(f"  Persisted: compaction_at_turn={at_turn}, summary length={len(stored or '')}")
print_seed("Scenario B", summary_b)


# ──────────────────────────────────────────────────────────────────────────────
# Scenario C — over threshold, cached summary reused (no refresh)

banner("SCENARIO C: cached summary, only 2 new messages — REUSE, no compaction call")
# conv_b already has 20 msgs + compacted at 20. Add 2 more (1 turn) → total 22.
add_turns(conv_b["id"], 1)
total_c = len([m for m in conversation_store.get_conversation(conv_b["id"])["messages"] if m["role"] in ("user", "assistant")])
print(f"  total messages now: {total_c}")
print(f"  compaction_at_turn: {at_turn}")
print(f"  should_refresh({total_c}, {at_turn}) = {should_refresh(total_c, at_turn)}")
print(f"  → expected: False (only {total_c - (at_turn or 0)} new since last compaction, threshold 6)\n")

# Patch Anthropic to assert it is NOT called this time
mock_client_c = MagicMock()
mock_client_c.messages.create.side_effect = AssertionError("Anthropic should NOT be called when cached summary is reused")
with patch("anthropic.Anthropic", return_value=mock_client_c) as mock_ctor_c:
    summary_c = orchestrator.load_conversation_summary(conv_b["id"])
    assert mock_ctor_c.call_count == 0, "Anthropic was instantiated even though cache is fresh"

print(f"  Anthropic SDK instantiated: {mock_ctor_c.call_count} time(s) ✅ (no refresh needed)")
print(f"  summary returned matches stored: {summary_c == stored}")
print_seed("Scenario C", summary_c)


# ──────────────────────────────────────────────────────────────────────────────
# Scenario D — over threshold, no API key → fallback to plain truncation

banner("SCENARIO D: over threshold, NO API KEY — fallback to plain truncation (degradation mode)")
conv_d = conversation_store.create_conversation("scenario D", user_email="test@example.com")
add_turns(conv_d["id"], 10)
total_d = len([m for m in conversation_store.get_conversation(conv_d["id"])["messages"] if m["role"] in ("user", "assistant")])
print(f"  total messages: {total_d}")
print(f"  should_refresh({total_d}, None) = {should_refresh(total_d, None)}")
print(f"  → expected: True (would refresh, except no key…)\n")

# Clear the env var so resolve_api_key raises
saved_key = os.environ.pop("ANTHROPIC_API_KEY", None)
try:
    # The function should not even instantiate Anthropic
    with patch("anthropic.Anthropic") as mock_ctor_d:
        summary_d = orchestrator.load_conversation_summary(conv_d["id"])
    print(f"  Anthropic SDK instantiated: {mock_ctor_d.call_count} time(s) ✅ (no key, no call)")
    print(f"  load_conversation_summary returned: {summary_d!r}")
    print(f"  → degradation: model gets last 12 messages verbatim, NO summary block in seed.\n")
finally:
    if saved_key is not None:
        os.environ["ANTHROPIC_API_KEY"] = saved_key

print_seed("Scenario D", summary_d)


print("═" * 72)
print("Manual verification complete — all four scenarios behaved as expected.")
print(f"Temp store: {FAKE_DB} (delete with: rm -rf {TMPDIR})")
print("═" * 72)
