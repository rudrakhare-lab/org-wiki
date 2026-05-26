# API Conwo vs Claude Code — Capability Audit

> Generated 2026-05-22 from Phase 1 (capability inventory) and Phase 2 (backend audit) of the parity investigation. Companion docs: `GAPS.md` (consolidated gap register), `PLAN.md` (closure plan), `../../eval/parity/` (30-question regression set).

---

## Methodology

Four parallel research agents read CLAUDE.md, `scripts/`, MCP configs, and `backend/` end-to-end. Where agents disagreed, I verified directly; corrections are inline.

- **Phase 1**: The capabilities Claude Code (CC) actually uses in this project. The baseline we audit against.
- **Phase 2**: For each Phase 1 row, the state of the API-based Conwo backend. Status: ✅ FULL / 🟡 PARTIAL / ❌ MISSING / ⚠️ DIFFERENT.

> **Inline correction:** Subagent C reported `scripts/pms_debug.py`, `scripts/audit_ingest.py`, and `docs/live-config-debug.md` as missing. Verified directly — all three files are present. Subagent B's "scripts not wrapped by backend" list missed Python-import wrappers (only checked subprocess invocations); corrected throughout.

---

# Phase 1: Capability Inventory (Claude Code Baseline)

## 1. Native Claude Code Tools

| Tool | Used? | Example invocations (file:line) | Frequency / criticality |
|------|-------|--------------------------------|------------------------|
| **Read** | YES — heavy | CLAUDE.md:546 ("Read `wiki/index.md`"); §8 Session Start (lines 836–842) reads 5 files unconditionally; INGEST §4 step 1 (line 462) reads entire source documents; LINT §6 (lines 764–780) reads all `wiki/modules/`, `wiki/log.md` | **Core.** Every workflow opens with Read. Files include PDFs, .docx (raw/), markdown (wiki/), SQLite (`raw/jira/tickets.sqlite`), TOML configs. |
| **Write** | YES — heavy | INGEST §4 steps 3–9 (lines 476–529): create `wiki/sources/<file>.md`, `wiki/entities/`, `wiki/modules/`, `wiki/cross-module/`, `wiki/decisions/` pages; updates `wiki/index.md`, `wiki/log.md`, `wiki/glossary.md` | **Core for INGEST.** Project ownership rule: line 22 "You **OWN** everything in `wiki/`". Never writes to `raw/` (line 21). |
| **Edit** | YES — heavy *(distinct from Write)* | §4 step 4 (line 488): "**If an entity page exists** → open it, add new fields"; step 5 (line 495): "**If a module page exists** → open it, update relevant sections"; log.md "NEVER edit existing entries. Only append." (line 449); `apply_feedback.py` appends Feedback Notes blocks between `<!-- BEGIN AUTO:* -->` idempotency markers (line 1010–1018); QUERY step 5 (line 638) saves answers by editing existing pages | **Core but distinct from Write.** Heavily used for in-place updates with bidirectional-link maintenance (line 536). The backend has no Edit equivalent — relevant for Phase 2. |
| **MultiEdit** | IMPLICIT | INGEST §4 step 6 (lines 500–504): cross-module connection requires updating BOTH module pages atomically + creating cross-module page; §7 line 536: bidirectional links must be updated on both endpoints in same operation | **Important.** CLAUDE.md doesn't name MultiEdit, but the bidirectional-link rule and cross-module updates assume atomic multi-file edits. Failure mode: half-updated link graph. |
| **Bash** | YES — heavy | sqlite3 queries (§9 line 878, §8 line 842); python script invocations (§5 step 2 line 584; §5 step 6 lines 657–699; §12 lines 1207–1234); `ls raw/modules/<slug>/` (line 484); env var exports (`PMS_TOKEN_COM`, lines 1194–1201) | **Core.** Categorized usage: (a) **sqlite3** for Jira aggregates and counts; (b) **python `scripts/*.py`** for sync, query helpers, PMS debug, feedback; (c) **ls** for filename verification; (d) **export** for credential setup in session. |
| **Glob** | IMPLICIT | LINT §6 check 2 (line 768): "find every page in `wiki/` … that has no inbound wikilinks" — requires globbing wiki/; INGEST §4 raw_path rule (line 484): `ls raw/modules/<slug>/` to enumerate files | **Used implicitly.** No direct Glob tool reference in CLAUDE.md; pattern matching happens through `ls` + bash globs or filesystem walks in `audit_ingest.py`. |
| **Grep** | IMPLICIT | LINT §6 check 4 (line 774): "scan for the same entity or concept described with different field names" — requires content search; check 1 (line 765): scan `depends_on` frontmatter across modules | **Used implicitly.** No direct Grep tool reference; in practice, the model uses bash `grep`/`rg` or reads files and searches by inspection. |
| **WebFetch** | NO direct use | No HTTP URLs fetched directly in CLAUDE.md workflows. External APIs (Jira, PMS) are reached via MCP server or python scripts that call them internally. | **Not used.** External I/O is mediated by MCP (Jira) or python scripts (PMS). The agent never directly fetches a URL. |
| **WebSearch** | NO | No web search references in CLAUDE.md or scripts. | **Not used.** Knowledge is closed-corpus (wiki + Jira + PMS only). |
| **Task / sub-agent dispatch** | NO direct use | No CLAUDE.md reference. Note: `.claude/settings.json` enables `superpowers@superpowers-marketplace` plugin which exposes sub-agent skills (brainstorming, executing-plans). Whether these are used in daily QUERY/INGEST workflows is unclear from CLAUDE.md alone. | **Not used in core workflows.** Superpowers skills available but not part of documented Conwo workflows. |
| **TodoWrite** | NO | No CLAUDE.md reference to task lists or planning persistence. Session Start checklist (§8 lines 836–852) is human-facing, not LLM-state. | **Not used.** Workflows are linear; no explicit plan-tracking primitive. |
| **NotebookEdit** | NO | No Jupyter notebooks in `raw/` or `wiki/`. | **Not used.** |

