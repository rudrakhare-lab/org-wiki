# Conwo — Claude Code vs Anthropic API: production architecture

**Status:** decision document · Owner: Conwo team · Last updated: 2026-05-20

> This document answers the question: *we have Conwo working brilliantly when I
> use Claude Code in terminal — what does it take to make it work for the rest
> of the org through a browser, using only an Anthropic API key?*

---

## 1. One-minute pitch

The Anthropic API gives us **the model only**. Claude Code in terminal also
gives us an **agent runtime** (the loop) and a **tool-execution layer**
(Read, Bash, Grep, MCP, etc.) — that's why it feels powerful on this repo.

To deliver the same usefulness to the org via a browser, we don't need to
"have an API key." We need to **build the runtime and tool layer ourselves**,
behind one auditable trust boundary, and let the API drive it. The good news:
the **agent runtime, chat UI, conversation store, and 9 of ~14 planned tools
already exist**. What we still need to add: SSO, audit logs, per-user
budgets, scheduled ingestion workers, a vector index, the MCP server,
Postgres, and 3–5 more tools.

**Recommendation:** *Build one Conwo tool layer (10–14 controlled tools) and
expose it through two consumer paths — the FastAPI tool-use loop for browser
users (Deep Search), and an MCP server for power users who prefer their own
Claude Code in terminal. Add SSO, audit logs, and cost controls before any org
pilot.* No raw bash, no raw filesystem, no raw SQL from the model in
production.

We are **not** trying to give every browser user the unrestricted capability
of a terminal Claude Code session in v1. That requires per-user sandboxed
agent workers, which is a 6-8 week project we should defer until pilot
telemetry shows we actually need it.

**Realistic timeline:** ~3 months from today to org-wide GA with one
engineer, ~2.5 months with two (coordination overhead, not 50% gain).

---

## 2. Five-minute pitch

### What we have today

| Piece | State |
|------|-------|
| Angular chat UI with sidebar, conversation history, modes | ✅ built |
| FastAPI backend, conversation store (SQLite), feedback log | ✅ built |
| 9 controlled backend tools (wiki/Jira/PMS/config/feedback) with sanitized trace | ✅ built |
| Anthropic tool-use loop (`DeepQueryProvider`, up to 8 rounds) | ✅ built |
| Local headless Claude Code mode (`claude -p --output-format=stream-json`) over SSE | ✅ built, single-user only |
| Jira sync to SQLite, Drive sync to `raw/modules/`, PMS config ingest, feedback apply | ✅ scripts exist, run manually |
| Auth via `config/allowed_users.toml` (Bearer tokens) | ⚠ functional, doesn't scale to org |
| SSO/RBAC, audit logs, rate limits, cost caps, scheduled sync, Postgres, vector DB | ❌ not yet |
| Per-session sandboxed agent workers | ❌ explicitly out of v1 scope |

### What we ship next

**One tool layer, two consumer paths:**

1. **Browser users → FastAPI `/query` → Anthropic API + tool-use loop → Conwo
   tools.** This is the "Deep Search" mode we already have. Harden it: real
   auth, audit logs, per-user budgets, scheduled ingestion, a few more tools
   (dependency_inspect, wiki_patch_proposal).

2. **Power users → their own Claude Code → remote Conwo MCP server → same
   Conwo tools.** New deliverable: wrap the existing tool registry behind an
   MCP server so terminal users get the same Conwo capabilities without
   needing the repo locally. Phase 3.

The headline insight: **path 1 and path 2 share the same tool
implementations.** One investment, two payoffs.

### What we deliberately *don't* ship in v1

- **Raw bash / raw filesystem / raw SQL** from the model. The current desktop
  Claude Code gets this because the user runs it themselves. Giving it to
  every org user via the browser is a security disaster (any user could ask
  the agent to read `~/.ssh/id_rsa` or push to a repo). We expose **named
  tools only**.
- **Per-session sandboxed agent workers.** This is the "true Claude Code in a
  browser" architecture (Docker container per session, ephemeral repo clone,
  restricted bash allowlist). Build it only if Deep Search hits a real
  ceiling we can measure.

### Hard truths

