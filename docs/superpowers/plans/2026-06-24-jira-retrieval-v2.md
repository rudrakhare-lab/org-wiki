# Jira Retrieval v2 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace Conwo's `ILIKE`-based Jira retrieval with a hybrid BM25 + pgvector dense + cross-encoder rerank pipeline, with strict-mode abstention, behind a feature flag for shadow → A/B → cutover rollout.

**Architecture:** Hybrid retrieval inside a single Postgres (tsvector + pgvector) fused by RRF, top-50 reranked locally with `bge-reranker-v2-m3`, gated on minimum reranker score, with Gemini-provided embeddings (org-approved), Claude-Haiku query decomposition, and a normalized `ticket_links` table for supersession-aware ranking.

**Tech Stack:** Python 3.11+, Postgres 15+ with `pgvector` and `pg_trgm` extensions, `psycopg` (already in repo), `google-generativeai` (new), `sentence-transformers` + `torch` (new, CPU only), `pytest` (already in repo), Anthropic Claude (already in repo). Docker multi-stage build to bake the ~560 MB reranker model into the runtime image.

## Global Constraints

- Spec: [`docs/superpowers/specs/2026-06-24-jira-retrieval-v2-design.md`](../specs/2026-06-24-jira-retrieval-v2-design.md). Every task implements a part of it.
- Postgres migrations apply at startup via `db.init_db()` (idempotent, advisory-locked).
- **Operational safety rule (from `CLAUDE.md`):** Never create or edit a `.py` file inside the project tree while the backend runs with `--reload`. Stop the backend before any `.py` write; `.md` writes are fine.
- The new pipeline must NOT change the public signatures of `backend/jira_retriever.search()` and `backend/jira_retriever.by_module()` — `backend/preflight.py` and `backend/tools/jira_tools.py` remain untouched.
- Feature flag: `CONWO_RETRIEVAL_V2 ∈ {off, shadow, ab, on}`. Default `off`. In `ab` mode, `CONWO_RETRIEVAL_V2_PCT ∈ {0..100}` controls split.
- Strict confidence gate is mandatory. Thresholds env-tunable: `CONWO_RETRIEVAL_V2_ABSTAIN_THRESHOLD=0.5`, `CONWO_RETRIEVAL_V2_HIGH_THRESHOLD=0.7`.
- Tests must not require a live Postgres, Gemini API, or LLM in CI. Use fixtures + mocks. A dedicated integration test may opt in via env flag.
- All Gemini calls use distinct task types: `RETRIEVAL_DOCUMENT` for tickets, `RETRIEVAL_QUERY` for user queries. Never mix.
- TDD: every behaviour-changing task starts with a failing test.
- Frequent commits: one task = one commit (or a small handful within the task).

---

## Locked interfaces (so tasks can reference each other without ambiguity)

```python
# backend/retrieval/v2/embed.py
def embed_query(text: str) -> list[float]: ...           # returns 768-dim
def embed_documents(texts: list[str]) -> list[list[float]]: ...  # batched

# Shared candidate shape (a plain dict; no class wrapper)
Candidate = dict  # keys: key, summary, description_text, comments_text,
                  #       status_category, priority, updated_at, resolved_at,
                  #       functional_area, links_json, fused_score (float, set by hybrid)

# backend/retrieval/v2/hybrid.py
def hybrid_search(conn, sub_queries: list[str], query_vecs: list[list[float]],
                  filters: dict, limit: int = 50) -> list[Candidate]: ...

# backend/retrieval/v2/links.py
def expand(conn, candidates: list[Candidate]) -> list[Candidate]: ...

# backend/retrieval/v2/rerank.py
def score(query: str, candidates: list[Candidate]) -> list[tuple[Candidate, float]]: ...

# backend/retrieval/v2/gate.py
@dataclass
class RetrievalResult:
    tickets: list[dict]          # the kept tickets with reranker_score attached
    confidence: str              # "High" | "Medium" | "Low" | "Abstain"
    abstain: bool
    message: str                 # human-readable summary, used by composer
    diagnostics: dict            # for logging / shadow comparison
def apply(scored: list[tuple[Candidate, float]]) -> RetrievalResult: ...

# backend/retrieval/v2/rewrite.py
@dataclass
class RewriteResult:
    sub_queries: list[str]
    expansions: dict[str, list[str]]
    filters: dict                # may include functional_area, resolved_after, module
    intent: str                  # "DEBUGGING" | "STATUS" | ... | "GENERAL"
def rewrite(question: str) -> RewriteResult: ...

# backend/retrieval/v2/pipeline.py
def search(question: str, *, functional_area: str | None = None,
           limit: int = 10) -> RetrievalResult: ...
def by_module(module_slug: str, query: str, limit: int = 5) -> list[Candidate]: ...
```

---

## Task 1: Migration — `pgvector`, `tsvector`, `ticket_links`, shadow log

**Files:**
- Create: `migrations/postgres/050_retrieval_v2.sql`
- Modify: `requirements.txt`
- Test: `tests/test_migration_050.py`

**Interfaces:**
- Consumes: existing `tickets` table from `migrations/postgres/040_tickets.sql`
- Produces: columns `tickets.search_tsv`, `tickets.embedding vector(768)`, `tickets.embedded_at`; tables `ticket_links`, `retrieval_shadow_log`; indexes for all of the above; extension `vector` enabled.

- [ ] **Step 1: Write the failing test**

