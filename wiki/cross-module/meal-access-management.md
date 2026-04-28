---
type: cross-module
modules: [meal-management, access-management]
last_updated: 2026-04-28
source: "[[sources/meal-checkin-prd]]"
---

# Meal Management ↔ Access Management — RFID Check-in

## Summary
Meal Management's RFID check-in feature depends on the Access Management module's RFID/HID
access card reader infrastructure to identify employees at the cafeteria. This is the first
documented use case where an access card (traditionally used for building entry) is repurposed
for meal consumption tracking.

## Modules Involved
- [[modules/meal-management]] — consumer of RFID identity signal; manages meal booking + check-in
- [[modules/access-management]] — owns RFID/HID card reader infrastructure and employee card mapping

## How They Connect
```
[Employee]
  Swipes RFID/HID access card at cafeteria RFID reader
              │
              ▼
[Access Management]
  RFID reader reads card → resolves to employee ID
  Transmits employee ID to MoveInSync system
              │
              ▼
[Meal Management]
  Receives employee ID signal
  Looks up meal booking for that employee for today
  Displays booking details on cafeteria tablet
              │
              ▼
[Employee]
  Selects meal from booking → system registers consumption
  OR (if no booking): creates standalone meal booking → checks in
```

## Potential Conflicts
- Not all employees may have physical RFID/HID cards (e.g. remote employees visiting a new office for the first time). Mobile QR fallback remains available.
- RFID reader availability is per-cafeteria — deployment scope needs client coordination.
- Access Management must expose employee identity signal to Meal Management — cross-service API contract not yet documented.

_Source: [[sources/meal-checkin-prd]]_
