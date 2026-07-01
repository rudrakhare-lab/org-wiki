# Conwo Jira Retrieval v2 — Design Spec

_Date: 2026-06-24_
_Status: approved (pending implementation plan)_
_Scope: Conwo's Jira retrieval engine only. Wiki retrieval, PMS, knowledge graph, MCP, multi-agent platform, frontend, traces — all untouched._

---

## 1. Why we are doing this

Conwo treats 37,484 Jira tickets as a knowledge base, but it currently searches them with
`ILIKE '%keyword%'` substring scans against `summary`, `description_text`, `comments_text`. There
is no full-text index, no semantic understanding, no use of ticket relationships, and no
relevance score — just substring presence/absence. Measurements (see
`docs/analysis/jira-retrieval-analysis.md`) showed:

- `login` and `authentication` matches overlap **1%** — synonyms silently miss recall.
- **52.5% of tickets** are structurally unreachable via the module-prefetch path (INNER JOIN on
  an incomplete `ticket_module_tags` table).
- **27.6% of tickets** have no description and no comments — near-invisible to keyword search.
- A common-term scan = **698 ms** on 37k rows (cold ≈ multi-second), with no index to lean on.
- No mechanism prevents confident wrong answers when retrieved evidence is weak or
  contradictory — there is no relevance score to threshold on.

The goal of v2 is to move retrieval from *lexical keyword scan* to *semantic understanding with
bounded confidence*, so a user query reliably gets the most accurate, complete answer — and
Conwo refuses to answer confidently when the evidence does not support it.

## 2. Goals and non-goals

**Goals:**
1. Reach the entire 37k corpus, not just keyword-matching slices.
2. Understand the query semantically (synonyms, paraphrases, compound questions).
3. Use ticket relationships (blocks/duplicates/supersedes/epics) as first-class signal.
4. Never produce a confident answer without strong, agreeing, recent evidence.
5. Roll out safely on a deployed system, with no regression in correctness during the transition.
6. Stay on existing Postgres infrastructure. No new SaaS, no new vendors that need infosec
   review, no GPU servers.

**Non-goals:**
- Not scaling Conwo itself to 1M tickets. The same architecture will survive 1M, but tuning for
  that volume (HNSW `m`/`ef_construction`, rerank batch size) is out of scope for this spec.
- Not touching wiki retrieval, PMS tools, the multi-agent platform, or the knowledge graph.
- Not introducing a context-compression layer (LLMLingua-style). At top-k = 5–10 Jira tickets,
  the LLM prompt is already small.

## 3. Architecture overview

```
                  User question
                       │
                       ▼
       ┌─────────────────────────────────┐
       │ Query rewrite (Claude, ~₹1)     │ ← decompose, expand, extract filters
       └────────────┬────────────────────┘
                    │ N sub-queries + filters
                    ▼
       ┌─────────────────────────────────┐
       │ Embed each sub-query (Gemini)   │ ← task_type="RETRIEVAL_QUERY"
       └────────────┬────────────────────┘
                    ▼
   ┌──────────────────────────────────────────────┐
   │           POSTGRES (one query)                │
   │  BM25 (tsvector+GIN)  ∥  Dense (pgvector)    │ ← runs in parallel within Postgres
   │           ↓                  ↓                │
   │           Reciprocal Rank Fusion              │ ← Python, ~10 lines
   │                    ↓                          │
   │           top 50 candidates                   │
   └──────────────────┬───────────────────────────┘
                      ▼
       ┌─────────────────────────────────┐
       │ Relationship expansion          │ ← 1-hop ticket_links, drop superseded
       └────────────┬────────────────────┘
                    ▼
       ┌─────────────────────────────────┐
       │ bge-reranker-v2-m3 (local CPU)  │ ← cross-encoder, ~200ms for 50 candidates
       └────────────┬────────────────────┘
                    ▼
       ┌─────────────────────────────────┐
       │ Strict confidence gate          │ ← top score < 0.5 → abstain
       └────────────┬────────────────────┘
                    │ top 5–10 tickets + confidence label + abstain-or-answer signal
                    ▼
       ┌─────────────────────────────────┐
       │ LLM (Claude) composes answer    │ ← grounded, cited
       └─────────────────────────────────┘
```

## 4. Component design

