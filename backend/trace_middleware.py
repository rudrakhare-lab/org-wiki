"""
trace_middleware.py — FastAPI HTTP-boundary tracing.

Responsibilities:
  - Mint trace_id (uuid4) at the HTTP boundary, store on request.state.trace_id
    so sync AND async handlers can read it (Decision 1A — explicit passing,
    NO ContextVar).
  - Only opens a trace SESSION for traced endpoints (/query, /query/stream).
    Other routes (health, conversations CRUD, admin) get an X-Trace-ID header
    for correlation but no session row (keeps the DB query-focused).
  - record request_start / request_end with total wall-clock latency.
  - On unhandled exception: record an `error` event + request_end(500), then
    re-raise so FastAPI's normal error handling is unchanged.
  - Fail-open: trace_store calls never raise (guaranteed by trace_store), but
    we also guard trace_id minting itself.

FK-ORDERING (verified): trace_events has a real FK → trace_sessions(trace_id)
with foreign_keys=ON. So the session ROW must exist before request_start is
inserted, otherwise the event is dropped by fail-open. Therefore:
  - Middleware calls start_session FIRST (mode='unknown' hint, no body parse) to
    CREATE the parent row, then records request_start.
  - The HANDLER calls start_session AGAIN (UPSERT) to enrich it with the real
    mode/question/conversation_id, and owns the authoritative end_session.
start_session is an idempotent UPSERT (see trace_store.start_session), so the
double call is safe; started_at/status are set once and never overwritten.
"""
from __future__ import annotations

import time
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from backend import trace_store

# Endpoints that open a full trace session (handler calls start_session).
_TRACED_PATHS = {"/query", "/query/stream"}


class TraceMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Mint id (guarded — a failure here must not break the request).
        try:
            trace_id = str(uuid4())
            request.state.trace_id = trace_id
        except Exception:
            request.state.trace_id = None
            return await call_next(request)

        traced = request.url.path in _TRACED_PATHS and request.method != "OPTIONS"
        start = time.perf_counter()

        if traced:
            # Create the parent session row FIRST (FK requires it before any event).
            # mode is a hint here (body not parsed yet); the handler UPSERTs the real mode.
            trace_store.start_session(
                trace_id, mode=(request.query_params.get("mode") or "unknown"))
            trace_store.record_event(
                trace_id, component="api_gateway", event_type="request_start",
                metadata={
                    # PII: store the SALTED HASH only, never the raw email (Resolution 2).
                    "user_email_hash": trace_store.hash_user_email(request.headers.get("x-user-email")),
                    "mode": request.query_params.get("mode"),           # hint only; handler authoritative
                    "headers_subset": {"user-agent": request.headers.get("user-agent")},
                },
            )

        try:
            response: Response = await call_next(request)
        except Exception as exc:
            dur_ms = int((time.perf_counter() - start) * 1000)
            if traced:
                trace_store.record_event(
                    trace_id, component="api_gateway", event_type="error",
                    duration_ms=dur_ms, status="error",
                    metadata={"exception_type": type(exc).__name__,
                              "exception_message": str(exc)[:500], "where": "middleware"},
                )
                trace_store.record_event(
                    trace_id, component="api_gateway", event_type="request_end",
                    duration_ms=dur_ms, status="error", metadata={"status_code": 500},
                )
                # Mark the session itself failed (handler may not have reached end_session).
                trace_store.end_session(trace_id, status="error", error_message=str(exc)[:500])
            raise  # FastAPI handles the 500 exactly as before

        dur_ms = int((time.perf_counter() - start) * 1000)
        # Correlation header for the client (X-Trace-ID).
        try:
            response.headers["X-Trace-ID"] = trace_id
        except Exception:
            pass
        if traced:
            trace_store.record_event(
                trace_id, component="api_gateway", event_type="request_end",
                duration_ms=dur_ms, status="ok",
                metadata={"status_code": response.status_code,
                          "response_size_bytes": int(response.headers.get("content-length", 0) or 0)},
            )
        return response


# Registration (in api.py, after CORS):
#   from backend.trace_middleware import TraceMiddleware
#   app.add_middleware(TraceMiddleware)
#
# Health endpoint for Step 3c verification (added in api.py):
#   @app.get("/trace/health")
#   def trace_health():
#       return {"ok": True, "db": str(trace_store._DB_PATH),
#               "exists": trace_store._DB_PATH.exists(),
#               "enabled": trace_store._check_tracing_enabled()}
#
# ── Session lifecycle split (Resolution 3 + FK-ordering fix) ──────────────────
# Middleware: creates the row (start_session hint) + request_start/request_end +
#   latency + a safety-net end_session(status='error') ONLY on an unhandled
#   exception that propagates back through call_next.
# Handlers: enrich via start_session (real mode/question) and own the
#   authoritative end_session.
#   - /query (sync): start_session early; end_session after orchestrator.run.
#   - /query/stream (CASE B — verified): work runs INSIDE an async generator
#     (event_source), so end_session lives in the GENERATOR'S `finally`, not the
#     handler's. client_disconnect is caught via (asyncio.CancelledError,
#     GeneratorExit). See /tmp/insertion_points.md item #2 for the exact code.
#
# request_end caveat for streaming: middleware's request_end fires when response
# HEADERS are sent (time-to-first-byte), NOT at stream close. Use
# trace_sessions.duration_ms (start→end_session) as the authoritative stream latency.
