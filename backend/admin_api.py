"""
Admin API logic — sync status, ingest queue, feedback management, patch apply.
All functions here are called only from authenticated admin endpoints in api.py.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from backend.config import (
    FEEDBACK_LOG,
    JIRA_DB,
    JIRA_SYNC_LOG,
    RAW_DIR,
    ROOT,
    SYNC_MANIFEST,
)
from backend.feedback_service import list_feedback, resolve_feedback

_SCRIPTS = ROOT / "scripts"
_PYTHON = sys.executable  # use the same interpreter that's running the backend


def get_sync_status() -> dict:
    """Return last sync timestamps and counts for the admin dashboard."""
    result: dict = {}

    # Jira sync
    jira_last_sync = ""
    jira_ticket_count = 0
    if JIRA_SYNC_LOG.exists():
        lines = JIRA_SYNC_LOG.read_text(encoding="utf-8", errors="replace").splitlines()
        for line in reversed(lines):
            if "sync complete" in line.lower() or "tickets" in line.lower():
                jira_last_sync = line.strip()
                break
    if JIRA_DB.exists():
        import sqlite3
        try:
            conn = sqlite3.connect(f"file:{JIRA_DB}?mode=ro", uri=True)
            jira_ticket_count = conn.execute("SELECT COUNT(*) FROM tickets").fetchone()[0]
            conn.close()
        except Exception:
            pass
    result["jira"] = {"last_sync_line": jira_last_sync, "ticket_count": jira_ticket_count}

    # Drive sync manifest
    drive_last_sync = ""
    drive_file_count = 0
    if SYNC_MANIFEST.exists():
        try:
            manifest = json.loads(SYNC_MANIFEST.read_text(encoding="utf-8"))
            drive_last_sync = manifest.get("synced_at", "")
            drive_file_count = len(manifest.get("files", {}))
        except Exception:
            pass
    result["drive"] = {"last_sync": drive_last_sync, "file_count": drive_file_count}

    # Feedback
    pending_feedback = list_feedback(status="pending")
    result["feedback"] = {"pending_count": len(pending_feedback)}

    return result


def get_ingest_queue() -> list[dict]:
    """Run audit_ingest.py and return the list of unprocessed files."""
    try:
        proc = subprocess.run(
            [_PYTHON, str(_SCRIPTS / "audit_ingest.py")],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(ROOT),
        )
        output = proc.stdout
        items: list[dict] = []
        # Parse lines like "    - filename.docx"
        current_module: str = ""
        for line in output.splitlines():
            if line.startswith("  ["):
                current_module = line.strip().strip("[]")
            elif line.strip().startswith("- ") and "raw/" in line:
                # Extract the path from lines like "      (raw/modules/.../file.docx)"
                path_match = line.strip().strip("()")
                if path_match.startswith("raw/"):
                    items.append({"module": current_module, "path": path_match})
        return items
    except subprocess.TimeoutExpired:
        return [{"error": "audit_ingest.py timed out"}]
    except Exception as exc:
        return [{"error": str(exc)}]


def trigger_jira_sync() -> dict:
    """Run jira_sync.py --incremental as a background subprocess."""
    try:
        proc = subprocess.Popen(
            [_PYTHON, str(_SCRIPTS / "jira_sync.py"), "--incremental"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=str(ROOT),
        )
        return {"status": "started", "pid": proc.pid}
    except Exception as exc:
        return {"status": "error", "message": str(exc)}


def get_feedback_list(status: str = "pending", limit: int = 50) -> list[dict]:
    return list_feedback(status=status, limit=limit)


def get_patch_plan(feedback_id: str) -> dict:
    """Run apply_feedback.py --dry-run for a specific feedback_id."""
    try:
        proc = subprocess.run(
            [
                _PYTHON,
                str(_SCRIPTS / "apply_feedback.py"),
                "--feedback-id", feedback_id,
            ],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(ROOT),
        )
        return {
            "feedback_id": feedback_id,
            "plan": proc.stdout,
            "errors": proc.stderr,
            "dry_run": True,
        }
    except subprocess.TimeoutExpired:
        return {"error": "apply_feedback.py timed out", "dry_run": True}
    except Exception as exc:
        return {"error": str(exc), "dry_run": True}


def apply_patch(feedback_id: str) -> dict:
    """Run apply_feedback.py --apply for a specific feedback_id."""
    try:
        proc = subprocess.run(
            [
                _PYTHON,
                str(_SCRIPTS / "apply_feedback.py"),
                "--feedback-id", feedback_id,
                "--apply",
            ],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(ROOT),
        )
        success = proc.returncode == 0
        if success:
            # Invalidate wiki index so the patched page is re-indexed
            from backend import wiki_retriever
            wiki_retriever.rebuild_index()
        return {
            "feedback_id": feedback_id,
            "success": success,
            "output": proc.stdout,
            "errors": proc.stderr,
        }
    except subprocess.TimeoutExpired:
        return {"feedback_id": feedback_id, "success": False, "error": "apply timed out"}
    except Exception as exc:
        return {"feedback_id": feedback_id, "success": False, "error": str(exc)}


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
