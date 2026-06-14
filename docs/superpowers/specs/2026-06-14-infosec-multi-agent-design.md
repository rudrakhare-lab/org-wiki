# Infosec Agent — Multi-Agent Platform Design

_Date: 2026-06-14 · Status: draft for owner review · Base commit: `7fe5552` (bitbucket/main)_

---

## 0. Plain-language summary (read this first)

Today the app runs **one** AI assistant: **Conwo**. It answers questions about
WorkInSync using a wiki knowledge base plus Jira and PMS config data.

Leadership wants a **second** assistant, **Infosec**, living in the **same app**.
You pick the agent from a switcher in the top-left of the screen, and **everything**
follows that choice — the chat, the dashboard, the traces, the ingest screen, and
the knowledge-base graph all show Infosec's data instead of Conwo's.

What's true about Infosec:

- It has its **own knowledge base** (its own wiki files + its own `CLAUDE.md` brain).
  It does **not** share anything with Conwo.
- It is **purely wiki-based** — **no Jira, no PMS**. Just documents you ingest.
- It's built and filled exactly the way Conwo was: you drop in `.md` source docs,
  run the **same ingest workflow**, and that automatically builds Infosec's nodes
  and relationships (the knowledge graph).
- It reuses the **same backend code and the same tools** as Conwo (minus the
  Jira/PMS tools, which are hidden for Infosec).

What we're building is really a small **platform**: agents are defined in a config
file, so adding a *third* agent later is just one config entry + ingesting docs —
no new code.

**What you need to do:** approve this plan, then later hand me the Infosec source
documents. I author Infosec's `CLAUDE.md`; you provide the content.

**Timeline:** ~8–9.5 working days of focused build **including testing**, spread across
6 reviewable phases (≈1.5–2.5 calendar weeks allowing for review at each checkpoint).

**The one thing to know:** this touches shared code that Conwo also uses. The plan's
#1 safety rule is that **every phase ends by proving Conwo still works** before we
move on.

---

## 1. Goals & non-goals

### Goals
1. A second agent, **Infosec**, selectable from the frontend, with full feature
   parity across all five surfaces: **chat (ask), dashboard, traces, ingest,
   knowledge-base graph**.
2. **Complete data isolation** of knowledge: separate wiki directory, separate
   `CLAUDE.md`, separate ingested content and derived graph.
3. **Operational isolation** of conversations, traces, feedback, and ingest jobs
   per agent (so each agent's dashboard/traces/history show only its own data).
4. **Shared backend + shared tools** — no forked codebase. One deployment.
5. **Config-driven** agent definitions so future agents need no code change.
6. **Zero regression** for Conwo at every step.

### Non-goals (explicitly out of scope for v1)
- Infosec will **not** support Jira or PMS tools or the live-config-debug workflow.
- Infosec will **not** support `agent`/Claude Code subprocess mode in v1
  (api/Deep-Search mode only — see §6.4). Conwo keeps both modes.
- No per-agent user permissions model — the existing RBAC roles
  (`admin`/`developer`/`general`) apply across all agents unchanged.
- No separate database or schema per agent (we use one DB with an `agent_id`
  column — see §7).
- No migration of Conwo's existing data to a new location (Conwo keeps its current
  paths — see §4).

---

## 2. Key decisions (all decided — no open technical questions)

| # | Decision | Rationale |
|---|----------|-----------|
| D1 | **Config-driven agent registry** (`config/agents.toml`) | Leadership wants growth; adding agent #3 = one config entry. |
| D2 | **One Postgres DB + `agent_id` column** on operational tables | Simplest ops (one backup, one migration set); clean per-agent filtering. |
| D3 | **Per-agent wiki dir + `CLAUDE.md`**; Conwo stays at existing paths | Knowledge isolation without risky data moves. |
| D4 | **Agent selected via `X-Agent-Id` HTTP header** (one frontend interceptor) | Lowest churn; no URL rewrite across every route. |
| D5 | **Per-agent tool allowlist**; Infosec = wiki + ingest tools only | Hides Jira/PMS without forking tool code. |
| D6 | **Per-agent capability flag `modes`**; Infosec = `["api"]` only | Avoids the Claude Code subprocess-isolation problem in v1. |
| D7 | **Preflight + prompts are agent-conditional** (Jira-free for wiki-only agents) | Hiding tools isn't enough; the evidence pipeline assumes Jira today. |
| D8 | **I author Infosec's `CLAUDE.md` + deep prompt**; owner provides source docs | Agreed with owner. |
| D9 | **Unknown/missing agent defaults to `conwo`** | Backward compatible — existing clients keep working. |

