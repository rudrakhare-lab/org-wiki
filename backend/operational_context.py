"""
Per-query operational context — surfaces freshness signals to the model.

Pulls a compact status snapshot from `admin_api.get_sync_status()` and renders
ONLY the signals that are "interesting" (stale mirror, non-zero pending
feedback, empty mirror). When everything is clean, returns "" so we don't
add prompt noise.

Cached per-process for 5 minutes so we don't hit SQLite + log files on every
single query.
"""
from __future__ import annotations

import json
import re
import time
from datetime import datetime, timezone

_CACHE: dict = {"value": None, "ts": 0.0}
_TTL_SECONDS = 300  # 5 minutes
_STALE_THRESHOLD_HOURS = 36


def get_context_block() -> str:
    """Return a compact operational-context block, or '' if nothing interesting."""
    now = time.time()
    if _CACHE["value"] is None or now - _CACHE["ts"] > _TTL_SECONDS:
        _CACHE["value"] = _compute_status()
        _CACHE["ts"] = now
    status = _CACHE["value"] or {}
    lines: list[str] = []

    # Jira freshness — empty mirror is a hard error, stale is a soft warning.
    # Prefer the authoritative `most_recent_successful_sync` timestamp (G31).
    # Fall back to the legacy `last_sync_line` parse if the new field isn't
    # present (e.g. old admin_api version) or is empty (no successful sync
    # has ever been logged).
    jira = status.get("jira") or {}
    mirror_count = jira.get("ticket_count", 0)
    if mirror_count == 0:
        lines.append("⚠️ Jira mirror is empty — no ticket data available.")
    else:
        age_h: float | None = None
        success_ts = jira.get("most_recent_successful_sync") or ""
        if success_ts:
            age_h = _age_hours(success_ts)
        elif jira.get("last_sync_line"):
            age_h = _hours_since_last_sync_line(jira["last_sync_line"])
        if age_h is not None and age_h > _STALE_THRESHOLD_HOURS:
            lines.append(
                f"⚠️ Jira mirror last successful sync is {age_h:.0f}h old — "
                f"verify freshness before citing recent tickets."
            )
        elif success_ts == "" and jira.get("last_log_line"):
            # No successful sync ever found, but logs exist — alert harder
            lines.append(
                "⚠️ Jira mirror log shows no successful sync (no 'ALL DONE:' "
                "line) — sync may be broken; verify before citing tickets."
            )

    # Pending feedback queue
    fb = status.get("feedback") or {}
    pending = fb.get("pending_count", 0)
    if pending > 0:
        lines.append(f"Pending feedback awaiting admin review: {pending} items.")

    if not lines:
        return ""
    return "**Operational context:**\n" + "\n".join(f"- {ln}" for ln in lines) + "\n\n"


def _hours_since_last_sync_line(line: str) -> float | None:
    """Parse a timestamp from the sync log line. Tries JSON-log first
    (admin_api.get_sync_status returns the raw log line, which jira_sync.py
    emits as JSON with a `ts` field), regex fallback for plain text.
    """
    if not isinstance(line, str) or not line.strip():
        return None
    # JSON-formatted log line — jira_sync.py default emit
    try:
        obj = json.loads(line)
        if isinstance(obj, dict) and obj.get("ts"):
            return _age_hours(str(obj["ts"]))
    except (json.JSONDecodeError, TypeError):
        pass
    # Plain-timestamp regex fallback
    m = re.search(r"(\d{4}-\d{2}-\d{2})[T ](\d{2}:\d{2}(?::\d{2})?)", line)
    if not m:
        return None
    return _age_hours(f"{m.group(1)}T{m.group(2)}")


def _age_hours(ts_str: str) -> float | None:
    """Parse an ISO-8601-ish timestamp and return hours since it (UTC-naive)."""
    try:
        # Handle trailing Z and missing tz
        normalized = ts_str.replace("Z", "+00:00") if ts_str.endswith("Z") else ts_str
        ts = datetime.fromisoformat(normalized)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - ts).total_seconds() / 3600
    except (ValueError, TypeError):
        return None


def _compute_status() -> dict:
    """Call admin_api.get_sync_status() with a safety net so a failure here
    never blocks a query."""
    try:
        from backend import admin_api
        return admin_api.get_sync_status()
    except Exception:
        return {}


def _reset_cache_for_testing() -> None:
    """Clear the module-level cache. Tests call this between scenarios."""
    _CACHE["value"] = None
    _CACHE["ts"] = 0.0
