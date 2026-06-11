"""
lib/db.py — SQLite helpers for Tier 0 ticket mirror.

Single source of truth for the schema in raw/jira/tickets.sqlite. All other
modules go through these helpers; nobody else writes raw SQL.

Idempotency contract (UPSERT):
- A ticket row is identified by `key` (PRIMARY KEY).
- Re-syncing a ticket whose `updated_at` is unchanged refreshes only
  `fetched_at` and `normalized_at`. Triage state is left alone — that's the
  classifier's domain.
- A ticket whose `updated_at` advanced gets the full row replaced AND
  `triage_tier`/`last_triaged_at` cleared, signaling the classifier should
  re-evaluate it.
"""

from __future__ import annotations

import json
import sys
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

# Make the repo root importable so scripts can use backend.db (the DSN builder,
# Row factory, and migration runner). Importing backend also loads .env via
# backend/__init__.py, so CONWO_DB_* are available.
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import psycopg  # noqa: E402
from backend import db as _appdb  # noqa: E402

# Postgres schema for the ticket mirror lives in migrations/postgres/040_tickets.sql.
# bootstrap_schema() applies it (and all migrations) via the idempotent runner.


# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------

def connect(db_path: Path | None = None) -> Any:
    """Open a dedicated PostgreSQL connection for batch scripts.

    autocommit=False so the explicit commit()/rollback()/transaction() style in
    this module works exactly like the old sqlite3 connection. The db_path arg is
    ignored (kept for call-site compatibility) — the target is the wis_conwo
    database resolved from CONWO_DB_* env vars.
    """
    conn = psycopg.connect(_appdb._dsn(), autocommit=False)
    conn.row_factory = _appdb._row_factory
    return conn


def bootstrap_schema(conn: Any) -> None:
    """Ensure the schema exists. Delegates to the migration runner (idempotent,
    advisory-locked). Safe to call on every script start.

    init_db() uses its own pooled connection; we close that pool afterward so a
    short-lived batch script doesn't leave pool worker threads running at exit.
    The script keeps using its own dedicated `conn` from connect()."""
    _appdb.init_db()
    _appdb.close_pool()


# ---------------------------------------------------------------------------
# Tickets — UPSERT with idempotency
# ---------------------------------------------------------------------------

_TICKET_COLUMNS = [
    "key", "project", "type", "status", "status_category", "priority", "resolution",
    "summary", "description_text", "description_raw_json", "resolution_text",
    "comment_count", "comments_text", "comments_raw_json",
    "functional_area", "components_json", "labels_json",
    "reporter_account_id", "reporter_display_name",
    "assignee_account_id", "assignee_display_name",
    "parent_key", "epic_key",
    "links_json", "external_urls_json", "attachments_json",
    "created_at", "updated_at", "resolved_at",
    "fetched_at", "normalized_at", "source_filter",
    "triage_tier", "triage_reason", "last_triaged_at", "embedding_id",
]


def upsert_ticket(conn: Any, row: dict[str, Any]) -> str:
    """
    Insert or update a ticket. Returns one of: 'new', 'updated', 'unchanged'.

    Idempotency: if updated_at is unchanged, we touch only fetched_at +
    normalized_at + source_filter (which may legitimately broaden when a
    ticket newly matches a second filter). triage_* and embedding_id are
    untouched in that case.
    """
    key = row["key"]
    existing = conn.execute(
        "SELECT updated_at, source_filter, triage_tier, triage_reason, "
        "last_triaged_at, embedding_id FROM tickets WHERE key = %s", (key,),
    ).fetchone()

    if existing is None:
        cols = ", ".join(_TICKET_COLUMNS)
        placeholders = ", ".join(["%s"] * len(_TICKET_COLUMNS))
        values = [row.get(c) for c in _TICKET_COLUMNS]
        conn.execute(f"INSERT INTO tickets ({cols}) VALUES ({placeholders})", values)
        return "new"

    if existing["updated_at"] == row["updated_at"]:
        # No content change — just refresh metadata + (possibly) source_filter
        merged_filter = _merge_source_filter(existing["source_filter"], row.get("source_filter"))
        conn.execute(
            "UPDATE tickets SET fetched_at = %s, normalized_at = %s, source_filter = %s "
            "WHERE key = %s",
            (row["fetched_at"], row["normalized_at"], merged_filter, key),
        )
        return "unchanged"

    # Genuine update — replace row, preserve embedding_id, clear triage so
    # the classifier picks it back up
    row = dict(row)  # shallow copy so we don't mutate caller's dict
    row["embedding_id"] = existing["embedding_id"]
    row["triage_tier"] = None
    row["triage_reason"] = None
    row["last_triaged_at"] = None
    row["source_filter"] = _merge_source_filter(existing["source_filter"], row.get("source_filter"))

    set_clause = ", ".join([f"{c} = %s" for c in _TICKET_COLUMNS if c != "key"])
    values = [row.get(c) for c in _TICKET_COLUMNS if c != "key"] + [key]
    conn.execute(f"UPDATE tickets SET {set_clause} WHERE key = %s", values)
    return "updated"


def _merge_source_filter(existing: str | None, incoming: str | None) -> str | None:
    """Source filter is a comma-separated set of filter names ('A', 'B', 'A,B')."""
    parts = set()
    for s in (existing, incoming):
        if s:
            parts.update(p.strip() for p in s.split(",") if p.strip())
    if not parts:
        return None
    return ",".join(sorted(parts))


# ---------------------------------------------------------------------------
# Sync run lifecycle
# ---------------------------------------------------------------------------

