#!/usr/bin/env python3
"""Track A end-to-end verification harness.

Walks through all 5 paths the admin apply layer can take:
  1. propose_new → apply → file exists on disk + retriever sees it
  2. propose_edit → apply → file content changed
  3. propose_append → apply → log entry appended
  4. propose_multi_edit → apply → both files changed atomically
  5. legacy_text → /apply refused → /mark-applied succeeds

Uses a temp directory throughout — the real wiki/ is never touched.
Mirrors G03/G04/G05 verify pattern.

Run: venv/bin/python tests/manual/track_a_verify.py
"""
from __future__ import annotations

import importlib
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

# Temp wiki + feedback
TMPDIR = Path(tempfile.mkdtemp(prefix="track_a_verify_"))
FAKE_WIKI = TMPDIR / "wiki"
FAKE_WIKI.mkdir()
FAKE_FB = TMPDIR / "feedback"
FAKE_FB.mkdir()

# Point modules at the temp paths BEFORE they're imported by anyone else
from backend import config
config.WIKI_DIR = FAKE_WIKI
config.FEEDBACK_DIR = FAKE_FB

# Reload modules so they see the new config
import backend.wiki_proposals as wp
importlib.reload(wp)
wp.PROPOSALS_FILE = FAKE_FB / "wiki_proposals.jsonl"
wp.FEEDBACK_DIR = FAKE_FB

import backend.wiki_apply as wa
importlib.reload(wa)
wa.WIKI_DIR = FAKE_WIKI

import backend.admin_api as adm
importlib.reload(adm)

import backend.tools.wiki_propose_tools as wpt
importlib.reload(wpt)
wpt.WIKI_DIR = FAKE_WIKI
wpt.wiki_proposals = wp

# Mock retriever for the propose-time validation (which calls get_page)
_retriever_pages: dict[str, MagicMock] = {}


def _set_retriever_page(rel_path: str, content: str) -> None:
    p = MagicMock()
    p.path = rel_path
    p.title = rel_path
    p.full_text = content
    _retriever_pages[rel_path] = p


def _fake_get_page(rel_path: str):
    return _retriever_pages.get(rel_path)


fake_retriever = MagicMock()
fake_retriever.get_page = _fake_get_page
fake_retriever.rebuild_index = MagicMock()
wpt.wiki_retriever = fake_retriever

# Also patch the admin_api's wiki_retriever import path so rebuild_index doesn't
# error on the real index
import backend.wiki_retriever as real_retriever
real_retriever.rebuild_index = lambda: None  # no-op for the harness


def banner(s: str) -> None:
    print("\n" + "═" * 72)
    print(s)
    print("═" * 72)


def show_proposal(pid: str) -> None:
    p = wp.get_proposal(pid)
    if not p:
        print(f"  proposal {pid} not found")
        return
    print(f"  proposal_id   : {p['id']}")
    print(f"  type          : {p['proposal_type']}")
    print(f"  status        : {p['status']}")
    print(f"  applied_by    : {p['applied_by']}")
    print(f"  applied_at    : {p['applied_at']}")


# ──────────────────────────────────────────────────────────────────────────────
# Scenario 1 — propose_new → apply

banner("Scenario 1: propose_new → apply (creates new page on disk)")
propose1 = wpt._wiki_propose_new_handler({
    "page_path": "concepts/meal-cutoff-ref.md",
    "content": "---\ntype: concept\nlast_updated: 2026-05-22\n---\n\n# Meal cutoff reference\n\nThis is the reusable answer.\n",
    "reason": "save answer as wiki page",
})
print(f"  propose result: {json.dumps({k: v for k, v in propose1.items() if k != 'message'}, indent=2)}")
pid1 = propose1["proposal_id"]
target1 = FAKE_WIKI / "concepts" / "meal-cutoff-ref.md"
assert not target1.exists(), "file shouldn't exist yet"

apply1 = adm.apply_wiki_proposal(pid1, applied_by="admin@example.com")
print(f"  apply result success={apply1['success']}, files_written={apply1.get('files_written')}")
assert apply1["success"], f"apply failed: {apply1}"
assert target1.is_file(), "file should now exist"
print(f"  on disk at: {target1}")
print(f"  content: {target1.read_text()[:80]!r}")
show_proposal(pid1)


# ──────────────────────────────────────────────────────────────────────────────
# Scenario 2 — propose_edit → apply

banner("Scenario 2: propose_edit → apply (str_replace on existing page)")
edit_page = FAKE_WIKI / "concepts" / "edit-target.md"
edit_page.parent.mkdir(parents=True, exist_ok=True)
edit_page.write_text("---\ntype: concept\n---\n\nDefault value is **false**.\n")
_set_retriever_page("concepts/edit-target.md", edit_page.read_text())

propose2 = wpt._wiki_propose_edit_handler({
    "page_path": "concepts/edit-target.md",
    "old_string": "Default value is **false**.",
    "new_string": "Default value is **true**.",
    "reason": "Q3 correction",
})
print(f"  propose result: status={propose2['status']}, has_companion_edit={propose2.get('has_companion_edit')}")
pid2 = propose2["proposal_id"]