## 2. MCP Servers

| Server | Config | Tools exposed | Used by |
|--------|--------|---------------|---------|
| **atlassian** | `.mcp.json:2–16` | `mcp-atlassian` server via `uvx`, `READ_ONLY_MODE=true` env enforced (`.mcp.json:14`). Tools determined at runtime via MCP `tools/list`; CLAUDE.md §9 line 864–867 names 3 use cases: live single-ticket status, recently-created tickets not yet in SQLite mirror, single-ticket detail. | QUERY workflow when local SQLite mirror is stale or a specific ticket key is named (§9 lines 859–867). Enabled in `.claude/settings.local.json:2–4`. |

No other MCP servers configured.

## 3. CLAUDE.md Workflows → Tool Requirements

| Workflow | Lines | Required tools | Critical scripts invoked |
|----------|-------|---------------|--------------------------|
| **Session Start checklist** | §8, lines 833–855 | Read (×4 files), Bash (sqlite3 COUNT, audit_ingest.py, record_feedback.py summary) | `scripts/audit_ingest.py --skip-copies`, `scripts/record_feedback.py summary` |
| **INGEST** (9 steps, all mandatory) | §4, lines 457–537 | Read (source doc, existing wiki pages), Write (new pages), Edit (existing pages), Bash (`ls` for raw_path verification, line 484), MultiEdit (bidirectional-link maintenance, line 536) | `scripts/ingest_pms_configs.py` for PMS sheets |
| **QUERY** (6 steps, mandatory parallel wiki+Jira) | §5, lines 540–756 | Read (wiki pages, line 548), Bash (sqlite3 ranked query lines 560–579, or `query_jira_ranked.py` line 584), Bash (log_answer.py line 662, record_feedback.py line 685, apply_feedback.py lines 695–699), Write (save answer as wiki page, line 638) | `scripts/query_jira_ranked.py`, `scripts/log_answer.py`, `scripts/record_feedback.py`, `scripts/apply_feedback.py` |
| **LINT** (6 checks) | §6, lines 760–788 | Read (every page in wiki/), Grep (implicit content scans for contradictions), Glob (implicit page enumeration) | None |
| **Live Config Debug** (PMS) | §12, lines 1127–1301 | Bash (`pms_debug.py` invocations: `init`, `fetch`, `list-offices`, `list-criteria`, `report`, lines 1207–1238), env var setup (lines 1194–1201), MCP fallback for live ticket lookup | `scripts/pms_debug.py` (16,851 bytes; never wrapped by backend) |

