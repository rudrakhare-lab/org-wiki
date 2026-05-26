#!/usr/bin/env python3
"""G04 — manual verification: print the actual seeded message under three
scenarios so we can SEE what the model would receive.

This is mock-based — no live admin_api call. The fixtures use the exact
shape that backend.admin_api.get_sync_status() actually returns (verified
2026-05-22), not what PLAN.md sketched.

Run:  venv/bin/python tests/manual/g04_verify.py
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import backend.operational_context as oc
from backend.preflight import PreflightBundle, build_seed_message


def banner(s: str) -> None:
    print("\n" + "═" * 72)
    print(s)
    print("═" * 72)


def install_fixture(status: dict) -> None:
    """Replace _compute_status() and clear the cache so the next call hits
    the fresh fixture."""
    oc._compute_status = lambda: status  # type: ignore[assignment]
    oc._reset_cache_for_testing()


def jira_log_line(hours_ago: float, msg: str = "sync complete; upserted 482 tickets") -> str:
    """Build a realistic JSON-encoded jira_sync log line."""
    ts = datetime.now(timezone.utc) - timedelta(hours=hours_ago)
    return json.dumps({
        "ts": ts.isoformat().replace("+00:00", "Z"),
        "level": "INFO",
        "logger": "jira_sync",
        "msg": msg,
    })


def sample_bundle() -> PreflightBundle:
    """Return an empty preflight bundle so the manual output focuses on
    operational context + scaffold, not seeded evidence."""
    return PreflightBundle()


SAMPLE_QUESTION = "What is the kioskRequireOTPBeforeRegister config used for?"
SAMPLE_SCOPE = ".com server | BUID: genpactindia-GInd"


# ──────────────────────────────────────────────────────────────────────────────
# Scenario 1: fresh mirror, no pending feedback → block omitted

banner("SCENARIO 1: fresh mirror (1h ago), 0 pending feedback")
install_fixture({
    "jira": {
        "last_sync_line": jira_log_line(hours_ago=1),
        "ticket_count": 37131,
    },
    "drive": {"last_sync": "", "file_count": 0},
    "feedback": {"pending_count": 0},
})

block = oc.get_context_block()
print(f"get_context_block() returned: {block!r}")
print(f"(empty string = block intentionally omitted)\n")

print("FULL SEEDED MESSAGE the model would receive:")
print("─" * 72)
print(build_seed_message(SAMPLE_QUESTION, SAMPLE_SCOPE, sample_bundle()))

assert block == "", "FAIL: expected empty block for fresh+zero-pending scenario"
print("\n✅ block correctly omitted")


# ──────────────────────────────────────────────────────────────────────────────
# Scenario 2: stale mirror (72h), 0 pending feedback → stale warning

banner("SCENARIO 2: stale mirror (72h ago — error log line), 0 pending")
install_fixture({
    "jira": {
        # Real-world: admin_api grabs the last line matching 'sync complete' OR
        # 'tickets'; that can be an error line if a sync failed. Mirror that here.
        "last_sync_line": jira_log_line(hours_ago=72, msg="normalize/upsert failed for TB-40308"),
        "ticket_count": 37131,
    },
    "drive": {"last_sync": "", "file_count": 0},
    "feedback": {"pending_count": 0},
})

block = oc.get_context_block()
print(f"get_context_block() returned:\n{block}")

print("FULL SEEDED MESSAGE the model would receive:")
print("─" * 72)
print(build_seed_message(SAMPLE_QUESTION, SAMPLE_SCOPE, sample_bundle()))

assert "⚠️" in block and "72h" in block, "FAIL: expected stale warning"
print("\n✅ stale-mirror warning present in block")


# ──────────────────────────────────────────────────────────────────────────────
# Scenario 3: fresh mirror + 5 pending feedback → pending line, no stale warning

banner("SCENARIO 3: fresh mirror (2h ago), 5 pending feedback")
install_fixture({
    "jira": {
        "last_sync_line": jira_log_line(hours_ago=2),
        "ticket_count": 37131,
    },
    "drive": {"last_sync": "", "file_count": 0},
    "feedback": {"pending_count": 5},
})

block = oc.get_context_block()
print(f"get_context_block() returned:\n{block}")

print("FULL SEEDED MESSAGE the model would receive:")
print("─" * 72)
print(build_seed_message(SAMPLE_QUESTION, SAMPLE_SCOPE, sample_bundle()))

assert "Pending feedback awaiting admin review: 5 items." in block
assert "⚠️" not in block, "FAIL: stale warning should not be present"
print("\n✅ pending-feedback line present, no stale warning\n")


# ──────────────────────────────────────────────────────────────────────────────
# Scenario 4 (bonus): empty mirror — hard error path

banner("SCENARIO 4 (bonus): empty Jira mirror (ticket_count=0)")
install_fixture({
    "jira": {"last_sync_line": "", "ticket_count": 0},
    "drive": {"last_sync": "", "file_count": 0},
    "feedback": {"pending_count": 0},
})

block = oc.get_context_block()
print(f"get_context_block() returned:\n{block}")
assert "Jira mirror is empty" in block, "FAIL: expected empty-mirror warning"
print("✅ empty-mirror hard error surfaced")


print("\n" + "═" * 72)
print("Manual verification complete — all four scenarios behaved as expected.")
print("═" * 72)