### 4.1 Query rewrite — `backend/retrieval/v2/rewrite.py`

A single Claude Haiku call (cheap, fast) before retrieval:

**Input:** raw user question + agent context (modules available, current date).

**Output (JSON):**
```json
{
  "sub_queries": ["meal booking bugs Q2 2026", "overnight meal scan bug status"],
  "expansions": {"OTP": ["one-time password"], "BRE": ["booking-rule-engine"]},
  "filters": {
    "functional_area": null,
    "resolved_after": "2026-04-01",
    "module": "meal-management"
  },
  "intent": "DEBUGGING" | "STATUS" | "DEFINITION" | "CONFIGURATION" | ...
}
```

**Rules:**
- Filters set only when the question is explicit. Never guess `functional_area` from semantic
  hints — that's what the embedding model is for.
- If the question references a config property or BUID, set a `route_to_pms: true` flag and the
  orchestrator runs PMS tools in parallel (out of scope for this spec, but the rewrite emits the
  signal).
- One LLM call per query. ~₹1 amortized. Cached on identical question strings for 5 minutes.

### 4.2 Embedding — `backend/retrieval/v2/embed.py`

Thin wrapper around Google's Gemini embeddings (`gemini-embedding-001`, 768-dim).

- **For documents** (sync time): `task_type="RETRIEVAL_DOCUMENT"`, input = `summary + "\n\n" + description_text` truncated to model max.
- **For queries** (query time): `task_type="RETRIEVAL_QUERY"`, input = the sub-query string.
- Asymmetric: mixing these up silently degrades recall. Enforce via separate functions
  `embed_document()` / `embed_query()`. No `embed()` general helper.
- Org-provided API key in env var `GOOGLE_GENAI_API_KEY`. Falls back to a local model
  (`bge-small-en-v1.5`) only if Gemini calls fail consecutively — a circuit breaker, not a
  primary path.
- Batching: document embedding runs in batches of 100 during sync (Gemini supports batch input).
  Query embedding is single-call.

### 4.3 Hybrid SQL retrieval — `backend/retrieval/v2/hybrid.py`

A single Postgres query that does BM25 and dense ANN in parallel and fuses by Reciprocal Rank Fusion:

```sql
WITH lex AS (
  SELECT key, ts_rank_cd(search_tsv, query) AS score,
         ROW_NUMBER() OVER (ORDER BY ts_rank_cd(search_tsv, query) DESC) AS rnk
  FROM tickets, websearch_to_tsquery('english', %(q)s) query
  WHERE search_tsv @@ query
  LIMIT 50
),
dense AS (
  SELECT key, 1 - (embedding <=> %(qvec)s) AS score,
         ROW_NUMBER() OVER (ORDER BY embedding <=> %(qvec)s) AS rnk
  FROM tickets
  WHERE embedding IS NOT NULL
  ORDER BY embedding <=> %(qvec)s
  LIMIT 50
),
fused AS (
  SELECT key, SUM(1.0 / (60 + rnk)) AS rrf
  FROM (SELECT key, rnk FROM lex UNION ALL SELECT key, rnk FROM dense) u
  GROUP BY key
)
SELECT t.*, f.rrf
FROM fused f JOIN tickets t USING (key)
ORDER BY f.rrf DESC
LIMIT 50;
```

RRF constant `k=60` is the standard choice; not tuned in v1. Each sub-query (from rewrite) runs
this independently; results are deduplicated and the per-key max RRF is kept.

### 4.4 Relationship expansion — uses `ticket_links` table

After fusion returns 50 candidates:

1. **Drop superseded:** for any candidate where `ticket_links` has
   `(candidate, dst, 'supersedes')`, replace with `dst` if `dst` is more recently updated.
2. **1-hop expansion:** pull every ticket linked to a top-20 candidate (limit 20 added). These
   join the pool *before* reranking — the reranker decides if they belong.
3. **Epic rollup tag:** if 3+ candidates share an epic, fetch the epic row and tag the result set
   with `epic_rollup: <KEY>`. The composer LLM is instructed to summarize "across this epic."

### 4.5 Cross-encoder rerank — `backend/retrieval/v2/rerank.py`

Loads `BAAI/bge-reranker-v2-m3` once at startup via `sentence-transformers`. CPU inference is
sufficient at Conwo's internal QPS (~200 ms for 50 candidates).

