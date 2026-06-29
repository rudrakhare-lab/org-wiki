---
type: source
ingested: 2026-06-29
doc_type: misc
sources_bundle: true
---

# Source Summary — SE Runbook: Parking Topic

> This page summarises the parking-related source documents distilled from
> `/tmp/parking_inputs.md` (Phase D of the SE runbook ingest series). Documents
> are from the team's "Conwo WorkInSync Docs" Google Drive, SE / implementation
> engineering authorship.

## Source Documents Covered

| Doc Title | Raw File | Date | Author(s) |
|-----------|----------|------|-----------|
| Parking Management PRD v1.2 | `raw/se-runbook/crawl/files/1KNzsoHARm84sNMurJ8EF2ksQLT88sOGNSp2OBAqcasM.docx` | 2022-03-30 | Jovil Nazareth, Binoy Dedhia |
| Dynamic Policy for Parking v1.3 | `raw/se-runbook/crawl/files/1liCPdzb7IIMbdWiLD3nBaEkyVGU4Ojg9K3Uvng63Qqo.docx` | 2025-10-22 | Aditya Dutta / Ujjwal Trivedi |
| Parking Technical Document v1.0 | `raw/se-runbook/crawl/files/1R1jA2bHvXtkT6uX2FEqVe3GuWEpgunDq8Ug-kfy7cfU.docx` | 2022-10-04 | Binoy Dedhia / Ujjwal Trivedi |
| WorkInSync Parking Checkin Integration v1.1 | `raw/se-runbook/crawl/files/1AxlT1NHtE4_eXXmzKu30Bo-uuf0agor_HbOHRm0fydc.docx` | 2022-06-07 | Binoy Dedhia / Ujjwal Trivedi |
| Vehicle Creation Handover | `raw/se-runbook/crawl/files/1f07HXrN6CHd5yCYvMIECVRsoD6yTIBlsJQeTU7sEP1I.docx` | undated | unknown |
| Parking Tag Creation | `raw/se-runbook/crawl/files/1mMSOXCgRID30nmg5jTm9ZoL6jQSLuR7OisW-YCeU_I8.docx` | undated | unknown |
| Download QR code for Level | `raw/se-runbook/crawl/files/1bUvokV-S8Y0_iwv_FPTezrHOF49ab4DFjfZCXXjueGk.docx` | undated | unknown |
| WorkInSync Parking Setup For Implementation Team | `raw/se-runbook/crawl/files/1VNM_iWrosoZJlr7lS1B02gQ2T7Yy97h0spD0L6MeNSA.docx` | undated | unknown |

**Skipped (noise / out of scope):**
- "Visitor Management PRD" — visitor topic, not parking
- "Discovery questions to ask" — visitor-specific (`visitor*`, `emailListTo*`, `formsMetaData*`, `sendInvite*` props); all in section D flagged as VISITOR service
- Release notes section B — empty in inputs file
- Decks section C — empty in inputs file
- "WorkInSync Check In Integration document" (docx,7014ch) — generic check-in integration, not parking-specific; covered by access-management module

## Key Takeaways

- **Parking dynamic policies** are the primary operational complexity: dual mapping
  (employee tag + slot tag must match), `BLOCK_HOTSEAT` nuance, and the exact `Yes`/`Null`/
  blank semantics in bulk upload files.
- **Tag creation is SE-only via API** (`POST /mis-floor-plan/api/<BUID>/tags`); the admin
  then uses the resulting tags in bulk-upload templates.
- **Vehicle sub-types** (SEDAN, SUV, etc.) are distinct from the generic CAR/BIKE
  classification — sub-types live in `mis-floor-plan` and are linked to both the floor plan
  and the PMS config `vehicleCreationDuringParkingFor`.
- **QR code generation** uses the `mis-security-guard/seat/generate-qr-seat-bulk` endpoint;
  `entityType=LEVEL` generates bulk-level codes, `entityType=PARKING` generates per-slot codes.
- **Parking integration** (checkin-integration doc): third-party hardware (boom barriers,
  access cards) integrates via Bearer-token API. Key endpoint: `GetParkingBookingDetails`
  (confirm booking existence) + `ParkingCheckIn` (perform check-in). See details below.
- **Client discovery checklist** (from "Parking Setup For Implementation Team") covers
  vehicle types, check-in mode, floor plan type, waitlist, advance booking days, tags —
  SE team runs this before implementation.
- **New slots are not self-serve**: clients email the MoveInSync team with office/zone/level/
  slot details; MIS adds them from the backend.
