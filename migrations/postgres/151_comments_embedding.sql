-- 151_comments_embedding.sql — dual-vector retrieval for retrieval-v2.
-- Adds a second embedding column for comment content, plus HNSW index.
-- Idempotent. Applied at startup by db.init_db().
--
-- See docs/superpowers/specs/2026-07-02-retrieval-v2-timeline-and-comments-design.md §6.1

ALTER TABLE tickets
    ADD COLUMN IF NOT EXISTS comments_embedding vector(768);

CREATE INDEX IF NOT EXISTS idx_tickets_comments_embedding
    ON tickets USING hnsw (comments_embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
