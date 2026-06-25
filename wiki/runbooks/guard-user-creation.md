---
type: runbook
module: guard-app-kiosks
team: SE (Service Engineering)
status: active
last_updated: 2026-06-25
source: "[[sources/se-runbook-ets-office-premise]]"
raw_path: raw/se-runbook/WIS-Configurations-ETS-EmployeeApp-GuardApp-SanitisationApp.docx
---

# Runbook — Guard User Creation & Premise-User Mapping

> SE procedure to **create Guard App users, map them to office premises, generate Office QR codes, and perform premise management operations** in the WorkInSync backend, using the **WIS-Configurations Google sheet** (`1FyWuDnS…`) + **Postman**.
> ⚠️ Every concrete value below (`randstad-RSInd`, UUIDs like `28fe2d1a-5609-4d55-9d6c-11af834471df`, mobile numbers, geocodes) is an **EXAMPLE / placeholder** — replace with the client's actual values. `startTime` and `endTime` are the exception: they are **standard constants — use the same values for all clients** (see Step D).
> _Source: [[sources/se-runbook-ets-office-premise]] (raw doc sections 19, 21–28)_

## Purpose & Scope

Covers the Guard App user slice of premise configuration: obtaining prerequisite data from the implementation team, creating guard users, validating creation, mapping users to office premises, validating the mapping, generating Office QR codes, and two premise-management operations (edit `premiseName`/`geoCode`, delete a premise).

Office premise creation, parking, floor, amenities, sanitization, and meal setup are covered in separate runbooks. **This runbook = Guard user lifecycle + Office QR code + premise edit/delete.**

## Prerequisites

