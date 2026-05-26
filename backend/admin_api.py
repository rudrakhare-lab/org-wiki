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
    """Return last sync timestamps and counts for the admin dashboard.

    Parses JIRA_SYNC_LOG as JSON-per-line (jira_sync.py's actual format).
    Returns both the most recent log line of any kind (for debugging) AND
    the timestamp of the most recent SUCCESSFUL completion (msg starts
    with "ALL DONE:") — the latter is what operational_context uses to
    decide stale-mirror warnings. G31 closure.
    """
    result: dict = {}

    jira_last_log_line = ""
    jira_most_recent_successful_sync = ""  # ISO timestamp, empty if none found
    jira_ticket_count = 0

    if JIRA_SYNC_LOG.exists():
        lines = JIRA_SYNC_LOG.read_text(encoding="utf-8", errors="replace").splitlines()
        for line in reversed(lines):
            stripped = line.strip()
            if not stripped:
                continue
            if not jira_last_log_line:
                jira_last_log_line = stripped
            if jira_most_recent_successful_sync:
                # Already found the success timestamp; still need to find the
                # last-of-any-kind line (handled above). If we have both, stop.
                if jira_last_log_line:
                    break
                continue
            try:
                obj = json.loads(stripped)
            except (json.JSONDecodeError, ValueError):
                continue
            if (
                isinstance(obj, dict)
                and obj.get("level") == "INFO"
                and isinstance(obj.get("msg"), str)
                and obj["msg"].startswith("ALL DONE:")
            ):
                jira_most_recent_successful_sync = str(obj.get("ts", ""))

    if JIRA_DB.exists():
        import sqlite3
        try:
            conn = sqlite3.connect(f"file:{JIRA_DB}?mode=ro", uri=True)
            jira_ticket_count = conn.execute("SELECT COUNT(*) FROM tickets").fetchone()[0]
            conn.close()
        except Exception:
            pass

    result["jira"] = {
        "last_log_line": jira_last_log_line,
        "most_recent_successful_sync": jira_most_recent_successful_sync,
        # Backwards-compat alias for callers that read the field name from G04.
        "last_sync_line": jira_last_log_line,
        "ticket_count": jira_ticket_count,
    }

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
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
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


def apply_wiki_proposal(proposal_id: str, applied_by: str = "admin") -> dict:
    """Apply a typed wiki proposal. Track A Sub-pass C closes G07/G14/G16.

    Dispatches on proposal.proposal_type:
      - "new"        → wiki_apply.apply_new (write new file under flock)
      - "edit"       → wiki_apply.apply_edit (str_replace with re-validation)
      - "append"     → wiki_apply.apply_append (append to existing file)
      - "multi_edit" → wiki_apply.apply_multi_edit (atomic multi-file w/ rollback)
      - "legacy_text"→ refuse — admin must use /mark-applied after manual edit

    Idempotency: if the proposal is already "applied", returns success without
    re-writing.

    After a successful write:
      - rebuild_index() so subsequent searches see the new content
      - mark proposal "applied" with applied_at and applied_by stamps
    """
    from backend.wiki_proposals import get_proposal, update_status
    from backend import wiki_apply, wiki_retriever

    proposal = get_proposal(proposal_id)
    if not proposal:
        return {
            "success": False,
            "code": "not_found",
            "message": f"Proposal not found: {proposal_id}",
            "proposal_id": proposal_id,
        }

    # Idempotency — already-applied proposals return success without re-writing.
    if proposal.get("status") == "applied":
        return {
            "success": True,
            "code": "already_applied",
            "message": "Proposal was previously applied; no work done now.",
            "proposal_id": proposal_id,
            "proposal": proposal,
            "files_written": [],
        }

    pt = proposal.get("proposal_type", "legacy_text")
    if pt == "new":
        result = wiki_apply.apply_new(proposal)
    elif pt == "edit":
        result = wiki_apply.apply_edit(proposal)
    elif pt == "append":
        result = wiki_apply.apply_append(proposal)
    elif pt == "multi_edit":
        result = wiki_apply.apply_multi_edit(proposal)
    elif pt == "legacy_text":
        result = wiki_apply.refuse_legacy_text(proposal)
    else:
        result = {
            "success": False,
            "code": "unknown_proposal_type",
            "message": f"Unknown proposal_type: {pt!r}",
        }

    result["proposal_id"] = proposal_id
    result["proposal_type"] = pt

    if not result.get("success"):
        # Surface companion edit advisory even on failure — the admin may want to
        # see what would have been suggested. Skip for refused legacy text.
        if pt != "legacy_text":
            result["suggested_companion_edit"] = proposal.get("suggested_companion_edit")
        return result

    # Rebuild index — failure here does NOT undo the write, but is logged on the result.
    try:
        wiki_retriever.rebuild_index()
        result["index_rebuilt"] = True
    except Exception as exc:
        result["index_rebuilt"] = False
        result["index_error"] = str(exc)

    update_status(proposal_id, "applied", applied_by=applied_by)
    # Reload to surface the updated record with applied_at/applied_by stamps
    result["proposal"] = get_proposal(proposal_id)
    result["suggested_companion_edit"] = proposal.get("suggested_companion_edit")
    return result


def mark_wiki_proposal_applied(proposal_id: str, applied_by: str = "admin") -> dict:
    """Mark a LEGACY_TEXT proposal as applied without invoking any writer.

    Used after an admin has manually edited the wiki to honor a pre-Track-A
    free-text proposal. Refuses (400) if called on a structured proposal —
    those should use /apply, not /mark-applied.
    """
    from backend.wiki_proposals import get_proposal, update_status

    proposal = get_proposal(proposal_id)
    if not proposal:
        return {
            "success": False,
            "code": "not_found",
            "message": f"Proposal not found: {proposal_id}",
        }
    pt = proposal.get("proposal_type", "legacy_text")
    if pt != "legacy_text":
        return {
            "success": False,
            "code": "not_legacy_text",
            "message": (
                f"Proposal {proposal_id} is type {pt!r}, not 'legacy_text'. "
                f"Structured proposals must use /apply, which dispatches to a writer."
            ),
        }
    if proposal.get("status") == "applied":
        return {
            "success": True,
            "code": "already_applied",
            "message": "Already marked applied.",
            "proposal": proposal,
        }
    update_status(proposal_id, "applied", applied_by=applied_by)
    # The admin's manual edit needs to be reflected in the in-memory index so
    # subsequent searches see the change. Defensive try/except — an index
    # failure is logged on the result but does NOT undo the status stamp.
    result: dict = {
        "success": True,
        "message": f"Marked legacy_text proposal {proposal_id} as applied.",
        "proposal": get_proposal(proposal_id),
    }
    try:
        from backend import wiki_retriever
        wiki_retriever.rebuild_index()
        result["index_rebuilt"] = True
    except Exception as exc:
        result["index_rebuilt"] = False
        result["index_error"] = str(exc)
    return result


def reject_wiki_proposal(proposal_id: str, admin_note: str | None = None) -> dict:
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
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=str(ROOT),
        )
        return {"status": "started", "pid": proc.pid}
    except Exception as exc:
        return {"status": "error", "message": str(exc)}
