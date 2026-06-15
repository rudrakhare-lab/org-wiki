# Infosec Multi-Agent — Frontend + Content Plan (Plan 2)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a frontend agent switcher so a user picks "Conwo" or "Infosec" and the entire app (chat, dashboard, traces, ingest, knowledge graph) operates as that agent — and author Infosec's full `CLAUDE.md` — building on the completed backend milestone (Plan 1).

**Architecture:** A new `AgentService` holds the active agent id (a signal), persists it to `localStorage`, and exposes the agent list from the backend's `GET /agents`. The existing `authInterceptor` attaches an `X-Agent-Id` header to every request from that persisted value — so all existing API calls become agent-scoped with no per-call edits. The switcher lives in the sidebar header; selecting an agent persists the choice and triggers a clean reload so every surface re-initializes as the new agent (an agent switch is a top-level context switch; reload is the reliable, idiomatic choice and avoids fragile per-screen reactivity). Branding and the Claude-Code mode toggle read the active agent.

**Tech Stack:** Angular (standalone components, signals, functional HTTP interceptor), `@angular/build` (`npx ng build` for compile/type-check), TypeScript.

**Companion spec:** `docs/superpowers/specs/2026-06-14-infosec-multi-agent-design.md` (§8 frontend, §9 Infosec content).
**Builds on:** Plan 1 backend (branch `claude/hopeful-roentgen-cda2f4`) — `GET /agents` exists and returns `[{id, display_name, description, modes, has_jira, has_pms}]`; the backend reads `X-Agent-Id` (default "conwo").

---

## Conventions for every task

- **Working dir:** `/Users/rudrakhare/Desktop/my-wiki/org-wiki/.claude/worktrees/hopeful-roentgen-cda2f4/frontend` for all frontend commands.
- **Verification gate:** `npx ng build` — MUST complete with "Application bundle generation complete" and **no new errors** (pre-existing budget WARNINGS for `initial` bundle and `ask.scss` are expected — ignore them). Build takes ~3s after the first run.
- `node_modules` is already installed. If missing, run `npm install` first.
- **localStorage convention:** keys are prefixed `conwo_` (existing pattern). The active-agent key is `conwo_active_agent`.
- **Do NOT edit backend files** in this plan — backend is done. Frontend + the one Infosec `CLAUDE.md` only.
- **Commit after every task.**

---

## File Structure

**New files:**
- `frontend/src/app/core/agent.service.ts` — active-agent signal + agent list + persistence.

**Modified files:**
- `frontend/src/app/core/api.service.ts` — add `Agent` interface + `getAgents()`.
- `frontend/src/app/core/auth.interceptor.ts` — attach `X-Agent-Id` header.
- `frontend/src/app/app.ts` — load agent list on bootstrap; expose active agent name for the title.
- `frontend/src/app/shared/app-sidebar/app-sidebar.ts` — agent switcher dropdown in `sb-head`; brand shows active agent name.
- `frontend/src/app/features/ask/ask.ts` — hide the Claude-Code ("agent") mode toggle when the active agent doesn't support it; show the active agent's name on the assistant bubble.
- `agents/infosec/CLAUDE.md` — replace the placeholder with the full Infosec brain.

---

## PHASE A — Agent infrastructure

### Task 1: `AgentService` + `getAgents()` API method

**Files:**
- Modify: `frontend/src/app/core/api.service.ts`
- Create: `frontend/src/app/core/agent.service.ts`

- [ ] **Step 1: Add the `Agent` interface + `getAgents()` to `api.service.ts`.**

Near the other exported interfaces at the top of `api.service.ts` (the file already exports `QueryRequest` at line 7, `ConversationSummary` at line 52), add:

```typescript
export interface Agent {
  id: string;
  display_name: string;
  description: string;
  modes: string[];
  has_jira: boolean;
  has_pms: boolean;
}
```

Inside `class ApiService` (after `listConversations`, near the other `http.get` methods), add:

```typescript
  getAgents(): Observable<Agent[]> {
    return this.http.get<Agent[]>(`${API_BASE}/agents`);
  }
```

(`API_BASE` is the empty-string constant at line 510; `Observable` is already imported.)

- [ ] **Step 2: Create `frontend/src/app/core/agent.service.ts`.**

