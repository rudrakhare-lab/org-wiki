"""
Conversation store — SQLite-backed chat history.

Two tables:
  conversations(id, title, created_at, updated_at)
  messages(id, conversation_id, role, content, created_at, mode, server, buid,
           answer_id, confidence, sources_json, tool_trace_json,
           missing_context_json)

Foreign keys cascade so deleting a conversation removes its messages atomically.

Persistence policy:
  - Never store API keys or Bearer tokens here.
  - tool_trace is assumed already sanitized by ToolRegistry.
  - sources/tool_trace/missing_context are JSON-serialized to TEXT.
"""
from __future__ import annotations

import json
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Iterator

from backend.config import CONVERSATIONS_DB, CONVERSATIONS_DIR

_SCHEMA = """
CREATE TABLE IF NOT EXISTS conversations (
    id          TEXT PRIMARY KEY,
    title       TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_conv_updated_at
    ON conversations(updated_at DESC);

CREATE TABLE IF NOT EXISTS messages (
    id                    TEXT PRIMARY KEY,
    conversation_id       TEXT NOT NULL,
    role                  TEXT NOT NULL,
    content               TEXT NOT NULL,
    created_at            TEXT NOT NULL,
    mode                  TEXT,
    server                TEXT,
    buid                  TEXT,
    answer_id             TEXT,
    confidence            TEXT,
    sources_json          TEXT,
    tool_trace_json       TEXT,
    missing_context_json  TEXT,
    FOREIGN KEY (conversation_id)
        REFERENCES conversations(id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_msg_conversation_id
    ON messages(conversation_id, created_at ASC);
"""

_MIGRATION_ADD_USER_EMAIL = """
ALTER TABLE conversations ADD COLUMN user_email TEXT;
"""

# G03: rolling summary of compacted older turns + the message-count snapshot
# at which the summary was generated. Both NULL on conversations created
# before G03 — load_conversation_summary handles that as "no summary yet".
_MIGRATION_ADD_COMPACTED_SUMMARY = """
ALTER TABLE conversations ADD COLUMN compacted_summary TEXT;
"""
_MIGRATION_ADD_COMPACTION_AT_TURN = """
ALTER TABLE conversations ADD COLUMN compaction_at_turn INTEGER;
"""


def _apply_migrations(conn: sqlite3.Connection) -> None:
    """Idempotently apply schema migrations. Safe to call on every startup."""
    cols = {row[1] for row in conn.execute("PRAGMA table_info(conversations)")}
    for col_name, stmt in (
        ("user_email", _MIGRATION_ADD_USER_EMAIL),
        ("compacted_summary", _MIGRATION_ADD_COMPACTED_SUMMARY),
        ("compaction_at_turn", _MIGRATION_ADD_COMPACTION_AT_TURN),
    ):
        if col_name in cols:
            continue
        try:
            conn.execute(stmt)
        except sqlite3.OperationalError as exc:
            if "duplicate column name" not in str(exc).lower():
                raise


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _new_id() -> str:
    return secrets.token_hex(8)  # 16-char hex


@contextmanager
def _connect() -> Iterator[sqlite3.Connection]:
    CONVERSATIONS_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(CONVERSATIONS_DB), isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def init_schema() -> None:
    """Create tables and indexes if they don't exist. Safe to call repeatedly."""
    with _connect() as conn:
        conn.executescript(_SCHEMA)
        _apply_migrations(conn)


# ── Conversations ────────────────────────────────────────────────────────────

def create_conversation(title: str | None = None, user_email: str | None = None) -> dict[str, Any]:
    init_schema()
    cid = _new_id()
    now = _now()
    final_title = (title or "New chat").strip()[:200] or "New chat"
    with _connect() as conn:
        conn.execute(
            "INSERT INTO conversations (id, title, created_at, updated_at, user_email) "
            "VALUES (?, ?, ?, ?, ?)",
            (cid, final_title, now, now, user_email),
        )
    return {
        "id": cid,
        "title": final_title,
        "created_at": now,
        "updated_at": now,
        "user_email": user_email,
        "message_count": 0,
    }


