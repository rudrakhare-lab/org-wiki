# Self-Service Agent Creation — Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let an admin create/manage agents from the Angular UI, make every agent appear in a multi-agent switcher, and theme each agent as a shared dark base + its own accent color (Conwo stays light).

**Architecture:** The backend already exposes `accent`/`theme_base` on `GET /agents` and admin endpoints `POST/PATCH/DELETE /admin/agents` (backend plan, done). This plan does three things: (1) generalize the existing hardcoded "Infosec violet" theme into a reusable `body.theme-dark` base whose accent-derived tokens consume a single runtime-injected `--accent`; (2) replace the binary Conwo↔Infosec toggle with a multi-agent dropdown; (3) add an admin "Manage Agents" page (create + rename + archive) wired to refresh the switcher.

**Tech Stack:** Angular (standalone components, signals, functional interceptors/guards), SCSS with CSS custom properties + `color-mix()`, Vitest (`ng test`) for unit logic, `npx ng build` as the hard compile gate.

**Testing approach (read this):** This frontend has near-zero component tests by convention (`frontend/src/app/app.spec.ts` is the only spec) and uses `npx ng build` as the real gate (memory: "ng build is the frontend gate"). So: write Vitest unit specs only for **pure logic** (theme-var derivation, AgentService accent persistence, API method URLs) where they're cheap and high-value; for **UI/visual** behavior, the gate is a clean `npx ng build` plus a dev-server smoke (screenshot via the `Claude_Preview` MCP, or curl) during review. Do NOT attempt heavy DOM/component TDD — it is not this codebase's pattern and will waste time.

**Working directory for all commands:** `/Users/rudrakhare/Desktop/my-wiki/org-wiki/frontend`
**Build gate command:** `npx ng build` (expected: "Application bundle generation complete", exit 0)
**Unit test command:** `npx ng test --watch=false` (Vitest, single run)

---

## File Structure

| File | Responsibility | Change |
|------|----------------|--------|
| `src/app/core/api.service.ts` | HTTP client + types | Extend `Agent` interface (`identity`,`accent`,`theme_base`); add `createAgent`/`updateAgent`/`archiveAgent` |
| `src/app/core/agent.service.ts` | Active-agent state | Persist `accent`+`theme_base`+`base` for anti-flash; expose `active()` (exists) used by theming |
| `src/app/app.ts` | Root theming effect | Apply `theme-<base>` class + inject `--accent` from active agent (replaces `id==='infosec'` check) |
| `src/index.html` | Anti-flash pre-boot | Read persisted base/accent, apply `theme-dark` + `--accent` before Angular boots |
| `src/styles.scss` | Global tokens + dark theme | Rename `body.theme-infosec` → `body.theme-dark`; derive accent tokens from `--accent` via `color-mix` (violet fallback) |
| `src/app/shared/mode-toggle/mode-toggle.ts` | Agent switcher | Binary toggle → multi-agent dropdown; `--mt-*` consume `--accent` |
| `src/app/features/admin/manage-agents.ts` (+`.scss`) | Admin Create/Manage UI | **New** component |
| `src/app/app.routes.ts` | Routing | New admin-gated `/admin/agents` route |
| `src/app/shared/app-sidebar/app-sidebar.ts` | Nav | New admin-only "Manage Agents" nav item |

---

## PHASE 1 — per-agent accent theming infrastructure

### Task 1: Extend `Agent` type + persist theme fields in AgentService

**Files:**
- Modify: `src/app/core/api.service.ts` (interface `Agent`, lines 52-59)
- Modify: `src/app/core/agent.service.ts`
- Test: `src/app/core/agent.service.spec.ts` (create)

- [ ] **Step 1: Extend the `Agent` interface.** In `src/app/core/api.service.ts` replace the interface (lines 52-59) with:

```typescript
export interface Agent {
  id: string;
  display_name: string;
  description: string;
  identity?: string;     // editable identity line (backend _agent_public sends it)
  accent?: string;       // hex, e.g. "#a78bfa"
  theme_base?: string;   // 'light' | 'dark'
  modes: string[];
  has_jira: boolean;
  has_pms: boolean;
}
```

- [ ] **Step 2: Add theme-persistence constants + helper in AgentService.** In `src/app/core/agent.service.ts`, add two exported keys next to `ACTIVE_AGENT_KEY` (line 13):

