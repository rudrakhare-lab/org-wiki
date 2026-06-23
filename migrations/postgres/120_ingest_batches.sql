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