```typescript
/**
 * AgentService — the active AI agent (e.g. "conwo" or "infosec").
 *
 * Holds the active agent id as a signal, persisted to localStorage so the
 * authInterceptor can stamp every request with X-Agent-Id (it reads the same
 * key directly, avoiding a DI cycle). Loads the selectable agent list from the
 * backend's GET /agents. Switching agent persists the choice and reloads the
 * app so every surface re-initializes cleanly as the new agent.
 */
import { Injectable, inject, signal } from '@angular/core';
import { ApiService, Agent } from './api.service';

export const ACTIVE_AGENT_KEY = 'conwo_active_agent';
export const DEFAULT_AGENT_ID = 'conwo';

@Injectable({ providedIn: 'root' })
export class AgentService {
  private api = inject(ApiService);

  readonly agents = signal<Agent[]>([]);
  readonly activeId = signal<string>(this.readPersisted());

  private readPersisted(): string {
    try {
      return localStorage.getItem(ACTIVE_AGENT_KEY) || DEFAULT_AGENT_ID;
    } catch {
      return DEFAULT_AGENT_ID;
    }
  }

  /** Load the selectable agent list from the backend (best-effort). */
  loadAgents(): void {
    this.api.getAgents().subscribe({
      next: (list) => {
        this.agents.set(list);
        // If the persisted agent is no longer offered, fall back to default.
        if (!list.some((a) => a.id === this.activeId())) {
          this.setActive(DEFAULT_AGENT_ID, /*reload*/ false);
        }
      },
      error: () => { /* leave default; switcher just won't populate */ },
    });
  }

  /** The active agent's full record, if the list is loaded. */
  active(): Agent | undefined {
    return this.agents().find((a) => a.id === this.activeId());
  }

  activeName(): string {
    return this.active()?.display_name ?? 'Conwo';
  }

  /**
   * Switch the active agent. Persists + updates the signal. By default reloads
   * the app so chat/dashboard/traces/ingest/graph all re-init as the new agent.
   */
  setActive(id: string, reload = true): void {
    if (id === this.activeId() && reload) return; // no-op switch
    try { localStorage.setItem(ACTIVE_AGENT_KEY, id); } catch { /* private mode */ }
    this.activeId.set(id);
    if (reload && typeof window !== 'undefined') {
      window.location.assign('/ask'); // clean slate on the chat surface
    }
  }
}
```

- [ ] **Step 3: Verify build.**

Run: `npx ng build`
Expected: "Application bundle generation complete" with no errors (budget warnings ok).

- [ ] **Step 4: Commit.**

```bash
git add frontend/src/app/core/api.service.ts frontend/src/app/core/agent.service.ts
git commit -m "feat(fe): AgentService + getAgents() — active-agent signal + list"
```

---

### Task 2: `X-Agent-Id` header in the interceptor

**Files:**
- Modify: `frontend/src/app/core/auth.interceptor.ts`

- [ ] **Step 1: Add the agent header.** Replace the body of `authInterceptor` so it attaches `X-Agent-Id` (read from the same localStorage key `AgentService` writes) to every non-public request, alongside the existing bearer-token logic. Full new file:

```typescript
import { HttpInterceptorFn } from '@angular/common/http';

const ADMIN_TOKEN_KEY = 'conwo_admin_token';
const ACTIVE_AGENT_KEY = 'conwo_active_agent';

const PUBLIC_PATHS = ['/health', '/health/claude-code'];

function isPublicPath(url: string): boolean {
  return PUBLIC_PATHS.some(p => url.endsWith(p));
}

function readLocal(key: string): string {
  try {
    return (typeof localStorage !== 'undefined') ? (localStorage.getItem(key) ?? '') : '';
  } catch {
    return '';
  }
}

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  if (isPublicPath(req.url)) {
    return next(req);
  }

  // Always stamp the active agent (default conwo) so every API call is
  // agent-scoped. The backend defaults to conwo when the header is absent,
  // so this is additive and safe for existing endpoints.
  const agentId = readLocal(ACTIVE_AGENT_KEY) || 'conwo';
  const setHeaders: Record<string, string> = { 'X-Agent-Id': agentId };

  // Attach the bearer token unless the caller set Authorization explicitly.
  if (!req.headers.has('Authorization')) {
    const token = readLocal(ADMIN_TOKEN_KEY);
    if (token) {
      setHeaders['Authorization'] = `Bearer ${token}`;
    }
  }

  return next(req.clone({ setHeaders }));
};
```

- [ ] **Step 2: Verify build.**

Run: `npx ng build`
Expected: success, no errors.

