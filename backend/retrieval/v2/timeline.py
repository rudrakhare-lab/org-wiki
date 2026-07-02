"""Timeline weighting for retrieval-v2 candidates.

Encodes the CLAUDE.md §5 Step 2 rules ("Jira evidence is a timeline") that were
previously enforced only in the prompt layer. Retrieval now emits candidates
tagged with a categorical bucket AND ranked by a continuous timeline_score, so
`deep_system_prompt.py`'s Latest/Historical rendering has structured input
instead of raw dates it must re-derive from.

Env knobs (defaults per spec §5.1):
  CONWO_RETRIEVAL_V2_TIMELINE_HALFLIFE_DAYS   default 180.0
  CONWO_RETRIEVAL_V2_TIMELINE_LATEST_DAYS     default 180
  CONWO_RETRIEVAL_V2_TIMELINE_STALE_DAYS      default 180
"""
from __future__ import annotations
import math
import os
from datetime import datetime, timezone
from typing import Iterable

HALFLIFE_DAYS = float(os.getenv("CONWO_RETRIEVAL_V2_TIMELINE_HALFLIFE_DAYS", "180"))
LATEST_DAYS   = int(os.getenv("CONWO_RETRIEVAL_V2_TIMELINE_LATEST_DAYS",   "180"))
STALE_DAYS    = int(os.getenv("CONWO_RETRIEVAL_V2_TIMELINE_STALE_DAYS",    "180"))

STATUS_WEIGHTS = {
    "done_resolved": 1.00,   # status_category='done' AND resolved_at IS NOT NULL
    "done":          0.90,   # status_category='done' AND resolved_at IS NULL
    "indeterminate": 0.75,
    "new":           0.65,
}
_FLOOR = 0.05


def _utcnow() -> datetime:
    """Indirection so tests can freeze time via monkeypatch."""
    return datetime.now(timezone.utc)


def _days_since(dt) -> float | None:
    """Days elapsed since `dt`, or None if `dt` is absent/unparseable.

    `dt` is normally a datetime (psycopg maps timestamptz -> datetime), but
    at least one deployment has returned an ISO-format string instead
    (confirmed in production: AttributeError, 'str' object has no attribute
    'tzinfo', on every /query request reaching this path). Parse defensively
    rather than assume a type; an unparseable value degrades to "unknown"
    (None) the same way a missing date already does, instead of crashing.
    """
    if dt is None:
        return None
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt)
        except ValueError:
            return None
    if not isinstance(dt, datetime):
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return max((_utcnow() - dt).total_seconds() / 86400.0, 0.0)


def _status_tier(row: dict) -> str:
    sc = (row.get("status_category") or "").lower()
    if sc == "done" and row.get("resolved_at") is not None:
        return "done_resolved"
    if sc == "done":
        return "done"
    if sc == "indeterminate":
        return "indeterminate"
    return "new"


def assign_bucket(row: dict) -> str:
    """Return the bucket for one candidate row.

    CLAUDE.md §5 Step 2 semantics, simplified to the fields available on a
    candidate row:
      LATEST     — updated_at OR resolved_at within LATEST_DAYS
                   OR resolved with substantive content
                   (resolved_at IS NOT NULL AND comment_count >= 2)
      STALE_OPEN — status_category IN {new, indeterminate}
                   AND days_since(updated_at) > STALE_DAYS
      HISTORICAL — everything else

    Note: CLAUDE.md's "substantive resolution" also requires >=500 chars of
    body+comments; that clause is dropped here because the candidate row has
    no character-length field to check it against.
    """
    days_updated  = _days_since(row.get("updated_at"))
    days_resolved = _days_since(row.get("resolved_at"))
    # Substantive-resolution branch: resolved with 2+ comments overrides age.
    if row.get("resolved_at") is not None and (row.get("comment_count") or 0) >= 2:
        return "latest"
    if days_updated is not None and days_updated <= LATEST_DAYS:
        return "latest"
    if days_resolved is not None and days_resolved <= LATEST_DAYS:
        return "latest"
    sc = (row.get("status_category") or "").lower()
    if sc in {"new", "indeterminate"} and days_updated is not None and days_updated > STALE_DAYS:
        return "stale_open"
    return "historical"


def timeline_score(row: dict) -> float:
    """Continuous decay × status-tier multiplier, floored at 0.05."""
    days_updated  = _days_since(row.get("updated_at"))
    days_resolved = _days_since(row.get("resolved_at"))
    # Use the more recent of updated / resolved for decay.
    ages = [d for d in (days_updated, days_resolved) if d is not None]
    days = min(ages) if ages else float("inf")
    decay = 0.5 ** (days / HALFLIFE_DAYS) if math.isfinite(days) else 0.0
    status = STATUS_WEIGHTS[_status_tier(row)]
    return max(decay * status, _FLOOR)


def apply_timeline(candidates: list[dict]) -> list[dict]:
    """Attach `bucket` and `timeline_score` to each candidate (in-place) and
    re-sort by `fused_score * timeline_score` descending. Returns the same
    list (for chaining).
    """
    for c in candidates:
        c["bucket"] = assign_bucket(c)
        c["timeline_score"] = timeline_score(c)
    candidates.sort(
        key=lambda c: (c.get("fused_score") or 0.0) * c["timeline_score"],
        reverse=True,
    )
    return candidates


def bucket_counts(candidates: Iterable[dict]) -> dict[str, int]:
    """Return {latest: N, historical: N, stale_open: N} counts."""
    out = {"latest": 0, "historical": 0, "stale_open": 0}
    for c in candidates:
        b = c.get("bucket")
        if b in out:
            out[b] += 1
    return out
