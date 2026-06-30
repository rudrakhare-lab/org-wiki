-- 150_retrieval_v2.sql — hybrid retrieval schema for Jira Retrieval v2.
-- Idempotent. Applied at startup by db.init_db().

-- ── 1. BM25 / lexical search ──────────────────────────────────────────────
ALTER TABLE tickets ADD COLUMN IF NOT EXISTS search_tsv tsvector
    GENERATED ALWAYS AS (
        setweight(to_tsvector('english', coalesce(summary,'')),          'A') ||
        setweight(to_tsvector('english', coalesce(description_text,'')), 'B') ||
        setweight(to_tsvector('english', coalesce(comments_text,'')),    'C')
    ) STORED;
CREATE INDEX IF NOT EXISTS idx_tickets_tsv ON tickets USING GIN (search_tsv);

-- ── 2. Dense / semantic search ────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS vector;
ALTER TABLE tickets ADD COLUMN IF NOT EXISTS embedding vector(768);
ALTER TABLE tickets ADD COLUMN IF NOT EXISTS embedded_at timestamptz;
CREATE INDEX IF NOT EXISTS idx_tickets_embedding
    ON tickets USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- ── 3. Normalized relationships ───────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ticket_links (
    src_key   text NOT NULL REFERENCES tickets(key) ON DELETE CASCADE,
    dst_key   text NOT NULL,
    link_type text NOT NULL,
    PRIMARY KEY (src_key, dst_key, link_type)
);
CREATE INDEX IF NOT EXISTS idx_links_dst ON ticket_links (dst_key, link_type);
CREATE INDEX IF NOT EXISTS idx_links_src ON ticket_links (src_key, link_type);

-- ── 4. Shadow-mode logging (Phase 2 evaluation) ───────────────────────────
CREATE TABLE IF NOT EXISTS retrieval_shadow_log (
    id            bigserial PRIMARY KEY,
    trace_id      text,
    question      text NOT NULL,
    v1_keys       text[],
    v2_keys       text[],
    v2_scores     real[],
    v2_confidence text,
    v2_latency_ms integer,
    served_v2     boolean NOT NULL,
    created_at    timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_shadow_created ON retrieval_shadow_log (created_at);
