# Infosec Theme + Futuristic Mode Toggle — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Give Infosec mode a dark electric-violet "security console" theme and replace the sidebar agent dropdown with a futuristic right-anchored toggle button — without changing layout, routing, components, or data, and with Conwo's appearance unchanged.

**Architecture:** Pure CSS-variable theming. A `body.theme-infosec` block in `styles.scss` overrides the existing `:root` design tokens (Conwo's values stay as-is). A new standalone `ModeToggle` component renders a floating pill (Conwo) or an inline top strip (Infosec) and calls the existing `AgentService.setActive()`. An inline script in `index.html` sets the theme class before Angular boots (no flash); an `effect()` keeps it synced.

**Tech Stack:** Angular standalone components + signals; `npx ng build` (run from `frontend/`) is the compile/type-check gate. Pre-existing budget WARNINGS for `initial` + `ask.scss` are expected — ignore them.

**Companion spec:** `docs/superpowers/specs/2026-06-15-infosec-theme-toggle-design.md`

---

## Conventions
- All commands from `frontend/`. `node_modules` already installed.
- Gate per task: `npx ng build` ends "Application bundle generation complete", no errors.
- Commit after each task.
- **Conwo must look identical to before.** Only `body.theme-infosec`-scoped rules change appearance; `:root` is untouched.

---

## Task 1: Infosec theme token block in `styles.scss`

**Files:** Modify `frontend/src/styles.scss`

- [ ] **Step 1:** Read `src/styles.scss`. Confirm the `:root { … }` token block (ends ~line 64). **Do not edit `:root`.**

- [ ] **Step 2:** Append a new theme block at the end of the file:

```scss
/* ── Infosec theme (electric violet) ───────────────────────────────────────
   Overrides ONLY the token VALUES. Conwo (:root) is untouched. Applied when
   <body class="theme-infosec">. */
body.theme-infosec {
  /* surfaces */
  --bg: #0b0a12;
  --surface: #15101f;
  --surface-muted: #1b1530;
  --surface-hover: #221a3a;
  --surface-inset: #120e1c;

  /* borders */
  --border: rgba(167, 139, 250, 0.22);
  --border-strong: rgba(167, 139, 250, 0.38);
  --border-focus: #a78bfa;

  /* text */
  --text: #f0ecff;
  --text-muted: #9b95b3;
  --text-subtle: #6f6986;
  --text-on-accent: #0b0a12;

  /* accent — electric violet */
  --accent: #a78bfa;
  --accent-hover: #c4b5fd;
  --accent-soft: #1b1530;
  --accent-ring: rgba(167, 139, 250, 0.45);

  /* status — brightened for dark bg */
  --success: #4ade80; --success-soft: #0e1f14; --success-border: #1f5132;
  --warning: #fbbf24; --warning-soft: #241c08; --warning-border: #5a4711;
  --error:   #f87171; --error-soft:   #2a1212; --error-border:   #5e2020;
  --info:    #818cf8; --info-soft:    #14152b; --info-border:    #2b2f5e;

  /* shadows — violet glow */
  --shadow-sm: 0 1px 2px rgba(0,0,0,0.5), 0 0 0 1px rgba(167,139,250,0.06);
  --shadow: 0 1px 3px rgba(0,0,0,0.5), 0 8px 28px -8px rgba(167,139,250,0.35);

  /* fonts unchanged (body keeps sans; --font-mono available for IDs/labels) */

  /* faint grid + glow background overlay */
  background-color: #0b0a12;
  background-image:
    radial-gradient(120% 80% at 85% -10%, rgba(167,139,250,0.16), transparent 55%),
    linear-gradient(rgba(167,139,250,0.05) 1px, transparent 1px),
    linear-gradient(90deg, rgba(167,139,250,0.05) 1px, transparent 1px);
  background-size: auto, 26px 26px, 26px 26px;
  background-attachment: fixed;

  /* electric edge: glow focus ring on interactive elements */
  & a:focus-visible, & button:focus-visible, & input:focus-visible,
  & textarea:focus-visible, & select:focus-visible {
    outline: 2px solid var(--accent);
    outline-offset: 1px;
    box-shadow: 0 0 0 4px var(--accent-ring);
  }
}
```

- [ ] **Step 3:** `npx ng build` → success.
- [ ] **Step 4:** Commit:
```bash
git add frontend/src/styles.scss
git commit -m "feat(fe): Infosec electric-violet theme token block (body.theme-infosec)"
```

---

## Task 2: Apply the theme class (anti-flash script + synced effect)

**Files:** Modify `frontend/src/index.html`, `frontend/src/app/app.ts`

- [ ] **Step 1:** In `src/index.html`, inside `<head>` (after the existing `<script src="…gsi/client">` line is fine), add an inline script that sets the theme class before Angular boots:

```html
  <script>
    /* Pre-boot theme: avoid a flash of the wrong theme on reload. */
    try {
      if ((localStorage.getItem('conwo_active_agent') || 'conwo') === 'infosec') {
        document.documentElement.dataset.bootTheme = 'infosec';
      }
    } catch (e) {}
  </script>
```
And update `<body>` to honor it (so the class is present at first paint):
```html
  <body>
    <script>
      if (document.documentElement.dataset.bootTheme === 'infosec') {
        document.body.classList.add('theme-infosec');
      }
    </script>
    <div class="liquid-chrome" aria-hidden="true"></div>
    <app-root></app-root>
  </body>
```
(Keep the existing `liquid-chrome` div and `app-root`.)

- [ ] **Step 2:** In `src/app/app.ts`, inject `AgentService` (already imported/injected from Plan 2 as `private agentSvc`). Add an `effect()` in the constructor that keeps `body.theme-infosec` in sync with the active agent:

```typescript
import { Component, inject, signal, effect } from '@angular/core';
// … in the constructor, after existing setup:
    effect(() => {
      const infosec = this.agentSvc.activeId() === 'infosec';
      if (typeof document !== 'undefined') {
        document.body.classList.toggle('theme-infosec', infosec);
      }
    });
```
(If `effect` isn't imported yet, add it to the `@angular/core` import. `agentSvc` already exists from Plan 2.)

- [ ] **Step 3:** `npx ng build` → success.
- [ ] **Step 4:** Commit:
```bash
git add frontend/src/index.html frontend/src/app/app.ts
git commit -m "feat(fe): apply theme-infosec body class (pre-boot + synced effect)"
```

---

## Task 3: `ModeToggle` component

**Files:** Create `frontend/src/app/shared/mode-toggle/mode-toggle.ts`

- [ ] **Step 1:** Create the component:

```typescript
import { Component, computed, inject } from '@angular/core';
import { AgentService } from '../../core/agent.service';

/**
 * Futuristic mode toggle. Floating pill (Conwo) / inline top strip (Infosec).
 * Label reflects the DESTINATION. Switching persists + reloads via AgentService.
 */
@Component({
  selector: 'app-mode-toggle',
  standalone: true,
  template: `
    <div class="mode-toggle" [class.strip]="isInfosec()" [class.floating]="!isInfosec()">
      <button type="button" class="mode-pill" (click)="switch()" [title]="label()">
        <span class="mode-pill-arrows" aria-hidden="true">⇄</span>
        <span class="mode-pill-label">{{ label() }}</span>
      </button>
    </div>
  `,
  styles: [`
    .mode-toggle.floating {
      position: fixed; top: 14px; right: 18px; z-index: 50;
    }
    .mode-toggle.strip {
      position: sticky; top: 0; z-index: 40;
      display: flex; justify-content: flex-end; align-items: center;
      padding: 8px 16px;
      border-bottom: 1px solid var(--border);
      background: color-mix(in srgb, var(--bg) 82%, transparent);
      backdrop-filter: saturate(140%) blur(8px);
    }
    .mode-pill {
      display: inline-flex; align-items: center; gap: 8px;
      font-family: var(--font-mono); font-size: 0.78rem; font-weight: 600;
      color: var(--text-on-accent); background: var(--accent);
      border: 1px solid var(--accent); border-radius: var(--radius-pill);
      padding: 7px 14px; cursor: pointer;
      box-shadow: 0 0 0 0 var(--accent-ring);
      transition: box-shadow .25s ease, transform .15s ease, background .2s ease;
    }
    .mode-pill:hover { background: var(--accent-hover); box-shadow: 0 0 18px var(--accent-ring); }
    .mode-pill:active { transform: scale(0.96); }
    .mode-pill-arrows { transition: transform .3s ease; }
    .mode-pill:hover .mode-pill-arrows { transform: rotate(180deg); }
  `]
})
export class ModeToggle {
  private agentSvc = inject(AgentService);

  isInfosec = computed(() => this.agentSvc.activeId() === 'infosec');
  target = computed(() => (this.agentSvc.activeId() === 'infosec' ? 'conwo' : 'infosec'));
  label = computed(() => {
    const id = this.target();
    const name = this.agentSvc.agents().find(a => a.id === id)?.display_name
      ?? (id === 'infosec' ? 'Infosec' : 'Conwo');
    return `Switch to ${name}`;
  });

  switch(): void {
    this.agentSvc.setActive(this.target());  // persists + reloads as the other agent
  }
}
```

> Note: the pill uses `var(--accent)`/`var(--accent-ring)`, so it's a clean light pill in Conwo and a glowing violet pill in Infosec automatically — one component, both looks.

- [ ] **Step 2:** `npx ng build` → success (component not yet rendered; this just confirms it compiles).
- [ ] **Step 3:** Commit:
```bash
git add frontend/src/app/shared/mode-toggle/mode-toggle.ts
git commit -m "feat(fe): ModeToggle component (floating pill / inline strip)"
```

---

## Task 4: Wire the toggle into the shell + remove the sidebar dropdown

**Files:** Modify `frontend/src/app/app.ts`, `frontend/src/app/app.html`, `frontend/src/app/shared/app-sidebar/app-sidebar.ts`

- [ ] **Step 1:** In `app.ts`, import + add `ModeToggle` to the component `imports`:
```typescript
import { ModeToggle } from './shared/mode-toggle/mode-toggle';
// @Component imports: [RouterOutlet, AppSidebar, ModeToggle]
```

- [ ] **Step 2:** In `app.html`, render the toggle inside `<main>` at the top, only when signed in:
```html
@if (showHeaderNav()) {
  <app-sidebar (signOut)="signOut()" />
}

<main class="app-main" [class.full]="!showHeaderNav()">
  @if (showHeaderNav()) { <app-mode-toggle /> }
  <router-outlet />
</main>
```
(Placing it as the first child of `<main>`: the Infosec `.strip` becomes a sticky top bar above content; the Conwo `.floating` pill is `position:fixed` so it ignores flow — Conwo's content layout is unchanged.)

- [ ] **Step 3:** In `app-sidebar.ts`, **remove the dropdown** added in Plan 2 — keep the brand label. Replace the `.sb-agent` wrapper block (the brand `<a>` + chevron button + `@if (agentMenuOpen())` menu) with just the brand link:
```html
        <a routerLink="/ask" class="sb-brand" (click)="closeMobile()"
           [attr.aria-label]="agentSvc.activeName() + ' — home'">
          <img src="logo.png" alt="" class="sb-logo" />
          <span class="sb-name sb-label">{{ agentSvc.activeName() }}</span>
        </a>
```
Then remove the now-unused class members `agentMenuOpen` and `onSelectAgent()`, and the `.sb-agent`, `.sb-agent-toggle`, `.sb-agent-menu`, `.sb-agent-item*` style rules. **Keep** `agentSvc = inject(AgentService)` (the brand label still uses `agentSvc.activeName()`). Leave all other nav/recent/footer markup untouched.

- [ ] **Step 4:** `npx ng build` → success.
- [ ] **Step 5:** Commit:
```bash
git add frontend/src/app/app.ts frontend/src/app/app.html frontend/src/app/shared/app-sidebar/app-sidebar.ts
git commit -m "feat(fe): render ModeToggle in shell; remove sidebar agent dropdown"
```

---

## Task 5: Build + visual verification

**Files:** none (verification)

- [ ] **Step 1:** `npx ng build` clean.
- [ ] **Step 2:** With backend (:8000) + `ng serve` (:4200) running, sign in. Verify:
  1. **Conwo** looks identical to before — light theme, **no top strip**, a clean floating pill top-right reading **"Switch to Infosec"**. Sidebar has the brand (no dropdown chevron).
  2. Click it → reloads into **Infosec**: dark violet theme, faint grid/glow background, glowing cards/links, **inline top strip** with a glowing violet pill reading **"Switch to Conwo"**.
  3. No theme flash on reload (anti-flash script).
  4. Click again → back to Conwo, identical to step 1.
  5. Text is legible in Infosec (contrast spot-check on body text, muted text, links).
- [ ] **Step 3:** Record pass/fail per check; fix in the relevant task if any fail.

---

## Exit criteria
- `npx ng build` clean.
- Conwo renders identically to before (light, floating pill, no strip, sidebar dropdown gone).
- Infosec shows the electric-violet theme + inline-strip glowing pill.
- Toggle label = destination; switch persists across reload with no flash.
- No routing/data/other-component/backend changes.