def list_conversations(limit: int = 200, user_email: str | None = None) -> list[dict[str, Any]]:
    init_schema()
    with _connect() as conn:
        if user_email is not None:
            rows = conn.execute(
                """
                SELECT c.id, c.title, c.created_at, c.updated_at,
                       (SELECT COUNT(*) FROM messages m WHERE m.conversation_id = c.id)
                       AS message_count
                FROM conversations c
                WHERE c.user_email = ?
                ORDER BY c.updated_at DESC
                LIMIT ?
                """,
                (user_email, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT c.id, c.title, c.created_at, c.updated_at,
                       (SELECT COUNT(*) FROM messages m WHERE m.conversation_id = c.id)
                       AS message_count
                FROM conversations c
                ORDER BY c.updated_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
    return [dict(r) for r in rows]


def get_conversation(conversation_id: str) -> dict[str, Any] | None:
    init_schema()
    with _connect() as conn:
        conv_row = conn.execute(
            "SELECT id, title, created_at, updated_at, user_email FROM conversations WHERE id = ?",
            (conversation_id,),
        ).fetchone()
        if not conv_row:
            return None
        msg_rows = conn.execute(
            """
            SELECT id, conversation_id, role, content, created_at, mode, server, buid,
                   answer_id, confidence, sources_json, tool_trace_json, missing_context_json
            FROM messages
            WHERE conversation_id = ?
            ORDER BY created_at ASC
            """,
            (conversation_id,),
        ).fetchall()

    conv = dict(conv_row)
    conv["messages"] = [_row_to_message(r) for r in msg_rows]
    return conv


def update_conversation_title(conversation_id: str, title: str) -> bool:
    init_schema()
    cleaned = (title or "").strip()[:200]
    if not cleaned:
        return False
    with _connect() as conn:
        cur = conn.execute(
            "UPDATE conversations SET title = ?, updated_at = ? WHERE id = ?",
            (cleaned, _now(), conversation_id),
        )
        return cur.rowcount > 0


def delete_conversation(conversation_id: str) -> bool:
    init_schema()
    with _connect() as conn:
        cur = conn.execute(
            "DELETE FROM conversations WHERE id = ?", (conversation_id,)
        )
        return cur.rowcount > 0


def touch_conversation(conversation_id: str) -> None:
    with _connect() as conn:
        conn.execute(
            "UPDATE conversations SET updated_at = ? WHERE id = ?",
            (_now(), conversation_id),
        )


# ── Messages ─────────────────────────────────────────────────────────────────

def add_message(
    conversation_id: str,
    role: str,
    content: str,
    *,
    mode: str | None = None,
    server: str | None = None,
    buid: str | None = None,
    answer_id: str | None = None,
    confidence: str | None = None,
    sources: dict | None = None,
    tool_trace: list[dict] | None = None,
    missing_context: list[str] | None = None,
) -> dict[str, Any]:
    """
    Append a message to a conversation. The caller is responsible for ensuring
    tool_trace has already passed through ToolRegistry sanitization.
    """
    init_schema()
    if role not in ("user", "assistant", "system"):
        raise ValueError(f"Invalid role: {role!r}")

    mid = _new_id()
    now = _now()
    with _connect() as conn:
        conv_exists = conn.execute(
            "SELECT 1 FROM conversations WHERE id = ?", (conversation_id,)
        ).fetchone()
        if not conv_exists:
            raise LookupError(f"Conversation not found: {conversation_id!r}")

        conn.execute(
            """
            INSERT INTO messages (
                id, conversation_id, role, content, created_at, mode, server, buid,
                answer_id, confidence, sources_json, tool_trace_json, missing_context_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                mid,
                conversation_id,
                role,
                content,
                now,
                mode,
                server,
                buid,
                answer_id,
                confidence,
                json.dumps(sources) if sources is not None else None,
                json.dumps(tool_trace) if tool_trace is not None else None,
                json.dumps(missing_context) if missing_context is not None else None,
            ),
        )
        conn.execute(
            "UPDATE conversations SET updated_at = ? WHERE id = ?",
            (now, conversation_id),
        )

    return {
        "id": mid,
        "conversation_id": conversation_id,
        "role": role,
        "content": content,
        "created_at": now,
        "mode": mode,
        "server": server,
        "buid": buid,
        "answer_id": answer_id,
        "confidence": confidence,
        "sources": sources,
        "tool_trace": tool_trace,
        "missing_context": missing_context,
    }


def auto_title_from_question(question: str, max_len: int = 60) -> str:
    """Generate a chat title from the first user question."""
    q = (question or "").strip().replace("\n", " ").replace("\r", " ")
    if len(q) <= max_len:
        return q or "New chat"
    return q[: max_len - 1].rstrip() + "…"


# ── Compaction state (G03) ───────────────────────────────────────────────────

def get_compaction_state(conversation_id: str) -> tuple[str | None, int | None]:
    """Return (compacted_summary, compaction_at_turn) for a conversation.

    Both are None for never-compacted conversations (or conversations
    created before the G03 migration). Returns (None, None) when the
    conversation does not exist — caller should treat as "no summary."
    """
    init_schema()
    with _connect() as conn:
        row = conn.execute(
            "SELECT compacted_summary, compaction_at_turn FROM conversations WHERE id = ?",
            (conversation_id,),
        ).fetchone()
    if not row:
        return None, None
    return row["compacted_summary"], row["compaction_at_turn"]


def set_compacted_summary(
    conversation_id: str,
    summary: str,
    at_turn: int,
) -> None:
    """Persist the rolling summary and the message-count snapshot at which
    it was generated. at_turn is the TOTAL message count at the time of
    compaction; should_refresh() uses it to decide when the next refresh
    is due."""
    init_schema()
    with _connect() as conn:
        conn.execute(
            "UPDATE conversations SET compacted_summary = ?, compaction_at_turn = ? WHERE id = ?",
            (summary, at_turn, conversation_id),
        )


# ── Internal helpers ─────────────────────────────────────────────────────────

def _row_to_message(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "conversation_id": row["conversation_id"],
        "role": row["role"],
        "content": row["content"],
        "created_at": row["created_at"],
        "mode": row["mode"],
        "server": row["server"],
        "buid": row["buid"],
        "answer_id": row["answer_id"],
        "confidence": row["confidence"],
        "sources": _safe_json(row["sources_json"]),
        "tool_trace": _safe_json(row["tool_trace_json"]),
        "missing_context": _safe_json(row["missing_context_json"]),
    }


def _safe_json(value: str | None) -> Any:
    if not value:
        return None
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return None
