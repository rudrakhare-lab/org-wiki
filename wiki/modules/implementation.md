---
type: module
status: active
owner: unknown (requires Ujjwal Trivedi sign-off)
depends_on: [desk-management, parking-management, mobile-app, floor-kiosk]
used_by: []
last_updated: 2026-04-28
source: "[[sources/launch-ets-sop]]"
---

# Implementation Module (Client Onboarding SOPs)

## Overview
The Implementation module is not a product feature module — it is a collection of internal
SOPs, checklists, and guides used by the WorkInSync implementation/SE team when onboarding
new clients or migrating existing MoveInSync clients to WorkInSync Workplace.

Currently documented: ETS (Employee Transportation Service) migration SOP.

## Purpose & Scope
Owns: implementation procedures, onboarding checklists, migration runbooks, troubleshooting guides.
Does **not** own any product entities.

## Key Docs Available
- [[sources/launch-ets-sop]] — SOP for launching WorkInSync on an existing MoveInSync ETS client server (4 phases: Pre-Launch, Launch, Testing, Troubleshooting)

## ETS Migration — Key Steps Summary

### Pre-Launch
1. Schedule + communicate downtime; prepare BCP (manual trip sheets)
2. Validate employee data; tag non-transport users
3. Operations Study doc (shifts, features, cut-off times)
4. Upload floor plan + parking plan
5. Desk allocation file
6. Decide check-in mechanism (Digipass / QR / RFID / geofence)
7. WIS configuration finalization
8. Configuration backup via SE ticket
9. **Create test user transport booking (DO NOT SKIP)**

### Launch
1. Create desk + transport shifts via SE ticket
2. Raise SE ticket for config updates
3. Upload floor plan + parking plan via SE request (SVG + JSON)
4. Migrate transport bookings via migration API

### Testing
1. Verify pre-migration bookings on app + work planner with correct OTP
2. Create fresh booking; verify on Work Planner

### Troubleshooting
24 documented scenarios covering: booking visibility, OTP mismatch, floor plan issues, duplicate bookings, app crashes, shift configuration, user permission errors, and more.

## Dependencies on Other Modules
- [[modules/desk-management]] — desk shifts, floor plan upload, desk allocation
- [[modules/parking-management]] — parking plan upload during onboarding
- [[modules/mobile-app]] — transport booking visibility verification
- [[modules/floor-kiosk]] — floor plan (SVG/JSON) pipeline

## Open Questions
- Does a more comprehensive implementation guide exist (referenced as "SOP WIS Implementation" in the links section)?
- What are the standard SE ticket templates for WIS onboarding?

## Last Updated
2026-04-28 — _Source: [[sources/launch-ets-sop]]_
