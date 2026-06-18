# Full-Pipeline "Sync now" Button — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the admin "Sync now" button run the full Jira pipeline (Stage 1 fetch + Stage 2 AI classification) in the background, block overlapping runs, and show live progress/result.

**Architecture:** A new in-process job tracker (`backend/sync_job.py`) runs the existing delta pipeline (`backend.tools.trigger_sync._trigger_jira_sync_handler({"mode":"delta"})` → `scripts/jira_daily_sync.py`) on a background thread, guarded by a module lock so only one runs at a time. `POST /admin/trigger-sync` starts it; `GET /admin/sync-status` exposes the live job state; the admin UI polls and renders progress → done/error.

**Tech Stack:** Python/FastAPI, `threading` (stdlib), Angular 21 signals, existing `subprocess`-based pipeline.

## Global Constraints
- Backend runs with `--reload`; **stop the backend before editing any `backend/*.py`** (a `.py` write triggers a reload that rebuilds the in-memory wiki index). Verify stopped with `ps aux | grep -E "uvicorn.*--reload" | grep -v grep`.
- venv at `venv/`; run `venv/bin/pytest`, `venv/bin/python`.
- Branch is already `feat/full-sync-button` (off latest `main`). Commit there; do not push unless asked.
- Fail-open: nothing in the job tracker may raise into the request path or crash the server.
- Single-replica prod → in-process lock is sufficient (multi-replica is out of scope; note as a comment).

---

## Task 1: `backend/sync_job.py` — in-process job tracker

**Files:**
- Create: `backend/sync_job.py`
- Test: `tests/test_sync_job.py`

**Interfaces:**
- Consumes: `backend.tools.trigger_sync._trigger_jira_sync_handler(inp: dict) -> dict` (returns `{"success": bool, "mode", "exit_code", "elapsed_s", "sync_summary", "classify_summary", "done_line", ...}`; on bad input returns `{"error", "code"}` with no `success` key).
- Produces:
  - `start() -> dict` → `{"status": "started"}` | `{"status": "already_running"}` | `{"status": "error", "message": str}`
  - `status() -> dict` → `{"state": "idle"|"running"|"done"|"error", "started_at": str|None, "ended_at": str|None, "result": dict|None, "message": str}` (never exposes internal keys)

- [ ] **Step 1: Write the failing tests**

Create `tests/test_sync_job.py`:

```python
"""In-process sync-job tracker: state transitions, overlap blocking, fail-open."""
import threading
import time

import pytest

from backend import sync_job


@pytest.fixture(autouse=True)
def reset_state():
    # Reset the module-global state before each test.
    with sync_job._lock:
        sync_job._state.update({
            "_running": False, "state": "idle",
            "started_at": None, "ended_at": None, "result": None, "message": "",
        })
    yield


def _wait_until_idle_done(timeout=3.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if sync_job.status()["state"] in ("done", "error"):
            return
        time.sleep(0.02)
    raise AssertionError(f"job did not finish; state={sync_job.status()['state']}")


def test_initial_status_is_idle():
    s = sync_job.status()
    assert s["state"] == "idle"
    assert "_running" not in s          # internal flag is never exposed


def test_start_runs_and_records_success(monkeypatch):
    monkeypatch.setattr(
        "backend.tools.trigger_sync._trigger_jira_sync_handler",
        lambda inp: {"success": True, "mode": "delta", "sync_summary": "fetched=5",
                     "classify_summary": "5 tickets, $0.01", "done_line": "DONE total=12s"},
    )
    assert sync_job.start() == {"status": "started"}
    _wait_until_idle_done()
    s = sync_job.status()
    assert s["state"] == "done"
    assert s["result"]["classify_summary"] == "5 tickets, $0.01"
    assert s["ended_at"] is not None


def test_failed_pipeline_sets_error(monkeypatch):
    monkeypatch.setattr(
        "backend.tools.trigger_sync._trigger_jira_sync_handler",
        lambda inp: {"success": False, "mode": "delta", "error": "boom"},
    )
    sync_job.start()
    _wait_until_idle_done()
    s = sync_job.status()
    assert s["state"] == "error"
    assert s["message"] == "boom"


def test_overlap_is_blocked(monkeypatch):
    gate = threading.Event()
    monkeypatch.setattr(
        "backend.tools.trigger_sync._trigger_jira_sync_handler",
        lambda inp: (gate.wait(2.0), {"success": True})[1],   # block until released
    )
    assert sync_job.start() == {"status": "started"}
    # second click while running:
    assert sync_job.start() == {"status": "already_running"}
    gate.set()
    _wait_until_idle_done()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `venv/bin/pytest tests/test_sync_job.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'backend.sync_job'`

- [ ] **Step 3: Create `backend/sync_job.py`**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `venv/bin/pytest tests/test_sync_job.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/sync_job.py tests/test_sync_job.py
git commit -m "feat(sync): in-process job tracker for full-pipeline sync"
```

---

## Task 2: Wire the admin endpoints to the full pipeline

**Files:**
- Modify: `backend/admin_api.py` (`trigger_jira_sync` ~line 105-116; `get_sync_status` ~line 73 return)
- Test: `tests/test_sync_job_admin.py`

**Interfaces:**
- Consumes: `backend.sync_job.start()`, `backend.sync_job.status()` (from Task 1).
- Produces: `admin_api.trigger_jira_sync() -> dict` now returns `sync_job.start()`'s value; `admin_api.get_sync_status()` return dict gains a `"job"` key = `sync_job.status()`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_sync_job_admin.py`:

