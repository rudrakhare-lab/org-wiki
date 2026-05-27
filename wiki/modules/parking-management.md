---
type: module
status: active
owner: unknown
depends_on: [tags-desk-parking, mobile-app, desk-management]
used_by: [desk-management]
last_updated: 2025-10-22
source: "[[sources/parking-prd]], [[sources/dynamic-policy-parking]], [[sources/parking-waitlist]]"
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

## Open Questions
- Who is the module owner team?
- What is the exact property name for the parking cut-off time config? (PRD says "Property name →" but leaves it blank.)
- Is parking check-in auto-release configured separately from meeting room auto-release, or shared?
- Does the waitlist mechanism auto-assign slot or notify employee to book?

## Last Updated
2025-10-22 — _Source: [[sources/parking-prd]], [[sources/dynamic-policy-parking]], [[sources/parking-waitlist]]_
