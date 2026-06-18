# Admin "Sync now" button runs the FULL Jira pipeline (fetch + classify)

_Date: 2026-06-19_
_Status: approved (pending spec review)_

## Context
The admin **"Sync now"** button calls `admin_api.trigger_jira_sync()`, which runs only
**Stage 1** (`jira_sync.py --incremental` — fetch tickets). It never runs **Stage 2**
(`classify_jira.py` — AI classification). Result: after clicking sync, freshly-fetched
tickets land in the DB but are **not classified** (observed: 90 recent tickets with no
`ticket_classifications` row; `last_classified` stuck at the load date). Module/type/bug
queries don't see those tickets correctly.

This change makes the button run the **full pipeline** (fetch **+** classify) so one click
brings the KB fully up to date. A ready-made full-pipeline runner already exists
(`backend/tools/trigger_sync.py` delta mode → `scripts/jira_daily_sync.py`); the button
just needs to use it, run it in the background (it takes minutes), block overlapping runs,
and report progress/result to the admin.

## Decisions (confirmed with user)
- **Scope:** Jira pipeline only — Stage 1 fetch + Stage 2 classify. (Drive/wiki are separate flows; out of scope.)
- **Execution:** fire-and-forget + live status polling (not a synchronous held-open request, which would hit the prod ingress timeout).
- **Overlap:** block concurrent runs — a click while a run is in progress is rejected with a clear message.

## Architecture & flow
```
[Sync now] ─POST /admin/trigger-sync─► sync_job.start()
                                          │ already running? → {status:"already_running"}
                                          │ else: state=running; spawn background thread
                                          ▼
                          thread runs delta pipeline (fetch → classify)
                          via _trigger_jira_sync_handler({"mode":"delta"})
                                          │ on finish → store result; state=done|error
   UI polls GET /admin/sync-status (~5s) ◄──────────────────────────────────────
   shows: "Sync in progress…" → "Done: fetched/new/updated, classified N, ₹/$cost, Ns"
```
Single-replica prod → an in-process job state + lock is sufficient to block overlaps.
(Multi-replica would need a DB/advisory lock — noted as a future limitation.)

## Components / files
- **`backend/sync_job.py`** (new) — in-process job tracker:
  - `start() -> dict`: if a run is active, return `{"status": "already_running"}`; else set
    state=running, spawn a `threading.Thread` that runs the pipeline, return `{"status": "started"}`.
  - `status() -> dict`: `{state: idle|running|done|error, started_at, ended_at, result, message}`.
  - A module-level `threading.Lock` + `_running` flag enforce a single run.
  - The worker calls the existing `backend.tools.trigger_sync._trigger_jira_sync_handler({"mode": "delta"})`
    (which runs `jira_daily_sync.py`, captures stdout, parses sync_summary / classify_summary /
    done_line / elapsed_s / cost) and stores that dict as `result`.
  - All worker exceptions caught → state=error with message. Never raises into the request path.
- **`backend/admin_api.py`** — repoint `trigger_jira_sync()` to call `sync_job.start()`
  (full pipeline) instead of the Stage-1-only `Popen`. Add the job state into
  `get_sync_status()` output under a `job` key.
- **`backend/api.py`** — endpoints unchanged in shape: `POST /admin/trigger-sync`
  (now full pipeline, returns `started`/`already_running`) and `GET /admin/sync-status`
  (now also returns `job`). Both stay `_require_admin`.
- **Frontend `frontend/src/app/features/admin/admin-dashboard.ts`** — `triggerSync()`:
  - On `started` → begin polling `getSyncStatus()` every ~5s; button disabled, show "Sync in progress…".
  - On `already_running` → show "A sync is already running" and start/continue polling.
  - On poll `state=done` → show summary (fetched/new/updated, classified count, cost, elapsed); stop polling.
  - On `state=error` → show the error message; stop polling.
  - Guard against leaked intervals (clear on destroy / on terminal state).
- **Frontend `frontend/src/app/core/api.service.ts`** — `triggerSync()` return type
  `{status: 'started'|'already_running'|'error', message?}`; `getSyncStatus()` already exists,
  extend its type to include the new `job` field.

## Error handling & edge cases
- Pipeline non-zero exit → state=error, message = done line / stderr tail; UI shows it.
- Missing Jira creds / `ANTHROPIC_API_KEY` → surfaced as the error message (not silent).
- Second click while running → `already_running`; UI keeps polling, no second pipeline.
- Backend restart mid-run → in-memory state resets to idle (the OS subprocess may still
  finish); UI shows idle. Acceptable for single-replica v1.
- Fail-open: any tracker/threading error must never crash the server or block other admin endpoints.

## Testing
- Backend unit (mock `_trigger_jira_sync_handler` so no real sync/LLM call):
  - idle → running → done transition; result stored.
  - error path: handler returns `success: False` → state=error with message.
  - overlap: while running, `start()` returns `already_running` and does NOT spawn a second thread.
  - `status()` shape stable in each state.
- Frontend: `ng build` clean; manual check that polling shows progress → done and the button re-enables.

## Out of scope
- Google Drive sync, wiki index rebuild (separate flows).
- Multi-replica-safe distributed locking (single replica today; note as future work).
- The nightly scheduler (already runs the full `jira_daily_sync.py`) — unchanged.
