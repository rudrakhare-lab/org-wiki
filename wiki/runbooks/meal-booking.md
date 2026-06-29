---
type: runbook
module: meal-management
team: SE (Service Engineering)
status: active
last_updated: 2026-06-29
source: "[[sources/se-runbook-meal-booking]]"
raw_path: raw/se-runbook/crawl/files/1BIdHGbsUrTp4hEKy8pL8u4DNPMTfWhQl5zd7cv2iWTE.docx
---

# Runbook — Meal Booking Setup

## Purpose & Scope

End-to-end configuration for enabling WorkInSync meal booking for a client. Covers:

1. Creating the cafeteria premise (mis-security-guard)
2. Mapping the cafeteria to an office or floor
3. Configuring meal types in the employee-exp Consul node
4. Enabling meal planning
5. Creating counters within the cafeteria
6. Uploading the counter-to-meal mapping
7. Generating QR codes for counters

This runbook covers WFO-integrated and standalone meal booking. It does **not** cover RFID access-card check-in (see [[modules/meal-management]]) or admin/vendor dashboard setup.

_Source: [[sources/se-runbook-meal-booking]]_

---

## Prerequisites

- A provisioned BUID for the target client
- The office `premiseId` UUID (the existing office or floor premise to which the cafeteria will be mapped) — obtainable from the mis-security-guard premise API
- Consul access (employee-exp namespace) for the client's BUID
- Bearer token for mis-security-guard API calls (`x-wis-token` header)
- Bearer token for meal-booking-app API calls
- `tenantId` for the meal-booking-app endpoints (client-specific; confirm with implementation team)
- Confirm which server the client is on (`.com` / `.in`) before using any URL
- The meal counter mapping spreadsheet (columns: Cafeteria Name, Counter Name, Meal Type, Meal Option name, Meal Name, Start Date, End Date)

---

## Configuration Flow (where this fits)

```
ETS Office Premise Setup
        ↓
Office / Floor Premise exists in mis-security-guard
        ↓
Cafeteria Premise Creation   ← STEP 1 of THIS RUNBOOK
        ↓
Cafeteria → Office Mapping   ← STEP 2
        ↓
Consul Meal Config           ← STEPS 3–4
        ↓
Counter Creation             ← STEP 5
        ↓
Counter Mapping Upload       ← STEP 6
        ↓
QR Code Generation           ← STEP 7
```

---

## Step-by-step

### Step 1 — Create the cafeteria premise

Create a new premise with `premiseType: "8"` (cafeteria) in mis-security-guard.

**Method:** `POST`
**Endpoint:**
```
https://mis-security.moveinsync.com/mis-security-guard/premise
```
> ⚠️ For `.in` clients use `mis-security.moveinsync.in` instead.

**Headers:**
```
Content-Type: application/json
x-wis-token: <token>
```

**Request body:**
```json
{
  "premiseType": "8",
  "premiseName": "<cafeteria-name>",
  "buid": ["<buid>"],
  "geoCode": "<lat,lon>",
  "geofenceDistance": <meters>,
  "city": "<city>",
  "country": "<country>",
  "businessDays": ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY"],
  "status": "ACTIVE"
}
```

> ⚠️ All values above are **placeholders** — replace with actual client values.
> - `premiseType: "8"` is the fixed code for cafeteria. Do not change.
> - `buid` is an array; supply the client's BUID string (e.g. `["<client-buid>"]`).
> - `geoCode` format: `"lat,lon"` as a string (e.g. `"12.9716,77.5946"`).
> - `businessDays` should match the client's working days.

**Response:** On success, the API returns the new premise object including its `premiseId` (a UUID). **Save this UUID** — it is the `cafeteria-premiseId` required for all subsequent steps.

_Source: [[sources/se-runbook-meal-booking]] — "Meal Booking Workflow Setup"_

---

### Step 2 — Map the cafeteria to an office or floor

Link the cafeteria premise to the client's existing office or floor premise.

