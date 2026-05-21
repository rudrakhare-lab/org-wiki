"""
In-memory per-user rate limiter.

Counter resets at midnight UTC. Thread-safe via a single lock.
Admin role bypasses the limit entirely.
"""
from __future__ import annotations

import threading
from datetime import date, datetime, timezone

_COUNTS: dict[str, int] = {}
_RESET_DATE: date = date.today()
_LOCK = threading.Lock()

DAILY_LIMIT = 30


def check_rate_limit(token: str, role: str) -> bool:
    """Return True if the request is allowed, False if the daily limit is exceeded."""
    if role == "admin":
        return True

    global _RESET_DATE

    with _LOCK:
        today = datetime.now(timezone.utc).date()
        if today != _RESET_DATE:
            _COUNTS.clear()
            _RESET_DATE = today
        current = _COUNTS.get(token, 0)
        if current >= DAILY_LIMIT:
            return False
        _COUNTS[token] = current + 1
        return True