```python
def score(query: str, candidates: list[dict]) -> list[tuple[dict, float]]:
    pairs = [(query, c["summary"] + " " + c["description_text"][:1000]) for c in candidates]
    scores = reranker.predict(pairs)  # returns float[0..1]
    return sorted(zip(candidates, scores), key=lambda x: x[1], reverse=True)
```

Truncating ticket text to ~1000 chars keeps inference fast and gives the model the high-signal
prefix (Jira tickets front-load the problem statement).

### 4.6 Strict confidence gate — `backend/retrieval/v2/gate.py`

Maps reranker scores → confidence label → action:

| Top score | Top-3 agree? | Confidence | Action |
|---|---|---|---|
| ≥ 0.7 | yes | **High** | answer normally with citations |
| ≥ 0.7 | no | **Medium** | surface both sides, flag conflict |
| 0.5–0.7 | yes | **Medium** | answer with explicit "evidence is moderate" |
| 0.5–0.7 | only 1 ticket | **Low** | answer + flag "single-source evidence" |
| < 0.5 | n/a | — | **Abstain.** Return: "I couldn't find strong evidence. Closest matches: [keys]. Please verify." |

"Top-3 agree" = top 3 tickets share at least one of: same functional_area, same epic, or share a
`supersedes`/`duplicates` link. This is heuristic; v1 uses the simple version, v2.1 may refine.

Thresholds are tunable via env vars (`CONWO_RETRIEVAL_V2_ABSTAIN_THRESHOLD=0.5` etc.) so we can
adjust without redeploying.

### 4.7 Orchestration — `backend/retrieval/v2/pipeline.py`

The public entry point. Replaces the current `jira_retriever.search()` / `by_module()` calls.
Same function signatures externally so `backend/preflight.py` and `backend/tools/jira_tools.py`
don't have to change.

```python
def search(query: str, *, functional_area: str | None = None,
           limit: int = 10, agent: Agent) -> RetrievalResult: ...

def by_module(module_slug: str, query: str, limit: int = 5) -> list[dict]: ...
```

`by_module` no longer INNER-JOINs `ticket_module_tags`. Instead it embeds the module description
(from the wiki module page) and uses semantic similarity as a soft boost. **This single change
makes 19,660 previously-untagged tickets reachable again.**

## 5. Schema changes — migration `migrations/postgres/150_retrieval_v2.sql`

```sql
-- ── BM25 / lexical ─────────────────────────────────────────────
ALTER TABLE tickets ADD COLUMN IF NOT EXISTS search_tsv tsvector
  GENERATED ALWAYS AS (
    setweight(to_tsvector('english', coalesce(summary,'')),          'A') ||
    setweight(to_tsvector('english', coalesce(description_text,'')), 'B') ||
    setweight(to_tsvector('english', coalesce(comments_text,'')),    'C')
  ) STORED;
CREATE INDEX IF NOT EXISTS idx_tickets_tsv ON tickets USING GIN (search_tsv);

-- ── Dense / semantic ───────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS vector;
ALTER TABLE tickets ADD COLUMN IF NOT EXISTS embedding vector(768);
ALTER TABLE tickets ADD COLUMN IF NOT EXISTS embedded_at timestamptz;
CREATE INDEX IF NOT EXISTS idx_tickets_embedding
  ON tickets USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);

-- ── Normalized relationships ───────────────────────────────────
CREATE TABLE IF NOT EXISTS ticket_links (
  src_key   text NOT NULL REFERENCES tickets(key) ON DELETE CASCADE,
  dst_key   text NOT NULL,
  link_type text NOT NULL,
  PRIMARY KEY (src_key, dst_key, link_type)
);
CREATE INDEX IF NOT EXISTS idx_links_dst ON ticket_links (dst_key, link_type);
CREATE INDEX IF NOT EXISTS idx_links_src ON ticket_links (src_key, link_type);

-- ── Shadow-mode logging (for Phase 2 evaluation) ───────────────
CREATE TABLE IF NOT EXISTS retrieval_shadow_log (
  id           bigserial PRIMARY KEY,
  trace_id     text,
  question     text NOT NULL,
  v1_keys      text[],
  v2_keys      text[],
  v2_scores    real[],
  v2_confidence text,           -- High | Medium | Low | Abstain
  v2_latency_ms integer,
  served_v2    boolean NOT NULL,
  created_at   timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_shadow_created ON retrieval_shadow_log (created_at);
```

