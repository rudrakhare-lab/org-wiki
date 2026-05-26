# Layer 3 — Sync Automation + Wiki Approval Queue Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Automate Jira + Drive sync on the deployment VM so data stays fresh without manual intervention; add a wiki edit approval queue so contributors can flag corrections without writing directly to wiki/.

**Architecture:** `scripts/jira_sync.py --incremental` and `scripts/sync_drive.py` already exist and are correct. Layer 3 wires them to crontab on the VM and adds an on-demand admin trigger for Drive. A new `backend/wiki_proposals.py` stores proposals in `raw/feedback/wiki_proposals.jsonl`. A new `wiki_propose_edit` tool in `backend/tools/wiki_tools.py` writes to that JSONL — never to `wiki/` directly. Admin endpoints expose the proposal queue for review and apply/reject actions.

**Tech Stack:** Python 3.12, FastAPI, crontab (VM), JSONL, Angular 17

**Prerequisite:** Layer 1 and Layer 2 plans complete and passing.

---

## File Structure

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `backend/wiki_proposals.py` | JSONL proposal store — create, list, get, update status |
| Modify | `backend/tools/wiki_tools.py` | Add `wiki_propose_edit` schema + handler |
| Modify | `backend/tools/__init__.py` | Register `wiki_propose_edit` for contributor+ roles |
| Modify | `backend/tools/registry.py` | Add `wiki_propose_edit` to `_TOOL_PERMISSIONS` for contributor |
| Modify | `backend/admin_api.py` | `get_wiki_proposals()`, `apply_wiki_proposal()`, `reject_wiki_proposal()`, `trigger_drive_sync()` |
| Modify | `backend/api.py` | New `/admin/wiki/proposals*` + `/admin/trigger-drive-sync` endpoints |
| Create | `deploy/crontab.example` | VM cron schedule with no real credentials |
| Create | `tests/test_wiki_proposals.py` | Proposal store CRUD + tool handler tests |
| Modify | `tests/test_tools.py` | `wiki_propose_edit` registered for contributor, blocked for viewer |

---

## Task 1: `backend/wiki_proposals.py` — JSONL proposal store

**Files:**
- Create: `backend/wiki_proposals.py`
- Create: `tests/test_wiki_proposals.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_wiki_proposals.py
import importlib
import json
import pytest
from pathlib import Path


@pytest.fixture
def isolated_proposals(tmp_path, monkeypatch):
    """Point wiki_proposals at a fresh JSONL under tmp_path."""
    feedback_dir = tmp_path / "raw" / "feedback"
    feedback_dir.mkdir(parents=True)
    proposals_file = feedback_dir / "wiki_proposals.jsonl"

    import backend.wiki_proposals as wp_module
    monkeypatch.setattr(wp_module, "PROPOSALS_FILE", proposals_file, raising=False)
    importlib.reload(wp_module)
    yield wp_module


def test_create_and_list_proposals(isolated_proposals):
    wp = isolated_proposals
    pid = wp.create_proposal(
        page_path="modules/visitor-management.md",
        proposed_change="OTP is required, not optional",
        submitter_email="alice@example.com",
        answer_id="abc123",
    )
    assert pid is not None
    proposals = wp.list_proposals()
    assert len(proposals) == 1
    assert proposals[0]["page_path"] == "modules/visitor-management.md"
    assert proposals[0]["status"] == "pending"


def test_get_proposal(isolated_proposals):
    wp = isolated_proposals
    pid = wp.create_proposal(
        page_path="modules/meeting-rooms.md",
        proposed_change="Booking slots are 30 min, not 15 min",
        submitter_email="bob@example.com",
    )
    p = wp.get_proposal(pid)
    assert p is not None
    assert p["id"] == pid


def test_apply_proposal(isolated_proposals):
    wp = isolated_proposals
    pid = wp.create_proposal(
        page_path="modules/visitor-management.md",
        proposed_change="Fix description",
        submitter_email="carol@example.com",
    )
    wp.update_status(pid, "applied", admin_note="Looks correct")
    p = wp.get_proposal(pid)
    assert p["status"] == "applied"
    assert p["admin_note"] == "Looks correct"


def test_reject_proposal(isolated_proposals):
    wp = isolated_proposals
    pid = wp.create_proposal(
        page_path="modules/desk-management.md",
        proposed_change="Wrong info",
        submitter_email="dave@example.com",
    )
    wp.update_status(pid, "rejected", admin_note="Not accurate")
    p = wp.get_proposal(pid)
    assert p["status"] == "rejected"


def test_list_proposals_filtered_by_status(isolated_proposals):
    wp = isolated_proposals
    p1 = wp.create_proposal("a.md", "fix a", "alice@example.com")
    p2 = wp.create_proposal("b.md", "fix b", "bob@example.com")
    wp.update_status(p1, "applied")

    pending = wp.list_proposals(status="pending")
    assert len(pending) == 1
    assert pending[0]["id"] == p2


def test_proposal_never_writes_to_wiki_dir(isolated_proposals, tmp_path):
    """Proposals JSONL must stay inside raw/feedback, not wiki/."""
    wp = isolated_proposals
    import os
    wiki_path = tmp_path / "wiki"
    wiki_path.mkdir()
    # create_proposal does NOT write inside wiki_path
    wp.create_proposal("modules/foo.md", "change", "eve@example.com")
    wiki_files = list(wiki_path.rglob("*"))
    assert wiki_files == [], "wiki/ must not be written by create_proposal"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd org-wiki && venv/bin/pytest tests/test_wiki_proposals.py -v 2>&1 | head -15
```

