# Manage-Agents Redesign + Description + Hard-Delete — Design

_Date: 2026-06-18 · Status: approved for planning · Branch: `claude/hopeful-roentgen-cda2f4`_

## 1. Problem
The admin "Manage Agents" page shows agents in a plain table and the create form takes
only a name. Requirements:
1. **Create** form gains a single-line **description** ("what this agent does"), supplied by the user.
2. **List** becomes a **card grid** (per the shared marketplace-style mockup): each agent shown as a
   glowing-outline, futuristic card with **name + small description + id** and **Rename / Archive / Delete**
   actions.
3. A real **Delete** (permanent) action in addition to **Archive** (soft).

## 2. Decisions (approved)
- **Description is a separate UI label**, distinct from the agent's `identity` (which stays
  auto-generated/LLM and independent). New DB column.
- **Delete = permanent hard-delete**: removes the DB row AND the `agents/<slug>/` directories,
  irreversible, behind a typed confirm. **Archive = soft** (status='archived', reversible, drops from
  switcher) — unchanged. Conwo/Infosec protected from both.
- Each card's glowing outline uses **that agent's own accent color** (on-brand with per-agent theming).
- Non-goals: description does NOT feed the system prompt; single-line only (no rich text); no bulk actions.

## 3. Backend

### 3.1 Schema — `description` column
- `migrations/postgres/100_agents.sql`: add `description TEXT NOT NULL DEFAULT ''` to the table DDL
  (for fresh DBs) and seed Conwo/Infosec descriptions in the INSERT.
- `migrations/postgres/103_agents_description.sql` (new, idempotent): `ALTER TABLE agents ADD COLUMN
  IF NOT EXISTS description TEXT NOT NULL DEFAULT '';` then `UPDATE agents SET description=... WHERE
  id='conwo' AND description='';` (and infosec) so existing dev/test DBs get non-empty built-in
  descriptions. Guarded by `description=''` so re-runs are no-ops.
  - Conwo: `Product, configuration, and debugging answers for WorkInSync.`
  - Infosec: `Information-security questions from the organization's security knowledge base.`

### 3.2 Registry
- `AgentSpec` already has `description: str = ""`. Change `_row_to_spec` to
  `description = r["description"] or r["identity"]` (real column, fallback to identity so built-ins/older
  rows display something). `SELECT *` already fetches the new column.

### 3.3 Provisioning (`backend/agent_provisioning.py`)
- `create_agent(name, created_by, description="")`: add `description` param; include it in the INSERT
  column list + values. Identity generation unchanged (independent).
- `update_agent(agent_id, *, display_name=None, identity=None, description=None)`: add `description`
  to the dynamic `SET` builder (same pattern as the others).
- New `delete_agent(agent_id)`: if `agent_id in PROTECTED` → raise `AgentError`; resolve the agent's
  dirs via `agent_registry.get(agent_id)` (its `wiki_dir`/`raw_dir` → parent `agents/<slug>/`), then
  `DELETE FROM agents WHERE id=%s`, then `shutil.rmtree(agents/<slug>, ignore_errors=True)`, then
  `agent_registry.invalidate_cache()`. Order: delete row first (source of truth), then best-effort dir
  cleanup. Resolve the dir to remove as `wiki_dir.parent` (== `<base>/agents/<slug>`); guard that it is
  under the data base dir before rmtree (safety).

### 3.4 Endpoints (`backend/api.py`)
- `CreateAgentRequest`: add `description: str | None = None`. `create_agent_endpoint` passes
  `description=req.description or ""`.
- `UpdateAgentRequest`: add `description: str | None = None`; `update_agent_endpoint` forwards it.
- `delete_agent_endpoint` (the existing `DELETE /admin/agents/{id}`): add query param `hard: bool = False`.
  `hard=True` → `agent_provisioning.delete_agent(id)` (catch `AgentError` → 400) returns
  `{"status":"deleted","id":id}`; otherwise → existing `archive_agent` path (unchanged).
- `_agent_public` returns the real `description` (`a.description`).

## 4. Frontend

### 4.1 `api.service.ts`
- `createAgent(name: string, description?: string)` → POST `{name, description}`.
- `updateAgent(id, patch: {display_name?, identity?, description?})` — extend the patch type.
- `archiveAgent(id)` — unchanged (`DELETE /admin/agents/{id}`).
- `deleteAgent(id)` → `DELETE /admin/agents/{id}?hard=true`.
- `Agent.description` already exists.

### 4.2 `manage-agents.ts` (redesign)
- **Create card:** Name input **+ single-line Description input** (placeholder "One line: what this agent
  does"), Create button. On success: existing success card; pass description to `createAgent`.
- **List → responsive card grid** (CSS grid, ~320px min cards). Each card:
  - Accent dot + **display_name** (title)
  - **description** (small muted line; falls back to "—" if empty)
  - **id** (mono, subtle)
  - Actions row: **Rename** (inline edit: name + description fields with Save/Cancel),
    **Archive**, **Delete**. Conwo/Infosec → a "built-in" badge instead of Archive/Delete.
  - **Glowing outline:** `border` + `box-shadow` tinted by `agent.accent` (e.g.
    `box-shadow: 0 0 0 1px <accent>55, 0 6px 24px -8px <accent>66`), subtle hover lift. Reads well on
    both light (Conwo) and dark themes.
- **Delete confirm:** clicking Delete reveals an inline typed-confirm ("type `<id>` to delete") + a
  confirm button enabled only on exact match → `deleteAgent(id)` → refresh list + `AgentService.loadAgents()`.
- **Rename/edit:** inline edit mode toggled per card; Save calls `updateAgent(id, {display_name, description})`
  then refreshes.
- After create/archive/delete/rename: call `agentSvc.loadAgents()` so the switcher stays in sync.

### 4.3 Styles (`manage-agents.scss`)
- `.agent-grid { display:grid; grid-template-columns: repeat(auto-fill, minmax(320px,1fr)); gap:16px; }`
- `.agent-card` glowing outline via accent (set per-card with an inline `--card-accent` custom property
  bound to `agent.accent`); rounded, padded, surface background, hover lift.
- Buttons reuse the existing `.primary`/`.danger` styles; add a subtle `.ghost` for Rename/Archive.

## 5. Error handling
- Create with blank description → allowed (stored as ''); list shows "—".
- Hard-delete of Conwo/Infosec → backend 400 (`AgentError`); frontend shows the error; UI also hides
  Delete for built-ins so it shouldn't be reachable.
- Hard-delete dir cleanup is best-effort (`ignore_errors=True`) and guarded to stay under the data dir;
  a missing dir never fails the call (row removal is the source of truth).
- Deleting the currently-active agent: after delete, `loadAgents()` runs; if the active id vanished,
  `AgentService.loadAgents()` already falls back to `conwo` (existing behavior).

## 6. Testing
- Backend: `create_agent(..., description=...)` persists it; `_agent_public` returns it; `delete_agent`
  removes row + dir and is protected (raises for conwo); `DELETE ?hard=true` removes vs default archives.
  Full suite stays green (5 known failures only).
- Frontend: `api.service.spec.ts` — createAgent sends description, deleteAgent hits `?hard=true`; `ng build` clean.

## 7. Definition of done
- Create form has Name + Description; new agents store and display the description.
- Manage Agents shows a glowing card grid (name + description + id + Rename/Archive/Delete), each card
  glowing in its agent's accent; Conwo/Infosec protected.
- Hard delete removes the row + `agents/<slug>/` dirs (typed confirm); archive still soft.
- Full backend suite green (5 known failures only); `ng build` clean.
