---
type: runbook
module: tags-desk-parking
team: SE
status: active
last_updated: 2026-06-29
source: "[[sources/se-runbook-tags-desk-parking]]"
raw_paths:
  - raw/se-runbook/crawl/files/1iRcMK_MLGkablzqN7siw5HvnmlFhZcoI5BgBnN78tU0.docx
  - raw/se-runbook/crawl/files/1PClIGPq7kwnhOAb1ovyq0yjKnJZ9u9Jeklz7LmiOLgw.xlsx
---

# Runbook — Tagging Config, Dynamic Fields & SeatTypeMapping Setup

## Purpose

Configure the shared tag engine for a client's desk and general-booking surface:

1. **GET/PUT `consulConfiguration/dynamicFields`** — read and update the Consul-backed dynamic-fields schema that controls which extra fields employees fill when making a desk booking (e.g. mode of transport, license plate number).
2. **SeatTypeMapping** — understand the seat-name → seat-type data structure used to classify seats across floors.

> For parking-specific tag creation (creating tags via `mis-floor-plan`, employee/slot bulk upload, `BLOCK_HOTSEAT` policy), see the dedicated parking runbooks:
> - [[runbooks/parking-tag-and-vehicle-setup]]
> - [[runbooks/parking-dynamic-policy]]

## Prerequisites

- SE-level access with a valid `x-wis-token` HS512 JWT for the target BUID/server
- Know whether the client is on the `.com` server (`wis-seat-beta.moveinsync.com` in source — confirm production host, see Notes)
- Know the client's BUID (a UUID)
- For SeatTypeMapping: the floor plan must already be uploaded and seats must exist before seat-type assignment is meaningful

## Steps

### Step 1 — Fetch the current dynamic-fields config

Retrieve the existing `DynamicData` payload for the client's BUID:

```
GET https://<wis-seat-host>/wisSeatBooking/<BUID>/consulConfiguration/dynamicFields
accept: */*
x-wis-token: <HS512 JWT — redacted>
```

The response body is a JSON object containing a `DynamicData` array. Each element in the array is a field definition. **Copy the full response** — the PUT step requires you to send the entire array (not a patch).

### Step 2 — Compose the updated DynamicData payload

Each field object in `DynamicData` has the following structure:

| Key | Type | Description |
|-----|------|-------------|
| `fieldType` | string | UI control type: `singleSelect`, `input`, etc. |
| `fieldInputType` | string | HTML input type: `radio`, `text`, etc. |
| `appFieldType` | string | Mobile app control: `dropdown`, `text`, etc. |
| `title` | string | Display label shown to the employee |
| `configName` | string | Internal key (stored in booking data) |
| `backedFieldType` | string | Backend data type: `STRING`, etc. |
| `messageTemplate` | string | Summary string template using `{0}` placeholder |
| `validators` | array | Validation rules, e.g. `{"type":"Required","message":"..."}` |
| `itemsList` | array | Options for select fields: `{"label":"...", "value":"..."}` |
| `subFields` | array | Conditional nested fields (appear when a parent value is selected); each sub-field carries `parentConfigValue` to trigger on |

**Example field — "Mode of Transport" (from SE source, transport to office):**

```json
{
  "fieldType": "singleSelect",
  "fieldInputType": "radio",
  "appFieldType": "dropdown",
  "title": "Mode of Transport",
  "configName": "transport",
  "messageTemplate": "Mode of Transport : {0}",
  "backedFieldType": "STRING",
  "validators": [{ "type": "Required", "message": "Required field is mandatory" }],
  "subFields": [
    {
      "fieldType": "input",
      "fieldInputType": "text",
      "appFieldType": "text",
      "title": "License No.",
      "configName": "licenseNo",
      "backedFieldType": "STRING",
      "parentConfigValue": "Personal Car",
      "validators": [{ "type": "Required", "message": "License No. is Mandatory" }]
    }
  ],
  "itemsList": [
    { "label": "Personal Car", "value": "Personal Car" }
    // source doc was truncated here — full option list not available
  ]
}
```