```python
"""Admin endpoints drive the full-pipeline job tracker."""
import time
import pytest
from backend import admin_api, sync_job


@pytest.fixture(autouse=True)
def reset_state():
    with sync_job._lock:
        sync_job._state.update({"_running": False, "state": "idle",
                                "started_at": None, "ended_at": None,
                                "result": None, "message": ""})
    yield


def test_trigger_starts_full_pipeline(monkeypatch):
    monkeypatch.setattr(
        "backend.tools.trigger_sync._trigger_jira_sync_handler",
        lambda inp: {"success": True, "mode": "delta", "done_line": "DONE"},
    )
    assert admin_api.trigger_jira_sync() == {"status": "started"}
    # wait for completion
    for _ in range(150):
        if sync_job.status()["state"] in ("done", "error"):
            break
        time.sleep(0.02)
    assert sync_job.status()["state"] == "done"


def test_sync_status_includes_job_block():
    status = admin_api.get_sync_status()
    assert "job" in status
    assert status["job"]["state"] in ("idle", "running", "done", "error")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `venv/bin/pytest tests/test_sync_job_admin.py -v`
Expected: FAIL — `trigger_jira_sync` still returns `{"status":"started","pid":...}` (not the job dict), and `get_sync_status()` has no `"job"` key.

- [ ] **Step 3: Update `backend/admin_api.py`**

Replace the `trigger_jira_sync` function (currently spawns `jira_sync.py --incremental`):

```python
def trigger_jira_sync() -> dict:
    """Run the FULL Jira pipeline (fetch + AI classification) in the background.

    Delegates to the in-process job tracker so the HTTP request returns instantly,
    overlapping runs are blocked, and the admin UI can poll get_sync_status() for
    progress. (Previously this ran Stage 1 only — jira_sync.py --incremental — which
    left freshly-fetched tickets unclassified.)"""
    from backend import sync_job
    return sync_job.start()
```

Then, in `get_sync_status()`, just before `return result` (~line 73), add the job block:

```python
    # Live state of the full-pipeline "Sync now" job (idle/running/done/error).
    try:
        from backend import sync_job
        result["job"] = sync_job.status()
    except Exception:
        result["job"] = {"state": "idle"}

    return result
```

(`subprocess`, `sys`, `_PYTHON`, `_SCRIPTS` may now be unused by this function but
are still used elsewhere in the file — leave them.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `venv/bin/pytest tests/test_sync_job_admin.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/admin_api.py tests/test_sync_job_admin.py
git commit -m "feat(admin): /admin/trigger-sync runs full pipeline; sync-status exposes job state"
```

---

## Task 3: Frontend — fire-and-forget + live status polling

**Files:**
- Modify: `frontend/src/app/core/api.service.ts` (`SyncStatus` ~line 315; `triggerSync` ~line 892)
- Modify: `frontend/src/app/features/admin/admin-dashboard.ts` (imports line 1; class `implements` line 205; `syncing`/`syncMessage` ~217; `triggerSync` ~292)

**Interfaces:**
- Consumes: `GET /admin/sync-status` now returns `{..., job: {state, started_at, ended_at, result, message}}`; `POST /admin/trigger-sync` returns `{status: 'started'|'already_running'|'error', message?}`.
- Produces: UI behavior only.

- [ ] **Step 1: Update `api.service.ts` types**

Replace the `SyncStatus` interface (~line 315) to add the `job` block, and add a `SyncJob` type above it:

```typescript
export interface SyncJob {
  state: 'idle' | 'running' | 'done' | 'error';
  started_at: string | null;
  ended_at: string | null;
  result: {
    success?: boolean;
    sync_summary?: string;
    classify_summary?: string;
    done_line?: string;
    elapsed_s?: number;
  } | null;
  message: string;
}

export interface SyncStatus {
  jira: { last_sync_line: string; ticket_count: number };
  drive: { last_sync: string; file_count: number };
  feedback: { pending_count: number };
  job?: SyncJob;
}
```

Replace `triggerSync()` (~line 892) so the return type matches the new endpoint:

```typescript
  triggerSync(): Observable<{ status: 'started' | 'already_running' | 'error'; message?: string }> {
    return this.http.post<{ status: 'started' | 'already_running' | 'error'; message?: string }>(
      `${API_BASE}/admin/trigger-sync`, {}, { headers: this.adminHeaders() });
  }
