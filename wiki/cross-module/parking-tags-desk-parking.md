---
type: cross-module
modules: [parking-management, tags-desk-parking]
last_updated: 2026-04-28
source: "[[sources/dynamic-policy-parking]], [[sources/parking-prd]]"
---

# Parking Management ↔ Tags & Desk/Parking — Dynamic Policy Engine

## Summary
Parking Management reuses the same tag engine owned by `tags-desk-parking` (also used by
Meeting Rooms) for vehicle-type-based slot access control. This is the third confirmed consumer
of the tag engine — establishing it as a true platform-level shared service across all
resource-booking modules.

## Modules Involved
- [[modules/parking-management]] — consumer of tag engine for parking slot access control
- [[modules/tags-desk-parking]] — owner of the tag creation/management/evaluation engine

## How They Connect
Two bulk-upload files govern the tag assignments:
1. **Employee Tagging** — assigns vehicle-type policies to employee profiles
2. **Parking Tagging** — assigns vehicle-type policies to parking slots

At booking time, the system matches:
```
if EmployeeTag.type == SlotTag.type AND EmployeeTag.value == SlotTag.value
  → slot is bookable by this employee
else
  → slot is grayed out / unavailable
```

Special policy: `BLOCK_HOTSEAT` — when applied to an employee, prevents them from booking
any hotslot, forcing them to only their tagged/dedicated slots.

## Tag Value Semantics
| Upload Value | Meaning |
|---|---|
| `Yes` (or any value) | Grant policy / make match active |
| `Null` / `null` | Remove policy from employee or slot |
| *(blank)* | No change to existing policy |

## Comparison with Other Tag Consumers
| Module | Tag Consumer For | Notes |
|--------|-----------------|-------|
| [[modules/meeting-rooms]] | Room access (Dynamic Policy) | Applies to native rooms only |
| [[modules/parking-management]] | Slot access (vehicle type, BLOCK_HOTSEAT) | Applied at slot level |
| [[modules/desk-management]] | Desk access | TBD — to be confirmed on ingest |

## Potential Conflicts
- Bulk upload path is under **Desk Allocation → Desk Bulk Upload** — despite being about parking. Could confuse admins.
- New slots require MoveInSync team backend intervention — creates a support bottleneck for customers self-managing parking.
- No documented rollback beyond the null-upload pattern (edge case: corrupted start dates).

_Source: [[sources/dynamic-policy-parking]], [[sources/parking-prd]]_