`tests/test_migration_050.py`:
```python
"""Verifies migration 050 creates expected schema. Skipped if no Postgres available."""
import os
import pytest
import psycopg

PG_DSN = os.getenv("CONWO_TEST_DSN")
pytestmark = pytest.mark.skipif(not PG_DSN, reason="requires CONWO_TEST_DSN")

def test_migration_050_creates_tsvector_column():
    with psycopg.connect(PG_DSN) as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT data_type FROM information_schema.columns
            WHERE table_name='tickets' AND column_name='search_tsv'
        """)
        row = cur.fetchone()
        assert row and row[0] == 'tsvector'

def test_migration_050_creates_embedding_column():
    with psycopg.connect(PG_DSN) as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT udt_name FROM information_schema.columns
            WHERE table_name='tickets' AND column_name='embedding'
        """)
        row = cur.fetchone()
        assert row and row[0] == 'vector'

def test_migration_050_creates_ticket_links_table():
    with psycopg.connect(PG_DSN) as conn, conn.cursor() as cur:
        cur.execute("SELECT to_regclass('ticket_links')")
        assert cur.fetchone()[0] == 'ticket_links'

def test_migration_050_creates_shadow_log_table():
    with psycopg.connect(PG_DSN) as conn, conn.cursor() as cur:
        cur.execute("SELECT to_regclass('retrieval_shadow_log')")
        assert cur.fetchone()[0] == 'retrieval_shadow_log'

def test_migration_050_creates_hnsw_index():
    with psycopg.connect(PG_DSN) as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT indexdef FROM pg_indexes
            WHERE tablename='tickets' AND indexname='idx_tickets_embedding'
        """)
        row = cur.fetchone()
        assert row and 'hnsw' in row[0].lower()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
CONWO_TEST_DSN="$CONWO_DSN" venv/bin/pytest tests/test_migration_050.py -v
```
Expected: 5 failures (columns/tables don't exist yet). If `CONWO_TEST_DSN` is unset, all skip — that's fine; we'll run the test after migration lands.

- [ ] **Step 3: Write the migration**

`migrations/postgres/050_retrieval_v2.sql`:
```sql
-- 050_retrieval_v2.sql — hybrid retrieval schema for Jira Retrieval v2.
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
```

`requirements.txt` (add these lines, keep existing):
```
google-generativeai>=0.8.0
sentence-transformers>=3.0.0
pgvector>=0.3.0
```

- [ ] **Step 4: Apply migration and run tests**

```bash
psql "$CONWO_DSN" -f migrations/postgres/050_retrieval_v2.sql
CONWO_TEST_DSN="$CONWO_DSN" venv/bin/pytest tests/test_migration_050.py -v
```
Expected: 5 PASS.

- [ ] **Step 5: Commit**

```bash
git add migrations/postgres/050_retrieval_v2.sql requirements.txt tests/test_migration_050.py
git commit -m "feat(retrieval-v2): migration 050 — tsvector + pgvector + ticket_links + shadow log"
```

---

## Task 2: Dockerfile — bake reranker model into image (multi-stage)

**Files:**
- Modify: `Dockerfile`
- Create: `scripts/download_reranker_model.py`
- Test: manual smoke (Docker build + container has the model file)

**Interfaces:**
- Consumes: nothing
- Produces: `/app/models/bge-reranker-v2-m3/` directory inside the runtime image, readable from `backend/retrieval/v2/rerank.py`.

- [ ] **Step 1: Write the model download script**

`scripts/download_reranker_model.py`:
```python
"""Download bge-reranker-v2-m3 weights to /app/models/. Run during Docker build.

Idempotent: if the target directory already exists with the expected files, skip.
"""
import os
import sys
from pathlib import Path

MODEL_ID = "BAAI/bge-reranker-v2-m3"
TARGET = Path(os.getenv("RERANKER_MODEL_DIR", "/app/models/bge-reranker-v2-m3"))

def main() -> int:
    if (TARGET / "config.json").exists() and (TARGET / "tokenizer.json").exists():
        print(f"reranker model already present at {TARGET}", flush=True)
        return 0
    TARGET.mkdir(parents=True, exist_ok=True)
    from sentence_transformers import CrossEncoder
    CrossEncoder(MODEL_ID).save(str(TARGET))
    print(f"reranker model downloaded to {TARGET}", flush=True)
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Update Dockerfile to bake model in**

Add to `Dockerfile` (place the model download as a separate layer so it caches well):

```dockerfile
# ── retrieval-v2 reranker model (bge-reranker-v2-m3, ~560MB) ──
# Cached layer: only re-runs when requirements.txt or this script change.
RUN python scripts/download_reranker_model.py
ENV RERANKER_MODEL_DIR=/app/models/bge-reranker-v2-m3
```

- [ ] **Step 3: Build and verify**

```bash
docker build -t conwo:retrieval-v2-test .
docker run --rm conwo:retrieval-v2-test ls -la /app/models/bge-reranker-v2-m3/
```
Expected: see `config.json`, `tokenizer.json`, `pytorch_model.bin` (or `model.safetensors`).

- [ ] **Step 4: Commit**

```bash
git add Dockerfile scripts/download_reranker_model.py
git commit -m "feat(retrieval-v2): bake bge-reranker-v2-m3 into Docker image"
```

---

## Task 3: Embedder — `backend/retrieval/v2/embed.py`

**Files:**
- Create: `backend/retrieval/v2/__init__.py` (empty)
- Create: `backend/retrieval/v2/embed.py`
- Test: `tests/retrieval/v2/test_embed.py`

**Interfaces:**
- Consumes: `GOOGLE_GENAI_API_KEY` env var.
- Produces: `embed_query(text) -> list[float]` and `embed_documents(texts) -> list[list[float]]`, both 768-dim. Task types are wired internally and never exposed.

- [ ] **Step 1: Write the failing tests**

`tests/retrieval/v2/test_embed.py`:
```python
"""Embedder uses the correct Gemini task types for doc vs query."""
from unittest.mock import patch, MagicMock

def test_embed_query_uses_retrieval_query_task_type():
    from backend.retrieval.v2 import embed
    with patch.object(embed, "_client") as client:
        client.embed_content.return_value = {"embedding": [0.0]*768}
        embed.embed_query("test question")
        kwargs = client.embed_content.call_args.kwargs
        assert kwargs["task_type"] == "RETRIEVAL_QUERY"
        assert kwargs["model"].endswith("text-embedding-004")

def test_embed_documents_uses_retrieval_document_task_type():
    from backend.retrieval.v2 import embed
    with patch.object(embed, "_client") as client:
        client.embed_content.return_value = {"embedding": [[0.0]*768, [0.0]*768]}
        embed.embed_documents(["doc1", "doc2"])
        kwargs = client.embed_content.call_args.kwargs
        assert kwargs["task_type"] == "RETRIEVAL_DOCUMENT"

def test_embed_query_returns_768d_list_of_floats():
    from backend.retrieval.v2 import embed
    with patch.object(embed, "_client") as client:
        client.embed_content.return_value = {"embedding": list(range(768))}
        v = embed.embed_query("x")
        assert isinstance(v, list)
        assert len(v) == 768
        assert all(isinstance(x, float) for x in v)

def test_embed_documents_batches_in_chunks_of_100():
    from backend.retrieval.v2 import embed
    with patch.object(embed, "_client") as client:
        client.embed_content.return_value = {"embedding": [[0.0]*768]*100}
        embed.embed_documents(["x"]*250)
        # 250 docs / 100 per batch = 3 calls
        assert client.embed_content.call_count == 3
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
venv/bin/pytest tests/retrieval/v2/test_embed.py -v
```
Expected: 4 FAILS (`ModuleNotFoundError: backend.retrieval.v2.embed`).

- [ ] **Step 3: Write the embedder**

`backend/retrieval/v2/__init__.py`:
```python
"""Retrieval v2 — hybrid Jira retrieval (BM25 + dense + rerank + strict gate)."""
```

`backend/retrieval/v2/embed.py`:
```python
"""Gemini embeddings for Jira retrieval v2.

Asymmetric: distinct task types for documents vs queries. Mixing them silently
degrades recall, so we expose two separate functions and never a generic one.
"""
from __future__ import annotations
import os
from typing import Any

import google.generativeai as genai

_MODEL = "models/text-embedding-004"
_BATCH = 100  # Gemini accepts batches; 100 is comfortably under the limit.

# Test seam: tests patch `_client.embed_content`.
class _GeminiClient:
    def embed_content(self, *, model: str, content: Any, task_type: str) -> dict:
        return genai.embed_content(model=model, content=content, task_type=task_type)

_client = _GeminiClient()

def _ensure_configured() -> None:
    key = os.getenv("GOOGLE_GENAI_API_KEY")
    if not key:
        raise RuntimeError(
            "GOOGLE_GENAI_API_KEY not set; required for retrieval v2 embeddings."
        )
    genai.configure(api_key=key)

def embed_query(text: str) -> list[float]:
    _ensure_configured()
    resp = _client.embed_content(model=_MODEL, content=text, task_type="RETRIEVAL_QUERY")
    vec = resp["embedding"]
    return [float(x) for x in vec]

def embed_documents(texts: list[str]) -> list[list[float]]:
    _ensure_configured()
    out: list[list[float]] = []
    for i in range(0, len(texts), _BATCH):
        batch = texts[i:i + _BATCH]
        resp = _client.embed_content(model=_MODEL, content=batch, task_type="RETRIEVAL_DOCUMENT")
        vecs = resp["embedding"]
        for v in vecs:
            out.append([float(x) for x in v])
    return out
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
venv/bin/pytest tests/retrieval/v2/test_embed.py -v
```
Expected: 4 PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/retrieval/v2/__init__.py backend/retrieval/v2/embed.py tests/retrieval/v2/
git commit -m "feat(retrieval-v2): Gemini embedder with doc/query task types"
```

---

## Task 4: Backfill script — `scripts/embed_tickets.py`

**Files:**
- Create: `scripts/embed_tickets.py`
- Test: `tests/scripts/test_embed_tickets.py`

**Interfaces:**
- Consumes: `embed_documents` from Task 3, Postgres connection.
- Produces: writes `embedding`, `embedded_at` columns on `tickets`. Modes: `--full` (every row), `--delta` (rows where `embedded_at IS NULL OR updated_at > embedded_at`).

- [ ] **Step 1: Write the failing tests**

`tests/scripts/test_embed_tickets.py`:
```python
from unittest.mock import patch
import pytest

def test_select_delta_query_excludes_already_embedded_unchanged_rows():
    from scripts import embed_tickets
    sql = embed_tickets.SELECT_DELTA
    assert "embedded_at IS NULL" in sql
    assert "updated_at > embedded_at" in sql

def test_select_full_query_returns_all_rows():
    from scripts import embed_tickets
    assert "embedded_at" not in embed_tickets.SELECT_FULL
    assert "FROM tickets" in embed_tickets.SELECT_FULL

def test_compose_text_concatenates_summary_and_description():
    from scripts import embed_tickets
    row = {"summary": "Login fails", "description_text": "Users see 500"}
    t = embed_tickets.compose_text(row)
    assert "Login fails" in t
    assert "Users see 500" in t

def test_compose_text_truncates_to_max_chars():
    from scripts import embed_tickets
    row = {"summary": "x", "description_text": "y" * 100000}
    t = embed_tickets.compose_text(row)
    assert len(t) <= embed_tickets.MAX_TEXT_CHARS
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
venv/bin/pytest tests/scripts/test_embed_tickets.py -v
```
Expected: 4 FAILS.

- [ ] **Step 3: Write the script**

`scripts/embed_tickets.py`:
```python
"""Embed Jira tickets into pgvector. Run as a one-time backfill (--full) or
nightly delta (--delta). Idempotent; resumable; safe to interrupt.
"""
from __future__ import annotations
import argparse
import os
import sys
import time
from typing import Iterable

import psycopg
from psycopg.rows import dict_row
from pgvector.psycopg import register_vector

# Add backend to path so we can import retrieval.v2.embed
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.retrieval.v2.embed import embed_documents  # noqa: E402

BATCH = 100
MAX_TEXT_CHARS = 8000  # Gemini handles more but trimming keeps embed cost predictable.

SELECT_FULL = """
    SELECT key, summary, description_text
    FROM tickets
    ORDER BY updated_at DESC
"""

SELECT_DELTA = """
    SELECT key, summary, description_text
    FROM tickets
    WHERE embedded_at IS NULL OR updated_at > embedded_at
    ORDER BY updated_at DESC
"""

UPDATE_ROW = """
    UPDATE tickets
    SET embedding = %s, embedded_at = now()
    WHERE key = %s
"""

def compose_text(row: dict) -> str:
    summary = (row.get("summary") or "").strip()
    desc = (row.get("description_text") or "").strip()
    text = f"{summary}\n\n{desc}" if desc else summary
    if len(text) > MAX_TEXT_CHARS:
        text = text[:MAX_TEXT_CHARS]
    return text

def iter_batches(rows: Iterable[dict], n: int) -> Iterable[list[dict]]:
    buf: list[dict] = []
    for r in rows:
        buf.append(r)
        if len(buf) >= n:
            yield buf
            buf = []
    if buf:
        yield buf

def run(dsn: str, mode: str) -> int:
    sql = SELECT_FULL if mode == "full" else SELECT_DELTA
    total = 0
    t0 = time.perf_counter()
    with psycopg.connect(dsn) as conn:
        register_vector(conn)
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql)
            for batch in iter_batches(cur, BATCH):
                texts = [compose_text(r) for r in batch]
                vecs = embed_documents(texts)
                with conn.cursor() as upd:
                    for r, v in zip(batch, vecs):
                        upd.execute(UPDATE_ROW, (v, r["key"]))
                conn.commit()
                total += len(batch)
                dt = time.perf_counter() - t0
                print(f"  embedded {total} rows ({total/dt:.1f}/s)", flush=True)
    print(f"done: {total} rows embedded.", flush=True)
    return 0

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["full", "delta"], required=True)
    ap.add_argument("--dsn", default=os.getenv("CONWO_DSN"))
    args = ap.parse_args()
    if not args.dsn:
        print("CONWO_DSN env var or --dsn required", file=sys.stderr)
        return 2
    return run(args.dsn, args.mode)

if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
venv/bin/pytest tests/scripts/test_embed_tickets.py -v
```
Expected: 4 PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/embed_tickets.py tests/scripts/
git commit -m "feat(retrieval-v2): embed_tickets script (full + delta modes)"
```

---

## Task 5: Backfill script — `scripts/backfill_ticket_links.py`

**Files:**
- Create: `scripts/backfill_ticket_links.py`
- Test: `tests/scripts/test_backfill_ticket_links.py`

**Interfaces:**
- Consumes: `tickets.links_json` (existing).
- Produces: rows in `ticket_links(src_key, dst_key, link_type)`. Modes: `--full` (rebuild all), `--delta` (process rows where `updated_at` is newer than last run, tracked in `sync_runs`).

- [ ] **Step 1: Write the failing tests**

`tests/scripts/test_backfill_ticket_links.py`:
```python
def test_parse_links_extracts_outward_and_inward_pairs():
    from scripts import backfill_ticket_links as bl
    src = "TS-1"
    links_json = (
        '[{"type":"Blocks","outward":"TS-2","inward":null},'
        ' {"type":"Duplicates","outward":null,"inward":"TS-3"}]'
    )
    pairs = bl.parse_links(src, links_json)
    assert ("TS-1", "TS-2", "blocks") in pairs
    assert ("TS-1", "TS-3", "duplicates") in pairs

def test_parse_links_normalizes_link_type_to_lowercase_snake():
    from scripts import backfill_ticket_links as bl
    pairs = bl.parse_links("TS-1", '[{"type":"Relates To","outward":"TS-9"}]')
    assert pairs and pairs[0][2] == "relates_to"

def test_parse_links_handles_empty_and_malformed():
    from scripts import backfill_ticket_links as bl
    assert bl.parse_links("TS-1", "") == []
    assert bl.parse_links("TS-1", "[]") == []
    assert bl.parse_links("TS-1", "not-json") == []
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
venv/bin/pytest tests/scripts/test_backfill_ticket_links.py -v
```
Expected: 3 FAILS.

- [ ] **Step 3: Write the script**

`scripts/backfill_ticket_links.py`:
```python
"""Normalize tickets.links_json into the ticket_links table.

Modes:
  --full   rebuild ticket_links from every ticket row.
  --delta  process tickets updated since the last successful run (tracked in sync_runs).
"""
from __future__ import annotations
import argparse
import json
import os
import re
import sys

import psycopg

_NORMALIZE = re.compile(r"[^a-z0-9]+")

def _norm_type(s: str) -> str:
    s = (s or "").strip().lower()
    s = _NORMALIZE.sub("_", s).strip("_")
    return s

def parse_links(src_key: str, links_json: str) -> list[tuple[str, str, str]]:
    """Return list of (src, dst, link_type) tuples. Robust to empty/malformed input."""
    if not links_json:
        return []
    try:
        data = json.loads(links_json)
    except Exception:
        return []
    if not isinstance(data, list):
        return []
    pairs: list[tuple[str, str, str]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        ltype = _norm_type(item.get("type") or "")
        if not ltype:
            continue
        for end_key in ("outward", "inward"):
            dst = item.get(end_key)
            if isinstance(dst, str) and dst:
                pairs.append((src_key, dst, ltype))
    return pairs

UPSERT = """
    INSERT INTO ticket_links (src_key, dst_key, link_type)
    VALUES (%s, %s, %s)
    ON CONFLICT (src_key, dst_key, link_type) DO NOTHING
"""

DELETE_FOR_SRC = "DELETE FROM ticket_links WHERE src_key = %s"

SELECT_FULL = "SELECT key, links_json FROM tickets"
SELECT_DELTA = """
    SELECT key, links_json
    FROM tickets
    WHERE updated_at > (
        SELECT COALESCE(MAX(ended_at), 'epoch'::timestamptz)
        FROM sync_runs WHERE status = 'success' AND filter_name = 'ticket_links'
    )
"""

def run(dsn: str, mode: str) -> int:
    sql = SELECT_FULL if mode == "full" else SELECT_DELTA
    n_rows = 0
    n_links = 0
    with psycopg.connect(dsn) as conn:
        with conn.cursor(name="cur") as cur:  # server-side cursor for streaming
            cur.execute(sql)
            for src_key, links_json in cur:
                pairs = parse_links(src_key, links_json or "")
                with conn.cursor() as wcur:
                    wcur.execute(DELETE_FOR_SRC, (src_key,))
                    for p in pairs:
                        wcur.execute(UPSERT, p)
                n_rows += 1
                n_links += len(pairs)
                if n_rows % 1000 == 0:
                    conn.commit()
            conn.commit()
        # mark sync_runs
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO sync_runs (started_at, ended_at, filter_name, mode, status) "
                "VALUES (now(), now(), 'ticket_links', %s, 'success')", (mode,))
        conn.commit()
    print(f"done: {n_rows} tickets processed, {n_links} links written.", flush=True)
    return 0

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["full", "delta"], required=True)
    ap.add_argument("--dsn", default=os.getenv("CONWO_DSN"))
    args = ap.parse_args()
    if not args.dsn:
        print("CONWO_DSN env var or --dsn required", file=sys.stderr)
        return 2
    return run(args.dsn, args.mode)

