-- 170: wiki_chunks — section-level wiki chunks for hybrid retrieval (wiki v2).
-- Nullable embedding: rows are inserted by scripts/embed_wiki.py with vectors;
-- an all-NULL/empty table means "backfill pending" and the retriever degrades
-- to the keyword path. Safe to deploy ahead of application code.

CREATE TABLE IF NOT EXISTS wiki_chunks (
  id             BIGSERIAL PRIMARY KEY,
  agent_id       TEXT NOT NULL,
  page_path      TEXT NOT NULL,
  section_anchor TEXT NOT NULL DEFAULT '',
  section_title  TEXT NOT NULL DEFAULT '',
  page_type      TEXT NOT NULL DEFAULT '',
  chunk_index    INT  NOT NULL DEFAULT 0,
  chunk_text     TEXT NOT NULL,
  last_updated   TEXT,
  content_hash   TEXT NOT NULL,
  embedding      vector(768),
  search_tsv     tsvector GENERATED ALWAYS AS (to_tsvector('english', chunk_text)) STORED
);

CREATE INDEX IF NOT EXISTS idx_wiki_chunks_embedding ON wiki_chunks
  USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);
CREATE INDEX IF NOT EXISTS idx_wiki_chunks_tsv  ON wiki_chunks USING gin (search_tsv);
CREATE INDEX IF NOT EXISTS idx_wiki_chunks_page ON wiki_chunks (agent_id, page_path);