- The current "Claude Code mode" backend endpoint (`/query/stream` → `claude
  -p` subprocess) **is not org-deployable**. It uses one local Claude
  session, bills against one seat, and grants whoever has a Bearer token
  full shell-like access to the backend machine. For shared deployment we
  must either gate it to admins only or replace it with the MCP path.
- `allowed_users.toml` does not scale beyond a handful of teammates. SSO is a
  pilot blocker, not a polish item.
- SQLite is fine for chat history today (~tens of users). It is **not** fine
  past ~50 concurrent or ~1 GB. Move to Postgres before that.
- Tool-use rounds multiply context tokens. Without per-user budgets and a
  Sonnet→Haiku fallback for cheap turns, costs will spiral on a wide rollout.

---

## 3. Architecture diagrams

### Today (what's actually running)

```
   ┌───────────────────────────────┐         ┌───────────────────────────────┐
   │  Angular browser (1 user)     │         │  Claude Code (terminal)       │
   │  - chat + sidebar             │         │  - power user, this repo open │
   │  - localStorage: api_key,     │         │  - reads CLAUDE.md            │
   │     admin_token               │         │  - uses Read/Bash/Grep/MCP    │
   └──────────────┬────────────────┘         └─────────────┬─────────────────┘
                  │ POST /query (api key)                  │ direct
                  │ POST /query/stream (Bearer token)      │ filesystem access
                  ▼                                         ▼
   ┌─────────────────────────────────────────┐    ┌────────────────────────┐
   │           FastAPI (port 8000)           │    │     Local repo         │
   │  Auth: Bearer tokens from allowed_users │    │  CLAUDE.md, wiki/,     │
   │  /query        → DeepQueryProvider      │    │  raw/, scripts/        │
   │  /query/stream → claude -p subprocess   │◄───┤  .mcp.json (atlassian) │
   │  /conversations CRUD (SQLite)           │    │  tickets.sqlite        │
   └─────┬────────────────────────────────┬──┘    └────────────────────────┘
         │ Anthropic Messages API         │ spawn
         │ (user's API key)               │ subprocess
         ▼                                ▼
   ┌──────────────┐              ┌──────────────────┐
   │  Anthropic   │              │  Local `claude`  │
   │  (LLM only)  │              │  CLI session     │
   └──────────────┘              └──────────────────┘
         │
         │ tool_use blocks
         ▼
   ┌─────────────────────────────────────────────────────────────────────┐
   │              Conwo tool registry (9 controlled tools)               │
   │  wiki_search    wiki_read_page    jira_search_ranked                │
   │  jira_get_ticket  jira_named_query  config_lookup                   │
   │  pms_default_properties  pms_runtime_values  feedback_record        │
   │  • secret-stripping sanitizer    • path-traversal blocked           │
   │  • named SQL only (no raw)       • PMS tokens from env, never logged│
   └────┬─────────────────┬──────────────────┬───────────────────────────┘
        ▼                 ▼                  ▼
  ┌──────────┐   ┌─────────────────┐   ┌──────────────────────┐
  │  wiki/   │   │ tickets.sqlite  │   │  PMS dashboard APIs  │
  │ (md docs)│   │ (Jira mirror)   │   │  .com + .in servers  │
  └──────────┘   └─────────────────┘   └──────────────────────┘
```

### Target (after M3 — org-wide pilot + MCP)