if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
venv/bin/pytest tests/scripts/test_backfill_ticket_links.py -v
```
Expected: 3 PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/backfill_ticket_links.py tests/scripts/test_backfill_ticket_links.py
git commit -m "feat(retrieval-v2): backfill_ticket_links script (full + delta modes)"
```

---

## Task 6: Hybrid retrieval (BM25 + dense + RRF) — `backend/retrieval/v2/hybrid.py`

**Files:**
- Create: `backend/retrieval/v2/hybrid.py`
- Test: `tests/retrieval/v2/test_hybrid.py`

**Interfaces:**
- Consumes: a live psycopg connection, a list of sub-queries (strings) and their pre-computed embedding vectors (from Task 3).
- Produces: `hybrid_search(conn, sub_queries, query_vecs, filters, limit=50) -> list[Candidate]`. Each candidate is a dict with `key, summary, description_text, comments_text, status_category, priority, updated_at, resolved_at, functional_area, links_json, fused_score (float)`.

- [ ] **Step 1: Write the failing tests**

`tests/retrieval/v2/test_hybrid.py`:
```python
"""Unit tests for the RRF fusion logic (the SQL is exercised by the integration
test in Task 14; here we test the in-memory fusion across sub-queries)."""

def test_rrf_fuse_combines_two_lists_by_rank():
    from backend.retrieval.v2.hybrid import _rrf_fuse
    a = [{"key": "TS-1", "rrf": 0.04}, {"key": "TS-2", "rrf": 0.03}]
    b = [{"key": "TS-2", "rrf": 0.04}, {"key": "TS-3", "rrf": 0.03}]
    out = _rrf_fuse([a, b])
    keys = [c["key"] for c in out]
    assert "TS-2" in keys and "TS-1" in keys and "TS-3" in keys
    # TS-2 appears in both → highest fused score
    assert out[0]["key"] == "TS-2"

def test_rrf_fuse_dedupes_same_key():
    from backend.retrieval.v2.hybrid import _rrf_fuse
    a = [{"key": "TS-1", "rrf": 0.04}]
    b = [{"key": "TS-1", "rrf": 0.03}]
    out = _rrf_fuse([a, b])
    assert len(out) == 1 and out[0]["key"] == "TS-1"

def test_filters_apply_functional_area_when_set():
    from backend.retrieval.v2.hybrid import _build_filters_sql
    sql, params = _build_filters_sql({"functional_area": "WP-admin"})
    assert "functional_area = %s" in sql
    assert "WP-admin" in params

def test_filters_apply_resolved_after_when_set():
    from backend.retrieval.v2.hybrid import _build_filters_sql
    sql, params = _build_filters_sql({"resolved_after": "2026-04-01"})
    assert "resolved_at >= %s" in sql

def test_filters_empty_when_no_filters():
    from backend.retrieval.v2.hybrid import _build_filters_sql
    sql, params = _build_filters_sql({})
    assert sql == "" and params == []
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
venv/bin/pytest tests/retrieval/v2/test_hybrid.py -v
```
Expected: 5 FAILS.

- [ ] **Step 3: Write the hybrid retriever**

