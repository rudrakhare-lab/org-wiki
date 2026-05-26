# Gap Closure Plan

> Generated 2026-05-22 from Phase 4 of the parity investigation. Companion docs: `AUDIT.md` (full capability audit), `GAPS.md` (consolidated gap register).

## Decisions Log

> Date: 2026-05-22. All three architectural decisions resolved.

| ID | Decision | Resolution |
|----|----------|------------|
| **D1** | Is the API supposed to edit `wiki/`? | **✅ YES** — wiki editing is in scope. Track A (next batch after Track C) will design + ship the wiki-edit tool family. Closes G07, G14, G16 once implemented. |
| **D2** | Should `mode="api"` stream tokens? | **✅ YES** — streaming is in scope. **Gated on API key arrival.** Track B parked until then. G02 stays open but flagged as in-scope. |
| **D3** | Are INGEST/LINT in scope for the API? | **❌ NO** — INGEST/LINT remain admin-local (run via Claude Code in the terminal). G18, G19, G26, G27 marked Out of Scope per D3. Batch 3 of this plan (G18 + G19 closure) is now formally cancelled. |

Estimates are grounded in code patterns already in this codebase — where I'm extrapolating from existing patterns I've seen, the estimate is firmer; where I'm guessing at unfamiliar territory (streaming refactor), I say so.

**Estimation calibration.** "1 day" = one focused engineering day (~6h productive). All P1 estimates include test coverage at the level the existing repo demonstrates (3–6 tests per new tool, following `tests/test_tools.py` patterns). I'm not padding for review cycles — that's separate.

**Two staffing scenarios:**
- **Lean:** 1 engineer + subagent-driven implementation. Estimates below assume this.
- **Parallel:** 2 engineers. Independent gaps (different files) can run in parallel; gated gaps cannot. Cuts wall-clock by ~30–40%, not 50%.

---

## Batch 0 — Architectural Decisions (1.5h total, must precede everything)

| ID | Decision | Format | Output |
|----|----------|--------|--------|
| D1 | Wiki-editing scope | 30-min sync | "Query-only" OR "Query + curator workflows" |
| D2 | Streaming for api mode | 30-min sync | "Match CC UX" OR "Accept 5–30s wait, document it" |
| D3 | INGEST/LINT scope | 30-min sync | "Non-goal — terminal only" OR "Deferred to vX" OR "Required for pilot" |

This plan is structured for the **most likely** decision set: **D1 = "query-only for now," D2 = "match CC UX," D3 = "non-goal for pilot."** If different, see the conditional batches at the bottom.

---

## Batch 1 — P1 (Pilot-Ready Shortlist)

*Goal: an internal user's first 10 queries don't hit any of the "stale data, silent context loss, missing fresh tickets, no feedback loop" failure modes.*

### G01 — Live Jira ticket lookup

**Approach:** Add `jira_live_get_ticket` tool. Direct HTTP to `https://moveinsync.atlassian.net/rest/api/3/issue/{key}` using existing `JIRA_API_TOKEN` env var (same one `mcp-atlassian` uses, configured in `.mcp.json`). Adapt the HTTP pattern from `scripts/pms_api_client.py` (`urllib`-based, no new deps). Triggered conditionally: model uses it when (a) user names a ticket key AND (b) `jira_get_ticket` from the mirror returns `not_found` or `updated_at` is more recent than mirror's last sync.

**Files:**
- New: `backend/tools/jira_live_tools.py` (~80 lines: schema + handler + auth helper)
- Modify: `backend/tools/__init__.py` (register tool)
- Modify: `backend/deep_system_prompt.py` (add 2-line instruction on when to call)
- New: `tests/test_jira_live.py` (~5 tests, mock `urllib.request`)

**Effort:** ~6h.

**Risks:** Atlassian rate limits (10 rps per `config/jira.toml`).

**Eval signal:** Q3p moves from FAIL → PASS.

---

### G02 — Streaming for api mode  *(gated by D2 = yes)*