```

- [ ] **Step 2: Verify the build still compiles**

Run: `cd frontend && npx ng build 2>&1 | tail -4`
Expected: build succeeds (pre-existing budget warnings OK).

- [ ] **Step 3: Update `admin-dashboard.ts` — polling + richer status**

(a) Import `OnDestroy` and the `SyncJob` type (line 1, line 4):
```typescript
import { Component, signal, computed, inject, OnInit, OnDestroy } from '@angular/core';
```
```typescript
import { ApiService, SyncStatus, SyncJob, IngestItem, FeedbackRecord, AdminUser } from '../../core/api.service';
```

(b) Class header (~line 205):
```typescript
export class AdminDashboard implements OnInit, OnDestroy {
```

(c) Add a poll handle near the `syncing` signal (~line 217):
```typescript
  private syncPoll: ReturnType<typeof setInterval> | null = null;
```

(d) Replace `triggerSync()` (~line 292) with start-then-poll logic:
```typescript
  triggerSync() {
    this.syncing.set(true);
    this.syncMessage.set('Starting full sync (fetch + classify)…');
    this.api.triggerSync().subscribe({
      next: r => {
        if (r.status === 'already_running') {
          this.syncMessage.set('A sync is already running — watching progress…');
        } else if (r.status === 'error') {
          this.syncing.set(false);
          this.syncMessage.set(`Could not start sync: ${r.message ?? 'unknown error'}`);
          return;
        } else {
          this.syncMessage.set('Sync in progress… (fetching + classifying tickets)');
        }
        this.startSyncPolling();
      },
      error: () => {
        this.syncing.set(false);
        this.syncMessage.set('Could not start sync (request failed).');
      },
    });
  }

  private startSyncPolling() {
    this.stopSyncPolling();
    this.syncPoll = setInterval(() => {
      this.api.getSyncStatus().subscribe({
        next: s => {
          this.status.set(s);
          const job: SyncJob | undefined = s.job;
          if (!job || job.state === 'running') return;
          this.stopSyncPolling();
          this.syncing.set(false);
          if (job.state === 'done') {
            const r = job.result || {};
            const parts = [r.sync_summary, r.classify_summary].filter(Boolean).join(' · ');
            this.syncMessage.set(`✓ Sync complete${parts ? ' — ' + parts : ''}`);
          } else if (job.state === 'error') {
            this.syncMessage.set(`Sync failed: ${job.message || 'see logs'}`);
          }
        },
        error: () => { /* transient poll error — keep polling */ },
      });
    }, 5000);
  }

  private stopSyncPolling() {
    if (this.syncPoll) { clearInterval(this.syncPoll); this.syncPoll = null; }
  }

  ngOnDestroy() {
    this.stopSyncPolling();
  }
```

(Leave the existing button markup as-is — `[disabled]="syncing()"` already disables it while a run is active; `syncMessage()` already renders below it.)

- [ ] **Step 4: Verify the build compiles**

Run: `cd frontend && npx ng build 2>&1 | tail -4`
Expected: build succeeds, no TS errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/app/core/api.service.ts frontend/src/app/features/admin/admin-dashboard.ts
git commit -m "feat(admin-ui): Sync now button polls full-pipeline job status to completion"
```

---

## Task 4: Full verification

- [ ] **Step 1: Backend suite**

Run: `venv/bin/pytest tests/test_sync_job.py tests/test_sync_job_admin.py -v`
Expected: all PASS.

- [ ] **Step 2: No regressions**

Run: `venv/bin/pytest -q 2>&1 | tail -6`
Expected: only the known pre-existing/environmental failures (Google-auth 500-vs-403, 2 PMS network-timeout tests, ingest lock ordering, lifespan `.env` reload). No new failures.

- [ ] **Step 3: Frontend build**

Run: `cd frontend && npx ng build 2>&1 | tail -4`
Expected: succeeds (pre-existing budget warnings only).

- [ ] **Step 4: Manual smoke (after restarting the backend)**

1. Restart backend + frontend; open Admin.
2. Click **Sync now** → message shows "Sync in progress…", button disables.
3. Click again while running → message reflects "already running" (no second pipeline).
4. On completion → "✓ Sync complete — fetched=… · N tickets, $cost".
5. Confirm classification advanced: `SELECT substr(MAX(classified_at),1,10) FROM ticket_classifications;` → today.

---

## Self-review notes (for the implementer)
- **Spec coverage:** job tracker → Task 1; endpoint repoint + status exposure → Task 2; fire-and-forget + polling + overlap UI → Task 3; tests/verification → Tasks 1-4. Error handling (fail-open, error state, already_running) covered in Tasks 1 & 3.
- **Type consistency:** `start()`/`status()` shapes match between `sync_job.py` (Task 1), `admin_api` (Task 2), and the TS `SyncJob`/`triggerSync` types (Task 3). The handler key names (`sync_summary`, `classify_summary`, `done_line`, `success`, `error`) match `backend/tools/trigger_sync.py:_run_synchronous`.
- **Reload safety:** Global Constraints require stopping the backend before Tasks 1-2 (`.py` edits); Task 3 is frontend-only.
