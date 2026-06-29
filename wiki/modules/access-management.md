---
type: module
status: active
owner: unknown
depends_on: [desk-management, meeting-rooms, parking-management, meal-management]
used_by: [meal-management]
last_updated: 2025-02-10
source: "[[sources/access-mgmt-integration-api-based]], [[sources/access-mgmt-integration-api-based-ind]], [[sources/access-mgmt-integration-file-based]], [[sources/se-runbook-access-card]]"
---

# Access Management Module

## Overview
Access Management is WorkInSync's integration surface for **external / third-party access-card
vendors**. When an employee swipes their access card at an office reader, the vendor's system
relays that check-in/check-out event to WorkInSync, which records it against the employee's
booking (and can optionally create a booking if none exists). The module supports **two
integration modes**: a real-time **REST API** (since 2022) and an **SFTP file-based** CSV
transfer (since Feb 2025). The API mode is regionally deployed across `api.moveinsync.com`
(global) and `api.moveinsync.in` (IND region). Nine PMS config properties govern check-in
behavior — see [[configs/booking-rule-engine]] and [[configs/emp-experience-common]].

## Purpose & Scope
Owns the integration contract between external access-management vendors and WorkInSync:
the authentication scheme, the check-in/out API, the SFTP file-exchange procedure, and the
mapping of swipe events to WorkInSync bookings.

