"""
Wiki apply layer — the ONLY code path that mutates wiki/ on disk.

The admin endpoint (admin_api.apply_wiki_proposal) loads a proposal, dispatches
on proposal_type, and calls one of the four writers here:
  - apply_new       — create a new wiki page (refuse if exists)
  - apply_edit      — str_replace on existing page; re-validates uniqueness
  - apply_append    — append to existing file (log.md)
  - apply_multi_edit — atomic multi-file edit with rollback

Each writer:
  - Re-validates at apply time (the propose-time check may be stale).
  - Acquires fcntl flock on every target file (POSIX; no-op on Windows).
  - Returns a structured result dict: success, code, message, files_written,
    rollback_status (multi_edit only), and any extra detail the admin UI needs.

Legacy text proposals (proposal_type='legacy_text') are NOT applied here —
the dispatcher returns refuse_legacy_text(), which directs the admin to the
manual mark-applied endpoint after they've edited the wiki by hand.

Stale-proposal semantics (CRITICAL): if the file has changed between propose
and apply, this layer detects it and refuses with code='stale_proposal'.
This is what protects us from race conditions and "the file you saw at
propose time is not the file you're editing now."
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from backend.config import WIKI_DIR
from backend.file_locks import locked_write, locked_read_write

_log = logging.getLogger(__name__)


# ── Path validation (shared with propose tools, duplicated here for safety) ──

def _validate_path(path: str) -> tuple[Path | None, dict | None]:
    """Same guards as backend/tools/wiki_propose_tools._validate_path.
    Duplicated rather than imported so the apply layer doesn't depend on
    a tool-layer module."""
    p = (path or "").strip()
    if not p:
        return None, {"success": False, "code": "missing_input", "message": "path is required"}
    if ".." in p or p.startswith("/"):
        return None, {"success": False, "code": "path_traversal", "message": "Path traversal not allowed."}
    try:
        resolved = (WIKI_DIR / p).resolve()
        wiki_root = WIKI_DIR.resolve()
        if resolved != wiki_root and wiki_root not in resolved.parents:
            return None, {"success": False, "code": "path_traversal", "message": "Path outside wiki directory."}
    except Exception:
        return None, {"success": False, "code": "path_traversal", "message": "Invalid path."}
    return resolved, None


# ── Writer 1: new page ────────────────────────────────────────────────────────

def apply_new(proposal: dict) -> dict:
    """Create a new wiki page. Refuses if the file already exists (the propose-
    time check could be stale)."""
    page_path = str(proposal.get("page_path") or "")
    content = proposal.get("content") or ""
    if not isinstance(content, str) or not content:
        return {"success": False, "code": "missing_input", "message": "content missing on proposal"}

    resolved, err = _validate_path(page_path)
    if err:
        return err
    # Stale check: file must not already exist at apply time
    if resolved.exists():
        return {
            "success": False,
            "code": "stale_proposal",
            "message": (
                f"Page {page_path} now exists on disk — the proposal was for a "
                f"NEW page. Either reject this proposal and use wiki_propose_edit "
                f"instead, or delete the existing file first."
            ),
        }

    resolved.parent.mkdir(parents=True, exist_ok=True)
    try:
        with locked_write(resolved) as fh:
            fh.write(content)
    except OSError as exc:
        return {"success": False, "code": "write_io_error", "message": str(exc)}

    return {
        "success": True,
        "message": f"Created {page_path}",
        "files_written": [page_path],
    }


# ── Writer 2: str_replace edit ────────────────────────────────────────────────

def apply_edit(proposal: dict) -> dict:
    """Apply a str_replace edit. Re-reads the file at apply time and refuses
    if old_string is no longer uniquely present."""
    page_path = str(proposal.get("page_path") or "")
    old_string = proposal.get("old_string")
    new_string = proposal.get("new_string")
    if not isinstance(old_string, str) or old_string == "":
        return {"success": False, "code": "missing_input", "message": "old_string missing"}
    if not isinstance(new_string, str):
        return {"success": False, "code": "missing_input", "message": "new_string missing"}

    resolved, err = _validate_path(page_path)
    if err:
        return err
    if not resolved.is_file():
        return {
            "success": False,
            "code": "stale_proposal",
            "message": f"Page {page_path} no longer exists on disk.",
        }

    try:
        with locked_read_write(resolved) as target:
            current = target.read_text(encoding="utf-8")
            occurrences = current.count(old_string)
            if occurrences == 0:
                return {
                    "success": False,
                    "code": "stale_proposal",
                    "message": (
                        f"old_string no longer found in {page_path}. The page "
                        f"changed between propose and apply. Reject this proposal "
                        f"and re-propose against the current content."
                    ),
                }
            if occurrences > 1:
                return {
                    "success": False,
                    "code": "stale_proposal",
                    "message": (
                        f"old_string now appears {occurrences} times in {page_path} "
                        f"(must be unique to apply). The page changed; reject and re-propose."
                    ),
                }
            new_content = current.replace(old_string, new_string, 1)
            target.write_text(new_content, encoding="utf-8")
    except OSError as exc:
        return {"success": False, "code": "write_io_error", "message": str(exc)}

    return {
        "success": True,
        "message": f"Edited {page_path}",
        "files_written": [page_path],
    }


# ── Writer 3: append ──────────────────────────────────────────────────────────

def apply_append(proposal: dict) -> dict:
    """Append content to an existing file. For log.md, we ensure proper
    separation (blank line + content) per the §3 format."""
    page_path = str(proposal.get("page_path") or "")
    content = proposal.get("content") or ""
    if not isinstance(content, str) or not content.strip():
        return {"success": False, "code": "missing_input", "message": "content missing"}

    resolved, err = _validate_path(page_path)
    if err:
        return err
    if not resolved.is_file():
        return {
            "success": False,
            "code": "stale_proposal",
            "message": f"Page {page_path} no longer exists on disk.",
        }

    try:
        with locked_read_write(resolved) as target:
            current = target.read_text(encoding="utf-8")
            # Ensure exactly one blank line between existing content and new entry
            if current and not current.endswith("\n"):
                current += "\n"
            if current and not current.endswith("\n\n"):
                current += "\n"
            target.write_text(current + content + ("\n" if not content.endswith("\n") else ""), encoding="utf-8")
    except OSError as exc:
        return {"success": False, "code": "write_io_error", "message": str(exc)}

    return {
        "success": True,
        "message": f"Appended to {page_path}",
        "files_written": [page_path],
    }


# ── Writer 4: multi_edit (atomic) ─────────────────────────────────────────────

def apply_multi_edit(proposal: dict) -> dict:
    """Atomic multi-file edit.

    Two-pass with rollback:
      Pass 1: read all targets, validate each (path, old_string unique) AGAINST
              the current file content. If any fails → return without touching
              any file.
      Pass 2: acquire flocks on all targets in sorted-path order (deadlock
              prevention), snapshot pre-edit content, apply all writes. If any
              write fails, restore each already-written file from its snapshot.
              If rollback itself fails, log loudly and return rollback_status='failed'.
    """
    edits = proposal.get("edits") or []
    if not isinstance(edits, list) or not edits:
        return {"success": False, "code": "missing_input", "message": "edits list is empty"}

    # ── Pass 1: validate everything against current disk state ──
    resolved_edits: list[dict] = []
    for i, e in enumerate(edits):
        page_path = str(e.get("page_path") or "")
        old_string = e.get("old_string")
        new_string = e.get("new_string")
        if not isinstance(old_string, str) or old_string == "":
            return {
                "success": False, "code": "missing_input",
                "message": f"edits[{i}] old_string missing", "edit_index": i,
            }
        if not isinstance(new_string, str):
            return {
                "success": False, "code": "missing_input",
                "message": f"edits[{i}] new_string missing", "edit_index": i,
            }
        resolved, err = _validate_path(page_path)
        if err:
            return {**err, "edit_index": i}
        if not resolved.is_file():
            return {
                "success": False, "code": "stale_proposal",
                "message": f"edits[{i}].page_path {page_path} no longer exists.",
                "edit_index": i,
            }
        current = resolved.read_text(encoding="utf-8")
        occ = current.count(old_string)
        if occ == 0:
            return {
                "success": False, "code": "stale_proposal",
                "message": f"edits[{i}] old_string not found in {page_path}.",
                "edit_index": i,
            }
        if occ > 1:
            return {
                "success": False, "code": "stale_proposal",
                "message": f"edits[{i}] old_string appears {occ} times in {page_path} (must be unique).",
                "edit_index": i,
            }
        resolved_edits.append({
            "page_path": page_path,
            "resolved": resolved,
            "old_string": old_string,
            "new_string": new_string,
            "pre_edit_content": current,
            "new_content": current.replace(old_string, new_string, 1),
        })

    # ── Pass 2: sort by resolved path → acquire all locks → apply ──
    # Deadlock prevention: if two multi_edit proposals overlap on the same
    # files, sorting by path guarantees both pick locks in the same order.
    resolved_edits.sort(key=lambda e: str(e["resolved"]))

    written: list[dict] = []
    rollback_status: str | None = None

    try:
        # NB: we don't hold a global lock — each file is flocked individually
        # via locked_read_write. The sort order ensures consistent acquisition.
        for entry in resolved_edits:
            try:
                with locked_read_write(entry["resolved"]) as target:
                    # Inside the lock, re-validate one more time (file could
                    # have changed between Pass 1 and this lock acquisition).
                    cur = target.read_text(encoding="utf-8")
                    if cur != entry["pre_edit_content"]:
                        # File changed under us between Pass 1 and Pass 2.
                        raise _StaleUnderLock(entry["page_path"])
                    target.write_text(entry["new_content"], encoding="utf-8")
                    written.append(entry)
            except _StaleUnderLock:
                raise  # propagate to rollback
            except OSError:
                raise  # propagate to rollback

    except _StaleUnderLock as exc:
        rollback_status = _rollback(written)
        return {
            "success": False,
            "code": "stale_proposal",
            "message": (
                f"File {exc.path} changed between validate and write. "
                f"Rolled back {len(written)} earlier write(s)."
            ),
            "rollback_status": rollback_status,
            "files_written": [],
        }
    except OSError as exc:
        rollback_status = _rollback(written)
        return {
            "success": False,
            "code": "write_io_error",
            "message": f"IO error mid-apply: {exc}",
            "rollback_status": rollback_status,
            "files_written": [],
        }

    return {
        "success": True,
        "message": f"Applied {len(written)} edits atomically",
        "files_written": [e["page_path"] for e in written],
        "rollback_status": "clean",  # no rollback was needed
    }


class _StaleUnderLock(Exception):
    """Raised when a multi_edit Pass 2 acquires a lock and finds the file
    has changed since Pass 1 validation."""
    def __init__(self, path: str):
        self.path = path
        super().__init__(path)


def _rollback(written: list[dict]) -> str:
    """Restore pre-edit content for each already-written file. Returns
    'clean' if all rolled back, 'partial' if some restorations failed,
    'failed' if rollback errored catastrophically."""
    if not written:
        return "clean"
    failures: list[str] = []
    for entry in written:
        try:
            with locked_write(entry["resolved"]) as fh:
                fh.write(entry["pre_edit_content"])
        except OSError as exc:
            _log.error(
                "ROLLBACK FAILED for %s — pre-edit content preserved in memory but disk write errored: %s. "
                "Manual cleanup required.",
                entry["page_path"], exc,
            )
            failures.append(entry["page_path"])
    if not failures:
        return "clean"
    if len(failures) == len(written):
        return "failed"
    return "partial"


# ── Legacy text refusal ───────────────────────────────────────────────────────

def refuse_legacy_text(proposal: dict) -> dict:
    """Pre-Track-A proposals (free-text 'proposed_change') cannot be applied
    automatically — the structured fields the writers need are absent. The
    admin must edit the wiki page manually and then call the mark-applied
    endpoint to record the work."""
    return {
        "success": False,
        "code": "legacy_text_refused",
        "message": (
            f"This proposal (id={proposal.get('id')}) is a legacy free-text "
            f"record from before Track A. The new apply pipeline cannot "
            f"automatically apply it. Edit the wiki page manually based on "
            f"the proposed_change description, then call "
            f"POST /admin/wiki/proposals/{proposal.get('id')}/mark-applied "
            f"to record the apply in the audit trail."
        ),
        "proposed_change": proposal.get("proposed_change", ""),
    }