```typescript
export const ACTIVE_BASE_KEY = 'conwo_active_base';     // 'light' | 'dark'
export const ACTIVE_ACCENT_KEY = 'conwo_active_accent'; // hex string
```

Then add a method (place after `active()`, around line 47) that resolves the active agent's base/accent and persists them for the anti-flash pre-boot script. Use `id==='conwo' ? 'light' : 'dark'` as the fallback base when the list hasn't loaded:

```typescript
/** Base theme of the active agent, with a safe fallback before the list loads. */
activeBase(): 'light' | 'dark' {
  const a = this.active();
  if (a?.theme_base === 'light' || a?.theme_base === 'dark') return a.theme_base;
  return this.activeId() === DEFAULT_AGENT_ID ? 'light' : 'dark';
}

/** Persist base+accent so index.html can pre-apply them on next load (anti-flash). */
persistThemeHints(): void {
  try {
    localStorage.setItem(ACTIVE_BASE_KEY, this.activeBase());
    const accent = this.active()?.accent;
    if (accent) localStorage.setItem(ACTIVE_ACCENT_KEY, accent);
    else localStorage.removeItem(ACTIVE_ACCENT_KEY);
  } catch { /* private mode */ }
}
```

- [ ] **Step 3: Write the unit spec** `src/app/core/agent.service.spec.ts`:

```typescript
import { TestBed } from '@angular/core/testing';
import { of } from 'rxjs';
import { AgentService, ACTIVE_BASE_KEY, ACTIVE_ACCENT_KEY } from './agent.service';
import { ApiService } from './api.service';

describe('AgentService theme hints', () => {
  function setup(agents: any[], activeId: string) {
    localStorage.setItem('conwo_active_agent', activeId);
    TestBed.configureTestingModule({
      providers: [
        AgentService,
        { provide: ApiService, useValue: { getAgents: () => of(agents) } },
      ],
    });
    return TestBed.inject(AgentService);
  }

  afterEach(() => localStorage.clear());

  it('persists dark base + accent for a created agent', () => {
    const svc = setup([{ id: 'legal', display_name: 'Legal', accent: '#3fa7d6', theme_base: 'dark', modes: ['api'], has_jira: false, has_pms: false, description: '' }], 'legal');
    svc.agents.set([{ id: 'legal', display_name: 'Legal', accent: '#3fa7d6', theme_base: 'dark', modes: ['api'], has_jira: false, has_pms: false, description: '' } as any]);
    svc.persistThemeHints();
    expect(localStorage.getItem(ACTIVE_BASE_KEY)).toBe('dark');
    expect(localStorage.getItem(ACTIVE_ACCENT_KEY)).toBe('#3fa7d6');
  });

  it('falls back to light base for conwo before list loads', () => {
    const svc = setup([], 'conwo');
    expect(svc.activeBase()).toBe('light');
  });
});
```

- [ ] **Step 4: Run** `npx ng test --watch=false` — expect the two specs PASS. Then `npx ng build` — expect success.

- [ ] **Step 5: Commit**
```bash
git add src/app/core/api.service.ts src/app/core/agent.service.ts src/app/core/agent.service.spec.ts
git commit -m "feat(fe): Agent type carries accent/theme_base; AgentService persists theme hints"
```

---

### Task 2: Generalize the dark theme — `theme-dark` + accent derived from `--accent`

**Files:**
- Modify: `src/styles.scss` (the `body.theme-infosec` block, lines ~222-277, and all `body.theme-infosec ...` surface overrides lines ~279-423)
- Modify: `src/app/shared/mode-toggle/mode-toggle.ts` (`:host-context(body.theme-infosec)`, lines ~26-31)

- [ ] **Step 1: Rename the theme class globally in `styles.scss`.** Replace every occurrence of `body.theme-infosec` with `body.theme-dark` (there are many — the main block plus the "darken non-tokenized surfaces" selectors). Use a careful find/replace of the exact string `body.theme-infosec` → `body.theme-dark`.

- [ ] **Step 2: Make the accent tokens derive from a single injected `--accent`.** In the `body.theme-dark` block (was lines 245-249), replace the four hardcoded violet accent lines:

```scss
  /* accent — electric violet */
  --accent: #a78bfa;
  --accent-hover: #c4b5fd;
  --accent-soft: #1b1530;
  --accent-ring: rgba(167, 139, 250, 0.45);
```
with derivations from `--accent` (keep violet as the fallback value so Infosec looks identical and any agent with no injected accent still works):

```scss
  /* accent — per-agent. Runtime injects --accent inline on <body>; everything
     below derives from it so each agent glows in its own color (zero per-agent CSS).
     The violet fallback keeps Infosec identical if no accent is injected. */
  --accent: #a78bfa;
  --accent-hover: color-mix(in srgb, var(--accent) 72%, white);
  --accent-soft:  color-mix(in srgb, var(--accent) 16%, #0b0a12);
  --accent-ring:  color-mix(in srgb, var(--accent) 45%, transparent);
```

- [ ] **Step 3: Make the accent-tinted borders/shadows/grid derive from `--accent` too.** Still inside `body.theme-dark`, replace the violet literals so the per-agent color flows through. Replace the border block (was lines 234-237):

```scss
  /* borders */
  --border: rgba(167, 139, 250, 0.22);
  --border-strong: rgba(167, 139, 250, 0.38);
  --border-focus: #a78bfa;
```
with:
```scss
  /* borders — tinted by the active accent */
  --border: color-mix(in srgb, var(--accent) 22%, transparent);
  --border-strong: color-mix(in srgb, var(--accent) 38%, transparent);
  --border-focus: var(--accent);
```

Replace the shadow block (was lines 257-259):
```scss
  /* shadows — violet glow */
  --shadow-sm: 0 1px 2px rgba(0,0,0,0.5), 0 0 0 1px rgba(167,139,250,0.06);
  --shadow: 0 1px 3px rgba(0,0,0,0.5), 0 8px 28px -8px rgba(167,139,250,0.35);
```
with:
```scss
  /* shadows — accent glow */
  --shadow-sm: 0 1px 2px rgba(0,0,0,0.5), 0 0 0 1px color-mix(in srgb, var(--accent) 6%, transparent);
  --shadow: 0 1px 3px rgba(0,0,0,0.5), 0 8px 28px -8px color-mix(in srgb, var(--accent) 35%, transparent);
```

Replace the background grid/glow (was lines 262-267):
```scss
  background-color: #0b0a12;
  background-image:
    radial-gradient(120% 80% at 85% -10%, rgba(167,139,250,0.16), transparent 55%),
    linear-gradient(rgba(167,139,250,0.05) 1px, transparent 1px),
    linear-gradient(90deg, rgba(167,139,250,0.05) 1px, transparent 1px);
  background-size: auto, 26px 26px, 26px 26px;
  background-attachment: fixed;
```
with (surfaces stay neutral dark; only the glow/grid tint with the accent):
```scss
  background-color: #0b0a12;
  background-image:
    radial-gradient(120% 80% at 85% -10%, color-mix(in srgb, var(--accent) 16%, transparent), transparent 55%),
    linear-gradient(color-mix(in srgb, var(--accent) 5%, transparent) 1px, transparent 1px),
    linear-gradient(90deg, color-mix(in srgb, var(--accent) 5%, transparent) 1px, transparent 1px);
  background-size: auto, 26px 26px, 26px 26px;
  background-attachment: fixed;
```

Leave the neutral dark surfaces (`--bg`, `--page-bg`, `--surface*`, `--text*`) and the brightened status colors exactly as they are — they are the shared dark base, not per-agent. In the "darken non-tokenized surfaces" section (lines ~279-423), if any selector hardcodes `rgba(167,139,250,...)` for an accent border/glow (not a neutral background), swap that literal to `color-mix(in srgb, var(--accent) <same-alpha*100>%, transparent)`; leave neutral dark backgrounds (`#0b0a12`, `#15101f`, etc.) untouched.

- [ ] **Step 4: Update the mode-toggle host-context** in `src/app/shared/mode-toggle/mode-toggle.ts` (lines ~26-31). Replace:
```typescript
    :host-context(body.theme-infosec) {
      /* Infosec: violet, matching the dark theme */
      --mt-color: #a78bfa;
      --mt-fill: #8b5cf6;
      --mt-glow: rgba(167, 139, 250, 0.6);
    }
```
with:
```typescript
    :host-context(body.theme-dark) {
      /* Dark agents: glow in the active accent */
      --mt-color: var(--accent);
      --mt-fill: color-mix(in srgb, var(--accent) 80%, black);
      --mt-glow: color-mix(in srgb, var(--accent) 60%, transparent);
    }
```