```
   ┌────────────────────┐    ┌────────────────────┐    ┌────────────────────┐
   │ Angular UI         │    │ Power-user Claude  │    │ Future: sandboxed  │
   │ (browser, org SSO) │    │ Code in terminal   │    │ agent worker (M4)  │
   └──────────┬─────────┘    └─────────┬──────────┘    └─────────┬──────────┘
              │ HTTPS                  │ HTTPS                    │
              │ JWT (org SSO)          │ OAuth/Bearer             │
              ▼                        ▼                          ▼
   ┌────────────────────────────────────────────────────────────────────────┐
   │                    AUTH BOUNDARY (Conwo gateway)                       │
   │   SSO/RBAC · per-user budgets · audit logs · rate limits               │
   └─────┬──────────────────────────────┬──────────────────────────┬────────┘
         ▼                              ▼                          ▼
   ┌──────────────────────┐    ┌──────────────────────┐    ┌─────────────────────┐
   │  FastAPI /query      │    │  Conwo MCP Server    │    │  Sandboxed worker   │
   │  Deep Search loop    │    │  (Streamable HTTP)   │    │  (Docker, optional) │
   │  + Anthropic API     │    │                      │    │                     │
   └─────────┬────────────┘    └──────────┬───────────┘    └──────────┬──────────┘
             └───────────────┬────────────┘                            │
                             ▼                                          │
   ┌─────────────────────────────────────────────────────────────┐     │
   │           ★ ONE Conwo tool layer (10–14 tools) ★            │◄────┘
   │   Same Python handlers serve both adapters.                  │
   │   Adapter A: Anthropic tool-use JSON schema                  │
   │   Adapter B: MCP `tools/list` + `tools/call`                 │
   └────┬────────────┬───────────────────┬──────────────────┬─────┘
        ▼            ▼                   ▼                  ▼
   ┌─────────┐ ┌──────────────┐ ┌──────────────┐ ┌────────────────────┐
   │ wiki/   │ │ Jira mirror  │ │ PMS APIs     │ │ Conversation +     │
   │ + vector│ │ Postgres     │ │ (service     │ │ feedback store     │
   │ index   │ │ + OpenSearch │ │ accounts)    │ │ Postgres           │
   └─────────┘ └──────────────┘ └──────────────┘ └────────────────────┘
        ▲            ▲                ▲                  ▲
        │            │                │                  │
   ┌────┴────────────┴────────────────┴──────────────────┴─────┐
   │   Scheduled ingestion workers (cron / queue)              │
   │   Drive → wiki/, Jira → Postgres, PMS defaults → cache    │
   └───────────────────────────────────────────────────────────┘
```

---

## 4. Decision table

| Option | What it is | Capability vs Claude Code terminal | Security risk | Scalability | Effort to build | Recommend? |
|--------|-----------|------------------------------------|--------------|-------------|---------------|----------|
| **A** Single-shot RAG | Backend fetches top-k wiki/Jira, sends prompt to API once. No tool loop. | ~30%. Misses anything not in initial retrieval. | Lowest. | Highest (cacheable). | Already exists as the orchestrator's `run_single_shot()`. | No. Strictly worse than B. |
| **B** API + controlled tools *(current "Deep Search")* | Anthropic tool_use loop, ≤8 rounds, 9–14 named tools. | ~70–80% on Q&A, debugging, config lookup. Loses on cross-repo investigation and ad-hoc shell. | Medium. Bounded by tool surface. | High. Stateless per request. | ✅ ~70% done. Needs SSO + audit + budgets + 3–5 more tools. | **Yes — primary path for org users.** |
| **C** API + remote MCP server | Same tools, exposed via MCP `tools/list` + `tools/call` over HTTPS. | Same as B. Different transport. | Same as B if behind SSO. | Same as B. | Wraps the same handlers — ~1–2 weeks once B exists. | Yes, **as the same investment** — see strategic note below. |
| **D** API + sandboxed agent workers | Per-session Docker container with ephemeral repo clone, allowlisted bash, MCP tools. | ~90–95% — close to Claude Code in terminal, safely. | High to operate; low per request thanks to sandbox. | Hardest. Stateful infra, container orchestration, cost. | 6–8 weeks. Real work. | Only after B+C ship and telemetry shows users hitting the controlled-tools ceiling. **Future option.** |
| **E** Server-side Claude Code headless *(current "Claude Code" mode)* | Backend spawns `claude -p` subprocess. Stream events back. | Equal to Claude Code on the backend machine. | **Very high for org deployment.** Single Claude session, shared filesystem, shared billing seat. | Per-process. Doesn't scale. | Already built — local-dev only. | Useful **only when backend == user's laptop** (local-dev mode). Not for shared deployment. |
| **F** Claude Code + remote MCP for power users | Power user runs their own Claude Code; it connects to our MCP server (Option C) for Conwo-specific tools. | Power user keeps their full Claude Code capability **plus** Conwo's curated tools. | Low — auth at MCP server boundary; user runs CLI under their own credentials. | High. Each power user is their own client. | Same effort as Option C — both reuse the tool layer. | **Yes** for power users. Same investment as C. |

