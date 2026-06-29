---
type: runbook
module: parking-management
team: SE (Service Engineering)
status: active
last_updated: 2026-06-25
source: "[[sources/se-runbook-ets-office-premise]]"
raw_path: raw/se-runbook/WIS-Configurations-ETS-EmployeeApp-GuardApp-SanitisationApp.docx
---

# Runbook — Parking Premise Setup

> SE procedure to **create a parking premise, validate it, and add booking capacity**, using the **WIS-Configurations Google sheet** (`1FyWuDnS…`) + **Postman**.
> ⚠️ Every concrete value below (`tata-TCPOC`, `randstad-RSInd`, GUIDs like `9f8eff3e-…`, premiseNames like `TATA Consumer_2WH`) is an **EXAMPLE / placeholder** — replace with the client's actual values. Nothing here is literal config.
> _Source: [[sources/se-runbook-ets-office-premise]] (raw doc sections 11–13)_

## Purpose & Scope

Covers the Parking-premise slice of WorkInSync premise configuration: prerequisites (TO ticket, existing office premise), creating a 2-wheeler or 4-wheeler parking premise, validating it, and adding/validating booking capacity. Floor-plan upload, guard user creation, and other downstream steps are separate runbooks.

## Prerequisites

1. **Raise a TO ticket** to get the Parking option enabled for the specific Site — this must happen before any of the steps below.
2. The **office premise** for the site must already exist in the backend (created via [[runbooks/ets-office-premise-setup]]). You will need the office's `premiseId` as the `parentPremise` value.
3. Have the following data ready for the WIS-Configurations sheet submission (refer to "How to find PremiseID?" guide linked from the source for how to retrieve these):
   - `parentPremise` (office `premiseId`)
   - `geoCode`
   - `techparkId`
   - `buIdOfficeGuid`
   - `City`, `Country`

## Configuration Flow (where this fits)

`Office Premise creation → Add Capacity to Office → Parking Premise → Parking Capacity → Floor premise → Upload Floor → Guard User → Amenity → Seat Sanitization → Meal Booking.`
Each uses **G-Tool and/or Postman**. **This runbook = Parking premise + capacity.**

## Step-by-step

### A — Create the parking premise

1. **Confirm the vehicle type required** (from the TO ticket):
   - Two-wheeler parking → `premiseType: 6`
   - Four-wheeler parking → `premiseType: 3`
   - Both types can be created as separate rows in the same sheet submission if required.

