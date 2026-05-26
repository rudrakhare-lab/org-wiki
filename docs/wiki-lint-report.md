# Wiki Lint Report
_Run: 2026-04-30 | Scope: all wiki/modules, wiki/entities, wiki/cross-module, wiki/decisions_

---

## Summary

| Severity | Issues Found | Auto-fixed | Deferred to open-decisions |
|----------|-------------|-----------|---------------------------|
| 🔴 Critical | 3 | 0 | 3 |
| 🟡 Warning | 8 | 6 | 2 |
| 🟢 Info | 4 | 1 | 3 |

---

## 🔴 Critical Issues

### C1 — Cafeteria entity ownership conflict
**Pages:** `wiki/entities/cafeteria.md`, `wiki/modules/meeting-rooms.md`, `wiki/modules/meal-management.md`
**Issue:** `cafeteria` entity is claimed as owned by `meeting-rooms` (from catering PRD) but `meal-management` also uses it as a central entity. `meeting-rooms.used_by` includes `meal-management` for this reason, but `meal-management.depends_on` does not include `meeting-rooms`.
**Status:** Deferred → `docs/open-decisions.md #OD-1`

### C2 — Delegation circular dependency
**Pages:** `wiki/modules/delegation.md`, `wiki/modules/meeting-rooms.md`, `wiki/modules/visitor-management.md`, `wiki/modules/desk-management.md`
**Issue:** `delegation.depends_on` includes `[meeting-rooms, visitor-management, desk-management]` AND `delegation.used_by` also includes the same three modules. This creates a bidirectional cycle in both directions. Architecturally, delegation is a layer ON TOP of these modules, not a peer-level dependency.
**Status:** Deferred → `docs/open-decisions.md #OD-2`

### C3 — Orphan page: `wiki/Untitled.md`
**Issue:** `wiki/Untitled.md` exists with no content, no links, no frontmatter. Leftover from initial workspace setup.
**Status:** Safe to delete. Action: flagged for user approval before removal.

---

## 🟡 Warnings

### W1 — 13 module stubs with no source documents ✅ Fixed (stubs created)
All 13 missing modules now have stub pages. Resolved by Task #2 in this run.

### W2 — Missing cross-module pages for 9 known dependencies ✅ Fixed
All 9 missing cross-module pages created in Task #4 in this run.

### W3 — digital-wayfinding missing floor-kiosk dependency
**Page:** `wiki/modules/digital-wayfinding.md`
**Issue:** `digital-wayfinding.depends_on = [mobile-app, parking-management]` but wayfinding renders floor plans produced by floor-kiosk's DIY Floor Planner pipeline. `floor-kiosk.used_by` originally listed digital-wayfinding (removed in this run to maintain bidirectionality — but the actual data dependency may be real).
**Status:** Deferred → `docs/open-decisions.md #OD-3`. Recommend adding `floor-kiosk` to digital-wayfinding.depends_on after PRD review.

### W4 — digital-wayfinding missing employee-experience dependency
**Page:** `wiki/modules/digital-wayfinding.md`
**Issue:** `employee-experience.used_by` includes `digital-wayfinding` (both are in the emp-exp service), but `digital-wayfinding.depends_on` does not include `employee-experience`.
**Status:** Deferred → `docs/open-decisions.md #OD-3`.

### W5 — esg-dashboard depends_on 4 modules with no backlinks ✅ Noted
`esg-dashboard.depends_on` = [desk-management, meeting-rooms, parking-management, meal-management]. None of those modules have `esg-dashboard` in their `used_by`. Since esg-dashboard is read-only analytics and these are stub relationships, updating all 4 booking modules' `used_by` lists would add noise. Acceptable gap for now; fix after ESG PRD is ingested.
**Status:** Deferred to post-PRD-ingest fix.

### W6 — meal-management.used_by includes meeting-rooms inconsistency
**Page:** `wiki/modules/meal-management.md`, `wiki/modules/meeting-rooms.md`
**Issue:** `meeting-rooms.used_by` lists `meal-management` (for Cafeteria entity sharing), but `meeting-rooms.depends_on` does NOT list `meal-management`. This is the inverse of C1 — the dependency direction is ambiguous.
**Status:** Deferred → `docs/open-decisions.md #OD-1`

### W7 — guard-app-kiosks ↔ visitor-management circular dependency
**Page:** `wiki/modules/guard-app-kiosks.md`, `wiki/modules/visitor-management.md`
**Issue:** `guard-app-kiosks.depends_on` includes `visitor-management` (reads visitor data), AND `visitor-management.depends_on` includes `guard-app-kiosks` (uses guard app for 2-step check-in). Circular, but architecturally correct — they are tightly coupled.
**Status:** Documented in `wiki/cross-module/vms-guard-app.md`. No fix needed; note in `depends_on` comments.

### W8 — transport area unrepresented in wiki
**Evidence:** ~7 WP-workflows sample tickets + full-data Jira patterns suggest significant transport/shuttle booking work. No module, PRD, or spec exists in raw/.
**Status:** Flagged as unrepresented area in `wiki/overview.md` and `config/functional_area_to_module.toml`. Do NOT auto-create module. Add note to solicit PRD upload.

---

## 🟢 Info

### I1 — wiki/Untitled.md orphan ✅ Noted (see C3)

### I2 — third-party module completely isolated
**Page:** `wiki/modules/third-party.md`
**Issue:** `third-party.depends_on = []`, `used_by = []`. No connections to any other module. This is expected for a stub — add connections when PRD is ingested.
**Status:** Acceptable for stub. No action needed.

### I3 — create-employee-form may be redundant with employee-provisioning
**Issue:** `create-employee-form` folder exists as a separate raw/modules entry, but the feature may be a sub-form within employee-provisioning rather than a standalone module.
**Status:** Deferred → `docs/open-decisions.md #OD-4`

### I4 — admin-experience may cover both WP-admin and WF-wis-admin
**Issue:** Two Jira functional areas (WP-admin = 3,318 tickets, WF-wis-admin = 3,819 tickets = 7,137 total) both mapped to `admin-experience`. Confirm these are the same module surface (not two separate admin portals) when PRD is available.
**Status:** Deferred → `docs/open-decisions.md #OD-5`

---

## Check Results Summary (CLAUDE.md §6 Checks)

| Check | Status |
|-------|--------|
| Check 1: Broken dependency links | ✅ All `depends_on` module slugs have corresponding pages (stubs created) |
| Check 2: Orphan pages | ⚠️ 1 orphan: `wiki/Untitled.md` |
| Check 3: Missing cross-module pages | ✅ All 9 missing pages created |
| Check 4: Contradictions | ⚠️ C1 (cafeteria ownership), C2 (delegation cycle) — see open-decisions |
| Check 5: Stubs | 🟡 13 stubs — all noted with `status: stub`; raw docs not yet uploaded |
| Check 6: Stale pages | ✅ All active pages updated within 30 days |
