# Manage-Agents Redesign + Description + Hard-Delete Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Add a user-supplied one-line description to agents, redesign the admin Manage-Agents page as a glowing accent card grid (name + description + id + Rename/Archive/Delete), and add a permanent hard-delete alongside soft archive.

**Architecture:** New `description` column on `agents` (separate from `identity`), threaded through registry → provisioning → endpoints → frontend. New `delete_agent` (hard: row + `agents/<slug>/` dirs, protected) exposed via `DELETE /admin/agents/{id}?hard=true`. Frontend Manage-Agents component rebuilt as a card grid; each card's outline glows in that agent's accent.

**Tech Stack:** Python 3.13 + pytest (gate: `venv/bin/python -m pytest`), Postgres (psycopg3, idempotent SQL migrations applied by `init_db`), Angular standalone + signals + SCSS (gate: `npx ng build`).

## Global Constraints
- Worktree ONLY: `/Users/rudrakhare/Desktop/my-wiki/org-wiki/.claude/worktrees/hopeful-roentgen-cda2f4`, branch `claude/hopeful-roentgen-cda2f4`. NEVER touch `/Users/rudrakhare/Desktop/my-wiki/org-wiki/...` (user's main checkout).
- Python: `/Users/rudrakhare/Desktop/my-wiki/org-wiki/venv/bin/python`. Frontend cwd: `<worktree>/frontend`.
- Backend may run with `--reload`; controller ensures it is STOPPED before backend `.py` tasks (MT1, MT2). Subagents don't start/stop servers.
- Back-compat: full backend suite stays green except the 5 known pre-existing failures (`test_google_login_returns_500_when_client_id_not_configured`, `test_plan_returns_409_when_locked`, `test_list_offices_no_credentials_returns_credentials_required`, `test_lifespan_warns_when_anthropic_key_missing`, `test_pms_runtime_values_no_credentials`); 0 new. `ng build` clean. `ng test` can't run (Node-25 webstorage) — `ng build` is the frontend gate.
- Co-author trailer every commit: `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.

---

## Task MT1: Backend — `description` column end-to-end

**Files:**
- Modify: `migrations/postgres/100_agents.sql` (DDL + conwo/infosec seed)
- Create: `migrations/postgres/103_agents_description.sql`
- Modify: `backend/agent_registry.py` (`_row_to_spec`)
- Modify: `backend/agent_provisioning.py` (`create_agent`, `update_agent`)
- Modify: `backend/api.py` (`CreateAgentRequest`, `UpdateAgentRequest`, `_agent_public`, `create_agent_endpoint`, `update_agent_endpoint`)
- Test: `tests/test_agent_provisioning.py` (append)

**Interfaces:**
- Produces: `agents.description` column; `AgentSpec.description` = real column (fallback identity); `create_agent(name, created_by, description="")`; `update_agent(..., description=None)`; `_agent_public` returns real description; `POST /admin/agents {name, description?}`; `PATCH /admin/agents/{id} {…, description?}`.

- [ ] **Step 1: Append failing test** to `tests/test_agent_provisioning.py` (reuse existing `clean_db`, `no_extra_agents`, `tmp_path`, `monkeypatch`):

```python
def test_create_agent_stores_description(clean_db, no_extra_agents, tmp_path, monkeypatch):
    from backend import agent_provisioning as ap, agent_registry, config, db
    monkeypatch.setattr(config, "_BASE", tmp_path, raising=False)
    monkeypatch.setattr(agent_registry, "_BASE", tmp_path, raising=False)
    spec = ap.create_agent("Legal", created_by="a", description="Answers legal questions")
    assert spec.description == "Answers legal questions"
    with db.connection() as c:
        row = c.execute("SELECT description FROM agents WHERE id='legal'").fetchone()
    assert row["description"] == "Answers legal questions"


def test_update_agent_sets_description(clean_db, no_extra_agents, tmp_path, monkeypatch):
    from backend import agent_provisioning as ap, agent_registry, config
    monkeypatch.setattr(config, "_BASE", tmp_path, raising=False)
    monkeypatch.setattr(agent_registry, "_BASE", tmp_path, raising=False)
    ap.create_agent("Legal", created_by="a", description="old")
    ap.update_agent("legal", description="new desc")
    agent_registry.invalidate_cache()
    assert agent_registry.get("legal").description == "new desc"
```

- [ ] **Step 2: Run — FAIL** (`create_agent` has no `description` param; column missing):
`/Users/rudrakhare/Desktop/my-wiki/org-wiki/venv/bin/python -m pytest tests/test_agent_provisioning.py -k description -q`

- [ ] **Step 3: Migration `100` DDL + seed.** In `migrations/postgres/100_agents.sql`:
  - Add a column line to the `CREATE TABLE` (after `identity ... DEFAULT ''`):
    ```sql
    description  TEXT NOT NULL DEFAULT '',
    ```
  - In the INSERT, add `description` to the column list and a value for each built-in. The INSERT column list currently is `(id, display_name, identity, accent, theme_base, schema_kind, modes, tools, has_jira, has_pms, wiki_dir, raw_dir, claude_md, prompt_sections, created_by)` — insert `description` right after `identity`, and add the matching value as the 4th column in each VALUES row:
    - conwo: `'Product, configuration, and debugging answers for WorkInSync.'`
    - infosec: `'Information-security questions from the organization''s security knowledge base.'`

- [ ] **Step 4: Create `migrations/postgres/103_agents_description.sql`** (idempotent — for existing dev/test DBs):

```sql
-- 103_agents_description.sql — idempotent. User-facing one-line description per agent
-- (separate from the system-prompt identity). Shown in the Manage-Agents card grid.
ALTER TABLE agents ADD COLUMN IF NOT EXISTS description TEXT NOT NULL DEFAULT '';

UPDATE agents SET description = 'Product, configuration, and debugging answers for WorkInSync.'
WHERE id = 'conwo' AND description = '';

UPDATE agents SET description = 'Information-security questions from the organization''s security knowledge base.'
WHERE id = 'infosec' AND description = '';
```

- [ ] **Step 5: Registry `_row_to_spec`.** In `backend/agent_registry.py`, change the last line of the `AgentSpec(...)` build from `description=r["identity"],` to:
```python
        status=r["status"], description=(r["description"] or r["identity"]),
```
(`SELECT *` already fetches the new column.)

- [ ] **Step 6: Provisioning.** In `backend/agent_provisioning.py`:
  - `create_agent` signature → `def create_agent(name: str, created_by: str, description: str = ""):`
  - In the INSERT, add `description` after `identity` in BOTH the column list and the VALUES placeholders, and add `description` to the params tuple after `identity`. Final statement:
    ```python
    c.execute(
        "INSERT INTO agents (id, display_name, identity, description, accent, theme_base, "
        "schema_kind, modes, tools, has_jira, has_pms, wiki_dir, raw_dir, "
        "claude_md, prompt_sections, status, created_by) VALUES "
        "(%s,%s,%s,%s,%s,'dark','generic','{api}',%s,false,false,%s,%s,%s,'{}','active',%s)",
        (slug, name.strip(), identity, description, accent, _GENERIC_TOOLS,
         wiki_rel, raw_rel, claude_rel, created_by),
    )
    ```
  - `update_agent` signature → add `description: str | None = None`; add to the dynamic SET builder:
    ```python
    if description is not None: sets.append("description=%s"); params.append(description)
    ```

- [ ] **Step 7: API.** In `backend/api.py`:
  - `CreateAgentRequest`: add `description: str | None = None`.
  - `UpdateAgentRequest`: add `description: str | None = None`.
  - `_agent_public`: change `"description": a.identity` → `"description": a.description`.
  - `create_agent_endpoint`: pass description:
    ```python
    spec = agent_provisioning.create_agent(req.name, created_by=admin.get("email", "admin"),
                                           description=req.description or "")
    ```
  - `update_agent_endpoint`: forward description:
    ```python
    agent_provisioning.update_agent(agent_id, display_name=req.display_name,
                                    identity=req.identity, description=req.description)
    ```

- [ ] **Step 8: Run** description tests + provisioning + agents-table + endpoint tests:
`/Users/rudrakhare/Desktop/my-wiki/org-wiki/venv/bin/python -m pytest tests/test_agent_provisioning.py tests/test_agents_table.py tests/test_admin_agents_api.py -q`
Expected: PASS (the test DB applies migration 103 on session start).

- [ ] **Step 9: Commit**
```bash
git add migrations/postgres/100_agents.sql migrations/postgres/103_agents_description.sql backend/agent_registry.py backend/agent_provisioning.py backend/api.py tests/test_agent_provisioning.py
git commit -m "feat(agents): user-supplied description field (separate from identity)"
```

---

## Task MT2: Backend — hard delete

**Files:**
- Modify: `backend/agent_provisioning.py` (new `delete_agent`)
- Modify: `backend/api.py` (`delete_agent_endpoint` gains `hard` flag)
- Test: `tests/test_agent_provisioning.py` (append)

**Interfaces:**
- Consumes: `agent_registry.get`, `backend.config._BASE`, existing `PROTECTED`, `AgentError`.
- Produces: `delete_agent(agent_id)` (hard, protected); `DELETE /admin/agents/{id}?hard=true` → delete, default → archive.

- [ ] **Step 1: Append failing test**:

```python
def test_delete_agent_removes_row_and_dir(clean_db, no_extra_agents, tmp_path, monkeypatch):
    import pytest
    from backend import agent_provisioning as ap, agent_registry, config, db
    monkeypatch.setattr(config, "_BASE", tmp_path, raising=False)
    monkeypatch.setattr(agent_registry, "_BASE", tmp_path, raising=False)
    ap.create_agent("Legal", created_by="a", description="x")
    agent_dir = tmp_path / "agents" / "legal"
    assert agent_dir.is_dir()
    ap.delete_agent("legal")
    agent_registry.invalidate_cache()
    with db.connection() as c:
        assert c.execute("SELECT 1 FROM agents WHERE id='legal'").fetchone() is None
    assert not agent_dir.exists()
    # built-ins protected
    with pytest.raises(ap.AgentError):
        ap.delete_agent("conwo")
```

- [ ] **Step 2: Run — FAIL** (`delete_agent` undefined).

- [ ] **Step 3: Implement `delete_agent`** in `backend/agent_provisioning.py` (place after `archive_agent`):

```python
def delete_agent(agent_id: str):
    """Hard delete: remove the DB row AND the agent's on-disk dirs. Irreversible.
    Conwo/Infosec are protected. Dir removal is best-effort and guarded to stay under
    the data base dir."""
    if agent_id in PROTECTED:
        raise AgentError(f"'{agent_id}' is a built-in agent and cannot be removed")
    import shutil
    from backend import db, agent_registry
    from backend.config import _BASE

    spec = agent_registry.get(agent_id)              # resolve dirs before deleting the row
    with db.connection() as c:
        c.execute("DELETE FROM agents WHERE id=%s", (agent_id,))
    agent_registry.invalidate_cache()

    try:
        agent_dir = spec.wiki_dir.parent             # <base>/agents/<slug>
        base = _BASE.resolve()
        # Guard: only rmtree a real per-agent dir under the data base, named for this agent.
        if (spec.id == agent_id and agent_dir.name == agent_id
                and base in agent_dir.resolve().parents):
            shutil.rmtree(agent_dir, ignore_errors=True)
    except Exception:
        pass
```

- [ ] **Step 4: Update the endpoint** in `backend/api.py` — replace `delete_agent_endpoint` with:

```python
@app.delete("/admin/agents/{agent_id}")
def delete_agent_endpoint(agent_id: str, hard: bool = False,
                          admin: dict = Depends(_require_admin)):
    try:
        if hard:
            agent_provisioning.delete_agent(agent_id)
            return {"status": "deleted", "id": agent_id}
        agent_provisioning.archive_agent(agent_id)
        return {"status": "archived", "id": agent_id}
    except agent_provisioning.AgentError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

- [ ] **Step 5: Run** delete tests + endpoint tests:
`/Users/rudrakhare/Desktop/my-wiki/org-wiki/venv/bin/python -m pytest tests/test_agent_provisioning.py -k delete tests/test_admin_agents_api.py -q`
Expected: PASS.

- [ ] **Step 6: Commit**
```bash
git add backend/agent_provisioning.py backend/api.py tests/test_agent_provisioning.py
git commit -m "feat(agents): hard delete (row + dirs, protected) via DELETE ?hard=true"
```

---

## Task MT3: Frontend — API service methods

**Files:**
- Modify: `frontend/src/app/core/api.service.ts`
- Test: `frontend/src/app/core/api.service.spec.ts` (append)

**Interfaces:**
- Produces: `createAgent(name, description?)`, `updateAgent(id, {display_name?, identity?, description?})`, `archiveAgent(id)` (unchanged), `deleteAgent(id)` (`DELETE ?hard=true`).

- [ ] **Step 1: Read** the current agent admin methods in `api.service.ts` (`createAgent`, `updateAgent`, `archiveAgent`).

- [ ] **Step 2: Append failing spec** to `frontend/src/app/core/api.service.spec.ts`:

```typescript
  it('createAgent sends name + description', () => {
    api.createAgent('Legal', 'does legal').subscribe();
    const r = http.expectOne('/admin/agents');
    expect(r.request.body).toEqual({ name: 'Legal', description: 'does legal' });
    r.flush({ id: 'legal' });
  });

  it('deleteAgent hits hard=true', () => {
    api.deleteAgent('legal').subscribe();
    const r = http.expectOne('/admin/agents/legal?hard=true');
    expect(r.request.method).toBe('DELETE');
    r.flush({ status: 'deleted', id: 'legal' });
  });
```
(`ng test` may not run in this env — that's fine; `ng build` is the gate. The spec documents intent for CI.)

- [ ] **Step 3: Edit `api.service.ts`**:
  - `createAgent`:
    ```typescript
    createAgent(name: string, description = ''): Observable<Agent> {
      return this.http.post<Agent>(`${API_BASE}/admin/agents`, { name, description }, { headers: this.adminHeaders() });
    }
    ```
  - `updateAgent` patch type → `{ display_name?: string; identity?: string; description?: string }` (signature only; body unchanged).
  - Add:
    ```typescript
    deleteAgent(id: string): Observable<{ status: string; id: string }> {
      return this.http.delete<{ status: string; id: string }>(`${API_BASE}/admin/agents/${encodeURIComponent(id)}?hard=true`, { headers: this.adminHeaders() });
    }
    ```
  Keep `archiveAgent` as-is.

- [ ] **Step 4: Verify build**:
```bash
cd /Users/rudrakhare/Desktop/my-wiki/org-wiki/.claude/worktrees/hopeful-roentgen-cda2f4/frontend
npx ng build   # must succeed
```

- [ ] **Step 5: Commit**
```bash
cd /Users/rudrakhare/Desktop/my-wiki/org-wiki/.claude/worktrees/hopeful-roentgen-cda2f4
git add frontend/src/app/core/api.service.ts frontend/src/app/core/api.service.spec.ts
git commit -m "feat(fe): api createAgent(description), deleteAgent(hard)"
```

---

## Task MT4: Frontend — Manage-Agents card-grid redesign

**Files:**
- Modify: `frontend/src/app/features/admin/manage-agents.ts`
- Modify: `frontend/src/app/features/admin/manage-agents.scss`

**Context:** Read the current component first. Keep the class name `ManageAgents`, selector `app-manage-agents`, `imports: [FormsModule]`, the injected `ApiService`/`AgentService`, the `PROTECTED` set, and the `create()`/`startRename()`/`saveRename()`/`archive()` patterns. Extend them. `Agent` has `id, display_name, description?, accent?, theme_base?`.

- [ ] **Step 1: Replace the component template + logic** in `manage-agents.ts` with:

```typescript
import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ApiService, Agent } from '../../core/api.service';
import { AgentService } from '../../core/agent.service';

const PROTECTED = new Set(['conwo', 'infosec']);

@Component({
  selector: 'app-manage-agents',
  standalone: true,
  imports: [FormsModule],
  styleUrl: './manage-agents.scss',
  template: `
    <section class="manage-agents">
      <h1>Agents</h1>

      <div class="create-card">
        <h2>Create a new agent</h2>
        <p class="hint">Name it and say in one line what it does. It starts with an empty knowledge
          base — ingest documents to teach it. It gets its own dashboard, traces, ingest, and graph.</p>
        <div class="form">
          <input [(ngModel)]="newName" placeholder="Name, e.g. Legal" [disabled]="busy()" />
          <input [(ngModel)]="newDesc" placeholder="One line: what this agent does" [disabled]="busy()"
                 (keyup.enter)="create()" />
          <button class="primary" (click)="create()" [disabled]="busy() || !newName().trim()">
            {{ busy() ? 'Creating…' : 'Create Agent' }}
          </button>
        </div>
        @if (error()) { <p class="error">{{ error() }}</p> }
        @if (created(); as c) {
          <div class="created">
            <span class="dot" [style.background]="c.accent || '#1e293b'"></span>
            Created <strong>{{ c.display_name }}</strong> — now selectable in the switcher.
          </div>
        }
      </div>

      <h2>Existing agents</h2>
      <div class="agent-grid">
        @for (a of agents(); track a.id) {
          <div class="agent-card" [style.--card-accent]="a.accent || '#64748b'">
            @if (editing() === a.id) {
              <input class="edit-name" [(ngModel)]="editName" placeholder="Name" />
              <input class="edit-desc" [(ngModel)]="editDesc" placeholder="Description" />
              <div class="actions">
                <button class="primary" (click)="saveRename(a)">Save</button>
                <button class="ghost" (click)="editing.set(null)">Cancel</button>
              </div>
            } @else {
              <div class="card-head">
                <span class="dot" [style.background]="a.accent || '#64748b'"></span>
                <span class="title">{{ a.display_name }}</span>
                @if (isProtected(a.id)) { <span class="badge">built-in</span> }
              </div>
              <p class="desc">{{ a.description || '—' }}</p>
              <code class="id">{{ a.id }}</code>
              <div class="actions">
                <button class="ghost" (click)="startRename(a)">Rename</button>
                @if (!isProtected(a.id)) {
                  <button class="ghost" (click)="archive(a)">Archive</button>
                  @if (deletingId() === a.id) {
                    <span class="confirm">
                      <input [(ngModel)]="deleteText" [placeholder]="'type ' + a.id" />
                      <button class="danger" [disabled]="deleteText !== a.id" (click)="confirmDelete(a)">Delete</button>
                      <button class="ghost" (click)="deletingId.set(null)">Cancel</button>
                    </span>
                  } @else {
                    <button class="danger" (click)="startDelete(a)">Delete</button>
                  }
                }
              </div>
            }
          </div>
        }
      </div>
    </section>
  `,
})
export class ManageAgents {
  private api = inject(ApiService);
  private agentSvc = inject(AgentService);

  agents = this.agentSvc.agents;
  newName = signal('');
  newDesc = signal('');
  busy = signal(false);
  error = signal('');
  created = signal<Agent | null>(null);
  editing = signal<string | null>(null);
  editName = '';
  editDesc = '';
  deletingId = signal<string | null>(null);
  deleteText = '';

  constructor() { this.agentSvc.loadAgents(); }

  isProtected(id: string): boolean { return PROTECTED.has(id); }

  create(): void {
    const name = this.newName().trim();
    if (!name || this.busy()) return;
    this.busy.set(true); this.error.set(''); this.created.set(null);
    this.api.createAgent(name, this.newDesc().trim()).subscribe({
      next: (agent) => {
        this.busy.set(false); this.created.set(agent);
        this.newName.set(''); this.newDesc.set('');
        this.agentSvc.loadAgents();
      },
      error: (err) => {
        this.busy.set(false);
        this.error.set(err?.error?.detail || 'Could not create agent. It may already exist.');
      },
    });
  }

  startRename(a: Agent): void { this.editing.set(a.id); this.editName = a.display_name; this.editDesc = a.description || ''; }

  saveRename(a: Agent): void {
    const name = this.editName.trim();
    if (!name) return;
    this.api.updateAgent(a.id, { display_name: name, description: this.editDesc.trim() }).subscribe({
      next: () => { this.editing.set(null); this.agentSvc.loadAgents(); },
      error: () => this.error.set('Update failed.'),
    });
  }

  archive(a: Agent): void {
    if (!confirm(`Archive "${a.display_name}"? It will disappear from the switcher.`)) return;
    this.api.archiveAgent(a.id).subscribe({
      next: () => this.agentSvc.loadAgents(),
      error: (err) => this.error.set(err?.error?.detail || 'Archive failed.'),
    });
  }

  startDelete(a: Agent): void { this.deletingId.set(a.id); this.deleteText = ''; }

  confirmDelete(a: Agent): void {
    if (this.deleteText !== a.id) return;
    this.api.deleteAgent(a.id).subscribe({
      next: () => { this.deletingId.set(null); this.agentSvc.loadAgents(); },
      error: (err) => this.error.set(err?.error?.detail || 'Delete failed.'),
    });
  }
}
```

- [ ] **Step 2: Replace `manage-agents.scss`** with the card-grid + glowing-accent styles:

```scss
.manage-agents { max-width: 1040px; margin: 0 auto; padding: 32px 20px; color: var(--text); }
h1 { margin: 0 0 20px; }
h2 { margin: 28px 0 12px; font-size: 1.05rem; }
.hint { color: var(--text-muted); margin: 0 0 12px; max-width: 70ch; }

.create-card { background: var(--surface); border: 1px solid var(--border); border-radius: 14px; padding: 20px; }
.form { display: flex; gap: 10px; flex-wrap: wrap; }
.form input { flex: 1 1 220px; padding: 10px 12px; border: 1px solid var(--border);
  border-radius: 10px; background: var(--surface); color: var(--text); font: inherit; }

button { padding: 8px 13px; border-radius: 9px; border: 1px solid var(--border);
  background: var(--surface); color: var(--text); cursor: pointer; font: inherit; }
button.primary { background: var(--accent); color: var(--text-on-accent); border-color: transparent; }
button.ghost { background: transparent; }
button.danger { color: var(--error); border-color: var(--error-border); }
button:disabled { opacity: .5; cursor: default; }
.error { color: var(--error); margin: 10px 0 0; }
.created { margin: 14px 0 0; padding: 12px; border-radius: 10px; background: var(--accent-soft); }
.dot { width: 11px; height: 11px; border-radius: 50%; display: inline-block; flex: none; }

.agent-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 16px; }
.agent-card {
  --card-accent: #64748b;
  position: relative; background: var(--surface); border-radius: 14px; padding: 16px;
  border: 1px solid color-mix(in srgb, var(--card-accent) 45%, transparent);
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--card-accent) 25%, transparent),
              0 8px 26px -10px color-mix(in srgb, var(--card-accent) 55%, transparent);
  transition: transform .15s ease, box-shadow .15s ease;
}
.agent-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--card-accent) 45%, transparent),
              0 12px 34px -10px color-mix(in srgb, var(--card-accent) 70%, transparent);
}
.card-head { display: flex; align-items: center; gap: 8px; }
.card-head .title { font-weight: 600; font-size: 1.02rem; }
.badge { margin-left: auto; font-size: .72rem; color: var(--text-subtle);
  border: 1px solid var(--border); border-radius: 999px; padding: 1px 8px; }
.desc { color: var(--text-muted); margin: 8px 0 10px; min-height: 1.2em; }
.id { font-family: ui-monospace, monospace; font-size: .8rem; color: var(--text-subtle); }
.actions { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; margin-top: 12px; }
.confirm { display: inline-flex; gap: 6px; align-items: center; }
.confirm input { width: 110px; padding: 6px 8px; border: 1px solid var(--border);
  border-radius: 8px; background: var(--surface); color: var(--text); font: inherit; }
.edit-name, .edit-desc { width: 100%; margin-bottom: 8px; padding: 8px 10px;
  border: 1px solid var(--border); border-radius: 9px; background: var(--surface); color: var(--text); font: inherit; }
```

- [ ] **Step 3: Verify build**:
```bash
cd /Users/rudrakhare/Desktop/my-wiki/org-wiki/.claude/worktrees/hopeful-roentgen-cda2f4/frontend
npx ng build   # must succeed (AOT type-checks the template)
```

- [ ] **Step 4: Commit**
```bash
cd /Users/rudrakhare/Desktop/my-wiki/org-wiki/.claude/worktrees/hopeful-roentgen-cda2f4
git add frontend/src/app/features/admin/manage-agents.ts frontend/src/app/features/admin/manage-agents.scss
git commit -m "feat(fe): Manage-Agents card grid — description, glowing accent, rename/archive/delete"
```

---

## Task MT5: Verification

- [ ] **Step 1: Full backend suite** — `/Users/rudrakhare/Desktop/my-wiki/org-wiki/venv/bin/python -m pytest tests/ -q` → only the 5 known failures; 0 new.
- [ ] **Step 2: Frontend build** — `cd <worktree>/frontend && npx ng build` → clean.
- [ ] **Step 3: Commit any fixups; done.**

---

## Milestone exit criteria
- Create form has Name + Description; new agents persist + display the description.
- Manage-Agents is a card grid: each card shows name + description + id + Rename/Archive/Delete, glowing in the agent's accent; Conwo/Infosec show "built-in" with no Archive/Delete.
- Hard delete (typed confirm) removes the DB row + `agents/<slug>/` dirs; archive still soft; both protected for built-ins.
- Full backend suite green (5 known failures only); `ng build` clean.