> ⚠️ `subFields` entries are only shown to the employee when the `parentConfigValue` matches the selected option. In the example above, `licenseNo` only appears when the employee picks "Personal Car".

### Step 3 — PUT the updated configuration

Send the full updated `DynamicData` array back:

```
PUT https://<wis-seat-host>/wisSeatBooking/<BUID>/consulConfiguration/dynamicFields
accept: */*
Content-Type: application/json
x-wis-token: <HS512 JWT — redacted>

{
  "DynamicData": [ ... ]
}
```

A 200 response confirms the config was persisted. **Verify by running the GET from Step 1 again** and confirming the response matches what you sent.

### Step 4 — SeatTypeMapping (for seat-type classification)

The SeatTypeMapping is a tabular configuration that assigns each named seat to a seat type. Columns:

| Column | Description |
|--------|-------------|
| `Office Name` | Human-readable office/premise name |
| `Floor Name` | Floor within the office |
| `Seat Name` | Exact seat identifier as it appears in the floor plan |
| `Seat Type` | Classification label (see known types below) |

**Known seat types (from SE source):**
- `Workstation`
- `Partner Cabin`
- `Director Cubicle/ Cabin`

> ⚠️ The SE source provides the data structure and sample rows only. The upload/apply mechanism (API call, Consul config write, or admin UI import) is **not documented** in the source. Confirm with the owning team before attempting to apply a SeatTypeMapping for a client. See Open Questions in [[modules/tags-desk-parking]].

## Validation

- [ ] GET returns a non-empty `DynamicData` array
- [ ] PUT returns 200
- [ ] Subsequent GET matches the payload you submitted
- [ ] In the booking UI, the new field(s) appear at booking time for the target BUID
- [ ] Conditional sub-fields (if used) only appear when the parent option is selected

## Screenshots

No screenshots are included in the source documents (docs 2 and 3 contain curl commands and an xlsx table only). For visual reference of the booking UI dynamic-field form, consult the desk-management product team or the client's booking UI directly.

## Notes & Gotchas

1. **Beta host in source:** The source doc uses `wis-seat-beta.moveinsync.com`. Confirm the correct production host for the client's server (`.com` vs `.in`) before running Steps 1–3 on a live client. Using the beta endpoint against a production BUID will likely return an empty config or a 404.

2. **Full-array replacement:** The PUT endpoint replaces the entire `DynamicData` array — it is **not** a PATCH. Always GET first, then modify the array, then PUT. Sending only the changed fields will delete the others.

3. **BUID in URL path:** The source URL contains a literal UUID in the path (`wisSeatBooking/<BUID>/...`). The example BUID in the SE source (`c9aa661f-0267-4cf2-a9f5-b88011619a84`) is an example value — always substitute the actual client BUID.

4. **Shared tag engine:** The `mis-floor-plan` tag API used for parking tag creation is the same engine used for desk and meeting-room tags. Changes to `entityType=EMPLOYEE` tags affect all booking surfaces simultaneously. See [[runbooks/parking-dynamic-policy]] for the tag-creation workflow; do not create duplicate tag definitions.

5. **Visitor dynamic fields are separate:** The SE source batch includes a visitor-type dynamic-fields JSON (`businessGuests`, `contractor`, `deliveryPersonnel`, `personalGuest` with `hideOnWalkin` flags). This is a **visitor-management** config, not a desk/seat config — it is owned and managed by a different service. Do not apply it via this runbook's PUT endpoint.

6. **Token expiry:** `x-wis-token` is an HS512 JWT. If the request returns 401, obtain a fresh token before retrying.

## Related Jira

—

## Linked Raw Evidence

- `raw/se-runbook/crawl/files/1iRcMK_MLGkablzqN7siw5HvnmlFhZcoI5BgBnN78tU0.docx` — Tagging & DynamicFields config: GET/UPDATE curl reference (source of Steps 1–3 and the field-schema table)
- `raw/se-runbook/crawl/files/1PClIGPq7kwnhOAb1ovyq0yjKnJZ9u9Jeklz7LmiOLgw.xlsx` — SeatTypeMapping xlsx (source of Step 4 column structure and seat-type examples)
