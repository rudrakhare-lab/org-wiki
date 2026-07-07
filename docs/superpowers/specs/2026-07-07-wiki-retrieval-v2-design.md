# Wiki Retrieval V2 — Hybrid Semantic + Graph + Intent-Aware Retrieval

**Date:** 2026-07-07
**Status:** Approved design, pending implementation plan
**Owner:** Conwo retrieval
**Predecessors:** Jira Retrieval V2 (`2026-07-02-retrieval-v2-timeline-and-comments-design.md`), the three-agent AI-pipeline audit (2026-07-06/07, this session), and the GraphRAG architecture evaluation (Gemini-conversation review).

---

## 1. Problem

Wiki retrieval is the least sophisticated retrieval path in the system, while the wiki itself is the most curated knowledge source:

1. **No semantic layer.** `backend/wiki_retriever.py` is a TF-weighted keyword index (`"No embeddings needed for Phase 1"` — still Phase 1). Vocabulary mismatch = silent miss: "OTP" never finds "one-time passcode". The Jira pillar got hybrid+embeddings+rerank (v2); the wiki never did.
2. **The knowledge graph is decoration.** 2,550 `[[wikilinks]]` + typed frontmatter relations (`depends_on`/`used_by`) exist, but nothing in retrieval walks an edge. `wiki_graph_api.py` builds nodes/edges solely to draw the frontend force-graph. The deep prompt *tells the model* to follow wikilinks and hopes.
3. **Broken ranking math.** `idf = 1/(1+df)` is not IDF; tokenizer drops all digits (`2FA`, numeric values unmatchable); no stemming; no phrases; `tf/len` penalizes thorough pages; config boost is a hardcoded `+2.0` + substring-matching service slugs.
4. **Dumb excerpts.** The seed shows the *first* 800 chars of a page with all headings stripped — not the section that matched.
5. **Intent barely matters.** The intent classifier only changes *how many* pages to fetch, never ranking, matching, or assembly.
6. **Duplicated graph logic.** `preflight.py:163-198` hand-walks frontmatter relations for related-module Jira fetch; `wiki_graph_api.py` re-extracts edges separately. Two implementations, zero shared with retrieval.

**Product context that shapes this design:** the majority of user queries concern PMS configs — property definitions, defaults, `.in`/`.com` differences, and multi-level config-on-config dependencies. The PMS pillar (config SQLite KB ~1,800 properties + live `pms_*` tools + `configs/` wiki pages) is a first-class citizen of this design, not a bystander.

## 2. Goals

- **Recall + relations:** retrieve *everything* relevant — matching sections, their config pages, dependency-connected modules, governing decisions — via semantic search plus graph traversal.
- **Precision by intent:** answer *exactly* what was asked; intent shapes ranking boosts and answer assembly.
- **Audit-level traceability:** every retrieval unit carries a section-level anchor; every cited source is mechanically verified against what was actually retrieved.
- **Zero new infrastructure. Zero devops asks.** pgvector + Postgres + in-process Python only. Flag defaults ON in code; env var is a kill switch.

## 3. Non-goals (explicitly rejected)

