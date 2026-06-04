"""
trace_store.py — request-lifecycle tracing backed by raw/traces/traces.sqlite.

Design contract:
  - FAIL-OPEN: any storage failure is logged and swallowed. A tracing error
    must NEVER break a user request.
  - Separate SQLite file + connections from conversations.sqlite.
  - Single serialized writer (module-level conn + Lock) → free `sequence`
    atomicity. Dashboard reads open their own read-only connections.
  - trace_id is passed EXPLICITLY through the call graph (no ContextVar).
  - Tri-state enablement: checked once; if the DB/schema is absent tracing is
    disabled cleanly for the whole process (no per-call retry, no log spam).

# ═══════════════════════════════════════════════════════════════════════════
# metadata_json shapes by event_type  (Tightening 2 — callers MUST follow)
# ═══════════════════════════════════════════════════════════════════════════
#   request_start          : {user_email_hash, mode, headers_subset: {...}}   # NO raw email
#   request_end            : {status_code, response_size_bytes}
#   preflight_wiki         : {results_count, top_paths: [str, ...]}
#   preflight_jira         : {bucket_counts: {LATEST, HISTORICAL, "STALE-OPEN"}}
#   preflight_module_tagged: {module_count, ticket_count, modules: [str, ...]}
#   preflight_related_module:{module_count, ticket_count, via_module}
#   round_start            : {} (optional — round_num column already carries it)
#   tool_call              : {} (input/output already in dedicated columns)
#   llm_request            : {model} (optional, pre-call)
#   llm_response           : {model, input_tokens, output_tokens,
#                             cache_read_input_tokens, cache_creation_input_tokens,
#                             stop_reason}
#   external_http          : DEFERRED TO v2 (not emitted; tool_call covers PMS granularity)
#   error                  : {exception_type, exception_message, where}
#
# ═══════════════════════════════════════════════════════════════════════════
# Sanitization (Tightening 3)
# ═══════════════════════════════════════════════════════════════════════════
#   PRIMARY source-of-truth for tool inputs/outputs is registry.ToolRegistry,
#   which already runs _SECRET_RE over tool_input/output BEFORE handing the
#   trace entry to callers. trace_store callers MUST pass already-sanitized
#   tool data.
#   DEFENSIVE final net: record_event runs _scrub() over every string field
#   (tool_input_json, tool_output_summary, metadata_json) before INSERT, using
#   the SAME secret pattern as registry. Bearer tokens, JWTs, and 40+ char
#   tokens become [REDACTED]. Cookies/tokens never land in the DB.
#   user_email is NEVER stored raw — only hash_user_email() (SHA-256 + salt,
#   16 chars). BUID is stored intentionally (operational, not a secret).
#
# Status enum: in_progress | success | error | client_disconnect | orphaned
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

_log = logging.getLogger("trace_store")

# ── Paths ────────────────────────────────────────────────────────────────────
_ROOT = Path(__file__).resolve().parent.parent          # backend/ -> repo root
_TRACES_DIR = _ROOT / "raw" / "traces"
_DB_PATH = _TRACES_DIR / "traces.sqlite"


def _get_db_path() -> Path:
    return _DB_PATH


# ── Secret scrub (mirror of registry._SECRET_RE — defensive final net) ────────
_SECRET_RE = re.compile(
    r"("
    r"Bearer\s+[A-Za-z0-9\-_\.=]+"
    r"|eyJ[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+"
    r"|[A-Za-z0-9]{40,}"
    r")"
)

def _scrub(s: str | None) -> str | None:
    if not s:
        return s
    return _SECRET_RE.sub("[REDACTED]", s)


# ── PII: hash user email (Resolution 2) ───────────────────────────────────────
_USER_HASH_SALT = os.environ.get("TRACE_USER_HASH_SALT", "conwo-default-salt-change-in-production")

def hash_user_email(email: str | None) -> str | None:
    """Hash user email for trace correlation WITHOUT storing PII. 16-char prefix —
    sufficient for correlation, not reversible. Set TRACE_USER_HASH_SALT in prod."""
    if not email:
        return None
    return hashlib.sha256(f"{_USER_HASH_SALT}:{email}".encode("utf-8")).hexdigest()[:16]


# ── Pricing (Resolution 2 of Step 1) ──────────────────────────────────────────
# Source: Anthropic prompt caching pricing (5-min TTL).
#   cache_write = 1.25× base input ;  cache_read = 0.10× base input
# Last verified: 2026-05-29. Update if Anthropic announces price changes.
_PRICING = {
    "claude-sonnet-4-6": {"input": 3.00, "output": 15.00, "cache_read": 0.30, "cache_write": 3.75},
    "claude-haiku-4-5":  {"input": 0.80, "output":  4.00, "cache_read": 0.08, "cache_write": 1.00},
}
_pricing_warned: set[str] = set()


def cost_for(model: str, usage: dict) -> float:
    """USD cost for one llm_response usage dict. Unknown model → 0.0 (fail-open)."""
    p = _PRICING.get(model)
    if not p:
        if model not in _pricing_warned:
            _log.warning("trace_store: no pricing for model %r — cost counted as 0", model)
            _pricing_warned.add(model)
        return 0.0
    return (
        usage.get("input_tokens", 0) * p["input"]
        + usage.get("output_tokens", 0) * p["output"]
        + usage.get("cache_read_input_tokens", 0) * p["cache_read"]
        + usage.get("cache_creation_input_tokens", 0) * p["cache_write"]
    ) / 1_000_000


# ── Tri-state enablement (CONCERN 1) ──────────────────────────────────────────
# None = unchecked · True = ok · False = disabled for the rest of the process.
_TRACING_ENABLED: bool | None = None
_ENABLE_LOCK = threading.Lock()


def _check_tracing_enabled() -> bool:
    """Checked once. Missing file OR missing schema → disabled cleanly for the
    whole process lifetime. No auto-create (would leave a half-broken state).
    No per-call retry (would spam logs)."""
    global _TRACING_ENABLED
    if _TRACING_ENABLED is not None:
        return _TRACING_ENABLED
    with _ENABLE_LOCK:
        if _TRACING_ENABLED is not None:        # double-checked under lock
            return _TRACING_ENABLED
        try:
            db_path = _get_db_path()
            if not db_path.exists():
                _log.warning("trace DB not found at %s — tracing disabled for this session. "
                             "Run scripts/init_traces_db.py to enable.", db_path)
                _TRACING_ENABLED = False
                return False
            conn = sqlite3.connect(db_path)
            cur = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='trace_sessions'")
            ok = cur.fetchone() is not None
            conn.close()
            if not ok:
                _log.warning("trace DB exists but schema not initialized — tracing disabled. "
                             "Run scripts/init_traces_db.py.")
                _TRACING_ENABLED = False
                return False
            _TRACING_ENABLED = True
            return True
        except Exception as exc:
            _log.warning("trace enablement check failed: %s — tracing disabled", exc)
            _TRACING_ENABLED = False
            return False


# ── Writer connection ──────────────────────────────────────────────────────────
_WRITE_LOCK = threading.Lock()
_conn: sqlite3.Connection | None = None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def _get_conn() -> sqlite3.Connection | None:
    """Lazy module-level writer connection. Assumes enablement already passed."""
    global _conn
    if _conn is not None:
        return _conn
    try:
        _conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
        _conn.execute("PRAGMA journal_mode=WAL;")
        _conn.execute("PRAGMA synchronous=NORMAL;")
        _conn.execute("PRAGMA foreign_keys=ON;")
        _conn.execute("PRAGMA busy_timeout=5000;")
        return _conn
    except Exception as exc:
        _log.warning("trace_store: could not open writer DB (tracing OFF): %s", exc)
        return None


def _write(fn) -> None:
    """Run a write under the lock with explicit rollback-on-failure (CONCERN 2).
    The lock is ALWAYS released (`with`); on any error we roll back then re-raise
    so the caller's fail-open try/except logs it. Never leaves a half-committed conn."""
    conn = _get_conn()
    if conn is None:
        return
    with _WRITE_LOCK:
        try:
            fn(conn)
            conn.commit()
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass   # rollback itself failed — nothing more we can safely do
            raise      # propagate to the public fn's fail-open handler