Expected: `ModuleNotFoundError: No module named 'backend.wiki_proposals'`

- [ ] **Step 3: Create `backend/wiki_proposals.py`**

```python
"""
Wiki edit proposal store — JSONL-backed.

Proposals are stored in raw/feedback/wiki_proposals.jsonl.
One JSON object per line, appended on create, rewritten on status update.

IMPORTANT: This module never writes to wiki/ directly. The wiki_propose_edit
tool uses this module, and apply_wiki_proposal() in admin_api.py invokes
apply_feedback.py which handles the actual wiki write after admin approval.
"""
from __future__ import annotations

import json
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.config import FEEDBACK_DIR

PROPOSALS_FILE = FEEDBACK_DIR / "wiki_proposals.jsonl"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _new_id() -> str:
    return "prop_" + secrets.token_hex(6)


def _load_all() -> list[dict[str, Any]]:
    if not PROPOSALS_FILE.exists():
        return []
    proposals = []
    for line in PROPOSALS_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                proposals.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return proposals


def _save_all(proposals: list[dict[str, Any]]) -> None:
    FEEDBACK_DIR.mkdir(parents=True, exist_ok=True)
    PROPOSALS_FILE.write_text(
        "\n".join(json.dumps(p, ensure_ascii=False) for p in proposals) + "\n",
        encoding="utf-8",
    )


def create_proposal(
    page_path: str,
    proposed_change: str,
    submitter_email: str,
    answer_id: str | None = None,
) -> str:
    """Append a new proposal and return its ID."""
    pid = _new_id()
    proposal = {
        "id": pid,
        "page_path": page_path,
        "proposed_change": proposed_change,
        "submitter_email": submitter_email,
        "answer_id": answer_id,
        "status": "pending",
        "admin_note": None,
        "created_at": _now(),
        "resolved_at": None,
    }
    FEEDBACK_DIR.mkdir(parents=True, exist_ok=True)
    with PROPOSALS_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(proposal, ensure_ascii=False) + "\n")
    return pid


def list_proposals(status: str | None = None) -> list[dict[str, Any]]:
    proposals = _load_all()
    if status is not None:
        proposals = [p for p in proposals if p.get("status") == status]
    return sorted(proposals, key=lambda p: p.get("created_at", ""), reverse=True)


def get_proposal(proposal_id: str) -> dict[str, Any] | None:
    for p in _load_all():
        if p.get("id") == proposal_id:
            return p
    return None


def update_status(
    proposal_id: str,
    status: str,
    admin_note: str | None = None,
) -> bool:
    proposals = _load_all()
    found = False
    for p in proposals:
        if p.get("id") == proposal_id:
            p["status"] = status
            p["admin_note"] = admin_note
            p["resolved_at"] = _now()
            found = True
            break
    if found:
        _save_all(proposals)
    return found
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
venv/bin/pytest tests/test_wiki_proposals.py -v
```