- [ ] **Step 3: Manually confirm the header travels (optional sanity).** Start the app (`npm start`), open the browser devtools Network tab, and confirm a request (e.g. `GET /conversations`) carries `X-Agent-Id: conwo`. (Full agent-switch behavior is verified in Task 7.)

- [ ] **Step 4: Commit.**

```bash
git add frontend/src/app/core/auth.interceptor.ts
git commit -m "feat(fe): attach X-Agent-Id header on every request"
```

---

### Task 3: Load the agent list on app bootstrap

**Files:**
- Modify: `frontend/src/app/app.ts`

- [ ] **Step 1: Inject `AgentService` and load the list when signed in.** In `app.ts`, add the import and inject it, then call `loadAgents()` in the constructor (after `hydrateUser()`), guarded by sign-in:

Add import near the top:
```typescript
import { AgentService } from './core/agent.service';
```

In the class, add the injection alongside the others (`private api`, `private conversations`):
```typescript
  private agentSvc = inject(AgentService);
```

In the constructor, after `this.hydrateUser();`, add:
```typescript
    if (this.signedIn()) {
      this.agentSvc.loadAgents();
    }
```

Also load after a fresh sign-in. There's no central "just signed in" hook in `app.ts` (login happens in the Login component), but `hydrateUser()` already runs on bootstrap for a signed-in session — the constructor guard above covers reloads. The Login flow navigates to `/ask`, which remounts the shell only if it was a full load; to be safe, ALSO call `loadAgents()` inside `hydrateUser()`'s success path:

In `hydrateUser()`, inside the `next:` callback (after `this.api.setUserApproved(me.approved);`), add:
```typescript
        this.agentSvc.loadAgents();
```

- [ ] **Step 2: Verify build.**

Run: `npx ng build`
Expected: success.

- [ ] **Step 3: Commit.**

```bash
git add frontend/src/app/app.ts
git commit -m "feat(fe): load agent list on bootstrap + after user hydrate"
```

---

## PHASE B — Switcher UI, branding, mode gating

### Task 4: Agent switcher dropdown in the sidebar

**Files:**
- Modify: `frontend/src/app/shared/app-sidebar/app-sidebar.ts`

- [ ] **Step 1: Inject `AgentService` + add a switcher.** In `app-sidebar.ts`:

Add the import:
```typescript
import { AgentService } from '../../core/agent.service';
```

In the `AppSidebar` class (near `store = inject(ConversationStore);` ~line 399), add:
```typescript
  agentSvc = inject(AgentService);
  agentMenuOpen = signal(false);

  onSelectAgent(id: string): void {
    this.agentMenuOpen.set(false);
    this.agentSvc.setActive(id);   // persists + reloads to /ask as the new agent
  }
```

- [ ] **Step 2: Render the switcher in the template `sb-head`.** Replace the existing brand block (the `<a routerLink="/ask" class="sb-brand" ...>...</a>` at ~lines 50-53) so the brand label shows the active agent name and a small chevron button opens an agent menu. Insert this INSIDE `.sb-head`, keeping the collapse button after it:

```html
        <div class="sb-agent">
          <a routerLink="/ask" class="sb-brand" (click)="closeMobile()" [attr.aria-label]="agentSvc.activeName() + ' — home'">
            <img src="logo.png" alt="" class="sb-logo" />
            <span class="sb-name sb-label">{{ agentSvc.activeName() }}</span>
          </a>
          @if (agentSvc.agents().length > 1) {
            <button class="sb-agent-toggle sb-label" type="button"
                    (click)="agentMenuOpen.set(!agentMenuOpen())"
                    [attr.aria-expanded]="agentMenuOpen()" aria-label="Switch agent" title="Switch agent">
              <svg viewBox="0 0 16 16" width="13" height="13" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M4 6l4 4 4-4"/></svg>
            </button>
          }
          @if (agentMenuOpen()) {
            <div class="sb-agent-menu">
              @for (a of agentSvc.agents(); track a.id) {
                <button type="button" class="sb-agent-item"
                        [class.active]="a.id === agentSvc.activeId()"
                        (click)="onSelectAgent(a.id)">
                  <span class="sb-agent-item-name">{{ a.display_name }}</span>
                  <span class="sb-agent-item-desc">{{ a.description }}</span>
                </button>
              }
            </div>
          }
        </div>
```

(The collapse `<button class="sb-collapse" ...>` block that currently follows the brand stays where it is, after this `.sb-agent` div.)

- [ ] **Step 3: Add styles.** In the component `styles: [...]` block (after the `.sb-brand`/`.sb-name` rules ~line 229), add:

