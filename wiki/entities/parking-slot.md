---
type: entity
owned_by: parking-management
used_by: [parking-management, tags-desk-parking]
last_updated: 2026-04-28
source: "[[sources/parking-prd]], [[sources/dynamic-policy-parking]]"
---

# ParkingSlot

## Description
A single bookable parking space within the WIS parking premise hierarchy.
Each slot belongs to a Zone (parking facility) → Level (floor) → Slot. Slots are typed by
vehicle category (car / bike) and have an assignment type controlling who can book them.

## Fields
| Field | Type | Description | Required |
|-------|------|-------------|----------|
| id | UUID | Unique slot identifier | Yes |
| slot_name | string | Human-readable slot name/number (e.g. "P1-100") | Yes |
| zone_id | UUID | FK → ParkingZone (facility within an office) | Yes |
| level_id | UUID | FK → ParkingLevel (floor within zone) | Yes |
| vehicle_type | enum | `CAR`, `BIKE` | Yes |
| assignment_type | enum | `HOTSLOT`, `EMPLOYEE`, `TEAM`, `BLOCKED`, `UNALLOCATED` | Yes |
| assigned_to | UUID | FK → Employee or Team (only when assignment_type = EMPLOYEE or TEAM) | No |
| tags | ParkingTag[] | Dynamic policy tags (e.g. vehicle build type: Sedan, SUV) | No |
| qr_code | string | QR code identifier for check-in at this level | No |

## Assignment Type Behaviour
| Type | Who Can Book |
|------|-------------|
| HOTSLOT | Any employee (open pool) |
| EMPLOYEE | Only the specifically assigned employee |
| TEAM | Only members of the assigned team |
| BLOCKED | No one |
| UNALLOCATED | No one (not yet assigned) |

## Used By
- [[modules/parking-management]] — owns and books slots
- [[modules/tags-desk-parking]] — provides tag engine for dynamic policy on slots

## Relationships to Other Entities
- [[entities/parking-booking]] — each booking claims one ParkingSlot
- [[entities/room-tag]] — ParkingTag follows the same schema as RoomTag (owned by tags-desk-parking)

## Source of Truth
[[modules/parking-management]] owns the ParkingSlot entity.

_Source: [[sources/parking-prd]], [[sources/dynamic-policy-parking]]_