Expected: all 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/wiki_proposals.py tests/test_wiki_proposals.py
git commit -m "feat(wiki-proposals): JSONL-backed proposal store, never writes to wiki/"
```

---

## Task 2: `wiki_propose_edit` tool

**Files:**
- Modify: `backend/tools/wiki_tools.py`
- Modify: `backend/tools/registry.py`
- Modify: `backend/tools/__init__.py`
- Modify: `tests/test_tools.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_tools.py`:

```python
# ── 10. wiki_propose_edit tool ─────────────────────────────────────────────────

def test_wiki_propose_edit_registered_for_contributor():
    """contributor role should have wiki_propose_edit in schema list."""
    registry = build_registry(user_role="contributor")
    names = {s["name"] for s in registry.schemas}
    assert "wiki_propose_edit" in names


def test_wiki_propose_edit_blocked_for_viewer():
    """viewer role gets permission_denied when calling wiki_propose_edit."""
    import json
    registry = build_registry(user_role="viewer")
    result_json, trace = registry.execute(
        "wiki_propose_edit",
        {"page_path": "modules/foo.md", "proposed_change": "fix"},
        round_num=1,
    )
    result = json.loads(result_json)
    assert result["code"] == "permission_denied"


def test_wiki_propose_edit_handler_writes_proposal(tmp_path, monkeypatch):
    """Handler appends to wiki_proposals.jsonl, never touches wiki/."""
    import importlib
    import backend.wiki_proposals as wp_module
    feedback_dir = tmp_path / "raw" / "feedback"
    feedback_dir.mkdir(parents=True)
    monkeypatch.setattr(wp_module, "PROPOSALS_FILE", feedback_dir / "wiki_proposals.jsonl", raising=False)
    monkeypatch.setattr(wp_module, "FEEDBACK_DIR", feedback_dir, raising=False)
    importlib.reload(wp_module)

    from backend.tools.wiki_tools import _wiki_propose_edit_handler
    result = _wiki_propose_edit_handler(
        {"page_path": "modules/visitor-management.md", "proposed_change": "OTP is required"}
    )
    assert result.get("status") == "submitted"
    assert "proposal_id" in result

    proposals = wp_module.list_proposals()
    assert len(proposals) == 1
    assert proposals[0]["page_path"] == "modules/visitor-management.md"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
venv/bin/pytest tests/test_tools.py::test_wiki_propose_edit_registered_for_contributor -v
```

Expected: `AssertionError: 'wiki_propose_edit' not in {'wiki_search', ...}`

- [ ] **Step 3: Add `wiki_propose_edit` schema and handler to `backend/tools/wiki_tools.py`**

Add to the end of `backend/tools/wiki_tools.py`:

```python
WIKI_PROPOSE_EDIT_SCHEMA = {
    "name": "wiki_propose_edit",
    "description": (
        "Submit a proposed correction to a wiki page for admin review. "
        "Use when tool results contradict existing wiki content or you spot an error. "
        "Does NOT write directly to the wiki — creates a proposal requiring admin approval."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "page_path": {
                "type": "string",
                "description": "Relative wiki path, e.g. 'modules/visitor-management.md'",
            },
            "proposed_change": {
                "type": "string",
                "description": "What is incorrect and what it should say instead.",
            },
            "answer_id": {
                "type": "string",
                "description": "The answer_id this proposal is based on (optional).",
            },
        },
        "required": ["page_path", "proposed_change"],
    },
}


