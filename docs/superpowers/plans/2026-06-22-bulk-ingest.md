# Bulk-Dump Ingestion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a backend-driven, durable bulk-dump ingestion: upload N files, hit Run, the backend runs them through the existing plan→execute pipeline serially and automatically (no per-file approval), persisting per-file state so the user can close the browser; the frontend polls one status endpoint and shows per-file progress + an overall bar.

**Architecture:** A new `ingest_batch` store (Postgres tables `ingest_batches` + `ingest_batch_items`) and a serial async runner that **reuses the existing `_run_plan_job` and `_run_ingest_job`** internals (auto-approving between them). Two endpoints (`POST /api/ingest/bulk`, `GET /api/ingest/bulk/{id}`), a startup reconciler, and a frontend bulk mode alongside the unchanged single-file review flow.

**Tech Stack:** FastAPI + psycopg/Postgres (mirrors `backend/auth_store.py` / `agent_access.py` DB patterns), asyncio background task, Angular 21 signals.

## Global Constraints
- Backend runs with `--reload`; **stop the backend before editing any `backend/*.py`** (verify `ps aux | grep -E "uvicorn.*--reload" | grep -v grep`). Migrations apply at startup.
- venv at `venv/`; `venv/bin/pytest`, `venv/bin/python`. Branch `feat/bulk-ingest`; commit there, don't push.
- Bulk is **serial** — respects the existing global ingest mutex (`ingest_service.acquire_lock`/`release_lock`/`is_locked`). No parallel LLM ingests.
- Bulk is **auto-run** (no per-file approval). Per-file failure → mark failed, continue the batch.
- Per-file states: `queued | planning | writing | done | failed`. Batch states: `running | done | failed | interrupted`.
- Endpoints reuse existing gating: `_require_developer_or_admin` + `_require_agent_access`; agent resolved from `X-Agent-Id` via `_get_agent`.
- DB access mirrors `auth_store`: `with db.connection() as conn: conn.execute(...).fetchone()`.
- Reuse, don't reimplement: `_run_plan_job(job, file_path, filename, notes, target_slug)` and `_run_ingest_job(session, job)` in `backend/ingest_api.py`; `ingest_service.create_plan_job/get_session/create_job/new_session_id/acquire_lock/release_lock/is_locked`. Avoid circular imports via lazy imports.

---

## Task 1: Migration + `ingest_batch` store

**Files:**
- Create: `migrations/postgres/120_ingest_batches.sql`
- Create: `backend/ingest_batch.py`
- Modify: `tests/conftest.py` (add the two tables to the truncation list so `clean_db` resets them — find the existing app-tables list, e.g. `_APP_TABLES`, and add `ingest_batches`, `ingest_batch_items`)
- Test: `tests/test_ingest_batch_store.py`

**Interfaces — Produces:**
- `create_batch(agent_id: str, created_by: str | None, items: list[dict]) -> dict` — `items` are `[{"upload_id","filename","file_path"}]`; inserts a batch + queued item rows; returns `{"batch_id": str, "total": int}`. Empty list → `ValueError`.
- `set_item_status(item_id: str, status: str, *, error: str | None = None, page_paths: list[str] | None = None) -> None`
- `set_batch_status(batch_id: str, status: str) -> None`
- `bump_counts(batch_id: str, *, completed: int = 0, failed: int = 0) -> None`
- `get_batch(batch_id: str) -> dict | None` — `{"batch": {...}, "items": [...]}` (items ordered by `ord`).
- `list_queued_items(batch_id: str) -> list[dict]` — item rows (id, ord, upload_id, filename, file_path) with status `queued`, ordered.
- `reconcile_interrupted() -> int` — flips `running` batches → `interrupted` and their `planning`/`writing` items → `interrupted` (well: items use `interrupted` too); returns count. Fail-open.