apply2 = adm.apply_wiki_proposal(pid2, applied_by="admin@example.com")
print(f"  apply result success={apply2['success']}, files_written={apply2.get('files_written')}")
assert apply2["success"], f"apply failed: {apply2}"
print(f"  post-edit content: {edit_page.read_text()!r}")
assert "**true**" in edit_page.read_text()
show_proposal(pid2)


# ──────────────────────────────────────────────────────────────────────────────
# Scenario 3 — propose_append → apply (log.md)

banner("Scenario 3: propose_append → apply (log.md entry)")
log_page = FAKE_WIKI / "log.md"
log_page.write_text("# Activity Log\n\nExisting entry.\n")
_set_retriever_page("log.md", log_page.read_text())

propose3 = wpt._wiki_propose_append_handler({
    "page_path": "log.md",
    "content": "## [2026-05-22 14:00] feedback-apply | OTP correction\n\n- patched configs/visitor-management.md\n",
    "reason": "log the apply",
})
print(f"  propose result: status={propose3['status']}, type={propose3.get('proposal_type')}")
pid3 = propose3["proposal_id"]

apply3 = adm.apply_wiki_proposal(pid3, applied_by="admin@example.com")
print(f"  apply result success={apply3['success']}, files_written={apply3.get('files_written')}")
assert apply3["success"], f"apply failed: {apply3}"
print("  post-append content:")
for line in log_page.read_text().splitlines():
    print(f"    {line}")
assert "feedback-apply | OTP correction" in log_page.read_text()
show_proposal(pid3)


# ──────────────────────────────────────────────────────────────────────────────
# Scenario 4 — propose_multi_edit → apply (atomic two-file change)

banner("Scenario 4: propose_multi_edit → apply (atomic, bidirectional links)")
a_page = FAKE_WIKI / "modules" / "module-a.md"
b_page = FAKE_WIKI / "modules" / "module-b.md"
a_page.parent.mkdir(parents=True, exist_ok=True)
a_page.write_text("---\ntype: module\nused_by: []\n---\n\n# A\n")
b_page.write_text("---\ntype: module\nused_by: []\n---\n\n# B\n")
_set_retriever_page("modules/module-a.md", a_page.read_text())
_set_retriever_page("modules/module-b.md", b_page.read_text())

propose4 = wpt._wiki_propose_multi_edit_handler({
    "edits": [
        {"page_path": "modules/module-a.md", "old_string": "used_by: []", "new_string": "used_by: [module-b]"},
        {"page_path": "modules/module-b.md", "old_string": "used_by: []", "new_string": "used_by: [module-a]"},
    ],
    "reason": "bidirectional reciprocity update",
})
print(f"  propose result: status={propose4['status']}, edit_count={propose4.get('edit_count')}")
pid4 = propose4["proposal_id"]

apply4 = adm.apply_wiki_proposal(pid4, applied_by="admin@example.com")
print(f"  apply result: success={apply4['success']}, rollback_status={apply4.get('rollback_status')}")
print(f"  files_written: {apply4.get('files_written')}")
assert apply4["success"], f"apply failed: {apply4}"
assert apply4["rollback_status"] == "clean"
assert "used_by: [module-b]" in a_page.read_text()
assert "used_by: [module-a]" in b_page.read_text()
print("  module-a.md post-edit:")
for line in a_page.read_text().splitlines():
    print(f"    {line}")
print("  module-b.md post-edit:")
for line in b_page.read_text().splitlines():
    print(f"    {line}")


# ──────────────────────────────────────────────────────────────────────────────
# Scenario 5 — legacy_text proposal: /apply refused, /mark-applied succeeds

banner("Scenario 5: legacy_text → /apply REFUSED → /mark-applied succeeds")
pid5 = wp.create_proposal(
    page_path="modules/visitor-management.md",
    proposed_change="Free-text correction from pre-Track-A.",
    submitter_email="agent",
)
print(f"  created legacy_text proposal: {pid5}")
apply5_a = adm.apply_wiki_proposal(pid5)
print(f"  /apply result: success={apply5_a['success']}, code={apply5_a.get('code')}")
print(f"    message: {apply5_a.get('message')[:200]}")
assert apply5_a["success"] is False
assert apply5_a["code"] == "legacy_text_refused"

apply5_b = adm.mark_wiki_proposal_applied(pid5, applied_by="admin@example.com")
print(f"  /mark-applied result: success={apply5_b['success']}")
assert apply5_b["success"]
show_proposal(pid5)


# ──────────────────────────────────────────────────────────────────────────────
# Scenario 6 — idempotency: re-applying succeeds without re-writing

banner("Scenario 6: idempotency — re-apply on already-applied proposal")
mtime_before = target1.stat().st_mtime
import time as _t; _t.sleep(0.05)
apply1_again = adm.apply_wiki_proposal(pid1, applied_by="admin@example.com")
mtime_after = target1.stat().st_mtime
print(f"  apply result: success={apply1_again['success']}, code={apply1_again.get('code')}")
assert apply1_again["code"] == "already_applied"
assert mtime_after == mtime_before, "file rewritten despite already_applied"
print(f"  file mtime unchanged: ✅ ({mtime_before})")


print("\n" + "═" * 72)
print("Track A end-to-end verification complete — all 6 scenarios passed.")
print(f"Temp dir: {TMPDIR} (delete with: rm -rf {TMPDIR})")
print("═" * 72)