```css
    .sb-agent { position: relative; flex: 1; display: flex; align-items: center; gap: 4px; min-width: 0; }
    .sb-agent-toggle {
      background: none; border: none; color: var(--text-muted); cursor: pointer;
      padding: 2px; display: inline-flex; align-items: center; border-radius: 4px;
      &:hover { color: var(--text); background: var(--surface-muted); }
    }
    .sb-agent-menu {
      position: absolute; top: 100%; left: 0; z-index: 30; margin-top: 4px;
      min-width: 220px; background: var(--surface, #fff); border: 1px solid var(--border);
      border-radius: var(--radius-sm); box-shadow: 0 8px 24px rgba(0,0,0,0.12);
      padding: 4px; display: flex; flex-direction: column; gap: 2px;
    }
    .sb-agent-item {
      text-align: left; background: none; border: none; cursor: pointer;
      padding: 8px 10px; border-radius: var(--radius-sm); display: flex; flex-direction: column; gap: 2px;
      &:hover { background: var(--surface-muted); }
      &.active { background: var(--surface-muted); }
    }
    .sb-agent-item-name { font-weight: 600; font-size: 0.88rem; color: var(--text); }
    .sb-agent-item-desc { font-size: 0.75rem; color: var(--text-muted); }
```

- [ ] **Step 4: Verify build.**

Run: `npx ng build`
Expected: success.

- [ ] **Step 5: Commit.**

```bash
git add frontend/src/app/shared/app-sidebar/app-sidebar.ts
git commit -m "feat(fe): agent switcher dropdown in sidebar header"
```

---

### Task 5: Dynamic branding (active agent name) + Claude-Code mode gating

**Files:**
- Modify: `frontend/src/app/app.ts`
- Modify: `frontend/src/app/features/ask/ask.ts`

- [ ] **Step 1: App title reflects the active agent.** In `app.ts`, change the static title into a getter sourced from `AgentService`. Replace `readonly title = 'Conwo';` with:

```typescript
  get title(): string { return this.agentSvc.activeName(); }
```

(`agentSvc` is injected in Task 3. If `title` is only used in tests/templates, this is safe; verify `npx ng build` passes.)

- [ ] **Step 2: Gate the Claude-Code mode toggle in `ask.ts`.** The Ask page offers a "Deep Search" vs "Claude Code" (`agent`) mode toggle. Infosec's `modes` is `["api"]` only, so the Claude-Code option must be hidden when the active agent doesn't support it.

Read `ask.ts` to find where the mode toggle is rendered and where `mode`/`claudeCodeAvailable` are defined (around lines 258, 416, 537 per the file). Inject `AgentService`:
```typescript
import { AgentService } from '../../core/agent.service';
// in the class:
private agentSvc = inject(AgentService);
agentSupportsAgentMode(): boolean {
  const a = this.agentSvc.active();
  return !a || a.modes.includes('agent');   // default-permissive until list loads
}
```

In the template, wrap the Claude-Code mode toggle option with `@if (agentSupportsAgentMode()) { ... }`. ALSO, if the persisted mode is `'agent'` but the active agent doesn't support it, coerce to `'api'` where the mode is initialized (near the existing `this.mode.set(stored === 'claude-code' ? 'api' : stored);` line ~416):
```typescript
    if (this.mode() === 'agent' && !this.agentSupportsAgentMode()) {
      this.mode.set('api');
    }
```

- [ ] **Step 3: Assistant bubble shows the active agent name.** In `ask.ts`, the assistant/transcript bubble renders the hardcoded label `Conwo` (around lines 75, 218, 230) next to `logo.png`. Replace the literal `Conwo` text in those bubble labels with `{{ agentSvc.activeName() }}`. (Leave `logo.png` as-is.)

- [ ] **Step 4: Verify build.**

Run: `npx ng build`
Expected: success.

- [ ] **Step 5: Commit.**

```bash
git add frontend/src/app/app.ts frontend/src/app/features/ask/ask.ts
git commit -m "feat(fe): dynamic agent branding + hide Claude-Code mode for api-only agents"
```

---

## PHASE C — Infosec content

### Task 6: Author Infosec's full `CLAUDE.md`

**Files:**
- Modify: `agents/infosec/CLAUDE.md` (replace the placeholder)