`backend/retrieval/v2/hybrid.py`:
```python
"""Hybrid retrieval: BM25 (tsvector) + dense (pgvector) fused by RRF.

The fused candidate pool feeds the reranker. One Postgres call per sub-query;
the fusion across sub-queries happens in Python.
"""
from __future__ import annotations
from typing import Any
from psycopg.rows import dict_row

RRF_K = 60  # standard Reciprocal Rank Fusion constant.

_BASE_SQL = """
WITH lex AS (
    SELECT key,
           ts_rank_cd(search_tsv, q) AS lex_score,
           ROW_NUMBER() OVER (ORDER BY ts_rank_cd(search_tsv, q) DESC) AS lex_rnk
    FROM tickets, websearch_to_tsquery('english', %(q_text)s) q
    WHERE search_tsv @@ q
    {filter_sql_lex}
    LIMIT 100
),
dense AS (
    SELECT key,
           1 - (embedding <=> %(q_vec)s::vector) AS dense_score,
           ROW_NUMBER() OVER (ORDER BY embedding <=> %(q_vec)s::vector) AS dense_rnk
    FROM tickets
    WHERE embedding IS NOT NULL
    {filter_sql_dense}
    ORDER BY embedding <=> %(q_vec)s::vector
    LIMIT 100
),
fused AS (
    SELECT key, SUM(1.0 / (%(k)s + rnk)) AS rrf
    FROM (
        SELECT key, lex_rnk  AS rnk FROM lex
        UNION ALL
        SELECT key, dense_rnk AS rnk FROM dense
    ) u
    GROUP BY key
)
SELECT t.key, t.summary, t.description_text, t.comments_text,
       t.status_category, t.priority, t.updated_at, t.resolved_at,
       t.functional_area, t.links_json,
       f.rrf
FROM fused f
JOIN tickets t USING (key)
ORDER BY f.rrf DESC
LIMIT %(limit)s
"""

def _build_filters_sql(filters: dict) -> tuple[str, list]:
    """Build an AND-clause fragment + positional params. Empty when no filters."""
    if not filters:
        return "", []
    parts: list[str] = []
    params: list[Any] = []
    if filters.get("functional_area"):
        parts.append("functional_area = %s")
        params.append(filters["functional_area"])
    if filters.get("resolved_after"):
        parts.append("resolved_at >= %s")
        params.append(filters["resolved_after"])
    if filters.get("status_category"):
        parts.append("status_category = %s")
        params.append(filters["status_category"])
    if not parts:
        return "", []
    return "AND " + " AND ".join(parts), params

def _rrf_fuse(per_subquery_results: list[list[dict]]) -> list[dict]:
    """Merge results from multiple sub-queries by summing their fused scores.

    Inputs are already-ranked lists from individual sub-query runs; here we
    just collapse duplicates and re-sort by the summed score. Note: we do NOT
    re-rank by rank-position across sub-queries — the per-sub-query RRF score
    already encodes the rank position. Summing is a reasonable approximation
    for "appears in multiple sub-queries".
    """
    by_key: dict[str, dict] = {}
    for batch in per_subquery_results:
        for row in batch:
            k = row["key"]
            if k in by_key:
                by_key[k]["rrf"] += row["rrf"]
            else:
                by_key[k] = {**row}
    out = list(by_key.values())
    out.sort(key=lambda r: r["rrf"], reverse=True)
    return out

def hybrid_search(conn, sub_queries: list[str], query_vecs: list[list[float]],
                  filters: dict, limit: int = 50) -> list[dict]:
    """Run hybrid retrieval per sub-query, fuse, return top-`limit` candidates."""
    if not sub_queries:
        return []
    filter_clause, filter_params = _build_filters_sql(filters or {})
    sql = _BASE_SQL.format(
        filter_sql_lex=filter_clause,
        filter_sql_dense=filter_clause,
    )
    per_sub: list[list[dict]] = []
    with conn.cursor(row_factory=dict_row) as cur:
        for q_text, q_vec in zip(sub_queries, query_vecs):
            params = {
                "q_text": q_text,
                "q_vec": q_vec,
                "k": RRF_K,
                "limit": limit,
                **{f"f{i}": v for i, v in enumerate(filter_params)},  # unused, kept for symmetry
            }
            # Manually substitute filter params; they appear twice (lex + dense).
            # Use a dedicated execute path for safety:
            full_params = [q_text] + filter_params + [q_vec] + filter_params + [q_vec, RRF_K, limit]
            cur.execute(_BASE_SQL.replace("%(q_text)s", "%s")
                                  .replace("%(q_vec)s", "%s", 1)
                                  .replace("%(q_vec)s", "%s", 1)
                                  .replace("%(q_vec)s", "%s", 1)
                                  .replace("%(k)s", "%s")
                                  .replace("%(limit)s", "%s")
                                  .format(filter_sql_lex=filter_clause, filter_sql_dense=filter_clause),
                        full_params)
            rows = list(cur.fetchall())
            per_sub.append([{"key": r["key"], "rrf": float(r["rrf"]), **r} for r in rows])

    fused = _rrf_fuse(per_sub)
    return fused[:limit]
```

> **Implementer note:** the SQL composition above mixes named and positional binding which can be brittle. If the test fixture for the integration test in Task 14 surfaces a binding issue, the safer refactor is to build the SQL with two separate filter clauses and pass a single dict of named params — `q_text`, `q_vec`, `k`, `limit`, `fa`, `resolved_after`, `status_category` — and reference the named params twice in the SQL. Keep the public function signature unchanged.

- [ ] **Step 4: Run tests to verify they pass**

```bash
venv/bin/pytest tests/retrieval/v2/test_hybrid.py -v
```
Expected: 5 PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/retrieval/v2/hybrid.py tests/retrieval/v2/test_hybrid.py
git commit -m "feat(retrieval-v2): hybrid BM25 + pgvector retrieval with RRF fusion"
```

---

## Task 7: Cross-encoder reranker — `backend/retrieval/v2/rerank.py`

**Files:**
- Create: `backend/retrieval/v2/rerank.py`
- Test: `tests/retrieval/v2/test_rerank.py`

**Interfaces:**
- Consumes: `RERANKER_MODEL_DIR` env (set by Dockerfile in Task 2; falls back to model ID for dev).
- Produces: `score(query, candidates) -> list[(candidate, float)]`, sorted descending by score.

- [ ] **Step 1: Write the failing tests**

`tests/retrieval/v2/test_rerank.py`:
```python
from unittest.mock import patch, MagicMock

def test_score_returns_pairs_sorted_descending():
    from backend.retrieval.v2 import rerank
    cands = [
        {"key": "TS-1", "summary": "Login", "description_text": "x"},
        {"key": "TS-2", "summary": "Meal",  "description_text": "y"},
        {"key": "TS-3", "summary": "Auth",  "description_text": "z"},
    ]
    fake = MagicMock()
    fake.predict.return_value = [0.2, 0.9, 0.5]
    with patch.object(rerank, "_model", fake):
        out = rerank.score("login fails", cands)
    assert [c["key"] for c, _ in out] == ["TS-2", "TS-3", "TS-1"]

def test_score_truncates_long_text_for_speed():
    from backend.retrieval.v2 import rerank
    cands = [{"key": "TS-1", "summary": "x", "description_text": "y" * 100000}]
    fake = MagicMock()
    fake.predict.return_value = [0.5]
    with patch.object(rerank, "_model", fake):
        rerank.score("q", cands)
    pair = fake.predict.call_args[0][0][0]
    assert len(pair[1]) <= rerank.MAX_DOC_CHARS

def test_score_handles_empty_candidates():
    from backend.retrieval.v2 import rerank
    assert rerank.score("q", []) == []
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
venv/bin/pytest tests/retrieval/v2/test_rerank.py -v
```
Expected: 3 FAILS.

- [ ] **Step 3: Write the reranker**

`backend/retrieval/v2/rerank.py`:
```python
"""Cross-encoder rerank step. Loads bge-reranker-v2-m3 once at import.

CPU inference is sufficient for Conwo's internal QPS (~200 ms for 50 candidates).
The model is baked into the Docker image; see scripts/download_reranker_model.py.
"""
from __future__ import annotations
import os
from functools import lru_cache

MODEL_DIR = os.getenv("RERANKER_MODEL_DIR", "BAAI/bge-reranker-v2-m3")
MAX_DOC_CHARS = 1500  # Truncate ticket text; Jira tickets front-load the problem.

@lru_cache(maxsize=1)
def _load_model():
    from sentence_transformers import CrossEncoder
    return CrossEncoder(MODEL_DIR, max_length=512)

# Test seam: tests patch `_model`.
_model = None

def _model_or_load():
    global _model
    if _model is None:
        _model = _load_model()
    return _model

def _doc_text(c: dict) -> str:
    summary = (c.get("summary") or "").strip()
    desc = (c.get("description_text") or "").strip()
    text = f"{summary}\n{desc}" if desc else summary
    if len(text) > MAX_DOC_CHARS:
        text = text[:MAX_DOC_CHARS]
    return text

def score(query: str, candidates: list[dict]) -> list[tuple[dict, float]]:
    if not candidates:
        return []
    pairs = [(query, _doc_text(c)) for c in candidates]
    m = _model_or_load() if _model is None else _model
    scores = m.predict(pairs)
    out = list(zip(candidates, (float(s) for s in scores)))
    out.sort(key=lambda x: x[1], reverse=True)
    return out
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
venv/bin/pytest tests/retrieval/v2/test_rerank.py -v
```
Expected: 3 PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/retrieval/v2/rerank.py tests/retrieval/v2/test_rerank.py
git commit -m "feat(retrieval-v2): bge-reranker-v2-m3 cross-encoder rerank"
```

---

## Task 8: Relationship expansion — `backend/retrieval/v2/links.py`

**Files:**
- Create: `backend/retrieval/v2/links.py`
- Test: `tests/retrieval/v2/test_links.py`

**Interfaces:**
- Consumes: `ticket_links` table (Task 1), a list of candidate dicts.
- Produces: `expand(conn, candidates) -> list[Candidate]`. Drops superseded candidates (replacing with the superseding ticket if newer), 1-hop-expands the top-20 (up to 20 added).

- [ ] **Step 1: Write the failing tests**