- [ ] **Step 5: Verify build.** `npx ng build` — expect success (color-mix is valid CSS; the SCSS compiler passes it through). Grep to confirm no stale class remains:
```bash
grep -rn "theme-infosec" src/ ; echo "exit:$?"
```
Expected: only matches (if any) are in comments you intend to keep; ideally zero. The `grep` exit 1 (no matches) is the goal for code.

- [ ] **Step 6: Commit**
```bash
git add src/styles.scss src/app/shared/mode-toggle/mode-toggle.ts
git commit -m "feat(fe): generalize dark theme to theme-dark with accent-derived tokens"
```

---

### Task 3: Root theming effect + anti-flash pre-boot

**Files:**
- Modify: `src/app/app.ts` (constructor effect, lines 39-44)
- Modify: `src/index.html` (pre-boot scripts, lines 11-25)

- [ ] **Step 1: Replace the theming effect in `app.ts`** (lines 39-44). The effect must track the agent list (so it re-runs when `/agents` loads), apply `theme-dark` for dark agents, inject `--accent` inline, and persist the hints. Replace:
```typescript
    effect(() => {
      const infosec = this.agentSvc.activeId() === 'infosec';
      if (typeof document !== 'undefined') {
        document.body.classList.toggle('theme-infosec', infosec);
      }
    });
```
with:
```typescript
    effect(() => {
      // Track both signals so this re-runs when the agent list loads.
      this.agentSvc.agents();
      this.agentSvc.activeId();
      if (typeof document === 'undefined') return;
      const base = this.agentSvc.activeBase();
      document.body.classList.toggle('theme-dark', base === 'dark');
      const accent = this.agentSvc.active()?.accent;
      if (base === 'dark' && accent) {
        document.body.style.setProperty('--accent', accent);
      } else {
        document.body.style.removeProperty('--accent'); // light/Conwo → :root token
      }
      this.agentSvc.persistThemeHints();
    });
```

- [ ] **Step 2: Replace the anti-flash pre-boot in `src/index.html`** (lines 11-25). Replace the two `<script>` blocks with base/accent-aware versions:
```html
  <script>
    /* Pre-boot theme: avoid a flash of the wrong theme/accent on reload. */
    try {
      var agent = localStorage.getItem('conwo_active_agent') || 'conwo';
      var base = localStorage.getItem('conwo_active_base') || (agent === 'conwo' ? 'light' : 'dark');
      if (base === 'dark') {
        document.documentElement.dataset.bootDark = '1';
        var ac = localStorage.getItem('conwo_active_accent') || '';
        if (ac) document.documentElement.dataset.bootAccent = ac;
      }
    } catch (e) {}
  </script>
```
and the in-`<body>` block:
```html
  <script>
    if (document.documentElement.dataset.bootDark === '1') {
      document.body.classList.add('theme-dark');
      var bootAc = document.documentElement.dataset.bootAccent;
      if (bootAc) document.body.style.setProperty('--accent', bootAc);
    }
  </script>
```

- [ ] **Step 3: Verify build + smoke.** `npx ng build` — expect success. Then a dev smoke (review-time): `npx ng serve` in the background, open the app, switch to Infosec → confirm it still renders violet-on-dark (the fallback + DB accent `#a78bfa` must look identical to before), switch to Conwo → light. Use the `Claude_Preview` MCP `preview_screenshot` if available, else describe manually. (No automated assertion here — visual.)

- [ ] **Step 4: Commit**
```bash
git add src/app/app.ts src/index.html
git commit -m "feat(fe): theme-dark + per-agent --accent applied at runtime and pre-boot"
```

---

## PHASE 2 — multi-agent switcher + admin Create/Manage UI

### Task 4: Multi-agent switcher dropdown (replace binary toggle)

**Files:**
- Modify: `src/app/shared/mode-toggle/mode-toggle.ts` (template + component logic; keep the file/selector so `app.ts`/`app.html` imports are unchanged)

