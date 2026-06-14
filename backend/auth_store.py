"""
PostgreSQL-backed user and token store.

Tables (created by migrations/postgres/010_auth.sql, applied at app startup):
  users(email, role, created_at, created_by)
  tokens(token, user_email, created_at, expires_at, revoked)

lookup_token() returns None for revoked or expired tokens.
All callers are responsible for hashing/salting tokens before passing in —
tokens are stored as-is (SHA-256 hex digest is already non-reversible).
"""
from __future__ import annotations

import secrets
from contextlib import contextmanager
from datetime import date, datetime, timezone
from typing import Any, Iterator

from backend import db


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@contextmanager
def _connect() -> Iterator[Any]:
    """Acquire a pooled Postgres connection (autocommit, Row factory)."""
    with db.connection() as conn:
        yield conn


def init_schema() -> None:
    """Ensure the schema exists. Delegates to the migration runner.

    Kept for backward compatibility with scripts/tests that call it directly;
    the app itself runs migrations once at startup (see api.py lifespan).
    """
    db.init_db()


# ── Users ─────────────────────────────────────────────────────────────────────

def create_user(
    email: str,
    role: str = "general",
    created_by: str | None = None,
    approved: bool = False,
) -> dict[str, Any]:
    now = _now()
    with _connect() as conn:
        conn.execute(
            "INSERT INTO users (email, role, created_at, created_by, approved) "
            "VALUES (%s, %s, %s, %s, %s)",
            (email, role, now, created_by, approved),
        )
    return {"email": email, "role": role, "created_at": now,
            "created_by": created_by, "approved": approved}


def get_user(email: str) -> dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT email, role, created_at, created_by, approved FROM users WHERE email = %s",
            (email,),
        ).fetchone()
    return dict(row) if row else None


def list_users() -> list[dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT email, role, created_at, created_by, approved "
            "FROM users ORDER BY created_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def delete_user(email: str) -> bool:
    with _connect() as conn:
        cur = conn.execute("DELETE FROM users WHERE email = %s", (email,))
        return cur.rowcount > 0


def set_user_approved(email: str, approved: bool) -> bool:
    """Set a user's approval flag. Returns True if a row was updated."""
    with _connect() as conn:
        cur = conn.execute(
            "UPDATE users SET approved = %s WHERE email = %s", (approved, email)
        )
        return cur.rowcount > 0


def set_user_role(email: str, role: str) -> bool:
    """Change a user's role. Returns True if a row was updated."""
    with _connect() as conn:
        cur = conn.execute(
            "UPDATE users SET role = %s WHERE email = %s", (role, email)
        )
        return cur.rowcount > 0


# ── Tokens ────────────────────────────────────────────────────────────────────

def create_token(user_email: str, expires_at: str | None = None) -> str:
    """Generate a 32-char hex token and store it. Returns the raw token."""
    token = secrets.token_hex(16)  # 32 hex chars
    now = _now()
    with _connect() as conn:
        conn.execute(
            "INSERT INTO tokens (token, user_email, created_at, expires_at, revoked) "
            "VALUES (%s, %s, %s, %s, 0)",
            (token, user_email, now, expires_at),
        )
    return token


def lookup_token(token: str) -> dict[str, Any] | None:
    """Return user dict if token is valid (not revoked, not expired). Else None."""
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT u.email, u.role, u.approved, t.expires_at
            FROM tokens t
            JOIN users u ON t.user_email = u.email
            WHERE t.token = %s AND t.revoked = 0
            """,
            (token,),
        ).fetchone()
    if not row:
        return None
    expires = row["expires_at"]
    if expires:
        try:
            # Accept both "YYYY-MM-DD" and full ISO datetime strings.
            if date.fromisoformat(str(expires)[:10]) < date.today():
                return None
        except ValueError:
            return None  # fail closed on unparseable expiry
    return {"email": row["email"], "role": row["role"],
            "approved": bool(row["approved"]), "token": token}


def revoke_token(token: str) -> bool:
    with _connect() as conn:
        cur = conn.execute(
            "UPDATE tokens SET revoked = 1 WHERE token = %s", (token,)
        )
        return cur.rowcount > 0


def list_tokens(user_email: str) -> list[dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT token, user_email, created_at, expires_at, revoked "
            "FROM tokens WHERE user_email = %s ORDER BY created_at DESC",
            (user_email,),
        ).fetchall()
    return [dict(r) for r in rows]