# ── Public API ──────────────────────────────────────────────────────────────
def start_session(trace_id: str, *, mode: str, question: str | None = None,
                  conversation_id: str | None = None, message_id: str | None = None) -> None:
    """UPSERT the session row. Called TWICE per traced request:
      1. by the middleware FIRST (mode='unknown' hint) — creates the parent row
         so subsequent trace_events (request_start, preflight…) satisfy the FK.
      2. by the handler — enriches with real mode/question/conversation_id.
    started_at and status are set on insert and never overwritten (earliest wins)."""
    if not trace_id or not _check_tracing_enabled():
        return
    question_val = (_scrub(question) or "")[:500] if question else None
    try:
        def op(conn):
            conn.execute(
                "INSERT INTO trace_sessions "
                "(trace_id, conversation_id, message_id, started_at, mode, question, status) "
                "VALUES (?,?,?,?,?,?, 'in_progress') "
                "ON CONFLICT(trace_id) DO UPDATE SET "
                "  mode = excluded.mode, "
                "  question = COALESCE(excluded.question, trace_sessions.question), "
                "  conversation_id = COALESCE(excluded.conversation_id, trace_sessions.conversation_id), "
                "  message_id = COALESCE(excluded.message_id, trace_sessions.message_id)",
                (trace_id, conversation_id, message_id, _now_iso(), mode, question_val),
            )
        _write(op)
    except Exception as exc:
        _log.warning("trace_store.start_session failed (ignored): %s", exc)


