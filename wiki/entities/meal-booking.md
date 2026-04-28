---
type: entity
owned_by: meal-management
used_by: [meal-management, desk-management]
last_updated: 2026-04-28
source: "[[sources/meal-checkin-prd]]"
---

# MealBooking

## Description
A reservation for a meal at a cafeteria. Exists in two forms:
1. **WFO-integrated**: created as part of an office/WFO booking (already existing behavior)
2. **Standalone** (new — PRD v1.0): created independently via mobile app or web, or created at the cafeteria using an RFID access card swipe

**Constraint**: Only one active meal booking per employee per day — if WFO booking includes meal, standalone is blocked; if standalone exists, WFO booking cannot add meals.

## Fields
| Field | Type | Description | Required |
|-------|------|-------------|----------|
| id | UUID | Unique meal booking ID | Yes |
| employee_id | UUID | FK → Employee | Yes |
| cafeteria_id | UUID | FK → [[entities/cafeteria]] | Yes |
| booking_date | date | Date of the meal | Yes |
| meal_type | string | Category/type of meal (as defined in cafeteria menu) | Yes |
| items | MealItem[] | Selected meal items | Yes |
| booking_source | enum | `WFO_BOOKING`, `STANDALONE_WEB`, `STANDALONE_APP`, `RFID_KIOSK` | Yes |
| check_in_status | enum | `NOT_CHECKED_IN`, `CHECKED_IN` | Yes |
| check_in_method | enum | `QR_SCAN`, `RFID_CARD`, `MANUAL` | No |
| checked_in_at | timestamp | Timestamp of meal check-in (UTC) | No |
| wfo_booking_id | UUID | FK → WFO booking (only when booking_source = WFO_BOOKING) | No |

## Used By
- [[modules/meal-management]] — owns and manages meal bookings
- [[modules/desk-management]] — WFO booking can include a meal (integrated booking path)

## Relationships to Other Entities
- [[entities/cafeteria]] — each MealBooking is at a specific Cafeteria

## Source of Truth
[[modules/meal-management]] owns the MealBooking entity.

_Source: [[sources/meal-checkin-prd]]_