---

## 3. The Agent Registry (the foundation)

A new file `config/agents.toml` defines every agent. Loaded once at startup into a
typed `AgentSpec` dataclass, accessed through a small `agent_registry` module.

```toml
[agents.conwo]
display_name    = "Conwo"
description     = "WorkInSync product, config & debugging assistant"
wiki_dir        = "wiki"                 # existing path — Conwo data does NOT move
raw_dir         = "raw"                  # existing path
claude_md       = "CLAUDE.md"            # existing file
prompt_sections = [5, 9, 12]             # current SYSTEM_PROMPT_SECTIONS
tools           = ["*"]                  # all tools: wiki + jira + pms + config
modes           = ["api", "agent"]       # Deep Search + Claude Code
has_jira        = true
has_pms         = true

[agents.infosec]
display_name    = "Infosec"
description     = "Information-security knowledge assistant"
wiki_dir        = "agents/infosec/wiki"
raw_dir         = "agents/infosec/raw"
claude_md       = "agents/infosec/CLAUDE.md"
prompt_sections = []                     # Infosec CLAUDE.md uses its own section layout
tools           = ["wiki_search", "wiki_read_page", "wiki_grep",
                   "wiki_list_pages", "wiki_check_duplicate",
                   "wiki_propose_new", "wiki_propose_edit",
                   "wiki_propose_append", "wiki_propose_multi_edit",
                   "feedback_record"]    # NO jira_*, NO pms_*, NO config_lookup, NO trigger_jira_sync
modes           = ["api"]                # Deep Search only in v1
has_jira        = false
has_pms         = false
```

`AgentSpec` fields: `id, display_name, description, wiki_dir (Path), raw_dir (Path),
claude_md (Path), prompt_sections, tools (allowlist or `["*"]`), modes, has_jira,
has_pms, identity`. Paths resolve relative to `CONWO_DATA_DIR` (honoring the existing
PVC override) or repo root, exactly like `config.py` does today.

`agent_registry` API:
- `get(agent_id) -> AgentSpec` (falls back to `conwo` on unknown/missing id, per D9)
- `all() -> list[AgentSpec]`
- `default() -> AgentSpec` (conwo)

---

## 4. Knowledge-base layout on disk

```
org-wiki/
├── wiki/                      ← Conwo (unchanged)
├── raw/                       ← Conwo raw + jira mirror + configs (unchanged, shared infra)
├── CLAUDE.md                  ← Conwo brain (unchanged)
└── agents/
    └── infosec/
        ├── wiki/              ← Infosec wiki pages (built by ingest)
        ├── raw/               ← Infosec source docs + uploads
        └── CLAUDE.md          ← Infosec brain (I author)
```

- Conwo is **not moved** — zero data-migration risk.
- The graph is computed on the fly from each agent's `wiki/*.md` `[[wikilinks]]`
  ([`wiki_graph_api.py:104`](../../../backend/wiki_graph_api.py)). A separate wiki dir
  ⇒ a separate graph automatically. No graph store to build.
- The Jira mirror (`raw/jira/tickets.sqlite`) and PMS configs stay shared/global —
  Infosec simply never queries them.

---

## 5. Request routing: how an agent is selected per request

1. Frontend stores the active agent id and sends it on **every** HTTP request via an
   **`X-Agent-Id` header**, injected in one place: the existing
   [`auth.interceptor.ts`](../../../frontend/src/app/core/auth.interceptor.ts).
2. Backend resolves the header once per request into an `AgentSpec`:
   - Passed **explicitly** to `orchestrator.run(agent=...)` (clean main path).
   - Set in a **`ContextVar`** (`current_agent`) so leaf code that today reads the
     module-global `WIKI_DIR` (the wiki retriever and wiki tools) reads the active
     agent's wiki dir instead — without threading a parameter through every function.
