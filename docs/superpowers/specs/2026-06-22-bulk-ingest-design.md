# Bulk Dump Ingestion (backend-driven, durable)

_Date: 2026-06-22_
_Status: approved (pending spec review)_

## Context
Today the ingest tab handles **one file at a time** through a human-in-the-loop flow:
upload → LLM **plan** → admin **approves** → LLM **execute** (writes schema-conformant
wiki pages + rebuilds the index). It's agent-scoped and already replicates to every agent.

Users want to import **many files at once** ("dump and walk away"). We are NOT adding a
verbatim pre-made-`.md` path — see "Decision: no verbatim `.md`" below; `.md` is still
accepted as a *source* and normalized by the pipeline like any other file. We keep the
existing single-file review flow and ADD a **bulk dump**: select/drop N files, hit Run, and
the **backend** runs them through the existing plan→execute pipeline **serially and
automatically (no per-file approval)**, persisting batch state so the user can close the
tab/laptop. The frontend polls one status endpoint and shows per-file progress.

## Decision: no verbatim `.md` (rejected during brainstorming)
We considered letting users drop already-written `.md` files into the KB verbatim (with
validation). Rejected because it would bypass schema enforcement, cross-linking
(`depends_on`/`used_by`, `index.md`/`log.md`), dedup, and provenance — degrading KB
consistency and the knowledge graph — and making it safe would mean re-implementing the
pipeline we already have. `.md` remains an accepted *source* (normalized by the pipeline).
Single, schema-enforcing ingestion path only.

## Decisions (confirmed with user)
- **Bulk = auto-run** each file end-to-end (plan→execute), no per-file approval.
- **Backend-driven + durable**: batch state persisted in Postgres; survives tab/laptop close.
- **Serial** (respects the existing global ingest mutex); one file at a time.
- **Per-file progress** states: `queued → planning → writing → done | failed`; a failed file
  does not stop the batch. Overall progress bar = `(done + failed) / total`.
- **Keep** the existing single-file review flow; bulk is an added mode.
- Agent-scoped + access-gated (reuses `_require_developer_or_admin` + `_require_agent_access`).

## Architecture & flow
```
Upload N files (reuse POST /api/ingest/upload → N upload_ids)
   POST /api/ingest/bulk {upload_ids[]} → create batch + item rows, start background
        runner, return {batch_id}
   Runner (async, serial, holds the existing global mutex per file): for each queued item →
        plan (reuse plan internals) → AUTO-execute (reuse execute internals) →
        mark item done/failed (record page_paths or error) → next
   Frontend polls GET /api/ingest/bulk/{batch_id} → per-file rows + overall progress bar
```

## Data model (migration `migrations/postgres/120_ingest_batches.sql`, idempotent)
```sql
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
    status      TEXT NOT NULL DEFAULT 'queued',  -- queued | planning | writing | done | failed
    error       TEXT,
    page_paths  TEXT,                            -- JSON array of pages written
    updated_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_ingest_batch_items_batch ON ingest_batch_items (batch_id, ord);
```
Durable across backend restarts. On startup a reconciler marks any `running` batch and its
`planning`/`writing` items as `interrupted` (truthful UI; user can re-run failed/interrupted).
Full mid-file auto-resume is deferred — v1 surfaces interruption, not silent resume.

## Backend components
- **`backend/ingest_batch.py`** (new):
  - `create_batch(agent_id, created_by, upload_ids: list[str]) -> dict` — validates upload_ids
    (each must exist in the agent's `_uploads`), inserts batch + item rows (`queued`), returns
    `{batch_id, total}`. Empty/all-invalid → error.
  - `run_batch(batch_id)` — async serial runner: for each `queued` item in `ord`,
    set `planning` → run the plan internals → set `writing` → run the execute internals
    (auto-approved) → set `done` (+ `page_paths`) or `failed` (+ `error`); update batch
    `completed`/`failed`; set batch `done` at end. Per-item try/except; holds the existing
    ingest mutex per file (no parallel LLM ingests).
  - `get_batch(batch_id) -> dict | None` — `{batch: {...}, items: [...]}`.
  - `reconcile_interrupted()` — called from lifespan startup.
  - Reuses the existing plan + execute service functions from `ingest_service`/`ingest_api`
    (refactor the per-file plan and execute bodies into callable helpers if they're currently
    inline in the endpoint jobs — keep single-file endpoints behaving identically).
- **Endpoints** (`ingest_api.py`, gated `_require_developer_or_admin` + `_require_agent_access`,
  agent resolved from `X-Agent-Id`):
  - `POST /api/ingest/bulk` → `create_batch` + spawn `run_batch` as a background task → `{batch_id, total}`.
  - `GET /api/ingest/bulk/{batch_id}` → `get_batch` (404 if unknown).
- **Lifespan**: call `ingest_batch.reconcile_interrupted()` at startup (fail-open).

## Frontend
- Ingest tab gains a **Bulk dump** mode (toggle/segment alongside the existing single-file flow):
  - Multi-file select/drop (same accepted types: pdf/docx/xlsx/md/txt/rtf).
  - Upload each via the existing `/api/ingest/upload`, showing an upload indicator; collect `upload_ids`.
  - **Run** → `POST /api/ingest/bulk` → store `batch_id` in localStorage → poll
    `GET /api/ingest/bulk/{batch_id}` (~2s).
  - Render **per-file rows** with state chips (`queued|planning|writing|done|failed`, error on
    failure) + an **overall progress bar** (`(completed+failed)/total`), and a final summary
    (N done / M failed). On return with a persisted `batch_id`, resume polling.
- The existing single-file review flow is unchanged.
- `api.service.ts`: `startBulkIngest(uploadIds: string[])`, `getBulkStatus(batchId)`.

## Edge cases
- A file failing → `failed` + error; batch continues; counts stay correct.
- Serial only (existing global mutex) — no parallel LLM ingests.
- Backend restart mid-batch → in-flight items → `interrupted`; user re-runs.
- Agent-scoped writes; access-gated; auto-replicates to new agents.
- Invalid/empty `upload_ids` → 400; oversized files already blocked at upload (100 MB).
- Polling a finished/unknown batch → returns terminal state / 404 cleanly.

## Testing
- Backend: create_batch (queues N items, rejects empty/invalid); run_batch processes serially,
  marks done, writes page_paths; a forced plan/execute failure on one item → that item `failed`,
  batch continues, overall counts correct, batch ends `done`; reconcile_interrupted flips
  in-flight → interrupted; get_batch shape; endpoints require dev/admin + agent access.
  (Plan/execute internals mocked so tests don't call a real LLM.)
- Frontend: `ng build` clean; progress states + bar render; resume via persisted batch_id.

## Out of scope
- Verbatim/pre-made `.md` placement (rejected above).
- Parallel ingestion (serial by design / mutex).
- Mid-file auto-resume after a backend restart (v1 marks interrupted + re-run).
- Per-file approval in bulk (explicitly auto-run).
