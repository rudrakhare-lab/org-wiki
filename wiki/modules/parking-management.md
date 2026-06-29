---
type: module
status: active
owner: unknown
depends_on: [tags-desk-parking, mobile-app, desk-management]
used_by: [access-management, digital-wayfinding, implementation, visitor-management]
last_updated: 2025-10-22
source: "[[sources/parking-prd]], [[sources/dynamic-policy-parking]], [[sources/parking-waitlist]], [[sources/se-runbook-parking]]"
---

# Parking Management Module

## Overview
Parking Management allows organizations to digitize and manage employee parking allocation.
Employees book parking as part of their WFO (Work From Office) booking — parking is an add-on
to the desk/office day booking, not a standalone flow. Parking slots are organized in a
hierarchical premise structure (Office → Zone → Level → Slot) and access is controlled via
assignment types and dynamic policy tags (same tag engine as desks and meeting rooms).

## Purpose & Scope
Owns the full lifecycle of parking slot reservations: premise configuration, slot assignment
(dedicated/team/hotslot), booking, check-in, auto-release, waitlist, and dynamic policy.
Also owns the parking-specific vehicle number management.

Does **not** own: the tag engine (owned by `tags-desk-parking`), the mobile app container
(owned by `mobile-app`), or the WFO booking form entry point (owned by `desk-management`).

## Key Features
- **WFO-integrated booking**: parking is added via the WFO/desk booking form (web and app). Not bookable independently.
- **Premise hierarchy**: Office → Zone (parking facility) → Level (floor) → Slot (car/bike)
- **Slot assignment types**: Hotslot (open to all), Employee (dedicated), Team, Blocked, Unallocated
- **Two booking modes**:
  - *Auto Allocation*: system picks optimal slot based on assignment priority (Employee > Team > Hotslot); slots are allocated **sequentially** within the chosen category
  - *Grid-based (Manual)*: employee visually selects a slot from the floor plan
- **Dynamic Policy (tags)**: tag-based access control reusing the **general-purpose** tag engine from `tags-desk-parking`. Most commonly vehicle-build policies, but tags are general (e.g. PWD-only slots, `WeekendOnly` slots). Includes the special `BLOCK_HOTSEAT` policy. See the **Dynamic Policy (Parking)** section below for mechanics.
- **Waitlist**: IRCTC-style FCFS waitlist per level when all slots are full. Real-time position number shown. Multi-level waitlist joining supported; a waitlisted employee can still book any open slot on a different level if one frees up.
- **Vehicle number**: stored per booking (not overwriting profile). Both car + bike registration storable on profile.
- **Default loading**: pre-fills last 30-day booking's zone/level to reduce re-selection friction.
- **Check-in**: QR scan at premise or Digipass on mobile. Premise check-in is chainable (parking check-in can automatically check-in to office, or remain independent — configurable).
- **Buffer times**: `MM` minutes before login time / after logout time for slot availability window.

## Dynamic Policy (Parking)
Dynamic policies restrict which employees can book which slots, most commonly by **vehicle build**.
_Source: Dynamic Policy for Parking v1.3 (2025-10-22)._

- **Dual mapping**: a policy must be assigned to **both** the employee **and** the parking slot/resource. The system matches the two — a slot is bookable by an employee only when the same policy value matches on both sides (e.g. employee `User A = Sedan` + slot `L1-S69 = Sedan` → User A can book that slot).
- **Vehicle-build policies available**: `Crossover/SUV/MUV`, `Sedan`, `Small/Hatchback`, `Micro/Hatchback`.
- **Value semantics** (in the bulk-upload tagging files):
  - `Yes` — assign the policy (pattern match; the slot becomes bookable by matching employees)
  - `Null/null` — remove the policy from that employee/slot
  - *Blank* — ignore the entry (existing policy left unmodified)
- **`BLOCK_HOTSEAT`**: blocks an employee from booking **hotslots only**. A user who has a matching policy (e.g. `Sedan` on both their profile and a `Sedan` slot) can still book that policy-matched slot — `BLOCK_HOTSEAT` does not block policy-assigned slots, only open hotslots.
- Configured via bulk upload: Sidenav → Desk Allocation → Desk Bulk Upload → **Employee Tagging** and **Parking Tagging** (see Admin Operations).

## Data Entities Used
- [[entities/parking-slot]] — owns this entity
- [[entities/parking-booking]] — owns this entity
- [[entities/employee]] — employee identity record (identity, entitlements, relationships)

## Dependencies on Other Modules
- [[modules/tags-desk-parking]] — tag engine for dynamic policy (vehicle-type-based slot access, BLOCK_HOTSEAT); same engine as desks and meeting rooms
- [[modules/mobile-app]] — booking card, Digipass check-in, QR scan check-in surface
- [[modules/desk-management]] — WFO booking form is the entry point; parking booking is an add-on to the WFO/desk booking record

## Used By
- [[modules/desk-management]] — WFO booking parent record contains parking booking reference

## Key Configurations
| Config Key | Type | Description |
|---|---|---|
| parking buffer before login | integer (min) | Slot availability window opens MM min before selected login time |
| parking buffer after logout | integer (min) | Slot availability window closes MM min after logout time |
| cut-off time | integer (min) | Same as desk booking cut-off — prevents last-minute parking booking |
| vehicle number PII | boolean | Whether to collect/store vehicle registration number (org-configurable) |
| check-in premise chaining | config | Whether parking check-in auto-triggers office check-in (and vice versa) |