**Approach:** Refactor `backend/providers/deep_query.py:generate_with_tools()` to use `client.messages.stream()` instead of `messages.create()`. Tool-use blocks arrive complete at `content_block_stop`; dispatch via `tool_registry.execute()`, then continue next `messages.stream()` call with appended tool_results. Plumb text deltas out to a generator that the API layer consumes. In `backend/api.py:/query`, switch to `StreamingResponse` similar to existing `/query/stream`. SSE events: `text_delta`, `tool_use_start`, `tool_result`, `done`, `error`.

**Files:**
- Modify heavily: `backend/providers/deep_query.py` (~200 lines rewrite of the loop)
- Modify: `backend/orchestrator.py:run_deep` (yield-based)
- Modify: `backend/api.py:/query` (StreamingResponse for mode=api)
- Frontend: switch fetch to EventSource for default mode
- Tests: existing `test_local_claude_code.py` pattern but for api mode

**Effort:** ~3–4 days. **Estimate has uncertainty** — Anthropic SDK supports streaming cleanly, but the existing loop has a specific structure (append full `resp.content` as one assistant message, batch all tool_results into one user message) that has to be preserved across stream chunks.

**Side benefit:** Self-interruption (G21) becomes ~free.

**Eval signal:** Q28 moves from FAIL → PASS.

---

### G03 — Conversation context compaction

**Approach:** Two-tier history: keep last 6 turns verbatim, plus a rolling summary of turns 7..N stored on the conversation row. Summary refreshed when turn count crosses threshold (e.g., every 6 new turns). Use a cheap call (claude-haiku-4-5, ~200 tokens out) with: "Summarize prior conversation in 5 bullets, preserving constraints and references."

**Files:**
- Modify: `backend/conversation_store.py` (add `compacted_summary TEXT` column via idempotent migration — pattern identical to the `user_email` migration in `_apply_migrations`)
- Modify: `backend/orchestrator.py:_load_conversation_context` (prepend summary as a synthetic system note when present)
- New: `backend/conversation_compactor.py` (~80 lines)
- Wire compaction trigger into `add_message` or run it lazily on `_load_conversation_context` when turn count > threshold
- Tests: extend `tests/test_conversations.py` with multi-turn scenario

**Effort:** ~1.5 days.

**Risks:** Adds 1–2s latency on the first query after threshold is crossed. Mitigate by running compaction async.

**Eval signal:** Q23 moves from FAIL → PASS.

---

### G04 — Session-start operational posture

**Approach:** Extend `backend/preflight.py:build_seed_message()` to prepend a compact operational-context block when relevant signals are non-default. Pull from `admin_api.get_sync_status()` (already exists). Cache results per-process for 5 min.

Block looks like:
```
**Operational context:** Jira mirror last sync: 2026-05-22 02:00 UTC (8h ago, fresh).
Wiki: 134 pages. Pending feedback: 2 items. Uningeseted raw files: 0.
```

Only include lines where the value is "interesting" (mirror >36h stale, feedback >0, etc.) to avoid prompt bloat.

**Files:**
- Modify: `backend/preflight.py:build_seed_message`
- New helper: `backend/operational_context.py` (~50 lines)
- Tests: 3 — fresh mirror (no block), stale mirror (warning block), pending feedback (prompt block)

**Effort:** ~4–6h.

**Eval signal:** Q21 and Q22 move from FAIL → PASS.

---

### G05 — Live Config Debug workflow completion

**Approach:** Expose 4 new tools mapping to existing `pms_session.py` / `pms_api_client.py` methods.

| New tool | Wraps | Effort |
|----------|-------|--------|
| `pms_list_offices` | `pms_api_client._cmd_offices` | ~3h |
| `pms_list_criteria` | `pms_api_client._cmd_criteria_values` | ~3h |
| `pms_verify_buid` | New — calls `roles` API, checks BUID accessible, returns mismatch warning | ~4h |
| `pms_diagnose_property` | `pms_session.Session.compare_property` + `debug_report` | ~6h |

