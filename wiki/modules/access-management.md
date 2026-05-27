---
type: module
status: active
owner: unknown
depends_on: [desk-management, meeting-rooms, parking-management, meal-management]
used_by: []
last_updated: 2025-02-10
source: "[[sources/access-mgmt-integration-api-based]], [[sources/access-mgmt-integration-api-based-ind]], [[sources/access-mgmt-integration-file-based]]"
---

# Access Management Module

## Overview
Access Management is WorkInSync's integration surface for **external / third-party access-card
vendors**. When an employee swipes their access card at an office reader, the vendor's system
relays that check-in/check-out event to WorkInSync, which records it against the employee's
booking (and can optionally create a booking if none exists). The module supports **two
integration modes**: a real-time **REST API** (since 2022) and an **SFTP file-based** CSV
transfer (since Feb 2025). The API mode is regionally deployed across `api.moveinsync.com`
(global) and `api.moveinsync.in` (IND region).

## Purpose & Scope
Owns the integration contract between external access-management vendors and WorkInSync:
the authentication scheme, the check-in/out API, the SFTP file-exchange procedure, and the
mapping of swipe events to WorkInSync bookings.

Does **not** own: the bookings themselves (those are owned by [[modules/desk-management]],
[[modules/meeting-rooms]], [[modules/parking-management]], and [[modules/meal-management]] —
this module reads/creates them via the integration API), the physical access-card hardware
or readers (third-party vendor devices), or identity (auth is a client-specific
username/password issued per integration, NOT the `sso` module's Azure AD).

## Key Features
- **API-based integration (REST)**: external vendors push check-in/out events via `POST /integration/bookings/ci-co`. Regionally deployed — see API Endpoints for the `.com` and `.in` baseUrls
- **Bearer-token authentication**: a client-specific username/password is exchanged via `POST /auth/token` (HTTP Basic) for a short-lived Bearer access token (`expires_in: 172799`, ~48h); the token is re-fetched on expiry
- **Check-in / check-out to bookings**: `bookingStatus` of `SIGNED_IN` checks in (or creates+checks-in), `SIGNED_OUT` signs the employee out of an existing booking
- **`createBookingIfNotPresent` flag**: when true, creates an office booking for employees who scan in without one, based on scan time + end time (flag location/scope not documented — see Open Questions)
- **RFID card support**: the `rfid` field (added in v1.2, Jul 2024) allows lookup by card number; `filter` can be left blank when `rfid` is supplied
- **Employee resolution by `filter`**: accepts EmployeeID, EmployeeName, or EmployeeEmailID
- **File-based integration (SFTP)**: an alternative mode (since Feb 2025) where clients push CSV swipe-data files to an SFTP server on a configured frequency, instead of real-time API calls. Setup requires SSH key, IP whitelisting, optional encryption, and a file-frequency agreement
- **Anomaly + utilization reporting (file-based mode)**: highlights employees who entered without a booking; optional configs to reject entry without a booking or auto-create one; resource-utilization reports for admins

## Data Entities Used
- [[entities/booking]] — consumed and optionally created via the integration; the booking itself is owned by the relevant booking module (desk / meeting-rooms / parking / meal)

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
| POST | `{baseUrl}/auth/token` | Exchange client credentials for a Bearer access token | `Authorization: Basic <base64(client_id:client_secret)>`, form `grant_type=client_credentials` |
| POST | `{baseUrl}/integration/bookings/ci-co` | Record a check-in or check-out event against a booking | `Authorization: Bearer <token>` |

**Auth response**: `{ "access_token": "<token>", "token_type": "Bearer", "expires_in": 172799 }`

**ci-co request fields:**

| Field | Format | Required | Description | Constraints |
|---|---|---|---|---|
| `filter` | String | ✓ | EmployeeID / EmployeeName / EmployeeEmailID | Max 50; unique per employee; may be blank if `rfid` is passed |
| `officeName` | String | (one of office identifiers) | Office where the action was performed | Max 100 |
| `bookingStatus` | String | ✓ | `SIGNED_IN` or `SIGNED_OUT` | Max 50 |
| `epochTime` | Long | ✓ | Timestamp of the action | Epoch milliseconds |
| `premiseId` | String | (one of office identifiers) | **⚠️ semantics differ between global and IND docs — see Open Questions** | Max 50 |
| `readerId` | String | (one of office identifiers) | Device ID at the entry point | Max 50; reader→office/floor mapping is a one-time setup |
| `rfid` | string | (alt to filter) | Card identifier | Max 50; requires RFID→employee mapping |

_Note: one of `readerId` / `premiseId` / `officeName` must be passed to identify the office._

**ci-co response fields:**

| Field | Format | Description |
|---|---|---|
| `status` | Integer | API status code (200 = success, 1001 = internal failure) |
| `data` | UUID | Booking Id (Max 50) |
| `message` | String | Success / failure message |

_Note: HTTP status is 200 on both success and internal failure; the `status` field in the body distinguishes them (200 vs 1001). HTTP 401 is returned only when the Authorization header is missing. Sample cURLs in the source carry sample auth tokens and base64 credentials — represented here as `Bearer <token>` / `Basic <base64(client_id:client_secret)>` placeholders per the wiki's no-tokens rule._

## Key Configurations
(none documented — none of the four source docs specify PMS config properties for this module. The `createBookingIfNotPresent` flag is referenced but its configuration location is not stated — see Open Questions)

## Open Questions
- ⚠️ **`premiseId` semantics contradict between the two API docs.** The global doc and the IND doc describe the same field with mutually incompatible meanings:
  - Global (`access-mgmt-integration-api-based`): *"The unique ID associated with the location where the action was performed. It may be an office or specific floor location."*
  - IND (`access-mgmt-integration-api-based-ind`): *"Type of booking that is requested ... Possible Values OFFICE, PARKING, PARKING_TWO, PARKING_FOUR, MEALS, MEETING"*
  Same field name, incompatible semantics. **Do not select an interpretation — engineering must clarify which `premiseId` semantic is canonical.**
- ⚠️ **Dependency grounding uncertainty** — the four dependency modules are inferred from the IND doc's premiseId enum (OFFICE, PARKING, MEALS, MEETING). The global doc's premiseId semantics (location identifier, not booking type) contradict this. If the global doc is correct, the actual module dependencies may differ. Engineering should clarify which premiseId semantic is canonical.
- ⚠️ **Regional API split** — `api.moveinsync.com` (global) vs `api.moveinsync.in` (IND). The IND doc's title says "IND Region [MUM]" ("MUM" presumably Mumbai), but the doc covers the `.in` region broadly. Why the MUM-specific title? Clients must use the correct regional baseUrl.
- ⚠️ **File-based mode is incompletely documented.** The file-based source (`access-mgmt-integration-file-based`) has empty "File format" and "Report insights" sections — the actual CSV schema and report contents are absent. The SFTP setup procedure is documented, but the data format is not. A consumer cannot implement the file push from this source alone.
- **`createBookingIfNotPresent` flag** is referenced in the API docs but its configuration location/scope (PMS config? per-client? per-office?) is not documented.
- **API Gateway design topics deferred by source** — the source notes throttling, fault tolerance, secure data exchange, error logging "need to be discussed in further detail" (global doc page 2). These are unspecified.
- **Documentation-hygiene observation** — the global and IND API docs share identical Version Control histories (same authors, approval dates, and descriptions at v1.0/1.1/1.2), suggesting the IND doc was branched/copied from the global rather than maintained independently. Not load-bearing for consumers, but a sign the two may drift.
- **No PMS configurations** documented for this module in any source.
- **Module owner not named** — authors across the four docs: Rahul Agrawal (API v1.0), Binoy Dedhia (API v1.1), Aditya Dutta (API v1.2 + File-based v1.0); approver Ujjwal Trivedi throughout. No owning team stated.

## Last Updated
2025-02-10 — _Source: [[sources/access-mgmt-integration-api-based]], [[sources/access-mgmt-integration-api-based-ind]], [[sources/access-mgmt-integration-file-based]]_