## Admin Operations
- Bulk upload: **Employee Tagging** (vehicle-type policies on employees) + **Parking Tagging** (policies on slots) — done via Desk Allocation → Desk Bulk Upload.
- Grid plan: admin slot allocation page showing summary (Hotslot/Team/Employee/Blocked counts per zone/level) with date/office/zone/level/vehicle filters.
- New parking slots require email to MoveInSync team for backend addition — **not self-serve**.

### Backend premise setup (SE-only)
Parking *premises* (distinct from the slot/grid admin above) are created at the backend by the SE team. Full procedure: [[runbooks/parking-premise-setup]].
- Requires a **TO ticket** to enable Parking per site first, plus an existing **office premise** (the parking premise's `parentPremise` = the office `premiseId`).
- SE/backend endpoints used:
  - `GET https://mis-security.moveinsync.com/mis-security-guard/premise/buid/<BUID>` — list premises (incl. parking)
  - `GET https://mis-security.moveinsync.com/mis-security-guard/premise-capcity/buid/<BUID>?startTime=<ms>&endTime=<ms>` — capacity records (note source's literal `premise-capcity` spelling)
- Parking `premiseType` codes (read from the runbook example — ⚠️ confirm as the standard convention): `6` = 2-wheeler, `3` = 4-wheeler.
- _Source: [[sources/se-runbook-ets-office-premise]]_

### Vehicle sub-type setup (SE-only)
When clients require slot differentiation beyond CAR/BIKE (e.g. Sedan, SUV, Hatchback),
vehicle sub-types must be created via the `mis-floor-plan` API and mapped to the client BUID.
Full procedure: [[runbooks/parking-tag-and-vehicle-setup]].

- `GET /mis-floor-plan/seat/seat-types?entityType=PARKING&buid=<BUID>` — list existing sub-types
- `POST /mis-floor-plan/seat/seat-types?entityType=PARKING` — create new sub-types (pass string array)
- `POST /mis-floor-plan/seat/sub-types?buid=<BUID>` — map sub-type IDs to BUID
- ⚠️ Duplicate `seatTypeName` values break floor plan creation in the CAD viewer — always check for existing sub-types first.
- For BIKE slots in non-DIY floor plan files: use `SubType: -1` (fixed sentinel).
- _Source: [[sources/se-runbook-parking]]_

### Tag creation for dynamic policies (SE-only)
Tags for dynamic policy (vehicle-build or category restrictions) are created via the
`mis-floor-plan` API. SE raises an SE ticket to create tags; admin then uploads the tagging files.
Full procedure: [[runbooks/parking-dynamic-policy]].

- `POST /mis-floor-plan/api/<BUID>/tags` — create tags (entityType, tagName, tagType)
- `POST /mis-floor-plan/api/<BUID>/tags/polygons` — map tag values (Yes/No) to each tag's `buTagId`
- `GET /mis-floor-plan/api/<BUID>/tags?entityType=PARKING` — verify tags created
- _Source: [[sources/se-runbook-parking]]_

### QR code generation (SE-only)
Physical QR codes are printed and affixed to parking slots for the "Scan QR" check-in mode.
Generated via: `GET https://mis-security.moveinsync.com/mis-security-guard/seat/generate-qr-seat-bulk`

- `entityType=LEVEL` + `floorPremiseId=<level-premise-id>` — bulk QR for all slots on a level
- `entityType=PARKING` + `floorPremiseId=<slot-premise-id>` — QR for individual slots
- Requires `x-wis-token: <token>` and `x-tenant-id: <tenant-id>`.
- Full procedure: [[runbooks/parking-tag-and-vehicle-setup]].
- _Source: [[sources/se-runbook-parking]]_

### Third-party hardware integration (Parking Checkin API)
When clients use boom barriers or access card systems, WorkInSync provides a check-in integration
API. The vendor's system polls WIS to confirm booking existence and then performs check-in.

- **Auth**: `POST {baseUrl}/auth/token` with Basic auth → returns Bearer token (expires in ~48h)
- **GetParkingBookingDetails**: confirms whether an employee has a booking; keyed on `EmployeeNumber` + `Date` + `DetectorID` (maps to office/zone/level)
- **ParkingCheckIn**: performs check-in; can create a new booking on-the-fly if no prior booking exists (via `EndTime` parameter)
- _Source: [[sources/se-runbook-parking]] — "WorkInSync Parking Checkin Integration" v1.1 (2022-06-07)_

## Related Runbooks

| Runbook | Scope |
|---------|-------|
| [[runbooks/parking-premise-setup]] | SE: create parking premise (2WH/4WH), validate, add capacity |
| [[runbooks/parking-dynamic-policy]] | SE + Admin: configure tag-based slot access policies; vehicle-build restrictions; BLOCK_HOTSEAT |
| [[runbooks/parking-tag-and-vehicle-setup]] | SE: create vehicle sub-types, map to BUID, generate and download slot QR codes |

## Open Questions
- Setup-time dependency on **ETS**: the parking premise is built under the office premise (created via [[runbooks/ets-office-premise-setup]] / [[modules/ets]]). Is this a `depends_on` (runtime) or a separate setup-time relationship? (Schema decision — affects desk/guard/parking/meal uniformly.)
- Who is the module owner team?
- What is the exact property name for the parking cut-off time config? (PRD says "Property name →" but leaves it blank.)
- Is parking check-in auto-release configured separately from meeting room auto-release, or shared?
- Does the waitlist mechanism auto-assign slot or notify employee to book?

## Last Updated
2026-06-29 — _Sources: [[sources/parking-prd]], [[sources/dynamic-policy-parking]], [[sources/parking-waitlist]], [[sources/se-runbook-ets-office-premise]] (SE backend premise setup), [[sources/se-runbook-parking]] (SE vehicle sub-type, tag creation, QR, integration API)_
