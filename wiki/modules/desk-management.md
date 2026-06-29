---
type: module
status: active
owner: unknown
depends_on: [tags-desk-parking]
used_by: [access-management, delegation, implementation, meal-management, parking-management]
last_updated: 2026-06-29
source: "[[sources/se-runbook-desk-management]]"
---

# Desk Management

## Overview

Desk Management is WorkInSync's core workspace-booking module. It lets employees book physical office desks (hot-desks or dedicated seats) for work-from-office days, and gives admins tools to allocate desk inventory by floor, team, or individual. The module owns the `WIS-SEAT-BOOKING` PMS service, exposes booking data to external systems via a REST integration API, and supports manager-approval workflows powered by Camunda for controlled-access scenarios.

_Source: [[sources/se-runbook-desk-management]]_

## Purpose & Scope

Desk Management is responsible for:

- The full lifecycle of a desk booking: create, edit, check-in, sign-out, cancel, and audit.
- Desk inventory management: floor-level seat counts, allocation to teams/BUs/individuals, hot-desk designation, and amenity tagging.
- Work-from-home (WFH) and work-from-office (WFO) booking types including recurring/WorkPlanner bookings.
- Booking approval workflow integration (Camunda decision tables) for clients requiring manager sign-off.
- External API access so client systems or third-party vendors can query bookings and available resources.

**Boundary:** Desk Management does not own floor-plan upload or premise creation (see [[modules/floor-kiosk]] and [[runbooks/floor-plan-upload]]). Tags applied to desks and employees are managed by [[modules/tags-desk-parking]]. Booking rule evaluation (weekly/monthly caps, shift eligibility) lives in the Booking Rule Engine service — see [[configs/booking-rule-engine]]. Meal booking attached to a WFO booking is handled by [[modules/meal-management]].

_Source: [[sources/se-runbook-desk-management]]_

## Key Features

