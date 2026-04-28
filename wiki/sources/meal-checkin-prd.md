---
type: source
raw_path: raw/modules/meal-management/Copy of Meal Check-in via Access Card PRD .docx
ingested: 2026-04-28
doc_type: PRD
---

# Meal Check-in via Access Card PRD

## Source Title
Meal Check-in via Access Card PRD (v1.0)

## Date
05/05/2025

## Type
PRD

## Key Takeaways
- Adds **RFID/HID access card-based check-in** for meals — alternative to mobile QR scan for employees who don't use personal phones at work.
- **Flow (user with booking)**: User swipes access card at RFID reader at cafeteria → tablet (Android/iOS) shows meal booking details (cafeteria, meal options, category/items, description, price) → user selects meal → system registers consumption → vendor provides meal.
- **Flow (user without booking)**: Swipe still reads user data → tablet shows user details → user can create a **standalone meal booking** directly at the cafeteria → then checks in to meal.
- **Standalone meal booking**: a new entity (like a new Room Type) bookable via mobile app + web, independent of WFO office booking. **Constraint**: only one active meal booking type per day — if WFO booking has meals, standalone not allowed; if standalone exists, WFO booking cannot include meals.
- **Admin/Vendor view**: dashboard (reuses Vendor Dashboard) shows details of user who just swiped — necessary as admin/vendor often can't see the employee-facing tablet screen.
- **Acceptance Criteria**: marked as TODO in doc — feature was in active development at time of writing.

## Entities Mentioned
- [[entities/meal-booking]]

## Modules Mentioned
- [[modules/meal-management]] (primary)
- [[modules/access-management]] (RFID/HID access card infrastructure)
- [[modules/desk-management]] (WFO booking — meal is currently an add-on to WFO)
- [[modules/floor-kiosk]] (tablet device used at cafeteria)

## Decisions Extracted
- [[decisions/2026-04-28-standalone-meal-booking-constraint]]

## Wiki Pages Created/Updated
- Created: [[modules/meal-management]]
- Created: [[entities/meal-booking]]
- Created: [[cross-module/meal-access-management]]

_Source: [[sources/meal-checkin-prd]]_
