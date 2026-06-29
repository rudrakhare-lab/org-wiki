---
type: runbook
module: parking-management
team: SE (Service Engineering)
status: active
last_updated: 2022-10-04
source: "[[sources/se-runbook-parking]]"
raw_paths:
  - raw/se-runbook/crawl/files/1f07HXrN6CHd5yCYvMIECVRsoD6yTIBlsJQeTU7sEP1I.docx
  - raw/se-runbook/crawl/files/1bUvokV-S8Y0_iwv_FPTezrHOF49ab4DFjfZCXXjueGk.docx
  - raw/se-runbook/crawl/files/1VNM_iWrosoZJlr7lS1B02gQ2T7Yy97h0spD0L6MeNSA.docx
---

# Runbook — Parking Vehicle Sub-type Setup & QR Code Generation

> SE / Implementation procedure for:
> 1. Configuring vehicle sub-types (CAR/BIKE classifications) on the backend
> 2. Mapping sub-types to a BUID
> 3. Generating and downloading QR codes for parking levels and slots
>
> ⚠️ All BUIDs (`wfo-MIS`, `wfo-Mis`), GUIDs (`19b885c7-…`, `61acd53a-…`),
> `seatTypeId` values (`35`, `36`), and example host `wis-premise-beta.workinsync.io`
> are **placeholders** from the source docs — replace with the client's actual values.
>
> _Sources: [[sources/se-runbook-parking]] — "Vehicle Creation Handover" and
> "Download QR code for Level" docs_

## Purpose & Scope

Covers:
- Adding parking vehicle sub-types to the WIS system (SEDAN, SUV, etc.)
- Mapping those sub-types to a client BUID
- Downloading QR codes (bulk) for parking levels and individual slots

**Not covered here:** dynamic policy tag assignment (→ [[runbooks/parking-dynamic-policy]]),
premise creation (→ [[runbooks/parking-premise-setup]]).

## Context: `vehicleCreationDuringParkingFor`

The PMS config property `vehicleCreationDuringParkingFor` (service: `EMP-EXP-COMMON-CONFIG`,
both servers) controls which vehicle types are offered during parking booking. Accepted values:
`["CAR","BIKE"]`, `["CAR"]`, `["BIKE"]`, or `[]`.

Before setting up sub-types, confirm with the client what vehicle types they require:
- **Car parking only**: `["CAR"]`
- **Bike parking only**: `["BIKE"]`
- **Both**: `["CAR","BIKE"]`

If the floor plan uses specific vehicle-build differentiation (Sedan vs. SUV), the sub-type
API steps below are also required. If the client only needs CAR/BIKE with no further
differentiation, sub-types may not be needed.

## Part A — Vehicle Sub-type Setup

### Step A1 — List existing sub-types

Verify what sub-types already exist in the system before adding new ones.

```
GET https://<wis-premise-host>/mis-floor-plan/seat/seat-types?entityType=PARKING&buid=<BUID>
accept: */*
Content-Type: application/json
x-wis-token: <token>
```

- If no BUID is passed, returns all sub-types system-wide.
- If BUID is passed, returns only sub-types mapped to that BUID.

> ⚠️ **Do not create duplicate `seatTypeName` values.** Duplicates break the floor plan in
> the CAD viewer tool and corrupt the floor plan upload. Verify the name does not already
> exist before proceeding.

### Step A2 — Add sub-types to the system

```
POST https://<wis-premise-host>/mis-floor-plan/seat/seat-types?entityType=PARKING
accept: */*
Content-Type: application/json
x-wis-token: <token>

["SEDAN", "SUV"]
```

Pass only the string names. Response returns the created sub-types with their assigned
`seatTypeId` values:

```json
[
  { "seatTypeId": <id-1>, "seatTypeName": "SUV"   },
  { "seatTypeId": <id-2>, "seatTypeName": "SEDAN" }
]
```

