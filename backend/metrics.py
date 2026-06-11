"""
Prometheus metrics — HTTP RED metrics + Postgres pool gauges, exposed at /metrics.

Uses raw prometheus_client (no web-framework coupling, so no FastAPI/Starlette
version conflict). The HTTP middleware is **pure ASGI** — it only wraps `send`
to read the response status, never buffers the body, so the SSE streaming
endpoint (/query/stream) is unaffected (Starlette's BaseHTTPMiddleware would
break streaming; this does not).

Cardinality: the `path` label is the matched route TEMPLATE
(e.g. /conversations/{conversation_id}), never the raw URL, so IDs don't explode
the label space. Unmatched requests (404) collapse to "__unmatched__".

Scope: each replica runs uvicorn --workers 1, so the default process-global
registry is correct — Prometheus scrapes each pod and aggregates via PromQL.
(If you ever run >1 worker per container, switch to prometheus_client multiprocess
mode via PROMETHEUS_MULTIPROC_DIR.)
"""
from __future__ import annotations

import time

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)
from starlette.responses import Response

# ── Metrics ─────────────────────────────────────────────────────────────────
_REQUESTS = Counter(
    "conwo_http_requests_total",
    "Total HTTP requests, by method, route template, and status code.",
    ["method", "path", "status"],
)
_LATENCY = Histogram(
    "conwo_http_request_duration_seconds",
    "HTTP request latency in seconds, by method and route template.",
    ["method", "path"],
)
_IN_PROGRESS = Gauge(
    "conwo_http_requests_in_progress",
    "Number of HTTP requests currently being served.",
)

_DB_POOL_SIZE = Gauge("conwo_db_pool_size", "Postgres pool: total connections.")
_DB_POOL_AVAILABLE = Gauge("conwo_db_pool_available", "Postgres pool: idle connections.")
_DB_POOL_WAITING = Gauge(
    "conwo_db_pool_requests_waiting", "Postgres pool: requests waiting for a connection."
)


class PrometheusMiddleware:
    """Pure-ASGI middleware: records request count, latency, and in-flight gauge.
    Streaming-safe — wraps only `send` to capture the status code."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope.get("path") == "/metrics":
            await self.app(scope, receive, send)
            return

        _IN_PROGRESS.inc()
        start = time.perf_counter()
        status_holder = {"code": 500}  # default if the app errors before sending

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                status_holder["code"] = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            duration = time.perf_counter() - start
            _IN_PROGRESS.dec()
            route = scope.get("route")
            path = getattr(route, "path", None) or "__unmatched__"
            method = scope.get("method", "UNKNOWN")
            _LATENCY.labels(method, path).observe(duration)
            _REQUESTS.labels(method, path, str(status_holder["code"])).inc()


def _refresh_pool_gauges() -> None:
    """Update the DB pool gauges from psycopg_pool stats. Called on each scrape.
    Fail-open: a stats hiccup must not break the metrics endpoint."""
    try:
        from backend import db
        pool = db._pool
        if pool is None:
            return
        stats = pool.get_stats()
        _DB_POOL_SIZE.set(stats.get("pool_size", 0))
        _DB_POOL_AVAILABLE.set(stats.get("pool_available", 0))
        _DB_POOL_WAITING.set(stats.get("requests_waiting", 0))
    except Exception:
        pass


def setup_metrics(app) -> None:
    """Attach the metrics middleware and expose GET /metrics (unauthenticated,
    like /health — restrict via network policy / ServiceMonitor as needed)."""
    app.add_middleware(PrometheusMiddleware)

    @app.get("/metrics", include_in_schema=False)
    def metrics() -> Response:
        _refresh_pool_gauges()
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