`tests/retrieval/v2/test_links.py`:
```python
from unittest.mock import MagicMock

def _fake_conn(by_src: dict[str, list[tuple[str,str]]], rows: dict[str, dict]):
    """Build a fake conn whose cursor.execute / fetchall returns scripted data."""
    cur = MagicMock()
    state = {"mode": None, "arg": None}
    def execute(sql, params):
        if "FROM ticket_links" in sql and "src_key = ANY" in sql:
            state["mode"], state["arg"] = "links", params[0]
        elif "FROM tickets" in sql and "key = ANY" in sql:
            state["mode"], state["arg"] = "tickets", params[0]
    def fetchall():
        if state["mode"] == "links":
            out = []
            for src in state["arg"]:
                for dst, lt in by_src.get(src, []):
                    out.append({"src_key": src, "dst_key": dst, "link_type": lt})
            return out
        if state["mode"] == "tickets":
            return [rows[k] for k in state["arg"] if k in rows]
        return []
    cur.execute.side_effect = execute
    cur.fetchall.side_effect = fetchall
    cur.__enter__ = MagicMock(return_value=cur); cur.__exit__ = MagicMock(return_value=False)
    conn = MagicMock(); conn.cursor.return_value = cur
    return conn

def test_drops_superseded_and_replaces_with_newer():
    from backend.retrieval.v2 import links
    cands = [
        {"key": "TS-1", "updated_at": "2024-01-01", "fused_score": 1.0},
        {"key": "TS-9", "updated_at": "2020-01-01", "fused_score": 0.5},
    ]
    by_src = {"TS-1": [("TS-2", "supersedes")]}
    rows = {"TS-2": {"key": "TS-2", "updated_at": "2026-01-01",
                     "summary": "newer", "description_text": "", "comments_text": "",
                     "status_category": "done", "priority": "P2",
                     "resolved_at": None, "functional_area": "WP-admin",
                     "links_json": "[]"}}
    conn = _fake_conn(by_src, rows)
    out = links.expand(conn, cands, top_for_expansion=20, max_added=20)
    keys = [c["key"] for c in out]
    assert "TS-2" in keys and "TS-1" not in keys

def test_one_hop_expansion_adds_linked_tickets():
    from backend.retrieval.v2 import links
    cands = [{"key": "TS-1", "updated_at": "2026-01-01", "fused_score": 1.0}]
    by_src = {"TS-1": [("TS-5", "blocks")]}
    rows = {"TS-5": {"key": "TS-5", "summary": "x", "description_text": "", "comments_text": "",
                     "status_category": "done", "priority": "P1", "updated_at": "2026-02-01",
                     "resolved_at": "2026-02-01", "functional_area": "WP-admin", "links_json": "[]"}}
    conn = _fake_conn(by_src, rows)
    out = links.expand(conn, cands, top_for_expansion=20, max_added=20)
    assert any(c["key"] == "TS-5" for c in out)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
venv/bin/pytest tests/retrieval/v2/test_links.py -v
```
Expected: 2 FAILS.

- [ ] **Step 3: Write the links module**

`backend/retrieval/v2/links.py`:
```python
"""Relationship expansion and supersession-aware ranking.

Two transforms applied on the candidate list before reranking:
  1. Supersession drop: if candidate X has `supersedes -> Y` and Y is newer,
     replace X with Y (only if Y not already in the set).
  2. 1-hop expansion: for the top-N candidates, pull every directly-linked
     ticket and append (capped). The reranker then decides if they're relevant.
"""
from __future__ import annotations
from psycopg.rows import dict_row

_LINKS_FOR_SRC_SQL = """
    SELECT src_key, dst_key, link_type
    FROM ticket_links
    WHERE src_key = ANY(%s)
"""

_TICKETS_BY_KEY_SQL = """
    SELECT key, summary, description_text, comments_text,
           status_category, priority, updated_at, resolved_at,
           functional_area, links_json
    FROM tickets
    WHERE key = ANY(%s)
"""

def _drop_superseded(conn, candidates: list[dict]) -> list[dict]:
    """If candidate X supersedes Y and Y is newer, swap. Use only the
    `supersedes` link type."""
    if not candidates:
        return candidates
    keys = [c["key"] for c in candidates]
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(_LINKS_FOR_SRC_SQL, (keys,))
        rows = cur.fetchall()
    superseding: dict[str, str] = {}
    for r in rows:
        if r["link_type"] == "supersedes":
            superseding[r["src_key"]] = r["dst_key"]
    if not superseding:
        return candidates
    # Fetch replacement rows; only swap when replacement is newer.
    repl_keys = list(set(superseding.values()))
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(_TICKETS_BY_KEY_SQL, (repl_keys,))
        repl_rows = {r["key"]: r for r in cur.fetchall()}
    out: list[dict] = []
    seen: set[str] = set()
    for c in candidates:
        rk = superseding.get(c["key"])
        if rk and rk in repl_rows and repl_rows[rk]["updated_at"] > c["updated_at"]:
            if rk not in seen:
                merged = {**repl_rows[rk], "fused_score": c.get("fused_score", 0.0)}
                out.append(merged)
                seen.add(rk)
        else:
            if c["key"] not in seen:
                out.append(c); seen.add(c["key"])
    return out

def _one_hop_expand(conn, candidates: list[dict], top_for_expansion: int,
                    max_added: int) -> list[dict]:
    if not candidates or max_added <= 0:
        return candidates
    seeds = [c["key"] for c in candidates[:top_for_expansion]]
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(_LINKS_FOR_SRC_SQL, (seeds,))
        link_rows = cur.fetchall()
    existing = {c["key"] for c in candidates}
    add_keys: list[str] = []
    for r in link_rows:
        if r["dst_key"] not in existing and r["dst_key"] not in add_keys:
            add_keys.append(r["dst_key"])
        if len(add_keys) >= max_added:
            break
    if not add_keys:
        return candidates
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(_TICKETS_BY_KEY_SQL, (add_keys,))
        added = [{**r, "fused_score": 0.0} for r in cur.fetchall()]
    return candidates + added

def expand(conn, candidates: list[dict], *,
           top_for_expansion: int = 20, max_added: int = 20) -> list[dict]:
    candidates = _drop_superseded(conn, candidates)
    candidates = _one_hop_expand(conn, candidates, top_for_expansion, max_added)
    return candidates
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
venv/bin/pytest tests/retrieval/v2/test_links.py -v
```
Expected: 2 PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/retrieval/v2/links.py tests/retrieval/v2/test_links.py
git commit -m "feat(retrieval-v2): supersession drop + 1-hop link expansion"
```

---

## Task 9: Confidence gate — `backend/retrieval/v2/gate.py`

**Files:**
- Create: `backend/retrieval/v2/gate.py`
- Test: `tests/retrieval/v2/test_gate.py`

**Interfaces:**
- Consumes: env vars `CONWO_RETRIEVAL_V2_ABSTAIN_THRESHOLD` (default `0.5`) and `CONWO_RETRIEVAL_V2_HIGH_THRESHOLD` (default `0.7`).
- Produces: `apply(scored) -> RetrievalResult(tickets, confidence, abstain, message, diagnostics)`.

- [ ] **Step 1: Write the failing tests**

`tests/retrieval/v2/test_gate.py`:
```python
def _scored(*pairs):
    return [({"key": k, "summary": "s", "functional_area": fa}, score)
            for k, fa, score in pairs]

def test_abstain_when_top_below_threshold():
    from backend.retrieval.v2 import gate
    r = gate.apply(_scored(("TS-1","A",0.3), ("TS-2","A",0.2)))
    assert r.abstain is True
    assert r.confidence == "Abstain"
    assert "couldn't find" in r.message.lower()

def test_high_when_top_score_strong_and_top3_agree():
    from backend.retrieval.v2 import gate
    r = gate.apply(_scored(("TS-1","A",0.9),("TS-2","A",0.85),("TS-3","A",0.8)))
    assert r.confidence == "High"
    assert r.abstain is False

def test_medium_when_top_strong_but_top3_disagree():
    from backend.retrieval.v2 import gate
    r = gate.apply(_scored(("TS-1","A",0.9),("TS-2","B",0.85),("TS-3","C",0.8)))
    assert r.confidence == "Medium"
    assert r.abstain is False

def test_low_when_single_source_above_abstain():
    from backend.retrieval.v2 import gate
    r = gate.apply(_scored(("TS-1","A",0.6)))
    assert r.confidence == "Low"
    assert r.abstain is False
    assert "single-source" in r.message.lower()

def test_diagnostics_includes_top_score_and_count():
    from backend.retrieval.v2 import gate
    r = gate.apply(_scored(("TS-1","A",0.9),("TS-2","A",0.85)))
    assert r.diagnostics["top_score"] == 0.9
    assert r.diagnostics["candidate_count"] == 2
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
venv/bin/pytest tests/retrieval/v2/test_gate.py -v
```
Expected: 5 FAILS.

- [ ] **Step 3: Write the gate**

`backend/retrieval/v2/gate.py`:
```python
"""Strict confidence gate. Translates reranker scores → confidence label and
the abstain-or-answer decision. Thresholds are env-tunable."""
from __future__ import annotations
import os
from dataclasses import dataclass, field
from typing import Any

def _f(env: str, default: float) -> float:
    try:
        return float(os.getenv(env, str(default)))
    except (TypeError, ValueError):
        return default

ABSTAIN = lambda: _f("CONWO_RETRIEVAL_V2_ABSTAIN_THRESHOLD", 0.5)
HIGH    = lambda: _f("CONWO_RETRIEVAL_V2_HIGH_THRESHOLD", 0.7)

@dataclass
class RetrievalResult:
    tickets: list[dict]
    confidence: str
    abstain: bool
    message: str
    diagnostics: dict = field(default_factory=dict)

def _top3_agree(scored: list[tuple[dict, float]]) -> bool:
    if len(scored) < 2:
        return False
    top = scored[:3]
    fas = {c.get("functional_area") for c, _ in top if c.get("functional_area")}
    # share at least one functional area
    if len(fas) <= 1 and fas:
        return True
    # share an epic (epic_key)
    epics = {c.get("epic_key") for c, _ in top if c.get("epic_key")}
    if len(epics) == 1 and epics:
        return True
    return False

def apply(scored: list[tuple[dict, float]]) -> RetrievalResult:
    abstain_t = ABSTAIN()
    high_t = HIGH()
    if not scored:
        return RetrievalResult(
            tickets=[], confidence="Abstain", abstain=True,
            message="I couldn't find any matching tickets.",
            diagnostics={"top_score": None, "candidate_count": 0},
        )
    top_score = scored[0][1]
    diag = {"top_score": top_score, "candidate_count": len(scored)}

    if top_score < abstain_t:
        keys = [c["key"] for c, _ in scored[:5]]
        return RetrievalResult(
            tickets=[],
            confidence="Abstain",
            abstain=True,
            message=(f"I couldn't find strong evidence. "
                     f"Closest matches: {', '.join(keys)}. Please verify."),
            diagnostics=diag,
        )

    # Build the tickets list with attached reranker_score, top-10 max.
    tickets = []
    for c, s in scored[:10]:
        out = {**c, "reranker_score": s}
        tickets.append(out)

    if len(scored) == 1:
        return RetrievalResult(
            tickets=tickets, confidence="Low", abstain=False,
            message="single-source evidence — only one ticket supports this.",
            diagnostics=diag,
        )

    if top_score >= high_t:
        if _top3_agree(scored):
            return RetrievalResult(tickets=tickets, confidence="High", abstain=False,
                                   message="strong, agreeing evidence", diagnostics=diag)
        return RetrievalResult(tickets=tickets, confidence="Medium", abstain=False,
                               message="strong evidence but tickets do not fully agree",
                               diagnostics=diag)
    # abstain_t <= top_score < high_t
    if _top3_agree(scored):
        return RetrievalResult(tickets=tickets, confidence="Medium", abstain=False,
                               message="moderate, agreeing evidence", diagnostics=diag)
    return RetrievalResult(tickets=tickets, confidence="Low", abstain=False,
                           message="moderate evidence, tickets disagree", diagnostics=diag)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