**Copy the `seatTypeId` values** — required for Step A3.

> ⚠️ For **BIKE slots**: when uploading a floor plan without DIY, use sub-type `SubType: -1`
> in the floor plan file. Bike slots use `-1` as a fixed sentinel value, not a named sub-type.

### Step A3 — Map sub-types to the client BUID

```
POST https://<wis-premise-host>/mis-floor-plan/seat/sub-types?buid=<BUID>
accept: */*
Content-Type: application/json
x-wis-token: <token>

[<seatTypeId-1>, <seatTypeId-2>]
```

Pass the `seatTypeId` integers from Step A2. This associates the sub-types with the BUID
so they appear in the floor plan and bulk-upload templates.

### Step A4 — Verify mapping

```
GET https://<wis-premise-host>/mis-floor-plan/seat/seat-types?entityType=PARKING&buid=<BUID>
```

Confirm the sub-types from Step A2 appear in the response for the target BUID.

### Floor plan integration

If the client uses a **DIY floor plan**: sub-type selection appears in the UI during
floor plan creation — no additional file column required.

If the client uses a **non-DIY floor plan upload**: add a column `SubType` to the floor
plan upload file with the `seatTypeId` for each slot row.

| Vehicle | SubType column value |
|---------|---------------------|
| SEDAN | `<seatTypeId for SEDAN>` |
| SUV | `<seatTypeId for SUV>` |
| BIKE | `-1` (fixed sentinel) |

**Reference floor plan sheets** (from source — internal links):
- Hybrid floor plan: `https://docs.google.com/spreadsheets/d/1Y93LZYVCgAM0b_yXcwXvJ0BDB1pUvuBejpA5TcVq04M/`
- 4-wheeler parking sheet: `https://docs.google.com/spreadsheets/d/1q26Xfuf1OLQX8tCSREms8ZhvyWV1O6rfKVyEipZLuag/`
- 2-wheeler parking sheet: `https://docs.google.com/spreadsheets/d/1iOuaWKpRm1ZDMvvaZdyqcaw4CF7S5yeSZVgjmfZe63U/`

## Part B — QR Code Generation

QR codes can be generated in bulk for an entire level or for individual parking slots.
These codes are printed and affixed to the physical parking spot, allowing employees to
scan them via the MIS app to check in.

**When to use:**
- Clients who select the **"Scan QR"** check-in mode (see [[runbooks/parking-premise-setup]]
  prerequisites — check-in mode is a setup decision)
- QR codes are associated with the `floorPremiseId` (level premise) or individual slot
  premise

### Step B1 — Download QR codes for a Level (bulk)

Generates one QR code per slot on the entire level. Print and affix to the entrance/level
signage.

```
GET https://mis-security.moveinsync.com/mis-security-guard/seat/generate-qr-seat-bulk
    ?entityType=LEVEL
    &floorPremiseId=<level-premise-id>
x-wis-token: <token>
x-tenant-id: <tenant-id>
```

- `floorPremiseId`: the premise GUID for the **level** (floor premise, not the parking
  premise). Retrieve from
  `GET https://mis-security.moveinsync.com/mis-security-guard/premise/buid/<BUID>`.
- `x-tenant-id`: the client's tenant identifier (example in source: `wfo-MIS` — replace
  with the client's actual value).

### Step B2 — Download QR codes for individual Slots

Generates QR codes for individual parking slots. Use `entityType=PARKING`.

```
GET https://mis-security.moveinsync.com/mis-security-guard/seat/generate-qr-seat-bulk
    ?entityType=PARKING
    &floorPremiseId=<slot-premise-id>
x-wis-token: <token>
x-tenant-id: <tenant-id>
```

> ⚠️ Note: despite the parameter name being `floorPremiseId`, for `entityType=PARKING`
> this refers to the **slot's** premise ID, not the level. Verify you are passing the
> correct GUID for the intended granularity.