| Rejected | Why |
|---|---|
| Neo4j / any graph database | 159 nodes / ~2,550 edges fits in a Python dict; 1–2-hop traversal in microseconds; a graph DB adds a service, a sync pipeline, and licensing for zero capability at this scale. Revisit at >10k densely-linked nodes or 4+ hop analytics. |
| Qdrant / Milvus | pgvector already deployed, already serving Jira v2, headroom to ~1M vectors. |
| Kafka / Ray ingestion tiers | Ingestion is batch, hundreds of docs. |
| ColPaLI / visual multi-vectors | Retrieval-time visual matching exceeds the CPU budget (see reranker history); text-at-ingest via Claude Vision already handles scanned content. |
| LLM entity/graph extraction (Microsoft GraphRAG style) | The human-curated graph is higher quality than extraction would produce. Extraction would degrade it. |
| Any reranker larger than MiniLM (e.g. BGE-Large) | A 568M reranker already took production down (exit 137, PR #38 era). MiniLM (22M) stays, shared instance. |
| Bi-temporal graph (full Graphiti) | The `history/` release-notes layer is the time axis; right-sized temporal handling per §5.10. |

## 4. Architecture overview

```
USER QUERY
   │
   ▼
[0] Guardrail (regex, fail-open)
   ▼
[1] SHARED REWRITE + INTENT (hoisted to preflight top — one Haiku call, all outputs used)
      sub-queries • synonym expansions • filters • LLM intent (second opinion)
      + regex intent classifier → combined verdict (soft-routing only)
   ▼
[2] PREFLIGHT — PUSH layer (parallel branches, each fails open with a visible note)
   ├─► WIKI V2 (new): hybrid chunk search (tsvector+pgvector, RRF across sub-queries)
   │     → graph expand (1 hop; 2 for ARCHITECTURAL; edge-priority + neighbor cap)
   │     → shared MiniLM rerank (sigmoid-calibrated) → intent-shaped selection
   ├─► JIRA V2 (existing): hybrid (BM25+desc+comments vectors) → links → rerank → gate
   ├─► CONFIG KB (new branch): named/described property → catalog row + dependency
   │     chain (1–2 levels transitive) pushed with anchors into configs/ pages
   └─► MODULE-TAGGED TICKETS: via wiki_graph (replaces hand-rolled frontmatter walk)
   ▼
[3] SEED ASSEMBLY — global token budget (~6k), intent-driven eviction, trim-note
      listing every matched-but-trimmed anchor/ticket key
   ▼
[4] DEEP LOOP (PULL layer, unchanged): model calls tools; wiki_search tool now
      runs the v2 engine; all wiki tool results carry anchors
   ▼
[5] SYNTHESIS — intent-shaped answer template (existing contract)
   ▼
[6] POST — inline mechanical anchor verification (gates confidence, no LLM)
      • async quality judge (telemetry/retro-flag only, never a gate)
      • answer_id logging • full lineage in traces
```

**Hop budget:** wiki graph 1 hop default / 2 for ARCHITECTURAL (hard cap 2); Jira links 1 hop (unchanged); config dependencies 1–2 levels transitive; LLM tool rounds ≤12 (existing cap).

## 5. Components

### 5.1 Migration `170_wiki_chunks.sql`

```sql
CREATE TABLE IF NOT EXISTS wiki_chunks (
  id             BIGSERIAL PRIMARY KEY,
  agent_id       TEXT NOT NULL,              -- multi-agent isolation (conwo, infosec, …)
  page_path      TEXT NOT NULL,              -- "modules/desk-management.md"
  section_anchor TEXT NOT NULL,              -- "api-endpoints" (heading slug; "" = preamble)
  section_title  TEXT NOT NULL DEFAULT '',
  page_type      TEXT NOT NULL DEFAULT '',   -- module|config|runbook|decision|concept|entity|history|…
  chunk_index    INT  NOT NULL DEFAULT 0,    -- ordinal within section (row-group splits)
  chunk_text     TEXT NOT NULL,
  last_updated   TEXT,                       -- from frontmatter (TEXT — matches repo date convention)
  content_hash   TEXT NOT NULL,              -- page-level hash for delta re-embed
  embedding      vector(768),
  search_tsv     tsvector GENERATED ALWAYS AS (to_tsvector('english', chunk_text)) STORED
);
CREATE INDEX IF NOT EXISTS idx_wiki_chunks_embedding ON wiki_chunks
  USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);
CREATE INDEX IF NOT EXISTS idx_wiki_chunks_tsv   ON wiki_chunks USING gin (search_tsv);
CREATE INDEX IF NOT EXISTS idx_wiki_chunks_page  ON wiki_chunks (agent_id, page_path);
```

Idempotent, nullable embedding, safe to deploy ahead of code (same discipline as migration 151). Every query against this table filters `agent_id`.

### 5.2 Chunker + `scripts/embed_wiki.py`

**Chunking rules:**
- Split at `##` headings (the CLAUDE.md page schema guarantees meaningful section boundaries). Page preamble (title + overview before first `##`) is its own chunk.
- Target ≤ ~1,200 chars/chunk. Oversized prose sections split at paragraph boundaries (`chunk_index` increments).
- **Markdown tables (config comparison tables): row-group chunking** — split every ~15 rows, **repeating the header row in every slice** so each chunk is self-describing and every property row stays individually retrievable. Never split mid-row.
- Each chunk is embedded with contextual prefix: `"{page_title} — {section_title}\n{chunk_text}"` (title carries signal for both embedding and rerank).
- Anchors derived from heading slugs (kebab-case, GitHub-style), stable across re-embeds.

**Script:** mirrors `embed_tickets.py` conventions — `--mode full|delta`, batching, resumable. Delta mode re-embeds only pages whose `content_hash` changed (delete + reinsert that page's chunks atomically). Reuses `backend/retrieval/v2/embed.py` (Gemini `gemini-embedding-001`, doc/query task types). Empty/whitespace chunks are skipped, never embedded.

**Sync triggers:** every wiki write path that calls `wiki_retriever.rebuild_index()` also enqueues a delta re-embed for the touched pages (background, non-blocking; a failed embed leaves old chunks in place — stale beats missing). Nightly full-delta pass as backstop.

### 5.3 `backend/wiki_graph.py` — one graph, three consumers

In-memory typed multigraph, built at startup + rebuilt on wiki writes (same triggers as index rebuild). Per-agent, keyed like `wiki_retriever._INDICES`.

**Edge extraction (all from existing content — nothing new to author):**
| Edge type | Source | Weight class |
|---|---|---|
| `depends_on` / `used_by` | module frontmatter | curated (highest) |
| `config_of` | `configs/X.md` ↔ `modules/X.md` + config page `module:` frontmatter | structural |
| `runbook_of` | runbook `module:`/`modules:` frontmatter | structural |
| `decision_for` | decision `modules:` frontmatter | structural |
| `wikilink` | `[[...]]` body links | generic (lowest) |

**Consumers:**
1. `retrieval/wiki_v2.py` — expansion (below).
2. `wiki_graph_api.py` — rewired to consume this module (stops re-extracting; UI unchanged).
3. `preflight.py` related-module Jira fetch — rewired to `wiki_graph.neighbors(slug, types=("depends_on","used_by"))`, deleting the hand-rolled frontmatter walk.

### 5.4 `backend/retrieval/wiki_v2.py` — the pipeline

```
search(question, rewrite_result, intent, agent_id, budget) -> WikiRetrievalResult
```

1. **Hybrid chunk search:** for each sub-query (from the shared rewrite; fallback `[question]`): tsvector match (websearch_to_tsquery, expansions appended as OR-terms) + pgvector cosine (query embedded once per sub-query), each LIMIT 50, fused via RRF (k=60) in Python across all sub-queries. Named-param SQL, `agent_id` filtered. Emitted SQL follows hybrid.py conventions.
2. **Graph expansion (the leash — hard requirements):**
   - Expand from the distinct *pages* of the top-10 fused chunks.
   - Depth 1 (depth 2 only when combined intent = ARCHITECTURAL).
   - **Edge-priority order:** curated → structural → wikilink. Wikilink edges only if the neighbor budget remains.
   - **Neighbor cap: 6 pages total.** For each neighbor, fetch only its single best chunk vs. the query (one pgvector lookup per neighbor page).
   - Every expanded chunk is tagged `related_via: "<from_page> —<edge_type>→ <to_page>"`. Expanded chunks are **never** presented as direct hits.
3. **Rerank:** shared MiniLM instance scores (question, chunk_text-with-title) pairs — direct + expanded together, so weak related chunks sink. **Prerequisite fix, in scope:** `rerank.predict` gains `activation_fn=Sigmoid` (or equivalent) so scores are [0,1]; the gate thresholds (0.5/0.7) become meaningful. Regression test asserts score range on known relevant/irrelevant pairs.
4. **Intent-shaped selection:** boosts (never filters — §5.5): CONFIGURATION → `page_type=config` ×boost, config-table chunks preferred whole; HOW_TO → `runbook` ×boost; DEFINITION → tighten to best page + its `config_of` neighbor only; ARCHITECTURAL → include `cross-module` pages, keep edge tags in output; temporal (§5.10). Output: ranked chunks with anchors, scores, `related_via` tags, capped by the seed budget share.

**Kill switch:** `CONWO_WIKI_RETRIEVAL_V2` — default **"on" in code**, env var set to `off` reverts `preflight` + `wiki_search` tool to `WikiIndex.search()` instantly (same pattern as `CONWO_RETRIEVAL_V2_COMMENTS`). Empty `wiki_chunks` table (pre-backfill) auto-degrades to the keyword path with a seed note.

### 5.5 Intent hardening

- **Combined verdict:** regex classifier + the rewriter's LLM intent (currently computed and discarded — now used). Agreement → proceed; disagreement or low regex margin → prefer LLM intent; both weak → GENERAL (broad retrieval).
- **Deterministic tie-break** in the regex classifier (fixed priority list) — fixes the dict-insertion-order bug.
- **Soft routing invariant (spec-level rule):** intent adjusts *weights and budgets only*. No intent value may exclude a page type from retrieval. A wrong intent degrades ranking, never recall.

### 5.6 Config KB preflight branch (the PMS pillar, strengthened)

Trigger: query names a config property (backticked token, camelCase token, or trigram match against the ~1,800-property catalog).

Push into the seed: property description, data type, default, server presence (`.in`/`.com`), `criteria_priority_list`, owning service, **and the dependency chain 1–2 levels transitive** (from the config KB's dependent-configs data; push what exists, never fabricate) — each item anchored to its `configs/<service>.md` page/section.

**Boundary (deliberate):** live PMS *values* remain pull-only via `pms_*` tools — fetching them requires `.in`/`.com` + BUID disambiguation (CLAUDE.md §12: guessing the server produces false negatives). Defaults and dependencies are pushed; live values stay a deliberate, disambiguated tool step. No existing PMS tool, workflow, or rule changes.

### 5.7 Seed assembly — budget, eviction, visible degradation

- **Global seed evidence budget: ~6,000 tokens** (tunable constant), covering wiki sections + Jira buckets + module-tagged tickets + config block + full ticket bodies.
- **Eviction is rank-ordered within intent-driven priorities** (drop lowest-ranked, `related_via`-tagged items first; never direct top hits):
  - CONFIGURATION/DEBUGGING/STATUS: protect config block + Jira evidence; evict wiki prose first.
  - HOW_TO: protect runbook sections; evict Jira historical first.
  - DEFINITION/ARCHITECTURAL: protect wiki; trim Jira to LATEST summaries.
- **Trim-note (mandatory):** the seed ends with an explicit list of every matched-but-trimmed item (`anchors`, ticket keys) + the tool to fetch each — trimmed means demoted to pull, never hidden.
- **Fail-open with visible note (every branch):** Gemini embed down → wiki falls back to keyword path, seed says so; rewriter API failure → `RewriteResult([question])` fallback (fixing the current crash path) + note; Jira degraded → note + confidence capped at Medium. No silent degradation.

### 5.8 The Anchor Strategy

Every chunk carries `page_path#section_anchor`. Anchors flow end-to-end: seed rendering → `wiki_search`/`wiki_read_page` tool results → model citations → answer Sources. Citations become section-precise and mechanically checkable. (Jira side already has this via ticket keys.)

### 5.9 No Source, No Fact — right-sized enforcement

| Layer | When | Mechanism | Power |
|---|---|---|---|
| **Inline anchor verification** | before response ships | set-membership: every anchor/ticket key cited in the answer must ∈ retrieved-this-query set; cited-but-not-retrieved ⇒ flagged + confidence capped at Medium + ⚠️ line; uncited-but-retrieved logged | **gates** (no LLM, ~0ms) |
| **Sources honesty** | at response assembly | `QueryResponse.sources` derived from anchors/keys present in the answer text — replaces the greedy-regex scrape (`_extract_pms_configs`) and the bucket-dump (`_trace_jira_keys`); confidence defaults to `Unknown` (no badge) when the model omits it, never fabricated "Medium" | trust display |
| **Async quality judge** | after response (existing BackgroundTask) | unchanged run; groundedness feeds dashboard, eval set, retro-flags. Explicitly **not** a gate (timing makes that impossible) | telemetry |

### 5.10 Temporal awareness (Graphiti steal, right-sized)

- Chunks carry `last_updated` + `page_type`.
- **Temporal intent** (patterns: "when did… change", "what was… before", "history of…", release-note references) → boost `history/` + dated `decisions/` chunks, order by date.
- **Current-state intents** → downrank (never exclude) `history/` chunks — codifying CLAUDE.md §5's "release notes are a dated changelog, not current truth" into ranking instead of prompt-hoping.
- No bi-temporal store; the `history/` layer is the time axis.

## 6. Per-intent behavior (retrieval → answer shape)

| Intent | Retrieval | Answer |
|---|---|---|
| CONFIGURATION | config chunks boosted; table row-groups; config KB block + dependency chain pushed; `config_of` context | Property table + `> ⚠️ related configs` |
| DEBUGGING | as CONFIGURATION + Jira deep; BUID present ⇒ model directed to live `pms_*` chain | failure-mode checklist; live value table; fix |
| HOW_TO | runbook boost; module 1-hop | numbered steps + ⚠️ caveats |
| DEFINITION | precision mode: best page + config_of only | 2–5 sentence prose |
| ARCHITECTURAL | 2-hop, cross-module pages, edges cited | ASCII diagram + narrative |
| COMPARISON | both subjects symmetric; tables whole | side-by-side table |
| Temporal | history/decisions boosted, date-ordered | timeline narrative |
| STATUS/GENERAL | Jira-dominant, wiki light | short prose |
| Weak evidence | gate abstains (post-sigmoid) | "couldn't find strong evidence; closest: X, Y — verify" |

## 7. Golden eval set (pre-merge gate)

~40 real questions sampled from the answer log (`scripts/log_answer.py` data) with known correct wiki pages/sections. Harness runs old vs new retriever: recall@5 (page-level), MRR, and section-hit rate. **New pipeline must beat the keyword baseline on recall@5 without degrading precision** before the flag ships default-on. The set becomes the permanent regression harness for future retrieval changes.

## 8. What becomes dormant/deleted

- `WikiIndex.search()` TF ranking → kill-switch path only (index itself stays: `get_page`, `wiki_grep`, `wiki_list_pages`, `all_paths`).
- `_mentioned_services` / `_SERVICE_SLUGS` boost hack → deleted (replaced by `config_of` edges + intent boosts).
- `WikiPage.excerpt()` in the seed path → replaced by anchored sections.
- `preflight.py` hand-rolled related-module frontmatter walk → replaced by `wiki_graph`.
- `wiki_graph_api._extract_links` duplication → consumes `wiki_graph`.
- Rewriter's discarded outputs (`expansions`, `intent`) → now consumed (dead-code finding resolved by use, not deletion).

## 9. Testing discipline

- **Prod-realistic fixtures mandatory** (session policy, from the July outages): ISO-string dates, `Decimal` scores where SQL rows are simulated, minimal-column row shapes for every consumer.
- TDD per component; RRF/chunker/graph/verification are pure functions with direct unit tests.
- Reranker sigmoid: range-assertion test (relevant pair > 0.7, irrelevant < 0.5 post-activation).
- Chunker: golden tests on real wiki pages (module page, 49-property config page with row-group splits, runbook).
- Graph: edge extraction tests against real frontmatter; leash tests (cap, priority order, tag presence).
- Failure-mode tests: embed API down → keyword fallback + note; empty chunks table → fallback; rewrite API down → `[question]` fallback.

## 10. Rollout

1. Merge (flag default-on in code; empty table ⇒ auto-degrade to keyword path — zero behavior change until backfill).
2. Deploy — migration 170 auto-applies (nullable col + indexes on empty table: instant).
3. Run `scripts/embed_wiki.py --mode full` (one-time backfill, ~1,500 chunks, minutes).
4. Wiki v2 activates as chunks appear. Kill switch: `CONWO_WIKI_RETRIEVAL_V2=off`.
5. Eval-set comparison recorded in the PR before merge (step 1 gate).

## 11. Out of scope (tracked separately)

Streaming api-mode, prompt caching, LLM-call timeouts, `get_conversation` LIMIT, injection-hardening prompt rule, evolution-hints restore in Jira v2 markdown, `temperature=0` on judge/compactor — all on the audit master fix list, independent of this project.