## 4. Implicit Runtime Capabilities

| Capability | Evidenced in CLAUDE.md? | Citation | How this project depends on it |
|-----------|------------------------|----------|------------------------------|
| **Multi-step planning across many tool calls** | YES, evidenced | Every workflow is multi-step (§4: 9 steps, §5: 6 steps). QUERY §5 explicitly requires steps 1–4 ALL run before answering (line 543). | Workflows expect the agent to sequence tool calls and not short-circuit on partial results. |
| **Chunked file reads with view_range** | INFERRED | Not directly named, but CLAUDE.md itself is ~1,300 lines and the system prompt is built from extracted sections (§5/§9/§12) via regex (`backend/system_prompt.py:25–41`). Large source docs in `raw/` (PDFs, .docx) imply chunked reading. | Without it, large source ingest (PDFs, multi-MB xlsx) would fail. |
| **Self-interruption when something looks wrong** | NOT EVIDENCED in CLAUDE.md | No direct text. Indirect: §4 line 531 "Do NOT silently overwrite. Add `⚠️ Conflict` block… Ask the user for resolution"; §12 line 1183 "Do not guess the server or the level." | CLAUDE.md tells the model to ask the user, not how to self-interrupt mid-response. Runtime behavior — needs separate evaluation. |
| **Context compaction (long sessions)** | NOT EVIDENCED in CLAUDE.md | No direct text. Implicit: §3 line 449 "NEVER edit existing entries [in log.md]. Only append." — implies sessions can be long. | Runtime property of Claude Code; not codified in CLAUDE.md. |
| **Follow-up on partial tool failures** | PARTIALLY EVIDENCED | §5 line 604–605: "If the first keyword returns nothing, try synonyms… Do not stop after one failed query"; §5 line 607–608: "If Jira returns no relevant results after multiple attempts: explicitly state… do NOT silently omit" | Project explicitly depends on retry-with-alternative-strategy behavior for query workflows. |
| **Approval prompts for destructive ops** | YES, evidenced | INGEST §4 step 2 line 474: "Present this to the user and confirm before writing any wiki pages"; §5 step 6 line 695 `apply_feedback.py --dry-run` shown FIRST, then `--apply` only on confirmation; §12 line 1164 "explicitly confirm with the user" for server/service/BUID/level | Multiple workflows gate destructive operations on user confirmation. |
| **Streaming output user can read as it generates** | NOT EVIDENCED in CLAUDE.md | No direct text. Implicit user-facing assumption ("the user sees your reasoning unfold"). | Runtime property; needs separate evaluation against backend `/query/stream` endpoint. |
| **Large tool output handling (truncation + retrieval)** | PARTIALLY EVIDENCED | §5 step 4 line 738: "DO NOT enumerate ticket lists. Cite at most 5 ticket keys inline. For more, offer a SQL query the user can run" — defensive truncation by convention, but no Claude Code mechanism cited | Workflows manually bound output size; truncation+continuation mechanism is runtime-dependent. |
| **Sub-agent delegation for complex sub-tasks** | NOT EVIDENCED in CLAUDE.md | No direct text. `.claude/settings.json:5` enables `superpowers@superpowers-marketplace` plugin — gives the user (not the project) access to brainstorming, writing-plans, subagent-driven-development skills. | Not used in documented workflows. |

## 5. Behavioral Assumptions About the Runtime

