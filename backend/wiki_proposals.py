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
