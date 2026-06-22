"""Durable bulk-ingest batch store.

A batch runs N uploaded files through the existing plan->execute pipeline serially
and automatically. State is persisted in Postgres so the run survives the browser
(and the API process). The serial runner lives in run_batch() (added in a later
task); this module is the data layer + reconciler. All reads/writes mirror
backend/auth_store.py. Fail-open where a failure must not crash the request path.
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from uuid import uuid4

from backend import db

_log = logging.getLogger("ingest_batch")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def create_batch(agent_id: str, created_by: str | None, items: list[dict]) -> dict:
    """Insert a batch + queued item rows. items: [{upload_id, filename, file_path}]."""
    if not items:
        raise ValueError("create_batch requires at least one item")
    batch_id = uuid4().hex
    now = _now()
    with db.connection() as conn:
        conn.execute(
            "INSERT INTO ingest_batches (id, agent_id, created_by, created_at, status, total) "
            "VALUES (%s, %s, %s, %s, 'running', %s)",
            (batch_id, agent_id, created_by, now, len(items)),
        )
        for ord_, it in enumerate(items):
            conn.execute(
                "INSERT INTO ingest_batch_items "
                "(id, batch_id, ord, upload_id, filename, file_path, status, updated_at) "
                "VALUES (%s, %s, %s, %s, %s, %s, 'queued', %s)",
                (uuid4().hex, batch_id, ord_, it["upload_id"], it["filename"],
                 it["file_path"], now),
            )
    return {"batch_id": batch_id, "total": len(items)}


def set_item_status(item_id: str, status: str, *, error: str | None = None,
                    page_paths: list[str] | None = None) -> None:
    with db.connection() as conn:
        conn.execute(
            "UPDATE ingest_batch_items SET status=%s, error=%s, page_paths=%s, updated_at=%s "
            "WHERE id=%s",
            (status, error, json.dumps(page_paths) if page_paths is not None else None,
             _now(), item_id),
        )


def set_batch_status(batch_id: str, status: str) -> None:
    with db.connection() as conn:
        conn.execute("UPDATE ingest_batches SET status=%s WHERE id=%s", (status, batch_id))


def bump_counts(batch_id: str, *, completed: int = 0, failed: int = 0) -> None:
    with db.connection() as conn:
        conn.execute(
            "UPDATE ingest_batches SET completed=completed+%s, failed=failed+%s WHERE id=%s",
            (completed, failed, batch_id),
        )


def get_batch(batch_id: str) -> dict | None:
    with db.connection() as conn:
        b = conn.execute("SELECT * FROM ingest_batches WHERE id=%s", (batch_id,)).fetchone()
        if not b:
            return None
        items = conn.execute(
            "SELECT id, batch_id, ord, upload_id, filename, status, error, page_paths, updated_at "
            "FROM ingest_batch_items WHERE batch_id=%s ORDER BY ord ASC",
            (batch_id,),
        ).fetchall()
    return {"batch": dict(b), "items": [dict(i) for i in items]}


def list_queued_items(batch_id: str) -> list[dict]:
    with db.connection() as conn:
        rows = conn.execute(
            "SELECT id, ord, upload_id, filename, file_path FROM ingest_batch_items "
            "WHERE batch_id=%s AND status='queued' ORDER BY ord ASC",
            (batch_id,),
        ).fetchall()
    return [dict(r) for r in rows]


async def _acquire_lock_blocking(poll: float = 0.5) -> None:
    """Wait until the global ingest lock is free, then take it. Bulk is serial and
    must not run concurrently with a single-file ingest."""
    from backend import ingest_service
    while not ingest_service.acquire_lock():
        await asyncio.sleep(poll)


async def run_batch(batch_id: str) -> None:
    """Serially run every queued item through plan -> auto-execute. Reuses the
    existing single-file job coroutines. Per-item try/except: one failure never
    stops the batch. Lazy imports avoid an ingest_api <-> ingest_batch cycle."""
    from backend import ingest_service
    from backend.ingest_api import _run_plan_job, _run_ingest_job

    for item in list_queued_items(batch_id):
        item_id = item["id"]
        try:
            # ── Phase 1: plan (reuses the single-file planner) ──────────────
            set_item_status(item_id, "planning")
            await _acquire_lock_blocking()                # _run_plan_job releases it
            plan_job = ingest_service.create_plan_job(
                uuid4().hex, item["upload_id"], agent_id=_batch_agent(batch_id))
            await _run_plan_job(plan_job, item["file_path"], item["filename"], "", "")
            if plan_job.status != "done" or not plan_job.session_id:
                set_item_status(item_id, "failed",
                                error=(plan_job.error_msg or "planning failed"))
                bump_counts(batch_id, failed=1)
                continue
            session = ingest_service.get_session(plan_job.session_id)
            if session is None:
                set_item_status(item_id, "failed", error="plan session expired")
                bump_counts(batch_id, failed=1)
                continue

            # ── Phase 2: execute (auto-approved) ────────────────────────────
            set_item_status(item_id, "writing")
            await _acquire_lock_blocking()                # _run_ingest_job releases it
            job = ingest_service.create_job(uuid4().hex, agent_id=session.agent_id)
            await _run_ingest_job(session, job)
            if job.status == "complete":
                set_item_status(item_id, "done",
                                page_paths=list(getattr(job, "files_created", []) or []))
                bump_counts(batch_id, completed=1)
            else:
                set_item_status(item_id, "failed",
                                error=(job.error_msg or "execution failed"))
                bump_counts(batch_id, failed=1)
        except Exception as exc:                          # never let one item kill the batch
            _log.exception("run_batch item %s failed", item_id)
            try:
                set_item_status(item_id, "failed", error=str(exc))
                bump_counts(batch_id, failed=1)
            except Exception:
                pass
            # ensure the lock isn't held across to the next item
            try:
                ingest_service.release_lock()
            except Exception:
                pass

    set_batch_status(batch_id, "done")


def _batch_agent(batch_id: str) -> str:
    with db.connection() as conn:
        row = conn.execute("SELECT agent_id FROM ingest_batches WHERE id=%s", (batch_id,)).fetchone()
    return row["agent_id"] if row else "conwo"


def reconcile_interrupted() -> int:
    """At startup, mark still-running batches and their in-flight items interrupted.
    Only items belonging to currently-running batches are touched.
    Returns the number of batches flipped to interrupted. Fail-open: never raise."""
    try:
        with db.connection() as conn:
            conn.execute(
                "UPDATE ingest_batch_items SET status='interrupted', updated_at=%s "
                "WHERE status IN ('planning','writing') "
                "AND batch_id IN (SELECT id FROM ingest_batches WHERE status='running')",
                (_now(),),
            )
            cur = conn.execute(
                "UPDATE ingest_batches SET status='interrupted' WHERE status='running'"
            )
            return cur.rowcount or 0
    except Exception as exc:
        _log.warning("ingest_batch.reconcile_interrupted failed (ignored): %s", exc)
        return 0