Before starting, obtain the following from the **implementation team**:
- Guard user **mobile number**
- Guard user **Location** and **Site Name**
- **Site BUID** (e.g. `randstad-RSInd` — example, replace with client's)

The implementation team provides these as a spreadsheet. The source shows an example registry with columns: **Security Guard ID · Name · Mobile No. · Location · Site name · Geo Code** (sec19_img029).

## Configuration Flow (where this fits)

`Office Premise creation → Add Capacity to Office → Parking Premise → Parking Capacity → Floor premise → Upload Floor → `**`Guard User → Premise-User Mapping`**` → Amenity → Seat Sanitization → Meal Booking.`

The Guard User process itself follows this linear flow:

```
User Creation → User Creation Validation → User-Premise Mapping → User-Premise Mapping Validation
```

**Tool link for Guard App configurations (Google sheet):**
`https://docs.google.com/spreadsheets/d/1FyWuDnS-L6wB9ZBqTvLwsk6qwQEBWIyTtMaHJ9PojlU/edit#gid=0`

## Step-by-step

### A — Collect prerequisite data from implementation team

Receive the guard registry data. The source example shows a spreadsheet with the following columns (sec19_img029):

| Column | Field | Example (replace with client's) |
|--------|-------|----------------------------------|
| A | Security Guard ID | `<guard-id>` |
| B | Name | `<guard-name>` |
| C | Mobile No. | `<mobile-number>` |
| D | Location | `Bangalore` |
| E | Site name | `Bangalore-Randstad` |
| F | Geo Code | `12.980163, 77.607308` |

> Keep this sheet open during steps B and D — you will need the mobile number and office name to match against API responses.

### B — Create the guard user (User Creation)

1. Open the **WIS-Configurations Google sheet**:
   `https://docs.google.com/spreadsheets/d/1FyWuDnS-L6wB9ZBqTvLwsk6qwQEBWIyTtMaHJ9PojlU/edit#gid=0`
2. Fill in the row with the following columns and click **Submit** (sec22_img030):

   | Column | Value | Note |
   |--------|-------|------|
   | `Buid` | site BUID | e.g. `randstad-RSInd` — example, replace |
   | `Service/Feature` | `User Creation` | select from dropdown |
   | `phoneNumber` | guard mobile number | from implementation team data |
   | `password` | guard password | origin not specified in source |

3. Repeat for each guard user.

### C — Validate user creation (User Creation Validation)

After submitting, cross-validate the created user via Postman (sec23_img031, sec23_img032):

1. Open Postman. Click **"+"** to open a new request tab.
2. Select method **`GET`** and enter:
   ```
   https://mis-security.moveinsync.com/mis-security-guard/user
   ```
3. Click **Send**.
4. In the response body, press **`Ctrl+F`** and search for the guard's **phone number**.
   - If the user was created successfully, the phone number will be found.
5. With the phone number located, copy the corresponding **`userId`** value shown in the same record.
   - Example `userId`: `28fe2d1a-5609-4d55-9d6c-11af834471df` _(example — replace with the client's)_
6. Note this `userId` — it is required for premise mapping in Step D.

> User creation is complete at this point. The next step maps each created user to their office premise.

### D — Map users to their office premise (Premise User Mapping)

This step saves each guard user under their respective office by linking their `userId` to the office `premiseId`.

#### D.1 — Look up the office premiseId

1. In Postman, select method **`GET`** and enter the premise list for the site BUID (sec24_img033):
   ```
   https://mis-security.moveinsync.com/mis-security-guard/premise/buid/<BUID>
   ```
   e.g. `https://mis-security.moveinsync.com/mis-security-guard/premise/buid/randstad-RSInd` _(example — replace with the client's)_
2. Click **Send**.
3. In the JSON response, locate premise objects where **`premiseType: "2"`** — this identifies Guard App office premises (sec24_img034).

   > **NOTE: `premiseType: "2"` is the Guard App office variable.** Only use premises of this type; ignore other premise types in the response.

4. Match each `premiseName` to the office name from the implementation team's sheet. Copy the corresponding `premiseId` (sec24_img035).
   - Example pairing _(example — replace with the client's)_:
     - Office: `Gurgaon-Randstad`
     - `premiseId`: `5a5b5165-83bf-45f5-9ed4-1417f5933230`
5. Record the `userId` → `premiseId` mapping for each guard in a working sheet.

#### D.2 — Submit the premise-user mapping

1. Open the **WIS-Configurations Google sheet** (same link as Step B).
2. Fill in the row with the following columns and click **Submit** (sec24_img036):

   | Column | Value | Note |
   |--------|-------|------|
   | `Buid` | site BUID | e.g. `randstad-RSInd` — example, replace |
   | `Service/Feature` | `Premise User Mapping` | select from dropdown |
   | `userId` | guard's userId | copied from Step C |
   | `premise id` | office premiseId | from Step D.1; `premiseType: "2"` only |
   | `startTime` | `1595615400` | **Standard constant — use the same value for all clients** |
   | `endTime` | `1690309740` | **Standard constant — use the same value for all clients** |

3. Repeat for each guard user.

### E — Validate the premise-user mapping (Premise User Mapping Validation)

After submitting, cross-validate the mapping via Postman (sec25_img037, sec25_img038):

1. In Postman, select method **`GET`** and enter:
   ```
   https://mis-security.moveinsync.com/mis-security-guard/premise-user-mapping
   ```
2. Click **Send**.
3. In the response body, search (**`Ctrl+F`**) for the guard's `userId`.
4. Confirm the returned record shows the expected `premiseId` alongside the `userId`.
   - If both match, the mapping is complete.
5. Repeat validation for each guard.

### F — Office QR Code Generation

Generate an Office QR code for each office.

1. In Postman, select method **`GET`** and call the QR string endpoint for the office's `premiseId`:
   ```
   https://mis-security.moveinsync.com/mis-security-guard/premise/generate-qr-string?premiseId=<PREMISE_ID>
   ```
   e.g. `?premiseId=daad02f1-ea3a-4e77-befc-948fb4906309` _(example — replace with the client's)_
2. Change the `premiseId` query parameter for each office and fetch the string.
3. Copy the returned QR string.
4. Open the QR code generator tool: `https://www.the-qrcode-generator.com/`
5. Paste the string into the **"Enter text to share here"** field.
6. Save the generated QR code image in the format **`<officename>_Office.png`**.

> Repeat steps 1–6 for every office that requires a QR code, swapping the `premiseId` each time.

### G — Update PremiseName / geoCode (premise edit)

> **Cross-reference:** the shared edit mechanics (GET the premise JSON, strip trailing comma, PUT back) are documented in [[runbooks/ets-office-premise-setup]] section C. This section captures only what is **additional or guard-specific**.

When the office name or geocode must be updated for an existing Guard App office premise:

1. **Fetch the current premise JSON.** In Postman, `GET`:
   ```
   https://mis-security.moveinsync.com/mis-security-guard/premise/buid/<BUID>
   ```
   Locate the premise object (match by `premiseName`) and copy its full JSON body (drop the trailing `,` comma — see [[runbooks/ets-office-premise-setup]] section C).

2. **Edit the target fields** in the copied JSON. The full premise object includes these fields (example values — replace with the client's):

   ```json
   {
     "premiseId": "64c032e0-25e9-4868-9e5d-444c68fa7f3c",
     "premiseType": "2",
     "parentPremise": "9921c2ed-aeef-45e6-9525-e6fd120cd312",
     "premiseName": "MISOffice",
     "buid": ["wfosa-wfoza"],
     "geoCode": "13.912557,88.643355",
     "geofenceDistance": 700,
     "city": null,
     "country": "India",
     "businessDays": ["0","1","2","3","4","5","6"],
     "businessStartTime": null,
     "businessEndTime": null,
     "totalCapacity": null,
     "status": "ACTIVE",
     "techparkId": "64c032e0-25e9-4868-9e5d-444c68fa7f3c",
     "officeGuid": "{\"wfosa-wfoza\":\"LOwfosaw-foza-$000-0000-000000000001\"}",
     "buIdOfficeGuid": {
       "wfosa-wfoza": "LOwfosaw-foza-$000-0000-000000000001"
     },
     "privacy": "PUBLIC",
     "thermalScannerId": "T001593409421136",
     "extras": null
   }
   ```
   Fields to change: `premiseName` (to the new name) and/or `geoCode` (to the new coordinates). All other fields stay as fetched.

3. **Submit the update.** In Postman, select method **`PUT`** and call:
   ```
   https://mis-security.moveinsync.com/mis-security-guard/premise
   ```
   Paste the edited JSON as the request body and click **Send**.

4. **Clear cache** — follow the cache-evict step from [[runbooks/ets-office-premise-setup]] section C (same evict URL pattern).

> **Note on section 27 vs ETS section C:** Section 27 uses the identical PUT endpoint as the ETS runbook section C. Section 27 omits the trailing-comma and cache-evict notes that section C documents; this runbook captures the additional premise fields visible in the section 27 example (particularly `officeGuid`, `buIdOfficeGuid`, `privacy`, `thermalScannerId`, `status`, `businessDays`) and defers to [[runbooks/ets-office-premise-setup]] section C for the shared mechanics. No contradiction was found between the two sources on the edit steps themselves.

### H — Delete a Premise

Use this when a premise (office, floor, parking, vaccination, or other type) must be removed entirely.

1. Obtain the `premiseId` of the premise to delete (from a prior `GET …/premise/buid/<BUID>` call).
2. In Postman, select method **`DELETE`** and call (sec28_img039):
   ```
   DELETE https://mis-security.moveinsync.com/mis-security-guard/premise/v2?premiseId=<PREMISE_ID>
   ```
   Supply the `premiseId` as a query parameter.
3. Send the request. Confirm the response indicates success.

> The source states that the `premiseId` parameter controls which entity is deleted — it can target an Office, Floor, Parking, Vaccination, or any other premise type. Confirm the correct `premiseId` before sending; the operation is destructive.

---

## Screenshots (transcribed; originals in the vault `raw/se-runbook/images/`)

- `sec19_img029` — Implementation-team input spreadsheet: columns Security Guard ID · Name · Mobile No. · Location · Site name · Geo Code, showing example guard records for Bangalore and Gurgaon sites.
- `sec22_img030` — WIS-Configurations Google sheet with **User Creation** selected in the `Service/Feature` dropdown (column B); visible columns: `Buid` · `Service/Feature` · `phoneNumber` · `password`. Submit button at right.
- `sec23_img031` — Postman: `GET https://mis-security.moveinsync.com/mis-security-guard/user` — request open in a new tab, URL bar highlighted.
- `sec23_img032` — Postman: same `/user` endpoint response body with `Ctrl+F` active; yellow annotation: `<-- Phone number available here so copy the corresponding UserId for further step`. Highlighted `phoneNumber` and `userId` fields side-by-side in the JSON.
- `sec24_img033` — Postman: `GET …/premise/buid/randstad-RSInd` — request bar with the BUID path appended, Params tab active.
- `sec24_img034` — Postman: JSON response for the premise/buid call; lines 362–370 visible showing a premise object including `premiseName`, `premiseType`, and `premiseId` fields. Arrow annotation pointing to the relevant object.
- `sec24_img035` — Working reference table (SE notepad view) showing a guard user mapping: columns for user mobile, office name, `userId`, and `premiseId`; example row: `<mobile>` / `Gurgaon-Randstad` / userId `28fe2d1a…` / premiseId `5a5b5165…`.
- `sec24_img036` — WIS-Configurations Google sheet with **Premise User Mapping** selected in the `Service/Feature` dropdown; visible columns: `Buid` · `Service/Feature` · `userId` · `premise id` · `startTime` · `endTime`. Submit button at right.
- `sec25_img037` — Postman: `GET https://mis-security.moveinsync.com/mis-security-guard/premise-user-mapping` — request bar with the endpoint, method GET.
- `sec25_img038` — Postman: `/premise-user-mapping` response body with `Ctrl+F` active; blue rectangle highlights around `userId` (line 1148) and `premiseId` (line 1149) fields in the JSON result confirming the mapping record.
- `sec28_img039` — Postman: `DELETE https://mis-security.moveinsync.com/mis-security-guard/premise/v2?premiseId=` with `premiseId` as a Query Param, value field visible.

_(Sections 26 and 27 have no associated screenshots in the source.)_

---

## Validation checklist

- [ ] Guard user phone number found in `GET …/mis-security-guard/user` response (Ctrl+F)
- [ ] `userId` copied correctly from the `/user` response for each guard
- [ ] `premiseType: "2"` confirmed for all office premises used in mapping
- [ ] `premiseId` matches the correct office name from the implementation team sheet
- [ ] `startTime = 1595615400` and `endTime = 1690309740` used as-is (standard constants)
- [ ] Mapping record found in `GET …/mis-security-guard/premise-user-mapping` — `userId` + `premiseId` both present
- [ ] QR code string fetched per office via `generate-qr-string?premiseId=…`; image saved as `<officename>_Office.png`

---

## Notes & Gotchas

- **`startTime` and `endTime` are fixed standard constants** — `1595615400` and `1690309740` respectively. The source explicitly states "Value is Standard — use the same value for all." Do **not** treat these as per-client placeholders.
- **`premiseType: "2"` = Guard App office variable.** The response from `premise/buid/<BUID>` returns premises of multiple types; only type `2` is the correct target for guard-user premise mapping.
- **userId is per-user, unique** — must be looked up individually from the `/user` validation endpoint for each guard; do not reuse across users.
- **Google sheet dropdown options** for `Service/Feature` (column B) are: `premise`, `premise capacity`, `covid tag`, `User Creation`, `Premise User Mapping`, `Parking/Floor plan`. Select the exact label; no free-text entry.
- **Section G (update premise)** — the source example shows a full premise JSON object including `officeGuid`, `buIdOfficeGuid`, `privacy`, `thermalScannerId`, and `businessDays` fields in addition to the fields documented in [[runbooks/ets-office-premise-setup]] section C. When performing a PUT update, always base the request body on a freshly fetched GET (never reconstruct from memory or partial data).
- **Section H (delete premise)** — deletion applies to any premise type via `premiseId`. The source lists: Office, Floor, Parking premis[e], Vaccination premise as examples. _(Note: "Parking premis" is the source's literal spelling — preserved verbatim.)_
- The section 28 trailing line "Security App Type-Manned(Security App)/Unmanned(iOT/Fevbot Device)/Fixed QR code Office Wise" is the lead-in to the next topic (Guard App linking, out of scope for this runbook).
- **QR code generator tool** `https://www.the-qrcode-generator.com/` — external third-party service; confirm it is still the approved tool before use (observed in the example — confirm with owning team).

---

## Related

- Module: [[modules/guard-app-kiosks]]
- Upstream runbook: [[runbooks/ets-office-premise-setup]] — Office premise creation and section C (edit premise mechanic shared with Step G above)
- Upstream runbook: [[runbooks/parking-premise-setup]]
- Tool: WIS-Configurations sheet (`1FyWuDnS-L6wB9ZBqTvLwsk6qwQEBWIyTtMaHJ9PojlU`)
- Service base: `https://mis-security.moveinsync.com/mis-security-guard/`

## Related Jira

— none cited in source sections 19, 21–28.

## Last Updated
2026-06-25 — source: [[sources/se-runbook-ets-office-premise]] (raw: `raw/se-runbook/WIS-Configurations-ETS-EmployeeApp-GuardApp-SanitisationApp.docx`, sections 19, 21–28)
