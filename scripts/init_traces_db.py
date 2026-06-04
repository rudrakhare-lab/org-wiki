#!/usr/bin/env python3
"""
init_traces_db.py — idempotent migration for raw/traces/traces.sqlite.

Creates the request-lifecycle tracing database: 3 tables + 7 indexes, with the
production PRAGMAs. Safe to re-run (IF NOT EXISTS everywhere) — re-running never
drops anything and just reprints row counts.

Standalone: run manually with the backend STOPPED. NOT imported by the backend
(backend.trace_store opens its own connection at runtime).

Usage:
    ./venv/bin/python scripts/init_traces_db.py
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TRACES_DIR = ROOT / "raw" / "traces"
DB_PATH = TRACES_DIR / "traces.sqlite"

# ── PRAGMAs (set per-connection; journal_mode=WAL persists on the file) ───────
_PRAGMAS = [
    "PRAGMA journal_mode=WAL;",
    "PRAGMA synchronous=NORMAL;",
    "PRAGMA foreign_keys=ON;",
    "PRAGMA busy_timeout=5000;",
]

# ── Schema (approved Step 1) ──────────────────────────────────────────────────
_SCHEMA = """
CREATE TABLE IF NOT EXISTS trace_sessions (
    trace_id            TEXT PRIMARY KEY,          -- uuid4, minted in middleware
    -- LOGICAL FK → conversations.sqlite::conversations.id (CROSS-FILE, app-enforced)
    conversation_id     TEXT,
    -- LOGICAL FK → conversations.sqlite::messages.id (CROSS-FILE, app-enforced)
    message_id          TEXT,
    started_at          TEXT NOT NULL,             -- ISO-8601 UTC, ms precision
    ended_at            TEXT,                      -- NULL while in_progress
    duration_ms         INTEGER,
    mode                TEXT NOT NULL,             -- 'api' | 'claude-code'
    question            TEXT,                      -- truncated user input (<=500)
    status              TEXT NOT NULL DEFAULT 'in_progress',  -- in_progress|success|error|client_disconnect|orphaned
    error_message       TEXT,
    -- total_tokens_*/total_cost_usd are NULL when mode='claude-code'
    -- (subprocess invocation, no resp.usage accessible)
    total_tokens_input  INTEGER,
    total_tokens_output INTEGER,
    total_cost_usd      REAL,
    tool_call_count     INTEGER NOT NULL DEFAULT 0,
    round_count         INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS trace_events (
    event_id            TEXT PRIMARY KEY,          -- uuid4
    trace_id            TEXT NOT NULL
        REFERENCES trace_sessions(trace_id) ON DELETE CASCADE,  -- REAL FK (same file)
    sequence            INTEGER NOT NULL,          -- 0-based, monotonic within trace_id
    timestamp           TEXT NOT NULL,             -- ISO-8601 UTC, ms precision
    component           TEXT NOT NULL,             -- api_gateway|preflight|agent_loop|tool_execution|external_call|llm_call
    event_type          TEXT NOT NULL,
    duration_ms         INTEGER,
    round_num           INTEGER,                   -- NULL=boundary · 0=preflight · 1..N=agent rounds
    tool_name           TEXT,
    tool_input_json     TEXT,                      -- already sanitized by registry + scrubbed by trace_store
    tool_output_summary TEXT,
    status              TEXT,                      -- ok|error|timeout|credentials_required
    metadata_json       TEXT
);

CREATE TABLE IF NOT EXISTS trace_metrics (
    trace_id              TEXT PRIMARY KEY
        REFERENCES trace_sessions(trace_id) ON DELETE CASCADE,  -- REAL FK (same file)
    latency_total_ms      INTEGER,
    latency_preflight_ms  INTEGER,
    latency_llm_ms        INTEGER,
    latency_tools_ms      INTEGER,
    tool_calls_by_name_json TEXT,
    tokens_input          INTEGER,
    tokens_output         INTEGER,
    tokens_cached_input   INTEGER,                 -- cache_read_input_tokens
    cost_usd              REAL,
    errors_count          INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_events_trace      ON trace_events(trace_id, sequence);
CREATE INDEX IF NOT EXISTS idx_events_component  ON trace_events(component);
CREATE INDEX IF NOT EXISTS idx_events_tool       ON trace_events(tool_name);
CREATE INDEX IF NOT EXISTS idx_sessions_conv     ON trace_sessions(conversation_id);
CREATE INDEX IF NOT EXISTS idx_sessions_started  ON trace_sessions(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_sessions_mode     ON trace_sessions(mode);
CREATE INDEX IF NOT EXISTS idx_sessions_status   ON trace_sessions(status);
"""

_TABLES = ("trace_sessions", "trace_events", "trace_metrics")


def main() -> None:
    TRACES_DIR.mkdir(parents=True, exist_ok=True)
    fresh = not DB_PATH.exists()
    conn = sqlite3.connect(DB_PATH)
    try:
        for p in _PRAGMAS:
            conn.execute(p)
        conn.executescript(_SCHEMA)
        conn.commit()
        print(f"{'Created' if fresh else 'Verified'} traces DB at {DB_PATH}")
        for t in _TABLES:
            n = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            print(f"  {t}: {n} rows")
    finally:
        conn.close()
    print("Done. Re-running is safe (idempotent).")


if __name__ == "__main__":
    main()
