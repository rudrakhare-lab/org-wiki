"""
trace_api.py — read-only FastAPI endpoints exposing trace data to the frontend.

Registration (in api.py, ONE line — auth applied at include time to avoid a
circular import, since the auth deps live in api.py):

    from backend import trace_api
    app.include_router(trace_api.router, dependencies=[Depends(_require_admin)])

So every /api/traces/* endpoint is admin-only. trace_api imports NOTHING from
api.py (no cycle).

Connection discipline:
  - Pooled connection per request via the _ro() context manager (Row factory,
    autocommit). Returned to the pool on block exit — never .close()'d.
  - If tracing is disabled (schema absent) every endpoint returns an empty/
    zeroed shape rather than 500 (fail-soft).

Percentiles: computed in Python from the durations fetched for the range.

Status filtering: dashboards EXCLUDE 'orphaned' by default (noise); pass
?include_orphaned=true to include. error_rate is defined as
errors / (errors + successes) — rejected/client_disconnect/orphaned never count.
"""
from __future__ import annotations

import json
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from backend import db, trace_store

router = APIRouter(prefix="/api/traces", tags=["traces"])

_TIME_RANGES = {"24h": 1, "7d": 7, "30d": 30}   # → days; "all" → None


def _agent_id(request: Request) -> str:
    """Resolve the active agent_id from request state (set by middleware).
    Defaults to 'conwo' so existing Conwo dashboards are unchanged."""
    return getattr(request.state, "agent_id", "conwo")


# ── helpers ───────────────────────────────────────────────────────────────────
def _cutoff_iso(time_range: str) -> str | None:
    """ISO-8601 cutoff matching the stored started_at format, or None for 'all'."""
    days = _TIME_RANGES.get(time_range)
    if days is None:
        return None
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat(timespec="milliseconds")


@contextmanager
def _ro():
    """Yield a pooled connection (Row factory, autocommit), or None if tracing
    is disabled. Returned to the pool on exit — callers must NOT close it."""
    if not trace_store._check_tracing_enabled():
        yield None
        return
    with db.connection() as conn:
        yield conn


def _percentiles(values: list[int], ps=(50, 95, 99)) -> dict:
    if not values:
        return {f"p{p}": None for p in ps}
    s = sorted(values)
    out = {}
    for p in ps:
        # nearest-rank
        idx = min(len(s) - 1, max(0, int(round((p / 100.0) * len(s) + 0.5)) - 1))
        out[f"p{p}"] = s[idx]
    return out


# ── response models ────────────────────────────────────────────────────────────
class SessionSummary(BaseModel):
    trace_id: str
    started_at: str
    ended_at: str | None = None
    duration_ms: int | None = None
    mode: str
    status: str
    question: str | None = None
    user_email: str | None = None
    total_tokens_input: int | None = None
    total_tokens_output: int | None = None
    total_cost_usd: float | None = None
    tool_call_count: int = 0
    round_count: int = 0


class SessionListResponse(BaseModel):
    total: int                  # count matching filters (ignoring limit/offset)
    limit: int
    offset: int
    sessions: list[SessionSummary]


class SessionDetailResponse(BaseModel):
    session: dict
    events: list[dict]
    metrics: dict | None = None


# ── 1. session list ──────────────────────────────────────────────────────────
@router.get("/sessions", response_model=SessionListResponse)
def list_sessions(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    mode: str = Query("all"),       # api | claude-code | all
    status: str = Query("all"),     # success|error|rejected|client_disconnect|orphaned|all
    since: str | None = Query(None),  # ISO timestamp
    search: str | None = Query(None),  # substring of question
    include_orphaned: bool = Query(False),
    agent_id: str = Depends(_agent_id),
):
    with _ro() as conn:
        if conn is None:
            return SessionListResponse(total=0, limit=limit, offset=offset, sessions=[])
        where, params = ["agent_id = %s"], [agent_id]
        if mode != "all":
            where.append("mode = %s"); params.append(mode)
        if status != "all":
            where.append("status = %s"); params.append(status)
        elif not include_orphaned:
            where.append("status != 'orphaned'")
        if since:
            where.append("started_at >= %s"); params.append(since)
        if search:
            where.append("question ILIKE %s"); params.append(f"%{search}%")
        clause = " AND ".join(where)

        total = conn.execute(f"SELECT COUNT(*) FROM trace_sessions WHERE {clause}", params).fetchone()[0]
        rows = conn.execute(
            f"SELECT trace_id, started_at, ended_at, duration_ms, mode, status, "
            f"substr(question,1,160) AS question, user_email, "
            f"total_tokens_input, total_tokens_output, "
            f"total_cost_usd, tool_call_count, round_count "
            f"FROM trace_sessions WHERE {clause} ORDER BY started_at DESC LIMIT %s OFFSET %s",
            params + [limit, offset],
        ).fetchall()
        return SessionListResponse(
            total=total, limit=limit, offset=offset,
            sessions=[SessionSummary(**dict(r)) for r in rows],
        )


