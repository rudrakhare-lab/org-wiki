---
type: module
status: active
owner: unknown
depends_on: [desk-management, guard-app-kiosks]
used_by: []
last_updated: 2026-06-29
source: "[[sources/se-runbook-sanitization]]"
---

# Sanitization Module

## Overview
The Sanitization module enables facilities managers to track and enforce seat (desk) sanitization workflows within WorkInSync. Housekeeping staff are onboarded as HOUSEKEEPER users, scan QR codes attached to seats or floors, and mark desks as sanitized. The system records sanitization timestamps that are surfaced on floor views and at booking time so employees can see the cleanliness status of a seat before and after use.

## Purpose & Scope
Owns the complete seat sanitization lifecycle: HOUSEKEEPER user provisioning, QR-code-based seat marking, sanitization status visibility (real-time floor view + employee booking view + admin reports), and configurable cut-off times. Does NOT own general desk booking or check-in — those belong to `desk-management`. Does NOT own the physical QR-code printing or floor-plan polygon layout — those belong to `guard-app-kiosks` and `digital-wayfinding` respectively.

## Key Features
- HOUSEKEEPER user creation via `mis-security-guard` API (name, phone, BUID, `type: HOUSEKEEPER`)
- QR-code scan workflow: housekeeping staff log in via phone + OTP, scan a floor/seat QR code, and mark one or more seats sanitized
- Non-QR fallback: staff can select a floor and mark all seats on it directly if QR codes are not deployed
- Per-seat sanitization timestamp captured and stored
- Admin report: filterable by office, floor, seat number; shows last sanitization time
- Real-time floor view: last sanitization time visible per seat
- Employee booking view: last sanitization time of the target seat shown at booking and on existing booking (on demand)
- Configurable QR-code scan enforcement (`enableQrCodeForSeatSanitize`)
- Configurable sanitization cut-off time in minutes (`seatSanitizeCuttoffInMinute`)
- Sanitization status toggle for the admin UI (`SANITISATION_STATUS_ENABLED` / `sanitisationStatus`)

## Vaccination Status
The Vaccination Status feature is operationally related to seat sanitization in that it was introduced as part of the same return-to-office safety umbrella and shares some config services (`BOOKING-RULE-ENGINE`, `EMP-EXP-COMMON-CONFIG`). Its workflow enables employees to declare vaccination status, upload certificates, and optionally blocks unvaccinated employees from booking desks.

Relevant config properties: `vaccinationBookingEnabled`, `showVaccinationOptionInSideMenu`, `blockUserIfNotVaccinated`, `vaccinationMaxApprovalDays`.

A note for setup: enabling `blockUserIfNotVaccinated` blocks ALL future bookings for unvaccinated users system-wide — confirm scope with client before enabling.

> **Open Question:** Should Vaccination Status be a standalone module (e.g. `vaccination-status`) separate from `sanitization`? The two features share return-to-office intent but have distinct user journeys, configs, and owning teams. See Open Questions section below.

## Data Entities Used
- [[entities/user]] — HOUSEKEEPER subtype of guard/worker user
- [[entities/seat]] — the desk being sanitized (seat polygon, QR code)
- [[entities/premise]] — floor/office premise that contains the seats

## Dependencies on Other Modules
- [[modules/desk-management]] — Sanitization status is surfaced on the desk booking flow; seat identifiers come from the desk-management seat graph
- [[modules/guard-app-kiosks]] — HOUSEKEEPER users are provisioned through the same `mis-security-guard` service used by guard users; QR-code scanning runs on the same infrastructure

> Reciprocal `used_by` entries in `desk-management` and `guard-app-kiosks` are **pending the graph-consistency sweep** — do not add them here until confirmed; see Open Questions.

## Used By
_(No confirmed downstream module consumers at time of ingest — pending graph-consistency sweep.)_