Does **not** own: the bookings themselves (those are owned by [[modules/desk-management]],
[[modules/meeting-rooms]], [[modules/parking-management]], and [[modules/meal-management]] —
this module reads/creates them via the integration API), the physical access-card hardware
or readers (third-party vendor devices), or identity (auth is a client-specific
username/password issued per integration, NOT the `sso` module's Azure AD). Check-in mode
config properties (`officeCheckInModeWeb`, `officeCheckInModeApp`) overlap with
[[modules/employee-experience]] configuration — set by the SE team per office.

## Key Features
- **API-based integration (REST)**: external vendors push check-in/out events via `POST /integration/bookings/ci-co`. Regionally deployed — see API Endpoints for the `.com` and `.in` baseUrls
- **Bearer-token authentication**: a client-specific `client_id` / `client_secret` is exchanged via `POST /auth/token` (HTTP Basic, `grant_type=client_credentials`) for a short-lived Bearer access token (`expires_in: 172799`, ~48h); the token is re-fetched on expiry. WorkInSync registers the client and issues credentials — vendor registers via the API Gateway before use
- **Check-in / check-out to bookings**: `bookingStatus` of `SIGNED_IN` checks in (or creates+checks-in), `SIGNED_OUT` signs the employee out of an existing booking
- **`createBookingIfNotPresent` flag**: when true, creates an office booking for employees who scan in without one, based on scan time + end time (configuration location not fully documented — see Open Questions). Related PMS config: `createBookingWhenCheckinReceived`
- **RFID card support**: the `rfid` field (added in v1.2, Jul 2024) allows lookup by card number; `filter` can be left blank when `rfid` is supplied; RFID→employee mapping is a prerequisite one-time setup
- **Employee resolution by `filter`**: accepts EmployeeID, EmployeeName, or EmployeeEmailID (max 50 chars); must be unique per employee
- **File-based integration (SFTP)**: an alternative mode (since Feb 2025) where clients push CSV swipe-data files to a WorkInSync SFTP server on a configured frequency. Setup requires SSH (Secure Shell) key, IP whitelisting, optional encryption method, and an agreed push frequency (e.g. every 1 hour). WorkInSync provides port, filepath, and server details after configuration. Enabled via `externalChannelCheckIn`
- **Device-to-floor mapping** (file-based and API mode): a one-time CSV upload (`POST mis-security-guard/csv/sta…`) maps each reader/device to an office and floor, so that reports show which office/floor a check-in was performed at. Required for per-floor utilization reporting (PB-45283)
- **External-check-in to booking creation**: when `createBookingWhenCheckinReceived` is enabled, a booking is auto-created for employees who swipe without one. `defaulBookingHoursIfExtCheckin` sets the default booking duration (DOUBLE, hours). `extCheckinToBookingBuffer` sets a buffer window (DOUBLE, hours) around the booking for check-in acceptance
- **Anomaly + utilization reporting (file-based mode)**: highlights employees who entered without a booking; optional configs to reject entry without a booking or auto-create one; resource-utilization reports for admins
- **First-check-in record** (`showFirstCheckInRecord`, PB-48998): when enabled, only the first check-in is honoured across bookings/audits/reports and shown in the UI (web + mobile). Checkout via SFTP Access Card integration was added later (PB-48425)
- **Last-swipe-as-checkout**: `lastSwipeAsCheckoutTimeForBUID` (EMP-EXP-COMMON-CONFIG, LIST, both servers) uses the last swipe as final checkout time instead of auto-checkout

## SE Setup Workflow (Access Card Integration)

### REST API mode
1. Collect from client: vendor `client_id` and `client_secret` to share, scanner device details, regional server preference (`.com` or `.in`), RFID→employee mapping file (if using RFID)
2. Register client credentials in the API Gateway; share the `client_id` + `client_secret` with the vendor
3. Perform device-to-office/floor mapping upload (one-time CSV — see [[runbooks/access-card-integration]])
4. Enable `recordCheckInOutViaAccessCardAPI = true` (BRE, `.com`) on the BUID
5. Configure optional behaviors: `createBookingWhenCheckinReceived`, `defaulBookingHoursIfExtCheckin`, `extCheckinToBookingBuffer`, `showFirstCheckInRecord`
6. Set `officeCheckInModeWeb` and `officeCheckInModeApp` per office (BRE, `.com`) — see config table below
7. Vendor tests end-to-end with a swipe → verify booking check-in in WIS admin

### SFTP file mode
1. Collect from client: SSH public key, IP addresses for whitelisting, encryption method (if any), push frequency
2. Configure SFTP server; share port, filepath, and server details with client
3. Share WorkInSync file format template for employee swipe data; request a sample file push and test
4. Enable `externalChannelCheckIn = true` (BRE, `.com`) on the BUID
5. Configure post-import behaviors: `createBookingWhenCheckinReceived`, `showFirstCheckInRecord`, `lastSwipeAsCheckoutTimeForBUID`

_Source: [[sources/se-runbook-access-card]]_

## Data Entities Used
- [[entities/booking]] — consumed and optionally created via the integration; the booking itself is owned by the relevant booking module (desk / meeting-rooms / parking / meal)
- [[entities/employee]] — employee identity record (identity, entitlements, relationships)

## Dependencies on Other Modules
- [[modules/desk-management]] — OFFICE bookings updated/created by access-card check-in
- [[modules/meeting-rooms]] — MEETING bookings (per the IND doc's `premiseId` booking-type enum)
- [[modules/parking-management]] — PARKING / PARKING_TWO / PARKING_FOUR bookings
- [[modules/meal-management]] — MEALS bookings

(see ⚠️ **Dependency grounding uncertainty** in Open Questions — these are inferred from the IND doc's `premiseId` enum, which the global doc contradicts)

## Used By
(none within WorkInSync — the consumers of this module are EXTERNAL access-management vendor systems, not other WIS modules)

## API Endpoints
Two regional deployments. Global clients use `https://api.moveinsync.com`; IND-region clients use `https://api.moveinsync.in`.

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| POST | `{baseUrl}/auth/token` | Exchange client credentials for a Bearer access token | `Authorization: Basic <base64(client_id:client_secret)>`, form body `grant_type=client_credentials` |
| POST | `{baseUrl}/integration/bookings/ci-co` | Record a check-in or check-out event against a booking | `Authorization: Bearer <token>` |

**Auth response**: `{ "access_token": "<bearer-token>", "token_type": "Bearer", "expires_in": 172799 }`

**ci-co request fields:**

| Field | Format | Required | Description | Constraints |
|---|---|---|---|---|
| `filter` | String | ✓ (or `rfid`) | EmployeeID / EmployeeName / EmployeeEmailID | Max 50; unique per employee; may be blank if `rfid` is passed |
| `bookingStatus` | String | ✓ | `SIGNED_IN` (check-in / create+check-in) or `SIGNED_OUT` (check-out) | Max 50 |
| `epochTime` | Long | ✓ | Timestamp of the action in epoch milliseconds | — |
| `officeName` | String | one of the three | Office where the action was performed | Max 100 |
| `premiseId` | String | one of the three | **⚠️ semantics differ between global and IND docs — see Open Questions** | Max 50 |
| `readerId` | String | one of the three | Device ID at the entry point; reader→office/floor mapping is a one-time setup | Max 50 |
| `rfid` | String | (alt to `filter`) | Card identifier; RFID→employee mapping required | Max 50 |

_Note: exactly one of `readerId` / `premiseId` / `officeName` must be passed to identify the office._

**ci-co response fields:**

| Field | Format | Description |
|---|---|---|
| `status` | Integer | API status code (200 = success, 1001 = internal failure) |
| `data` | UUID | Booking Id (Max 50) |
| `message` | String | Success / failure message |

_Note: HTTP status is 200 on both success and internal failure; the `status` field in the body distinguishes them (200 vs 1001). HTTP 401 is returned only when the Authorization header is missing. Source docs contain sample cURLs with live base64 credentials and `eyJ…` tokens — these are REDACTED here per wiki policy and replaced with `<base64(client_id:client_secret)>` / `<bearer-token>` placeholders._

## Key Config Properties

These PMS properties govern access-card check-in behavior. Full details and dual-server comparison at [[configs/booking-rule-engine]] and [[configs/emp-experience-common]].

| Property | Service | Type | Default | Server | Description |
|----------|---------|------|---------|--------|-------------|
| `recordCheckInOutViaAccessCardAPI` | BRE | BOOLEAN | false | .com only | Enable check-in/out recording via access-card API integration |
| `externalChannelCheckIn` | BRE | BOOLEAN | false | .com only | Enables SFTP file-based access card check-in mode |
| `createBookingWhenCheckinReceived` | BRE | BOOLEAN | false | .com only | Auto-create a booking when a check-in event is received for an employee with no booking |
| `defaulBookingHoursIfExtCheckin` | BRE | DOUBLE | not documented | .com only | Default booking duration (hours) when a booking is auto-created via external check-in. Note: property name has a typo — `defaul` not `default` |
| `extCheckinToBookingBuffer` | BRE | DOUBLE | not documented | both | Buffer window (hours) around a booking within which an external check-in is accepted |
| `showFirstCheckInRecord` | BRE | BOOLEAN | false | .com only | When enabled, only the first check-in is honoured in bookings, audits, and reports (PB-48998) |
| `officeCheckInModeWeb` | BRE | STRING | not documented | .com only | Check-in mode for the web app. Values: `directCheckIn` / `digiPass` / `scanQR` / `noCheckIn` |
| `officeCheckInModeApp` | BRE | STRING | not documented | .com only | Check-in mode for the mobile app. Values: `directCheckIn` / `digiPass` / `scanQR` / `noCheckIn` |
| `lastSwipeAsCheckoutTimeForBUID` | EMP-EXP-COMMON | LIST | not documented | both | BUIDs for which the last access-card swipe is used as checkout time instead of auto-checkout |

> ⚠️ `officeCheckInModeWeb` and `officeCheckInModeApp` are set per-office by the SE team; they control the check-in UX for all users at that office, not just access-card users. Setting these is required even for non-access-card deployments when a specific check-in mode is needed.

_Source: [[sources/se-runbook-access-card]]_

## Open Questions
- ⚠️ **`premiseId` semantics contradict between the two API docs.** The global doc and the IND doc describe the same field with mutually incompatible meanings:
  - Global (`access-mgmt-integration-api-based`): *"The unique ID associated with the location where the action was performed. It may be an office or specific floor location."*
  - IND (`access-mgmt-integration-api-based-ind`): *"Type of booking that is requested ... Possible Values OFFICE, PARKING, PARKING_TWO, PARKING_FOUR, MEALS, MEETING"*
  Same field name, incompatible semantics. **Do not select an interpretation — engineering must clarify which `premiseId` semantic is canonical.**
- ⚠️ **Dependency grounding uncertainty** — the four dependency modules are inferred from the IND doc's premiseId enum (OFFICE, PARKING, MEALS, MEETING). The global doc's premiseId semantics (location identifier, not booking type) contradict this. If the global doc is correct, the actual module dependencies may differ. Engineering should clarify which premiseId semantic is canonical.
- ⚠️ **Regional API split** — `api.moveinsync.com` (global) vs `api.moveinsync.in` (IND). The IND doc's title says "IND Region [MUM]" ("MUM" presumably Mumbai), but the doc covers the `.in` region broadly. Clients must use the correct regional baseUrl.
- ⚠️ **File-based mode CSV schema not documented.** The file-based source (`access-mgmt-integration-file-based`) has empty "File format" and "Report insights" sections — the actual CSV column schema is absent. The SFTP setup procedure is documented, but the data format is not. A consumer cannot implement the file push from this source alone.
- **`defaulBookingHoursIfExtCheckin` and `extCheckinToBookingBuffer` defaults** are not stated in any source doc. Values to be confirmed with the owning team.
- **`lastSwipeAsCheckoutTimeForBUID` values** — source confirms it is a LIST type (presumably a list of BUID strings). Exact format not documented.
- **API Gateway design topics deferred by source** — the source notes throttling, fault tolerance, secure data exchange, error logging "need to be discussed in further detail" (global doc). These are unspecified.
- **Documentation-hygiene observation** — the global and IND API docs share identical Version Control histories (same authors, approval dates, and descriptions at v1.0/1.1/1.2), suggesting the IND doc was branched/copied from the global rather than maintained independently.
- **Module owner not named** — authors across the four docs: Rahul Agrawal (API v1.0), Binoy Dedhia (API v1.1), Aditya Dutta (API v1.2 + File-based v1.0); approver Ujjwal Trivedi throughout. No owning team stated.

## Related Runbooks
- [[runbooks/access-card-integration]] — SE setup guide: vendor onboarding, REST auth flow, SFTP mode, check-in config properties

## Last Updated
2026-06-29 — _Source: [[sources/access-mgmt-integration-api-based]], [[sources/access-mgmt-integration-api-based-ind]], [[sources/access-mgmt-integration-file-based]], [[sources/se-runbook-access-card]]_