Update `deep_system_prompt.py` to encode the §12 disambiguation pattern: "If user mentions a config without specifying server, ask 'which server?' before fetching."

**Files:**
- Modify: `backend/tools/pms_tools.py` (4 new schemas + 4 new handlers)
- Modify: `backend/tools/__init__.py` (register 4 tools)
- Modify: `backend/deep_system_prompt.py` (~10 lines for disambiguation)
- New tests (4–8 tests with mocked PMS responses)

**Effort:** ~2.5 days. **Caveat:** half-day buffer for verifying `pms_session.Session.compare_property` returns the shape needed for a tool result.

**What this does NOT close:** Multi-turn conversational disambiguation (G08).

**Eval signal:** Q13, Q14 move from FAIL → PASS. Q12, Q15 improve from PARTIAL → PASS.

---

### G06 — Answer-ID feedback prompt

**Approach:** Two changes:
1. In `backend/deep_system_prompt.py:54–76`, append:
   ```
   ---
   **Review this answer:** Score 1–5 (5 = fully correct).
   **Answer ID:** `<ANSWER_ID>`
   If score ≤3, tell me what was wrong.
   ```
2. In `backend/orchestrator.py:run_deep` (lines 187–199 region), AFTER `log_answer()` returns the id, do a single `.replace("<ANSWER_ID>", answer_id)` on `raw_answer` before assigning to `OrchestratorResult.answer_text`.

**Files:**
- Modify: `backend/deep_system_prompt.py` (~6 lines added)
- Modify: `backend/orchestrator.py` (~3 lines: post-hoc substitution)
- Test: 1 — verify rendered answer contains `**Answer ID:** abc123def456` not the placeholder

**Effort:** ~2h.

**Eval signal:** Q19 moves from FAIL → PASS. Q20 improves (user knows the answer_id to reference).

---

### G07 — wiki_propose_edit admin-apply doesn't write to wiki  *(gated by D1 = yes)*

**If D1 = query-only:** This gap collapses to "design intent." Update the admin UI and code comments to say so explicitly. ~30min.

**If D1 = yes:**
**Approach:** Add `applied_content: str | None` field to `POST /admin/wiki/proposals/{id}/apply` request body. When provided, write that content to the wiki page. Frontend admin UI shows the current page + proposed_change side-by-side; admin types the new content and submits.

**Files:**
- Modify: `backend/admin_api.py:apply_wiki_proposal`
- Modify: `backend/api.py:admin_apply_wiki_proposal` (add request schema field)
- Frontend: admin proposals page needs editor textarea

**Effort:** ~1 day backend + ~1 day frontend.

---

### G08 — Conversational clarification primitive

**Approach (lean):** No new tool. Instruct the model in `deep_system_prompt.py` to emit answers in `confidence: "Low"` with an ending question when scope is ambiguous. Frontend treats this as "ask follow-up."

Concretely, append to the system prompt:
> If the user's question is ambiguous on server, BUID, office, or service, set Confidence to "Low" and end your answer with a single clarifying question prefixed by `**Need:**`. Do not guess.

**Files:**
- Modify: `backend/deep_system_prompt.py` (~8 lines)
- Frontend: detect `**Need:**` in answer; render as inline follow-up prompt

**Effort:** ~2h backend + ~half day frontend.

**Eval signal:** Q11 moves from FAIL → PASS.

---

### G09 — Large tool output continuation

**Approach:** Add `offset` and `limit` params to `jira_get_ticket` and `wiki_read_page`. Return `{description_text, description_total_length, description_has_more}` shape. Model can then call again with offset advanced.

**Files:**
- Modify: `backend/tools/jira_tools.py` (handler + schema, ~30 lines)
- Modify: `backend/tools/wiki_tools.py` (handler + schema, ~20 lines)
- Tests: 4 — happy path full content, offset midway, offset past end, has_more flag

**Effort:** ~4–5h.

**Eval signal:** Q25 moves from FAIL → PASS.

---

