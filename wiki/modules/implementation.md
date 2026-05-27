---
type: module
status: active
owner: unknown (requires Ujjwal Trivedi sign-off)
depends_on: [desk-management, parking-management, mobile-app, floor-kiosk]
used_by: []
last_updated: 2026-04-28
source: "[[sources/launch-ets-sop]]"
---

# Implementation Module (Client Onboarding SOPs & Guides)

## Overview
The Implementation module is **not a product feature module** — it is a collection of internal
SOPs, reference guides, and operational checklists used by the WorkInSync implementation/SE team
when onboarding new clients or migrating existing MoveInSync (ETS) clients to WorkInSync Workplace.
It owns no product entities. Three artifact types are catalogued here: a **migration SOP**, a
**configuration/support reference guide**, and a **per-client onboarding checklist**.

## Purpose & Scope
Owns: implementation procedures, onboarding checklists, migration runbooks, troubleshooting guides.
Does **not** own any product entities.

## Source Artifacts
Unlike product modules, implementation contains internal SOPs, reference guides, and operational
checklists used by the WorkInSync implementation team — not customer-facing product features.

- **ETS Launch SOP** — [[sources/launch-ets-sop]] (`raw/modules/implementation/SOP for Launching WorkinSync on Live ETS Server.docx`). The 4-phase ETS→WIS migration runbook (Pre-Launch, Launch, Testing, Troubleshooting). Undated; the doc header notes it needs Ujjwal Trivedi sign-off before publishing. Summarized below.
- **Implementation ELC Guide 1.0** — xlsx, 14 sheets (`raw/modules/implementation/Implementation ELC Guide 1.0.xlsx`). An implementation configuration/support reference. Categories listed below.
- **WIS Implementation Checklist** — xlsx, 22 per-client sheets (`raw/modules/implementation/WIS Implementation Checklist.xlsx`). A per-client onboarding tracker. ⚠️ Operational data including client contacts — its per-client contents are **not reproduced** here (see schema below).

## ETS Migration — Key Steps Summary

### Pre-Launch
1. Schedule + communicate downtime; prepare BCP (manual trip sheets)
2. Validate employee data; tag non-transport users
3. Operations Study doc (shifts, features, cut-off times)
4. Upload floor plan + parking plan
5. Desk allocation file
6. Decide check-in mechanism (Digipass / QR / RFID / geofence)
7. WIS configuration finalization
8. Configuration backup via SE ticket
9. **Create test user transport booking (DO NOT SKIP)**

### Launch
1. Create desk + transport shifts via SE ticket
2. Raise SE ticket for config updates
3. Upload floor plan + parking plan via SE request (SVG + JSON)
4. Migrate transport bookings via migration API

### Testing
1. Verify pre-migration bookings on app + work planner with correct OTP
2. Create fresh booking; verify on Work Planner

### Troubleshooting
24 documented scenarios covering: booking visibility, OTP mismatch, floor plan issues, duplicate bookings, app crashes, shift configuration, user permission errors, and more.

## Implementation Configuration Categories
The ELC Guide 1.0 workbook organizes implementation reference material into ~14 category sheets:

- **Admin Property and functions** / **Admin property (New)** — admin-side property configuration
- **ETS Configurations** / **ETS Flow** — transport scheduling, IVR, call-to-employee, driver flow
- **Driver device configuration** — driver app/device setup
- **Employee app configuration** — employee-facing app setup
- **Hardware support** / **Software support** / **Enablers support** — support-topic references
- **THD** — Transport Help Desk
- **Tickets to create** — standard ticket types to raise (ETS and WFO columns: DSARM access requests, SE solution-enabler tickets, with descriptions)
- **training steps** — onboarding training sequence
- **Important links** — internal references (prod wiki, ops study, training modules, support console)
- (plus one unnamed misc sheet)

⚠️ The ELC Guide is heavily **transport-era** (driver app, IVR, THD, commute-oriented configurations). For pure-WorkInSync (non-commute) deployments, only a subset applies. This parallels the SFTP doc flagged in Wave B.2 — content preserved but flagged as legacy-leaning.

## Per-Client Onboarding Checklist
The WIS Implementation Checklist workbook tracks onboarding across **~21 enterprise clients + 1 Test Client** (22 sheets, one per client). Each client sheet follows a common schema (field names only — per-client values are not reproduced here):

- Client name
- Implementation rep
- Number of users
- Decision maker
- POC contact
- Organization workflow (which WIS modules the client adopted — e.g. desk + visitor + meeting-room)
- Key pain areas from the previous system
- Data-migration status (Yes/No)

⚠️ **Privacy boundary:** client identities, decision-maker names, and contact details (emails/phone numbers) are operational/PII data and are deliberately **not reproduced** in the wiki — refer to the source xlsx for the actual per-client data. (Same category-not-literal discipline used for credentials.)

## Dependencies on Other Modules
- [[modules/desk-management]] — desk shifts, floor plan upload, desk allocation
- [[modules/parking-management]] — parking plan upload during onboarding
- [[modules/mobile-app]] — transport booking visibility verification
- [[modules/floor-kiosk]] — floor plan (SVG/JSON) pipeline

_Note: individual client module adoption (VMS, meeting-rooms, etc.) is a per-client operational choice recorded in the checklist, not a structural dependency of the implementation process._

## Data Entities Used
- [[entities/employee]] — employee identity record (identity, entitlements, relationships)

## Open Questions
- The "more comprehensive implementation guide" referenced in April-28 is now catalogued: the **ELC Guide 1.0** and **WIS Implementation Checklist** workbooks (above). Remaining: is there a single canonical, non-ETS-era WIS onboarding guide, or is the ELC Guide (transport-leaning) still the primary reference?
- What are the standard SE ticket templates for WIS onboarding? (Partially covered by the ELC Guide's "Tickets to create" sheet.)

## Last Updated
2026-04-28 — _Source: [[sources/launch-ets-sop]]_

_Source artifacts are living operational files (the two xlsx workbooks are undated); the ETS Launch
SOP is the only formally-tracked source (itself undated, pending Ujjwal Trivedi sign-off). The date
reflects the wiki restore point, not a source revision._