3. Missing/unknown header ⇒ defaults to `conwo` (D9). Existing API clients unaffected.

> ⚠️ The `ContextVar` is set/reset per request in a dependency or middleware, never
> left dangling between requests. The explicit `agent=` parameter is the source of
> truth for the orchestrator; the `ContextVar` is only the bridge for the
> currently-global wiki access.

---

## 6. Backend changes

### 6.1 Config & registry
- New: `config/agents.toml`, `backend/agent_registry.py` (`AgentSpec` + loaders).
- `backend/config.py`: keep `WIKI_DIR`/`RAW_DIR`/`CLAUDE_MD` as **conwo aliases**
  (resolved from the registry's default) so untouched call sites keep working during
  the transition.

### 6.2 Wiki retriever — singleton → per-agent
[`wiki_retriever.py`](../../../backend/wiki_retriever.py) currently holds one
module-global `_INDEX`. Change to a dict `{agent_id: WikiIndex}` with
`get_index(agent_id)` that builds lazily and caches. Build all registered agents at
startup. Ingest rebuilds **only** the affected agent's index (and `search()` /
`all_paths()` read the current agent's index via the `ContextVar`).

### 6.3 System prompts — parameterize by agent
- [`system_prompt.py`](../../../backend/system_prompt.py): `load_system_prompt(agent_id)`
  reads that agent's `CLAUDE.md` + `prompt_sections` + `identity`. Replace
  `@lru_cache(maxsize=1)` with a per-agent cache (keyed by `agent_id`).
- [`deep_system_prompt.py`](../../../backend/deep_system_prompt.py): today a single
  inline string hardcoded to "You are Conwo … PMS configs and Jira history." This is a
  **real rewrite, not a string swap** (D7). Build the deep prompt from the agent's
  identity and capabilities: the Jira/PMS evidence-workflow scaffolding is **omitted**
  for agents with `has_jira=false`/`has_pms=false`. Authored as part of the Infosec
  content work (§9), keyed by agent.

### 6.4 Mode scoping (D6)
- `orchestrator.run(...)` and the `/query`, `/query/stream` endpoints reject a mode the
  agent doesn't list in `modes` (Infosec + `agent` mode ⇒ clean error, never a silent
  subprocess). Frontend hides the Claude Code toggle for agents without `agent` mode.
- _Future note (not v1):_ enabling `agent` mode for Infosec later requires giving the
  `claude` subprocess its own working dir + `CLAUDE.md` and a Jira-free preamble.

### 6.5 Preflight & seed message — agent-conditional (D7)
[`preflight.py`](../../../backend/preflight.py) `run_preflight` /
`build_seed_message` / `build_agent_preamble` currently always do Jira ranked search
and format Jira buckets. Make Jira retrieval + Jira scaffolding **conditional on
`agent.has_jira`**. For Infosec: wiki-only preflight, no empty Jira blocks, no calls to
tools the registry doesn't expose.

### 6.6 Tool registry — per-agent allowlist (D5)
- [`tools/__init__.py`](../../../backend/tools/__init__.py) `build_registry(user_role)`
  → `build_registry(user_role, agent)`. After registering, filter to the agent's
  `tools` allowlist (`["*"]` = keep all). Existing **role** permissions in
  [`tools/registry.py`](../../../backend/tools/registry.py) are unchanged and stack on
  top.
- Wiki tool handlers that import the global `WIKI_DIR` resolve the dir from the
  `current_agent` `ContextVar` instead.

### 6.7 Orchestrator
- Thread `agent` through `run` → `run_deep` / `run_single_shot` → `run_preflight`,
  `build_registry`, `load_deep_system_prompt`, `load_system_prompt`,
  `wiki_retriever.search`. (`run_single_shot`/`search_only` also get the agent so their
  direct `jira_retriever.search` is gated by `has_jira`.)

### 6.8 Ingest
- [`ingest_api.py`](../../../backend/ingest_api.py) /
  [`ingest_service.py`](../../../backend/ingest_service.py): ingest requests carry the
  agent (from `X-Agent-Id`); uploads land in the agent's `raw/`, writes target the
  agent's `wiki/`, and the PLAN/EXECUTE prompts are parameterized with the agent's
  identity + its `CLAUDE.md` schema. Registries built with the agent. On completion,
  rebuild that agent's wiki index only.

