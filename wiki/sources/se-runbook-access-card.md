---
type: source
raw_path: raw/se-runbook/crawl/
ingested: 2026-06-29
doc_type: spec
---

# Source: Access Card Integration — SE Runbook Docs

## Source Title
WorkInSync Access Card Integration — SE runbook source set

## Date
Various: Jun 2022 (API v1.0), Nov 2022 (API v1.1), Jul 2024 (API v1.2 + RFID), Feb 2025 (SFTP v1.0)

## Type
spec (integration setup guides + check-in mode reference)

## Key Takeaways
- WorkInSync supports two access-card integration modes: REST API (real-time, since 2022) and SFTP file-based (batch, since Feb 2025)
- REST API auth uses a client-specific `client_id` / `client_secret` exchanged via `POST {baseUrl}/auth/token` (HTTP Basic, `grant_type=client_credentials`) for a ~48h Bearer token (`expires_in: 172799`)
- The check-in/out endpoint is `POST {baseUrl}/integration/bookings/ci-co`; `bookingStatus` drives `SIGNED_IN` (check-in / create+check-in) vs `SIGNED_OUT` (check-out)
- RFID support was added in v1.2 (Jul 2024); employee can be resolved by `filter` (ID/name/email) or `rfid` card number
- SFTP mode requires SSH key, IP whitelisting, optional encryption, and an agreed push frequency; WorkInSync provides server details after configuration
- Nine PMS config properties govern external check-in behavior: `recordCheckInOutViaAccessCardAPI`, `externalChannelCheckIn`, `createBookingWhenCheckinReceived`, `defaulBookingHoursIfExtCheckin` (typo preserved — real property name), `extCheckinToBookingBuffer`, `showFirstCheckInRecord`, `officeCheckInModeWeb`, `officeCheckInModeApp`, `lastSwipeAsCheckoutTimeForBUID`
- `officeCheckInModeWeb` / `officeCheckInModeApp` accept values `directCheckIn` / `digiPass` / `scanQR` / `noCheckIn` — set per-office by the SE team
- Device-to-office/floor mapping is a one-time CSV upload required for per-floor utilization reports (PB-45283)
- `showFirstCheckInRecord` (PB-48998): honours only the first check-in across system; SFTP checkout support was added later in PB-48425
- Source docs contain live base64 credentials and `eyJ…` JWT tokens as sample cURLs — all REDACTED in wiki pages and runbooks

## Source Documents (in `/tmp/acc_inputs.md`)
| Document | Version | Date | Notes |
|----------|---------|------|-------|
| WorkInSync Check In/Out Mode | — | undated | Describes all check-in modes incl. `officeCheckInModeWeb/App` values |
| WorkInSync Access Card Management Integration - File based | 1.0 | Feb 10, 2025 | SFTP setup; internal configs listed |
| WorkInSync Check In Integration document | 1.1 | Nov 29, 2022 | Older API spec; `AccessCardCheckIn` endpoint |
| WorkInSync Access Card Integration API Document [OG Tech] For Majid Al Futtaim | 1.2 | Jul 19, 2024 | Client-specific variant; API identical to global |
| WorkInSync Access Card Management Integration - API based (global) | 1.2 | Jul 19, 2024 | Main API integration doc |
| WorkInSync Access Card Management Integration - API based IND Region [MUM] | 1.2 | Jul 19, 2024 | India region variant; `premiseId` semantic conflict with global |
| WorkInSync Access Card Check In Integration document | — | undated | Check-in integration supplemental |
| WorkInSync Booking APIs | — | undated | Booking API context |
| WorkInSync Parking Setup For Implementation Team | — | undated | Cross-referenced for parking check-in modes |

## Entities Mentioned
- [[entities/booking]] — consumed and optionally created by check-in events
- [[entities/employee]] — identified by `filter` (EmployeeID / EmployeeName / EmployeeEmailID) or `rfid`

## Modules Mentioned
- [[modules/access-management]] — primary module; all docs
- [[modules/desk-management]] — OFFICE booking type
- [[modules/meeting-rooms]] — MEETING booking type
- [[modules/parking-management]] — PARKING / PARKING_TWO / PARKING_FOUR booking types
- [[modules/meal-management]] — MEALS booking type
- [[modules/employee-experience]] — `officeCheckInModeWeb/App` config overlap

## Decisions Extracted
None formal. Implicit design decision: SFTP mode introduced Feb 2025 as a fallback for
clients whose access systems cannot make outbound REST calls.

## Wiki Pages Created / Updated
- Updated: [[modules/access-management]] — added SE Setup Workflow, Key Config Properties section, Related Runbooks; enriched Key Features with SFTP details, device mapping, first-check-in, last-swipe-checkout
- Created: [[runbooks/access-card-integration]] — full SE setup guide for both REST API and SFTP modes
- Updated: [[configs/booking-rule-engine]] — descriptions + defaults filled for 8 access-card properties
- Updated: [[configs/emp-experience-common]] — description confirmed for `lastSwipeAsCheckoutTimeForBUID`

## Secrets Redaction Note
Source documents contain live `eyJ…` JWT Bearer tokens and base64-encoded `client_id:client_secret`
strings embedded in sample cURL commands. All such values have been REDACTED in all wiki output
and replaced with `<bearer-token>` / `<base64(client_id:client_secret)>` placeholders.
Count: 3 unique credential strings identified across the API docs (1 base64 Basic credential,
2 truncated `eyJ…` JWT samples). Zero `eyJ…` strings appear in any wiki page written from this source.