**Batch 1 totals (Lean staffing, D2=yes, D1=no):**

| Scenario | Effort | Wall clock |
|----------|--------|---|
| Without G02 streaming | G01 + G03 + G04 + G06 + G09 = ~3.5 days | ~1 week |
| With G02 streaming + G05 PMS + G08 | ~12 days | ~3 weeks |

---

## Batch 2 — P2 (Quality of Life)

### G10 — Bump 8-round cap to 12
Change `_MAX_ROUNDS_ABSOLUTE = 8` → `12` in `backend/providers/deep_query.py:32`. Run eval set and confirm no regression. **Effort:** ~3h.

### G11 — Filesystem Read for raw/  *(gated by D1)*
Add `read_source_doc(path, format='text')` tool. Allowlist: `.md`, `.txt`, `.pdf` (via `pdfplumber`), `.docx` (via `python-docx`). Path scoped to `raw/`. Size cap 1MB. **Effort:** ~1 day. New deps: `pdfplumber`, `python-docx`.

### G12 — More named Jira queries / read-only SQL
**Option A:** Add 3–4 more `jira_named_query` templates (area+priority+recency, count_by_status, content_search). ~1 day.
**Option B:** Add `jira_readonly_sql(query)` tool with `sqlparse`-based validation. ~2 days.
Recommend A.

### G13 — wiki_grep literal-match
Add `wiki_grep(pattern, regex=False, path_glob=None)` tool. Iterate over `wiki_retriever`'s page index, run `re.search` or substring match. **Effort:** ~5h.

### G14 — Save-answer-as-wiki-page  *(gated by D1)*
Add `wiki_save_concept(title, content, tags)` tool. **Effort:** ~1 day if Edit tools exist; ~2 days standalone.

### G15 — Tool trace UI surfacing
Backend already returns `tool_trace`. Frontend renders it as a collapsible "How I got this answer" panel. **Effort:** 0 backend / ~4h frontend.

### G16 — Atomic MultiEdit  *(gated by D1)*
Add `wiki_multi_edit(edits: list[{path, before, after}])` tool. All-or-nothing semantics. **Effort:** ~1 day.

### G17 — In-conversation approval prompts
Status quo is acceptable. **No code change.** Document in CLAUDE.md.

**Batch 2 totals:** ~3–5 days unconditional. + ~3 days if D1 = yes. Wall clock: ~1 week unconditional, +~1 week for D1-gated.

---

## Batch 3 — P1 / P2 conditional on D3 (INGEST/LINT in scope)

These collapse to "out of scope" if D3 = non-goal.

### G18 — INGEST workflow (9 tools)  *(D3 = yes)*

Tool mapping:
1. `ingest_read_source(raw_path)`
2. `ingest_summarize_for_review(content)`
3. `wiki_create_source_page(filename, frontmatter, content)`
4. `wiki_create_entity_page(name, frontmatter, sections)`
5. `wiki_create_module_page(name, frontmatter, sections)`
6. `wiki_create_cross_module_page(modules, content)`
7. `wiki_create_decision_page(date, title, content)`
8. `wiki_update_glossary(terms: list[{term, definition}])`
9. `wiki_update_index_and_log(operation, pages_touched)`

Plus admin-approval gating.

**Effort:** ~2.5–3 weeks. **Strongly recommend deferring to v2.**

### G19 — LINT workflow  *(D3 = yes)*
3 new tools: `wiki_list_pages(filter)`, `wiki_grep(pattern)`, `wiki_check_links()`. Plus orchestrator `lint_wiki()`. **Effort:** ~1 week.

---

## Batch 4 — P3 (Polish, Quick Wins)

| ID | Gap | Approach | Effort |
|----|-----|----------|--------|
| G20 | view_range in wiki_read_page | Same offset/limit pattern as G09 | 2h *(bundle with G09)* |
| G24 | Model version configurable | Read `ANTHROPIC_MODEL` env var; default to current literal | 30min |
| G25 | `/query/stream` misleading name | Add `/query/stream-claude-code` alias; mark `/query/stream` deprecated | 30min |

