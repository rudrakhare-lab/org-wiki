# Open Decisions
_Decisions that require human input before they can be resolved in the wiki._
_Append only. Do not modify existing entries._

---

## OD-1 — Cafeteria entity ownership: meeting-rooms vs. meal-management
**Opened:** 2026-04-30
**Affects:** `wiki/entities/cafeteria.md`, `wiki/modules/meeting-rooms.md`, `wiki/modules/meal-management.md`

**Context:**
The `Cafeteria` entity was first introduced in the Meeting Rooms Catering PRD (cafeteria configurations for catering orders during room bookings). When meal-management was ingested, it also uses `Cafeteria` as a central entity (RFID-based meal check-in tied to a cafeteria).

**The question:**
Who owns the `Cafeteria` entity — meeting-rooms (introduced it for catering) or meal-management (core to its feature)?

**Options:**
A. `meeting-rooms` owns it — meal-management consumes it (requires adding meeting-rooms to meal-management.depends_on)
B. `meal-management` owns it — meeting-rooms consumes it for catering (requires adding meal-management to meeting-rooms.depends_on)1₹
C. A shared `cafeteria-management` entity owned by neither (new module/entity)
D. Split into `catering-cafeteria` (meeting-rooms) and `meal-cafeteria` (meal-management) — separate entities

**Recommendation:** Option B (meal-management owns it) is most architecturally clean — cafeteria operations are meal-management's core business; meeting rooms catering is an integration. But this needs confirmation from the product/engineering team.

**Decision (Resolved):** **B**
**Resolved on:** 2026-05-05
**Resolution note:** Cafeteria ownership is assigned to `meal-management`. `meeting-rooms` consumes the cafeteria entity for catering workflows.

---

## OD-2 — Delegation circular dependency with booking modules
**Opened:** 2026-04-30
**Affects:** `wiki/modules/delegation.md`, `wiki/modules/meeting-rooms.md`, `wiki/modules/visitor-management.md`, `wiki/modules/desk-management.md`