**Context:** Today this is a binary Conwo↔Infosec toggle (`target()`/`label()`/`switch()`, lines ~100-110). With N agents it must list all agents from `agentSvc.agents()`. Keep the component class name `ModeToggle`, the selector, and the fixed top-right placement so `app.ts` (line 8 import, line 14 imports array) and `app.html` need no change.

- [ ] **Step 1: Replace the template** (the `template:` block, lines ~10-18) with a dropdown: a trigger button showing the active agent + an accent dot, and a menu listing every agent. Use Angular control flow (`@if`, `@for`) and signals:

```typescript
  template: `
    <div class="agent-switcher" [class.open]="open()">
      <button class="trigger" (click)="open.set(!open())" [attr.aria-expanded]="open()" title="Switch agent">
        <span class="dot" [style.background]="activeAccent()"></span>
        <span class="name">{{ activeName() }}</span>
        <span class="caret">▾</span>
      </button>
      @if (open()) {
        <div class="menu" role="listbox">
          @for (a of agents(); track a.id) {
            <button class="item" role="option" [class.active]="a.id === activeId()" (click)="choose(a.id)">
              <span class="dot" [style.background]="a.accent || '#1e293b'"></span>
              <span class="name">{{ a.display_name }}</span>
              @if (a.id === activeId()) { <span class="check">✓</span> }
            </button>
          }
        </div>
      }
    </div>
  `,
```

- [ ] **Step 2: Replace the component logic** (`target()`/`label()`/`switch()` and any binary-only fields) with list-driven members. Inject `AgentService`, expose its signals, and add `open`/`choose`:

```typescript
  protected agentSvc = inject(AgentService);
  protected open = signal(false);

  protected agents = this.agentSvc.agents;
  protected activeId = this.agentSvc.activeId;
  protected activeName(): string { return this.agentSvc.activeName(); }
  protected activeAccent(): string { return this.agentSvc.active()?.accent || '#1e293b'; }

  protected choose(id: string): void {
    this.open.set(false);
    if (id !== this.activeId()) this.agentSvc.setActive(id); // persists + reloads to /ask
  }
```
Ensure the imports at the top include `signal` and `inject` from `@angular/core` and `AgentService` from `../../core/agent.service`. Remove now-unused imports/fields. Keep `--mt-*` styles and the `:host-context(body.theme-dark)` block from Task 2.

- [ ] **Step 3: Add menu styles.** In the component `styles:` array add (the existing pill styles can stay for the trigger; add the dropdown bits):
```typescript
    .agent-switcher { position: fixed; top: 14px; right: 18px; z-index: 60; }
    .trigger { display: inline-flex; align-items: center; gap: 8px; padding: 6px 12px;
      border-radius: 999px; border: 1px solid var(--border); background: var(--surface);
      color: var(--text); cursor: pointer; font: inherit; }
    .dot { width: 10px; height: 10px; border-radius: 50%; display: inline-block; flex: none; }
    .caret { opacity: .6; }
    .menu { position: absolute; top: 110%; right: 0; min-width: 200px; padding: 6px;
      background: var(--surface); border: 1px solid var(--border); border-radius: 12px;
      box-shadow: var(--shadow); display: flex; flex-direction: column; gap: 2px; }
    .item { display: flex; align-items: center; gap: 8px; padding: 8px 10px; border: 0;
      background: transparent; color: var(--text); border-radius: 8px; cursor: pointer;
      font: inherit; text-align: left; }
    .item:hover { background: var(--surface-hover); }
    .item.active { background: var(--accent-soft); }
    .item .check { margin-left: auto; color: var(--accent); }
    .item .name, .trigger .name { white-space: nowrap; }
```

- [ ] **Step 4: Verify build.** `npx ng build` — expect success. Review smoke: with the dev server, the top-right control now lists all agents with colored dots and switches on click.

- [ ] **Step 5: Commit**
```bash
git add src/app/shared/mode-toggle/mode-toggle.ts
git commit -m "feat(fe): multi-agent switcher dropdown (replaces binary toggle)"
```

---

### Task 5: API service — admin agent methods

**Files:**
- Modify: `src/app/core/api.service.ts` (add methods near the other `/admin/*` methods, after `adminHeaders()` ~line 829)
- Test: `src/app/core/api.service.spec.ts` (create)