## SE Setup Workflow
The full SE procedure is in [[runbooks/seat-sanitization]]. Summary steps:
1. **TO team** enables `SANITISATION_STATUS_ENABLED` in Consul → TeamManager Service → BUID
2. **SE team** creates one or more HOUSEKEEPER users via Postman
3. **SE team** sets `enableQrCodeForSeatSanitize` in `mis-security-guard` config (true/false)
4. **SE team** sets `seatSanitizeCuttoffInMinute` value in `mis-security-guard` config

## Key Config Properties

| Property | Service | Type | Default | Server | Notes |
|----------|---------|------|---------|--------|-------|
| `SANITISATION_STATUS_ENABLED` | TeamManager (Consul) | BOOLEAN | — | both | Enables sanitization status UI view; set by TO team |
| `enableQrCodeForSeatSanitize` | `mis-security-guard` | BOOLEAN | — | both | Enables QR-code scan requirement for housekeepers |
| `seatSanitizeCuttoffInMinute` | `mis-security-guard` | DOUBLE | — | both | Minutes after booking start/end before seat is flagged for sanitization |
| `vaccinationBookingEnabled` | `EMP-EXP-COMMON-CONFIG` | BOOLEAN | — | both | Master toggle for vaccination booking workflow |
| `showVaccinationOptionInSideMenu` | `EMP-EXP-COMMON-CONFIG` (Consul) | BOOLEAN | — | .com | Shows vaccination option in app side menu |
| `blockUserIfNotVaccinated` | `BOOKING-RULE-ENGINE` | BOOLEAN | false | both | Blocks unvaccinated users from booking — set false by default to avoid blocking all users |
| `vaccinationMaxApprovalDays` | `BOOKING-RULE-ENGINE` | INTEGER | 5 | .com | Max days admin has to approve vaccination certificate |

> Default values marked `—` are not documented in PMS config files. Check Jira or ping the owning team.

## API Endpoints
| Method | Path | Description | Auth Required |
|--------|------|-------------|---------------|
| POST | `https://mis-security.moveinsync.com/mis-security-guard/user` | Create HOUSEKEEPER user | Yes |
| GET | `https://mis-security.moveinsync.com/mis-security-guard/login/phoneNumber/{phone}` | Look up existing HOUSEKEEPER/Guard user by phone | Yes |
| PUT | `http://empexp.moveinsync.com/employee-exp/{buid}/update-config?feature=common` | Enable `vaccinationBookingEnabled` | Yes |

> All endpoint base URLs are examples sourced from the SE runbook. Confirm current production hostnames before use.

## Related Runbooks
- [[runbooks/seat-sanitization]] — HOUSEKEEPER user creation, QR-scan toggle, cut-off time configuration

## Open Questions
- **Module placement:** Should `sanitization` be a standalone module (as created here) or folded into `desk-management` (sanitization is a status attribute of a desk) or `guard-app-kiosks` (HOUSEKEEPER users live in the guard service)? Confirm placement with owning team before linking this page from index.
- **Vaccination as separate module:** The Vaccination Status Feature (v1 doc) covers a substantively different user workflow (employee self-declaration, certificate upload, admin approval, booking gate). It may warrant its own module slug (e.g. `vaccination-status`). Currently documented as a section here — promote if scope warrants.
- **Reciprocal used_by pending:** `desk-management` should list `sanitization` in `used_by`, and `guard-app-kiosks` should reference the HOUSEKEEPER user type. These updates are deferred to the graph-consistency sweep.
- **`seatSanitizeCuttoffInMinute` type anomaly:** The source shows this property set to `true` (boolean-like) rather than a numeric value. The property name implies a duration in minutes. Likely an SE-runbook example error — confirm actual data type with owning team.
- **Owner:** Module owner unknown at ingest time. Likely shared between Facilities/SE team and a product team — confirm.
- **`sanitisationStatus` vs `SANITISATION_STATUS_ENABLED`:** Source section 59 maps these as equivalent (camelCase config key ↔ Consul flag). Verify if they are the same property in different config surfaces or distinct toggles.

## Last Updated
2026-06-29 — source: [[sources/se-runbook-sanitization]]

_Source: [[sources/se-runbook-sanitization]]_