### 6.9 Wiki graph API
- [`wiki_graph_api.py`](../../../backend/wiki_graph_api.py): `GET /api/wiki/graph` reads
  `X-Agent-Id` (or `?agent_id=`) and walks that agent's wiki dir. The PMS config overlay
  runs only when `agent.has_pms`.

### 6.10 New endpoint
- `GET /agents` → `[{id, display_name, description, modes, has_jira, has_pms}]` for the
  frontend switcher. Auth-gated like other read endpoints.

---

## 7. Database (one DB, add `agent_id`)

New migration **`migrations/postgres/090_agent_id.sql`** (latest is currently `080`):

- `ALTER TABLE conversations ADD COLUMN agent_id TEXT NOT NULL DEFAULT 'conwo';`
  + index `(agent_id, user_email)`.
- `ALTER TABLE messages ADD COLUMN agent_id TEXT NOT NULL DEFAULT 'conwo';`
- `ALTER TABLE trace_sessions ADD COLUMN agent_id TEXT NOT NULL DEFAULT 'conwo';`
  + index `(agent_id, started_at)`.
- `trace_events` / `trace_metrics` inherit agent via join to `trace_sessions` (no column
  needed unless dashboards need it for speed — add only if profiling shows it).
- `DEFAULT 'conwo'` backfills every existing row correctly — **no data loss, no manual
  backfill**. Migration is idempotent (`ADD COLUMN IF NOT EXISTS`), matching the
  existing migration style.

Store changes:
- [`conversation_store.py`](../../../backend/conversation_store.py):
  `create_conversation(..., agent_id)`, and `list_conversations(..., agent_id)` adds
  `WHERE agent_id = %s`. Same agent stamped onto messages.
- [`trace_store.py`](../../../backend/trace_store.py): `start_session(..., agent_id=...)`.
  The session is stamped in the **handler** call (which has `X-Agent-Id`), not the early
  middleware UPSERT. Trace list/dashboard queries filter by `agent_id`.
- Feedback & proposals (file-based: `wiki_proposals.py`, `feedback_service.py`,
  `config.py` `ANSWER_LOG`/`FEEDBACK_LOG`): add an `agent_id` field to each JSON record
  and filter reads by it. (File split per agent is an acceptable alternative; field is
  lower-churn.)

**Stays global/shared (untouched):** `users`, `tokens`, `tickets` (Jira mirror),
`configs` (PMS), `rate_limits`.

---

## 8. Frontend changes

- **New `AgentService`** (`core/agent.service.ts`): `activeAgent` signal, persisted to
  `localStorage` (`conwo.active_agent`), agent list fetched from `GET /agents`. Default
  = `conwo`.
- **`auth.interceptor.ts`**: add `X-Agent-Id: <activeAgent>` to every request (single
  chokepoint — same place the Bearer token is attached today, ~line 32). Public health
  paths excluded as they are now.
- **Switcher UI**: a dropdown in the sidebar header
  ([`app-sidebar.ts`](../../../frontend/src/app/shared/app-sidebar/app-sidebar.ts),
  between brand and "New chat"). Changing it updates the signal.
- **Reactivity**: features that load agent-scoped data react to `activeAgent` via an
  Angular `effect()` and refetch:
  - `ask` — clear active thread, reload conversation list for the new agent;
  - `traces` (list + detail + dashboard) — refetch;
  - `ingest` — reset/reload its job state (its `localStorage` job keys become
    agent-namespaced);
  - `graph` — refetch `/api/wiki/graph`.
- **Branding**: the 7 hardcoded "Conwo" strings (app title, sidebar brand, login,
  pending, ask avatar/transcript) read the active agent's `display_name` where they
  refer to the *active agent*. (Login/pending may stay product-branded; ask/sidebar
  reflect the active agent.)
- **Mode toggle**: hidden when the active agent's `modes` excludes `agent` (Infosec
  shows Deep Search only).
- **Conversation store** (`conversation.store.ts`): scope refresh/list to the active
  agent (the backend already filters; the store just refreshes on agent change).

---

## 9. Infosec content (authored as part of this work)

