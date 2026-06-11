-- Trace store (was raw/traces/traces.sqlite). Idempotent.
-- conversation_id / message_id are LOGICAL (app-enforced) cross-store links —
-- kept as plain columns WITHOUT FK constraints, exactly as in SQLite, so a
-- trace for a missing conversation still inserts (identical behavior).
CREATE TABLE IF NOT EXISTS trace_sessions (
    trace_id            TEXT PRIMARY KEY,
    conversation_id     TEXT,
    message_id          TEXT,
    started_at          TEXT NOT NULL,
    ended_at            TEXT,
    duration_ms         INTEGER,
    mode                TEXT NOT NULL,
    question            TEXT,
    status              TEXT NOT NULL DEFAULT 'in_progress',
    error_message       TEXT,
    total_tokens_input  INTEGER,
    total_tokens_output INTEGER,
    total_cost_usd      DOUBLE PRECISION,
    tool_call_count     INTEGER NOT NULL DEFAULT 0,
    round_count         INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS trace_events (
    event_id            TEXT PRIMARY KEY,
    trace_id            TEXT NOT NULL
        REFERENCES trace_sessions(trace_id) ON DELETE CASCADE,
    sequence            INTEGER NOT NULL,
    timestamp           TEXT NOT NULL,
    component           TEXT NOT NULL,
    event_type          TEXT NOT NULL,
    duration_ms         INTEGER,
    round_num           INTEGER,
    tool_name           TEXT,
    tool_input_json     TEXT,
    tool_output_summary TEXT,
    status              TEXT,
    metadata_json       TEXT
);

CREATE TABLE IF NOT EXISTS trace_metrics (
    trace_id                TEXT PRIMARY KEY
        REFERENCES trace_sessions(trace_id) ON DELETE CASCADE,
    latency_total_ms        INTEGER,
    latency_preflight_ms    INTEGER,
    latency_llm_ms          INTEGER,
    latency_tools_ms        INTEGER,
    tool_calls_by_name_json TEXT,
    tokens_input            INTEGER,
    tokens_output           INTEGER,
    tokens_cached_input     INTEGER,
    cost_usd                DOUBLE PRECISION,
    errors_count            INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_events_trace      ON trace_events(trace_id, sequence);
CREATE INDEX IF NOT EXISTS idx_events_component  ON trace_events(component);
CREATE INDEX IF NOT EXISTS idx_events_tool       ON trace_events(tool_name);
CREATE INDEX IF NOT EXISTS idx_sessions_conv     ON trace_sessions(conversation_id);
CREATE INDEX IF NOT EXISTS idx_sessions_started  ON trace_sessions(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_sessions_mode     ON trace_sessions(mode);
CREATE INDEX IF NOT EXISTS idx_sessions_status   ON trace_sessions(status);
