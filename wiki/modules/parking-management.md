---
type: module
status: active
owner: unknown
depends_on: [tags-desk-parking, mobile-app, desk-management]
used_by: [desk-management]
last_updated: 2026-04-28
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
  - *Auto Allocation*: system picks optimal slot based on assignment priority (Employee > Team > Hotslot)
  - *Grid-based (Manual)*: employee visually selects a slot from the floor plan
- **Dynamic Policy (tags)**: vehicle-type-based access control; reuses tag engine from `tags-desk-parking`. Includes special `BLOCK_HOTSEAT` policy to prevent hotslot booking for specific employees.
- **Waitlist**: IRCTC-style FCFS waitlist per level when all slots are full. Real-time position number shown. Multi-level waitlist joining supported.
- **Vehicle number**: stored per booking (not overwriting profile). Both car + bike registration storable on profile.
- **Default loading**: pre-fills last 30-day booking's zone/level to reduce re-selection friction.
- **Check-in**: QR scan at premise or Digipass on mobile. Premise check-in is chainable (parking check-in can automatically check-in to office, or remain independent — configurable).
- **Buffer times**: `MM` minutes before login time / after logout time for slot availability window.

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
2026-04-28 — _Source: [[sources/parking-prd]], [[sources/dynamic-policy-parking]], [[sources/parking-waitlist]]_