**Effort:** ~3h total.

Genuinely defer: G21 (free with G02), G22, G23, G26, G27, G28.

---

## Sequenced Plan (recommended ordering, lean staffing)

Assumes D1 = query-only for now, D2 = yes, D3 = non-goal for pilot.

| Week | Batch contents | Wall-clock |
|------|----------------|------------|
| **Week 1** | G01 (live Jira), G06 (answer-id prompt), G09 + G20 (output continuation), G04 (session posture), G24 + G25 (quick wins) | 5 working days |
| **Week 2** | G02 (streaming refactor) — full week | 5 working days |
| **Week 3** | G03 (context compaction), G05 (PMS workflow completion), G08 (clarification UX) | 5 working days |
| **Week 4** | Batch 2 P2s: G10, G12 (named queries), G13 (wiki_grep), G15 (frontend tool trace), G17 (no-op) | 5 working days |
| **Pilot ready** | After Week 3. Week 4 is enrichment, not blocker. | |

**If D2 = no:** collapse Week 2 into Week 3 → pilot-ready after 2 weeks.
**If D1 = yes:** add 2 weeks. Pilot-ready after 5 weeks.
**If D3 = yes:** add 3–4 more weeks. **Strongly recommend deferring D3 to v2.**

---

## Conventions (re-baselined from real-Jira surprises)

### Outbound HTTPS — truststore policy depends on the destination

The MoveInSync corporate network intercepts SOME outbound HTTPS with a self-signed root CA but not all. The OS keychain trusts that CA; `certifi`/urllib's default bundle does not. Empirically (smoke tests G01 and G05, 2026-05-22):

| Destination | Intercepted? | Truststore required? |
|---|---|---|
| `*.atlassian.net` (Atlassian Cloud) | YES | **YES** — without it, `CERTIFICATE_VERIFY_FAILED` |
| `cmsapp.moveinsync.{com,in}` (PMS API) | NO | No |
| `mis-security.moveinsync.{com,in}` (Offices) | NO | No |

**Rule:** for any new backend tool that makes outbound HTTPS calls to an **external** host (not `*.moveinsync.*`), inject `truststore` at module import time, BEFORE any SSL machinery loads:

```python
try:
    import truststore  # type: ignore
    truststore.inject_into_ssl()
except ImportError:  # pragma: no cover
    pass
```

Place it **before** `import urllib.request` / `import requests` / `import httpx`. `truststore==0.10.1` is already in `requirements.txt`. Existing examples: `scripts/lib/jira_client.py`, `backend/tools/jira_live_tools.py`.

For MoveInSync-internal hosts (PMS, mis-security, etc.), the inject is currently not needed. If those calls ever start failing with SSL errors after a network reconfiguration, add the inject — it's safe (no-op when not needed).

Refactoring opportunity to extract a shared `backend/_ssl_setup.py`, low priority.

### Re-baselined G01 effort

Original estimate: ~6h. Actual with SSL diagnosis and fix: ~7h. PLAN.md's "use urllib (no new deps)" sketch was right about no NEW deps but wrong about not needing the truststore pattern. Future estimates for tools hitting Atlassian / external HTTPS: add ~1h SSL buffer if you haven't done one before.

---

## Where my estimates have the most uncertainty

1. **G02 (streaming refactor) — 3–4 days, ±1 day.** Have not refactored a streaming tool-use loop in *this* codebase. If the tool-use loop interacts badly with the `_FORCE_SYNTHESIS` round 8 logic, add a day.
2. **G05 (PMS workflow completion) — 2.5 days, ±0.5 day.** Dependent on `pms_session.Session.compare_property` returning the shape needed.
3. **G18 (INGEST workflow) — 2.5–3 weeks, ±5 days.** Many tools, content team likely has tacit conventions not in CLAUDE.md.
4. **Everything else: ±20%.** Patterns are well-established (`tests/test_tools.py`, `tests/test_admin_wiki_proposals.py` provide templates).