def _wiki_propose_edit_handler(inp: dict) -> dict:
    """Write a proposal to wiki_proposals.jsonl — never to wiki/."""
    from backend.wiki_proposals import create_proposal

    page_path = str(inp.get("page_path", "")).strip()
    proposed_change = str(inp.get("proposed_change", "")).strip()
    answer_id = inp.get("answer_id")

    if not page_path or not proposed_change:
        return {"error": "page_path and proposed_change are required", "code": "missing_fields"}

    proposal_id = create_proposal(
        page_path=page_path,
        proposed_change=proposed_change,
        submitter_email="agent",
        answer_id=answer_id,
    )
    return {
        "status": "submitted",
        "proposal_id": proposal_id,
        "message": (
            f"Proposal submitted for admin review. "
            f"The wiki page '{page_path}' has NOT been changed. "
            "An admin will review and apply or reject this proposal."
        ),
    }
```

- [ ] **Step 4: Add `wiki_propose_edit` to `_TOOL_PERMISSIONS` in `backend/tools/registry.py`**

In `backend/tools/registry.py`, update `_TOOL_PERMISSIONS`:

```python
_TOOL_PERMISSIONS: dict[str, str] = {
    "wiki_propose_edit": "contributor",   # viewer cannot propose edits
}
```

- [ ] **Step 5: Register `wiki_propose_edit` in `backend/tools/__init__.py`**

In `build_registry()`, add the registration (place with the other wiki tool registrations):

```python
from backend.tools.wiki_tools import (
    ...,  # existing imports
    WIKI_PROPOSE_EDIT_SCHEMA,
    _wiki_propose_edit_handler,
)

def build_registry(user_role: str = "viewer") -> ToolRegistry:
    r = ToolRegistry(user_role=user_role)
    # ... existing registrations ...
    r.register(WIKI_PROPOSE_EDIT_SCHEMA, _wiki_propose_edit_handler)
    return r
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
venv/bin/pytest tests/test_tools.py tests/test_wiki_proposals.py -v
```

Expected: all tests pass. Note: `test_registry_loads_all_tools` will fail because it now expects 10 tools instead of 9. Update it:

```python
def test_registry_loads_all_tools():
    registry = build_registry(user_role="contributor")  # contributor sees wiki_propose_edit
    names = {s["name"] for s in registry.schemas}
    expected = {
        "wiki_search", "wiki_read_page",
        "jira_search_ranked", "jira_get_ticket", "jira_named_query",
        "pms_default_properties", "pms_runtime_values",
        "config_lookup",
        "feedback_record",
        "wiki_propose_edit",
    }
    assert names == expected, f"Missing tools: {expected - names}"
```

- [ ] **Step 7: Commit**

```bash
git add backend/tools/wiki_tools.py backend/tools/registry.py backend/tools/__init__.py tests/test_tools.py
git commit -m "feat(tools): add wiki_propose_edit tool — writes to JSONL, blocked for viewer role"
```

---

## Task 3: Admin endpoints for wiki proposal queue

**Files:**
- Modify: `backend/admin_api.py`
- Modify: `backend/api.py`

- [ ] **Step 1: Add wiki proposal functions to `backend/admin_api.py`**

Add these functions to `backend/admin_api.py`:

```python
def get_wiki_proposals(status: str | None = None) -> list[dict]:
    from backend.wiki_proposals import list_proposals
    return list_proposals(status=status)