**Method:** `GET`
**Endpoint:**
```
https://mis-security.moveinsync.com/mis-security-guard/premise-mapping/create?buid=<buid>&premiseId=<cafeteria-premiseId>&mappedPremiseId=<office-premiseId>
```

> ⚠️ All path parameters are **placeholders**:
> - `buid` — client's BUID (example: `colt-CNcr`)
> - `premiseId` — the `cafeteria-premiseId` returned in Step 1
> - `mappedPremiseId` — the existing office or floor `premiseId` to map to
> - Optional: `officeGuids` — comma-separated office GUIDs (if applicable)

> ⚠️ For `.in` clients use `mis-security.moveinsync.in`.

**Success:** Returns a mapping confirmation. The cafeteria is now associated with the specified office/floor.

**To remove a mapping later (optional):**

**Method:** `PUT`
**Endpoint:**
```
https://mis-security.moveinsync.com/mis-security-guard/premise-mapping
```
**Body:**
```json
{
  "mappedPremiseid": "<cafeteria-premiseId-to-unmap>"
}
```

_Source: [[sources/se-runbook-meal-booking]] — "Meal Booking Workflow Setup"_

---

### Step 3 — Configure meal types in Consul (employee-exp)

Set the meal type and meal option mappings for the client in Consul.

**Consul path:**
```
employee-exp → <buid> → meal
```

Replace `<buid>` with the client's BUID (example: `<client-buid>`).

**Value format (JSON):**
```json
{
  "mealTypes": {
    "100": { "name": "Breakfast", "status": "ACTIVE", "options": [0, 1, 2] },
    "101": { "name": "Lunch",     "status": "ACTIVE", "options": [0, 1, 2, 3] },
    "102": { "name": "Dinner",    "status": "ACTIVE", "options": [0, 1, 2] }
  },
  "mealOptions": {
    "0": { "name": "None",        "status": "ACTIVE" },
    "1": { "name": "Veg",         "status": "ACTIVE" },
    "2": { "name": "Non-Veg",     "status": "ACTIVE" },
    "3": { "name": "Vegan",       "status": "ACTIVE" },
    "4": { "name": "Continental", "status": "ACTIVE" },
    "5": { "name": "Italian",     "status": "ACTIVE" }
  }
}
```

> ⚠️ The meal type codes (`100`, `101`, `102`) and meal option codes (`0`–`5`) above are **examples** from the source doc. Confirm the correct codes and option set with the client/implementation team. Only include `mealOptions` and `mealTypes` that the client's cafeteria will serve.

_Source: [[sources/se-runbook-meal-booking]] — "Meal Booking Workflow Setup"_

---

### Step 4 — Enable meal planning in Consul (employee-exp common)

Set the master meal planning switch to `true` in the common Consul node.

**Consul path:**
```
employee-exp → common → mealPlanningEnabled
```

**Value:** `true`

> ⚠️ This is the value you *set to enable* meals. The system default for `mealPlanningEnabled` when not configured is not explicitly documented in the source — treat any existing value as deliberate and confirm before changing.

> ⚠️ This is a **common** (cross-BUID) node — changes here apply to all BUIDs on the server unless per-BUID overrides exist. Confirm scope with the implementation team before editing.

_Source: [[sources/se-runbook-meal-booking]] — "Meal Booking Workflow Setup"_

---

### Step 5 — Create counter(s) within the cafeteria

Create one or more named counters inside the cafeteria premise.

**Method:** `POST`
**Endpoint:**
```
https://mis-security.moveinsync.com/mis-security-guard/premise/<cafeteria-premiseId>/meal/create-counter
```

Replace `<cafeteria-premiseId>` with the UUID from Step 1 (example: `<cafeteria-premise-uuid>`).

**Headers:**
```
accept: */*
Content-Type: application/json
x-wis-token: <token>
```