- **Beta host warning**: vehicle creation and tag creation docs show `wis-premise-beta.workinsync.io`
  — production host must be confirmed before live use.

## Modules Mentioned

- [[modules/parking-management]] — primary module
- [[modules/tags-desk-parking]] — shared tag engine

## Entities Mentioned

- `parking-slot` — sub-type (SEDAN, SUV) is a property of the slot entity
- `parking-booking` — check-in confirmed via integration API returns bookingId

## Decisions Extracted

None extracted — documents are operational SOPs and technical references, not architecture
decisions.

## Config Properties Documented (genuine parking/vehicle props only)

| Property | Service | Source doc | What the doc says |
|----------|---------|------------|-------------------|
| `vehicleCreationDuringParkingFor` | EMP-EXP-COMMON-CONFIG (both servers) | Vehicle Creation Handover | Controls which vehicle types are offered; valid values: `["CAR","BIKE"]`, `["CAR"]`, `["BIKE"]`, `[]` |

All other properties listed in section D of the inputs (`visitor*`, `emailListTo*`,
`formsMetaData*`, `recordCheckInOutViaAccessCardAPI`, `lastSwipeAsCheckoutTimeForBUID`)
are **VISITOR service or access-management props, not parking** — skipped per task instructions.

## Integration API Reference (from Parking Checkin Integration v1.1)

**Authentication:**
```
POST {baseUrl}/auth/token
Authorization: Basic <base64(username:password)>
grant_type=client_credentials
→ returns { "access_token": "<token>", "token_type": "bearer", "expires_in": 172799 }
```

**GetParkingBookingDetails** — confirm whether an employee has a booking:

Request fields: `EmployeeNumber` (required), `VehicleRegistrationNo`, `Date`
(format: `dd-MMM-yyyy` or `MM-dd-yyyy`), `ScanTime` (`HH:mm` or `HH:mm:ss`),
`DetectorID` (identifies office+zone+level), `Email`, `RFID/CardNo`, `PhoneNo`.

Response fields: `BookingID`, `EmployeeNumber`, `EmployeeName`, `CheckInTime`, `CheckOutTime`,
`OfficeName`, `ParkingZoneName`, `ParkingLevelName`, `ParkingSlotName`,
`VehicleRegistrationNo`, `VehicleType`, `Email`, `RFID/CardNo`, `PhoneNo`.

**ParkingCheckIn** — perform check-in for a booking:

Required fields: `EmployeeNumber`, `Date`, `ScanTime`, `EndTime` (required only when no
prior booking exists — system can create a booking on-the-fly), `DetectorID`.
Optional: `VehicleRegistrationNo`.

> ⚠️ Integration API is used by third-party hardware vendors (boom barriers, access cards),
> not by end users. Credentials are client-specific and shared by WorkInSync.

## Secrets Redacted

**3 JWT tokens** found in the source documents and redacted in all runbook pages:
- `<HS512 JWT — redacted>` (a `wisservices` `x-wis-token`) —
  appeared in Vehicle Creation Handover (3 occurrences in `x-wis-token` headers)
  and in QR code download doc (2 occurrences in `x-wis-token` headers).
  All replaced with `<token>` in runbook pages.
- `<RS256 JWT — redacted>` — partial token in an authentication-response
  example in the parking integration doc. Replaced with `<token>` in this summary.

Total redactions: **5 individual token occurrences** across 3 source files.

## Wiki Pages Created / Updated

- **Created:** [[runbooks/parking-dynamic-policy]]
- **Created:** [[runbooks/parking-tag-and-vehicle-setup]]
- **Created:** [[sources/se-runbook-parking]] (this page)
- **Updated:** [[modules/parking-management]] — added integration API endpoints, vehicle
  sub-type API details, SE setup checklist, related runbooks; bumped `last_updated`
- **Updated:** [[configs/emp-experience-common]] — filled `vehicleCreationDuringParkingFor`
  description with valid-values enumeration from Vehicle Creation Handover doc

## Open Questions

- No `raw_path` for "Parking Tag Creation" or "Download QR code for Level" source files —
  the crawled paths are confirmed above but the Drive doc titles are generic. If these
  are surfaced as standalone wiki sources later, update `raw_paths` in the runbook frontmatter.
- Production hostname for sub-type and tag-creation APIs (docs show
  `wis-premise-beta.workinsync.io` and `wis-premise.workinsync.io`) — confirm the correct
  production endpoint with the owning team before SE use.
- `vehicleCreationDuringParkingFor` default: the source gives valid value formats but does
  not state a default. Leaving blank in the config page pending confirmation.