| Assumption | Evidence |
|-----------|----------|
| Working directory persists across bash invocations | §8 line 842 chains `audit_ingest.py` and SQL queries assuming cwd; session files at `/tmp/pms_debug_*.json` (line 1240) survive between commands |
| Env vars persisted within session | §12 lines 1194–1201 export tokens once, used across multiple `pms_debug.py` invocations |
| User can be asked clarifying questions interactively | §12 line 1170 "Is this client hosted at cmsapp.moveinsync.com or cmsapp.moveinsync.in?"; §4 step 2 line 474 confirm-before-write |
| Single read of long files (no page-by-page) | §4 step 1 line 462 "Read the entire source document. Do not skim" |
| Tool outputs are visible to the user (not just the model) | §5 step 6 feedback loop assumes user has read the answer to score it |
| Append-only logs persist | §3 line 449 "NEVER edit existing entries. Only append" — assumes log.md visible across sessions |

## 6. Scripts Referenced in CLAUDE.md — Backend Wrapping Status

| Script | Referenced in CLAUDE.md | Backend wrapping | Status |
|--------|------------------------|------------------|--------|
| `audit_ingest.py` | §8 line 842 | `admin_api.py:71` subprocess | ✅ Wrapped |
| `apply_feedback.py` | §5 lines 695–699 | `admin_api.py:118,144` subprocess | ✅ Wrapped |
| `jira_sync.py` | §9 nightly cron | `admin_api.py:100` subprocess | ✅ Wrapped |
| `sync_drive.py` | §1 line 14 + Layer 3 | `admin_api.py:233` subprocess | ✅ Wrapped |
| `log_answer.py` | §5 lines 657–671 | `feedback_service.py:15` Python import | ✅ Wrapped (import) |
| `record_feedback.py` | §5 lines 685–691 | `feedback_service.py:16` Python import | ✅ Wrapped (import) |
| `query_jira_ranked.py` | §5 line 584 | `jira_retriever.py:19` Python import | ✅ Wrapped (import) |
| `pms_api_client.py` | §12 implied | `pms_tools.py:145` Python import | ✅ Wrapped (import) |
| `pms_session.py` | §12 implied | `pms_tools.py:192` Python import | ✅ Wrapped (import) |
| **`pms_debug.py`** | §12 lines 1127–1301 (entire workflow) | **None** | ❌ **NOT wrapped — interactive debugging workflow has no API equivalent** |
| **`ingest_pms_configs.py`** | §2i config-page generation | **None** | ❌ **NOT wrapped (wiki-editing path; backend is query-only)** |
| **`enrich_modules.py`** | §10 line 1010 | **None** | ❌ **NOT wrapped (stub)** |
| **`synthesize_patterns.py`** | §10 line 1010 | **None** | ❌ **NOT wrapped (stub)** |

---

# Phase 2: API Conwo Backend Audit

For each Phase 1 row, status with file citations and behavioral deltas.

## A. Native Claude Code Tools