**Request body (array):**
```json
[
  {
    "cafeteriaName": "<cafeteria-name>",
    "cafeteriaPremiseId": "<cafeteria-premise-uuid>",
    "counterNames": ["<Counter-1>", "<Counter-2>"]
  }
]
```

> ⚠️ All values are **placeholders**:
> - `cafeteriaName` — human-readable name matching Step 1
> - `cafeteriaPremiseId` — the UUID from Step 1 (same as path param)
> - `counterNames` — list of counter names for this cafeteria (e.g. `["North Counter", "South Counter"]`)

> ⚠️ The source document captures this call from a **beta** host (`mis-security-beta1...`). The production equivalent is `mis-security.moveinsync.com` as shown above. Always confirm the correct host with the implementation team.

_Source: [[sources/se-runbook-meal-booking]] — "Create Counter"_

---

### Step 6 — Upload counter-to-meal mapping

Upload a spreadsheet that maps each counter to the meals it serves.

**Method:** `POST`
**Endpoint:**
```
https://meal-booking.moveinsync.com/meal-booking-app/<tenantId>/bulk-upload/counter-details
```

Replace `<tenantId>` with the client's tenant identifier (example: `<client-tenant-id>`).

**Headers:**
```
x-wis-token: <token>
requestorUUID: <uuid>
Content-Type: multipart/form-data
```

**Form body:** multipart file upload (key: `file`).

**File format (spreadsheet columns, in order):**

| Column | Format | Example |
|--------|--------|---------|
| Cafeteria Name | String | `Main Cafeteria` |
| Counter Name | String | `Counter 1` |
| Meal Type | String | `Lunch` |
| Meal Option name | String | `Veg` |
| Meal Name | String | `Dal Rice` |
| Start Date | DD-MM-YYYY | `01-07-2026` |
| End Date | DD-MM-YYYY | `31-07-2026` |

> ⚠️ `<tenantId>` and `<uuid>` are **placeholders** — obtain from implementation team. Do not hardcode client identifiers in wiki pages.
> ⚠️ Date format is `DD-MM-YYYY` — incorrect format will cause upload failure.

_Source: [[sources/se-runbook-meal-booking]] — "Create Counter"_

---

### Step 7 — Generate QR codes for counters

Download the QR code(s) for the cafeteria's counters. The QR codes are printed and placed at each counter for employee scan.

**Method:** `GET`
**Endpoint:**
```
https://meal-booking.moveinsync.com/meal-booking-app/<tenantId>/meal/generate-qr-meal?premiseId=<cafeteria-premiseId>
```

**Headers:**
```
x-tenant-id: <tenantId>
x-wis-token: <token>
```

> ⚠️ `<tenantId>` and `<cafeteria-premiseId>` are **placeholders** — use the client's values.
> ⚠️ The response is a binary/image stream (PDF or image). Save it and print for the cafeteria.

_Source: [[sources/se-runbook-meal-booking]] — "Create Counter"_

---

## Validation checklist

- [ ] Step 1: `POST /premise` returns 2xx; new `premiseId` UUID is in the response
- [ ] Step 2: Premise mapping call returns success; the cafeteria appears under the office in the admin console
- [ ] Step 3: Consul key `employee-exp → <buid> → meal` is set with correct meal type/option codes
- [ ] Step 4: Consul key `employee-exp → common → mealPlanningEnabled` is `true`
- [ ] Step 5: Counter creation returns 2xx; counter names appear in the cafeteria's counter list
- [ ] Step 6: Bulk-upload returns success; meal items appear on the counter in admin console
- [ ] Step 7: QR endpoint returns an image/PDF; QR codes are scannable and resolve to correct counter
- [ ] End-to-end: an employee can create a meal booking (standalone or WFO-integrated) and check in via QR scan

---

## Notes & Gotchas

1. **`premiseType: "8"` is mandatory** — this is the fixed code for cafeteria in mis-security-guard. Using any other value will create the wrong premise type and the meal booking flow will not work.