**Context:**
`delegation.depends_on` includes `[meeting-rooms, visitor-management, desk-management]` because delegation has specific integration logic for those modules (e.g., delegatee excluded from meeting invite; audit records show delegatee's name).

`delegation.used_by` also includes the same three modules because those modules call delegation to resolve the effective user context during a booking.

This creates a circular dependency in both directions — architecturally unusual.

**The question:**
Which direction is the correct code-level dependency?

**Options:**
A. Booking modules (meeting-rooms etc.) depend on delegation — they call delegation to check for active delegation context. `delegation.depends_on` should be empty for these three; `delegation.used_by` should include them.
B. Delegation depends on booking modules — delegation has module-specific logic (invite handling, audit). `delegation.depends_on` keeps the three; `booking.used_by` drops delegation.
C. True circular — acceptable in a distributed microservices architecture (event-based). Document explicitly.

**Recommendation:** Option A is architecturally cleanest. Delegation is a cross-cutting concern; booking modules query it, not the other way around. Delegation's module-specific logic (e.g., meeting room invite handling) should be modeled as configuration/callback, not a hard dependency.

**Decision (Resolved):** **A**
**Resolved on:** 2026-05-05
**Resolution note:** Booking modules depend on delegation context; delegation does not hard-depend on meeting/visitor/desk booking modules.

---

## OD-3 — digital-wayfinding dependency on floor-kiosk and employee-experience
**Opened:** 2026-04-30
**Affects:** `wiki/modules/digital-wayfinding.md`, `wiki/modules/floor-kiosk.md`, `wiki/modules/employee-experience.md`

**Context:**
1. `digital-wayfinding` renders floor plans produced by floor-kiosk's DIY Floor Planner pipeline. The `floor-plan-sop` source was ingested for both modules. However, `digital-wayfinding.depends_on` does not include `floor-kiosk`.
2. `employee-experience.used_by` includes `digital-wayfinding` (both live in the emp-exp service), but `digital-wayfinding.depends_on` does not include `employee-experience`.

**The question:**
Should `floor-kiosk` and `employee-experience` be listed in `digital-wayfinding.depends_on`?

**Options:**
A. Yes to both — floor plan data and emp-exp hosting are real dependencies
B. Yes to employee-experience only — hosting is a dependency; floor plan data is just a data feed
C. Neither — floor plan data is a data-at-rest dependency (not a service call), not a module dependency; digital-wayfinding is a sub-feature of emp-exp (not a separate dependent)

**Recommendation:** Confirm the service architecture — does digital-wayfinding call floor-kiosk's API at runtime, or does it load pre-built floor plan JSON/SVG files? If the former, add floor-kiosk as dependency. If latter, it's a deployment-time dependency, which should be documented in the cross-module page but not modeled as a runtime depends_on.

**Decision (Resolved):** **B**
**Resolved on:** 2026-05-05
**Resolution note:** Add `employee-experience` as a dependency. Keep `floor-kiosk` as a data/pipeline reference documented in cross-module pages, not a runtime hard dependency.

---

## OD-4 — create-employee-form: standalone module vs. sub-feature of employee-provisioning
**Opened:** 2026-04-30
**Affects:** `wiki/modules/create-employee-form.md`, `wiki/modules/employee-provisioning.md`

**Context:**
`create-employee-form` exists as a separate folder in `raw/modules/`, suggesting the team treats it as a distinct entity. However, it's also plausible that it's simply the admin UI for employee provisioning, not a separate service.

**The question:**
Is `create-employee-form` a standalone module (separate service/surface) or a sub-feature of `employee-provisioning`?

**Options:**
A. Standalone module — keep as separate wiki page
B. Sub-feature of employee-provisioning — merge into employee-provisioning wiki page; delete create-employee-form stub
C. Sub-feature of admin-experience — the form is an admin UI concern, employee-provisioning owns the backend

**Recommendation:** Confirm with the team. If no PRD/spec exists for create-employee-form independently, lean toward merging into employee-provisioning.

**Decision (Resolved):** **C**
**Resolved on:** 2026-05-05
**Resolution note:** `create-employee-form` is a sub-feature of `admin-experience` (admin UI concern). `employee-provisioning` remains a separate creation/provisioning path.

---

## OD-5 — admin-experience: one module or two (WP-admin vs. WF-wis-admin)?
**Opened:** 2026-04-30
**Affects:** `wiki/modules/admin-experience.md`, `config/functional_area_to_module.toml`

**Context:**
Two Jira functional areas both map to `admin-experience`:
- `WP-admin` — 3,318 tickets (product backlog admin tickets)
- `WF-wis-admin` — 3,819 tickets (WIS admin-side workflow/config tickets)

Together ~7,137 tickets.

**The question:**
Are WP-admin and WF-wis-admin the same admin surface, or are they two distinct admin contexts (e.g., admin web portal vs. admin configuration API)?

**Options:**
A. Same surface — one `admin-experience` module covers both Jira areas
B. Two surfaces — WP-admin = admin portal, WF-wis-admin = admin API/config layer (needs second module slug)

**Recommendation:** Review 10–15 representative tickets from each area to check if they describe the same product surface. If ticket types overlap heavily, Option A. If WF-wis-admin tickets are all API/config-level, consider a separate `admin-config` module.

**Decision (Resolved):** **A**
**Resolved on:** 2026-05-05
**Resolution note:** Keep one `admin-experience` module for both `WP-admin` and `WF-wis-admin`.

---

## OD-6 — transport/shuttle as unrepresented module
**Opened:** 2026-04-30
**Affects:** `wiki/overview.md`, `config/functional_area_to_module.toml`

**Context:**
~7 WP-workflows tickets (in the 100-ticket sample) cover transport/shuttle visibility for shifts, transport booking UI, and shift filtering. At 13% ticket share for WP-workflows across 36,741 tickets, the absolute count may be significant.

**The question:**
Does WorkInSync have a transport/shuttle management module? If so, does a PRD exist?

**Action required:**
- Confirm with product/engineering whether a transport module exists
- If yes: upload PRD to `raw/modules/transport/` and ingest
- If no: confirm it's a legacy/deprecated feature and note in overview.md

**Rule:** Do NOT create a module page from ticket evidence alone (CLAUDE.md §10 Rule 6). This decision unblocks that.

**Decision (Resolved):** **Yes — transport module approved without PRD**
**Resolved on:** 2026-05-05
**Resolution note:** Product decision is to treat the ~7 tickets as sufficient evidence. Create/maintain `transport` as a module node even before PRD upload.

---

## OD-7 — PMS runtime config precedence and API semantics
**Opened:** 2026-05-13
**Affects:** `docs/pms-runtime-api-playbook.md`, `docs/pms-config-evaluation-workflow.md`, `config/pms_service_scope_matrix.toml`

**Context:**
The PMS dashboard exposes runtime config values through
`POST /propmanagement/api/<SERVICE_ID>/properties/v2` using criteria bodies such
as `{"BUID": "..."}` and `{"BUID": "...", "OFFICEID": "..."}`. Property
metadata from `default-properties/details` includes `criteriaPriorityList`, but
the exact precedence semantics are not yet confirmed.

**The questions:**
1. In `criteriaPriorityList`, does priority `1` mean highest precedence or
   lowest precedence?
2. Does `properties/v2` return only explicitly configured values for the
   requested criteria body, or does it return an already-resolved/effective
   merged value?
3. How should absence of a property in an office/room/role response be
   interpreted: inherit parent, not customizable at that level, or missing data?
4. What are the office-directory and room-directory APIs for mapping names to
   `OFFICEID` and `ROOMID`?
5. What is the save/update API and request body for changing a property value?

**Recommendation:**
Confirm these with PMS engineering before implementing automatic
change-level recommendations. Until then, the resolver should report raw BUID
and lower-level values side by side and avoid claiming final precedence.
