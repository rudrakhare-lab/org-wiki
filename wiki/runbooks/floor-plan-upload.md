---
type: runbook
module: floor-kiosk
team: SE (Service Engineering)
status: active
last_updated: 2026-06-25
source: "[[sources/se-runbook-ets-office-premise]]"
raw_path: raw/se-runbook/WIS-Configurations-ETS-EmployeeApp-GuardApp-SanitisationApp.docx
---

# Runbook — Floor Premise & Floor Plan Upload

## Purpose & Scope

Covers the full floor-plan onboarding process for a WorkInSync site:
1. Creating a floor premise record (premiseType 4) under an existing office premise.
2. Obtaining the resulting `premiseId` (FloorPremiseID).
3. Uploading the floor plan via one of three mutually-exclusive methods depending on the assets provided by the client.

Out of scope: guard user creation, parking premise setup, desk booking capacity configuration. Those are separate runbooks.

---

## Prerequisites

1. **Booking service prerequisite:** `seatValidation=true` must be set for the Booking service before floor-plan work begins (noted at the top of section 5 in the source).
2. The **office premise** for the site must already exist in the backend (created via [[runbooks/ets-office-premise-setup]]). You will need its `premiseId` as the `parentPremise` value when creating the floor premise.
3. Have the following data ready before using the WIS-Configurations sheet:
   - `parentPremise` — the office `premiseId` (retrieve via GET on the premise endpoint filtered by premiseType)
   - `geoCode` — the office's geocode (same geocode as the parent office)
   - `techparkId` — the office's techpark GUID
   - `buIdOfficeGuid` — the office's building GUID (note: the WIS-Configurations sheet header shows `buldOfficeGuid`; the source body text spells it `buIdOfficeGuid` — use whichever label the sheet displays; both appear in source)
   - `City`, `Country`
   - `premiseName` — the floor label to be visible in the frontend (e.g. "2nd Floor West Wing")
4. Decide which upload method applies to the client's assets (choose exactly one):
   - **Method A — File-based only:** client provides a floor plan file (SVG or similar) but no background image and no DIY JSON.
   - **Method B — Background image + file:** client provides a background image AND a floor plan file.
   - **Method C — DIY (JSON + SVG):** client's floor plan was built in the DIY Floor Planner and exported as a `.json` file + `.svg` file.
5. Collect the floor plan files before proceeding to the upload steps:
   - Site URL, floor name, `.svg`/`.dwg` + `.json` files (see `sec13_img018` — the prerequisite overview diagram for this process).

---

## Configuration Flow (where this fits)

```
ETS Office Premise Setup
    ↓
Parking Premise Setup (parallel, if applicable)
    ↓
Floor Premise Creation  ← THIS RUNBOOK (Step A)
    ↓
Collect FloorPremiseID  ← THIS RUNBOOK (Step B)
    ↓
Floor Plan Upload       ← THIS RUNBOOK (Step C, choose one method)
    ↓
Guard User Creation (separate runbook)
```

The three-box overview diagram (`sec13_img018`) shows this exact sequence: **Floor premise Creation → Collect FloorPremiseID → Plan Upload**.

---

## Step-by-step

### A — Create the floor premise

Use the **WIS-Configurations sheet** (Google Sheets):
`https://docs.google.com/spreadsheets/d/1FyWuDnS-L6wB9ZBqTvLwsk6qwQEBWIyTtMaHJ9PojlU/edit#gid=0`

Set `Service/Feature = Parking/Floor plan` and fill in all required columns:

| Column | Field | Value / Notes |
|--------|-------|---------------|
| Buid | client BUID | e.g. `tata-TCPOC` (example — replace with the client's) |
| Service/Feature | `Parking/Floor plan` | fixed value |
| premiseType | `4` | fixed value — floor premise type |
| parentPremise | office `premiseId` | e.g. `26ff30ff-b3fc-4bee-af65-5c4275c864ff` (example — replace with the client's) |
| premiseName | floor display name | e.g. `2nd Floor West Wing` (example — replace with the client's) |
| geoCode | office geocode | e.g. `13.051826,77.595410` (example — replace with the client's) |
| techparkId | office techpark GUID | e.g. `081ae46d-82b…` (example — replace with the client's) |
| buldOfficeGuid | office building GUID | e.g. `L0tataTC-POC$-…` (example — replace with the client's) |
| City | city name | e.g. `Bangalore` (example — replace with the client's) |
| Country | country name | e.g. `INDIA` (example — replace with the client's) |

Click **Submit** when all fields are filled.

_Source: `sec14_img022.png` — WIS-Configurations sheet showing a floor premise row for `tata-TCPOC` with `premiseType: 4`, `premiseName: 2nd Floor West Wing`, `parentPremise: 26ff30ff-b3fc-4bee-af65-5c4275c864ff`, `geoCode: 13.051826,77.59…`, `techparkId: 081ae46d-82b…`, `buldOfficeGuid: L0tataTC-POC$-…`, `City: Bangalore`, `Country: INDIA`; Submit button visible at right._

### B — Validate the premise and collect the FloorPremiseID

Use Postman, **GET** method, substituting the correct BUID:

```
GET https://mis-security.moveinsync.com/mis-security-guard/premise/buid/<BUID>
```

Example used in source: `https://mis-security.moveinsync.com/mis-security-guard/premise/buid/tata-TCPOC` (example — replace with the client's BUID).

In the response, filter for `"premiseType": "4"`. Copy and hold the matching `premiseId` — this is the **FloorPremiseID** needed for all upload steps below.

Example from source:
```json
{
  "premiseId": "a5fa16cd-05ec-4497-95e3-657b9ddaeeac",
  "premiseType": "4"
}
```
(example — replace with the client's)

---

### C — Floor plan upload (choose exactly ONE method)

### Method A — File-based upload only (`WITH_FLOOR_PLAN`)

Use when the client provides a floor plan file but no background image and no DIY JSON/SVG pair.

**Postman: POST**

```
POST https://mis-security.moveinsync.com/mis-security-guard/csv/upload/floorplan
     ?floorType=WITH_FLOOR_PLAN
     &forceUpdateFloorPlan=false
     &premiseId=<FloorPremiseID>
```

Example shown in source URL: `premiseId=25d7cb03-ff02-4e25-9ee8-9a95aced08f9` (example — replace with the client's FloorPremiseID from Step B).

**CRITICAL:** Do NOT click Send before adding the correct `premiseId` under **Params**.

Params tab — set three parameters:

| Key | Value |
|-----|-------|
| `floorType` | `WITH_FLOOR_PLAN` |
| `forceUpdateFloorPlan` | `false` |
| `premiseId` | `<FloorPremiseID>` (example — replace with the client's) |

Body tab — select **form-data**, then add:

| Key | Value |
|-----|-------|
| `file` | select the floor plan file |

Click **Send**.

_Source: `sec16_img023.png` — Postman Params tab showing `floorType=WITH_FLOOR_PLAN`, `forceUpdateFloorPlan=false`, `premiseId` (enabled, all three checkboxes checked). `sec16_img024.png` — Postman Body tab showing `form-data` selected and a single `file` field with a floor plan file attached (e.g. `DD.xlsx` shown in OCR — exact filename is client-specific); Send button visible._

> ⚠️ Casing note: Method A body key is `file` (lowercase) — confirmed in `sec16_img024.png`. Method B body key is `File` (capital F) — per `sec17_img026.png`. The casing difference is source-verbatim; do not normalize.

> ⚠️ The source states: "InCase of Floor plan Upload/REUPLOAD always keep `forceUpdateFloorPlan: false`" — this applies to initial uploads AND re-uploads.

---

### Method B — Background image + file upload (`WITH_BACKGROUND_IMAGE`)

Use when the client provides both a background image and a floor plan file.

**Postman: POST**

```
POST https://mis-security.moveinsync.com/mis-security-guard/csv/upload/floorplan
     ?floorType=WITH_BACKGROUND_IMAGE
     &forceUpdateFloorPlan=false
     &premiseId=<FloorPremiseID>
```

**CRITICAL:** Do NOT click Send before adding the correct `premiseId`.

Params tab — set three parameters:

| Key | Value |
|-----|-------|
| `floorType` | `WITH_BACKGROUND_IMAGE` |
| `forceUpdateFloorPlan` | `false` |
| `premiseId` | `<FloorPremiseID>` (example — replace with the client's) |

Example `premiseId` value shown in source: `a5fa16cd-05ec-4497-95e3-657b9ddaeeac` (example — replace with the client's).

Body tab — select **form-data**, then add:

| Key | Value |
|-----|-------|
| `File` | select the floor plan file |
| `floorBackgroungImage` | select the background image |

Note: `floorBackgroungImage` is the exact spelling used in the source — preserve verbatim.

Click **Send**.

_Source: `sec17_img025.png` — Postman Params tab showing the three parameters (`floorType=WITH_BACKGROUND_IMAGE`, `forceUpdateFloorPlan=false`, `premiseId=a5fa16cd-05ec-4497-95e3-657b9ddaeeac`). `sec17_img026.png` — Postman Body tab showing `form-data` selected with two fields: `File` (floor plan) and `floorBackgroungImage` (background image); Send button visible._

---

### Method C — DIY floor plan upload (JSON + SVG)

Use when the floor plan was built in the DIY Floor Planner tool and exported as one `.json` file and one `.svg` file.

**Postman: POST**

```
POST https://wis-premise.workinsync.io/mis-security-guard/csv/upload/layout/<FloorPremiseID>
     ?forceUpdateFloorPlan=false
     &wktDimensionInCm=100
```

Note: the `premiseId` appears as a **path parameter** in the URL (not a query param). Replace `<FloorPremiseID>` with the FloorPremiseID from Step B before clicking Send.

**CRITICAL:** Do NOT click Send without updating the premiseId in the URL. The source shows example URL:
`https://wis-premise.workinsync.io/mis-security-guard/csv/upload/layout/4a8de968-2a38-49b9-9b32-ef6983bdb130?forceUpdateFloorPlan=false&wktDimensionInCm=100`
(example — replace `4a8de968-2a38-49b9-9b32-ef6983bdb130` with the client's FloorPremiseID)

Fixed query parameters:

| Key | Value |
|-----|-------|
| `forceUpdateFloorPlan` | `false` |
| `wktDimensionInCm` | `100` |

Body tab — select **form-data**, then add:

| Key | Value |
|-----|-------|
| `floorImage` | select the `.svg` file — e.g. `TCI-I_GROUND_FLOOR_PLAn_file.svg` (example — replace with the client's; note the lowercase `n` in `PLAn` in the example is as shown in the source) |
| `floor` | select the `.json` file — e.g. `TCI-I_GROUND_FLOOR_PLAN_file.json` (example — replace with the client's) |

Click **Send**.

_Source: `sec18_img027.png` — Postman POST to `https://wis-premise.workinsync.io/mis-security-guard/csv/upload/layout/:premiseId?forceUpdateFloorPlan=false&wktDimensionInCm=100…`; Body tab in form-data mode showing two rows: `floorImage` → `TCI-I_GROUND_FLOOR_PLAn_file.svg` (Required) and `floor` → `TCI-I_GROUND_FLOOR_PLAN_file.json`; response Status 200 OK, Time 7.54s, Size 519B._

#### First-time DIY upload — additional URL check

For the **very first** DIY floor plan upload to a site, verify and update these URLs via Postman before or after the upload:

1. **Check current values** (GET):
```
GET https://empexp.moveinsync.com/employee-exp/<BUID>/configurations/common
```
Verify that `employeeFloorPlanUrl`, `adminFloorPlanUrl`, and `adminAssignmentFloorPlanUrl` are set.
Example used in source: `https://empexp.moveinsync.com/employee-exp/freshworks-FRPOC/configurations/common` (example — replace `freshworks-FRPOC` with the client's BUID)

2. **Update if missing or incorrect** (PUT):
```
PUT https://empexp.moveinsync.com/employee-exp/<BUID>/update-config?feature=common
```
Body (JSON):
```json
{
  "employeeFloorPlanUrl": "https://empexp.moveinsync.com/employee-exp/static/pages/page/#/employee-view",
  "adminFloorPlanUrl": "https://empexp.moveinsync.com/employee-exp/static/pages/page/#/admin-view",
  "adminAssignmentFloorPlanUrl": "https://empexp.moveinsync.com/employee-exp/static/pages/page/#/assignment-view"
}
```
Example BUID path used in source: `freshworks-FRPOC` (example — replace with the client's BUID).

---

## Screenshots (transcribed; originals in the vault `raw/se-runbook/images/`)

- `sec13_img018` — Three-box process overview diagram: **Floor premise Creation → Collect FloorPremiseID → Plan Upload** (all boxes blue with white text, connected by chevron arrows). This is the top-level sequence for this runbook.
- `sec13_img019` — WIS site Desk Management / Desk Allocation screen showing an existing **grid-based floor plan** with seats displayed in a color-coded grid. Illustrates what a successfully uploaded floor plan looks like in the admin UI.
- `sec13_img020` — WIS-MIS site Desk Management screen (no floor plan uploaded yet); table shows floor rows with columns for seat counts and a blue **"Upload Seats"** button (highlighted with a red circle annotation) in the rightmost column. Illustrates the UI state before upload and where the upload trigger lives.
- `sec13_img021` — Excel spreadsheet showing two columns of seat UUID data (labeled **OLD** and **NEW**) with Excel Conditional Formatting → Highlight Cells Rules → Duplicate Values open; duplicate `seatUUID` values are highlighted. Used to check for UUID duplicates when preparing or replacing seat UUID data. Annotations point to the Conditional Formatting menu path and the duplicate highlights.
- `sec14_img022` — WIS-Configurations sheet with a floor premise submission row: `Buid: tata-TCPOC`, `Service/Feature: Parking/Floor plan`, `premiseType: 4`, `parentPremise: 26ff30ff-b3fc-4bee-af65-5c4275c864ff`, `premiseName: 2nd Floor West Wing`, `geoCode: 13.051826,77.59…`, `techparkId: 081ae46d-82b…`, `buldOfficeGuid: L0tataTC-POC$-…`, `City: Bangalore`, `Country: INDIA`; Submit button visible at right.
- `sec16_img023` — Postman Params tab for Method A upload: `POST https://mis-security.moveinsync.com/mis-security-guard/csv/upload/floorplan`; three parameters `floorType=WITH_FLOOR_PLAN`, `forceUpdateFloorPlan=false`, `premiseId` (all enabled).
- `sec16_img024` — Postman Body tab for Method A: `form-data` selected, single `file` field with floor plan attached; Send button visible.
- `sec17_img025` — Postman Params tab for Method B upload: same endpoint as Method A but `floorType=WITH_BACKGROUND_IMAGE`; `forceUpdateFloorPlan=false`, `premiseId=a5fa16cd-05ec-4497-95e3-657b9ddaeeac` (all enabled).
- `sec17_img026` — Postman Body tab for Method B: `form-data` with two fields — `File` (floor plan) and `floorBackgroungImage` (background image); Send button visible.
- `sec18_img027` — Postman POST to `https://wis-premise.workinsync.io/mis-security-guard/csv/upload/layout/:premiseId?forceUpdateFloorPlan=false&wktDimensionInCm=100…`; Body tab (form-data) with `floorImage → TCI-I_GROUND_FLOOR_PLAn_file.svg` and `floor → TCI-I_GROUND_FLOOR_PLAN_file.json`; response 200 OK.
- `sec18_img028` — Postman POST to `https://serviceuat.moveinsync.com/mis-security-guard/csv/upload/seat_uuid`; Body tab with `floor` field for JSON file upload; illustrates the Seat UUID change API ("Send and Download" pattern).

---

## Validation checklist

- [ ] GET `https://mis-security.moveinsync.com/mis-security-guard/premise/buid/<BUID>` returns a premise object with `"premiseType": "4"` for the newly created floor premise.
- [ ] The floor `premiseId` (FloorPremiseID) has been copied and confirmed.
- [ ] POST upload call returned HTTP 200 OK (for Method C: Status 200 OK visible in Postman response bar).
- [ ] (Method C first-time only) `employeeFloorPlanUrl`, `adminFloorPlanUrl`, `adminAssignmentFloorPlanUrl` are set correctly for the BUID via the `empexp` GET/PUT check.
- [ ] Seats are visible in the WIS admin Desk Management screen under the correct floor.

---

## Notes & Gotchas

1. **`forceUpdateFloorPlan: false` on REUPLOAD — counter-intuitive but mandatory.** The source explicitly states: "InCase of Floor plan Upload/REUPLOAD always keep `forceUpdateFloorPlan: false`." Do not set it to `true` even when replacing an existing plan.

2. **Do NOT click Send before setting the premiseId.** All three upload methods include a bolded warning in the source: the premiseId must be updated in the URL/params before sending. Method C in particular has the premiseId baked into the URL path.

3. **premiseId inconsistency in sec16 source text.** The raw text of section 16 shows two different values: the URL uses `25d7cb03-ff02-4e25-9ee8-9a95aced08f9` while the params list shows `a5fa16cd-05ec-4497-95e3-657b9ddaeeac`. Both are examples; always replace with the actual FloorPremiseID from Step B.

4. **premiseId inconsistency in sec18 source text.** The raw text of section 18 shows the URL path as `/layout/4a8de968-2a38-49b9-9b32-ef6983bdb130` while the params list shows `a5fa16cd-05ec-4497-95e3-657b9ddaeeac`. The screenshot (`sec18_img027`) shows `/layout/:premiseId` as a placeholder. Always replace with the actual FloorPremiseID from Step B.

5. **Seat UUID change API points to UAT.** The source gives the Seat UUID change endpoint as `https://serviceuat.moveinsync.com/mis-security-guard/csv/upload/seat_uuid` — the `serviceuat` subdomain indicates a UAT environment, not production. Confirm the correct environment with the owning team before use in production (observed in source — confirm with owning team).

6. **Seat UUID change workflow** (from sec18). When you need to replace seat UUIDs in an existing JSON file:
   - `POST https://serviceuat.moveinsync.com/mis-security-guard/csv/upload/seat_uuid`
   - Header: `requestorUUID: <UUID>` (example from source: `dd011714-18c6-4486-9742-fd4547be5f76` — replace with the client's)
   - Body (form-data): `floor` → select the `.json` file whose UUIDs need changing
   - Use "Send and Download" (click the arrow next to the Send button → "Send and Download"), NOT plain Send.
   - Save the downloaded file as `<floor name>.json` (e.g. `abc floor.json`).
   - **Prerequisite:** The JSON file must already contain `seatUUID` values. Very old JSON files may not have `seatUUID` present — check the file before running this API.

7. **Reader ID mapping to an existing office.** Use the same premise-update API. Add `"readerNumber": ["<readerNumber>"]` in the `extras` JSON field, e.g.:
   ```json
   "extras": {
     "readerNumber": [
       "JYK8241200274"
     ]
   }
   ```
   Reference: SE-46441.

8. **`seatValidation=true` must be set in the Booking service before floor work begins.** This is noted at the top of section 5 (Floor premise Creation) in the source. It is a prerequisite, not part of the floor-upload steps themselves.

9. **Removing cabs from the Parking page.** The source notes at the tail of section 14: to remove the office cabs option from the Parking page, set `showCabs: false` in the Booking Rule Engine (`Bookingruleengine` service). This is unrelated to floor plan upload but is flagged in the same section.

10. **Booking disclaimer — out-of-scope note (section 15).** Section 15 of the source sits between the floor premise creation and floor plan upload sections and contains a parking booking disclaimer config (`bookingDisclaimers` property in Emp-Exp). It does not belong to any floor-plan upload step. It is preserved here for traceability:
    - **Property name:** `bookingDisclaimers`
    - **Service:** Emp-Exp
    - **Property value (parking):**
      ```json
      {"parking":{"title":"Consent on Commute Address","message":"I hereby state that the address provided by me in People Central is accurate and reflects my address for commuting to/from office. Any changes to my present address will be updated by me at the earliest in the People Central tool and by raising a ticket on the HR Query tool and office services tool.","actionButtonName":"Okay"}}
      ```
    - Reference TO: https://moveinsync.atlassian.net/browse/TO-14152

11. **`buIdOfficeGuid` vs `buldOfficeGuid` — two spellings in source.** The WIS-Configurations sheet column header (visible in `sec14_img022`) reads `buldOfficeGuid`. The source body text in section 14 spells it `buIdOfficeGuid`. Use whichever label the sheet displays at time of configuration; do not normalize.

12. **Premise validation endpoint uses `buid` in path** (not a query param): `GET .../premise/buid/<BUID>`. The source example is `/premise/buid/tata-TCPOC` — always substitute the real client BUID.

---

## Related

- Module: [[modules/floor-kiosk]]
- Upstream runbook: [[runbooks/ets-office-premise-setup]]
- Upstream runbook: [[runbooks/parking-premise-setup]]
- Tool: WIS-Configurations sheet (`1FyWuDnS…`) — same sheet used for office and parking premise creation
- Downstream: guard user creation (separate runbook, pending ingest)
- Downstream: SE ticket to enable feature flag per BUID after plan upload (noted in floor-kiosk module's Floor Plan Data Pipeline)

---

## Related Jira

- SE-46441 — Reader ID mapping via `extras.readerNumber` in premise update
- TO-14152 — Booking disclaimer (`bookingDisclaimers`) for parking — referenced in section 15
- SE-20977 — Appears in a CURL attachment filename in section 18 (`SE-20977_attachments/…`); weak signal only — no ticket details confirmed in source

---

## Last Updated

2026-06-25 — source: [[sources/se-runbook-ets-office-premise]] (raw: `raw/se-runbook/WIS-Configurations-ETS-EmployeeApp-GuardApp-SanitisationApp.docx`, sections 13 tail [img018–021], 14, 15, 16, 17, 18)
