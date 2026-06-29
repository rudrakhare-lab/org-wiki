---
type: module
status: active
owner: Aditya Dutta / Ujjwal Trivedi
depends_on: [access-management, floor-kiosk, desk-management, meeting-rooms, ets]
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
- [[modules/ets]] — _(setup-time)_ the ETS-issued office premise is the parent entity under which the cafeteria/meal-booking premise is created

## Used By
- [[modules/desk-management]] — WFO booking can include a meal add-on
- [[modules/meeting-rooms]] — shares [[entities/cafeteria]] for meeting catering

## SE Setup Workflow

A new cafeteria requires the following steps (see [[runbooks/meal-booking]] for full details):

1. Create cafeteria premise via `POST /mis-security-guard/premise` with `premiseType: "8"` — returns the `cafeteria-premiseId` UUID.
2. Map the cafeteria to an existing office/floor premise via the premise-mapping API.
3. Set meal types and option codes per-BUID in Consul: `employee-exp → <buid> → meal`.
4. Enable meal planning in Consul common node: `employee-exp → common → mealPlanningEnabled: true`.
5. Create counters within the cafeteria: `POST /mis-security-guard/premise/<cafeteria-premiseId>/meal/create-counter`.
6. Upload the counter-to-meal mapping file: `POST /meal-booking-app/<tenantId>/bulk-upload/counter-details` (multipart CSV/XLSX).
7. Generate QR codes for counters: `GET /meal-booking-app/<tenantId>/meal/generate-qr-meal?premiseId=<cafeteria-premiseId>`.

Two separate services are involved: `mis-security-guard` (cafeteria/counter management) and `meal-booking-app` (counter mapping and QR).

_Source: [[sources/se-runbook-meal-booking]]_

## Key Config Properties

The following PMS config properties govern meal behaviour. For full details and dual-server comparison, see [[configs/booking-rule-engine]] and [[configs/emp-experience-common]].

| Property | Service | Default | Notes |
|----------|---------|---------|-------|
| `allowedMealBookingPerEmployee` | BRE | 1 | Max meal bookings per employee per day (.com only) |
| `enableMealBookingNudge` | BRE | false | Enables meal booking nudge notifications (both servers) |
| `enableMealConfigureKiosk` | BRE | false | Shows "Configure Kiosk" button on meal dashboard (.com only) |
| `enableSeparateMealOption` | BRE | false | Enables standalone meal-only booking (.com only) |
| `mealCancelCutoffInMinutes` | BRE | -1440 | Cancellation window in minutes (-1440 = 24 hrs before) (.com only) |
| `mealFinalStage` | BRE | ['delivered', 'DELIVERED'] | Final status values for a meal booking (.com only) |
| `excludeMealOnlyBookingsFromActiveBookingCount` | EMP-EXP-COMMON | false | Whether standalone meal bookings count toward active booking limit (.com only) |
| `mealCutoffInMinutes` | EMP-EXP-COMMON | not documented | Meal booking cutoff from 00:00 of booked date (both servers) |

Additional properties referenced in SE runbook docs (not yet in config catalog — to be confirmed with Meal Management team): `mealBookingEnabled`, `mealCheckinOptions`, `enableMealFallbackFlow`, `enableMealQrPrintButtonenableMealQrPrint`.

_Source: [[sources/se-runbook-meal-booking]]_

## Open Questions
- Core meal booking PRD not yet ingested — the SE runbook confirms the setup flow but does not substitute for a full feature PRD.
- Who owns `Cafeteria` — meal-management or meeting-rooms? ⚠️ (recurring open question)
- Is the Vendor Dashboard a separate module or part of meal-management?
- Four config properties from SE runbook (`mealBookingEnabled`, `mealCheckinOptions`, `enableMealFallbackFlow`, `enableMealQrPrintButtonenableMealQrPrint`) are not in the current config catalog — confirm service assignment and add to [[configs/booking-rule-engine]].
- `enableMealQrPrintButtonenableMealQrPrint` appears to be a concatenation of two property names in the source. ⚠️ Verify correct property name(s) with the Meal Management team.

## Related Runbooks

- [[runbooks/meal-booking]] — end-to-end SE setup runbook (cafeteria premise → QR generation)

## Last Updated
2026-06-29 — _Source: [[sources/se-runbook-meal-booking]]_ (prior: 2025-05-05 [[sources/meal-checkin-prd]])
