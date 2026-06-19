"""Per-(user, agent) access control store.

The default agent (agent_registry.DEFAULT_AGENT_ID) is open to everyone and is
never stored here. Admins bypass all checks. For every other agent, a user needs
a row with status='granted'. Fail-closed: a store error denies non-default access
but never raises into the request path.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from backend import db, agent_registry

_log = logging.getLogger("agent_access")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def has_access(user: dict | None, agent_id: str) -> bool:
    """True if the user may use this agent. Default agent → always; admin → always;
    otherwise requires a granted row. Fail-closed on error."""
    if agent_id == agent_registry.DEFAULT_AGENT_ID:
        return True
    if user and user.get("role") == "admin":
        return True
    if not user or not user.get("email"):
        return False
    try:
        with db.connection() as conn:
            row = conn.execute(
                "SELECT 1 FROM agent_access "
                "WHERE user_email=%s AND agent_id=%s AND status='granted'",
                (user["email"], agent_id),
            ).fetchone()
            return row is not None
    except Exception as exc:
        _log.warning("agent_access.has_access failed (deny non-default): %s", exc)
        return False


def request_access(email: str, agent_id: str) -> dict:
    """Upsert a pending request. Never downgrades an existing grant."""
    now = _now()
    with db.connection() as conn:
        conn.execute(
            "INSERT INTO agent_access (user_email, agent_id, status, requested_at) "
            "VALUES (%s, %s, 'pending', %s) "
            "ON CONFLICT (user_email, agent_id) DO UPDATE SET "
            "status='pending', requested_at=%s WHERE agent_access.status <> 'granted'",
            (email, agent_id, now, now),
        )
        row = conn.execute(
            "SELECT status FROM agent_access WHERE user_email=%s AND agent_id=%s",
            (email, agent_id),
        ).fetchone()
    return {"agent_id": agent_id, "status": row["status"] if row else "pending"}


def set_status(email: str, agent_id: str, status: str, decided_by: str) -> bool:
    """Set the access status for (email, agent_id). Upserts the row."""
    now = _now()
    with db.connection() as conn:
        conn.execute(
            "INSERT INTO agent_access "
            "(user_email, agent_id, status, requested_at, decided_at, decided_by) "
            "VALUES (%s, %s, %s, %s, %s, %s) "
            "ON CONFLICT (user_email, agent_id) DO UPDATE SET "
            "status=%s, decided_at=%s, decided_by=%s",
            (email, agent_id, status, now, now, decided_by, status, now, decided_by),
        )
    return True


def list_pending() -> list[dict]:
    with db.connection() as conn:
        rows = conn.execute(
            "SELECT user_email, agent_id, requested_at FROM agent_access "
            "WHERE status='pending' ORDER BY requested_at ASC"
        ).fetchall()
    return [dict(r) for r in rows]


def list_for_user(email: str) -> dict[str, str]:
    with db.connection() as conn:
        rows = conn.execute(
            "SELECT agent_id, status FROM agent_access WHERE user_email=%s",
            (email,),
        ).fetchall()
    return {r["agent_id"]: r["status"] for r in rows}


def list_grants() -> list[dict]:
    with db.connection() as conn:
        rows = conn.execute(
            "SELECT user_email, agent_id, decided_by, decided_at FROM agent_access "
            "WHERE status='granted' ORDER BY user_email, agent_id"
        ).fetchall()
    return [dict(r) for r in rows]