def apply_wiki_proposal(proposal_id: str) -> dict:
    """Apply a wiki proposal: run apply_feedback if answer_id exists, then mark applied."""
    from backend.wiki_proposals import get_proposal, update_status
    from backend import wiki_retriever

    proposal = get_proposal(proposal_id)
    if not proposal:
        return {"success": False, "error": f"Proposal not found: {proposal_id}"}

    result: dict = {"proposal_id": proposal_id}

    # If there's a linked feedback answer, run apply_feedback.py
    answer_id = proposal.get("answer_id")
    if answer_id:
        try:
            proc = subprocess.run(
                [_PYTHON, str(_SCRIPTS / "apply_feedback.py"),
                 "--feedback-id", answer_id, "--apply"],
                capture_output=True, text=True, timeout=60, cwd=str(ROOT),
            )
            result["apply_output"] = proc.stdout
            result["apply_errors"] = proc.stderr
            result["apply_success"] = proc.returncode == 0
        except subprocess.TimeoutExpired:
            result["apply_success"] = False
            result["apply_errors"] = "apply_feedback.py timed out"
    else:
        result["apply_success"] = True
        result["apply_output"] = "No linked answer_id — proposal marked applied without patch"

    # Rebuild wiki index regardless
    wiki_retriever.rebuild_index()

    update_status(proposal_id, "applied")
    result["success"] = True
    return result


def reject_wiki_proposal(proposal_id: str, admin_note: str = "") -> dict:
    from backend.wiki_proposals import update_status
    found = update_status(proposal_id, "rejected", admin_note=admin_note)
    if not found:
        return {"success": False, "error": f"Proposal not found: {proposal_id}"}
    return {"success": True, "proposal_id": proposal_id, "status": "rejected"}