- **`agents/infosec/CLAUDE.md`** — a trimmed clone of Conwo's `CLAUDE.md`:
  - **Keep:** page types (module/concept/entity/integration/decision/cross-module/
    source/person), the 9-step ingest workflow, the query workflow, the lint workflow,
    index/log conventions, cross-link rules.
  - **Drop:** all Jira-layer, PMS-config, `.in`/`.com` server, live-config-debug, and
    functional-area sections.
  - **Rewrite:** identity, purpose, and module-naming for the security domain.
- **Infosec deep prompt** (the agent branch in §6.3) — security-knowledge identity,
  wiki-only evidence workflow, no Jira/PMS instructions.
- **Source docs:** owner provides Infosec `.md` docs later; we then run the **same
  ingest pipeline** against the Infosec agent to build its pages + graph.

---

## 10. Phasing with verification gates

Each phase ends at a **review checkpoint** and a **Conwo-regression gate** before the
next begins. The backend phases (0–3) form an independently-verifiable milestone
**before** any frontend work.

| Phase | Scope | Exit / verification gate | Effort (build + test) |
|------|-------|--------------------------|----------------|
| **0** | Agent registry + `AgentSpec` + `config/agents.toml` + `current_agent` ContextVar + request resolution + `GET /agents` | `GET /agents` returns both agents; default resolves to conwo; existing tests green | ~1 day |
| **1** | DB migration `090` + `agent_id` in conversation/trace/feedback/proposal stores | Migration applies idempotently; existing rows show `agent_id='conwo'`; **Conwo conversations + traces still list correctly** | ~1 day |
| **2** | Backend agent-awareness: retriever multi-index, system + deep prompts per agent, preflight/seed agent-conditional, tool allowlist, orchestrator threading, mode gating | **Conwo `api` query passes** (regression); **Infosec answerable via `curl` with `X-Agent-Id: infosec`** against a tiny placeholder wiki — wiki-only, no Jira calls in trace | ~2 days |
| **3** | API endpoints propagate agent: `/query`, `/query/stream`, conversations, traces, dashboard, ingest, graph | Per-agent curl checks for all surfaces; Conwo unaffected; Infosec ingest writes to `agents/infosec/wiki` and rebuilds only its index | ~1–1.5 days |
| **4** | Frontend: `AgentService`, interceptor header, sidebar switcher, per-feature reactivity, branding, mode-toggle gating | Manual UI pass: switch agent → chat/traces/dashboard/ingest/graph all swap; switch back → Conwo intact | ~2 days |
| **5** | Author Infosec `CLAUDE.md` + deep prompt; register agent; ingest a sample doc; end-to-end verification | Full E2E: ingest an Infosec doc via UI → graph shows new nodes → ask Infosec a question → correct answer, no Jira/PMS leakage; Conwo full regression | ~1 day |

**Total: ~8–9.5 working days** of focused Claude-Code-driven build **including test
time** (the earlier 6–9 day figure excluded explicit testing; this is the realistic
number). Calendar: **≈1.5–2.5 weeks** allowing for owner review at each checkpoint.

Each phase is one coherent commit (or its own PR) on the feature branch, so review
happens phase-by-phase. Final PR: `feature/infosec-multi-agent → main`.

---

## 11. Risks & mitigations

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Shared-code edits regress Conwo | Medium | Conwo-regression gate every phase (§10); backend milestone verified before frontend. |
| `ContextVar` leaks between requests | Low-Med | Set/reset in one dependency; explicit `agent=` is source of truth for orchestrator; add a test asserting reset. |
| Preflight calls a tool the allowlist removed | Medium | §6.5 makes preflight agent-conditional, not just the registry. |
| Claude Code subprocess leaks Conwo context into Infosec | Low (v1) | D6: Infosec is api-only; agent mode gated off per-agent. |
| Wiki index memory grows per agent | Low | Indexes are small; built lazily; fine for a handful of agents. |
| Owner can't deeply review a technical spec | High | This summary + all-decisions-made spec; **I am the de facto technical reviewer** and own the regression gates. |

---

## 12. What I need from the owner

1. **Approve this plan** (or tell me what to change).
2. **Later:** hand me the Infosec **source `.md` documents** to ingest (Phase 5).
   Nothing needed before then.

Everything else (including authoring Infosec's `CLAUDE.md`) is on me.