2. **Save the `cafeteria-premiseId` from Step 1 immediately** — it is needed for Steps 2, 5, and 7. There is no dedicated "get premiseId" endpoint; if lost, retrieve it via:
   ```
   GET https://mis-security.moveinsync.com/mis-security-guard/premise/{premiseId}
   ```
   or query all premises for the BUID and filter by `premiseType: 8`.

3. **Beta host in the source** — the "Create Counter" doc captures an `x-wis-token` call to `mis-security-beta1...`. The production endpoint is `mis-security.moveinsync.com`. Always use the production host for live client setups unless explicitly instructed otherwise.

4. **One meal per employee per day** — `allowedMealBookingPerEmployee` defaults to `1`. A WFO booking with meal and a standalone meal booking are mutually exclusive for the same day. See [[modules/meal-management]] for the constraint.

5. **`mealPlanningEnabled` is a common Consul key** — editing it affects all clients sharing the common node. Scope changes carefully.

6. **Consul meal type codes** — the codes (`100` = Breakfast, `101` = Lunch, etc.) and meal option codes (`0` = None, `1` = Veg, etc.) are from the source doc examples. These may vary by client configuration. Confirm with the implementation team before setting.

7. **`tenantId` for meal-booking-app** — this is distinct from the client's BUID. It is a separate identifier for the meal-booking-app service. Obtain from the implementation team; never infer from the BUID name.

8. **Date format in counter mapping file** — must be `DD-MM-YYYY`. Common mistake: using `YYYY-MM-DD` (ISO format) will fail silently or cause upload error.

9. **New config properties (not yet in config catalog)** — the source doc references the following properties which are not in the current KB config pages. These appear to be BRE-level configs:
   - `mealBookingEnabled` — master switch to enable meal booking
   - `mealCheckinOptions` — sets check-in options (e.g. `["Scan Meal QR"]`); default per source: `[Scan Meal QR]`
   - `enableMealFallbackFlow` — fallback flow if primary check-in fails; default per source: `false`
   - `enableMealQrPrintButtonenableMealQrPrint` — ⚠️ this appears to be two property names concatenated in the source (likely `enableMealQrPrintButton` and `enableMealQrPrint`); default per source: `false` for each; server assignment not stated in the source doc
   
   These properties should be confirmed with the Meal Management team and added to [[configs/booking-rule-engine]] once verified.

---

## Related Jira

No PB- Jira tickets were referenced in the source documents for this runbook.

---

## Linked Raw Evidence

| File | Description |
|------|-------------|
| `raw/se-runbook/crawl/files/1BIdHGbsUrTp4hEKy8pL8u4DNPMTfWhQl5zd7cv2iWTE.docx` | "Meal Booking Workflow Setup" — Steps 1–5 (premise creation, mapping, Consul config) |
| `raw/se-runbook/crawl/files/1JVY9qshShtAiIBGWD9iDkzA73YQ2n-FBLl4-9sy-U.docx` | "Create Counter" — Steps 5–7 (counter creation, bulk upload, QR generation); contained real auth tokens — all redacted |
| `raw/se-runbook/crawl/files/1-vBpXc3eg0STypByMS22SkP_zVh625iHqVaq4xgJePs.docx` | "Master property to enable meal" — PMS config property list and defaults |
| `raw/se-runbook/crawl/files/1yVLbX83WWvjWbCjqcrRq4drtQjbp1DITSbCewfUYJ4g.docx` | Release Notes: "Meal booking Options Timewise" |

---

## Related

- [[modules/meal-management]] — parent module page
- [[configs/booking-rule-engine]] — BRE-level meal config properties
- [[configs/emp-experience-common]] — `mealCutoffInMinutes`, `mealPlanningEnabled`, `excludeMealOnlyBookingsFromActiveBookingCount`
- [[modules/floor-kiosk]] — tablet device used for RFID-based meal check-in
- [[modules/access-management]] — RFID infrastructure for access-card check-in

## Last Updated
2026-06-29 — source: [[sources/se-runbook-meal-booking]]