def record_event(trace_id: str, component: str, event_type: str, *,
                 duration_ms: int | None = None, round_num: int | None = None,
                 tool_name: str | None = None, tool_input_json: str | None = None,
                 tool_output_summary: str | None = None, status: str | None = None,
                 metadata: dict | None = None) -> None:
    """Append one event. sequence = MAX+1 within trace (atomic under the lock). Fail-open."""
    if not trace_id or not _check_tracing_enabled():
        return
    try:
        meta_str = _scrub(json.dumps(metadata, default=str)) if metadata else None
        def op(conn):
            cur = conn.cursor()
            cur.execute("SELECT COALESCE(MAX(sequence), -1) + 1 FROM trace_events WHERE trace_id=?", (trace_id,))
            seq = cur.fetchone()[0]
            cur.execute(
                "INSERT INTO trace_events (event_id, trace_id, sequence, timestamp, component, "
                "event_type, duration_ms, round_num, tool_name, tool_input_json, "
                "tool_output_summary, status, metadata_json) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (str(uuid4()), trace_id, seq, _now_iso(), component, event_type, duration_ms,
                 round_num, tool_name, _scrub(tool_input_json),
                 _scrub(tool_output_summary), status, meta_str),
            )
        _write(op)
    except Exception as exc:
        _log.warning("trace_store.record_event failed (ignored): %s", exc)


def end_session(trace_id: str, *, status: str, error_message: str | None = None,
                message_id: str | None = None) -> None:
    """Finalize: compute duration, roll up trace_metrics from events. Fail-open.
    status ∈ success | error | client_disconnect (orphaned is set only by reconcile)."""
    if not trace_id or not _check_tracing_enabled():
        return
    try:
        def op(conn):
            cur = conn.cursor()
            cur.execute("SELECT started_at FROM trace_sessions WHERE trace_id=?", (trace_id,))
            row = cur.fetchone()
            if row is None:
                return  # never started
            started = datetime.fromisoformat(row[0])
            ended = datetime.now(timezone.utc)
            dur_ms = int((ended - started).total_seconds() * 1000)
            agg = _aggregate_events(cur, trace_id)
            cur.execute(
                "UPDATE trace_sessions SET ended_at=?, duration_ms=?, status=?, error_message=?, "
                "message_id=COALESCE(?, message_id), total_tokens_input=?, total_tokens_output=?, "
                "total_cost_usd=?, tool_call_count=?, round_count=? WHERE trace_id=?",
                (ended.isoformat(timespec="milliseconds"), dur_ms, status, error_message,
                 message_id, agg["tokens_input"], agg["tokens_output"], agg["cost_usd"],
                 agg["tool_calls"], agg["rounds"], trace_id),
            )
            cur.execute(
                "INSERT OR REPLACE INTO trace_metrics (trace_id, latency_total_ms, "
                "latency_preflight_ms, latency_llm_ms, latency_tools_ms, tool_calls_by_name_json, "
                "tokens_input, tokens_output, tokens_cached_input, cost_usd, errors_count) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (trace_id, dur_ms, agg["preflight_ms"], agg["llm_ms"], agg["tools_ms"],
                 json.dumps(agg["tool_by_name"]), agg["tokens_input"], agg["tokens_output"],
                 agg["tokens_cached"], agg["cost_usd"], agg["errors"]),
            )
        _write(op)
    except Exception as exc:
        _log.warning("trace_store.end_session failed (ignored): %s", exc)