- [ ] **Step 1: Add the three admin methods** to `ApiService`:
```typescript
  // ── Agents (admin) ──────────────────────────────────────────────────────
  createAgent(name: string): Observable<Agent> {
    return this.http.post<Agent>(`${API_BASE}/admin/agents`, { name }, { headers: this.adminHeaders() });
  }
  updateAgent(id: string, patch: { display_name?: string; identity?: string }): Observable<Agent> {
    return this.http.patch<Agent>(`${API_BASE}/admin/agents/${encodeURIComponent(id)}`, patch, { headers: this.adminHeaders() });
  }
  archiveAgent(id: string): Observable<{ status: string; id: string }> {
    return this.http.delete<{ status: string; id: string }>(`${API_BASE}/admin/agents/${encodeURIComponent(id)}`, { headers: this.adminHeaders() });
  }
```

- [ ] **Step 2: Write a spec** `src/app/core/api.service.spec.ts` using `HttpTestingController` to assert the URLs/verbs/body:
```typescript
import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { ApiService } from './api.service';

describe('ApiService agent admin', () => {
  let api: ApiService; let http: HttpTestingController;
  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [ApiService, provideHttpClient(), provideHttpClientTesting()] });
    api = TestBed.inject(ApiService); http = TestBed.inject(HttpTestingController);
  });
  afterEach(() => http.verify());

  it('POSTs name to /admin/agents', () => {
    api.createAgent('Legal').subscribe();
    const r = http.expectOne('/admin/agents');
    expect(r.request.method).toBe('POST');
    expect(r.request.body).toEqual({ name: 'Legal' });
    r.flush({ id: 'legal' });
  });

  it('PATCHes identity to /admin/agents/:id', () => {
    api.updateAgent('legal', { identity: 'x' }).subscribe();
    const r = http.expectOne('/admin/agents/legal');
    expect(r.request.method).toBe('PATCH');
    r.flush({ id: 'legal' });
  });

  it('DELETEs /admin/agents/:id', () => {
    api.archiveAgent('legal').subscribe();
    const r = http.expectOne('/admin/agents/legal');
    expect(r.request.method).toBe('DELETE');
    r.flush({ status: 'archived', id: 'legal' });
  });
});
```

- [ ] **Step 3: Run** `npx ng test --watch=false` — expect these 3 PASS. Then `npx ng build`.

- [ ] **Step 4: Commit**
```bash
git add src/app/core/api.service.ts src/app/core/api.service.spec.ts
git commit -m "feat(fe): api methods create/update/archive agent"
```

---

### Task 6: Manage-Agents admin component (create + list + rename + archive)

**Files:**
- Create: `src/app/features/admin/manage-agents.ts`
- Create: `src/app/features/admin/manage-agents.scss`

**Context:** Follow the existing admin component pattern (`src/app/features/admin/admin-dashboard.ts`): standalone component, `inject(ApiService)`, signals for state, `@if/@for` in the template. The list source is `GET /agents` (public, returns active agents incl. accent) via `AgentService`. Conwo/Infosec are protected (no archive).