| Tool | Status | Evidence | Behavioral delta | User-visible impact |
|------|--------|----------|-----------------|---------------------|
| **Read** | ❌ MISSING | Only `wiki_read_page` exists (`backend/tools/wiki_tools.py:88–110`) and it is scoped to `wiki/` with hard path-traversal guards. There is no tool to read `raw/`, `scripts/`, `config/`, `.env`, or arbitrary files. | Cannot read source PDFs, .docx, .xlsx in `raw/modules/`, cannot read `docs/sqlite-queries.md`, cannot inspect a config TOML or a script file. | A user asking "what does the booking-rule-engine doc actually say?" cannot be answered — the source is `raw/modules/booking-rule-engine/<doc>.pdf` and there is no tool to read it. The model can only quote what was previously ingested into `wiki/`. |
| **Write** | ❌ MISSING | No tool produces a new file anywhere. `wiki_propose_edit` (`wiki_tools.py:140–169`) appends a JSON record to `wiki_proposals.jsonl` — that is an admin queue entry, not a file. | The model cannot create `wiki/sources/<doc>.md`, `wiki/decisions/YYYY-MM-DD-<title>.md`, or any new wiki page. | The entire INGEST workflow (§4, lines 457–537) is unreachable from the API. A user asking "ingest this PDF" gets nothing. |
| **Edit** | ❌ MISSING | No tool modifies an existing file. `wiki_propose_edit` creates a proposal record; admin endpoints `/admin/wiki/proposals/{id}/apply` mark a proposal "applied" but do NOT actually edit the wiki — that is documented in code as the admin's manual responsibility (`admin_api.py:189–194`). | Cannot append to `wiki/log.md`, cannot add fields to existing entity pages, cannot maintain the `<!-- BEGIN AUTO:* -->` marker blocks, cannot apply `apply_feedback.py` patches in-tool. Backend has `apply_feedback.py` wrapped via subprocess (`admin_api.py:144`) but it is an admin-only HTTP endpoint, not a tool the agent can call mid-answer. | A user asking the agent to "save this answer as a wiki page" — required by §5 step 5 line 638 — fails silently. |
| **MultiEdit** | ❌ MISSING | No atomic multi-file primitive exists. Even if `Edit` existed, bidirectional-link maintenance (§7 line 536) would have no transactional support. | Bidirectional-link rule from CLAUDE.md cannot be enforced by the API. | INGEST and LINT consequences both downstream of Edit/MultiEdit being absent. |
| **Bash** | ❌ MISSING (by design) | No general shell tool in `backend/tools/`. The only `subprocess.run` calls live in `backend/admin_api.py` (4 wrapped scripts) and are invoked only by admin HTTP endpoints — the agent itself cannot reach them. | Cannot run `sqlite3 raw/jira/tickets.sqlite "SELECT ..."` ad-hoc. Cannot `ls raw/modules/<slug>/` to verify a filename for INGEST §4 line 484. Cannot `export PMS_TOKEN_COM=...` mid-session as §12 lines 1194–1201 require. Cannot run an arbitrary script the user authored. | A power-user query like "how many open P0 tickets in WP-admin updated last week?" needs a custom SQL query. Backend has `jira_named_query` with 4 whitelisted templates (`jira_tools.py:39–71`) — `open_by_priority` is one of them, but cross-cutting filters (functional_area + priority + recency) are not in the whitelist. The agent has no escape hatch. |
| **Glob** | ❌ MISSING | No filesystem enumeration tool. `wiki_retriever` builds an in-memory index of wiki pages at startup — the model cannot enumerate it. | Cannot find "every page in `wiki/modules/`" or "every page with `status: stub` frontmatter". | LINT check 5 ("List all pages where frontmatter contains `status: stub`") is unreachable. |
| **Grep** | 🟡 PARTIAL | `wiki_search` (`wiki_tools.py:69–85`) does keyword search via `wiki_retriever.search()` — but it returns 300-char excerpts (`wiki_tools.py:80`), is scoped to `wiki/`, and ranks by an opaque retrieval scorer rather than literal grep semantics. There is no equivalent for `raw/`, `scripts/`, or `config/`. | Cannot do "find every wiki page that mentions `kioskRequireOTPBeforeRegister`" with deterministic match semantics. Cannot grep frontmatter for contradictions (LINT check 4). | A precision-sensitive question ("which pages cite TS-12345?") is at the mercy of retriever ranking; the model can't guarantee completeness. |
| **WebFetch** | ❌ MISSING (consistent with CLAUDE.md) | No URL-fetch tool. PMS APIs are reached through `pms_default_properties` and `pms_runtime_values`, both whitelisted to specific endpoints. | Consistent with CC usage — no new gap. | None. |
| **WebSearch** | ❌ MISSING (consistent) | — | Consistent with CC usage. | None. |
| **Task / sub-agent** | ❌ MISSING (consistent in core workflows) | No sub-agent tool. `backend/providers/deep_query.py:64–149` runs one linear tool loop. | Consistent with documented CC workflows. Superpowers skills not exposed either way. | None for documented use cases. |
| **TodoWrite** | ❌ MISSING (consistent) | No task-list persistence. Conversation history is the only state. | Consistent with CC usage. | None for documented workflows. |
| **NotebookEdit** | ❌ MISSING (consistent) | — | Consistent. | None. |

