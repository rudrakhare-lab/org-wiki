---
type: source
raw_path: raw/modules/implementation/SOP for Launching WorkinSync on Live ETS Server.docx
ingested: 2026-04-28
doc_type: spec
---

# SOP for Launching WorkInSync on Existing MoveInSync ETS Server

## Source Title
Launching WorkInSync on Existing MoveInSync Client Server (ETS migration SOP)

## Date
Unknown (requires Ujjwal Trivedi sign-off before publishing)

## Type
spec (internal SOP)

## Key Takeaways
- Step-by-step guide for migrating an existing MoveInSync ETS (Employee Transportation Service) client to the WorkInSync Workplace solution.
- **4 phases**: (1) Pre-Launch Preparation, (2) Launch, (3) Testing, (4) Troubleshooting

### Phase 1 — Pre-Launch
- Schedule downtime (communicate to stakeholders, have manual trip sheets as BCP)
- Validate employee data from HR; tag non-transport users
- Operations Study doc: shift timings, feature list, cut-off times (transport + desk)
- Upload floor plan + parking plan (signed-off SVG/JSON)
- Desk allocation file (type, employee/team → desk number)
- Decide check-in mechanism: Digipass, QR scan, access card, geofence
- Finalize WIS configurations (features, parking, meeting rooms, cafeteria)
- Enable relevant reports
- Configuration backup via SE ticket (scrapped from laptops within 60 days post-launch)
- **Create a test user transport booking before launch** (DO NOT SKIP)

### Phase 2 — Launch
- Create shifts (desk shifts for non-transport users + transport shifts) via SE ticket
- Raise SE ticket for configuration updates (features + cut-offs)
- Upload floor plan + parking plan via SE request (SVG + JSON)
- Migrate existing transport bookings via migration API (Akshay/Anirban/Pranjal/Anoop)

### Phase 3 — Testing
- Verify pre-migration transport bookings appear on app + work planner with correct OTP
- Create fresh booking and verify on Work Planner

### Phase 4 — Troubleshooting (24 documented scenarios)
- Booking not on app → migration issue; re-upload future bookings
- Wrong OTP → serious operational issue; involve tech team immediately; remove + redo bookings
- Floor plan not visible → check SE ticket completion
- Transport booking cut-off incorrect → raise SE ticket
- Duplicate bookings → clean up via tech team
- App crash → capture screen recording + app version + OS + emp details
- (plus 17 more scenarios)

## Entities Mentioned
- None specific.

## Modules Mentioned
- [[modules/implementation]] (primary)
- [[modules/desk-management]] (desk shifts, allocation, floor plan)
- [[modules/parking-management]] (parking plan upload)
- [[modules/mobile-app]] (transport booking visibility)

## Decisions Extracted
- None new.

## Wiki Pages Created/Updated
- Created: [[modules/implementation]]

_Source: [[sources/launch-ets-sop]]_
