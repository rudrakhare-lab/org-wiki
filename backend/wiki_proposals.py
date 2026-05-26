"""
Wiki edit proposal store — JSONL-backed, typed proposals (Track A).

Proposals live in raw/feedback/wiki_proposals.jsonl. One JSON object per line,
appended on create, full-rewrite on status update (no locking — single-writer
assumption matches pilot scale; multi-process safety is out of scope).

This module NEVER writes to wiki/. The proposal queue is the source of truth
until the admin apply endpoint (admin_api.apply_wiki_proposal, closed in
Sub-pass C / G07) reads a proposal and writes the change to disk.

Proposal types:
  - "new"          → page_path, content
  - "edit"         → page_path, old_string, new_string
  - "append"       → page_path, content
  - "multi_edit"   → edits: list[{path, old_string, new_string}]
  - "legacy_text"  → page_path, proposed_change (pre-Track-A free-text shape)

All proposals share base fields: id, submitter_email, answer_id, reason,
validation_log, suggested_companion_edit, status, admin_note, created_at,
resolved_at, applied_at, applied_by.

Legacy records (pre-Track-A) lack `proposal_type`. They are normalized to
"legacy_text" on load so consumers see a consistent shape.
"""
from __future__ import annotations

import json
import logging
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.config import FEEDBACK_DIR

PROPOSALS_FILE = FEEDBACK_DIR / "wiki_proposals.jsonl"

_log = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _new_id() -> str:
    return "prop_" + secrets.token_hex(6)


def _normalize(record: dict[str, Any]) -> dict[str, Any]:
    """Add proposal_type='legacy_text' to records that predate Track A."""
    if "proposal_type" not in record:
        record["proposal_type"] = "legacy_text"
    record.setdefault("applied_at", None)
    record.setdefault("applied_by", None)
    record.setdefault("validation_log", [])
    record.setdefault("suggested_companion_edit", None)
    record.setdefault("reason", "")
    return record


def _load_all() -> list[dict[str, Any]]:
    if not PROPOSALS_FILE.exists():
        return []
    proposals = []
    for line in PROPOSALS_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            proposals.append(_normalize(json.loads(line)))
        except json.JSONDecodeError:
            pass
    return proposals


def _save_all(proposals: list[dict[str, Any]]) -> None:
    FEEDBACK_DIR.mkdir(parents=True, exist_ok=True)
    PROPOSALS_FILE.write_text(
        "\n".join(json.dumps(p, ensure_ascii=False) for p in proposals) + "\n",
        encoding="utf-8",
    )


def _append_record(proposal: dict[str, Any]) -> None:
    """Append a single proposal line — preferred over _save_all for new
    records to minimize the read-modify-write race window."""
    FEEDBACK_DIR.mkdir(parents=True, exist_ok=True)
    with PROPOSALS_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(proposal, ensure_ascii=False) + "\n")


def _base_proposal(
    submitter_email: str,
    answer_id: str | None,
    reason: str,
    validation_log: list[str] | None,
    suggested_companion_edit: dict | None,
) -> dict[str, Any]:
    return {
        "id": _new_id(),
        "submitter_email": submitter_email,
        "answer_id": answer_id,
        "reason": reason or "",
        "validation_log": list(validation_log or []),
        "suggested_companion_edit": suggested_companion_edit,
        "status": "pending",
        "admin_note": None,
        "created_at": _now(),
        "resolved_at": None,
        "applied_at": None,
        "applied_by": None,
    }


# ── Typed creators (Track A) ──────────────────────────────────────────────────

def create_new_proposal(
    page_path: str,
    content: str,
    submitter_email: str,
    reason: str = "",
    answer_id: str | None = None,
    validation_log: list[str] | None = None,
) -> str:
    proposal = _base_proposal(submitter_email, answer_id, reason, validation_log, None)
    proposal.update({
        "proposal_type": "new",
        "page_path": page_path,
        "content": content,
    })
    _append_record(proposal)
    return proposal["id"]