### Strategic insight

**B, C, and F share the same tool implementations.** Build one Python tool
layer, expose it through two adapters (Anthropic tool-use schema + MCP server)
and you serve all three audiences simultaneously. This is the architecture's
single biggest leverage point.

D (sandboxed workers) is the only option that requires fundamentally new
infrastructure. Don't build it on speculation.

---

## 5. Recommendation

**One sentence:** *Harden today's Deep Search into a real product (auth,
budgets, ingestion, audit), wrap the existing tool registry as a remote MCP
server, and defer sandboxed agent workers until usage data demands it.*

The investment is the tool layer. Everything else is plumbing around it.

### Why two adapters and not just MCP

Anthropic's Messages API now has an **MCP connector** that can call a remote
MCP server directly from the API. In principle, Adapter A (Anthropic tool-use
schema, used by `DeepQueryProvider`) and Adapter B (MCP server, used by power
users' Claude Code) could collapse into one server.

We deliberately keep both for now because:

1. The MCP connector is newer and ties us to a specific API surface that's
   still evolving; the direct tool-use schema is the mature path.
2. Our existing DeepQueryProvider, tool registry, sanitization, and audit
   trail are already wired against Adapter A — rewiring them through an
   MCP-connector hop adds latency and an extra failure mode for no immediate
   gain.
3. Both adapters call **the same Python handlers** — duplication is at the
   envelope layer (10–20 lines each), not at the implementation layer.

**Forward path:** when the MCP connector stabilizes (track via
`docs/agents-and-tools/mcp-connector` on Anthropic's docs), evaluate
collapsing to a single MCP-server source of truth. Estimated effort to switch
once we decide: ~1 week. Decision criterion: when the connector supports
prompt caching and our latency budget can absorb the extra hop.

---

## 6. Milestones and timeline

Realistic estimates for **one engineer** (multiply by 0.6 with two).

### M1 — Production-ready Deep Search (2–3 weeks)

Goal: today's Deep Search shippable to a 5–10 person internal beta.

- Replace `allowed_users.toml` with OIDC / SAML SSO behind FastAPI. Issue
  per-user JWTs.
- Audit-log every `/query` and every tool call (user, prompt, tool inputs
  sanitized, tool outputs hashed, model, tokens, cost).
- Per-user daily token budget (configurable). Hard cap before the LLM call.
- Sonnet → Haiku fallback for follow-up "small" turns to halve cost.
- Drop the current `/query/stream` (server-side Claude Code) from prod or
  gate it admin-only.
- Move `raw/feedback/answer_log.jsonl` + `raw/conversations/*.sqlite` to a
  shared Postgres instance.

### M2 — Pilot tools + scheduled ingestion (4–6 weeks)

Goal: org-wide pilot (50–100 users).

- Add 3–5 missing tools (see §8): `dependency_inspect`,
  `wiki_patch_proposal` (proposes patch, admin reviews), sync-status reads.
- **Per-user BUID allowlist** — `pms_runtime_values` reads `allowed_buids[]`
  from the JWT, refuses any BUID outside that list at the handler boundary.
  Source of the mapping is still open (IT directory vs. customer-ops-owned
  table) — that's a §11 question, but the deliverable in M2 is "scoping is
  enforced regardless of which source we settle on."
- Move Jira sync, Drive sync, PMS-default-properties refresh, embeddings
  rebuild onto a real cron (k8s CronJobs / GitHub Actions). Hands-off.
- Add a sparse vector index (OpenSearch / pgvector) for wiki search. Today
  it's keyword + path. Embeddings are a stub.
- Wiki write proposals stay admin-gated. The model can *propose* a patch
  via `wiki_patch_proposal`; an admin reviews and runs `apply_feedback.py`.
- Cost dashboard: spend per user, per tool, per query.

### M3 — Remote MCP server (2–3 weeks)

Goal: power users get the curated Conwo toolset in their own Claude Code,
without cloning the repo or running our backend locally.

- New `backend/mcp_server/` exposing `tools/list` + `tools/call` over
  Streamable HTTP. Same handlers as Adapter A, different envelope.
- OAuth token issued via Conwo gateway; bound to the same user identity as
  the web app.
- Per-user PMS BUID scoping carried via the OAuth token, not the request.
- Docs: how a power user adds `https://conwo.internal/mcp` to their
  `~/.claude/settings.json` and uses Conwo tools alongside their personal
  MCP integrations (atlassian, gmail, …).

> **Credentials asymmetry note** — When a power user calls a *Conwo* MCP
> tool like `pms_runtime_values`, the request hits *our* PMS service account
> (via env-var tokens on our backend), not the user's personal credentials.
> Their BUID access is governed by the JWT issued by our gateway, not by
> their own PMS login. This is deliberate — it gives consistent permissions
> across web and terminal — but it's not what a power user might assume.
> Document explicitly in M3 release notes.

### M4 — Sandboxed agent workers (6–8 weeks, only if needed)

Trigger: M2 telemetry shows ≥20% of queries hit "missing capability" labels
that mean "I needed to run something not in our tool list."

- Per-session ephemeral container (Docker / Firecracker / gVisor).
- Read-only repo clone, scratch workspace, allowlisted bash (`sqlite3 :ro`,
  `grep`, `rg`, `git log` — no `git push`, no network egress except to our
  MCP server).
- Audit + recording of every command.
- Hard wall-clock and cost limits per session.

### Total timeline

| Phase | Duration | Cumulative |
|------|--------|-----------|
| POC (already there) | done | week 0 |
| M1 (internal beta) | 2–3w | week 3 |
| M2 (org pilot) | 4–6w | week 9 |
| M3 (power-user MCP) | 2–3w | week 12 |
| M4 (sandboxed, optional) | +6–8w | week 20 |

Org-wide GA realistic at week 12 (≈3 months) with one engineer. With two
engineers in tight collaboration, expect ~0.75× — i.e. ~9 weeks to GA, not
6. (The gain is real but coordination overhead is non-zero.)

---

# Supporting rationale

The sections below explain *why* each part of the recommendation is what it
is. Read these if §1–§6 leaves a question.

---

## 7. The capability gap, framed correctly

The common framing is wrong. *"Claude Code can do X, the API can't"* makes it
sound like Anthropic withheld features. The accurate framing:

**Claude Code is a desktop application that bundles three components: a model
(via Anthropic's API), an agent runtime (the loop that turns model output into
tool execution), and a tool layer (Read, Write, Edit, Bash, Grep, WebFetch,
plus MCP plug-ins).**

The Anthropic API only ships component #1. Components #2 and #3 are open for
anyone to build. Claude Code is one implementation; our `DeepQueryProvider`
+ `ToolRegistry` is another. They differ in *which tools are wired up*, not
in what the model can do.

So when our user says *"Claude Code in terminal is more powerful,"* the
literal cause is:

| Claude Code in terminal has | Our backend tool layer has |
|---|---|
| `Read` over the whole filesystem | `wiki_read_page` over `wiki/` only |
| `Bash` (arbitrary commands) | `jira_named_query` (4 whitelisted SQL queries) |
| `Grep`/`Glob` over whole repo | `wiki_search`, `jira_search_ranked` (specific corpora) |
| `Edit`/`Write` (full repo write) | `feedback_record` only; no wiki writes |
| Personal MCP integrations (the user's own atlassian/gmail) | One service-account MCP (`.mcp.json` atlassian read-only) |
| The user's `CLAUDE.md` loaded as system context | Our own short `deep_system_prompt.py` instead |

**Every row is a deliberate scope choice, not a missing feature.** The
"missing power" you're measuring is the power we chose not to give the model
when a stranger (any browser user) is the one steering it.

Where this matters most: open-ended debugging. "Read CLAUDE.md and tell me
how Conwo answers PMS config questions" is trivial for terminal Claude Code
(one `Read` call) and *currently impossible* for our Deep Search (we don't
expose CLAUDE.md). We can fix that specific case by adding it to the wiki
search index. We can't fix the *general* case ("read any file you want")
without sandboxing.

---

## 8. The tool layer — what to expose, with permissions

These are the tools we should ship. The first 9 are built. The rest are M1–M2
additions.

### Read-only knowledge tools (any authenticated user)

| Tool | Purpose | Built? |
|------|---------|------|
| `wiki_search` | Keyword search across wiki pages. | ✅ |
| `wiki_read_page` | Read one wiki page, path-validated. | ✅ |
| `jira_search_ranked` | Search Jira SQLite with recency/status ranking; returns LATEST/HISTORICAL/STALE-OPEN buckets. | ✅ |
| `jira_get_ticket` | Read one Jira ticket by key (validated `^[A-Z]+-\d+$`). | ✅ |
| `jira_named_query` | One of 4 whitelisted SQL queries with positional `?` params. **No raw SQL.** | ✅ |
| `config_lookup` | Find PMS property name in wiki/configs/. | ✅ |
| `dependency_inspect` | "Module A depends on what? Used by what?" — reads `wiki/modules/<name>.md` frontmatter. | ⏳ M2 |
| `wiki_index_inspect` | Glob/list pages by type (`module`, `concept`, `entity`). | ⏳ M2 |

### Customer-scoped tools (BUID gated to user's permission set)

| Tool | Purpose | Built? |
|------|---------|------|
| `pms_default_properties` | Fetch metadata for a service (props, types, defaults). Reads env vars; never logs tokens. | ✅ |
| `pms_runtime_values` | Fetch live config for one BUID ± OFFICEID/ROOMID/ROLE. Returns `status: credentials_required` if no token. | ✅ |

For org rollout: the OAuth/JWT identity must carry the list of BUIDs the user
is allowed to query. The tool handler enforces that — *not* the prompt.

### Write tools (admin only)

| Tool | Purpose | Built? |
|------|---------|------|
| `feedback_record` | Wraps `scripts/record_feedback.py`. Anyone may call. | ✅ |
| `wiki_patch_proposal` | Generates a `Feedback Notes` block proposal. **Does NOT write the wiki.** Admin reviews and runs `apply_feedback.py`. | ⏳ M2 |
| `admin_trigger_jira_sync` | Spawns `jira_sync.py --incremental`. Admin only. | ✅ (in `admin_api.py`, not yet wrapped as an LLM tool — and probably shouldn't be) |

**Wiki writes stay admin-gated** even when LLMs are involved. That's the
right behavior. `apply_feedback.py` already enforces idempotent
`<!-- feedback:<id> -->` markers so the same suggestion never double-patches.
Don't auto-apply.

### Why no `bash`, no raw SQL, no `Edit`?

Because the trust boundary for browser users is the FastAPI tool layer.
Anything you put behind that boundary can be invoked by any authenticated
user. Browser users do not have OS-level identity for us to audit against.
If you want them to run `git log`, give them a tool called `recent_changes`
that runs `git log` with safe flags — not bash.

The model can't escape the registry. The registry is the policy.

---

## 9. Production concerns at scale

### Auth & RBAC

- **SSO via OIDC** (Okta, Google Workspace, Auth0, depending on org). Issue
  short-lived JWTs.
- JWT claims include: `email`, `groups[]`, `allowed_buids[]`. Tool handlers
  consume `allowed_buids[]` directly; the LLM never sees it.
- Three roles: `viewer` (read-only tools), `contributor` (+ feedback writes),
  `admin` (+ sync, + patch apply, + Claude Code mode if we keep it).
- Replace `config/allowed_users.toml` after M1.

### Audit logging

Every `/query` writes one structured record:

```jsonc
{
  "ts": "2026-05-20T12:34:56Z",
  "user_email": "rudra.khare@moveinsync.com",
  "user_groups": ["wis-platform"],
  "conversation_id": "abc123",
  "model": "claude-sonnet-4-6",
  "rounds": 4,
  "tools": [
    { "name": "wiki_read_page", "input_hash": "sha256:…", "ok": true },
    { "name": "pms_runtime_values", "input_hash": "sha256:…", "ok": true }
  ],
  "input_tokens": 8421,
  "output_tokens": 612,
  "cost_usd": 0.034,
  "answer_id": "9f2c1ad03b81"
}
```

Inputs are *hashed*, not logged, to avoid persisting PII / customer config
values in the audit trail. Outputs link to the existing `answer_log.jsonl`
which is already PII-aware.

### Rate limits + queueing

- **Per-user**: N requests/min, M tokens/day. Burst bucket.
- **Per-org**: global circuit-breaker on Anthropic cost spend.
- **Queueing**: not needed for single-LLM-call requests. *Required* when M4
  sandboxed workers land (containers have boot time).

### Caching

- **Tool result cache** by `(tool_name, sanitized_input_hash)` for ~60s.
  Cuts redundant `wiki_search` calls within a conversation.
- **Prompt prefix cache** — Anthropic prompt caching for the deep-search
  system prompt + tool definitions. Free reuse across calls.
- **Embeddings cache** in the vector index — never recompute.

### Indexes

Today:
- `wiki/` — Python in-memory keyword index, rebuilt at startup.
- `tickets.sqlite` — full-text via `LIKE COLLATE NOCASE` (slow over 50k+
  tickets).
- `raw/jira/embeddings.db` — stub, **not implemented** (`scripts/jira_embed.py`).

For pilot:
- Move wiki search to a real index (OpenSearch or pgvector). 5–10× faster
  with semantic search.
- Add Jira embeddings (Voyage AI or Cohere via Anthropic, stored in pgvector).
- Keep SQLite for chat history until ~50 concurrent users; then Postgres.

### Secrets & PII

- **Anthropic API key** — browser user provides per-request, stored only in
  `localStorage`, never echoed back. Server never persists it. Already the
  case.
- **PMS bearer tokens** — env vars on the backend host. `ToolRegistry`
  sanitizer strips them from any string that ever leaves the trust boundary.
  Already the case.
- **MCP integrations** — for Phase 2 service-account model: Conwo backend
  uses a service-account atlassian token, not a personal one. For Phase 3
  power-user MCP: the user's own Claude Code uses *their* MCP credentials;
  our server doesn't see them.
- **PII in feedback / conversation store** — both stores currently treat
  question + answer text as opaque. Add a redaction pass if real customer
  data starts appearing in questions (emails, customer IDs).

### Cost control

Tool use multiplies tokens (each round re-sends the conversation). A 4-round
Deep Search query costs roughly 4× a single completion at the same final
quality.

**Back-of-envelope** (Claude Sonnet 4.6 list pricing, no caching):

| Inputs | Estimate |
|--------|---------|
| Avg query: 25k input + 1k output × 4 rounds | ~$0.12 per query |
| 50 users × 20 queries/day × 22 working days | **~$2,640/month uncached** |
| With prompt caching on system prompt + tool defs (~60% reduction) | **~$1,100/month** |
| With Haiku fallback for short follow-up turns (~30% further) | **~$770/month** |

Scale to 200 users with the same usage and the cached number is ~$4.4k/mo —
real money but not catastrophic. The numbers blow up if average rounds
double (open-ended debugging questions); cap `max_rounds` to 8 (already done)
and surface the *cost per query* in the trace so users see it.

- Per-user daily budget hard-cap **before** the call to Anthropic.
- Switch the system prompt + tool definitions to use Anthropic's **prompt
  caching** (ephemeral 1h).
- Model fallback: route follow-up "small" turns (e.g., "summarize the trace")
  to Haiku instead of Sonnet.
- Surface live spend in the admin dashboard. Slack alert at 70% / 90% of
  monthly budget.

### Failure modes & fallbacks

| Failure | Behavior |
|--------|----------|
| Anthropic API down or rate-limited | Return cached previous answer if available; otherwise error with retry-after. |
| One backend tool fails (Jira DB locked, PMS API 401) | Registry returns a structured error; the loop continues with other evidence; answer's `Missing context:` block surfaces the gap. |
| PMS token expired / missing | `pms_runtime_values` returns `status: credentials_required` (already implemented). Model is instructed to answer from wiki + Jira instead. |
| Sandboxed worker (M4) container OOM | Kill, return partial trace, mark session failed. Never silently truncate. |
| Wiki sync stale | Admin dashboard surfaces last-sync timestamp; user-facing answer adds *"wiki last refreshed N days ago"* to the trace. |
| Cost cap hit | Hard 402 before the call. Admin gets a Slack notification. |

### Monitoring (must-have for pilot)

- **Latency**: p50/p95/p99 per endpoint, per mode.
- **Token spend**: per user, per tool, per day.
- **Tool error rate**: per tool. A spike in `pms_runtime_values` errors
  signals expired tokens.
- **Conversation quality**: weekly summary of feedback scores ≤3, grouped by
  label.
- **Drift**: number of pages added/changed in wiki by `apply_feedback.py`
  vs. by humans. The model should not be the dominant editor.

---

## 10. Risks & mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|----------|------|----------|
| User asks model to exfiltrate secrets via a tool input | Medium | High | Sanitizer regex in `ToolRegistry` strips Bearer/JWT/long-hex from trace; tool inputs are size-capped. Audit log records hash, not raw. |
| Browser user with admin token causes destructive Claude Code subprocess in shared deploy | High if we expose `mode=agent` outside local-dev | Critical | Deprecate `/query/stream` for shared deploy. Keep it local-only. Power users get Option F (their own Claude Code + MCP). |
| Cost spirals on rollout | Medium-high | Medium | Per-user budgets *before* M2 pilot, not after. Prompt caching. Model fallback. |
| Wiki gets polluted by auto-applied feedback | Low (current design is admin-gated) | High | Keep `apply_feedback.py` admin-only. Never give the LLM a tool that writes to `wiki/` directly. |
| Stale data (Jira sync down) leads to confidently wrong answers | Medium | Medium | Sync timestamp visible in trace. If staleness > 24h, answer banner: *"Jira mirror is N hours old."* |
| PMS BUID leakage — one user sees another customer's config | Low if scoping enforced | Critical | BUID allowlist lives in JWT claims, enforced in `pms_runtime_values` *handler*, never in prompt. |
| MCP server (Phase 3) becomes a backdoor if mis-deployed | Medium | High | Same auth boundary as `/query`. Mandatory OAuth + per-tool scopes. No anonymous access ever. |
| The model invents a config name that doesn't exist | Medium | Medium | Tool returns `not_found`; the model is system-prompted never to invent property names. Confidence: Low. |
| Vendor lock — Anthropic deprecates a model | Low per quarter | Medium | The orchestrator already names `claude-sonnet-4-6` in one place. Add a config-driven model selector. Consider testing one fallback model from a different vendor for resilience. |

---

## 11. Open questions for the manager

1. **SSO provider** — Okta, Google Workspace, Microsoft Entra? M1 needs this picked.
2. **Budget envelope** — what's the monthly Anthropic spend ceiling? See §9 cost back-of-envelope; ~$1.1k–$4.4k/mo at pilot scale with caching.
3. **PMS BUID allowlist source** — IT directory groups vs. a customer-ops-owned mapping vs. a Conwo-internal table? The *enforcement* is M2 work; the *source of truth* is your call.
4. **Power-user MCP audience** — how many engineers would actually use Option F vs the browser? Determines M3 priority.
5. **Are we OK with `apply_feedback.py` staying CLI-only**, or do we need an admin UI to review and apply patches from the browser? (Currently CLI-only; admin endpoint exists but no UI.)

---

## 12. Appendix — reference links

- **Anthropic Messages API tool use** — *Tool use with Claude*, [platform.claude.com](https://platform.claude.com/docs/en/docs/agents-and-tools/tool-use/overview). Client tools run in the developer's app; the API only returns `tool_use` blocks. Tool definitions need `name`, `description`, `input_schema`.
- **MCP architecture** — *Model Context Protocol — Architecture overview*, [modelcontextprotocol.io/docs/learn/architecture](https://modelcontextprotocol.io/docs/learn/architecture). Host → Client → Server. Local stdio or remote Streamable HTTP. Primitives: tools / resources / prompts.
- **Claude Code headless** — `claude -p <prompt> --output-format=stream-json --verbose` emits NDJSON events (`system/init`, `assistant` with `tool_use` blocks, `user` with `tool_result` blocks, `result`). We already consume this in `backend/providers/claude_code_agent.py`.
- **Internal docs to read** — `docs/feedback-loop-workflow.md`, `docs/pms-runtime-api-playbook.md`, `docs/modes-and-traces.md`, `docs/live-config-debug.md`.

---

*End of document.*