Note: `file_path` is needed by the runner but is transient (the upload's path); store it on the item row as a column `file_path TEXT` so the runner doesn't need to re-resolve it.

- [ ] **Step 1: Write the migration**

Create `migrations/postgres/120_ingest_batches.sql`:
```sql
-- Bulk-dump ingestion batches. A batch runs N uploaded files through the existing
-- plan->execute pipeline serially + automatically. Durable across restarts.
-- Idempotent; applied at startup by db.init_db().
CREATE TABLE IF NOT EXISTS ingest_batches (
    id          TEXT PRIMARY KEY,
    agent_id    TEXT NOT NULL,
    created_by  TEXT,
    created_at  TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'running',  -- running | done | failed | interrupted
    total       INTEGER NOT NULL DEFAULT 0,
    completed   INTEGER NOT NULL DEFAULT 0,
    failed      INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS ingest_batch_items (
    id          TEXT PRIMARY KEY,
    batch_id    TEXT NOT NULL,
    ord         INTEGER NOT NULL,
    upload_id   TEXT NOT NULL,
    filename    TEXT NOT NULL,
    file_path   TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'queued',  -- queued | planning | writing | done | failed | interrupted
    error       TEXT,
    page_paths  TEXT,                            -- JSON array of pages written
    updated_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_ingest_batch_items_batch ON ingest_batch_items (batch_id, ord);
```

- [ ] **Step 2: Write the failing tests**

Create `tests/test_ingest_batch_store.py`:
```python
"""ingest_batch store: batch+item lifecycle, counts, get shape, reconcile."""
import json
import pytest
from backend import ingest_batch


@pytest.fixture(autouse=True)
def clean(clean_db):
    yield


def _items(n):
    return [{"upload_id": f"u{i}", "filename": f"f{i}.pdf", "file_path": f"/tmp/u{i}/f{i}.pdf"}
            for i in range(n)]


def test_create_batch_queues_items():
    r = ingest_batch.create_batch("conwo", "admin@x.com", _items(3))
    assert r["total"] == 3
    got = ingest_batch.get_batch(r["batch_id"])
    assert got["batch"]["status"] == "running"
    assert len(got["items"]) == 3
    assert [i["status"] for i in got["items"]] == ["queued", "queued", "queued"]
    assert [i["ord"] for i in got["items"]] == [0, 1, 2]


def test_create_batch_rejects_empty():
    with pytest.raises(ValueError):
        ingest_batch.create_batch("conwo", "admin@x.com", [])


def test_status_and_counts_and_pages():
    r = ingest_batch.create_batch("conwo", "a@x.com", _items(2))
    items = ingest_batch.get_batch(r["batch_id"])["items"]
    ingest_batch.set_item_status(items[0]["id"], "done", page_paths=["wiki/modules/x.md"])
    ingest_batch.bump_counts(r["batch_id"], completed=1)
    ingest_batch.set_item_status(items[1]["id"], "failed", error="boom")
    ingest_batch.bump_counts(r["batch_id"], failed=1)
    ingest_batch.set_batch_status(r["batch_id"], "done")
    got = ingest_batch.get_batch(r["batch_id"])
    assert got["batch"]["completed"] == 1 and got["batch"]["failed"] == 1
    assert got["batch"]["status"] == "done"
    by_ord = {i["ord"]: i for i in got["items"]}
    assert by_ord[0]["status"] == "done" and json.loads(by_ord[0]["page_paths"]) == ["wiki/modules/x.md"]
    assert by_ord[1]["status"] == "failed" and by_ord[1]["error"] == "boom"


def test_list_queued_items_orders_and_filters():
    r = ingest_batch.create_batch("conwo", "a@x.com", _items(2))
    items = ingest_batch.get_batch(r["batch_id"])["items"]
    ingest_batch.set_item_status(items[0]["id"], "done")
    q = ingest_batch.list_queued_items(r["batch_id"])
    assert [i["ord"] for i in q] == [1]


def test_reconcile_interrupted_flips_running_and_inflight():
    r = ingest_batch.create_batch("conwo", "a@x.com", _items(2))
    items = ingest_batch.get_batch(r["batch_id"])["items"]
    ingest_batch.set_item_status(items[0]["id"], "writing")
    n = ingest_batch.reconcile_interrupted()
    assert n >= 1
    got = ingest_batch.get_batch(r["batch_id"])
    assert got["batch"]["status"] == "interrupted"
    assert {i["status"] for i in got["items"]} <= {"interrupted", "queued"}
    # the in-flight 'writing' item became 'interrupted'
    assert any(i["status"] == "interrupted" for i in got["items"])
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `venv/bin/pytest tests/test_ingest_batch_store.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'backend.ingest_batch'`

- [ ] **Step 4: Create `backend/ingest_batch.py`**

```python
"""Durable bulk-ingest batch store.

A batch runs N uploaded files through the existing plan->execute pipeline serially
and automatically. State is persisted in Postgres so the run survives the browser
(and the API process). The serial runner lives in run_batch() (added in a later
task); this module is the data layer + reconciler. All reads/writes mirror
backend/auth_store.py. Fail-open where a failure must not crash the request path.
"""
from __future__ import annotations

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


def reconcile_interrupted() -> int:
    """At startup, mark still-running batches and their in-flight items interrupted.
    Fail-open: never raise."""
    try:
        with db.connection() as conn:
            conn.execute(
                "UPDATE ingest_batch_items SET status='interrupted', updated_at=%s "
                "WHERE status IN ('planning','writing')",
                (_now(),),
            )
            cur = conn.execute(
                "UPDATE ingest_batches SET status='interrupted' WHERE status='running'"
            )
            return cur.rowcount or 0
    except Exception as exc:
        _log.warning("ingest_batch.reconcile_interrupted failed (ignored): %s", exc)
        return 0
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `venv/bin/pytest tests/test_ingest_batch_store.py -v`
Expected: PASS (5). If `clean_db` doesn't reset the new tables, add `ingest_batches` and `ingest_batch_items` to the truncation list in `tests/conftest.py` (search for where the other app tables are truncated).

- [ ] **Step 6: Commit**
```bash
git add migrations/postgres/120_ingest_batches.sql backend/ingest_batch.py tests/conftest.py tests/test_ingest_batch_store.py
git commit -m "feat(ingest): durable bulk-batch store + tables"
```

---

## Task 2: Serial auto-run runner

**Files:**
- Modify: `backend/ingest_batch.py` (add `run_batch` + a lock-wait helper)
- Test: `tests/test_ingest_batch_runner.py`

**Interfaces:**
- Consumes: Task 1 store fns; `ingest_service.{acquire_lock, release_lock, create_plan_job, get_session, create_job, new_session_id}`; `backend.ingest_api.{_run_plan_job, _run_ingest_job}` (lazy import to avoid a cycle).
- Produces: `async def run_batch(batch_id: str) -> None` — processes each queued item serially: `planning` → reuse `_run_plan_job` → on plan failure mark item `failed`+`bump failed`; else `writing` → reuse `_run_ingest_job` → mark `done`(+page_paths)/`failed`; updates batch counts; sets batch `done` at end. Per-item try/except so one failure never stops the batch.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_ingest_batch_runner.py`:
```python
"""run_batch: serial processing, done/failed per item, failure isolation, counts."""
import asyncio
import pytest
from backend import ingest_batch, ingest_service


@pytest.fixture(autouse=True)
def clean(clean_db):
    yield


def _items(n):
    return [{"upload_id": f"u{i}", "filename": f"f{i}.pdf", "file_path": f"/tmp/f{i}.pdf"}
            for i in range(n)]


def _stub_plan(monkeypatch, *, fail_on=()):
    """Stub _run_plan_job: set job.status done + a session, or error for fail_on filenames."""
    from backend import ingest_api

    async def fake_plan(job, file_path, filename, notes, target_slug):
        if filename in fail_on:
            job.status = "error"; job.error_msg = f"plan failed: {filename}"
            return
        sid = ingest_service.new_session_id()
        ingest_service.store_session(ingest_service.IngestSession(
            session_id=sid, upload_id=job.upload_id, plan={"operations": []},
            created_at=0, slug="x", filename=filename, original_path=file_path,
            agent_id=job.agent_id))
        job.session_id = sid; job.status = "done"
    monkeypatch.setattr(ingest_api, "_run_plan_job", fake_plan)


def _stub_execute(monkeypatch, *, fail_on=()):
    from backend import ingest_api

    async def fake_exec(session, job):
        if session.filename in fail_on:
            job.status = "error"; job.error_msg = f"exec failed: {session.filename}"
            return
        job.status = "complete"; job.files_created = [f"wiki/modules/{session.filename}.md"]
    monkeypatch.setattr(ingest_api, "_run_ingest_job", fake_exec)


def test_run_batch_all_succeed(monkeypatch):
    _stub_plan(monkeypatch); _stub_execute(monkeypatch)
    r = ingest_batch.create_batch("conwo", "a@x.com", _items(3))
    asyncio.run(ingest_batch.run_batch(r["batch_id"]))
    got = ingest_batch.get_batch(r["batch_id"])
    assert got["batch"]["status"] == "done"
    assert got["batch"]["completed"] == 3 and got["batch"]["failed"] == 0
    assert all(i["status"] == "done" for i in got["items"])


def test_run_batch_isolates_a_plan_failure(monkeypatch):
    _stub_plan(monkeypatch, fail_on=("f1.pdf",)); _stub_execute(monkeypatch)
    r = ingest_batch.create_batch("conwo", "a@x.com", _items(3))
    asyncio.run(ingest_batch.run_batch(r["batch_id"]))
    got = ingest_batch.get_batch(r["batch_id"])
    assert got["batch"]["completed"] == 2 and got["batch"]["failed"] == 1
    by_ord = {i["ord"]: i for i in got["items"]}
    assert by_ord[1]["status"] == "failed" and "plan failed" in by_ord[1]["error"]
    assert by_ord[0]["status"] == "done" and by_ord[2]["status"] == "done"


def test_run_batch_isolates_an_execute_failure(monkeypatch):
    _stub_plan(monkeypatch); _stub_execute(monkeypatch, fail_on=("f0.pdf",))
    r = ingest_batch.create_batch("conwo", "a@x.com", _items(2))
    asyncio.run(ingest_batch.run_batch(r["batch_id"]))
    got = ingest_batch.get_batch(r["batch_id"])
    assert got["batch"]["failed"] == 1 and got["batch"]["completed"] == 1
    assert ingest_service.is_locked() is False  # lock always released
```

- [ ] **Step 2: Run to verify fail**

Run: `venv/bin/pytest tests/test_ingest_batch_runner.py -v`
Expected: FAIL — `AttributeError: module 'backend.ingest_batch' has no attribute 'run_batch'`

- [ ] **Step 3: Add `run_batch` to `backend/ingest_batch.py`**

Append:
```python
import asyncio


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
```

- [ ] **Step 4: Run to verify pass**

Run: `venv/bin/pytest tests/test_ingest_batch_runner.py -v`
Expected: PASS (3).

- [ ] **Step 5: Commit**
```bash
git add backend/ingest_batch.py tests/test_ingest_batch_runner.py
git commit -m "feat(ingest): serial auto-run bulk runner (reuses plan+execute)"
```

---

## Task 3: Bulk endpoints + startup reconcile

**Files:**
- Modify: `backend/ingest_api.py` (add 2 endpoints; reuse `_get_agent`, `_uploads_root`, gating deps)
- Modify: `backend/api.py` (call `ingest_batch.reconcile_interrupted()` in lifespan startup)
- Test: `tests/test_ingest_bulk_api.py`

**Interfaces — Consumes:** `ingest_batch.{create_batch, run_batch, get_batch}`; `_get_agent`, `_uploads_root`; the ingest router's existing gating (`_require_developer_or_admin`, `_require_agent_access`).

- [ ] **Step 1: Write the failing tests**

Create `tests/test_ingest_bulk_api.py`:
```python
"""POST /api/ingest/bulk + GET /api/ingest/bulk/{id}: create, resolve uploads, gate."""
import pathlib
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient


@pytest.fixture
def client(clean_db, tmp_path, monkeypatch):
    import backend.ingest_api as ia
    monkeypatch.setattr(ia, "UPLOAD_DIR", str(tmp_path), raising=False)
    from backend import api, auth_store
    auth_store.create_user("dev@moveinsync.com", role="developer", approved=True)
    tok = auth_store.create_token("dev@moveinsync.com")
    return TestClient(api.app, raise_server_exceptions=False), {"Authorization": f"Bearer {tok}"}, tmp_path


def _make_upload(root: pathlib.Path, upload_id: str, filename: str) -> None:
    d = root / upload_id
    d.mkdir(parents=True, exist_ok=True)
    (d / filename).write_text("dummy")


def test_bulk_creates_batch_and_starts_runner(client):
    c, h, root = client
    _make_upload(root, "u0", "a.pdf"); _make_upload(root, "u1", "b.pdf")
    # Don't actually run the pipeline — patch run_batch to a no-op coroutine.
    async def _noop(_bid): return None
    with patch("backend.ingest_batch.run_batch", _noop):
        r = c.post("/api/ingest/bulk", json={"upload_ids": ["u0", "u1"]}, headers=h)
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 2 and body["batch_id"]
    got = c.get(f"/api/ingest/bulk/{body['batch_id']}", headers=h).json()
    assert len(got["items"]) == 2
    assert {i["filename"] for i in got["items"]} == {"a.pdf", "b.pdf"}


def test_bulk_rejects_empty(client):
    c, h, _ = client
    r = c.post("/api/ingest/bulk", json={"upload_ids": []}, headers=h)
    assert r.status_code == 400


def test_bulk_rejects_unknown_upload(client):
    c, h, _ = client
    async def _noop(_bid): return None
    with patch("backend.ingest_batch.run_batch", _noop):
        r = c.post("/api/ingest/bulk", json={"upload_ids": ["does-not-exist"]}, headers=h)
    assert r.status_code == 400


def test_bulk_status_404_unknown(client):
    c, h, _ = client
    assert c.get("/api/ingest/bulk/nope", headers=h).status_code == 404


def test_bulk_requires_auth(client):
    c, _, root = client
    _make_upload(root, "u0", "a.pdf")
    r = c.post("/api/ingest/bulk", json={"upload_ids": ["u0"]})  # no token
    assert r.status_code in (401, 403)
```

- [ ] **Step 2: Run to verify fail**

Run: `venv/bin/pytest tests/test_ingest_bulk_api.py -v`
Expected: FAIL (endpoints 404 / not found).

- [ ] **Step 3: Add the endpoints in `backend/ingest_api.py`**

Add a request model near the other Pydantic models and the endpoints near the other ingest routes:
```python
class BulkIngestRequest(BaseModel):
    upload_ids: list[str]


@router.post("/bulk")
async def start_bulk_ingest(req: BulkIngestRequest, request: Request):
    """Create a bulk batch from already-uploaded files and start the serial runner.
    Each upload_id must exist under the active agent's uploads root."""
    from backend import ingest_batch
    agent = _get_agent(request)
    if not req.upload_ids:
        raise HTTPException(status_code=400, detail="upload_ids must not be empty")
    root = _uploads_root(agent)
    items: list[dict] = []
    for uid in req.upload_ids:
        updir = root / uid
        files = [p for p in updir.iterdir() if p.is_file()] if updir.is_dir() else []
        if not files:
            raise HTTPException(status_code=400, detail=f"unknown or empty upload: {uid}")
        f = files[0]
        items.append({"upload_id": uid, "filename": f.name, "file_path": str(f)})
    created_by = getattr(request.state, "user_email", None)
    result = ingest_batch.create_batch(agent.id, created_by, items)
    import asyncio
    asyncio.create_task(ingest_batch.run_batch(result["batch_id"]))
    return result


@router.get("/bulk/{batch_id}")
def get_bulk_status(batch_id: str):
    from backend import ingest_batch
    got = ingest_batch.get_batch(batch_id)
    if got is None:
        raise HTTPException(status_code=404, detail="batch not found")
    return got
```
Notes:
- The ingest `router` is already included in `api.py` with `Depends(_require_developer_or_admin)` and `Depends(_require_agent_access)`, so these inherit auth + agent-access gating — do not re-add per-route.
- `created_by`: if `request.state.user_email` isn't set elsewhere, pass `None` (the column is nullable). Do not block on it.

- [ ] **Step 4: Call the reconciler at startup in `backend/api.py`**

In the lifespan startup (after the existing `trace_store.reconcile_orphans()` call), add:
```python
    from backend import ingest_batch
    ingest_batch.reconcile_interrupted()
```

- [ ] **Step 5: Run to verify pass**

Run: `venv/bin/pytest tests/test_ingest_bulk_api.py -v`
Expected: PASS (5).

- [ ] **Step 6: Commit**
```bash
git add backend/ingest_api.py backend/api.py tests/test_ingest_bulk_api.py
git commit -m "feat(ingest): POST/GET /api/ingest/bulk endpoints + startup reconcile"
```

---

## Task 4: Frontend bulk mode

**Files:**
- Modify: `frontend/src/app/core/api.service.ts` (2 methods + a BulkBatch type)
- Modify: `frontend/src/app/features/ingest/ingest.ts` (add a Bulk-dump mode beside the single-file flow)

**Interfaces — Consumes:** `POST /api/ingest/upload` (existing, returns `{upload_id, filename, ...}`); `POST /api/ingest/bulk {upload_ids[]}` → `{batch_id, total}`; `GET /api/ingest/bulk/{id}` → `{batch:{status,total,completed,failed}, items:[{filename,status,error}]}`.

- [ ] **Step 1: api.service.ts — types + methods**

Add:
```typescript
export interface BulkBatchItem { filename: string; status: string; error?: string | null; }
export interface BulkBatch {
  batch: { id: string; status: string; total: number; completed: number; failed: number };
  items: BulkBatchItem[];
}
```
Methods (use the session Bearer header, same as other authed calls — reuse the existing header helper, e.g. `adminHeaders()`):
```typescript
  startBulkIngest(uploadIds: string[]): Observable<{ batch_id: string; total: number }> {
    return this.http.post<{ batch_id: string; total: number }>(
      `${API_BASE}/api/ingest/bulk`, { upload_ids: uploadIds }, { headers: this.adminHeaders() });
  }
  getBulkStatus(batchId: string): Observable<BulkBatch> {
    return this.http.get<BulkBatch>(
      `${API_BASE}/api/ingest/bulk/${encodeURIComponent(batchId)}`, { headers: this.adminHeaders() });
  }
```
(Confirm the existing single-file upload method's name in this file — reuse it for the per-file upload loop rather than re-implementing the multipart POST.)

- [ ] **Step 2: ingest.ts — bulk mode**

Add a mode toggle (e.g. a segmented control: "Single (review)" | "Bulk dump") that switches the existing single-file UI and a new bulk panel. Bulk panel logic (signals):
```typescript
  bulkMode = signal(false);
  bulkFiles = signal<File[]>([]);
  bulkUploading = signal(false);
  bulkBatchId = signal<string | null>(localStorage.getItem('conwo_bulk_batch') || null);
  bulkStatus = signal<BulkBatch | null>(null);
  private bulkPoll: ReturnType<typeof setInterval> | null = null;

  onBulkFiles(ev: Event) {
    const input = ev.target as HTMLInputElement;
    this.bulkFiles.set(input.files ? Array.from(input.files) : []);
  }

  async runBulk() {
    const files = this.bulkFiles();
    if (!files.length) return;
    this.bulkUploading.set(true);
    const uploadIds: string[] = [];
    for (const f of files) {
      const res = await this.api.uploadFile(f).toPromise();   // reuse existing upload method
      if (res?.upload_id) uploadIds.push(res.upload_id);
    }
    this.bulkUploading.set(false);
    if (!uploadIds.length) return;
    this.api.startBulkIngest(uploadIds).subscribe({
      next: r => {
        this.bulkBatchId.set(r.batch_id);
        localStorage.setItem('conwo_bulk_batch', r.batch_id);
        this.startBulkPolling();
      },
    });
  }

  private startBulkPolling() {
    this.stopBulkPolling();
    const id = this.bulkBatchId();
    if (!id) return;
    const tick = () => this.api.getBulkStatus(id).subscribe({
      next: s => {
        this.bulkStatus.set(s);
        if (['done', 'failed', 'interrupted'].includes(s.batch.status)) this.stopBulkPolling();
      },
      error: () => { /* keep polling */ },
    });
    tick();
    this.bulkPoll = setInterval(tick, 2000);
  }
  private stopBulkPolling() { if (this.bulkPoll) { clearInterval(this.bulkPoll); this.bulkPoll = null; } }

  bulkProgress(): number {
    const b = this.bulkStatus()?.batch;
    return b && b.total ? Math.round(((b.completed + b.failed) / b.total) * 100) : 0;
  }
```
Resume on init: in the component's `ngOnInit` (or constructor), if `bulkBatchId()` is set, call `startBulkPolling()`. Add `OnDestroy` → `stopBulkPolling()`.

Template (bulk panel): a multi `<input type="file" multiple (change)="onBulkFiles($event)">` (accept `.pdf,.docx,.xlsx,.md,.txt,.rtf`), a **Run** button (`[disabled]="bulkUploading() || !bulkFiles().length"`), an overall progress bar bound to `bulkProgress()`, a summary line (`{{ bulkStatus()?.batch?.completed }} done / {{ bulkStatus()?.batch?.failed }} failed of {{ bulkStatus()?.batch?.total }}`), and a per-file list:
```html
@for (it of bulkStatus()?.items || []; track it.filename) {
  <div class="bulk-row">
    <span class="fname">{{ it.filename }}</span>
    <span class="chip" [class]="'st-' + it.status">{{ it.status }}</span>
    @if (it.status === 'failed' && it.error) { <span class="err">{{ it.error }}</span> }
  </div>
}
```

- [ ] **Step 3: Build**

Run: `cd frontend && npx ng build 2>&1 | tail -4`
Expected: succeeds, no TS errors (pre-existing budget warnings OK).

- [ ] **Step 4: Commit**
```bash
git add frontend/src/app/core/api.service.ts frontend/src/app/features/ingest/ingest.ts
git commit -m "feat(ingest-ui): bulk-dump mode — multi-upload, run, per-file progress + bar"
```

---

## Task 5: Full verification

- [ ] **Step 1: Backend suites**

Run: `venv/bin/pytest tests/test_ingest_batch_store.py tests/test_ingest_batch_runner.py tests/test_ingest_bulk_api.py -v`
Expected: all PASS.

- [ ] **Step 2: No regressions**

Run: `venv/bin/pytest -q 2>&1 | tail -6`
Expected: only the known pre-existing/environmental failures (Google-auth 500-vs-403, 2 PMS network-timeouts, ingest-lock 409, lifespan `.env` reload). No NEW failures (in particular existing `tests/test_ingest_api.py` single-file tests still pass).

- [ ] **Step 3: Frontend build**

Run: `cd frontend && npx ng build 2>&1 | tail -4`
Expected: succeeds (budget warnings only).

- [ ] **Step 4: Manual smoke (after restarting backend, ANTHROPIC_API_KEY set)**

1. Ingest tab → Bulk dump → select 2–3 small files → Run.
2. Watch per-file rows: queued → planning → writing → done (or failed with reason); overall bar advances.
3. Reload the page mid-run → progress resumes (persisted batch_id).
4. Confirm pages were created in the active agent's wiki and the single-file review flow still works unchanged.

---

## Self-review notes
- **Spec coverage:** tables+store → Task 1; serial auto-run runner reusing plan/execute → Task 2; endpoints + reconcile → Task 3; frontend bulk mode (multi-upload, run, per-file states + bar, resume) → Task 4; verification → Task 5. Single-file flow left untouched (only additive endpoints/UI).
- **Type consistency:** store fns + shapes (`create_batch`→`{batch_id,total}`, `get_batch`→`{batch,items}`) are consumed identically in Tasks 2/3; TS `BulkBatch` mirrors `get_batch`; endpoint routes match the TS calls.
- **Reuse:** runner calls the real `_run_plan_job`/`_run_ingest_job` (lazy import for the cycle); lock acquired before each phase (they release in their finally). Serial via the existing mutex.
- **Reload safety:** Tasks 1-3 edit `backend/*.py` → backend stopped (Global Constraints). Task 4 frontend-only.
