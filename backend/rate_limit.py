"""
Per-user daily rate limiter, backed by PostgreSQL (table: rate_limits).

Was an in-memory dict — that counted PER REPLICA, so under N load-balanced
replicas the effective daily limit was N× the intended value. The counter now
lives in Postgres so the limit is global across replicas. Resets at midnight
UTC (the `day` column is the UTC date; we only ever consult today's row).

Admin role bypasses the limit entirely. Fail-open: if the rate-limit store is
unreachable, the request is ALLOWED (a limiter hiccup must not block users).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from backend import db

_log = logging.getLogger("uvicorn.error")

DAILY_LIMIT = 30


def check_rate_limit(token: str, role: str) -> bool:
    """Return True if the request is allowed, False if the daily limit is exceeded.

    Atomic increment-then-check via a single UPSERT — race-free across replicas.
    A denied request still increments the counter (harmless; the row resets at
    midnight UTC). Fail-open on any DB error.
    """
    if role == "admin":
        return True

    today = datetime.now(timezone.utc).date().isoformat()
    try:
        with db.connection() as conn:
            row = conn.execute(
                "INSERT INTO rate_limits (token, day, count) VALUES (%s, %s, 1) "
                "ON CONFLICT (token, day) DO UPDATE SET count = rate_limits.count + 1 "
                "RETURNING count",
                (token, today),
            ).fetchone()
        new_count = row[0]
        return new_count <= DAILY_LIMIT
    except Exception as exc:
        # Fail-open: never block a legitimate request because the limiter store
        # is momentarily unavailable.
        _log.warning("rate_limit check failed (allowing request): %s", exc)
        return True