# ── 2. session detail ──────────────────────────────────────────────────────────
@router.get("/sessions/{trace_id}", response_model=SessionDetailResponse)
def get_session(trace_id: str):
    data = trace_store.query_session(trace_id)   # already ordered by sequence
    if data is None:
        raise HTTPException(status_code=404, detail="trace not found")
    return SessionDetailResponse(**data)


# ── 3. dashboard overview ──────────────────────────────────────────────────────
@router.get("/dashboard/overview")
def dashboard_overview(
    time_range: str = Query("7d"),
    include_orphaned: bool = Query(False),
    agent_id: str = Depends(_agent_id),
):
    empty = {"total_queries": 0, "status_breakdown": {}, "error_rate": None,
             "latency_ms": {"avg": None, "p50": None, "p95": None, "p99": None},
             "total_cost_usd": 0.0, "cost_by_day": [], "top_tools": [], "mode_breakdown": {}}
    with _ro() as conn:
        if conn is None:
            return empty
        cutoff = _cutoff_iso(time_range)
        base, params = "FROM trace_sessions WHERE agent_id = %s", [agent_id]
        if cutoff:
            base += " AND started_at >= %s"; params.append(cutoff)
        if not include_orphaned:
            base += " AND status != 'orphaned'"

        status_rows = conn.execute(f"SELECT status, COUNT(*) c {base} GROUP BY status", params).fetchall()
        status_breakdown = {r["status"]: r["c"] for r in status_rows}
        total = sum(status_breakdown.values())
        succ, err = status_breakdown.get("success", 0), status_breakdown.get("error", 0)
        error_rate = (err / (err + succ)) if (err + succ) else None

        durs = [r[0] for r in conn.execute(
            f"SELECT duration_ms {base} AND duration_ms IS NOT NULL "
            f"AND status IN ('success','error')", params).fetchall()]
        avg = round(sum(durs) / len(durs)) if durs else None
        pct = _percentiles(durs)

        total_cost = conn.execute(
            f"SELECT COALESCE(SUM(total_cost_usd),0) {base} AND status IN ('success','error')",
            params).fetchone()[0]
        cost_by_day = [dict(r) for r in conn.execute(
            f"SELECT substr(started_at,1,10) AS \"day\", "
            f"ROUND(SUM(COALESCE(total_cost_usd,0))::numeric,6)::double precision cost, COUNT(*) queries "
            f"{base} AND status IN ('success','error') "
            f"GROUP BY substr(started_at,1,10) ORDER BY substr(started_at,1,10)", params).fetchall()]
        mode_rows = conn.execute(f"SELECT mode, COUNT(*) c {base} GROUP BY mode", params).fetchall()
        mode_breakdown = {r["mode"]: r["c"] for r in mode_rows}

        # top tools — from events in the same window (join sessions for the time filter + agent)
        tparams = [agent_id]
        tclause = "AND s.agent_id = %s"
        if cutoff:
            tclause += " AND s.started_at >= %s"; tparams.append(cutoff)
        top_tools = [dict(r) for r in conn.execute(
            f"SELECT e.tool_name, COUNT(*) call_count FROM trace_events e "
            f"JOIN trace_sessions s ON s.trace_id = e.trace_id "
            f"WHERE e.event_type='tool_call' AND e.tool_name IS NOT NULL {tclause} "
            f"GROUP BY e.tool_name ORDER BY call_count DESC LIMIT 10", tparams).fetchall()]

        return {"total_queries": total, "status_breakdown": status_breakdown,
                "error_rate": error_rate,
                "latency_ms": {"avg": avg, **pct},
                "total_cost_usd": round(total_cost, 6), "cost_by_day": cost_by_day,
                "top_tools": top_tools, "mode_breakdown": mode_breakdown}


# ── 4. dashboard tools ──────────────────────────────────────────────────────────
@router.get("/dashboard/tools")
def dashboard_tools(
    time_range: str = Query("7d"),
    agent_id: str = Depends(_agent_id),
):
    with _ro() as conn:
        if conn is None:
            return {"tools": []}
        cutoff = _cutoff_iso(time_range)
        clause, params = "AND s.agent_id = %s", [agent_id]
        if cutoff:
            clause += " AND s.started_at >= %s"; params.append(cutoff)
        rows = conn.execute(
            f"SELECT e.tool_name, COUNT(*) call_count, "
            f"ROUND(AVG(e.duration_ms)::numeric,1)::double precision avg_duration_ms, "
            f"ROUND((100.0*SUM(CASE WHEN e.status='error' THEN 1 ELSE 0 END)/COUNT(*))::numeric,1)"
            f"::double precision error_rate_pct "
            f"FROM trace_events e JOIN trace_sessions s ON s.trace_id=e.trace_id "
            f"WHERE e.event_type='tool_call' AND e.tool_name IS NOT NULL {clause} "
            f"GROUP BY e.tool_name ORDER BY call_count DESC", params).fetchall()
        return {"tools": [dict(r) for r in rows]}