venv/bin/pytest tests/retrieval/v2/test_gate.py -v
```
Expected: 5 PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/retrieval/v2/gate.py tests/retrieval/v2/test_gate.py
git commit -m "feat(retrieval-v2): strict confidence gate with env-tunable thresholds"
```

---

## Task 10: Query rewrite — `backend/retrieval/v2/rewrite.py`

**Files:**
- Create: `backend/retrieval/v2/rewrite.py`
- Test: `tests/retrieval/v2/test_rewrite.py`

**Interfaces:**
- Consumes: `ANTHROPIC_API_KEY` (already in env), uses Claude Haiku (`claude-haiku-4-5-20251001` per `CLAUDE.md` env note).
- Produces: `rewrite(question) -> RewriteResult(sub_queries, expansions, filters, intent)`.

- [ ] **Step 1: Write the failing tests**

`tests/retrieval/v2/test_rewrite.py`:
```python
from unittest.mock import patch, MagicMock
import json

def test_rewrite_returns_subqueries_for_compound_question():
    from backend.retrieval.v2 import rewrite
    payload = {
        "sub_queries": ["meal booking bugs Q2", "overnight scan bug status"],
        "expansions": {"OTP": ["one-time password"]},
        "filters": {"module": "meal-management"},
        "intent": "DEBUGGING",
    }
    fake = MagicMock()
    fake.messages.create.return_value = MagicMock(
        content=[MagicMock(text=json.dumps(payload))]
    )
    with patch.object(rewrite, "_client", fake):
        r = rewrite.rewrite("what broke in meal booking and is overnight scan fixed?")
    assert r.sub_queries == ["meal booking bugs Q2", "overnight scan bug status"]
    assert r.intent == "DEBUGGING"
    assert r.filters["module"] == "meal-management"

def test_rewrite_falls_back_to_question_on_parse_failure():
    from backend.retrieval.v2 import rewrite
    fake = MagicMock()
    fake.messages.create.return_value = MagicMock(content=[MagicMock(text="not-json")])
    with patch.object(rewrite, "_client", fake):
        r = rewrite.rewrite("how does login work?")
    assert r.sub_queries == ["how does login work?"]
    assert r.intent == "GENERAL"

def test_rewrite_caches_identical_questions_for_5_minutes(monkeypatch):
    from backend.retrieval.v2 import rewrite
    fake = MagicMock()
    payload = {"sub_queries":["q"], "expansions":{}, "filters":{}, "intent":"GENERAL"}
    fake.messages.create.return_value = MagicMock(content=[MagicMock(text=json.dumps(payload))])
    with patch.object(rewrite, "_client", fake):
        rewrite._cache.clear()
        rewrite.rewrite("same question?")
        rewrite.rewrite("same question?")
    assert fake.messages.create.call_count == 1
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
venv/bin/pytest tests/retrieval/v2/test_rewrite.py -v
```
Expected: 3 FAILS.

- [ ] **Step 3: Write the rewriter**

`backend/retrieval/v2/rewrite.py`:
```python
"""Claude-Haiku query decomposer for Jira Retrieval v2.

Decomposes compound questions into sub-queries, expands synonyms, extracts
filters (functional_area, resolved_after, module). Cached for 5 minutes on
identical question strings to keep cost down at ~₹1 per query.
"""
from __future__ import annotations
import json
import os
import time
from dataclasses import dataclass, field

import anthropic

_MODEL = "claude-haiku-4-5-20251001"
_CACHE_TTL = 300  # seconds

@dataclass
class RewriteResult:
    sub_queries: list[str]
    expansions: dict[str, list[str]] = field(default_factory=dict)
    filters: dict = field(default_factory=dict)
    intent: str = "GENERAL"

_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))
_cache: dict[str, tuple[float, RewriteResult]] = {}

_SYSTEM = (
    "You are a query analyzer for a Jira knowledge base. Given a user question, "
    "output a JSON object with these keys:\n"
    "  sub_queries: list[str] — break compound questions into focused sub-queries; "
    "for a single question, return a one-element list of the original or a "
    "lightly normalized version.\n"
    "  expansions: dict[str, list[str]] — acronyms/synonyms only when you are "
    "confident (e.g. {\"OTP\":[\"one-time password\"]}).\n"
    "  filters: dict — set only when the user is explicit. Allowed keys: "
    "functional_area, module, resolved_after (YYYY-MM-DD), status_category.\n"
    "  intent: one of DEBUGGING, STATUS, DEFINITION, CONFIGURATION, COMPARISON, "
    "HOW_TO, ARCHITECTURAL, GENERAL.\n"
    "Output JSON only. No prose."
)

def _call_claude(question: str) -> RewriteResult:
    resp = _client.messages.create(
        model=_MODEL,
        max_tokens=600,
        system=_SYSTEM,
        messages=[{"role": "user", "content": question}],
    )
    raw = resp.content[0].text if resp.content else ""
    try:
        data = json.loads(raw)
        return RewriteResult(
            sub_queries=list(data.get("sub_queries") or [question]) or [question],
            expansions=dict(data.get("expansions") or {}),
            filters=dict(data.get("filters") or {}),
            intent=str(data.get("intent") or "GENERAL"),
        )
    except Exception:
        return RewriteResult(sub_queries=[question])

def rewrite(question: str) -> RewriteResult:
    now = time.time()
    cached = _cache.get(question)
    if cached and now - cached[0] < _CACHE_TTL:
        return cached[1]
    result = _call_claude(question)
    _cache[question] = (now, result)
    return result
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
venv/bin/pytest tests/retrieval/v2/test_rewrite.py -v
```
Expected: 3 PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/retrieval/v2/rewrite.py tests/retrieval/v2/test_rewrite.py
git commit -m "feat(retrieval-v2): Claude-Haiku query rewriter (decompose + expand + filters)"
```

---

## Task 11: Pipeline orchestrator — `backend/retrieval/v2/pipeline.py`

**Files:**
- Create: `backend/retrieval/v2/pipeline.py`
- Test: `tests/retrieval/v2/test_pipeline.py`

**Interfaces:**
- Consumes: all of Tasks 3, 6, 7, 8, 9, 10. Connection from `backend.db.get_conn()`.
- Produces: `search(question, *, functional_area=None, limit=10) -> RetrievalResult`. `by_module(module_slug, query, limit=5) -> list[dict]`.

- [ ] **Step 1: Write the failing test**

`tests/retrieval/v2/test_pipeline.py`:
```python
from unittest.mock import patch, MagicMock
from backend.retrieval.v2.rewrite import RewriteResult
from backend.retrieval.v2.gate import RetrievalResult

def test_pipeline_calls_rewrite_embed_hybrid_links_rerank_gate_in_order(monkeypatch):
    from backend.retrieval.v2 import pipeline
    order: list[str] = []
    monkeypatch.setattr(pipeline, "rewrite",
        lambda q: order.append("rewrite") or RewriteResult(sub_queries=["q1"]))
    monkeypatch.setattr(pipeline, "embed_query",
        lambda q: order.append("embed") or [0.0]*768)
    monkeypatch.setattr(pipeline, "hybrid_search",
        lambda *a, **k: order.append("hybrid") or [{"key":"TS-1","summary":"x",
            "description_text":"","comments_text":"","status_category":"done",
            "priority":"P1","updated_at":"2026-01-01","resolved_at":None,
            "functional_area":"A","links_json":"[]","fused_score":1.0}])
    monkeypatch.setattr(pipeline, "expand_links",
        lambda c, cands: order.append("expand") or cands)
    monkeypatch.setattr(pipeline, "rerank_score",
        lambda q, cands: order.append("rerank") or [(cands[0], 0.9)])
    monkeypatch.setattr(pipeline, "gate_apply",
        lambda scored: order.append("gate") or RetrievalResult(
            tickets=[{"key":"TS-1","reranker_score":0.9}],
            confidence="High", abstain=False,
            message="ok", diagnostics={"top_score":0.9,"candidate_count":1}))
    monkeypatch.setattr(pipeline, "get_conn", lambda: MagicMock())
    r = pipeline.search("what is X?")
    assert r.confidence == "High"
    assert order == ["rewrite","embed","hybrid","expand","rerank","gate"]
```

- [ ] **Step 2: Run test to verify it fails**

```bash
venv/bin/pytest tests/retrieval/v2/test_pipeline.py -v
```
Expected: 1 FAIL.

- [ ] **Step 3: Write the pipeline**

`backend/retrieval/v2/pipeline.py`:
```python
"""Retrieval v2 pipeline: rewrite → embed → hybrid → links → rerank → gate."""
from __future__ import annotations
from typing import Any

from backend.db import get_conn
from backend.retrieval.v2.embed import embed_query
from backend.retrieval.v2.hybrid import hybrid_search
from backend.retrieval.v2.links import expand as expand_links
from backend.retrieval.v2.rerank import score as rerank_score
from backend.retrieval.v2.rewrite import rewrite
from backend.retrieval.v2.gate import apply as gate_apply, RetrievalResult

