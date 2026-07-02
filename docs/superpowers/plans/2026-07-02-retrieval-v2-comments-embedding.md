# Retrieval-V2 Comments-Aware Embedding Implementation Plan (Phase 2 / spec §6)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Comment content participates in both dense retrieval (via a second `comments_embedding` vector column, searched as a third RRF source) and reranker scoring (via a fixed-budget `_doc_text` that always includes trailing comments). Behind an independent feature flag so code, migration, backfill, and activation are decoupled.

**Architecture:** New Postgres column + HNSW index for `comments_embedding`. `embed_tickets.py` gains a `compose_comments_text` helper and a `--comments-only` backfill mode. `hybrid.py` extends its SQL template with a conditional `dense_c` CTE gated on `CONWO_RETRIEVAL_V2_COMMENTS ∈ {off, on}` — when off, emitted SQL is byte-identical to Phase 1. `rerank.py._doc_text` becomes a fixed 200/500/300-char budget (summary/description/comments), ships alongside Phase 2 code but is unconditional.

**Tech Stack:** Postgres + pgvector (HNSW index), psycopg 3, Gemini `gemini-embedding-001` via existing `backend.retrieval.v2.embed.embed_documents`, MiniLM cross-encoder via existing `backend.retrieval.v2.rerank`. No new dependencies.

## Global Constraints

- Assumes Phase 1 (`2026-07-02-retrieval-v2-timeline-weighting.md`) is merged and shipped. Phase 2 imports do not depend on Phase 1 code, but the rollout order matters — Phase 1 first, verify shadow signal, then Phase 2.
- Migration 151 must be idempotent (`IF NOT EXISTS`).
- Feature flag `CONWO_RETRIEVAL_V2_COMMENTS` domain: `"off" | "on"`, default `"off"`.
- `_doc_text` change is **unconditional** — ships alongside Phase 2 code, not gated on the subflag. Deliberate: `_doc_text` doesn't touch the embedding column, and letting the reranker see comment text is a free lift.
- Bucket string values remain `"latest" | "historical" | "stale_open"` (unchanged from Phase 1).
- CLAUDE.md §1 rule: no `.py` edits while backend runs with `--reload`. Kill any local dev server before starting.
- Backfill script must be resumable — re-running after Gemini quota trip or interruption picks up cleanly.

---

### Task 1: Migration 151 — comments_embedding column + HNSW index

**Files:**
- Create: `migrations/postgres/151_comments_embedding.sql`

**Interfaces:**
- Consumes: `tickets` table (exists), `vector` extension (already enabled by migration 150).
- Produces: `tickets.comments_embedding vector(768)` column + `idx_tickets_comments_embedding` HNSW index. Used by Tasks 2 and 4.

- [ ] **Step 1: Create the migration file**

Create `migrations/postgres/151_comments_embedding.sql`:

```sql
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
```