def _aggregate_events(cur, trace_id: str) -> dict:
    """Roll up trace_events → trace_metrics. claude-code: no llm_response usage → tokens/cost NULL."""
    out = {"preflight_ms": 0, "llm_ms": 0, "tools_ms": 0, "tokens_input": None,
           "tokens_output": None, "tokens_cached": None, "cost_usd": None,
           "tool_calls": 0, "rounds": 0, "errors": 0, "tool_by_name": {}}
    cur.execute("SELECT component, event_type, duration_ms, round_num, tool_name, status, metadata_json "
                "FROM trace_events WHERE trace_id=?", (trace_id,))
    tok_in = tok_out = tok_cached = 0
    cost = 0.0
    saw_usage = False
    max_round = 0
    for component, etype, dur, rnum, tname, status, meta in cur.fetchall():
        dur = dur or 0
        if component == "preflight":
            out["preflight_ms"] += dur
        elif component == "llm_call":
            out["llm_ms"] += dur
        elif component == "tool_execution":
            out["tools_ms"] += dur
        if etype == "tool_call" and tname:
            out["tool_calls"] += 1
            out["tool_by_name"][tname] = out["tool_by_name"].get(tname, 0) + 1
        if rnum and rnum > max_round:
            max_round = rnum
        if status == "error":
            out["errors"] += 1
        if etype == "llm_response" and meta:
            try:
                u = json.loads(meta)
                tok_in += u.get("input_tokens", 0) or 0
                tok_out += u.get("output_tokens", 0) or 0
                tok_cached += u.get("cache_read_input_tokens", 0) or 0
                cost += cost_for(u.get("model", ""), u)
                saw_usage = True
            except Exception:
                pass
    out["rounds"] = max_round
    if saw_usage:                       # api mode
        out["tokens_input"], out["tokens_output"] = tok_in, tok_out
        out["tokens_cached"], out["cost_usd"] = tok_cached, round(cost, 6)
    return out


# ── Orphan reconciliation (Tightening 1) ──────────────────────────────────────
def _reconcile_orphans() -> None:
    """Mark sessions left in_progress by a previous backend crash as 'orphaned'. At import."""
    if not _check_tracing_enabled():
        return
    try:
        result = {"n": 0}
        def op(conn):
            cur = conn.cursor()
            cur.execute(
                "UPDATE trace_sessions SET status='orphaned', ended_at=COALESCE(ended_at, ?) "
                "WHERE status='in_progress'", (_now_iso(),))
            result["n"] = cur.rowcount
        _write(op)
        if result["n"] > 0:
            _log.info("trace_store: marked %d orphaned session(s) from previous run", result["n"])
    except Exception as exc:
        _log.warning("trace_store: orphan reconciliation failed (ignored): %s", exc)


# ── Read API (dashboard) — own read-only connection, never the writer ─────────
def _read_conn() -> sqlite3.Connection:
    return sqlite3.connect(f"file:{_DB_PATH}?mode=ro", uri=True, check_same_thread=False)


def query_session(trace_id: str) -> dict | None:
    if not _check_tracing_enabled():
        return None
    try:
        c = _read_conn()
        c.row_factory = sqlite3.Row
        s = c.execute("SELECT * FROM trace_sessions WHERE trace_id=?", (trace_id,)).fetchone()
        if s is None:
            c.close()
            return None
        evs = c.execute("SELECT * FROM trace_events WHERE trace_id=? ORDER BY sequence", (trace_id,)).fetchall()
        m = c.execute("SELECT * FROM trace_metrics WHERE trace_id=?", (trace_id,)).fetchone()
        c.close()
        return {"session": dict(s), "events": [dict(e) for e in evs], "metrics": dict(m) if m else None}
    except Exception as exc:
        _log.warning("trace_store.query_session failed: %s", exc)
        return None


# query_sessions(filters, limit) + aggregate_metrics(time_range, filters) for the
# dashboard endpoints are drafted in Step 4 (trace_api_draft.py).

# Reconcile on import (Tightening 1). No-op if DB/schema missing (tracing disabled).
_reconcile_orphans()