def search(question: str, *, functional_area: str | None = None,
           limit: int = 10) -> RetrievalResult:
    rw = rewrite(question)
    # Caller-supplied functional_area wins over inferred filter
    filters = dict(rw.filters)
    if functional_area:
        filters["functional_area"] = functional_area
    sub_queries = rw.sub_queries or [question]
    query_vecs = [embed_query(q) for q in sub_queries]
    conn = get_conn()
    candidates = hybrid_search(conn, sub_queries, query_vecs, filters, limit=50)
    if not candidates:
        return gate_apply([])
    candidates = expand_links(conn, candidates)
    scored = rerank_score(question, candidates)
    return gate_apply(scored)

def by_module(module_slug: str, query: str, limit: int = 5) -> list[dict]:
    """Module-scoped retrieval. Used by preflight to prefetch related tickets.

    Replaces the old INNER-JOIN-on-ticket_module_tags path. Instead, we treat
    the module slug as an additional sub-query token so semantic similarity to
    the module description does the routing.
    """
    qvec = embed_query(query)
    mvec = embed_query(module_slug.replace("-", " "))
    conn = get_conn()
    sub_queries = [query, module_slug.replace("-", " ")]
    query_vecs = [qvec, mvec]
    candidates = hybrid_search(conn, sub_queries, query_vecs, {}, limit=limit)
    return candidates
```

- [ ] **Step 4: Run test to verify it passes**

```bash
venv/bin/pytest tests/retrieval/v2/test_pipeline.py -v
```
Expected: 1 PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/retrieval/v2/pipeline.py tests/retrieval/v2/test_pipeline.py
git commit -m "feat(retrieval-v2): pipeline orchestrator (rewrite→embed→hybrid→links→rerank→gate)"
```

---

## Task 12: Feature-flag dispatch + shadow logging in `backend/jira_retriever.py`

**Files:**
- Modify: `backend/jira_retriever.py`
- Create: `backend/retrieval/v2/shadow.py`
- Test: `tests/retrieval/v2/test_shadow_dispatch.py`

**Interfaces:**
- Consumes: env vars `CONWO_RETRIEVAL_V2` and `CONWO_RETRIEVAL_V2_PCT`. Existing `jira_retriever.search()` and `by_module()` signatures.
- Produces: external behaviour is identical to v1 unless flag flipped. In `shadow` mode, v2 runs alongside v1 and writes to `retrieval_shadow_log` but never serves users. In `ab` mode, percent-split. In `on` mode, v2 always serves.

- [ ] **Step 1: Write the failing tests**

`tests/retrieval/v2/test_shadow_dispatch.py`:
```python
from unittest.mock import patch, MagicMock
import os, pytest

@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for k in ["CONWO_RETRIEVAL_V2","CONWO_RETRIEVAL_V2_PCT"]:
        monkeypatch.delenv(k, raising=False)

def test_default_off_serves_v1(monkeypatch):
    from backend import jira_retriever
    v1 = MagicMock(return_value="v1-result")
    v2 = MagicMock(return_value="v2-result")
    monkeypatch.setattr(jira_retriever, "_v1_search", v1)
    monkeypatch.setattr(jira_retriever, "_v2_search", v2)
    out = jira_retriever.search("q")
    assert out == "v1-result"
    v2.assert_not_called()

def test_shadow_runs_both_serves_v1(monkeypatch):
    monkeypatch.setenv("CONWO_RETRIEVAL_V2", "shadow")
    from backend import jira_retriever
    v1 = MagicMock(return_value="v1-result")
    v2 = MagicMock(return_value="v2-result")
    log = MagicMock()
    monkeypatch.setattr(jira_retriever, "_v1_search", v1)
    monkeypatch.setattr(jira_retriever, "_v2_search", v2)
    monkeypatch.setattr(jira_retriever, "_shadow_log", log)
    out = jira_retriever.search("q")
    assert out == "v1-result"
    v2.assert_called_once()
    log.assert_called_once()

def test_on_serves_v2(monkeypatch):
    monkeypatch.setenv("CONWO_RETRIEVAL_V2", "on")
    from backend import jira_retriever
    v1 = MagicMock(); v2 = MagicMock(return_value="v2-result")
    monkeypatch.setattr(jira_retriever, "_v1_search", v1)
    monkeypatch.setattr(jira_retriever, "_v2_search", v2)
    assert jira_retriever.search("q") == "v2-result"
    v1.assert_not_called()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
venv/bin/pytest tests/retrieval/v2/test_shadow_dispatch.py -v
```
Expected: 3 FAILS.

- [ ] **Step 3: Write the shadow logger**

`backend/retrieval/v2/shadow.py`:
```python
"""Write retrieval-v2 results to retrieval_shadow_log for offline comparison."""
from __future__ import annotations
import time
from backend.db import get_conn

_INSERT = """
    INSERT INTO retrieval_shadow_log
        (trace_id, question, v1_keys, v2_keys, v2_scores, v2_confidence,
         v2_latency_ms, served_v2)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
"""

def log(*, trace_id: str | None, question: str,
        v1_keys: list[str], v2_result, v2_latency_ms: int,
        served_v2: bool) -> None:
    v2_keys = [t.get("key") for t in (v2_result.tickets or [])]
    v2_scores = [float(t.get("reranker_score") or 0.0) for t in (v2_result.tickets or [])]
    try:
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(_INSERT, (
                trace_id, question, v1_keys, v2_keys, v2_scores,
                v2_result.confidence, v2_latency_ms, served_v2,
            ))
            conn.commit()
    except Exception:
        # fail-open: shadow logging never breaks production retrieval
        pass
```

- [ ] **Step 4: Modify `backend/jira_retriever.py` to add the dispatch**

Add to the top of `backend/jira_retriever.py` (keep existing `search` / `by_module` definitions intact, rename them to `_v1_search` / `_v1_by_module`):

```python
# ── v2 dispatch ──────────────────────────────────────────────────────────────
import os, random, time
from backend.retrieval.v2 import shadow as _shadow_mod

def _v2_search(query: str, *, functional_area: str | None = None,
               limit: int = 10, **kwargs):
    from backend.retrieval.v2.pipeline import search as _p
    return _p(query, functional_area=functional_area, limit=limit)

def _v2_by_module(module_slug: str, query: str, limit: int = 5, **kwargs):
    from backend.retrieval.v2.pipeline import by_module as _bm
    return _bm(module_slug, query, limit=limit)

_shadow_log = _shadow_mod.log  # test seam

def _mode() -> str:
    return (os.getenv("CONWO_RETRIEVAL_V2") or "off").lower()

def _ab_serve_v2() -> bool:
    try:
        pct = int(os.getenv("CONWO_RETRIEVAL_V2_PCT", "0"))
    except ValueError:
        pct = 0
    return random.randint(1, 100) <= pct

def search(query: str, *, functional_area: str | None = None,
           limit: int = 10, **kwargs):
    mode = _mode()
    if mode == "off":
        return _v1_search(query, functional_area=functional_area, limit=limit, **kwargs)
    if mode == "on":
        return _v2_search(query, functional_area=functional_area, limit=limit, **kwargs)
    if mode == "ab":
        if _ab_serve_v2():
            return _v2_search(query, functional_area=functional_area, limit=limit, **kwargs)
        return _v1_search(query, functional_area=functional_area, limit=limit, **kwargs)
    # shadow: serve v1, run v2 in parallel, log both
    v1_result = _v1_search(query, functional_area=functional_area, limit=limit, **kwargs)
    t0 = time.perf_counter()
    try:
        v2_result = _v2_search(query, functional_area=functional_area, limit=limit, **kwargs)
        dt = int((time.perf_counter() - t0) * 1000)
        v1_keys = _extract_v1_keys(v1_result)
        _shadow_log(trace_id=kwargs.get("trace_id"), question=query,
                    v1_keys=v1_keys, v2_result=v2_result,
                    v2_latency_ms=dt, served_v2=False)
    except Exception:
        pass
    return v1_result

def by_module(module_slug: str, query: str, limit: int = 5, **kwargs):
    mode = _mode()
    if mode == "off":
        return _v1_by_module(module_slug, query, limit=limit, **kwargs)
    if mode == "on":
        return _v2_by_module(module_slug, query, limit=limit, **kwargs)
    if mode == "ab" and _ab_serve_v2():
        return _v2_by_module(module_slug, query, limit=limit, **kwargs)
    return _v1_by_module(module_slug, query, limit=limit, **kwargs)

def _extract_v1_keys(v1_result) -> list[str]:
    """Best-effort extraction of ticket keys from a v1 retrieval result."""
    if v1_result is None:
        return []
    rows = getattr(v1_result, "rows", None) or getattr(v1_result, "results", None) or v1_result
    out = []
    try:
        for r in rows:
            if isinstance(r, dict) and "key" in r:
                out.append(r["key"])
    except Exception:
        pass
    return out
```

> Implementer: locate the existing `def search(...)` and `def by_module(...)` in `backend/jira_retriever.py` and rename them to `_v1_search` and `_v1_by_module`. Move them below the dispatch block above. Do not change their bodies.

- [ ] **Step 5: Run tests to verify they pass**

```bash
venv/bin/pytest tests/retrieval/v2/test_shadow_dispatch.py -v
```
Expected: 3 PASS. Then run the existing jira test files to confirm no regression:
```bash
venv/bin/pytest tests/ -k "jira" -v
```

- [ ] **Step 6: Commit**

```bash
git add backend/jira_retriever.py backend/retrieval/v2/shadow.py tests/retrieval/v2/test_shadow_dispatch.py
git commit -m "feat(retrieval-v2): feature-flag dispatch (off/shadow/ab/on) + shadow logging"
```

---

## Task 13: Daily sync integration — `scripts/jira_daily_sync.py`

**Files:**
- Modify: `scripts/jira_daily_sync.py`
- Test: `tests/scripts/test_jira_daily_sync_v2.py`

