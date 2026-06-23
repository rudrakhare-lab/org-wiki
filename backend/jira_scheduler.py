"""In-app nightly Jira sync scheduler.

An alternative to a Kubernetes CronJob: when CONWO_ENABLE_JIRA_CRON is enabled,
the running app itself runs scripts/jira_daily_sync.py once a day at
CONWO_JIRA_CRON_HOUR_UTC (default 02:00 UTC). jira_daily_sync.py does both
stages — jira_sync.py --incremental (Stage 1, writes tickets to the DB) and
classify_jira.py --delta (Stage 2, AI classification).

Single-replica safety: in a StatefulSet, pods are named <name>-0, <name>-1, …
Only the pod whose hostname ends in `-0` runs the scheduler, so scaling to
multiple replicas never double-syncs (which would duplicate work and double the
Anthropic classification cost). On non-k8s hosts (local dev) the hostname won't
match that pattern, so it's treated as the leader.

A sync_runs check skips a second run on the same UTC day if the pod restarts
after the nightly run already happened. Everything is fail-open: a scheduler
problem must never crash the app or block serving traffic.
"""
from __future__ import annotations

import asyncio
import logging
import os
import re
import socket
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

_log = logging.getLogger("jira_scheduler")
_ROOT = Path(__file__).resolve().parent.parent
_SCRIPTS = _ROOT / "scripts"
_STATEFULSET_ORDINAL_RE = re.compile(r"-(\d+)$")


def enabled() -> bool:
    """True when the operator has opted into the in-app nightly sync."""
    return os.getenv("CONWO_ENABLE_JIRA_CRON", "").strip().lower() in {
        "1", "true", "yes", "on"
    }


def _is_leader() -> bool:
    """Only the StatefulSet's pod-0 runs the scheduler. A hostname like
    'conwo-0' → leader; 'conwo-1' → not. A hostname with no ordinal suffix
    (local dev, plain Deployment) → treated as leader."""
    m = _STATEFULSET_ORDINAL_RE.search(socket.gethostname())
    return m.group(1) == "0" if m else True


def _hour_utc() -> int:
    try:
        return max(0, min(23, int(os.getenv("CONWO_JIRA_CRON_HOUR_UTC", "2"))))
    except (TypeError, ValueError):
        return 2


def _seconds_until(hour: int) -> float:
    """Seconds from now until the next occurrence of `hour`:00 UTC."""
    now = datetime.now(timezone.utc)
    target = now.replace(hour=hour, minute=0, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    return (target - now).total_seconds()


def _already_ran_today() -> bool:
    """True if a successful sync already started today (UTC). Fail-open: on any
    error, return False (allow the run) — a missed sync is worse than a rare
    double. ::text cast works whether started_at is timestamptz or text."""
    try:
        from backend import db
        today = datetime.now(timezone.utc).date().isoformat()
        with db.connection() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT MAX(started_at)::text FROM sync_runs WHERE status = 'success'"
            )
            row = cur.fetchone()
        last = (row[0] or "")[:10] if row else ""
        return last >= today
    except Exception as exc:
        _log.warning("jira_scheduler: sync_runs check failed (%s); allowing run", exc)
        return False


def _run_sync() -> None:
    """Run the two-stage daily sync as a subprocess (blocking — call via a thread)."""
    _log.info("jira_scheduler: starting nightly jira_daily_sync.py")
    try:
        proc = subprocess.run(
            [sys.executable, str(_SCRIPTS / "jira_daily_sync.py")],
            cwd=str(_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=3600,
        )
        tail = (proc.stdout or "").strip().splitlines()[-1:] or [""]
        _log.info("jira_scheduler: sync finished rc=%s — %s", proc.returncode, tail[0])
    except Exception as exc:
        _log.error("jira_scheduler: sync failed: %s", exc)


async def run_forever() -> None:
    """Daily loop. Started from the FastAPI lifespan; returns immediately (cheap)
    when disabled or not the leader pod."""
    if not enabled():
        return
    if not _is_leader():
        _log.info("jira_scheduler: not leader pod (%s) — scheduler idle",
                  socket.gethostname())
        return
    hour = _hour_utc()
    _log.info("jira_scheduler: enabled; nightly Jira sync at %02d:00 UTC", hour)
    while True:
        try:
            await asyncio.sleep(_seconds_until(hour))
            if _already_ran_today():
                _log.info("jira_scheduler: already synced today; skipping")
            else:
                await asyncio.to_thread(_run_sync)
            # Sleep past the trigger minute so we don't re-fire within the hour.
            await asyncio.sleep(90)
        except asyncio.CancelledError:
            _log.info("jira_scheduler: cancelled (shutdown)")
            raise
        except Exception as exc:
            # Never let a bad night kill the loop; wait a bit and carry on.
            _log.error("jira_scheduler: loop error (%s); retrying in 5 min", exc)
            await asyncio.sleep(300)