## B. MCP Servers

| Server | Status | Evidence | Behavioral delta | User-visible impact |
|--------|--------|----------|-----------------|---------------------|
| **atlassian MCP** | ❌ MISSING | Backend has Jira tools (`jira_search_ranked`, `jira_get_ticket`, `jira_named_query`) but all query the local SQLite mirror at `raw/jira/tickets.sqlite`. The mirror is refreshed only when `jira_sync.py --incremental` runs — `deploy/crontab.example:8` schedules this daily at 02:00 UTC; admin can also trigger via `/admin/trigger-sync` (`admin_api.py:97–108`). No equivalent of the live MCP fetch. | CLAUDE.md §9 lines 864–867 names three use cases for the MCP path: (a) live status of a specific ticket, (b) recently-created tickets not yet in mirror, (c) single-ticket detail not in mirror. The API can answer (a) and (c) only for tickets already mirrored. Use case (b) — recently created tickets, e.g. one filed an hour ago — is unreachable for up to 24 hours. | "What's the status of TS-99999, just filed?" — if the ticket was created after the last 02:00 UTC sync, the agent returns "ticket not found." User has to wait for the next sync window or ask an admin to manually trigger one via `/admin/trigger-sync`. |

## C. CLAUDE.md Workflows

| Workflow | Status | Per-step detail |
|----------|--------|------------------|
| **Session Start checklist** | ❌ MISSING | The four admin endpoints (`/admin/sync-status`, `/admin/ingest-queue`, `/admin/feedback`, `/admin/wiki/proposals`) exist but are HTTP-only and never auto-invoked. The agent system prompt does not surface their results. `deep_system_prompt.py` does not mention session-start posture (sync timestamps, pending feedback, uningested files). |
| **INGEST (§4, 9 steps)** | ❌ MISSING | The 9 steps require Read (raw/), Write (wiki/), Edit (wiki/, log.md, index.md, glossary.md), and discussion gating. The backend has none of these. `deep_system_prompt.py` (lines 11–91) does not mention ingest at all. |
| **QUERY (§5, 6 steps)** | 🟡 PARTIAL | The orchestrator's `run_deep()` (`orchestrator.py:107–215`) implements a deterministic preflight + tool loop. Per-step status: Step 1 (Read wiki) ✅; Step 2 (Jira search) ✅; Step 3 (Conflict & evolution detection) ✅ (prompt-only); Step 4 (Synthesis with structured format) ✅; Step 5 (Save or log) ❌ — "save as wiki page" needs Write; Step 6 (Log + feedback loop) 🟡 — `log_answer()` is called automatically but the user-facing prompt "**Answer ID:** `<id>`" is not in `deep_system_prompt.py:54–76`. |
| **LINT (§6, 6 checks)** | ❌ MISSING | No tools for cross-page link auditing, orphan detection, contradiction scanning, or stale-page detection. |
| **Live Config Debug (§12)** | 🟡 PARTIAL | `pms_default_properties` and `pms_runtime_values` (`pms_tools.py`) implement the underlying API calls. Specific deltas: (a) **disambiguation flow broken** — §12 lines 1158–1183 require asking user to confirm server, service, BUID, level BEFORE fetching; (b) **session state absent** — `/tmp/pms_debug_*.json` cache has no equivalent; (c) **`list-offices`, `list-criteria`, `show-session`, `diagnose`, `report`, `compare` subcommands have no API tool equivalents**. |

## D. Implicit Runtime Capabilities