def create_edit_proposal(
    page_path: str,
    old_string: str,
    new_string: str,
    submitter_email: str,
    reason: str = "",
    answer_id: str | None = None,
    suggested_companion_edit: dict | None = None,
    validation_log: list[str] | None = None,
) -> str:
    proposal = _base_proposal(
        submitter_email, answer_id, reason, validation_log, suggested_companion_edit,
    )
    proposal.update({
        "proposal_type": "edit",
        "page_path": page_path,
        "old_string": old_string,
        "new_string": new_string,
    })
    _append_record(proposal)
    return proposal["id"]


def create_append_proposal(
    page_path: str,
    content: str,
    submitter_email: str,
    reason: str = "",
    answer_id: str | None = None,
    validation_log: list[str] | None = None,
) -> str:
    proposal = _base_proposal(submitter_email, answer_id, reason, validation_log, None)
    proposal.update({
        "proposal_type": "append",
        "page_path": page_path,
        "content": content,
    })
    _append_record(proposal)
    return proposal["id"]


def create_multi_edit_proposal(
    edits: list[dict],
    submitter_email: str,
    reason: str = "",
    answer_id: str | None = None,
    suggested_companion_edit: dict | None = None,
    validation_log: list[str] | None = None,
) -> str:
    proposal = _base_proposal(
        submitter_email, answer_id, reason, validation_log, suggested_companion_edit,
    )
    proposal.update({
        "proposal_type": "multi_edit",
        "edits": [dict(e) for e in edits],  # defensive copy
    })
    _append_record(proposal)
    return proposal["id"]


# ── Legacy creator (preserved for migration / tests) ──────────────────────────

def create_proposal(
    page_path: str,
    proposed_change: str,
    submitter_email: str,
    answer_id: str | None = None,
) -> str:
    """LEGACY free-text proposal (pre-Track-A shape). Kept for any caller that
    hasn't migrated. New code should use create_edit_proposal() instead with
    structured old_string/new_string fields. Tagged as 'legacy_text' so the
    new apply handler in Sub-pass C can refuse to apply automatically."""
    proposal = _base_proposal(submitter_email, answer_id, "", None, None)
    proposal.update({
        "proposal_type": "legacy_text",
        "page_path": page_path,
        "proposed_change": proposed_change,
    })
    _append_record(proposal)
    return proposal["id"]


# ── Read / update ─────────────────────────────────────────────────────────────

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
    applied_by: str | None = None,
) -> bool:
    """Update a proposal's status. When status='applied' and applied_by is
    provided, also stamps applied_at + applied_by. Sub-pass C's admin apply
    handler will use the applied_by path; the existing (pre-Sub-pass-C)
    apply path won't set it, and that's intentional — closing G07 is a
    later pass."""
    proposals = _load_all()
    found = False
    for p in proposals:
        if p.get("id") == proposal_id:
            p["status"] = status
            p["admin_note"] = admin_note
            p["resolved_at"] = _now()
            if status == "applied":
                p["applied_at"] = _now()
                if applied_by:
                    p["applied_by"] = applied_by
            found = True
            break
    if found:
        _save_all(proposals)
    return found


# ── Startup hooks ─────────────────────────────────────────────────────────────

def count_legacy_pending() -> int:
    """Return count of pending proposals with proposal_type='legacy_text'.
    Called at server startup to log a WARN so admins know to drain them."""
    return sum(
        1 for p in _load_all()
        if p.get("proposal_type") == "legacy_text" and p.get("status") == "pending"
    )


def warn_if_legacy_pending() -> int:
    """Log a WARN if any legacy_text proposals are pending. Returns the count
    so callers can also surface it elsewhere (e.g., admin dashboard)."""
    n = count_legacy_pending()
    if n > 0:
        _log.warning(
            "%d legacy_text wiki proposals are pending. These cannot be applied "
            "automatically by the new admin endpoint — drain via the admin UI "
            "(manual edit + mark resolved) or migrate to structured proposals.",
            n,
        )
    return n
