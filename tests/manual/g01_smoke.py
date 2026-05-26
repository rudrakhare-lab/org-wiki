#!/usr/bin/env python3
"""G01 — Live Jira ticket lookup smoke test against REAL Atlassian.

Run:  venv/bin/python tests/manual/g01_smoke.py

Loads .env from the project root (same pattern as scripts/jira_sync.py),
then exercises backend.tools.jira_live_tools._jira_live_get_ticket_handler
against real tickets, a known-bad key, and a malformed key. Prints the
result and basic rate-limit info.

This is NOT part of the regular test suite — it requires live network +
real Jira credentials. Do not commit the produced output (it contains
ticket data).
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Make backend + scripts importable when run directly
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

# Load .env the same way scripts/jira_sync.py does
from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

# Now config + tool module can pick up JIRA_BASE_URL et al.
from backend.tools.jira_live_tools import _jira_live_get_ticket_handler


def banner(s: str) -> None:
    print("\n" + "─" * 72)
    print(s)
    print("─" * 72)


def print_result(label: str, result: dict) -> None:
    print(f"[{label}]")
    # Don't print huge fields verbatim
    pretty = {k: v for k, v in result.items() if k != "_rate_limit_remaining"}
    print(json.dumps(pretty, indent=2, default=str))
    if "_rate_limit_remaining" in result:
        print(f"  X-RateLimit-Remaining: {result['_rate_limit_remaining']}")


# ── Sanity: env loaded? ────────────────────────────────────────────────────

banner("Env preflight")
for var in ("JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_API_TOKEN"):
    val = os.getenv(var, "")
    if not val:
        print(f"  ❌ {var} not set — abort.")
        sys.exit(1)
    # Show only that it exists, never the value (tokens especially)
    print(f"  ✅ {var}: set ({len(val)} chars)")


# ── Case 1: known-good ticket from local mirror ─────────────────────────────

banner("Case 1: real ticket TO-25737 (last resolved P0 in mirror; expect status=Done)")
result1 = _jira_live_get_ticket_handler({"key": "TO-25737"})
print_result("TO-25737", result1)

assert "error" not in result1, f"Live call failed: {result1.get('error')}"
assert result1.get("key") == "TO-25737"
assert result1.get("source") == "live"
print("  ✅ no error envelope")
print("  ✅ key echoes back correctly")
print(f"  ▸ Status: {result1.get('status')} (category: {result1.get('status_category')})")
print(f"  ▸ Priority: {result1.get('priority')}")
print(f"  ▸ Resolution: {result1.get('resolution')}")
print(f"  ▸ Updated: {result1.get('updated')}")
print(f"  ▸ Assignee: {result1.get('assignee')}")
print(f"  ▸ Summary: {(result1.get('summary') or '')[:120]}")
print("  → compare these against Jira UI to confirm field mapping is correct.")


# ── Case 2: secondary ticket for sanity ─────────────────────────────────────

banner("Case 2: real ticket SE-57495 (second-most-recent resolved P0)")
result2 = _jira_live_get_ticket_handler({"key": "SE-57495"})
print_result("SE-57495", result2)

assert "error" not in result2, f"Live call failed: {result2.get('error')}"
assert result2.get("key") == "SE-57495"
print("  ✅ second ticket also returned cleanly")
print(f"  ▸ Status: {result2.get('status')} | Resolution: {result2.get('resolution')}")


# ── Case 3: deliberately bad key — expect not_found ─────────────────────────

banner("Case 3: bad key FAKE-999999 (expect not_found)")
result3 = _jira_live_get_ticket_handler({"key": "FAKE-999999"})
print_result("FAKE-999999", result3)

assert result3.get("code") == "not_found", f"Expected not_found, got {result3}"
print("  ✅ returned not_found code (404 mapped correctly)")


# ── Case 4: malformed key — expect invalid_key_format, no network call ──────

banner("Case 4: malformed key 'not-a-key' (expect invalid_key_format, no network)")
result4 = _jira_live_get_ticket_handler({"key": "not-a-key"})
print_result("not-a-key", result4)

assert result4.get("code") == "invalid_key_format", f"Expected invalid_key_format, got {result4}"
print("  ✅ regex short-circuit fired before any HTTP call")


# ── Rate-limit observation ──────────────────────────────────────────────────

banner("Rate limit observation")
rl = result1.get("_rate_limit_remaining")
if rl is None:
    print("  ▸ X-RateLimit-Remaining header NOT present in response.")
    print("    Atlassian may not surface it on /rest/api/3/issue/{key} —")
    print("    rely on the documented 10 rps cap in config/jira.toml instead.")
else:
    print(f"  ▸ X-RateLimit-Remaining: {rl}")
    try:
        if int(rl) < 50:
            print("  ⚠️  Less than 50 requests remaining — consider backoff in production.")
    except (TypeError, ValueError):
        pass


print("\n" + "─" * 72)
print("Smoke test complete.")