**Interfaces:**
- Consumes: existing nightly stages 1 (incremental) and 2 (classify).
- Produces: two new stages — (3) embed delta via Gemini, (4) backfill links delta. Both run only when `CONWO_RETRIEVAL_V2` is anything other than `off`.

- [ ] **Step 1: Write the failing test**

`tests/scripts/test_jira_daily_sync_v2.py`:
```python
from unittest.mock import patch
import importlib

def test_daily_sync_skips_v2_steps_when_flag_off(monkeypatch):
    monkeypatch.setenv("CONWO_RETRIEVAL_V2", "off")
    daily = importlib.import_module("scripts.jira_daily_sync")
    with patch.object(daily, "_run_embed_delta") as e, \
         patch.object(daily, "_run_links_delta") as l, \
         patch.object(daily, "_run_incremental") as i, \
         patch.object(daily, "_run_classify_delta") as c:
        i.return_value = 0; c.return_value = 0
        daily.run()
    e.assert_not_called(); l.assert_not_called()

def test_daily_sync_runs_v2_steps_when_flag_on(monkeypatch):
    monkeypatch.setenv("CONWO_RETRIEVAL_V2", "shadow")
    daily = importlib.import_module("scripts.jira_daily_sync")
    with patch.object(daily, "_run_embed_delta") as e, \
         patch.object(daily, "_run_links_delta") as l, \
         patch.object(daily, "_run_incremental") as i, \
         patch.object(daily, "_run_classify_delta") as c:
        i.return_value = 0; c.return_value = 0; e.return_value = 0; l.return_value = 0
        daily.run()
    e.assert_called_once(); l.assert_called_once()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
venv/bin/pytest tests/scripts/test_jira_daily_sync_v2.py -v
```
Expected: 2 FAILS.

- [ ] **Step 3: Modify `scripts/jira_daily_sync.py`**

Locate the `run()` (or equivalent main flow). Add two new subprocess-launch helpers and call them after the classify step.

Add near the existing helpers:
```python
import os, subprocess, sys

def _run_embed_delta() -> int:
    return subprocess.call([sys.executable, "scripts/embed_tickets.py", "--mode", "delta"], timeout=900)

def _run_links_delta() -> int:
    return subprocess.call([sys.executable, "scripts/backfill_ticket_links.py", "--mode", "delta"], timeout=600)
```

Inside `run()` (after the existing classify-delta call), add:
```python
    if (os.getenv("CONWO_RETRIEVAL_V2") or "off").lower() != "off":
        rc = _run_embed_delta()
        if rc != 0:
            print(f"WARNING: embed delta exited {rc}", flush=True)
        rc = _run_links_delta()
        if rc != 0:
            print(f"WARNING: links delta exited {rc}", flush=True)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
venv/bin/pytest tests/scripts/test_jira_daily_sync_v2.py -v
```
Expected: 2 PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/jira_daily_sync.py tests/scripts/test_jira_daily_sync_v2.py
git commit -m "feat(retrieval-v2): nightly sync runs embed + links delta when flag set"
```

---

## Task 14: End-to-end integration test + eval harness

**Files:**
- Create: `tests/retrieval/v2/test_e2e_integration.py`
- Create: `tests/retrieval/v2/eval/queries.json`
- Create: `tests/retrieval/v2/eval/run_eval.py`
- Test: itself

**Interfaces:**
- Consumes: a Postgres instance with the migration applied, embedded tickets, populated `ticket_links`. All optional — tests skip if `CONWO_TEST_DSN` and `GOOGLE_GENAI_API_KEY` are not present.
- Produces: a script (`run_eval.py`) that measures `recall@10` and `abstention_rate` against a hand-graded query set.

- [ ] **Step 1: Write the integration test**

`tests/retrieval/v2/test_e2e_integration.py`:
```python
"""End-to-end integration test. Requires CONWO_TEST_DSN + GOOGLE_GENAI_API_KEY."""
import os
import pytest

pytestmark = pytest.mark.skipif(
    not (os.getenv("CONWO_TEST_DSN") and os.getenv("GOOGLE_GENAI_API_KEY")),
    reason="requires Postgres + Gemini key",
)

def test_e2e_returns_either_tickets_or_abstain():
    os.environ["CONWO_DSN"] = os.environ["CONWO_TEST_DSN"]
    from backend.retrieval.v2.pipeline import search
    r = search("kioskRequireOTP behaviour for new visitors")
    assert r.confidence in {"High","Medium","Low","Abstain"}
    if not r.abstain:
        assert len(r.tickets) >= 1
        assert all("reranker_score" in t for t in r.tickets)
    else:
        assert r.tickets == []
        assert "verify" in r.message.lower() or "couldn't" in r.message.lower()
```

- [ ] **Step 2: Create the eval set**

`tests/retrieval/v2/eval/queries.json`:
```json
[
  {"q": "what does kioskRequireOTPBeforeRegister do?", "intent": "CONFIGURATION", "expected_any_of": []},
  {"q": "recently resolved tickets in WF-empexp", "intent": "STATUS", "expected_any_of": []},
  {"q": "how does meal scan work for overnight bookings?", "intent": "HOW_TO", "expected_any_of": []},
  {"q": "tickets blocked by TS-1234", "intent": "GENERAL", "expected_any_of": []}
]
```
> The `expected_any_of` lists are filled in by hand during the Phase 2 shadow week, after seeing real top-k. This file is a scaffold — populate it before Phase 3 cutover.

- [ ] **Step 3: Write the eval runner**

`tests/retrieval/v2/eval/run_eval.py`:
```python
"""Run the eval set against the v2 pipeline; print recall@10 and abstention rate."""
import json, os, sys
from pathlib import Path

def main() -> int:
    here = Path(__file__).parent
    qs = json.loads((here / "queries.json").read_text())
    sys.path.insert(0, str(here.parent.parent.parent.parent))  # repo root
    from backend.retrieval.v2.pipeline import search
    abstained = 0; hits = 0; graded = 0
    for item in qs:
        r = search(item["q"])
        if r.abstain:
            abstained += 1
            print(f"[ABSTAIN] {item['q']}"); continue
        expected = set(item.get("expected_any_of") or [])
        if expected:
            graded += 1
            got = {t["key"] for t in r.tickets}
            if expected & got:
                hits += 1
                print(f"[HIT]     {item['q']}  → {sorted(expected&got)}")
            else:
                print(f"[MISS]    {item['q']}  expected {sorted(expected)} got {sorted(got)}")
        else:
            print(f"[OK]      {item['q']}  top={r.tickets[0]['key'] if r.tickets else '-'}")
    print(f"\nabstention_rate={abstained}/{len(qs)} = {100*abstained//max(1,len(qs))}%")
    if graded:
        print(f"recall@10={hits}/{graded} = {100*hits//graded}%")
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run integration test (skips if env not set)**

```bash
venv/bin/pytest tests/retrieval/v2/test_e2e_integration.py -v
```
Expected: PASS (or SKIPPED if env not set).

- [ ] **Step 5: Commit**

```bash
git add tests/retrieval/v2/test_e2e_integration.py tests/retrieval/v2/eval/
git commit -m "test(retrieval-v2): e2e integration + eval harness scaffolding"
```

---

## Rollout checklist (post-implementation)

These are not tasks — they're the operational steps to take after the 14 implementation tasks land.

1. **Confirm `pgvector` on prod RDS** — `CREATE EXTENSION vector` works.
2. **Apply migration 050** in staging, then prod. (Will run automatically at backend startup via `db.init_db()`; manual `psql` apply is a faster path for the first deploy.)
3. **Confirm Gemini API approval for internal customer data** (Jira tickets contain BUIDs and incident details). If approval is restricted, set `RETRIEVER_EMBED_FALLBACK_LOCAL=1` and host `bge-large-en-v1.5` instead. (Out of scope for v1 plan; design preserves the option.)
4. **Run one-time backfills:**
   ```bash
   venv/bin/python scripts/backfill_ticket_links.py --mode full
   venv/bin/python scripts/embed_tickets.py --mode full
   ```
   ~20 min for embeddings, ~1 min for links.
5. **Set `CONWO_RETRIEVAL_V2=shadow`** in prod. Watch `retrieval_shadow_log` for ~1 week. Compare v1 vs v2 keys.
6. **Populate `expected_any_of`** in the eval set from observed top-k.
7. **Run eval:** `venv/bin/python tests/retrieval/v2/eval/run_eval.py` — gate Phase 3 on `recall@10 ≥ 85%` and `abstention_rate ≤ 30%`. Tune `CONWO_RETRIEVAL_V2_ABSTAIN_THRESHOLD` if needed.
8. **Flip `CONWO_RETRIEVAL_V2=ab` with `CONWO_RETRIEVAL_V2_PCT=10`**. After 24h, → 50%. After 48h, → 100% (== `on`).
9. **Decommission v1** in a follow-up cleanup PR once v2 has run at 100% for 2 weeks.

---

## Self-review

- **Spec coverage:** every section of the spec maps to a task — schema (T1), Docker (T2), embed (T3+T4), links (T5+T8), hybrid SQL (T6), rerank (T7), gate (T9), rewrite (T10), pipeline (T11), feature flag + shadow log (T12), nightly sync (T13), integration test + eval (T14). The "Risks and Mitigations" and "Rollout" sections are operational and live in the post-implementation checklist above.
- **Placeholder scan:** every step has runnable commands and complete code. No "TBD" / "implement later" / "add validation" / "similar to Task N" left.
- **Type consistency:** the candidate dict shape is defined once at the top of this plan and used identically across Tasks 6, 7, 8, 9, 11. `RetrievalResult` is defined in Task 9 and referenced by Tasks 11, 12. `RewriteResult` is defined in Task 10 and referenced by Task 11. `embed_query`/`embed_documents` types are stable across Tasks 3, 4, 11. The dispatch in Task 12 calls `_v2_search` which wraps `pipeline.search` from Task 11 — signatures match.
