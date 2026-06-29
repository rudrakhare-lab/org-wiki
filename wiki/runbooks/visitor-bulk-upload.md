---
type: runbook
module: visitor-management
team: SE
status: active
last_updated: 2026-06-29
source: "[[sources/se-runbook-visitor-management]]"
raw_path: raw/se-runbook/crawl/files/11MeiqEXurvV4xIwgk5tic_bw2tZvfnGFD4H0hTMbeyU.docx
---

# Visitor Bulk Upload — Enablement & Configuration

## Purpose
Enable the visitor booking bulk-upload feature for a client BUID and configure the template columns (profile fields, custom fields, room details).

> Note: Bulk upload supports a maximum of **100 visitors per file** (existing module page limit). Exceeding this limit will cause the upload to fail.

## Prerequisites
- BUID already provisioned and VMS enabled.
- Consul access for the target environment.
- For Stratus-hosted clients: access to the privilege management console.
- Profile fields (`profileFieldsMetaData`) already defined for the BUID.
- (Optional) Custom fields (`formsMetaDataForHostPWC`) defined if custom-field columns are needed.
- (Optional) Meeting rooms enabled for the BUID if room-column is needed.

## Ordered Steps

### Step 1 — Enable the feature flag via Consul

Set the configuration key in Consul:

```
Key path:   teammanager / {buid} / configuration
Property:   BULK_OPERATION_VISITOR_BOOKING
Value:      true
```

Then add the key to `role_access` for every role that should have access:

```
Key path:   teammanager / {buid} / role_access
Action:     Add "BULK_OPERATION_VISITOR_BOOKING" to the role's access array
```

Repeat the `role_access` step for each role (e.g. EMPLOYEE, RECEPTIONIST, MANAGER) as agreed with the client.

### Step 2 — Grant privilege (Stratus sites only)

On Stratus-hosted sites, additionally grant the privilege:

```
Privilege name:  Bulk_Operation_Visitor_Booking
Access level:    edit
```

This step is not required for non-Stratus deployments.

### Step 3 — Configure profile field columns

Profile fields define the standard columns (Name, Email, Phone Number, etc.) in the bulk upload template.

1. Confirm `profileFieldsMetaData` is set correctly for the BUID (standard fields: name, email, phoneNumber).
2. Set `visitorBulkUploadData` to control which profile field headers appear in the template and their display order.

> ⚠️ **Critical:** The field `key` value in `profileFieldsMetaData` **must exactly match** the `key` value in `visitorBulkUploadData`. A mismatch silently breaks the bulk upload functionality — columns appear in the template but data does not map correctly.

Changes to these two properties take effect in both the **invited-flow** and **bulk-operations** upload templates.

### Step 4 — Configure custom field columns (optional)

To include company, designation, or other custom fields in the bulk upload template:

1. Verify custom fields are defined in `formsMetaDataForHostPWC`.
2. Set the PMS property `addCustomFieldsWithVisitorBulkUpload = true` to expose those fields as columns in the template.

If this property is `false` (default), custom fields are collected only via the invite form, not the bulk upload sheet.

### Step 5 — Add meeting room column (optional, native rooms only)

To allow bulk-upload rows to include a meeting room assignment:

1. Confirm meeting rooms are enabled for the BUID.
2. Set the PMS property `addRoomWithVisitorBulkUpload = true`.

> ⚠️ This is supported only for **native WIS rooms** (not Outlook-integrated rooms). Do not enable for clients whose rooms are managed via the Outlook/Exchange integration.

### Step 6 — Validate

1. Log in as a user with the bulk-upload role.
2. Navigate to Visitor Management → Bulk Upload.
3. Download the template — verify expected columns are present (profile fields, custom fields if enabled, room column if enabled).
4. Upload a test file with 2–3 rows.
5. Confirm visitors appear in the invite list with correct data.

## Screenshots
The source document (`11MeiqEXurvV4xIwgk5tic_bw2tZvfnGFD4H0hTMbeyU.docx`) contains the original written steps. No UI screenshots were captured in the SE crawl text extract.

## Validation
- Bulk upload option is visible for roles that were granted access.
- Template download returns correct columns.
- A small test upload creates visitors without errors.
- 100-visitor limit: upload of 101 rows should return an error (test on staging before production).

## Notes & Gotchas
- Maximum **100 visitors per bulk upload file**. Files exceeding this limit fail silently or with a generic error.
- The `key` matching rule (`profileFieldsMetaData` ↔ `visitorBulkUploadData`) is the most common breakage point during setup.
- `addRoomWithVisitorBulkUpload` only works with native rooms — confirm with client before enabling.
- `addCustomFieldsForBulkUpload` is a `.com-only` property that also controls custom-field header inclusion; `addCustomFieldsWithVisitorBulkUpload` is the `both`-server equivalent — use the latter for `.in` clients.

## Related Jira
—

## Linked Raw Evidence
- `raw/se-runbook/crawl/files/11MeiqEXurvV4xIwgk5tic_bw2tZvfnGFD4H0hTMbeyU.docx` — "Steps to enable visitor-bulk-upload"

_Source: [[sources/se-runbook-visitor-management]]_
