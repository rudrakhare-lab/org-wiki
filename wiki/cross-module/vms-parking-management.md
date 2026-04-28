---
type: cross-module
modules: [visitor-management, parking-management]
last_updated: 2026-04-28
source: "[[sources/vms-prd]]"
---

# Visitor Management ↔ Parking Management — Visitor Parking Allocation

## Summary
VMS integrates with the Parking module to auto-allocate parking slots for visitors at invite creation.
Visitor parking slots are a separate, tagged pool (the "Visitor" tag) that is invisible to regular
employees. This is an extension of the parking Dynamic Policy tag engine to the VMS use case.

## Modules Involved
- [[modules/visitor-management]] — creates parking requests at invite time; receptionist views/records slot
- [[modules/parking-management]] — owns slot infrastructure; provides auto-allocation

## How They Connect
- Admin tags specific parking slots with `Visitor: Yes` via the Parking Tagging bulk upload
- These slots are **not visible** to employees in the regular WFO booking flow
- When `Visitor_Parking_Auto_Allocation = true`, a "+ Parking" button appears in the invite form
- Host selects Car/Bike for each visitor → VMS calls parking module's auto-allocation at "Confirm Invite"
- If even one slot is unavailable at confirm-time, invite creation fails with toast (slots not held/reserved pre-confirm)
- After confirm, allocated zone/level/slot shown on invite preview and in visitor's digipass email
- Receptionist can see parking slot in guest details drawer and note changes in a text box
- Visitor check-in = parking check-in start time; visitor check-out = parking release

## Data Flow
```
[Admin]
  Tags parking slots as "Visitor" via Parking Tagging bulk upload
              │
              ▼
[VMS Invite Form]  (when Visitor_Parking_Auto_Allocation = true)
  Host selects Car/Bike per visitor
              │
              ▼
[Parking Module - auto-allocation]
  Checks visitor-tagged slot availability at confirm time
  Allocates slot (or rejects with "Parking Slots Unavailable")
              │
              ▼
[VMS Invite confirmed]
  Parking details added to invite + digipass email
              │
              ▼
[Visitor arrives → Receptionist check-in]
  Receptionist sees zone/level/slot; notes any changes
  Visitor check-out triggers parking release
```

## Potential Conflicts
- Parking slot is only checked and allocated at "Confirm Invite" time — no pre-hold. High concurrency invites could result in failures.
- Overstay scenario: visitor stays beyond booking end time; parking buffer applies (from parking module config).
- Visitor parking data does not appear in the standard parking report or Parking Allocation page.

_Source: [[sources/vms-prd]]_