2. **Fill the WIS-Configurations sheet** (`https://docs.google.com/spreadsheets/d/1FyWuDnS-L6wB9ZBqTvLwsk6qwQEBWIyTtMaHJ9PojlU/edit#gid=0`) and click **Submit**. Columns:

   | Column | Value | Note |
   |--------|-------|------|
   | `Buid` | client BUID | e.g. `tata-TCPOC` (example — replace with the client's) |
   | `Service/Feature` | `Parking/Floor plan` | exact value from source |
   | `premiseType` | `6` or `3` | **6 = 2-wheeler, 3 = 4-wheeler** |
   | `parentPremise` | office `premiseId` | e.g. `26ff30ff-b3fc-4bee-af65-5c4275c864ff` (example — replace with the client's) |
   | `premiseName` | `2WH` or `4WH` | name for the parking premise |
   | `geoCode` | office geocode | e.g. `13.051826,77.595410` (example — replace with the client's) |
   | `techparkId` | tech park ID | retrieve from "How to find PremiseID?" |
   | `buIdOfficeGuid` | BUID office GUID | e.g. `081ae46d-82b…` (example — replace with the client's) |
   | `City` | city name | e.g. `Bangalore` (example — replace with the client's) |
   | `Country` | country name | e.g. `INDIA` (example — replace with the client's) |

### B — Validate the premise

`GET https://mis-security.moveinsync.com/mis-security-guard/premise/buid/<BUID>` _(example BUID: `tata-TCPOC`)_

- Search (`Ctrl+F`) using the **office `premiseId`** in the response to locate the parking premise entry.
- Confirm the parking `premiseName` appears (`TATA Consumer_2WH` / `TATA Consumer_4WH` in the example) and `premiseType` matches (`"6"` for 2-wheeler, `"3"` for 4-wheeler).
- **Copy the parking `premiseId`** — you need it for capacity (Step C). E.g. `9f8eff3e-de7c-41bf-afc7-35d0f17a1567` (example — replace with the client's).

### C — Add capacity to parking

1. **Retrieve the parking `premiseId`** (if not already noted):
   `GET https://mis-security.moveinsync.com/mis-security-guard/premise/buid/<BUID>` → search for `"premiseType": "6"` (or `"3"`) → copy the `premiseId` for the target parking premise.

2. **Fill the WIS-Configurations sheet** (`https://docs.google.com/spreadsheets/d/1FyWuDnS-L6wB9ZBqTvLwsk6qwQEBWIyTtMaHJ9PojlU/edit#gid=0`) and click **Submit**. Columns:

   | Column | Value | Note |
   |--------|-------|------|
   | `Buid` | client BUID | e.g. `randstad-RSInd` (example — replace with the client's) |
   | `Service/Feature` | `premise capacity` | exact value |
   | `premiseId` | parking `premiseId` from step 1 | enter 2-wheeler OR 4-wheeler parking premiseId |
   | `capacity` | number as per requirement | e.g. `500` (example — replace with the client's) |
   | `startDate` | `2020-08-01` | example date — replace with the client's |
   | `endDate` | `2023-12-31` | example date — replace with the client's |
   | `startMinOfDay` | `0` | start of day in minutes (full-day window) |
   | `endMinOfDay` | `1439` | end of day in minutes (full-day window) |

### D — Validate capacity

`GET https://mis-security.moveinsync.com/mis-security-guard/premise-capcity/buid/<BUID>?endTime=<epoch_ms>&startTime=<epoch_ms>` _(example: `tata-TCPOC?endTime=1605589580000&startTime=1605416780000` — replace with the client's BUID and appropriate epoch timestamps)_

- Search (`Ctrl+F`) the response using the parking `premiseId`.
- Confirm the capacity record appears with the expected `capacity`, `startDate`, `endDate`, `startMinOfDay: 0`, `endMinOfDay: 1439`.

## Screenshots (transcribed; originals in the vault `raw/se-runbook/images/`)

- `sec11_img013` — **WIS-Configurations sheet** with two parking premise rows submitted for `tata-TCPOC`: one `premiseType: 6` (2-wheeler, `premiseName: TATA Consumer_2WH`) and one `premiseType: 3` (4-wheeler, `premiseName: TATA Consumer_4WH`), both sharing the same `parentPremise` GUID and geocode `13.051826,77.595410`; the **Submit** button is visible at right.
- `sec12_img014` — Postman **GET** `https://mis-security.moveinsync.com/mis-security-guard/premise/buid/tata-TCPOC` (Status: 200 OK); response shows a parking premise object with `"premiseType": "6"`, `"parentPremise": "26ff30ff-b3fc-4bee-af65-5c4275c864ff"`, `"premiseName": "TATA Consumer_2W"`, `"buid": ["tata-TCPOC"]`, `"geoCode": "13.051826,77.595410"`. Annotation: "search with office premiseID & check for PremiseType".
- `sec13_img015` — Postman **GET** same URL; response with search filter `"premiseType": "6"` active — annotation points to `"premiseId": "9f8eff3e-de7c-41bf-afc7-35d0f17a1567"` and says "Copy this 2Wheeler parking PremiseID".
- `sec13_img016` — **WIS-Configurations sheet** capacity row: `Buid: tata-TCPOC`, `Service/Feature: premise capacity`, `premiseId: 9f8eff3e-de7c-41bf-afc7-35d0f17a1567`, `capacity: 500`, `startDate: 2020-08-01`, `endDate: 2023-12-31`, `startMinOfDay: 0`, `endMinOfDay: 1439`; **Submit** button visible.
- `sec13_img017` — Postman **GET** `https://mis-security.moveinsync.com/mis-security-guard/premise-capcity/buid/tata-TCPOC?endTime=1605589580000&startTime=1605416780000` (Status: 200 OK); response shows two capacity objects each with `premiseId: 9f8eff3e-…`, `capacity: 480`, `startDate: 2020-08-01`, `endDate: 2023-12-31`, `startMinOfDay: 0`, `endMinOfDay: 1439`, `shiftGuid: null`. Annotation: "Check here for the submitted capacity."
- `sec13_img018` — **Floor-plan upload introduction** (prerequisite checklist: Site URL, floor name, .svg/.dwg + .json files). _Belongs to `runbooks/floor-plan-upload` — section 13's source continues into the next topic at this image._
- `sec13_img019` — WIS site Desk Management screen showing an existing **grid-based floor plan** in Desk Allocation. _Floor-plan-upload topic; out of scope for this runbook._
- `sec13_img020` — WIS-MIS site Desk Management screen showing the **"Upload Seats" button** (no floor plan present). _Floor-plan-upload topic; out of scope for this runbook._
- `sec13_img021` — Excel file screenshot showing seat UUIDs with duplicate detection (highlighted duplicates, null seat names). _Floor-plan-upload topic; out of scope for this runbook._

## Validation checklist

- [ ] TO ticket raised and Parking option confirmed enabled for the site
- [ ] Parking premise visible via `GET …/premise/buid/<BUID>` — confirm `premiseName`, `premiseType` (6 or 3), and `parentPremise` matches the office premiseId
- [ ] Parking `premiseId` copied correctly before proceeding to capacity step
- [ ] Capacity visible via `GET …/premise-capcity/buid/<BUID>` — Ctrl+F parking `premiseId` confirms capacity record present

## Notes & Gotchas

- **Raise the TO ticket first.** The source is explicit: parking must be explicitly enabled per site before any configuration can proceed.
- **`premiseType` values for parking** — in the example (sheet `sec11_img013` and the validation responses), `premiseType 6` is used for the 2-wheeler row (`TATA Consumer_2WH`) and `3` for the 4-wheeler row (`TATA Consumer_4WH`). ⚠️ This 6↔2-wheeler / 3↔4-wheeler correspondence is **read from the example screenshots — the doc does not state it as a definitional rule** — confirm it is the standard convention with the owning team before relying on it. (Office premise type = `2`; see [[runbooks/ets-office-premise-setup]].)
- **`parentPremise` must be the office `premiseId`**, not blank. Unlike the office premise creation step (where `parentPremise` is left blank), the parking premise always requires a parent.
- **The `premise-capcity` URL path is misspelled in the source** (missing a letter in "capacity"). Preserve the exact spelling — it is the live endpoint path: `…/mis-security-guard/premise-capcity/buid/…`.
- **`startMinOfDay: 0` and `endMinOfDay: 1439`** are the full-day window values from the source example. The source does not describe varying these — use as-is unless the client requires shift-based windows.
- **Separate capacity submissions per vehicle type.** Each parking premise (2-wheeler and 4-wheeler) has its own `premiseId` — submit capacity separately for each.
- The WIS-Configurations sheet URL `1FyWuDnS-L6wB9ZBqTvLwsk6qwQEBWIyTtMaHJ9PojlU` is the same sheet used across all premise operations (office, parking, capacity).
- **Section 13 source continues into floor-plan upload steps** (Cases 1–3) after Step-3. Those steps belong to `runbooks/floor-plan-upload` and are not covered here.

## Related

- Module: [[modules/parking-management]]
- Upstream runbook: [[runbooks/ets-office-premise-setup]] (office premise must exist first; this runbook consumes the office `premiseId` as `parentPremise`)
- Tool: WIS-Configurations sheet (`1FyWuDnS…`)
- Downstream runbooks: [[runbooks/parking-tag-and-vehicle-setup]] (vehicle sub-type + QR codes), [[runbooks/parking-dynamic-policy]] (tag-based access policy), `runbooks/floor-plan-upload`, `runbooks/guard-user-creation` (pending ingest)

## Related Jira

— none cited in sections 11–13.

## Last Updated

2026-06-25 — source: [[sources/se-runbook-ets-office-premise]] (raw: `raw/se-runbook/WIS-Configurations-ETS-EmployeeApp-GuardApp-SanitisationApp.docx`, sections 11–13)
