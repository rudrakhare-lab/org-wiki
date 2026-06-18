"""In-process tracker for the admin 'Sync now' full pipeline (fetch + classify).

Single-replica prod: a module-level lock + a private `_running` flag ensure only
one run happens at a time. The worker thread runs the existing delta pipeline
(backend.tools.trigger_sync._trigger_jira_sync_handler → scripts/jira_daily_sync.py)
and records its structured result. Fail-open: nothing here raises into the request
path. Multi-replica safety would need a DB/advisory lock — out of scope today.
"""
from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone
from typing import Any

_log = logging.getLogger("sync_job")
_lock = threading.Lock()
_state: dict[str, Any] = {
    "_running": False,      # private guard, never exposed by status()
    "state": "idle",        # idle | running | done | error
    "started_at": None,
    "ended_at": None,
    "result": None,         # the handler's structured dict (done/error)
    "message": "",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def status() -> dict:
    """Public snapshot of the current job (internal keys stripped)."""
    with _lock:
        return {k: v for k, v in _state.items() if not k.startswith("_")}


def _worker() -> None:
    try:
        from backend.tools.trigger_sync import _trigger_jira_sync_handler
        result = _trigger_jira_sync_handler({"mode": "delta"})
        ok = bool(result.get("success"))
        with _lock:
            _state.update({
                "state": "done" if ok else "error",
                "ended_at": _now(),
                "result": result,
                "message": "" if ok else (result.get("error")
                                          or result.get("done_line") or "sync failed"),
            })
    except Exception as exc:  # never let a worker crash escape
        _log.exception("sync_job worker crashed")
        with _lock:
            _state.update({"state": "error", "ended_at": _now(),
                           "result": None, "message": str(exc)})
    finally:
        with _lock:
            _state["_running"] = False


def start() -> dict:
    """Start the full pipeline in the background unless one is already running."""
    with _lock:
        if _state["_running"]:
            return {"status": "already_running"}
        _state.update({
            "_running": True, "state": "running",
            "started_at": _now(), "ended_at": None, "result": None, "message": "",
        })
    try:
        threading.Thread(target=_worker, name="jira-sync-job", daemon=True).start()
    except Exception as exc:
        with _lock:
            _state.update({"_running": False, "state": "error", "message": str(exc)})
        return {"status": "error", "message": str(exc)}
    return {"status": "started"}
