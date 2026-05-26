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
import sqlite3
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


SCHEMA_DDL = """
CREATE TABLE IF NOT EXISTS tickets (
  key                    TEXT PRIMARY KEY,
  project                TEXT NOT NULL,
  type                   TEXT,
  status                 TEXT,
  status_category        TEXT,
  priority               TEXT,
  resolution             TEXT,

  summary                TEXT,
  description_text       TEXT,
  description_raw_json   TEXT,
  resolution_text        TEXT,

  comment_count          INTEGER DEFAULT 0,
  comments_text          TEXT,
  comments_raw_json      TEXT,

  functional_area        TEXT,
  components_json        TEXT,
  labels_json            TEXT,

  reporter_account_id    TEXT,
  reporter_display_name  TEXT,
  assignee_account_id    TEXT,
  assignee_display_name  TEXT,

  parent_key             TEXT,
  epic_key               TEXT,

  links_json             TEXT,
  external_urls_json     TEXT,
  attachments_json       TEXT,

  created_at             TEXT NOT NULL,
  updated_at             TEXT NOT NULL,
  resolved_at            TEXT,

  -- Pipeline metadata (NOT from Jira)
  fetched_at             TEXT NOT NULL,
  normalized_at          TEXT NOT NULL,
  source_filter          TEXT,
  triage_tier            TEXT,
  triage_reason          TEXT,
  last_triaged_at        TEXT,
  embedding_id           INTEGER
);

CREATE INDEX IF NOT EXISTS idx_functional_area ON tickets(functional_area);
CREATE INDEX IF NOT EXISTS idx_project_status  ON tickets(project, status_category);
CREATE INDEX IF NOT EXISTS idx_updated         ON tickets(updated_at);
CREATE INDEX IF NOT EXISTS idx_triage          ON tickets(triage_tier);
CREATE INDEX IF NOT EXISTS idx_resolved        ON tickets(resolved_at);

CREATE TABLE IF NOT EXISTS sync_runs (
  id               INTEGER PRIMARY KEY AUTOINCREMENT,
  started_at       TEXT NOT NULL,
  ended_at         TEXT,
  filter_name      TEXT,
  mode             TEXT,
  tickets_fetched  INTEGER,
  tickets_new      INTEGER,
  tickets_updated  INTEGER,
  errors_json      TEXT,
  status           TEXT
);

CREATE TABLE IF NOT EXISTS custom_field_map (
  field_name   TEXT NOT NULL,
  project      TEXT NOT NULL,
  field_id     TEXT NOT NULL,
  cached_at    TEXT NOT NULL,
  PRIMARY KEY (field_name, project)
);
"""


# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------

def connect(db_path: Path) -> sqlite3.Connection:
    """Open the SQLite DB with WAL + foreign keys, create dir if missing."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA synchronous = NORMAL")
    return conn


def bootstrap_schema(conn: sqlite3.Connection) -> None:
    """Idempotent — safe to call on every script start."""
    conn.executescript(SCHEMA_DDL)
    conn.commit()


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


def upsert_ticket(conn: sqlite3.Connection, row: dict[str, Any]) -> str:
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
        "last_triaged_at, embedding_id FROM tickets WHERE key = ?", (key,),
    ).fetchone()

    if existing is None:
        cols = ", ".join(_TICKET_COLUMNS)
        placeholders = ", ".join(["?"] * len(_TICKET_COLUMNS))
        values = [row.get(c) for c in _TICKET_COLUMNS]
        conn.execute(f"INSERT INTO tickets ({cols}) VALUES ({placeholders})", values)
        return "new"

    if existing["updated_at"] == row["updated_at"]:
        # No content change — just refresh metadata + (possibly) source_filter
        merged_filter = _merge_source_filter(existing["source_filter"], row.get("source_filter"))
        conn.execute(
            "UPDATE tickets SET fetched_at = ?, normalized_at = ?, source_filter = ? "
            "WHERE key = ?",
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

    set_clause = ", ".join([f"{c} = ?" for c in _TICKET_COLUMNS if c != "key"])
    values = [row.get(c) for c in _TICKET_COLUMNS if c != "key"] + [key]
    conn.execute(f"UPDATE tickets SET {set_clause} WHERE key = ?", values)
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

def start_sync_run(conn: sqlite3.Connection, filter_name: str, mode: str) -> int:
    cur = conn.execute(
        "INSERT INTO sync_runs (started_at, filter_name, mode, status) "
        "VALUES (?, ?, ?, ?)",
        (utcnow_iso(), filter_name, mode, "running"),
    )
    conn.commit()
    return cur.lastrowid  # type: ignore[return-value]


def end_sync_run(
    conn: sqlite3.Connection,
    run_id: int,
    *,
    status: str,
    fetched: int,
    new: int,
    updated: int,
    errors: list[dict] | None = None,
) -> None:
    conn.execute(
        "UPDATE sync_runs SET ended_at = ?, tickets_fetched = ?, "
        "tickets_new = ?, tickets_updated = ?, errors_json = ?, status = ? "
        "WHERE id = ?",
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


def last_successful_incremental(conn: sqlite3.Connection) -> str | None:
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
    conn: sqlite3.Connection, field_name: str, project: str, max_age_hours: int
) -> str | None:
    row = conn.execute(
        "SELECT field_id, cached_at FROM custom_field_map "
        "WHERE field_name = ? AND project = ?",
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
    conn: sqlite3.Connection, field_name: str, project: str, field_id: str
) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO custom_field_map "
        "(field_name, project, field_id, cached_at) VALUES (?, ?, ?, ?)",
        (field_name, project, field_id, utcnow_iso()),
    )


# ---------------------------------------------------------------------------
# Distribution report (no API call)
# ---------------------------------------------------------------------------

def report(conn: sqlite3.Connection) -> dict[str, Any]:
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
def transaction(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """Explicit BEGIN/COMMIT around a block. Rolls back on exception."""
    conn.execute("BEGIN")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