| Capability | Status | Behavioral delta |
|-----------|--------|------------------|
| **Multi-step planning** | 🟡 PARTIAL | `deep_query.py:78` caps at `_MAX_ROUNDS_ABSOLUTE = 8`; `deep_query.py:127–137` forces synthesis on the 8th round. CC has no hard cap. |
| **Chunked file reads (view_range)** | ❌ MISSING | `wiki_read_page` returns full `page.full_text` (`wiki_tools.py:88–110`); no `offset`/`limit`. |
| **Self-interruption** | ❌ MISSING | `deep_query.py:81–138` runs the loop to completion; no cancellation primitive. The Anthropic SDK call (`messages.create`) is blocking. |
| **Context compaction** | ❌ MISSING | `_load_conversation_context()` (`orchestrator.py:31–55`) loads last 6 turns (max 12 messages) and stops. No summarization of older turns. |
| **Follow-up on partial failures** | 🟡 PARTIAL | Tools return structured error dicts (e.g. `{"error": "...", "code": "credentials_required"}`); the model can choose to call an alternative tool. Prompt-driven, not enforced. |
| **Approval prompts for destructive ops** | ❌ MISSING (in query path) | The query path does not gate anything mid-flow. Admin endpoints exist for post-hoc proposal approval. |
| **Streaming output** | 🟡 PARTIAL | `/query/stream` exists (`api.py:403–486`) but only proxies the `mode="claude-code"` subprocess via `stream_claude_code()`. For `mode="api"`, `deep_query.py:84` calls `messages.create()` non-streaming. |
| **Large tool output handling** | 🟡 PARTIAL | Tools truncate at fixed limits: `jira_get_ticket` description and comments capped at 2000 chars (`jira_tools.py:250–251`); `wiki_search` excerpts at 300 chars (`wiki_tools.py:80`); `config_lookup` at 300 chars. No continuation/pagination primitive. |
| **Sub-agent delegation** | ❌ MISSING | No equivalent of CC's Task tool. |

## E. Behavioral Assumptions

| Assumption | Status | Evidence |
|-----------|--------|----------|
| Working directory persists | ⚠️ DIFFERENT | All tool calls are stateless; there is no per-session cwd. Not applicable — no Bash tool to depend on it. |
| Env vars persist across calls | ✅ | `pms_tools.py:108–117` reads `os.getenv("PMS_TOKEN_COM")` etc. on each call; env is process-level, set at FastAPI startup. |
| Conversational clarifying questions | ❌ | `/query` is request-response; one Q in, one A out. No turn-level "I need to ask you" primitive. |
| Single-read of long files | N/A | wiki_read_page returns full text; not paged. OK at current scale. |
| Tool outputs visible to user | ⚠️ DIFFERENT | `OrchestratorResult.tool_trace` is returned in the API response but it's not surfaced in the answer text. |
| Append-only logs persist | ✅ | `conversation_store` SQLite at `raw/conversations/`; `log_answer.py` writes to `raw/feedback/answer_log.jsonl`. |

## F. Quantified Coverage Summary

| Category | Rows | ✅ FULL | 🟡 PARTIAL | ❌ MISSING | ⚠️ DIFFERENT |
|----------|------|---------|-----------|-----------|-------------|
| Native CC tools | 12 | 0 | 1 (Grep) | 11 | 0 |
| MCP servers | 1 | 0 | 0 | 1 | 0 |
| CLAUDE.md workflows | 5 | 0 | 2 (QUERY, Live Config Debug) | 3 (Session Start, INGEST, LINT) | 0 |
| QUERY sub-steps | 6 | 4 | 1 (Step 6) | 1 (Step 5) | 0 |
| Implicit capabilities | 9 | 0 | 4 | 5 | 0 |
| Behavioral assumptions | 6 | 2 | 0 | 1 | 3 |
| **Overall (39 rows)** | **39** | **6 (15%)** | **8 (21%)** | **22 (56%)** | **3 (8%)** |

**Honest reading:** the API backend covers ~36% of Claude Code capability (full or partial), 56% is straight-up missing, 8% behaves differently in ways a user would notice. The bulk of the gap is in **wiki-editing** (Write/Edit/INGEST/LINT) and **runtime UX** (streaming/compaction/large-output handling). The **query path itself** — the workflow you ship to internal users — is in better shape (4/6 steps ✅, the remaining 2 partial).
