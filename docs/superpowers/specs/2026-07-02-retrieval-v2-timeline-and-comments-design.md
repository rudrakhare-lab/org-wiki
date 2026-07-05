# Jira Retrieval V2 — Timeline Weighting + Comments-Aware Embedding

**Date:** 2026-07-02
**Status:** Design — pending implementation plan
**Predecessor:** [2026-06-24 jira-retrieval-v2 design](./2026-06-24-jira-retrieval-v2-design.md)

---

## 1. Problem

Retrieval V2 shipped with two structural gaps against the rules the wiki's own
prompt layer enforces:

**Gap 1 — Retrieval is timeline-blind.** `CLAUDE.md` §5 Step 2 and §9 require
Jira tickets to be bucketed into `LATEST` / `HISTORICAL` / `STALE-OPEN` and
ranked with recency + status weight. `deep_system_prompt.py` (lines 229–243,
318–321) speaks that vocabulary and asks the model to render answers using
"Latest evidence" / "Historical evidence" sections. But `hybrid.py`'s RRF fusion
gives every ticket equal weight per lexical/semantic hit — a 2023 stale-open
ticket ranks alongside a 2026 resolved ticket. The prompt is asked to re-derive
buckets from raw dates on candidates that were never ranked by those signals.
Result: the prompt template is a fiction the retrieval doesn't support.

**Gap 2 — Comments are absent from the dense embedding.** `embed_tickets.py`
embeds only `summary + description_text`. `comments_text` is in the tsvector
(BM25 side, weight C — the lowest), but not in `embedding` at all. Debugging
queries whose answer lives in the resolution comment can only be found by
lexical match — the case where dense retrieval should be strongest is the case
where it is disabled by design.

## 2. Goals

- Retrieval ranks candidates by recency + status, not just RRF match density.
- Every candidate ticket carries a `bucket ∈ {latest, historical, stale_open}`
  label all the way from `hybrid.py` to the LLM context. The prompt template
  renders from structured input, not from re-derivation.
- The gate factors bucket mix into confidence: three all-historical tickets on
  top → confidence downgraded one tier.
- Comment content participates in dense retrieval and in reranker scoring.
- Phase 1 (timeline) ships alone with no schema change or reembed. Phase 2
  (comments) ships behind an independent subflag so code, migration, backfill,
  and activation are decoupled.

## 3. Non-goals

- No new reranker model. `ms-marco-MiniLM-L-6-v2` stays. Reranker quality is
  bounded by CPU pod budget — separate decision from timeline/comments.