def trigger_drive_sync() -> dict:
    """Run sync_drive.py as a background subprocess."""
    drive_staging = ROOT / "raw" / "_drive_staging"
    drive_staging.mkdir(parents=True, exist_ok=True)
    try:
        proc = subprocess.Popen(
            [_PYTHON, str(_SCRIPTS / "sync_drive.py"),
             "--source", str(drive_staging)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=str(ROOT),
        )
        return {"status": "started", "pid": proc.pid}
    except Exception as exc:
        return {"status": "error", "message": str(exc)}
```

- [ ] **Step 2: Add API endpoints to `backend/api.py`**

Add these endpoints (with the other admin endpoints):

```python
class WikiProposalRejectRequest(BaseModel):
    admin_note: str = ""


@app.get("/admin/wiki/proposals")
def admin_list_wiki_proposals(
    status: str | None = None,
    _admin: dict = Depends(_require_admin),
):
    return {"proposals": admin_api.get_wiki_proposals(status=status)}


@app.post("/admin/wiki/proposals/{proposal_id}/apply")
def admin_apply_wiki_proposal(
    proposal_id: str,
    _admin: dict = Depends(_require_admin),
):
    result = admin_api.apply_wiki_proposal(proposal_id)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", "Apply failed"))
    return result


@app.post("/admin/wiki/proposals/{proposal_id}/reject")
def admin_reject_wiki_proposal(
    proposal_id: str,
    req: WikiProposalRejectRequest,
    _admin: dict = Depends(_require_admin),
):
    result = admin_api.reject_wiki_proposal(proposal_id, admin_note=req.admin_note)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", "Reject failed"))
    return result


@app.post("/admin/trigger-drive-sync")
def trigger_drive_sync(_admin: dict = Depends(_require_admin)):
    return admin_api.trigger_drive_sync()
```

- [ ] **Step 3: Run full test suite**

```bash
venv/bin/pytest tests/ -v -q
```

Expected: all tests pass

- [ ] **Step 4: Commit**

```bash
git add backend/admin_api.py backend/api.py
git commit -m "feat(admin): wiki proposal apply/reject endpoints + drive sync trigger"
```

---

## Task 4: VM cron setup

**Files:**
- Create: `deploy/crontab.example`

- [ ] **Step 1: Create `deploy/crontab.example`**

```
# Conwo VM crontab — deploy/crontab.example
# Install with: crontab -e  and paste these lines.
# Replace /opt/conwo with actual deploy path.
# Jira sync credentials must be set in /opt/conwo/.env or as system env vars.
# Google Drive rclone must be configured: rclone config (run once as deploy user).

# Jira incremental sync — daily at 02:00 UTC
0 2 * * * cd /opt/conwo && ./venv/bin/python scripts/jira_sync.py --incremental >> /var/log/conwo/jira-sync.log 2>&1

# Drive staging pull — daily at 03:00 UTC (rclone must be configured)
0 3 * * * cd /opt/conwo && rclone sync "gdrive:Conwo WorkInSync Docs" ./raw/_drive_staging/ >> /var/log/conwo/drive-staging.log 2>&1 && ./venv/bin/python scripts/sync_drive.py --source ./raw/_drive_staging >> /var/log/conwo/drive-sync.log 2>&1

# Log rotation — keep last 30 days
0 4 * * * find /var/log/conwo -name "*.log" -mtime +30 -delete
```

- [ ] **Step 2: Create log directory on VM**

Run this on the deployment VM (not in the repo):

```bash
sudo mkdir -p /var/log/conwo
sudo chown $(whoami):$(whoami) /var/log/conwo
```

- [ ] **Step 3: Install crontab on VM**

Run this on the deployment VM:

```bash
crontab -e
# Paste the contents of deploy/crontab.example
# Save and exit

# Verify it was installed:
crontab -l
```

- [ ] **Step 4: Verify crons run**

After the next scheduled time, check:

```bash
tail -20 /var/log/conwo/jira-sync.log
tail -20 /var/log/conwo/drive-sync.log
```

Expected: logs show "sync complete" and timestamp within last 24h.

- [ ] **Step 5: Commit**

```bash
git add deploy/crontab.example
git commit -m "ops(deploy): crontab.example for daily Jira + Drive sync on deployment VM"
```

---

## Task 5: Security checklist + final verification

- [ ] **Step 1: Verify `wiki_propose_edit` never writes to `wiki/`**

```bash
venv/bin/pytest tests/test_wiki_proposals.py::test_proposal_never_writes_to_wiki_dir -v
```

Expected: PASS

- [ ] **Step 2: Verify `crontab.example` has no real credentials**

```bash
grep -iE "(token|password|secret|key\s*=)" deploy/crontab.example
```

Expected: no output (no credentials in the file)

- [ ] **Step 3: Run full test suite**

```bash
venv/bin/pytest tests/ -v
```

Expected: all tests pass

- [ ] **Step 4: Smoke test — submit a proposal via tool and verify admin can see it**

```bash
# Start backend
uvicorn backend.api:app --reload --port 8000 &

# Contributor submits a question (the tool loop may invoke wiki_propose_edit internally)
# Or test directly via the proposals API:
curl -s -X GET http://localhost:8000/admin/wiki/proposals \
  -H "Authorization: Bearer <ADMIN_TOKEN>"
# Expected: {"proposals": []}

# Manually create a proposal (to test the admin queue)
python -c "
from backend.wiki_proposals import create_proposal
pid = create_proposal('modules/visitor-management.md', 'Test correction', 'test@example.com')
print('Created proposal:', pid)
"

# Verify admin can see it
curl -s -X GET http://localhost:8000/admin/wiki/proposals \
  -H "Authorization: Bearer <ADMIN_TOKEN>" | python -m json.tool
# Expected: proposal appears with status "pending"
```

- [ ] **Step 5: Final Layer 3 commit**

```bash
git add -A
git commit -m "feat(layer3): Layer 3 complete — sync automation + wiki edit approval queue"
```

---

## Post-Layer 3 — Eval Set Verification

Run the 20-question eval set from the spec to confirm the full system works end-to-end before the internal pilot. See `docs/superpowers/specs/2026-05-21-conwo-multi-user-api-design.md` § 9 for the full question list.

Key questions that exercise Layer 3 specifically:
- **Question 17** ("Has there been any recent change to how kiosk OTP works?") — exercises `wiki_propose_edit` if tool finds a Jira contradiction with wiki content
- **Question 20** (multi-turn: visitor management → OTP follow-up) — exercises conversation threading from Layer 2

For each question, record:
- [ ] Answer received (not empty, not error)
- [ ] Confidence field present (High / Medium / Low)
- [ ] Sources cited (at least one wiki path or Jira key)
- [ ] No `permission_denied` errors in tool_trace for standard viewer queries