- [ ] **Step 1: Create `src/app/features/admin/manage-agents.ts`:**
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
        <p class="hint">Type a name. The agent starts with an empty knowledge base — ingest
          documents to teach it. It gets its own dashboard, traces, ingest, and graph automatically.</p>
        <div class="row">
          <input [(ngModel)]="newName" placeholder="e.g. Legal" (keyup.enter)="create()" [disabled]="busy()" />
          <button class="primary" (click)="create()" [disabled]="busy() || !newName().trim()">
            {{ busy() ? 'Creating…' : 'Create Agent' }}
          </button>
        </div>
        @if (error()) { <p class="error">{{ error() }}</p> }
        @if (created()) {
          <div class="created">
            <span class="dot" [style.background]="created()!.accent"></span>
            Created <strong>{{ created()!.display_name }}</strong> — now selectable in the switcher.
            <div class="identity">Identity: <em>{{ created()!.identity || created()!.description }}</em></div>
          </div>
        }
      </div>

      <h2>Existing agents</h2>
      <table class="agents">
        <thead><tr><th></th><th>Name</th><th>ID</th><th>Theme</th><th></th></tr></thead>
        <tbody>
          @for (a of agents(); track a.id) {
            <tr>
              <td><span class="dot" [style.background]="a.accent || '#1e293b'"></span></td>
              <td>
                @if (editing() === a.id) {
                  <input [(ngModel)]="editName" />
                } @else { {{ a.display_name }} }
              </td>
              <td class="mono">{{ a.id }}</td>
              <td>{{ a.theme_base || (a.id === 'conwo' ? 'light' : 'dark') }}</td>
              <td class="actions">
                @if (editing() === a.id) {
                  <button (click)="saveRename(a)">Save</button>
                  <button (click)="editing.set(null)">Cancel</button>
                } @else {
                  <button (click)="startRename(a)">Rename</button>
                  @if (!isProtected(a.id)) {
                    <button class="danger" (click)="archive(a)">Archive</button>
                  } @else { <span class="protected">built-in</span> }
                }
              </td>
            </tr>
          }
        </tbody>
      </table>
    </section>
  `,
})
export class ManageAgents {
  private api = inject(ApiService);
  private agentSvc = inject(AgentService);

  agents = this.agentSvc.agents;
  newName = signal('');
  busy = signal(false);
  error = signal('');
  created = signal<Agent | null>(null);
  editing = signal<string | null>(null);
  editName = '';

  constructor() { this.agentSvc.loadAgents(); }

  isProtected(id: string): boolean { return PROTECTED.has(id); }

  create(): void {
    const name = this.newName().trim();
    if (!name || this.busy()) return;
    this.busy.set(true); this.error.set(''); this.created.set(null);
    this.api.createAgent(name).subscribe({
      next: (agent) => {
        this.busy.set(false);
        this.created.set(agent);
        this.newName.set('');
        this.agentSvc.loadAgents(); // refresh switcher list
      },
      error: (err) => {
        this.busy.set(false);
        this.error.set(err?.error?.detail || 'Could not create agent. It may already exist.');
      },
    });
  }

  startRename(a: Agent): void { this.editing.set(a.id); this.editName = a.display_name; }

  saveRename(a: Agent): void {
    const name = this.editName.trim();
    if (!name) return;
    this.api.updateAgent(a.id, { display_name: name }).subscribe({
      next: () => { this.editing.set(null); this.agentSvc.loadAgents(); },
      error: () => this.error.set('Rename failed.'),
    });
  }

  archive(a: Agent): void {
    if (!confirm(`Archive "${a.display_name}"? It will disappear from the switcher.`)) return;
    this.api.archiveAgent(a.id).subscribe({
      next: () => this.agentSvc.loadAgents(),
      error: (err) => this.error.set(err?.error?.detail || 'Archive failed.'),
    });
  }
}
```

- [ ] **Step 2: Create `src/app/features/admin/manage-agents.scss`** (reuse design tokens; dark theme handled globally):
```scss
.manage-agents { max-width: 820px; margin: 0 auto; padding: 32px 20px; color: var(--text); }
h1 { margin: 0 0 20px; }
h2 { margin: 28px 0 12px; font-size: 1.05rem; }
.hint { color: var(--text-muted); margin: 0 0 12px; }
.create-card { background: var(--surface); border: 1px solid var(--border); border-radius: 14px; padding: 20px; }
.row { display: flex; gap: 10px; }
.row input { flex: 1; padding: 10px 12px; border: 1px solid var(--border); border-radius: 10px;
  background: var(--surface); color: var(--text); font: inherit; }
button { padding: 9px 14px; border-radius: 10px; border: 1px solid var(--border);
  background: var(--surface); color: var(--text); cursor: pointer; font: inherit; }
button.primary { background: var(--accent); color: var(--text-on-accent); border-color: transparent; }
button.danger { color: var(--error); border-color: var(--error-border); }
button:disabled { opacity: .5; cursor: default; }
.error { color: var(--error); margin: 10px 0 0; }
.created { margin: 14px 0 0; padding: 12px; border-radius: 10px; background: var(--accent-soft); }
.created .identity { color: var(--text-muted); font-size: .9rem; margin-top: 4px; }
.dot { width: 11px; height: 11px; border-radius: 50%; display: inline-block; vertical-align: middle; }
table.agents { width: 100%; border-collapse: collapse; margin-top: 4px; }
table.agents th, table.agents td { text-align: left; padding: 10px 8px; border-bottom: 1px solid var(--border); }
.mono { font-family: ui-monospace, monospace; color: var(--text-muted); }
.actions { display: flex; gap: 8px; align-items: center; }
.protected { color: var(--text-subtle); font-size: .85rem; }
```