## 6. Ingestion / sync changes

Existing nightly: `scripts/jira_daily_sync.py` → `jira_sync.py --incremental` → `classify_jira.py --delta`.

**Add two steps after existing nightly:**

1. `scripts/embed_tickets.py --delta` — finds rows where `embedded_at IS NULL OR updated_at > embedded_at`, batches them through Gemini, writes back. ~seconds for typical daily delta.
2. `scripts/backfill_ticket_links.py --delta` — parses `links_json` of new/updated tickets, upserts into `ticket_links`. Removed links also cleaned up.

**One-time bootstrap** (run once after migration ships, before flipping any traffic):
- `embed_tickets.py --full` — embed all 37,484 tickets. ~20 min, free (Gemini org key).
- `backfill_ticket_links.py --full` — normalize all `links_json`. ~1 min.

Both jobs are idempotent and resumable. They write progress to `sync_runs`.

## 7. Backend additions

| File | Role | LOC estimate |
|---|---|---|
| `backend/retrieval/v2/__init__.py` | Public API: `search()`, `by_module()` | 30 |
| `backend/retrieval/v2/embed.py` | Gemini doc/query embedding + circuit breaker | 80 |
| `backend/retrieval/v2/rerank.py` | bge-reranker-v2-m3 loader + `score()` | 60 |
| `backend/retrieval/v2/hybrid.py` | The fused SQL query + RRF in app for multi-subquery | 120 |
| `backend/retrieval/v2/links.py` | Supersession drop, 1-hop expansion, epic rollup | 100 |
| `backend/retrieval/v2/gate.py` | Strict-mode thresholds + abstention envelope | 80 |
| `backend/retrieval/v2/rewrite.py` | Claude-Haiku query decomposer | 100 |
| `backend/retrieval/v2/pipeline.py` | Orchestrates all of the above | 150 |
| `scripts/embed_tickets.py` | Full + delta embed job | 120 |
| `scripts/backfill_ticket_links.py` | Full + delta link normalizer | 80 |
| `migrations/postgres/150_retrieval_v2.sql` | Schema | 40 |
| Updated `scripts/jira_daily_sync.py` | Call new sub-steps | +20 |

Total new code: ~1,100 LOC + 1 migration. No changes to `backend/preflight.py`, no changes to
`backend/tools/jira_tools.py` (their imports of `jira_retriever` now route to v2 behind a flag).

## 8. Rollout — Shadow → A/B → Cutover

Controlled by env var `CONWO_RETRIEVAL_V2`:
- `off` (default initially) → v1 ILIKE serves; v2 not invoked.
- `shadow` → v1 serves users; v2 also runs and logs to `retrieval_shadow_log` for offline comparison. No user-visible impact.
- `ab` → percentage of queries routed to v2 (via `CONWO_RETRIEVAL_V2_PCT=10|50|100`); rest get v1.
- `on` → all queries get v2.

**Phase 0 — Infra prep (1 day):** Enable `pgvector` on RDS, run migration in staging, verify, run in prod. Bake bge-reranker model into the backend Docker image.

**Phase 1 — Backfill (1 day):** Run `embed_tickets.py --full` + `backfill_ticket_links.py --full` in prod. Verify counts.

**Phase 2 — Shadow (~1 week):** Flip env to `shadow`. Live traffic. We compare v1 vs. v2 on every query through offline review of `retrieval_shadow_log`. Build an eval set of ~50 graded questions during this week.

**Phase 3 — A/B (~3–5 days):** `ab` mode at 10% → 50% → 100%, watching feedback scores and abstention rate at each step. Roll back to v1 instantly by flipping the env var if anything regresses.

**Phase 4 — Decommission (later):** Once v2 has run at 100% for 2 weeks with no issues, delete the v1 retrieval code in a separate cleanup PR.

