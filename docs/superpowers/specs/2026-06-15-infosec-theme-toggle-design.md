# Infosec Theme + Futuristic Mode Toggle — Design

_Date: 2026-06-15 · Status: draft for owner review · Builds on: Plan 1 (backend) + Plan 2 (frontend switcher), branch `claude/hopeful-roentgen-cda2f4`_

---

## 0. Plain-language summary

When the app is in **Infosec** mode, give it a dark, futuristic "security console" skin
(deep near-black background, **violet** accents, subtle glow). **Conwo** mode looks
**exactly as it does today** (light theme). Replace the current sidebar agent dropdown
with a single **futuristic toggle button** whose label points at where you'll go
("Switch to Infosec" / "Switch to Conwo").

This is **theming + one control**, not a re-architecture. Layout, routing, components,
and data are untouched. It's driven entirely by CSS variables flipped by a class on
`<body>`, so the switch is instant and no component templates change for the theme.

Visual intensity chosen: **electric** (the glow-heavy direction) — glowing borders,
neon-ish focus rings, faint grid + glow background, glowing pill. Any single element
can be dialled down during build if it reads as too much in the real app.

---

## 1. Goals & non-goals

### Goals
- A dark, futuristic **violet** visual theme that applies **only** in Infosec mode.
- Remove the existing sidebar dropdown; add a **futuristic toggle button** anchored right.
- Persist the selected mode across reloads (already handled by `AgentService`).
- **Conwo's colors, background, fonts, spacing, and components stay byte-for-byte unchanged.**

### Non-goals
- No change to routing, component templates/logic, layout structure, or data flow
  (beyond the toggle control + the theme class hook).
- No backend changes.
- No new agent behavior — this rides on the existing two agents (`conwo`, `infosec`).
- Not a general N-theme system; exactly two themes (Conwo light = default, Infosec violet).

---

## 2. Theming mechanism

The app is already fully tokenized: every color/background/shadow/font in
`frontend/src/styles.scss` comes from CSS custom properties under `:root`, and all
components consume them (`var(--bg)`, `var(--surface)`, `var(--accent)`, …).

- **Conwo (default):** the existing `:root` token values — **unchanged**.
- **Infosec:** a new `body.theme-infosec { … }` block that overrides those same
  variable *values* (dark violet palette + glow shadow tokens). Because components read
  the variables, the entire app reskins with **zero markup changes**.
- A class on `<body>` (`theme-infosec` present/absent) flips the theme instantly.

**Anti-flash on reload:** switching agents persists the choice and reloads the page
(existing `AgentService.setActive` behavior). To avoid a flash of the wrong theme before
Angular boots, add a tiny inline script in `frontend/src/index.html` that reads the
persisted agent from `localStorage` (`conwo_active_agent`) and sets
`document.body.className = 'theme-infosec'` when it's `infosec`, before the app loads.
Angular then keeps it in sync via an `effect()` on `AgentService.activeId`.

---

## 3. Infosec palette (electric violet) — token overrides

Approximate values (final hex tuned during build for contrast/legibility):

| Token | Conwo (unchanged) | Infosec (electric violet) |
|---|---|---|
| `--bg` | `#fafaf9` | `#0b0a12` (near-black, deep navy-violet) |
| `--surface` | `#ffffff` | `#15101f` |
| `--surface-muted` | `#f5f5f4` | `#1b1530` |
| `--border` | `#e7e5e4` | `rgba(167,139,250,0.22)` (violet-tinted) |
| `--border-focus` | `#94a3b8` | `#a78bfa` (neon focus ring) |
| `--text` | `#1c1917` | `#f0ecff` |
| `--text-muted` | `#57534e` | `#8b86a0` |
| `--accent` | `#1e293b` | `#a78bfa` (electric violet) |
| `--accent-hover` | `#0f172a` | `#c4b5fd` |
| `--accent-ring` | `rgba(30,41,59,0.12)` | `rgba(167,139,250,0.45)` (glow) |
| `--text-on-accent` | `#ffffff` | `#0b0a12` |
| `--shadow` / `--shadow-sm` | barely-there grey | violet-tinted glow (`… rgba(167,139,250,0.35)`) |
| status colors | as-is | brightened for dark bg (legible) |

Plus, under `body.theme-infosec`:
- **Background overlay** on `body`: a faint radial violet glow (top-right) + a barely
  visible grid (`linear-gradient` 1px lines at ~6% violet) — the "electric" look.
- **Glow accents:** interactive elements get a soft violet box-shadow on hover/focus;
  cards get a subtle neon edge highlight.
- **Monospace accent:** labels / IDs / metadata may use the existing `--font-mono`
  (body text keeps the existing sans font).
- **Accessibility:** text/background pairings kept at WCAG-AA-legible contrast.

> All of the above are variable values + a handful of `body.theme-infosec`-scoped rules
> in `styles.scss`. No component `.scss` files change.

---

## 4. The toggle control

**Remove:** the sidebar agent dropdown built in Plan 2 (the `.sb-agent` brand chevron +
`.sb-agent-menu` in `app-sidebar.ts`). The sidebar brand label (showing the active
agent name) **stays**.

**Add:** a new standalone `ModeToggle` component rendered in the app shell, shown only
when signed in (same condition as the sidebar, `showHeaderNav()`):

- **Conwo mode → floating pill**, fixed to the **top-right of the viewport**, hovering
  over content (adds nothing to layout — keeps Conwo's chrome pixel-identical).
- **Infosec mode → inline top strip**: a thin bar at the top of the content area with
  the pill **right-aligned** in it. (The strip exists only in Infosec; Conwo uses the
  floating pill, so Conwo's layout is unchanged.)
- **Label = destination:** `Switch to Infosec` when in Conwo; `Switch to Conwo` when in
  Infosec.
- **Style:** futuristic pill — glow + smooth transition/slide animation on click; in
  Infosec it's the glowing violet pill, in Conwo a clean light pill consistent with
  Conwo's current styling.
- **Action:** calls `AgentService.setActive('<the other agent id>')` — persists +
  reloads (existing behavior). With exactly two agents this is a true toggle. (If a 3rd
  agent is ever added, revisit; out of scope now.)

---

## 5. Files touched (scope guardrails)

| File | Change |
|---|---|
| `frontend/src/styles.scss` | Add `body.theme-infosec { … }` token overrides + background overlay + glow rules. `:root` (Conwo) untouched. |
| `frontend/src/index.html` | Add anti-flash inline script (reads `conwo_active_agent`, sets body class pre-boot). |
| `frontend/src/app/shared/mode-toggle/mode-toggle.ts` (new) | The toggle component (floating pill / inline strip + label + animation). |
| `frontend/src/app/app.ts` + `app.html` | Render `<app-mode-toggle>` in the shell (when signed in); `effect()` syncs `body.theme-infosec` to `AgentService.activeId`. |
| `frontend/src/app/shared/app-sidebar/app-sidebar.ts` | **Remove** the `.sb-agent` dropdown + menu (keep the brand label). |

**Not touched:** routing, other component templates/logic, any feature `.scss`, backend.

---

## 6. Verification

- `npx ng build` clean (compile/type-check gate).
- Manual/companion check: Conwo renders identically to current (light, no strip, floating
  pill top-right); Infosec shows the dark violet theme + inline strip pill.
- Toggle label reflects destination; clicking switches + persists across reload; no theme
  flash on reload.
- Contrast spot-check on Infosec text/links/cards.
- Conwo regression: nothing in Conwo's colors/layout changed.