- [ ] **Step 3: Verify build.** `npx ng build` — expect success.

- [ ] **Step 4: Commit**
```bash
git add src/app/features/admin/manage-agents.ts src/app/features/admin/manage-agents.scss
git commit -m "feat(fe): Manage Agents admin component (create/rename/archive)"
```

---

### Task 7: Route + sidebar nav item

**Files:**
- Modify: `src/app/app.routes.ts` (add a route near the `/admin` route, ~lines 27-29)
- Modify: `src/app/shared/app-sidebar/app-sidebar.ts` (the `navItems` array)

- [ ] **Step 1: Add the admin-gated route** in `src/app/app.routes.ts`, mirroring the existing `/admin` route's guards:
```typescript
  {
    path: 'admin/agents',
    canActivate: [authGuard, roleGuard(['admin'])],
    loadComponent: () => import('./features/admin/manage-agents').then(m => m.ManageAgents),
  },
```
(Place it adjacent to the existing `path: 'admin'` route. Confirm `authGuard` and `roleGuard` are already imported in this file — they are, used by the `/admin` route.)

- [ ] **Step 2: Add a nav item.** In `src/app/shared/app-sidebar/app-sidebar.ts`, read the existing `navItems` array and its `NavItem` shape, then add an admin-only entry consistent with that shape. Based on the existing pattern `{ label, route, icon, roles }`:
```typescript
    { label: 'Manage Agents', route: '/admin/agents', icon: 'agents', roles: ['admin'] },
```
If the `NavItem` shape differs (e.g. no `icon`, or a different role-filtering field), MATCH the existing entries exactly — read the array first and copy the structure of the existing admin item (e.g. the one routing to `/admin`). If `icon: 'agents'` has no registered glyph, reuse an existing icon key used by another admin item rather than inventing one.

- [ ] **Step 3: Verify build.** `npx ng build` — expect success.

- [ ] **Step 4: Commit**
```bash
git add src/app/app.routes.ts src/app/shared/app-sidebar/app-sidebar.ts
git commit -m "feat(fe): admin route + nav item for Manage Agents"
```

---

### Task 8: End-to-end verification

**Files:** none (verification)

- [ ] **Step 1: Clean build + unit tests.**
```bash
cd /Users/rudrakhare/Desktop/my-wiki/org-wiki/frontend
npx ng build          # expect: Application bundle generation complete
npx ng test --watch=false   # expect: all specs pass (Tasks 1 + 5)
grep -rn "theme-infosec" src/   # expect: no code matches (comments only, if any)
```

- [ ] **Step 2: Live smoke (needs backend running on :8000 + an admin login).** With `npx ng serve` and the backend up:
  1. Log in as admin, open **Manage Agents** (sidebar, admin-only).
  2. Create an agent named "Legal" → it appears in the success card with an accent swatch + identity, and in the top-right switcher dropdown.
  3. Switch to "Legal" → app reloads on `/ask`, themed dark with Legal's accent color (dots, focus rings, glow tint match its hue). Its Dashboard/Traces/Ingest/Graph load empty + isolated.
  4. Switch to Conwo → light theme intact. Switch to Infosec → violet-on-dark, unchanged from before.
  5. In Manage Agents: rename "Legal", confirm the switcher updates; archive "Legal", confirm it disappears from the switcher; confirm Conwo/Infosec show "built-in" with no Archive button.
  Capture screenshots via the `Claude_Preview` MCP (`preview_screenshot`) if available.

- [ ] **Step 3: Commit any fixups; milestone done.**

---

## Milestone exit criteria
- Admin can create an agent from the UI; it provisions via `POST /admin/agents` and immediately appears in the switcher with its own accent.
- Switcher lists all agents (not a binary toggle); selecting one switches the whole app.
- Each dark agent renders the shared dark base tinted by its own `--accent` (zero per-agent CSS); Conwo stays light; Infosec unchanged (violet).
- Rename + archive work from Manage Agents; Conwo/Infosec are protected.
- `npx ng build` is clean; unit specs (Tasks 1, 5) pass; no `theme-infosec` left in code.
- Anti-flash: reloading as a dark agent shows the correct base + accent before Angular boots.