def start_sync_run(conn: Any, filter_name: str, mode: str) -> int:
    # Postgres has no cursor.lastrowid — use RETURNING to get the new id.
    cur = conn.execute(
        "INSERT INTO sync_runs (started_at, filter_name, mode, status) "
        "VALUES (%s, %s, %s, %s) RETURNING id",
        (utcnow_iso(), filter_name, mode, "running"),
    )
    new_id = cur.fetchone()[0]
    conn.commit()
    return new_id


def end_sync_run(
    conn: Any,
    run_id: int,
    *,
    status: str,
    fetched: int,
    new: int,
    updated: int,
    errors: list[dict] | None = None,
) -> None:
    conn.execute(
        "UPDATE sync_runs SET ended_at = %s, tickets_fetched = %s, "
        "tickets_new = %s, tickets_updated = %s, errors_json = %s, status = %s "
        "WHERE id = %s",
        (
            utcnow_iso(),
            fetched,
            new,
            updated,
            json.dumps(errors) if errors else None,
            status,
            run_id,
        ),
    )
    conn.commit()


def last_successful_incremental(conn: Any) -> str | None:
    """Returns ISO timestamp of the most recent completed sync run, or None."""
    row = conn.execute(
        "SELECT MAX(ended_at) AS t FROM sync_runs "
        "WHERE status = 'success' AND mode IN ('backfill', 'incremental')"
    ).fetchone()
    return row["t"] if row and row["t"] else None


# ---------------------------------------------------------------------------
# Custom field map
# ---------------------------------------------------------------------------

def get_field_id(
    conn: Any, field_name: str, project: str, max_age_hours: int
) -> str | None:
    row = conn.execute(
        "SELECT field_id, cached_at FROM custom_field_map "
        "WHERE field_name = %s AND project = %s",
        (field_name, project),
    ).fetchone()
    if not row:
        return None
    cached_at = datetime.fromisoformat(row["cached_at"].replace("Z", "+00:00"))
    age = (datetime.now(timezone.utc) - cached_at).total_seconds() / 3600
    if age > max_age_hours:
        return None
    return row["field_id"]


def set_field_id(
    conn: Any, field_name: str, project: str, field_id: str
) -> None:
    conn.execute(
        "INSERT INTO custom_field_map "
        "(field_name, project, field_id, cached_at) VALUES (%s, %s, %s, %s) "
        "ON CONFLICT (field_name, project) DO UPDATE SET "
        "field_id = excluded.field_id, cached_at = excluded.cached_at",
        (field_name, project, field_id, utcnow_iso()),
    )


# ---------------------------------------------------------------------------
# Distribution report (no API call)
# ---------------------------------------------------------------------------

def report(conn: Any) -> dict[str, Any]:
    """Aggregate counts for the --report mode."""
    total = conn.execute("SELECT COUNT(*) AS n FROM tickets").fetchone()["n"]
    by_project = [
        dict(r) for r in conn.execute(
            "SELECT project, COUNT(*) AS n FROM tickets "
            "GROUP BY project ORDER BY n DESC"
        ).fetchall()
    ]
    by_fa = [
        dict(r) for r in conn.execute(
            "SELECT functional_area, COUNT(*) AS n FROM tickets "
            "GROUP BY functional_area ORDER BY n DESC"
        ).fetchall()
    ]
    by_status = [
        dict(r) for r in conn.execute(
            "SELECT status_category, COUNT(*) AS n FROM tickets "
            "GROUP BY status_category ORDER BY n DESC"
        ).fetchall()
    ]
    by_priority = [
        dict(r) for r in conn.execute(
            "SELECT priority, COUNT(*) AS n FROM tickets "
            "GROUP BY priority ORDER BY n DESC"
        ).fetchall()
    ]
    empty_shell = conn.execute(
        "SELECT COUNT(*) AS n FROM tickets WHERE triage_reason = 'empty-shell'"
    ).fetchone()["n"]
    with_resolution = conn.execute(
        "SELECT COUNT(*) AS n FROM tickets "
        "WHERE resolution_text IS NOT NULL AND TRIM(resolution_text) != ''"
    ).fetchone()["n"]
    with_external = conn.execute(
        "SELECT COUNT(*) AS n FROM tickets "
        "WHERE external_urls_json IS NOT NULL AND external_urls_json != '[]'"
    ).fetchone()["n"]
    date_range = conn.execute(
        "SELECT MIN(created_at) AS oldest, MAX(created_at) AS newest FROM tickets"
    ).fetchone()
    runs = [
        dict(r) for r in conn.execute(
            "SELECT id, started_at, ended_at, filter_name, mode, "
            "tickets_fetched, tickets_new, tickets_updated, status "
            "FROM sync_runs ORDER BY id DESC LIMIT 10"
        ).fetchall()
    ]
    return {
        "total_tickets": total,
        "by_project": by_project,
        "by_functional_area": by_fa,
        "by_status_category": by_status,
        "by_priority": by_priority,
        "empty_shell_count": empty_shell,
        "with_resolution_text": with_resolution,
        "with_external_urls": with_external,
        "oldest_created": date_range["oldest"],
        "newest_created": date_range["newest"],
        "recent_runs": runs,
    }


# ---------------------------------------------------------------------------
# Misc helpers
# ---------------------------------------------------------------------------

def utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


@contextmanager
def transaction(conn: Any) -> Iterator[Any]:
    """Commit on success, roll back on exception. With autocommit=False a
    transaction auto-starts on the first statement, so no explicit BEGIN."""
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
