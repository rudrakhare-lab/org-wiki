"""
SQLite-backed user and token store.

DB at raw/auth/auth.sqlite. Two tables:
  users(email, role, created_at, created_by)
  tokens(token, user_email, created_at, expires_at, revoked)

lookup_token() returns None for revoked or expired tokens.
All callers are responsible for hashing/salting tokens before passing in —
tokens are stored as-is (SHA-256 hex digest is already non-reversible).
"""
from __future__ import annotations

import secrets
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from backend.config import RAW_DIR

AUTH_DIR = RAW_DIR / "auth"
AUTH_DB = AUTH_DIR / "auth.sqlite"

_SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    email       TEXT PRIMARY KEY,
    role        TEXT NOT NULL DEFAULT 'viewer',
    created_at  TEXT NOT NULL,
    created_by  TEXT
);

CREATE TABLE IF NOT EXISTS tokens (
    token       TEXT PRIMARY KEY,
    user_email  TEXT NOT NULL REFERENCES users(email) ON DELETE CASCADE,
    created_at  TEXT NOT NULL,
    expires_at  TEXT,
    revoked     INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_tokens_email   ON tokens(user_email);
CREATE INDEX IF NOT EXISTS idx_tokens_revoked ON tokens(revoked, expires_at);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@contextmanager
def _connect() -> Iterator[sqlite3.Connection]:
    AUTH_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(AUTH_DB), isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def init_schema() -> None:
    with _connect() as conn:
        conn.executescript(_SCHEMA)


# ── Users ─────────────────────────────────────────────────────────────────────

def create_user(
    email: str,
    role: str = "viewer",
    created_by: str | None = None,
) -> dict[str, Any]:
    init_schema()
    now = _now()
    with _connect() as conn:
        conn.execute(
            "INSERT INTO users (email, role, created_at, created_by) VALUES (?, ?, ?, ?)",
            (email, role, now, created_by),
        )
    return {"email": email, "role": role, "created_at": now, "created_by": created_by}


def get_user(email: str) -> dict[str, Any] | None:
    init_schema()
    with _connect() as conn:
        row = conn.execute(
            "SELECT email, role, created_at, created_by FROM users WHERE email = ?",
            (email,),
        ).fetchone()
    return dict(row) if row else None


def list_users() -> list[dict[str, Any]]:
    init_schema()
    with _connect() as conn:
        rows = conn.execute(
            "SELECT email, role, created_at, created_by FROM users ORDER BY created_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def delete_user(email: str) -> bool:
    init_schema()
    with _connect() as conn:
        cur = conn.execute("DELETE FROM users WHERE email = ?", (email,))
        return cur.rowcount > 0


# ── Tokens ────────────────────────────────────────────────────────────────────

def create_token(user_email: str, expires_at: str | None = None) -> str:
    """Generate a 32-char hex token and store it. Returns the raw token."""
    init_schema()
    token = secrets.token_hex(16)  # 32 hex chars
    now = _now()
    with _connect() as conn:
        conn.execute(
            "INSERT INTO tokens (token, user_email, created_at, expires_at, revoked) "
            "VALUES (?, ?, ?, ?, 0)",
            (token, user_email, now, expires_at),
        )
    return token


def lookup_token(token: str) -> dict[str, Any] | None:
    """Return user dict if token is valid (not revoked, not expired). Else None."""
    init_schema()
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT u.email, u.role, t.expires_at
            FROM tokens t
            JOIN users u ON t.user_email = u.email
            WHERE t.token = ? AND t.revoked = 0
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
    return {"email": row["email"], "role": row["role"], "token": token}


def revoke_token(token: str) -> bool:
    init_schema()
    with _connect() as conn:
        cur = conn.execute(
            "UPDATE tokens SET revoked = 1 WHERE token = ?", (token,)
        )
        return cur.rowcount > 0


def list_tokens(user_email: str) -> list[dict[str, Any]]:
    init_schema()
    with _connect() as conn:
        rows = conn.execute(
            "SELECT token, user_email, created_at, expires_at, revoked "
            "FROM tokens WHERE user_email = ? ORDER BY created_at DESC",
            (user_email,),
        ).fetchall()
    return [dict(r) for r in rows]