(HNSW parameters match migration 150's existing `idx_tickets_embedding` for consistency.)

- [ ] **Step 2: Verify idempotency locally against a test DB**

Run against a local Postgres (or the dev DSN):

```bash
psql "$CONWO_DSN" -f migrations/postgres/151_comments_embedding.sql
psql "$CONWO_DSN" -f migrations/postgres/151_comments_embedding.sql   # second run — must succeed
psql "$CONWO_DSN" -c "\d tickets" | grep comments_embedding
```

Expected: both migration runs succeed silently; the `\d` output shows `comments_embedding` column as `vector`.

- [ ] **Step 3: Commit**

```bash
git add migrations/postgres/151_comments_embedding.sql
git commit -m "feat(retrieval-v2): migration 151 — comments_embedding column + HNSW (spec §6.1)

Adds tickets.comments_embedding vector(768) plus HNSW index with m=16,
ef_construction=64 (matching migration 150's embedding index). Idempotent;
safe to run before Phase 2 code deploy. Column stays NULL until
scripts/embed_tickets.py --comments-only is run."
```

---

### Task 2: Extend embed_tickets.py — compose_comments_text + dual-embed + --comments-only

**Files:**
- Modify: `scripts/embed_tickets.py`
- Test: `tests/scripts/test_embed_tickets.py` (create — see Step 1)

**Interfaces:**
- Consumes: `backend.retrieval.v2.embed.embed_documents` (existing), `tickets.comments_text` column, `tickets.comments_embedding` column (from Task 1).
- Produces:
  - `compose_comments_text(row: dict) -> str` — truncated comments text or "".
  - New CLI flag `--comments-only`: backfill mode that populates only `comments_embedding`, preserves existing `embedding` values via `COALESCE`.

- [ ] **Step 1: Create the failing test file**

First verify the test directory. Run:

```bash
ls tests/scripts/ 2>/dev/null || mkdir -p tests/scripts
[ -f tests/scripts/__init__.py ] || touch tests/scripts/__init__.py
```

Create `tests/scripts/test_embed_tickets.py`:

```python
"""Unit tests for scripts/embed_tickets.py helpers.

DB-touching behavior is covered by the opt-in PG fixture in
tests/retrieval/v2/conftest.py; here we only test pure functions and
CLI argument parsing.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


def test_compose_comments_text_returns_empty_when_no_comments():
    from scripts.embed_tickets import compose_comments_text
    assert compose_comments_text({"comments_text": None}) == ""
    assert compose_comments_text({"comments_text": ""}) == ""
    assert compose_comments_text({}) == ""


def test_compose_comments_text_returns_stripped_text():
    from scripts.embed_tickets import compose_comments_text
    assert compose_comments_text({"comments_text": "  hello  "}) == "hello"


def test_compose_comments_text_truncates_at_max():
    from scripts.embed_tickets import compose_comments_text, MAX_COMMENTS_CHARS
    long = "x" * (MAX_COMMENTS_CHARS + 100)
    out = compose_comments_text({"comments_text": long})
    assert len(out) == MAX_COMMENTS_CHARS


def test_argparse_accepts_comments_only_flag():
    """CLI flag --comments-only must parse successfully."""
    import argparse
    from scripts.embed_tickets import _build_argparser
    ap = _build_argparser()
    args = ap.parse_args(["--mode", "full", "--comments-only"])
    assert args.comments_only is True

    args = ap.parse_args(["--mode", "full"])
    assert args.comments_only is False
```

- [ ] **Step 2: Run tests, verify all 4 fail**

Run: `venv/bin/pytest tests/scripts/test_embed_tickets.py -v`
Expected: `ImportError: cannot import name 'compose_comments_text'` / `MAX_COMMENTS_CHARS` / `_build_argparser` from `scripts.embed_tickets`.

- [ ] **Step 3: Extend scripts/embed_tickets.py**

Edit `scripts/embed_tickets.py`. Apply these changes:

**A. Add constant near the top (after `MAX_TEXT_CHARS = 8000`, around line 20):**

```python
MAX_COMMENTS_CHARS = 8000  # Larger than MAX_TEXT_CHARS? No, same — comments already
                           # carry the answer for debugging queries; no need to bias larger.
```

**B. Extend the SELECT queries to include `comments_text` (replace lines 22–33):**

```python
SELECT_FULL = """
    SELECT key, summary, description_text, comments_text
    FROM tickets
    ORDER BY updated_at DESC
"""

SELECT_DELTA = """
    SELECT key, summary, description_text, comments_text
    FROM tickets
    WHERE embedded_at IS NULL OR updated_at > embedded_at
    ORDER BY updated_at DESC
"""
```

**C. Replace `UPDATE_ROW` with a `COALESCE`-based version (replace lines 35–39):**

```python
UPDATE_ROW = """
    UPDATE tickets
    SET embedding          = COALESCE(%(desc_vec)s::vector, embedding),
        comments_embedding = COALESCE(%(comm_vec)s::vector, comments_embedding),
        embedded_at        = now()
    WHERE key = %(key)s
"""
```

**D. Add `compose_comments_text` after `compose_text` (after line 47):**

```python
def compose_comments_text(row: dict) -> str:
    """Return trimmed comments_text for the second embedding, or '' if empty."""
    text = (row.get("comments_text") or "").strip()
    if len(text) > MAX_COMMENTS_CHARS:
        text = text[:MAX_COMMENTS_CHARS]
    return text
```

**E. Refactor `run()` for dual-embed + `--comments-only` (replace lines 59–78):**

```python
def run(dsn: str, mode: str, comments_only: bool = False) -> int:
    sql = SELECT_FULL if mode == "full" else SELECT_DELTA
    total = 0
    t0 = time.perf_counter()
    with psycopg.connect(dsn) as conn:
        register_vector(conn)
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql)
            for batch in iter_batches(cur, BATCH):
                # Description embeddings (unless --comments-only).
                desc_vecs: list = [None] * len(batch)
                if not comments_only:
                    desc_texts = [compose_text(r) for r in batch]
                    desc_vecs = embed_documents(desc_texts)

                # Comment embeddings — separate batch; skip rows with empty comments.
                comm_texts_indexed = [(i, compose_comments_text(r))
                                      for i, r in enumerate(batch)]
                non_empty = [(i, t) for i, t in comm_texts_indexed if t]
                comm_vecs: list = [None] * len(batch)
                if non_empty:
                    embedded = embed_documents([t for _, t in non_empty])
                    for (i, _), v in zip(non_empty, embedded):
                        comm_vecs[i] = v

                with conn.cursor() as upd:
                    for r, dv, cv in zip(batch, desc_vecs, comm_vecs):
                        upd.execute(UPDATE_ROW, {
                            "key": r["key"],
                            "desc_vec": dv,
                            "comm_vec": cv,
                        })
                conn.commit()
                total += len(batch)
                dt = time.perf_counter() - t0
                print(f"  embedded {total} rows ({total/dt:.1f}/s)", flush=True)
    print(f"done: {total} rows embedded.", flush=True)
    return 0
```

**F. Extract argparser into a testable helper (replace `main()` at lines 104–117):**

```python
def _build_argparser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["full", "delta"], required=True)
    ap.add_argument("--dsn", default=None)
    ap.add_argument("--comments-only", action="store_true",
                    help="Populate only comments_embedding; leave embedding untouched. "
                         "Used for the post-migration-151 backfill of existing tickets.")
    return ap


def main() -> int:
    args = _build_argparser().parse_args()
    dsn = _resolve_dsn(args.dsn)
    if not dsn:
        print(
            "DSN required. Set one of: --dsn, CONWO_DSN, DATABASE_URL, or "
            "CONWO_SECRET_ID (for AWS Secrets Manager auto-load).",
            file=sys.stderr,
        )
        return 2
    return run(dsn, args.mode, comments_only=args.comments_only)
```

- [ ] **Step 4: Run tests, verify all 4 pass**

Run: `venv/bin/pytest tests/scripts/test_embed_tickets.py -v`
Expected: 4 passed.

- [ ] **Step 5: Manual smoke test — --help output**

Run: `venv/bin/python scripts/embed_tickets.py --help`
Expected output includes:
```
  --mode {full,delta}
  --dsn DSN
  --comments-only       Populate only comments_embedding; ...
```

- [ ] **Step 6: Commit**

```bash
git add scripts/embed_tickets.py tests/scripts/test_embed_tickets.py tests/scripts/__init__.py
git commit -m "feat(retrieval-v2): embed_tickets dual-embed + --comments-only (spec §6.2)

- compose_comments_text() with MAX_COMMENTS_CHARS trim.
- SELECT_FULL/SELECT_DELTA now include comments_text.
- UPDATE_ROW uses COALESCE so --comments-only backfill doesn't clobber
  existing embedding values.
- --comments-only CLI flag for the post-migration one-shot backfill."
```

---

### Task 3: rerank.py — fixed-budget _doc_text with comments

**Files:**
- Modify: `backend/retrieval/v2/rerank.py:56-62`
- Test: `tests/retrieval/v2/test_rerank.py` (extend)

**Interfaces:**
- Consumes: candidate dicts with `summary`, `description_text`, `comments_text` (all already selected by `hybrid.py`).
- Produces: `_doc_text(c: dict) -> str` — up to 1000 chars total (200 summary + 500 description + 300 comments), safe under MiniLM's 256-token limit.

- [ ] **Step 1: Read the current test file to preserve style**

Run: `cat tests/retrieval/v2/test_rerank.py`

- [ ] **Step 2: Append failing tests**

Append to `tests/retrieval/v2/test_rerank.py`:

```python
def test_doc_text_truncates_summary_to_200():
    from backend.retrieval.v2.rerank import _doc_text
    long_summary = "s" * 500
    out = _doc_text({"summary": long_summary, "description_text": "", "comments_text": ""})
    assert out == "s" * 200


def test_doc_text_truncates_description_to_500():
    from backend.retrieval.v2.rerank import _doc_text
    long_desc = "d" * 1200
    out = _doc_text({"summary": "sum", "description_text": long_desc, "comments_text": ""})
    # summary + "\n" + first 500 chars of desc
    assert out == "sum\n" + ("d" * 500)


def test_doc_text_truncates_comments_to_300_with_prefix():
    from backend.retrieval.v2.rerank import _doc_text
    long_comments = "c" * 1000
    out = _doc_text({"summary": "sum", "description_text": "", "comments_text": long_comments})
    assert "[comments] " + ("c" * 300) in out
    assert out.endswith("c" * 300)


def test_doc_text_omits_comments_prefix_when_empty():
    from backend.retrieval.v2.rerank import _doc_text
    out = _doc_text({"summary": "sum", "description_text": "desc", "comments_text": ""})
    assert "[comments]" not in out
    assert out == "sum\ndesc"


def test_doc_text_full_layout_all_three_fields():
    from backend.retrieval.v2.rerank import _doc_text
    out = _doc_text({
        "summary": "s" * 200,
        "description_text": "d" * 500,
        "comments_text": "c" * 300,
    })
    assert len(out) <= 1000 + len("[comments] \n\n")  # allow prefix + separators
    assert ("s" * 200) in out
    assert ("d" * 500) in out
    assert ("[comments] " + "c" * 300) in out


def test_doc_text_handles_none_fields_defensively():
    from backend.retrieval.v2.rerank import _doc_text
    out = _doc_text({"summary": None, "description_text": None, "comments_text": None})
    assert out == ""
```

- [ ] **Step 3: Run tests, verify they fail**

Run: `venv/bin/pytest tests/retrieval/v2/test_rerank.py -v -k doc_text`
Expected: 6 new tests fail because current `_doc_text` truncates at MAX_DOC_CHARS globally, doesn't split budget, doesn't include comments.

- [ ] **Step 4: Replace `_doc_text` in rerank.py**

Edit `backend/retrieval/v2/rerank.py`. Replace lines 56–62 (`def _doc_text` through its `return`) with:

```python
_SUMMARY_MAX  = 200
_DESC_MAX     = 500
_COMMENTS_MAX = 300


def _doc_text(c: dict) -> str:
    """Fixed-budget layout for reranker input — 1000 chars max total.

    Layout (each field independently trimmed):
      summary            : 0..200 chars
      description_text   : 0..500 chars
      [comments] ...     : 0..300 chars (prefix omitted when empty)

    Total <= 1000 chars, safe under MiniLM cross-encoder's 256-token limit
    even at ~4 chars/token. Fields joined with '\\n'; empty fields skipped.
    """
    summary  = (c.get("summary")          or "").strip()[:_SUMMARY_MAX]
    desc     = (c.get("description_text") or "").strip()[:_DESC_MAX]
    comments = (c.get("comments_text")    or "").strip()[:_COMMENTS_MAX]
    parts: list[str] = []
    if summary:  parts.append(summary)
    if desc:     parts.append(desc)
    if comments: parts.append(f"[comments] {comments}")
    return "\n".join(parts)
```

Also delete the now-unused constant `MAX_DOC_CHARS = 1000` at line 30 — it is no longer referenced.

- [ ] **Step 5: Run tests, verify rerank tests pass**

Run: `venv/bin/pytest tests/retrieval/v2/test_rerank.py -v`
Expected: all tests pass (existing + 6 new).

- [ ] **Step 6: Commit**

```bash
git add backend/retrieval/v2/rerank.py tests/retrieval/v2/test_rerank.py
git commit -m "feat(retrieval-v2): _doc_text fixed budget with comments (spec §6.4)

Reranker input layout: 200 summary + 500 description + 300 comments,
joined with newlines, [comments] prefix on the comments segment.
Total <=1000 chars — safe under MiniLM's 256-token limit.

Ships alongside Phase 2 code but is unconditional (not gated on
CONWO_RETRIEVAL_V2_COMMENTS) — _doc_text doesn't touch the embedding
column, and letting the reranker see comment text is a free lift.

Removes now-unused MAX_DOC_CHARS constant."
```

---

### Task 4: hybrid.py — conditional dense_c CTE

**Files:**
- Modify: `backend/retrieval/v2/hybrid.py`
- Test: `tests/retrieval/v2/test_hybrid.py` (extend)

**Interfaces:**
- Consumes: `tickets.comments_embedding` column (from Task 1).
- Produces:
  - `_build_base_sql(comments_enabled: bool) -> str` — new helper returning the SQL template. Testable by string inspection.
  - `hybrid_search` uses `_build_base_sql(os.getenv("CONWO_RETRIEVAL_V2_COMMENTS", "off") == "on")`.
  - When flag off, emitted SQL is byte-identical to Phase 1's `_BASE_SQL`.
  - When on, adds `dense_c` CTE (searching `comments_embedding`) as a third RRF source.

- [ ] **Step 1: Append failing tests**

Append to `tests/retrieval/v2/test_hybrid.py`:

```python
def test_build_base_sql_omits_dense_c_when_flag_off():
    from backend.retrieval.v2.hybrid import _build_base_sql
    sql = _build_base_sql(comments_enabled=False)
    assert "dense_c" not in sql
    assert "comments_embedding" not in sql


def test_build_base_sql_includes_dense_c_when_flag_on():
    from backend.retrieval.v2.hybrid import _build_base_sql
    sql = _build_base_sql(comments_enabled=True)
    assert "dense_c AS" in sql
    assert "comments_embedding IS NOT NULL" in sql
    # The UNION ALL block must include the dense_c source.
    assert "SELECT key, dense_c_rnk" in sql or "SELECT key, rnk FROM dense_c" in sql


def test_hybrid_search_reads_env_flag(monkeypatch):
    """hybrid_search picks up CONWO_RETRIEVAL_V2_COMMENTS at call time."""
    from backend.retrieval.v2 import hybrid
    captured_sql = []

    class FakeCur:
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def execute(self, sql, params): captured_sql.append(sql)
        def fetchall(self): return []
    class FakeConn:
        def cursor(self, **k): return FakeCur()

    monkeypatch.setenv("CONWO_RETRIEVAL_V2_COMMENTS", "on")
    hybrid.hybrid_search(FakeConn(), ["q"], [[0.0]*768], {}, limit=5)
    assert any("dense_c" in s for s in captured_sql)

    captured_sql.clear()
    monkeypatch.setenv("CONWO_RETRIEVAL_V2_COMMENTS", "off")
    hybrid.hybrid_search(FakeConn(), ["q"], [[0.0]*768], {}, limit=5)
    assert not any("dense_c" in s for s in captured_sql)
```

- [ ] **Step 2: Run tests, verify they fail**

Run: `venv/bin/pytest tests/retrieval/v2/test_hybrid.py -v -k "dense_c or env_flag"`
Expected: 3 new tests fail — `_build_base_sql` doesn't exist yet; hybrid_search doesn't read the env flag.

- [ ] **Step 3: Refactor hybrid.py — extract `_build_base_sql`, extend for dense_c**

Edit `backend/retrieval/v2/hybrid.py`.

**A. Replace the module-level `_BASE_SQL` constant with a helper function.** Remove lines 16–53 (the `_BASE_SQL = "..."` block) and replace with:

```python
_BASE_SQL_PHASE1 = """
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
{dense_c_cte}
fused AS (
    SELECT key, SUM(1.0 / (%(k)s + rnk)) AS rrf
    FROM (
        SELECT key, lex_rnk  AS rnk FROM lex
        UNION ALL
        SELECT key, dense_rnk AS rnk FROM dense
        {dense_c_union}
    ) u
    GROUP BY key
)
SELECT t.key, t.summary, t.description_text, t.comments_text,
       t.status_category, t.priority, t.updated_at, t.resolved_at,
       t.functional_area, t.links_json,
       f.rrf AS fused_score
FROM fused f
JOIN tickets t USING (key)
ORDER BY f.rrf DESC
LIMIT %(limit)s
"""

_DENSE_C_CTE = """dense_c AS (
    SELECT key,
           1 - (comments_embedding <=> %(q_vec)s::vector) AS dense_c_score,
           ROW_NUMBER() OVER (ORDER BY comments_embedding <=> %(q_vec)s::vector) AS dense_c_rnk
    FROM tickets
    WHERE comments_embedding IS NOT NULL
    {filter_sql_dense_c}
    ORDER BY comments_embedding <=> %(q_vec)s::vector
    LIMIT 100
),
"""

_DENSE_C_UNION = """UNION ALL
        SELECT key, dense_c_rnk AS rnk FROM dense_c"""


def _build_base_sql(comments_enabled: bool) -> str:
    """Return the base SQL template. Filter clauses still need to be
    interpolated by the caller via `.format(filter_sql_lex=..., filter_sql_dense=..., filter_sql_dense_c=...)`.
    """
    if comments_enabled:
        return _BASE_SQL_PHASE1.format(
            dense_c_cte=_DENSE_C_CTE,
            dense_c_union=_DENSE_C_UNION,
            filter_sql_lex="{filter_sql_lex}",
            filter_sql_dense="{filter_sql_dense}",
            filter_sql_dense_c="{filter_sql_dense_c}",
        )
    return _BASE_SQL_PHASE1.format(
        dense_c_cte="",
        dense_c_union="",
        filter_sql_lex="{filter_sql_lex}",
        filter_sql_dense="{filter_sql_dense}",
        filter_sql_dense_c="",  # discarded because no dense_c CTE present
    )
```

**Note:** the nested `.format(...)` is deliberate — the outer format resolves the CTE/UNION slots at build-time, leaving the `{filter_sql_*}` slots for `hybrid_search` to resolve at call-time.

**B. Update `hybrid_search`.** Replace the body (lines 103–128) with:

```python
def hybrid_search(conn, sub_queries: list[str], query_vecs: list[list[float]],
                  filters: dict, limit: int = 50) -> list[dict]:
    """Run hybrid retrieval per sub-query, fuse, return top-`limit` candidates."""
    if not sub_queries:
        return []
    comments_enabled = (os.getenv("CONWO_RETRIEVAL_V2_COMMENTS", "off").lower() == "on")
    filter_clause, filter_params = _build_filters_sql(filters or {})
    base_sql = _build_base_sql(comments_enabled)
    sql = base_sql.format(
        filter_sql_lex=filter_clause,
        filter_sql_dense=filter_clause,
        filter_sql_dense_c=filter_clause,
    )
    per_sub: list[list[dict]] = []
    with conn.cursor(row_factory=dict_row) as cur:
        for q_text, q_vec in zip(sub_queries, query_vecs):
            params: dict[str, Any] = {
                "q_text": q_text,
                "q_vec": q_vec,
                "k": RRF_K,
                "limit": limit,
                **filter_params,
            }
            cur.execute(sql, params)
            rows = list(cur.fetchall())
            per_sub.append([{"key": r["key"], "fused_score": float(r["fused_score"]), **r} for r in rows])

    fused = _rrf_fuse(per_sub)
    fused = timeline.apply_timeline(fused)
    return fused[:limit]
```

Add `import os` at the top of `hybrid.py` if not already present.

- [ ] **Step 4: Run tests, verify all hybrid tests pass**

Run: `venv/bin/pytest tests/retrieval/v2/test_hybrid.py -v`
Expected: all pass (existing + 3 new).

- [ ] **Step 5: Full retrieval-v2 test sweep**

Run: `venv/bin/pytest tests/retrieval/v2/ -v --ignore=tests/retrieval/v2/test_e2e_integration.py`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add backend/retrieval/v2/hybrid.py tests/retrieval/v2/test_hybrid.py
git commit -m "feat(retrieval-v2): conditional dense_c CTE for comments search (spec §6.3)

hybrid_search reads CONWO_RETRIEVAL_V2_COMMENTS env var. When 'on',
adds a dense_c CTE searching tickets.comments_embedding as a third
RRF source. When 'off' (default), emitted SQL is byte-identical to
Phase 1 — no behavioral change for existing deploys.

_build_base_sql extracted as a testable helper. Tests inspect the
emitted SQL string; full SQL execution is covered by the opt-in PG
fixture in test_e2e_integration."
```

---

### Task 5: Push branch, open PR, run backfill, flip flag

**Files:** none (git + Bitbucket + operational).

- [ ] **Step 1: Verify clean tree + commits**

Run: `git status && git log --oneline main..HEAD`
Expected: clean tree; 4 new commits (Tasks 1–4).

- [ ] **Step 2: Push and open PR #39**

```bash
git checkout -b feat/retrieval-v2-comments
git push -u bitbucket feat/retrieval-v2-comments
```

Open PR #39. Title: `feat(retrieval-v2): dual-vector comments embedding`

Body:
```
Closes spec §6 (Phase 2 of docs/superpowers/specs/2026-07-02-retrieval-v2-timeline-and-comments-design.md).

- Migration 151: adds tickets.comments_embedding vector(768) + HNSW index.
- embed_tickets.py: dual-embed + --comments-only backfill mode.
- hybrid.py: conditional dense_c CTE gated on CONWO_RETRIEVAL_V2_COMMENTS.
  When 'off' (default), emitted SQL is byte-identical to Phase 1.
- rerank.py: fixed-budget _doc_text with 200/500/300 layout including
  trailing comments. Unconditional — reranker sees comment text even
  when the dense_c CTE is disabled.

Rollout after merge:
  1. Migration 151 applied automatically on deploy.
  2. Run: python scripts/embed_tickets.py --mode full --comments-only
     (one-shot backfill, ~$1-5 in Gemini cost).
  3. PR #40: flip CONWO_RETRIEVAL_V2_COMMENTS=on in shadow env.
  4. Monitor shadow logs 3-5 days; flip on serving instance if healthy.

Tests: 13 new (4 embed_tickets + 6 rerank + 3 hybrid).
```

- [ ] **Step 3: Merge PR #39 after CI green + reviewer LGTM**

Squash-merge per project convention. Migration 151 applies on next deploy startup (via `db.init_db()`).

- [ ] **Step 4: Run one-shot backfill against production**

```bash
# From a machine with prod DSN access:
venv/bin/python scripts/embed_tickets.py --mode full --comments-only
```

Watch progress (`  embedded N rows (X/s)` lines). Cost: at current ticket count (~10K), ~$1–5 in Gemini charges. Resumable — if interrupted, re-run picks up where it left off (empty comments → NULL, skipped naturally).

- [ ] **Step 5: Verify backfill result in prod DB**

```sql
SELECT count(*) AS total,
       count(comments_embedding) AS with_comments_emb,
       count(comments_text) FILTER (WHERE comments_text IS NOT NULL AND comments_text <> '') AS with_comments_text
FROM tickets;
```

Expected: `with_comments_emb` roughly equal to `with_comments_text` (tickets with empty comments correctly have NULL embeddings).

- [ ] **Step 6: PR #40 — flip flag to on in shadow env**

Edit deploy config (whatever holds `CONWO_RETRIEVAL_V2*` env vars — likely `deploy/` YAML or the Kubernetes secret; consult the deploy docs). Add:

```
CONWO_RETRIEVAL_V2_COMMENTS=on
```

Only on the shadow-mode instance initially. Open PR #40 for the config change, merge, deploy.

- [ ] **Step 7: Monitor shadow logs 3–5 days**

Grep production logs for `shadow.bucket_counts` (from Phase 1) and inspect the `v2_keys` in `retrieval_shadow_log` table. Compare top-1 stability between v2-without-comments (baseline) and v2-with-comments (after flip):

```sql
SELECT date_trunc('day', created_at) AS day,
       count(*) FILTER (WHERE v2_keys[1] != v1_keys[1]) AS top1_differs
FROM retrieval_shadow_log
WHERE created_at > now() - interval '5 days'
GROUP BY 1 ORDER BY 1;
```

Success criterion (spec §9): ≥5% top-1 change rate on debugging-labeled queries indicates comments retrieval is finding tickets description-only retrieval missed. No p99 `/query` latency regression >100ms.

- [ ] **Step 8: If shadow signal is healthy, flip on serving instance**

Deploy config: set `CONWO_RETRIEVAL_V2_COMMENTS=on` on the serving instance (whichever runs `CONWO_RETRIEVAL_V2=on` or `=ab`). Merge as PR #41 (a second, isolated config change PR — never bundle flag flips with code changes).

---

## Rollback plan

At any step:
- **Post-migration, pre-code-deploy:** column exists but unused; nothing to roll back.
- **Post-code-deploy, flag off:** `CONWO_RETRIEVAL_V2_COMMENTS` unset or `off` → SQL byte-identical to Phase 1 → zero behavioral change.
- **Flag on, regression detected:** set `CONWO_RETRIEVAL_V2_COMMENTS=off` on the affected instance → immediate revert. No data loss; `comments_embedding` column stays populated for future retry.
- **Migration itself is bad (unlikely — pure `ADD COLUMN` + index):** `ALTER TABLE tickets DROP COLUMN comments_embedding;` and `DROP INDEX idx_tickets_comments_embedding;` are cheap. Do this only if the column is confirmed unused (no code path reads it).
