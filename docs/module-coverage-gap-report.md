# Module Coverage Gap Report
_Generated: 2026-04-30_

---

## Summary

| Category | Count |
|----------|-------|
| Raw module folders in `raw/modules/` | 22 |
| Wiki module pages in `wiki/modules/` | 9 |
| Modules fully ingested from source docs | 9 |
| Modules with empty raw folder (no docs yet) | 13 |
| Missing cross-module pages for known dependencies | 9 |
| Bidirectionality violations in existing pages | 6 |

---

## A) Already Ingested Modules

| Module | Source Docs Ingested | Status |
|--------|---------------------|--------|
| `meeting-rooms` | 8 docs (PRD, kiosk, catering, dynamic policy, maintenance, Outlook × 2, resources) | active |
| `parking-management` | 3 docs (PRD, dynamic policy, waitlist) | active |
| `visitor-management` | 2 docs (PRD, implementation SOP) | active |
| `delegation` | 1 doc (PRD) | active |
| `digital-wayfinding` | 1 doc (SOP) | active |
| `employee-experience` | Derived from delegation + wayfinding docs | active |
| `floor-kiosk` | 3 docs (DIY Floor Planner PRD, device spec, floor plan SOP) | active |
| `meal-management` | 1 doc (meal check-in PRD) | active |
| `implementation` | 1 doc (ETS server SOP) | active |

---

## B) Raw Docs Present But Not Yet Ingested