## Client Discovery Questions

Before implementation, confirm the following with the client
(from "Parking Setup For Implementation Team"):

| Question | Determines |
|----------|-----------|
| Car-only or also bike parking? | `vehicleCreationDuringParkingFor` value; whether to create `BIKE` sub-type |
| Number of zones and levels | Floor plan scope |
| UI layout: Auto-allocate / Grid / Floor plan? | Implementation effort (floor plan = ~3 days/level + agreed price) |
| Check-in mode: UI button / Digipass / QR scan / Hardware integration? | Whether QR codes are needed (Part B above) |
| Reminder notifications? | `parkingReminderNotificationEnabled` / `parkingMailNotificationMinutes` |
| Auto-release unretrieved slots? | Booking auto-release config |
| Waitlist? | `enableWaitlistBooking` / `enableJoinAllWaitlist` |
| How many days advance booking? | `parkingScheduleCutoff` |
| Dedicated slots for categories (PWD, Executive)? | Dynamic policy setup (→ [[runbooks/parking-dynamic-policy]]) |
| Capture vehicle registration number? | `showRegistrationNumberInputFieldForParking` (PII — recommend not collecting unless mandatory) |
| Vehicle type restrictions per slot (EV, SUV-only)? | Sub-type + dynamic policy setup |

**SE actions after discovery:**
1. Create an SE ticket with slot names and zone/level mapping (SE adds slots from backend).
2. Enable the booking layout type (Floor plan, Auto-allocate, or Grid).
3. For floor plan: raise a separate SE ticket for the DWG-to-floor-plan upload.
4. For tags: raise an SE ticket to create the required tags (then admin uploads the tagging files).

## Validation Checklist

- [ ] `vehicleCreationDuringParkingFor` PMS config set correctly for the client
- [ ] Sub-types created (Step A2) — no duplicates; names confirmed with client
- [ ] Sub-types mapped to BUID (Step A3) — verified via GET
- [ ] Floor plan file updated with `SubType` column if non-DIY upload
- [ ] QR codes generated and downloaded (if client uses QR scan check-in)
- [ ] QR codes printed and affixed at physical slots

## Notes & Gotchas

1. **Beta host in source**: the Vehicle Creation Handover doc uses
   `wis-premise-beta.workinsync.io` in its curls. Use the **production host** for live
   client setups unless explicitly instructed to use beta/staging.

2. **`seatTypeName` duplicates break floor plans** — the source explicitly warns:
   "Don't create duplicate seatTypeNames. It will be confusing while creating floor plan
   from cad viewer tool and floor plan will break." Always run Step A1 first.

3. **BIKE sub-type is always `-1`** in the floor plan file, regardless of any named BIKE
   sub-type in the system. This is a fixed sentinel — do not pass a `seatTypeId` for bikes
   in the floor plan file.

4. **QR and Digipass are separate check-in paths** — QR (physical codes on slots) vs.
   Digipass (QR generated on the employee's app, scanned by a guard). Both can coexist
   if the client wants flexibility. Document which the client is enabling in the SE ticket.

5. **`showSeparateDigipassForParking`** controls whether parking gets its own Digipass
   QR in the app (separate from the office check-in Digipass). Confirm with the client
   if they want a unified or separate Digipass experience.

## Related

- Module: [[modules/parking-management]]
- Premise setup (upstream): [[runbooks/parking-premise-setup]]
- Dynamic policy (tag assignment): [[runbooks/parking-dynamic-policy]]
- Config reference: [[configs/emp-experience-common]] (`vehicleCreationDuringParkingFor`,
  `vehicleCreationDuringParkingEnabled`, `parkingEnabled`, `parkingScheduleCutoff`, etc.)

## Last Updated

2026-06-29 — source: [[sources/se-runbook-parking]]
("Vehicle Creation Handover" undated, "Download QR code for Level" undated,
"Parking Setup For Implementation Team" undated)
