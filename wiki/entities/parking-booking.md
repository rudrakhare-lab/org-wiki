---
type: entity
owned_by: parking-management
used_by: [parking-management, mobile-app, desk-management]
last_updated: 2026-04-28
source: "[[sources/parking-prd]], [[sources/parking-waitlist]]"
---

# ParkingBooking

## Description
A reservation of a parking slot by an employee, created as part of the WFO (Work From Office)
booking flow. Parking is an add-on to a desk/WFO booking — not a standalone booking.
Includes check-in state, vehicle details, and optional waitlist position.

## Fields
| Field | Type | Description | Required |
|-------|------|-------------|----------|
| id | UUID | Unique booking identifier | Yes |
| employee_id | UUID | FK → Employee | Yes |
| wfo_booking_id | UUID | FK → WFO/Desk booking (parent booking) | Yes |
| slot_id | UUID | FK → [[entities/parking-slot]] | Yes |
| booking_date | date | Date of the parking booking | Yes |
| vehicle_type | enum | `CAR`, `BIKE` | Yes |
| vehicle_number | string | Registration number (stored per booking, not overwriting profile) | No |
| check_in_status | enum | `NOT_CHECKED_IN`, `CHECKED_IN`, `NO_SHOW` | Yes |
| checked_in_at | timestamp | Timestamp of check-in (UTC) | No |
| is_released | boolean | Whether slot was auto-released (no check-in) | No |
| waitlist_position | integer | Current position in waitlist (null if slot confirmed) | No |
| waitlist_level_ids | UUID[] | Level IDs this employee is waitlisted for | No |

## Used By
- [[modules/parking-management]] — owns lifecycle
- [[modules/mobile-app]] — booking card shows parking details; Digipass/QR check-in
- [[modules/desk-management]] — WFO booking form is the entry point for parking booking

## Relationships to Other Entities
- [[entities/parking-slot]] — each booking occupies one slot (or is waitlisted)

## Source of Truth
[[modules/parking-management]] owns the ParkingBooking entity.

_Source: [[sources/parking-prd]], [[sources/parking-waitlist]]_
