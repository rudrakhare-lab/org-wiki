---
type: module
status: active
owner: Aditya Dutta / Ujjwal Trivedi
depends_on: [access-management, floor-kiosk, desk-management, meeting-rooms]
used_by: [access-management]
last_updated: 2025-05-05
source: "[[sources/meal-checkin-prd]]"
---

# Meal Management Module

## Overview
Meal Management handles employee meal booking and consumption tracking at office cafeterias.
Currently documented only via the "Meal Check-in via Access Card" PRD (May 2025) —
a feature that adds RFID/HID card-based check-in as an alternative to QR scan on mobile.
The core meal booking feature (as part of WFO/office booking) pre-dates this doc and is
assumed to be operational; detailed PRD for it is not yet ingested.

## Purpose & Scope
Owns: meal bookings (standalone + WFO-integrated), RFID check-in flow, vendor/admin dashboard
for cafeteria orders. Shares the `Cafeteria` entity with Meeting Rooms catering.

Does **not** own: the cafeteria entity (⚠️ ownership contested with `meeting-rooms`), the RFID
reader/access card infrastructure (owned by `access-management`), or the kiosk tablet hardware
(owned by `floor-kiosk`).

## Key Features
- **WFO-integrated meal booking**: employee adds meal to their office/WFO booking (pre-existing feature)
- **Standalone meal booking** (new in v1.0): bookable independently via mobile app or web — implemented as a new entity (the PRD notes it is created "just like the New Room Type"); also creatable at the cafeteria via RFID swipe
- **RFID/HID access card check-in** (new in v1.0): swipe at cafeteria → tablet (Android/iOS) shows booking → select meal → register consumption. Replaces mobile QR for phone-averse employees. The tablet screen shows: Office & Cafeteria; meal selection (single meal shown directly, multiple meals listed for choice); meal category & item(s); description (if set); and price (if set)
- **On-the-spot booking via RFID**: employees without a booking can swipe → create booking at kiosk → check in immediately
- **Vendor/admin dashboard**: shows employee details after swipe (reuses existing Vendor Dashboard) — lets the vendor verify the swiped user's details when they cannot see the user-facing tablet screen

## Constraint — One Meal Per Day
Only one active meal booking per employee per day. WFO booking with meals and standalone meal booking are mutually exclusive.

## Data Entities Used
- [[entities/meal-booking]] — owns this entity
- [[entities/cafeteria]] — ⚠️ shared with `meeting-rooms` — ownership TBD once core meal PRD is ingested
- [[entities/employee]] — employee identity record (identity, entitlements, relationships)

## Dependencies on Other Modules
- [[modules/access-management]] — RFID/HID access card reader infrastructure for meal check-in
- [[modules/floor-kiosk]] — tablet device at cafeteria (Android/iOS kiosk showing booking details)
- [[modules/desk-management]] — WFO booking is the parent of integrated meal bookings

## Used By
- [[modules/desk-management]] — WFO booking can include a meal add-on
- [[modules/meeting-rooms]] — shares [[entities/cafeteria]] for meeting catering

## Open Questions
- Core meal booking PRD not yet ingested — what is the full feature set beyond RFID check-in?
- Who owns `Cafeteria` — meal-management or meeting-rooms? ⚠️ (recurring open question)
- Is the Vendor Dashboard a separate module or part of meal-management?

## Last Updated
2025-05-05 — _Source: [[sources/meal-checkin-prd]]_