## 9. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Gemini API approval doesn't cover internal customer data in Jira tickets | Verify with infosec **before Phase 1 backfill**. Fallback: local `bge-large-en-v1.5` embeddings — same architecture, no change downstream. |
| Embedding cost / rate limits | One-time backfill is ~37k embed calls; nightly delta is ~10–100. Well within free-tier quotas. |
| Reranker latency on CPU at peak QPS | At Conwo's internal QPS this is fine. If it ever becomes a bottleneck, switch to `onnxruntime` (4–8× faster on CPU) — same model, drop-in. |
| Abstention rate too high (users frustrated) | Thresholds env-tunable. If Phase 2 shadow logs show abstention >30% on real queries, retune before A/B. |
| Reranker model file (~560 MB) bloats Docker image | Multi-stage Docker build; download model in a builder stage, copy to slim final image. ~700 MB net increase, acceptable. |
| pgvector not enabled on RDS instance | Confirmed available on standard AWS RDS / GCP Cloud SQL Postgres 15+. One DBA action. |
| HNSW index build time on backfill | At 37k rows × 768d, build is ~1 min. Negligible. |
| Drift between `embedded_at` and `updated_at` (stale embeddings) | Nightly delta job catches this; `embed_tickets.py` re-embeds when `updated_at > embedded_at`. |
| New retrieval changes ranking enough that the LLM "answer prompt" becomes miscalibrated | Shadow phase explicitly checks answer text similarity vs. v1; cutover gated on no quality regression. |

## 10. Testing strategy

1. **Unit tests** per component: `embed.py` (doc/query separation), `gate.py` (every threshold transition), `links.py` (supersession drop), `rerank.py` (score monotonicity on a fixed pair).
2. **Integration test** of the full pipeline against a small fixture corpus (~50 tickets, sqlite-backed) so CI doesn't need Postgres or Gemini.
3. **Eval set** of ~50 manually-graded queries with expected top-k tickets. Built during Phase 2 shadow. Required to pass at >85% recall@10 before Phase 3.
4. **Shadow-log review tool** — small script that prints v1 vs. v2 disagreements for human spot-check.
5. **Performance test** — measure p50/p95 latency at 10× expected QPS; abort if rerank dominates and > 1s.

## 11. Explicit out-of-scope (deliberate)

- ❌ Elasticsearch / OpenSearch — Postgres `tsvector` is enough at 37k.
- ❌ Pinecone / Weaviate / Qdrant — pgvector is enough; same Postgres simplifies ops.
- ❌ vLLM / Triton / TGI GPU servers — CPU inference is fast enough at Conwo's QPS.
- ❌ LLMLingua / context compression — top-k = 5–10 tickets fits comfortably in Claude's window.
- ❌ Cohere reranker — bge-reranker-v2-m3 is ~98% as good and free, no infosec review.
- ❌ Streaming/SSE changes — orthogonal to retrieval; current path already streams.
- ❌ Touching wiki retrieval, PMS, knowledge graph, multi-agent, frontend.

## 12. Open questions (to resolve during implementation)

1. Confirm Gemini `gemini-embedding-001` is approved for internal customer data (Jira tickets contain customer BUIDs, support incident details).
2. Final RRF constant `k` (60 is standard but worth a small ablation on the eval set).
3. Whether to embed `comments_text` in addition to `summary + description_text` for documents. Comments are large; the marginal recall gain may not justify the embedding cost.
4. Whether "top-3 agree" should consider `ticket_module_tags` confidence when present, or stay purely structural.
5. Decommissioning path for `ticket_module_tags`: shrink to "boost only," or remove entirely once `embedding` covers the use case.

## 13. Decision log

| Decision | Choice | Reason |
|---|---|---|
| Stay on Postgres vs. dedicated vector DB | Postgres + pgvector | Sufficient to ~1M rows; keeps one data store. |
| Embedding source | Gemini API (org-approved) | Top-tier quality, free at our volume, infosec already cleared. |
| Reranker | Local `bge-reranker-v2-m3` | ~98% of Cohere's quality, free, private, no new vendor. |
| Confidence behavior | **Strict — abstain when weak** | Aligns with "never confidently wrong" north star. |
| Query handling | **Decompose + expand** via Claude | Biggest accuracy unlock for messy real-world questions. |
| Relationships | **Normalize + use for ranking & expansion** | Largest qualitative leap toward true understanding of the corpus. |
| Rollout | **Shadow → A/B → cutover** | Zero-risk on a deployed system. |
