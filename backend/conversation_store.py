"""
Conversation store — PostgreSQL-backed chat history.

Tables (created by migrations/postgres/020_conversations.sql at app startup):
  conversations(id, title, created_at, updated_at, user_email,
                compacted_summary, compaction_at_turn)
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
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Iterator

from backend import db


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _new_id() -> str:
    return secrets.token_hex(8)  # 16-char hex


@contextmanager
def _connect() -> Iterator[Any]:
    """Acquire a pooled Postgres connection (autocommit, Row factory)."""
    with db.connection() as conn:
        yield conn


def init_schema() -> None:
    """Ensure the schema exists. Delegates to the migration runner.

    Kept for scripts/tests that call it directly; the app runs migrations once
    at startup (see api.py lifespan). The schema columns user_email,
    compacted_summary, and compaction_at_turn (formerly added by a hand-rolled
    PRAGMA-based migration) are now part of 020_conversations.sql.
    """
    db.init_db()


# ── Conversations ────────────────────────────────────────────────────────────

def create_conversation(title: str | None = None, user_email: str | None = None,
                        agent_id: str = "conwo") -> dict[str, Any]:
    cid = _new_id()
    now = _now()
    final_title = (title or "New chat").strip()[:200] or "New chat"
    with _connect() as conn:
        conn.execute(
            "INSERT INTO conversations (id, title, created_at, updated_at, user_email, agent_id) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (cid, final_title, now, now, user_email, agent_id),
        )
    return {
        "id": cid,
        "title": final_title,
        "created_at": now,
        "updated_at": now,
        "user_email": user_email,
        "agent_id": agent_id,
        "message_count": 0,
    }


def list_conversations(limit: int = 200, user_email: str | None = None,
                       agent_id: str = "conwo") -> list[dict[str, Any]]:
    where = ["c.agent_id = %s"]
    params: list[Any] = [agent_id]
    if user_email is not None:
        where.append("c.user_email = %s")
        params.append(user_email)
    params.append(limit)
    with _connect() as conn:
        rows = conn.execute(
            f"""
            SELECT c.id, c.title, c.created_at, c.updated_at,
                   (SELECT COUNT(*) FROM messages m WHERE m.conversation_id = c.id)
                   AS message_count
            FROM conversations c
            WHERE {" AND ".join(where)}
            ORDER BY c.updated_at DESC
            LIMIT %s
            """,
            tuple(params),
        ).fetchall()
    return [dict(r) for r in rows]


def get_conversation(conversation_id: str) -> dict[str, Any] | None:
    with _connect() as conn:
        conv_row = conn.execute(
            "SELECT id, title, created_at, updated_at, user_email, agent_id FROM conversations WHERE id = %s",
            (conversation_id,),
        ).fetchone()
        if not conv_row:
            return None
        msg_rows = conn.execute(
            """
            SELECT id, conversation_id, role, content, created_at, mode, server, buid,
                   answer_id, confidence, sources_json, tool_trace_json, missing_context_json,
                   cost_inr
            FROM messages
            WHERE conversation_id = %s
            ORDER BY created_at ASC
            """,
            (conversation_id,),
        ).fetchall()

    conv = dict(conv_row)
    conv["messages"] = [_row_to_message(r) for r in msg_rows]
    return conv


def update_conversation_title(conversation_id: str, title: str) -> bool:
    cleaned = (title or "").strip()[:200]
    if not cleaned:
        return False
    with _connect() as conn:
        cur = conn.execute(
            "UPDATE conversations SET title = %s, updated_at = %s WHERE id = %s",
            (cleaned, _now(), conversation_id),
        )
        return cur.rowcount > 0


def delete_conversation(conversation_id: str) -> bool:
    with _connect() as conn:
        cur = conn.execute(
            "DELETE FROM conversations WHERE id = %s", (conversation_id,)
        )
        return cur.rowcount > 0


def touch_conversation(conversation_id: str) -> None:
    with _connect() as conn:
        conn.execute(
            "UPDATE conversations SET updated_at = %s WHERE id = %s",
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
    agent_id: str = "conwo",
    cost_inr: float | None = None,
) -> dict[str, Any]:
    """
    Append a message to a conversation. The caller is responsible for ensuring
    tool_trace has already passed through ToolRegistry sanitization.

    Note: the INSERT and the conversation `updated_at` UPDATE are autocommitted
    separately (not wrapped in one transaction) — matching the prior SQLite
    isolation_level=None behavior exactly.
    """
    if role not in ("user", "assistant", "system"):
        raise ValueError(f"Invalid role: {role!r}")

    mid = _new_id()
    now = _now()
    with _connect() as conn:
        conv_exists = conn.execute(
            "SELECT 1 FROM conversations WHERE id = %s", (conversation_id,)
        ).fetchone()
        if not conv_exists:
            raise LookupError(f"Conversation not found: {conversation_id!r}")

        conn.execute(
            """
            INSERT INTO messages (
                id, conversation_id, role, content, created_at, mode, server, buid,
                answer_id, confidence, sources_json, tool_trace_json, missing_context_json,
                agent_id, cost_inr
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                agent_id,
                cost_inr,
            ),
        )
        conn.execute(
            "UPDATE conversations SET updated_at = %s WHERE id = %s",
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
        "agent_id": agent_id,
        "cost_inr": cost_inr,
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

    Both are None for never-compacted conversations. Returns (None, None) when
    the conversation does not exist — caller should treat as "no summary."
    """
    with _connect() as conn:
        row = conn.execute(
            "SELECT compacted_summary, compaction_at_turn FROM conversations WHERE id = %s",
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
    with _connect() as conn:
        conn.execute(
            "UPDATE conversations SET compacted_summary = %s, compaction_at_turn = %s WHERE id = %s",
            (summary, at_turn, conversation_id),
        )


# ── Internal helpers ─────────────────────────────────────────────────────────

def _row_to_message(row: Any) -> dict[str, Any]:
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
        "cost_inr": float(row["cost_inr"]) if row["cost_inr"] is not None else None,
    }


def _safe_json(value: str | None) -> Any:
    if not value:
        return None
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return None