- [ ] **Step 1: Read the two references.** Read the root `CLAUDE.md` (Conwo's brain) for structure, and the design spec §9 for what to keep/drop. Keep: identity/purpose; page types (module/concept/entity/integration/decision/cross-module/source/person); the INGEST 9-step workflow; the QUERY workflow (wiki-only — NO Jira/PMS steps); the LINT workflow; index.md/log.md conventions; cross-link rules. Drop: ALL Jira-layer, PMS-config, `.in`/`.com` server, live-config-debug, functional-area, and trace/observability-internal sections. Rewrite identity + module-naming for the information-security domain.

- [ ] **Step 2: Write `agents/infosec/CLAUDE.md`** as a self-contained brain. It MUST:
  - Open with an identity/purpose section: the Infosec agent maintains an information-security knowledge wiki under `agents/infosec/wiki/`, is wiki-only (no Jira/PMS/live-config), and is read-only at query time (edits go through propose-for-admin-review tools).
  - Define the page types it uses (reuse Conwo's concept/entity/cross-module/decision/source schemas, drop config/PMS page types).
  - Include the INGEST (read source → summarize → create source page → process entities/concepts → cross-link → update index/log) and QUERY (read wiki → synthesize → cite → "not documented" only after exhausting wiki search) and LINT workflows, all phrased wiki-only.
  - Contain NO references to Jira, PMS, `.in`/`.com` servers, BUID, or config properties.
  - Reference the security module-naming convention (kebab-case slugs under `agents/infosec/wiki/`, e.g. `phishing`, `incident-response`, `access-control`, `vulnerability-management` — illustrative, to be expanded when real docs land).

- [ ] **Step 3: Sanity-check it contains no Jira/PMS leakage.**

Run: `grep -ciE 'jira|pms|buid|\.in server|\.com server' agents/infosec/CLAUDE.md`
Expected: `0`.

- [ ] **Step 4: Verify the agent still boots with the new brain.**

Run (from repo root): `/Users/rudrakhare/Desktop/my-wiki/org-wiki/venv/bin/python -m pytest tests/test_agent_registry.py -q`
Expected: PASS (the registry just points at the file; this confirms nothing broke).

- [ ] **Step 5: Commit.**

```bash
git add agents/infosec/CLAUDE.md
git commit -m "feat(infosec): author full Infosec CLAUDE.md (wiki-only brain)"
```

---

## PHASE D — End-to-end verification

### Task 7: Full agent-switch smoke test

**Files:** none (verification only)

- [ ] **Step 1: Build clean.**

Run (from `frontend/`): `npx ng build`
Expected: "Application bundle generation complete", no errors.

- [ ] **Step 2: Boot backend + frontend.** In one shell, from repo root:
`/Users/rudrakhare/Desktop/my-wiki/org-wiki/venv/bin/python -m uvicorn backend.api:app --port 8000` (or the project's normal start). In another, from `frontend/`: `npm start` (proxies API to the backend per the project's dev setup; if no proxy is configured, point the frontend at the backend origin as the project normally does).

- [ ] **Step 3: Verify the switch end-to-end (manual or via a browser automation tool).** Sign in. Confirm:
  1. The sidebar shows a switcher with **Conwo** and **Infosec**.
  2. Selecting **Infosec** reloads; the sidebar brand now reads **Infosec**; the chat assistant bubble shows **Infosec**.
  3. On Infosec, the **Knowledge graph** shows only the Infosec pages (the `phishing` node + index), NOT Conwo's ~1,181 nodes.
  4. On Infosec, the Ask page shows **no Claude-Code mode toggle** (Deep Search only).
  5. Network tab: requests carry `X-Agent-Id: infosec`.
  6. Switch back to **Conwo** → graph, chat, dashboard, traces all return to Conwo's data.
  7. Conversations started under Infosec do not appear under Conwo and vice-versa.

- [ ] **Step 4: Record the result.** Note pass/fail for each of the 7 checks. If any fail, fix in the relevant task before declaring done.

---

## Milestone exit criteria (Plan 2 done)

- `npx ng build` clean.
- Sidebar agent switcher lists both agents; selecting one swaps every surface (chat, graph, dashboard, traces, ingest) to that agent's data.
- `X-Agent-Id` travels on every request.
- Infosec shows Deep-Search-only (no Claude-Code toggle) and its own (small) knowledge graph.
- Branding reflects the active agent.
- Infosec `CLAUDE.md` is the full wiki-only brain (no Jira/PMS), and the agent boots on it.

**Deferred (needs owner input):** ingesting the REAL Infosec source documents — run the existing ingest workflow under the Infosec agent once the owner provides the docs. No code change required; it's a content operation through the now-agent-aware ingest pipeline.
