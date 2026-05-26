#!/usr/bin/env python3
"""Throwaway hand-verification for G06 — Answer-ID feedback prompt.

Exercises backend.orchestrator._inject_answer_id with two synthetic inputs
that mirror what the model would actually emit, prints the before/after,
and asserts the expected outcomes. No API or DB needed.

Run:  venv/bin/python scratch/g06_verify.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

# Make backend importable when run directly
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.orchestrator import _inject_answer_id

REAL_ID = "9f3a7b1c8d4e"  # 12 hex chars, what log_answer() would return

# ── Case 1: model followed the template ─────────────────────────────────────

raw_with_placeholder = """**Answer:** OTP defaults to required on .com.

**Latest evidence** (last ~6 months):
- TS-12345 — updated 2026-04-12 — confirms default = true

**Sources:**
- Wiki/docs: configs/visitor-management.md
- Jira: TS-12345
- PMS configs/runtime: kioskRequireOTPBeforeRegister

---
**Review this answer:** Score 1–5 (5 = fully correct).
**Answer ID:** `<ANSWER_ID>`
If score ≤3, tell me what was wrong or what the answer should have said."""

out1 = _inject_answer_id(raw_with_placeholder, REAL_ID)
print("─" * 72)
print("CASE 1: placeholder present (happy path)")
print("─" * 72)
print(out1)
print()
assert "<ANSWER_ID>" not in out1, "FAIL: placeholder still present"
assert re.search(r"\*\*Answer ID:\*\*\s*`[a-f0-9]{12}`", out1), "FAIL: 12-hex id not rendered"
assert out1.count("**Answer ID:**") == 1, "FAIL: duplicate marker"
print("  ✅ placeholder replaced with real id")
print("  ✅ 12-hex-char id format preserved")
print("  ✅ no duplicate **Answer ID:** marker\n")

# ── Case 2: model dropped the block entirely ────────────────────────────────

raw_without_placeholder = """**Answer:** OTP defaults to required on .com.

**Latest evidence** (last ~6 months):
- TS-12345 — updated 2026-04-12 — confirms default = true

**Sources:**
- Wiki/docs: configs/visitor-management.md
- Jira: TS-12345"""

out2 = _inject_answer_id(raw_without_placeholder, REAL_ID)
print("─" * 72)
print("CASE 2: placeholder missing AND no marker (fallback path)")
print("─" * 72)
print(out2)
print()
assert "<ANSWER_ID>" not in out2, "FAIL: phantom placeholder appeared"
assert "**Review this answer:** Score 1–5 (5 = fully correct)." in out2, "FAIL: line 1 missing"
assert f"**Answer ID:** `{REAL_ID}`" in out2, "FAIL: line 2 (id line) missing or wrong format"
assert "If score ≤3, tell me what was wrong" in out2, "FAIL: line 3 missing"
assert "---\n**Review this answer:**" in out2, "FAIL: --- separator missing"
print("  ✅ 3-line synthetic block appended (matches happy-path format)")
print("  ✅ real id present")
print("  ✅ separator and all three lines correct\n")

print("─" * 72)
print("All hand-verification cases passed.")
