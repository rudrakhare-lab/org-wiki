# Self-Service Agent Creation — Design

_Date: 2026-06-17 · Status: draft for owner review · Builds on: the multi-agent system already on `main` (Conwo + Infosec; backend PR #3, theme PR #5)_

---

## 0. Plain-language summary

Today, adding an agent (like we did for Infosec) means editing a config file and
redeploying. This feature lets an **admin create a brand-new, fully-working agent at
runtime, from the UI, by typing a name** — no code, no deploy.

The admin opens a **"Create Agent"** tab, types a name (e.g. *Legal*), clicks Create.
The system instantly provisions a complete agent: its own empty knowledge base, its own
dashboard, traces, ingest page, and knowledge graph, plus a distinct accent color. The
admin then ingests documents on the agent's Ingest page, and **that agent's knowledge,
graph, and answers come only from those documents.**

The crucial realization that makes this small rather than huge: **everything that makes an
agent work — the orchestrator, all the tools, the ingest pipeline, the query workflow, the
graph/index builder, and the per-agent dashboard/traces/conversations — is already shared
code keyed by `agent_id`.** A new agent inherits all of it automatically. The only genuinely
new work is (a) making the agent *list* dynamic (a DB table instead of a baked config file),
(b) a **provisioning service** that sets up a new agent's files + row, and (c) the **Create
Agent UI** + per-agent accent color.

---

## 1. Goals & non-goals

### Goals
- An admin creates a complete agent **at runtime from the UI** by name; it appears in the
  switcher immediately with its own empty KB, dashboard, traces, ingest, and graph.
- Each created agent is a **generic, wiki-only** agent (no Jira/PMS) that learns **only**
  from ingested docs — "by name, not by concept."
- Each created agent uses the **proven Conwo ingest/query methodology** (shared code) with a
  **generic, domain-agnostic page-type schema**.
- Each agent gets an **auto-assigned distinct accent color** on a shared dark theme.
- Admin can **rename** and **archive/delete** agents.
- Production-grade: works under **multiple replicas**, atomic provisioning with rollback,
  validated LLM use with safe fallback.

### Non-goals
- Created agents do **not** get Jira/PMS or `agent`/Claude-Code mode (api/Deep-Search only),
  matching Infosec.
- **No per-agent custom CLAUDE.md authoring** — the methodology is shared; identity is
  auto-generated + editable.
- **No per-agent access control** in v1 — every approved user sees every agent (same as
  Conwo/Infosec today). Per-agent permissions are a future phase.
- **No domain-tailored page-type names** — one generic schema for all created agents
  (decided: Option 2). Domain specificity emerges from ingested content.
- Conwo and Infosec keep their existing behavior/appearance.

---

## 2. Key decisions (all settled in brainstorming)

| # | Decision |
|---|----------|
| D1 | Agents move from `config/agents.toml` → a Postgres **`agents` table** (dynamic). Conwo + Infosec become seeded rows. |
| D2 | A created agent = **generic wiki-only clone**: empty KB, wiki+ingest tools only, `modes=["api"]`, `has_jira/has_pms=false`. |
| D3 | **One shared generic Conwo-methodology ingest schema** for all non-Conwo agents (sources/concepts/entities/relationships/decisions/topics). Conwo keeps its WorkInSync schema. Driven by a `schema_kind` flag. (This also fixes Infosec, which today wrongly uses the WorkInSync schema.) |
| D4 | **Identity** is auto-generated from the name via one Anthropic call at create time, **validated**, with a **template fallback**; it is **editable** by the admin afterward. |
| D5 | **Theme:** shared dark base + an **auto-assigned accent color** derived deterministically from the slug (Option B). Conwo stays light; Infosec stays violet. |
| D6 | Access: **all approved users** see all agents. Management: admin can **rename** + **archive/delete** (Conwo/Infosec protected). |
| D7 | Per-agent `CLAUDE.md` is **not** in the runtime path for these agents; a templated one is written to disk for documentation/structure parity only. |

---

## 3. Architecture — dynamic DB-backed registry

New migration `migrations/postgres/100_agents.sql` — table `agents`:

| Column | Notes |
|--------|-------|
| `id` TEXT PK | slug (kebab-case), e.g. `legal` |
| `display_name` TEXT | e.g. `Legal` |
| `identity` TEXT | the LLM-generated, editable purpose line |
| `accent` TEXT | hex color, auto-assigned from slug |
| `modes` TEXT[] | default `{api}` |
| `has_jira` BOOL / `has_pms` BOOL | default false |
| `tools` TEXT[] | default wiki+ingest allowlist (same as Infosec) |
| `schema_kind` TEXT | `generic` (created/infosec) or `workinsync` (conwo) |
| `wiki_dir` / `raw_dir` / `claude_md` TEXT | paths (relative; resolved under `CONWO_DATA_DIR`) |
| `theme_base` TEXT | `light` (conwo) or `dark` (infosec + created) |
| `status` TEXT | `active` / `archived` |
| `created_by` TEXT, `created_at` TIMESTAMPTZ |

- **Seed Conwo + Infosec** as rows in the migration (Conwo: `has_jira/has_pms=true`,
  `tools={*}`, `schema_kind=workinsync`, paths `wiki`/`raw`/`CLAUDE.md`, `theme_base=light`;
  Infosec: wiki-only, `schema_kind=generic`, `agents/infosec/*`, `theme_base=dark`, its violet accent).
- **`backend/agent_registry.py` refactor:** load `AgentSpec`s from the DB instead of the
  TOML, behind a **short-TTL cache** (e.g. 30s) so a create on one replica becomes visible on
  all replicas within the TTL. `AgentSpec` gains `accent`, `schema_kind`, `theme_base`,
  `status`. Public API (`get`/`all`/`default`) unchanged in shape; `all()` returns only
  `active` agents. `config/agents.toml` is removed (or kept only as a one-time seed reference).

---

## 4. Provisioning service — `create_agent(name, created_by)`

New `backend/agent_provisioning.py`. Steps, **atomic with rollback**:

1. **Slug + validate** — derive kebab-case slug from name; reject blanks, duplicates
   (DB unique constraint), and a **reserved blocklist** (`conwo`, `infosec`, `admin`, `api`,
   `agents`, `health`, …).
2. **Accent** — deterministic hue from `sha1(slug)` → a pleasant HSL → hex (good contrast on
   dark base).
3. **Identity (LLM)** — one Anthropic call: "Given an internal knowledge agent named `<Name>`,
   write a 1–2 sentence identity…". **Validate** (non-empty, length-bounded, no injection);
   on any failure/timeout **fall back** to `"You are the <Name> assistant, answering questions
   from the organization's <Name> knowledge base. Answer only from ingested documents."`
   Creation never blocks on the LLM.
4. **Filesystem (PVC)** — create `agents/<slug>/wiki/` (+ seeded `index.md`),
   `agents/<slug>/raw/`, and a **templated `CLAUDE.md`** (generic methodology + name; for
   parity/docs only).
5. **DB row** — insert with `status=active`.
6. **Activate** — invalidate the registry cache; build the agent's (empty) wiki index.

On any failure after partial work: **roll back** (remove created dirs + DB row) so there are
no half-created agents. The whole operation is **idempotent** by slug.

---

## 5. Generic ingest schema (shared)

Refactor the ingest plan/execute prompts (`backend/ingest_api.py`) so the embedded page-type
schema is **selected by `agent.schema_kind`**:
- `workinsync` (Conwo only) → current schema (modules/configs/entities/cross-module/decisions).
- `generic` (Infosec + all created agents) → neutral Conwo-methodology schema:
  `sources/`, `concepts/`, `entities/`, `relationships/` (cross-topic), `decisions/`, `topics/`,
  with the same frontmatter discipline, bidirectional `[[wikilinks]]`, `index.md`/`log.md`
  conventions, and the same plan→execute→rebuild-index flow.

The two schema strings live as named constants; the prompt renderer picks one. No tool or
orchestrator changes — only the prompt text the planner/executor receives. Wiki write-tool
path validation is relaxed to allow the agent's own generic subtrees.

---

## 6. Theme — per-agent accent on a shared base

- `GET /agents` returns `accent` and `theme_base` per agent.
- Frontend `AgentService` already drives theming. Extend it to, for the active agent:
  set the `theme-<base>` body class (`dark` for created agents) and set `--accent`
  (+ derived `--accent-hover`/`--accent-ring`/glow) from `agent.accent` as an inline custom
  property on `<body>`. The existing dark theme tokens + the `--mt-*` toggle vars consume
  `--accent`, so each agent glows in its own color with **zero per-agent CSS**.
- Conwo → `light` base (unchanged). Infosec → `dark` + its violet accent (unchanged).
  Created agents → `dark` + their auto hue.
- Anti-flash pre-boot script extended to also set the accent from the persisted agent.

---

## 7. Frontend — Create Agent + management

- **New admin route/section "Create Agent"** (admin-gated): a centered **name input + Create
  Agent** button. On submit → `POST /admin/agents` → on success, the new agent is added to the
  switcher and selected. Show the generated **identity** (editable field) + **accent preview**.
- **Manage Agents** list (in Admin): rename (`display_name`/`identity`), archive/delete (typed
  confirm), per agent. Conwo/Infosec shown as protected (no delete).
- Everything else (that agent's Ask/Dashboard/Traces/Ingest/Graph) **already works** via the
  existing agent-scoped routes — nothing new per surface.

---

## 8. Endpoints (admin-gated)

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/admin/agents` `{name}` | provision a new agent (returns the created agent) |
| `PATCH` | `/admin/agents/{id}` `{display_name?, identity?}` | rename / edit identity |
| `DELETE` | `/admin/agents/{id}` | archive/delete (cleanup; Conwo/Infosec protected) |
| `GET` | `/agents` | list (now DB-backed; already exists) |

Delete cleanup removes the agent's dirs and its agent-scoped rows (conversations, messages,
trace_sessions) within a transaction; archive (soft) is the default, hard-delete behind an
explicit flag + typed confirm.

---

## 9. Production hardening

- **Multi-replica:** DB row is the source of truth; agent dirs live on the **shared PVC**;
  registry uses a **short-TTL cache** + each replica **lazily builds** a new agent's index on
  first use → eventual consistency within the TTL. No cross-replica RPC needed.
- **Atomic create + rollback**; unique-slug constraint; reserved-name blocklist.
- **LLM** is validated + has a deterministic fallback → never blocks or corrupts creation.
- **Delete** is guarded (typed confirm, Conwo/Infosec protected, transactional cleanup).
- **Backward compatible:** Conwo/Infosec seeded identically to today; `agent_id` defaulting to
  `conwo` everywhere is preserved.

---

## 10. What's reused (so scope stays sane)

Unchanged, inherited by every new agent automatically (all keyed by `agent_id`):
orchestrator, tool registry + all tools, preflight, deep/query prompts, wiki retriever +
per-agent index, graph endpoint, ingest pipeline, conversations/traces/dashboard scoping,
the `X-Agent-Id` middleware + frontend switcher. **The new code is only:** the `agents` table
+ registry-reads-DB, the provisioning service, 3 admin endpoints, the generic-schema prompt
split, the Create-Agent/Manage-Agents UI, and per-agent accent theming.

---

## 11. Phasing & effort (Claude-built; each phase ends with tests + a Conwo/Infosec-regression gate)

**Backend milestone**
| Phase | Scope | Effort |
|------|-------|--------|
| 1 | `agents` table + seed Conwo/Infosec + registry reads DB (cache/TTL); no behavior change | ~1.5–2 d |
| 2 | Generic ingest schema split by `schema_kind` (fixes Infosec too) | ~1 d |
| 3 | Provisioning service + LLM identity (validate/fallback) + accent + create/rename/delete endpoints; curl-verified | ~2–3 d |

**Frontend milestone**
| Phase | Scope | Effort |
|------|-------|--------|
| 4 | Create-Agent + Manage-Agents UI; per-agent accent theming; anti-flash accent | ~2–3 d |
| 5 | End-to-end + multi-agent/multi-replica verification | ~1 d |

**Total ≈ 7.5–10 working days**, ≈2–2.5 calendar weeks with review gates. Written as two
plans (backend Phases 1–3, then frontend Phases 4–5), mirroring how the multi-agent feature
was built.

---

## 12. Risks & mitigations

| Risk | Mitigation |
|------|-----------|
| Removing the TOML breaks startup if DB seed missing | Migration seeds Conwo/Infosec; registry falls back to a built-in default for `conwo` if the table is somehow empty |
| Multi-replica staleness (new agent not visible) | Short-TTL cache + lazy index build → visible within seconds; acceptable |
| LLM identity bad/slow | Validate + deterministic template fallback; never blocks create |
| Half-provisioned agent on failure | Atomic create with rollback; idempotent by slug |
| Generic schema page types rejected by write tools | Relax path validation to the agent's own subtrees |
| Accidental agent deletion / data loss | Soft-archive default; typed confirm for hard delete; Conwo/Infosec protected |

---

## 13. What I need from the owner

1. **Approve this design** (or flag changes).
2. Later, nothing required to *create* agents — it's self-service. (Real domain docs are
   ingested per agent by whoever owns that agent.)