# ── 5. dashboard errors ──────────────────────────────────────────────────────────
@router.get("/dashboard/errors")
def dashboard_errors(
    time_range: str = Query("7d"),
    limit: int = Query(20, ge=1, le=100),
    agent_id: str = Depends(_agent_id),
):
    # errors_by_component : ALL status='error' events (includes failed tool_calls)
    # exceptions_by_type  : ONLY event_type='error' events (carry exception metadata)
    # recent_exceptions   : last N event_type='error' rows
    with _ro() as conn:
        if conn is None:
            return {"errors_by_component": {}, "exceptions_by_type": {}, "recent_exceptions": []}
        cutoff = _cutoff_iso(time_range)
        clause, params = "AND s.agent_id = %s", [agent_id]
        if cutoff:
            clause += " AND e.timestamp >= %s"; params.append(cutoff)
        comp_rows = conn.execute(
            f"SELECT e.component, COUNT(*) c FROM trace_events e "
            f"JOIN trace_sessions s ON s.trace_id = e.trace_id "
            f"WHERE e.status='error' {clause} GROUP BY e.component ORDER BY c DESC", params).fetchall()
        errors_by_component = {r["component"]: r["c"] for r in comp_rows}

        # exception_type lives in metadata_json — aggregate in Python
        err_rows = conn.execute(
            f"SELECT e.trace_id, e.timestamp, e.metadata_json FROM trace_events e "
            f"JOIN trace_sessions s ON s.trace_id = e.trace_id "
            f"WHERE e.event_type='error' {clause} ORDER BY e.timestamp DESC LIMIT %s",
            params + [limit]).fetchall()
        exceptions_by_type: dict[str, int] = {}
        recent_exceptions = []
        for r in err_rows:
            meta = json.loads(r["metadata_json"]) if r["metadata_json"] else {}
            etype = meta.get("exception_type", "unknown")
            exceptions_by_type[etype] = exceptions_by_type.get(etype, 0) + 1
            recent_exceptions.append({"trace_id": r["trace_id"], "timestamp": r["timestamp"],
                                      "exception_type": etype,
                                      "exception_message": meta.get("exception_message"),
                                      "where": meta.get("where")})
        return {"errors_by_component": errors_by_component,
                "exceptions_by_type": exceptions_by_type,
                "recent_exceptions": recent_exceptions}


# ── 6. dashboard cost ──────────────────────────────────────────────────────────
@router.get("/dashboard/cost")
def dashboard_cost(
    time_range: str = Query("7d"),
    agent_id: str = Depends(_agent_id),
):
    empty = {"cost_by_day": [], "cost_per_query": {"avg": None, "p50": None, "p95": None},
             "tokens": {"input": 0, "output": 0, "cached_input": 0}, "cache_hit_rate": None}
    with _ro() as conn:
        if conn is None:
            return empty
        cutoff = _cutoff_iso(time_range)
        base, params = "FROM trace_sessions WHERE status != 'orphaned' AND agent_id = %s", [agent_id]
        if cutoff:
            base += " AND started_at >= %s"; params.append(cutoff)

        cost_by_day = [dict(r) for r in conn.execute(
            f"SELECT substr(started_at,1,10) AS \"day\", "
            f"ROUND(SUM(COALESCE(total_cost_usd,0))::numeric,6)::double precision cost "
            f"{base} AND status IN ('success','error') "
            f"GROUP BY substr(started_at,1,10) ORDER BY substr(started_at,1,10)", params).fetchall()]
        costs = [r[0] for r in conn.execute(
            f"SELECT total_cost_usd {base} AND total_cost_usd IS NOT NULL "
            f"AND status IN ('success','error')", params).fetchall()]
        avg = round(sum(costs) / len(costs), 6) if costs else None
        # µ$ integers for the nearest-rank percentile, then back to $
        pct = _percentiles([int(c * 1_000_000) for c in costs], ps=(50, 95))
        cost_pct = {k: (v / 1_000_000 if v is not None else None) for k, v in pct.items()}

        # token + cache totals from trace_metrics (api-mode rows; claude-code NULLs ignored)
        mbase = ("FROM trace_metrics m JOIN trace_sessions s ON s.trace_id=m.trace_id "
                 "WHERE s.status IN ('success','error') AND s.agent_id = %s")
        mparams = [agent_id]
        if cutoff:
            mbase += " AND s.started_at >= %s"; mparams.append(cutoff)
        trow = conn.execute(
            f"SELECT COALESCE(SUM(tokens_input),0) ti, COALESCE(SUM(tokens_output),0) to_, "
            f"COALESCE(SUM(tokens_cached_input),0) tc {mbase}", mparams).fetchone()
        ti, to_, tc = trow["ti"], trow["to_"], trow["tc"]
        cache_hit = round(100.0 * tc / (ti + tc), 1) if (ti + tc) else None

        return {"cost_by_day": cost_by_day,
                "cost_per_query": {"avg": avg, **cost_pct},
                "tokens": {"input": ti, "output": to_, "cached_input": tc},
                "cache_hit_rate": cache_hit}