All remaining raw/modules/* folders are **empty**. The following files exist but are "Copy of Copy of"
duplicates of already-ingested originals and should NOT be re-ingested:

| File | Status |
|------|--------|
| `raw/modules/meal-management/Copy of Copy of Meal Check-in via Access Card PRD .docx` | Duplicate of `sources/meal-checkin-prd` |
| `raw/modules/meeting-rooms/Copy of Copy of Meeting Rooms App PRD.docx` | Duplicate of `sources/meeting-rooms-app-prd` |
| `raw/modules/meeting-rooms/Copy of Meeting Rooms App PRD.docx` | Duplicate of `sources/meeting-rooms-app-prd` |
| `raw/modules/parking-management/Copy of Copy of MoveInSync Workplace - Dynamic Policy for Parking.docx` | Duplicate of `sources/dynamic-policy-parking` |
| `raw/modules/visitor-management/Copy of Copy of Visitor Management PRD.docx` | Duplicate of `sources/vms-prd` |

**Action required:** Upload PRDs/specs for the 13 missing modules into their respective `raw/modules/<slug>/` folders.
Priority order for upload (based on reference frequency in existing wiki):

1. `desk-management` — referenced by parking-management, delegation, meal-management, implementation
2. `tags-desk-parking` — referenced by meeting-rooms, parking-management
3. `mobile-app` — referenced by meeting-rooms, parking-management, delegation, digital-wayfinding, implementation
4. `guard-app-kiosks` — referenced by visitor-management
5. `ms-teams-integration` — referenced by meeting-rooms
6. `access-management` — referenced by meal-management
7. `sso` — referenced by employee-provisioning (likely)
8. `employee-provisioning` — standalone, needed for onboarding coverage
9. `admin-experience` — large Jira footprint (WP-admin + WF-wis-admin = ~7,137 tickets)
10. `create-employee-form` — likely part of employee-provisioning flow
11. `esg-dashboard` — analytics module
12. `safe-reach` — safety/emergency features
13. `third-party` — external integrations

---

## C) Module Pages Missing or Stale

All 13 modules below have been created as **stubs** (status: stub) in this run.
Each stub captures known facts from cross-module references; body fills in when PRDs are uploaded.

| Module | Stub Created | Primary Known Facts |
|--------|-------------|---------------------|
| `desk-management` | ✅ 2026-04-30 | Used by parking (WFO entry), delegation, meal-management, implementation |
| `tags-desk-parking` | ✅ 2026-04-30 | Tag engine for meeting-rooms dynamic policy + parking slot access |
| `mobile-app` | ✅ 2026-04-30 | App container; surfaces meeting-rooms, parking, wayfinding, delegation |
| `guard-app-kiosks` | ✅ 2026-04-30 | Guard App for visitor check-in at gate (step 1 of VMS 2-step) |
| `ms-teams-integration` | ✅ 2026-04-30 | Outlook/Google Calendar bidirectional sync for meeting-rooms |
| `access-management` | ✅ 2026-04-30 | RFID/HID badge reader for meal check-in |
| `sso` | ✅ 2026-04-30 | Single Sign-On integration |
| `employee-provisioning` | ✅ 2026-04-30 | Employee onboarding to WIS |
| `admin-experience` | ✅ 2026-04-30 | Admin UI + config surfaces (large Jira footprint) |
| `create-employee-form` | ✅ 2026-04-30 | Employee creation form (part of provisioning flow) |
| `esg-dashboard` | ✅ 2026-04-30 | ESG/sustainability tracking dashboard |
| `safe-reach` | ✅ 2026-04-30 | Safety/emergency declaration workflow |
| `third-party` | ✅ 2026-04-30 | Third-party integrations (non-MS) |

---

## D) Cross-Module Pages Missing for Known Dependencies

Dependencies inferred from existing module `depends_on` frontmatter that had no corresponding
cross-module page before this run:

| Dependency | Direction | Cross-Module Page |
|------------|-----------|-------------------|
| meeting-rooms → ms-teams-integration | Outlook sync | ✅ Created |
| delegation → employee-experience | delegation lives in emp-exp | ✅ Created |
| delegation → meeting-rooms | booking delegation layer | ✅ Created |
| delegation → visitor-management | booking delegation layer | ✅ Created |
| parking-management → mobile-app | parking booking surface in app | ✅ Created |
| parking-management → desk-management | WFO form entry point | ✅ Created |
| digital-wayfinding → mobile-app | wayfinding runs inside app | ✅ Created |
| meal-management → floor-kiosk | kiosk vendor dashboard surface | ✅ Created |
| meal-management → desk-management | WFO integration entry point | ✅ Created |

---

## E) Bidirectionality Violations Fixed

| Module Page | Issue | Fix Applied |
|-------------|-------|-------------|
| `meeting-rooms` | Missing `delegation` in `used_by` | Added |
| `visitor-management` | Missing `delegation` in `used_by` | Added |
| `parking-management` | Missing `visitor-management`, `digital-wayfinding`, `implementation` in `used_by` | Added |
| `floor-kiosk` | Missing `meal-management`, `implementation` in `used_by` | Added |
| `employee-experience` | Already correct | — |
| `meeting-rooms` (depends_on) | `delegation` should be added (delegation.used_by lists meeting-rooms) | ⚠️ Circular — see open-decisions.md |

---

## F) Jira Functional Area Mapping Gaps

| Functional Area | Ticket Count | Pre-fix Status | Resolution |
|----------------|-------------|----------------|------------|
| `WF-empexp` | 16,457 | `employee-experience` ✓ | Already mapped |
| `WF-wis-meeting-vms` | 4,778 | `meeting-rooms`, `visitor-management` ✓ | Already mapped |
| `WF-wis-booking` | 3,512 | `desk-management`, `parking-management` ✓ | Already mapped |
| `WP-workflows` | 4,857 | _unmapped_ | ✅ Mapped in this run |
| `WF-wis-admin` | 3,819 | _unmapped_ | ✅ Mapped in this run |
| `WP-admin` | 3,318 | _unmapped_ | ✅ Mapped in this run |

---

## G) Boundary Ambiguity Notes

| Issue | Status |
|-------|--------|
| `cafeteria` entity — owned by `meeting-rooms` or `meal-management`? | ⚠️ Open — logged in open-decisions.md |
| Delegation circular dependency (depends_on AND used_by meeting-rooms) | ⚠️ Open — logged in open-decisions.md |
| `digital-wayfinding` depends on `floor-kiosk` (floor plan data) but not listed | ⚠️ Open — logged in open-decisions.md |
| `admin-experience` vs `WF-wis-admin` vs `WP-admin` — are these 1 or 2 modules? | ⚠️ Open — logged in open-decisions.md |
| `create-employee-form` — standalone module or part of `employee-provisioning`? | ⚠️ Open — logged in open-decisions.md |