- No chunk-level indexing (Option C's Variant `c` — deferred). If dual-vector
  comments don't lift accuracy enough, we revisit; not in this design.
- No prompt template rewrite. `deep_system_prompt.py`'s Latest/Historical
  vocabulary is authoritative — retrieval conforms to it.
- No frontend change. Bucket badges on tickets in the UI is a separate,
  optional follow-up.

## 4. Data flow

```
question
   │
   ▼
rewrite()                                   ← unchanged
   │
   ▼
embed_query()                               ← unchanged
   │
   ▼
hybrid_search()                             ← MODIFIED
   │  (Phase 1: post-fusion timeline weight; Phase 2: dual-vector dense_c CTE)
   │  emits candidates[] with {..., fused_score, bucket, timeline_score}
   ▼
expand_links()                              ← unchanged (propagates fields)
   │
   ▼
rerank.score() / score_async()              ← MODIFIED (Phase 2: _doc_text budget)
   │
   ▼
gate.apply()                                ← MODIFIED (Phase 1: bucket-mix penalty)
   │
   ▼
RetrievalResult
   ├── tickets[] each with {..., bucket, timeline_score, reranker_score}
   └── diagnostics: {..., bucket_counts: {latest, historical, stale_open}}
```

## 5. Phase 1 — Timeline weighting (B)

### 5.1 New module: `backend/retrieval/v2/timeline.py`

Single-purpose module, unit-testable in isolation. Owned by both `hybrid.py`
(uses `apply_timeline`) and `gate.py` (uses `bucket_counts`, penalty logic).

Public surface:

```python
# Env-tunable knobs — same pattern as gate.py's `_f` helper.
HALFLIFE_DAYS = float(os.getenv("CONWO_RETRIEVAL_V2_TIMELINE_HALFLIFE_DAYS", "180"))
LATEST_DAYS   = int(os.getenv("CONWO_RETRIEVAL_V2_TIMELINE_LATEST_DAYS",   "180"))
STALE_DAYS    = int(os.getenv("CONWO_RETRIEVAL_V2_TIMELINE_STALE_DAYS",    "180"))

STATUS_WEIGHTS = {
    "done_resolved": 1.00,   # status_category='done' AND resolved_at IS NOT NULL
    "done":          0.90,   # status_category='done' AND resolved_at IS NULL
    "indeterminate": 0.75,
    "new":           0.65,
}

def assign_bucket(row: dict) -> Literal["latest", "historical", "stale_open"]:
    """CLAUDE.md §5 Step 2 semantics, verbatim.

    LATEST     — updated_at OR resolved_at within LATEST_DAYS
                 OR resolved_at IS NOT NULL AND comment_count >= 2 (substantive)
    STALE_OPEN — status_category in {new, indeterminate}
                 AND days_since(updated_at) > STALE_DAYS
    HISTORICAL — everything else
    """

def timeline_score(row: dict) -> float:
    """Continuous multiplier in ~[0.05, 1.0].

    days = days_since(max(updated_at, resolved_at))
    decay = 0.5 ** (days / HALFLIFE_DAYS)   # 1.0 today, 0.5 at half-life, → 0
    status = STATUS_WEIGHTS[_status_tier(row)]
    return max(decay * status, 0.05)        # floor prevents zero-scoring
    """

def apply_timeline(candidates: list[dict]) -> list[dict]:
    """Mutates each candidate in-place: attaches `bucket` and `timeline_score`.
    Re-sorts descending by `fused_score * timeline_score`.
    Returns the same list (for chaining).
    """

def bucket_counts(candidates: list[dict]) -> dict:
    return {"latest":     sum(1 for c in candidates if c["bucket"] == "latest"),
            "historical": sum(1 for c in candidates if c["bucket"] == "historical"),
            "stale_open": sum(1 for c in candidates if c["bucket"] == "stale_open")}
```

### 5.2 Changes to `hybrid.py`

Single-line addition at the end of `hybrid_search()`:

```python
fused = _rrf_fuse(per_sub)
fused = timeline.apply_timeline(fused)    # NEW
return fused[:limit]
```

The SQL is unchanged in Phase 1 — `hybrid.py` already returns `updated_at`,
`resolved_at`, `status_category` on each row. `apply_timeline` operates on the
Python dicts.

### 5.3 Changes to `gate.py`

Two additions:

1. `_bucket_penalty(scored) -> int` — returns the number of tiers to downgrade
   (0, 1, or 2). Rule: if top-3 all `historical` or all `stale_open` → 1 tier.
   If top-3 all `stale_open` → 2 tiers.
2. `bucket_counts` added to `diagnostics` dict via `timeline.bucket_counts([c for c,_ in scored])`.

Applied at the end of `apply()`, after the existing tier assignment:

```python
result = <existing logic>
penalty = _bucket_penalty(scored)
if penalty:
    result.confidence = _downgrade(result.confidence, penalty)
    result.message += f" (downgraded: top candidates are {top_bucket})"
```

### 5.4 LLM contract

The candidate dicts flowing through `gate.py → RetrievalResult.tickets` now
carry `bucket` and `timeline_score`. Callers upstream (`jira_retriever.py`,
`jira_tools.py`) pass these fields through unchanged. The tool result payload
consumed by `deep_system_prompt.py` therefore contains tagged tickets — the
template's Latest/Historical rendering logic gets structured input for the
first time.

No prompt-file change is required in Phase 1. The bucket vocabulary in
`deep_system_prompt.py` already matches `timeline.assign_bucket`'s return
values exactly.

> **Note on string casing:** Python enum values are `"latest" | "historical"
> | "stale_open"` (snake_case, code-idiomatic). The prompt template at
> `deep_system_prompt.py` lines 229–232 renders these as "Latest" /
> "Historical" / "Stale-open" (title case, hyphenated). The LLM handles both
> forms interchangeably — same pattern already in use for `status_category`
> (`"done"` in DB, "Done" / "Resolved" in prompt narrative). No transform
> layer needed.

### 5.5 Testing (Phase 1)

- `tests/retrieval/v2/test_timeline.py` — pure functions:
  - `assign_bucket` at 179d / 180d / 181d boundaries (both `updated_at` and
    `resolved_at` axes).
  - Substantive-resolution branch (resolved_at + comment_count ≥ 2 → LATEST
    regardless of age).
  - Stale-open branch (open status + no update in >180d).
  - `timeline_score` monotonicity: newer > older; done > indeterminate > new
    at identical age; floor at 0.05.
- `tests/retrieval/v2/test_hybrid.py` — extend:
  - Assert every returned row has `bucket` and `timeline_score`.
  - Assert sort order changes vs. raw RRF when candidates have differing dates.
- `tests/retrieval/v2/test_gate.py` — extend:
  - Bucket-mix penalty: three historical top-3 → tier downgrade.
  - `diagnostics.bucket_counts` populated.

### 5.6 Shadow logging (Phase 1)

`shadow.py` already logs v1 vs v2 outputs. Extension: also log `bucket_counts`
and `timeline_score_stats` so we can verify — before flipping traffic — that
timeline weighting doesn't erase relevant HISTORICAL tickets when they're the
correct answer.

### 5.7 Shippable alone

Phase 1 has no schema change, no reembed, no feature-flag beyond the existing
`CONWO_RETRIEVAL_V2`. One PR, land, monitor 1–2 days in shadow, done.

---

## 6. Phase 2 — Dual-vector comments (C, Variant b)

### 6.1 Migration `migrations/postgres/151_comments_embedding.sql`

```sql
ALTER TABLE tickets
    ADD COLUMN IF NOT EXISTS comments_embedding vector(768);

CREATE INDEX IF NOT EXISTS idx_tickets_comments_embedding
    ON tickets
    USING hnsw (comments_embedding vector_cosine_ops);
```

Idempotent. Safe to run before code deploy.

### 6.2 `scripts/embed_tickets.py` — extension

Add:

- `MAX_COMMENTS_CHARS = 8000` — larger than `MAX_TEXT_CHARS` because comments
  contain the answer for debugging queries, so we bias toward more context.
- `compose_comments_text(row) -> str` — trims `comments_text` to
  `MAX_COMMENTS_CHARS`. Returns empty string if `comments_text` is null/empty.
- Dual-embed loop: for each batch, call `embed_documents(texts)` once for
  descriptions, once for comments (both are batch calls — cost is per-char
  input, not per-request). Rows whose comments text is empty are omitted from
  the comments batch — their `comments_embedding` stays `NULL`.
- New CLI flag `--comments-only` — skips the main `embedding` column, only
  updates `comments_embedding`. Used for the one-shot post-migration backfill
  without needlessly re-embedding descriptions we already have.

Update SQL:

```sql
UPDATE tickets SET
    embedding          = COALESCE(%(desc_vec)s::vector, embedding),
    comments_embedding = COALESCE(%(comm_vec)s::vector, comments_embedding)
WHERE key = %(key)s
```

`COALESCE` ensures `--comments-only` runs don't clobber existing `embedding`.

### 6.3 `hybrid.py` — third RRF source

`_BASE_SQL` extended with a conditional `dense_c` CTE:

```sql
WITH lex AS (...),        -- unchanged
     dense AS (...),      -- unchanged: description embedding
     dense_c AS (         -- NEW, conditionally injected via .format
         SELECT key,
                1 - (comments_embedding <=> %(q_vec)s::vector) AS dense_c_score,
                ROW_NUMBER() OVER (ORDER BY comments_embedding <=> %(q_vec)s::vector) AS dense_c_rnk
         FROM tickets
         WHERE comments_embedding IS NOT NULL
         {filter_sql_dense_c}
         ORDER BY comments_embedding <=> %(q_vec)s::vector
         LIMIT 100
     ),
     fused AS (
         SELECT key, SUM(1.0 / (%(k)s + rnk)) AS rrf
         FROM (
             SELECT key, lex_rnk    AS rnk FROM lex
             UNION ALL SELECT key, dense_rnk   AS rnk FROM dense
             {union_dense_c}                                      -- NEW, conditional
         ) u
         GROUP BY key
     ) ...
```

Two `str.format` template slots (`dense_c AS (…)` and `UNION ALL … dense_c`)
are populated iff `os.getenv("CONWO_RETRIEVAL_V2_COMMENTS", "off") == "on"`.
When off, the emitted SQL is byte-identical to today's — no regression risk.

### 6.4 `rerank.py._doc_text()` — fixed-budget layout

```python
def _doc_text(c: dict) -> str:
    summary  = (c.get("summary")          or "").strip()[:200]
    desc     = (c.get("description_text") or "").strip()[:500]
    comments = (c.get("comments_text")    or "").strip()[:300]
    parts = [summary]
    if desc:     parts.append(desc)
    if comments: parts.append(f"[comments] {comments}")
    return "\n".join(parts)   # <= 1000 chars total, safe under MiniLM 256-token limit
```

Comments now feed the reranker unconditionally — including when Phase 2's
comments-flag is `off`. This is deliberate: even without the second embedding,
letting the reranker see comment text is a free accuracy lift. Ships alongside
Phase 2 code (not gated on the subflag) because `_doc_text` doesn't touch the
embedding column.

### 6.5 Feature flag: `CONWO_RETRIEVAL_V2_COMMENTS`

- Domain: `"off"` (default) | `"on"`
- Read by `hybrid.py` only. `_doc_text` change is unconditional.
- Independent from `CONWO_RETRIEVAL_V2` — you can run V2 without comments
  (safe fallback if backfill isn't complete), or V2 with comments (post-backfill).

### 6.6 Rollout order (each step reversible)

1. **PR #38** — Phase 1 (Section 5). Merge → deploy → 1–2 day shadow monitor.
2. **PR #39** — Phase 2 code + migration 151. Deploy with
   `CONWO_RETRIEVAL_V2_COMMENTS=off`. Column exists but unused.
3. **Backfill** — `python scripts/embed_tickets.py --comments-only`. Runs
   against production Postgres, ~$1–5 in Gemini cost at current ticket count.
   Idempotent — safe to re-run.
4. **PR #40** — Deploy config flip: `CONWO_RETRIEVAL_V2_COMMENTS=on` on the
   shadow instance. Shadow log now compares "v2 no-comments" vs "v2 with-comments".
5. **Activation** — After 3–5 days of shadow evidence showing lift and no
   regression, flip flag on serving instance.

Rollback at any step: revert env var → SQL reverts to today's shape → dead
column can be dropped in a later migration if desired.

### 6.7 Testing (Phase 2)

- `tests/retrieval/v2/test_embed_tickets.py` (extend):
  - Dual-embed path — both columns updated.
  - `--comments-only` — `embedding` untouched, `comments_embedding` written.
  - Empty comments_text — `comments_embedding` stays NULL.
- `tests/retrieval/v2/test_hybrid.py` (extend):
  - Flag off — emitted SQL byte-identical to Phase 1 baseline.
  - Flag on — three-stream RRF, tickets with NULL `comments_embedding` still
    surface via `lex` + `dense`.
  - Fusion math with a candidate that scores in only via comments.
- `tests/retrieval/v2/test_rerank.py` (extend):
  - `_doc_text` character budget (200/500/300).
  - Comments-only ticket (empty description) → still gets rendered.
  - No comments — no `[comments]` prefix emitted.

### 6.8 Error handling

- **Gemini quota trip mid-backfill:** script logs the last successful `key`
  and exits non-zero. Re-run picks up from the WHERE clause naturally
  (rows already updated have non-null `comments_embedding`; the script
  processes rows where either column is stale).
- **Malformed `comments_text` (e.g. binary):** `compose_comments_text` returns
  empty string, ticket's `comments_embedding` stays NULL. Same fail-open
  pattern as description handling today.
- **HNSW index bloat during backfill:** index update is incremental per
  `UPDATE`; no explicit REINDEX needed. If p99 write latency degrades during
  backfill, script's `--batch-size` flag (already exists for the main embed
  loop) throttles.

---

## 7. Deferred / open

- **Chunk-level indexing (Variant c)** — deferred. Reconsider if Phase 2
  shadow logs show comment-heavy queries still miss because comments were
  averaged into one vector. Would require a `ticket_chunks` table, chunk-level
  hybrid query, group-back-to-ticket dedup.
- **Bucket badge in frontend UI** — deferred. Backend surfaces `bucket` on
  every ticket in the API response; frontend can render at any time without
  further backend changes.
- **Bucket-aware sub-query weighting** — deferred. Currently all sub-queries
  from the rewriter contribute equally to fusion. A future refinement could
  weight sub-queries by whether they name a recency-sensitive concept (e.g.
  "current" vs "originally"), but this belongs in `rewrite.py`, not here.

## 8. Risks

- **Timeline weight suppresses correct HISTORICAL evidence.** Mitigation: the
  status-tier weight for `done_resolved = 1.00` is generous — resolved tickets
  never decay below decay-factor × 1.0. Only unresolved-open-and-stale drops
  hard. Shadow logs verify pre-flip.
- **Comments dilute rather than help.** Mitigation: dual-vector (not concat)
  keeps signals separate. Shadow log compares `top1_agreement` between v2 and
  v2-with-comments; regression → don't flip flag.
- **Backfill takes longer than expected.** Mitigation: `--comments-only` flag
  makes backfill re-runnable and interruptible. No hard dependency on when it
  finishes — activation flag is separate.
- **CLAUDE.md § 5 bucket definitions drift.** Mitigation: `assign_bucket` cites
  §5 Step 2 verbatim in its docstring. If §5 changes, this function is the
  single locus to update.

## 9. Success criteria

- Phase 1 shadow log shows ≥ 90% of user queries surface at least one LATEST
  ticket in top-3 when a LATEST candidate exists in the corpus (proxy for
  "we didn't accidentally suppress fresh evidence").
- Phase 2 shadow log shows ≥ 5% top-1 change rate on debugging-labeled
  queries (proxy for "comments retrieval is finding tickets that description-
  only retrieval missed"). Higher is better; regression → don't flip.
- No p99 `/query` latency regression > 100ms between v2 and v2-with-comments.