**Employee-facing:**
- Book a desk for WFO or WFH on a given date/shift via floor-plan UI or mobile app.
- Search for a colleague and select an available seat nearby.
- Filter available seats by amenity (dual monitors, height-adjustable desk, IP phone, printer, etc.).
- Recurring / WorkPlanner bookings across a date range (requires `enableRecurrenceOnTeamPlanner` on BOOKING-RULE-ENGINE).
- Dedicated-seat "Perpetual Digi Pass" — employees with a fixed assigned desk can scan in without making a daily booking (the system auto-creates the booking on check-in). ⚠️ This was introduced Sep 2021 (see [Historical note](#open-questions)); current enablement status is a property-based feature requiring a TO ticket.
- Booking preferences (preferred desk, preferred shift) for repeated WFO patterns.
- Team Calendar — weekly view of colleagues' upcoming office days.

**Manager / BU Head:**
- Rostering dashboard for booking on behalf of multiple team members at once.
- Create, edit, cancel, and view bookings for team members.
- Approve or reject booking requests (when approval flow is enabled).
- Team-wise dashboard and reporting.

**Admin:**
- Allocate/deallocate desks to BU / team / individual or mark as hot-desk.
- Add/remove desk inventory and amenities per floor.
- Desk Bulk Upload via Excel (seat assignment, booking upload, desk tagging).
- Real-time floor layout view of occupied vs. available seats.
- Booking Autocancellation after configurable hours post-login-time.
- Restrict bookings by tag/team rules.
- Audit trail for all booking changes.
- Reports: Seat Booking, Seat Assignment (date-range selectable).

**Booking approval (Camunda-powered):**
- Configurable approval criteria: applicable to WFO, WFH, or both; by shift; by employee tag; weekly/monthly booking limits.
- Manager receives request; approves/rejects with reason; auto-approval if no action within deadline.
- Managed via a Camunda DMN decision table (`bookingApproval-prod.dmn`) hosted at `wis-camunda-engine.workinsync.io`.

_Source: [[sources/se-runbook-desk-management]]_

## Data Entities Used

- [[entities/booking]] — core booking record (BookingID, requestStatus/bookingStatus, startTime, endTime, premiseType, resourceName, officeName, floorName, employee email).
- **Desk / Seat** — physical seat entity with amenity metadata, floor assignment, allocation type (hot-desk / team / individual / BU). No standalone entity page yet — see Open Questions.
- **Floor** — the parent container for desks; referenced via FloorPremiseID (managed by [[modules/floor-kiosk]]).
- **Tag** — desk-level and employee-level tags managed by [[modules/tags-desk-parking]], consumed here for allocation rules and approval routing.
- [[entities/employee]] — employee profile (email, team, BU, reporting manager) used for booking validation, proximity search, and approval routing.

_Source: [[sources/se-runbook-desk-management]]_

## Dependencies on Other Modules

- [[modules/tags-desk-parking]] — desk tags and employee tags drive allocation rules, booking eligibility restrictions, and approval-flow tag checks.

**Cross-cutting services referenced (no standalone module page):**
- `BOOKING-RULE-ENGINE` — evaluates booking rules (weekly/monthly caps, shift eligibility, WFO/WFH constraints). Config reference: [[configs/booking-rule-engine]].

_Source: [[sources/se-runbook-desk-management]]_

## Used By

- [[modules/access-management]] — card swipes at office entry auto-create or check in a desk booking for the employee; the access-card integration calls `WIS-SEAT-BOOKING` to record sign-in/sign-out.
- [[modules/delegation]] — delegates (proxy users) can create and manage desk bookings on behalf of the employee whose profile they are acting under.
- [[modules/implementation]] — client-onboarding SOPs include desk-booking configuration steps (capacity, shifts, allocation setup) as part of initial site activation.
- [[modules/meal-management]] — meal booking is optionally linked to a WFO desk booking; meal cutoff and booking-mandate rules reference the desk booking record.
- [[modules/parking-management]] — parking is offered as a WFO add-on alongside a desk booking; the parking module reads the desk booking context to validate combined WFO eligibility.

_Source: [[sources/se-runbook-desk-management]]_

## API Endpoints

All endpoints require a Bearer token obtained from the authentication endpoint first.

**Authentication:**

| Method | Path | Description | Auth Required |
|--------|------|-------------|---------------|
| POST | `{baseUrl}/auth/token` | Obtain access token via client credentials (`Authorization: Basic <base64(username:password)>`, body: `grant_type=client_credentials`). Token valid 48 h (configurable). | Basic (client credentials) |

**Booking & Resource APIs (base: `{baseURL}`):**

| Method | Path | Description | Auth Required |
|--------|------|-------------|---------------|
| GET | `/integration/bookings` | `GetBookingDetails` — all bookings in a time window. Params: `startTime`, `endTime` (epoch ms; defaults today), `emailID`, `officeId`, `bookingTypeList`, `pageNo`, `limit` (max 100). Response includes `BookingID`, `requestStatus`, `premiseType`. | Bearer token |
| GET | `/integration/booking` | `GetAllBookings` (newer endpoint) — same purpose; response adds `bookingStatus`, `officeName`, `resourceName` (desk/room name), `floorName`. | Bearer token |
| GET | `/premise/offices` | `Office List` — all offices configured for the client. No input params. Response: `officeguid`, `officename`, `geoCords`, `timezone`. | Bearer token |
| GET | `/booking/available/{emailID}` | `Available Resources` — available desks and rooms for the employee in a given office and time window. Params: `emailID`, `officeId`, `startTime`, `endTime`. Response includes `floor` (JSON: `{floorName: {}}`). | Bearer token |

**Notes:**
- `premiseType` values in booking response: `OFFICE`, `CAFE`, `PARKING`, `PARKING_TWO`, `PARKING_FOUR`, `MEALS`, `MEETING`, `ON_CALL`, `VACCINATION`, `VISITOR`, `WFH`.
- `requestStatus` (legacy endpoint): `CONFIRMED`, `TO BE ASSIGNED`, `PENDING`, `SIGNED_IN`, `SIGNED_OUT`.
- `bookingStatus` (new endpoint): adds `CANCELLED`.
- Base URL example (EU): `https://api.eu.workinsync.io`; global: `https://api.moveinsync.com`.

_Source: [[sources/se-runbook-desk-management]]_

## Related Runbooks

- [[runbooks/desk-booking-setup]] — end-to-end space-management and desk allocation setup (floor plan, inventory, allocation, bulk upload).
- [[runbooks/recurring-booking-setup]] — enabling recurring/WorkPlanner bookings via Booking Rule Engine properties.
- [[runbooks/booking-approval-camunda]] — adding a BUID to the Camunda approval decision table.

## Open Questions

- **Module owner:** `owner: unknown` — no team name appears in any source doc; confirm with the WIS desk-booking squad.
- **Perpetual Digi Pass current status:** Introduced Sep 2021 as a property-based feature (raise a TO ticket). The 2021 pptx source is the only reference — it is unclear whether the enablement process has changed since then. Confirm with the team before documenting setup steps.
- **`booking-rule-engine` as a module:** BOOKING-RULE-ENGINE is cross-cutting and has no `wiki/modules/` page. If a standalone module page is ever created, add it to `depends_on`. For now, link via [[configs/booking-rule-engine]].
- **Desk entity page:** No `wiki/entities/desk.md` exists. The desk/seat entity (amenities, allocation type, seat name, floor, status) is significant enough to warrant one. Create during next ingest pass.
- **`implementation` in `used_by`:** The reciprocal link (`desk-management` in `implementation`'s depends_on) is not confirmed in source. Flagged for the graph sweep.
- **`sanitization` module:** The index shows `[[modules/sanitization]]` depends on `desk-management` but it is not in the `used_by` list. Flagged for the graph sweep.
- **Approval property defaults:** Several `WIS-SEAT-BOOKING` approval properties (`expiryCutOffInMinutes`, `wfhWeeklyLimit`, `wfhMonthlyLimit`, `autoExpireHour`) have no defaults stated in source. Check [[configs/wis-seat-booking]] and Jira for confirmed values.

## Last Updated

2026-06-29 — source: [[sources/se-runbook-desk-management]]
