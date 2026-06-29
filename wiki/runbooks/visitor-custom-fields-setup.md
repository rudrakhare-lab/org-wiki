---
type: runbook
module: visitor-management
team: SE
status: active
last_updated: 2026-06-29
source: "[[sources/se-runbook-visitor-management]]"
raw_paths:
  - raw/se-runbook/crawl/files/1s4xrLJFFehzcDlOPcnM8fFOIIubOXW_6TlAwO1jc5eY.docx
  - raw/se-runbook/crawl/files/1pyPfofkI9yUedQs5b2EbtC9Xfk5MqL7ahQW_AxXntao.docx
---

# Visitor Custom Fields & Dynamic Fields Setup

## Purpose
Configure custom (non-standard) fields on visitor forms for the walk-in flow and the per-visitor-type dynamic field schema (`formsMetaDataForWalkIn`, `formsMetaDataForHostPWC`, and the `visitorFormsMetaData` / `dynamicFields` JSON). Also covers the Belongings section configuration.

## Prerequisites
- VMS enabled for the BUID.
- Agreement on which custom fields are required for each visitor type (Business Guest, Contractor, Delivery Personnel, etc.).
- PMS access to set `formsMetaDataForWalkIn` and/or `formsMetaDataForHostPWC`.
- For dynamic-field JSON schema: Consul access (the `dynamicFields` or `visitorFormsMetaData` config is Consul-backed, not a simple PMS boolean).

## Ordered Steps

### Part A — Walk-in Custom Fields (`formsMetaDataForWalkIn`)

#### Step A1 — Add custom fields to the walk-in form

The master property for walk-in custom fields is **`formsMetaDataForWalkIn`** (JSON, both servers).

- Place custom fields under the **`other details`** section of the JSON structure.
- Typical custom fields: Company, Designation, Purpose of Visit, Asset serial numbers.

#### Step A2 — Configure Belongings

The Belongings section (for item check-in/out logging) uses the **same property** `formsMetaDataForWalkIn`.

Add required belonging entries under the dedicated Belongings section of the JSON.

> ⚠️ **Critical:** Any belonging added in one visitor flow (e.g. walk-in) **must be included in ALL visitor flows** (invited, self check-in). If a belonging entry is present in the walk-in flow but absent from another flow, the front-desk flow will break when that visitor type is processed.

---

### Part B — Host-side Custom Fields for Invited Flow (`formsMetaDataForHostPWC`)

For the **invited** (scheduled) flow, host-side custom fields are defined in **`formsMetaDataForHostPWC`** (JSON, both servers).

- Add fields such as Company, Designation, additional approval fields.
- These are shown to the host/employee when creating an invite.
- Also used as the source for custom-field columns in the bulk-upload template (see [[runbooks/visitor-bulk-upload]] §Step 4).

---

### Part C — Per-Visitor-Type Dynamic Field Schema

The dynamic field schema controls which standard and custom fields appear per visitor type (Business Guest, Contractor, Delivery Personnel) and whether fields are hidden on the walk-in form specifically.

This schema is stored in a Consul JSON property (surfaced in the config layer as `visitorFormsMetaData` or `dynamicFields` depending on client/flow). The JSON is a top-level object with one key per visitor type.

#### Visitor type keys in the schema

| Key | Label |
|-----|-------|
| `businessGuests` | Business Guests |
| `contractor` | Contractor |
| `deliveryPersonnel` | Delivery Personnel |
| `personalGuest` | Personal Guest _(not in captured extract; may exist in full schema)_ |

> ⚠️ The SE-provided JSON sample (doc 5) is truncated — `personalGuest` and any additional types were not captured. Verify the complete list with the owning team before deploying.

#### Schema structure per visitor type

Each visitor-type key maps to:
```json
{
  "<visitorType>": {
    "label": "Display Label",
    "fields": [ <field objects> ],
    "enableStandardWalkinVisitorForm": true | false
  }
}
```

**`enableStandardWalkinVisitorForm`** — when `true` (e.g. `businessGuests`), the standard walk-in form is used for this visitor type. When `false` (e.g. `contractor`), the visitor type uses only the fields defined in its `fields` array.

#### Field object structure

Each entry in the `fields` array:

| Key | Purpose |
|-----|---------|
| `key` | Unique field identifier — must match across all flows |
| `label` | Display name shown on the form |
| `type` | Input type: `text`, `email`, `number`, etc. |
| `placeholder` | Placeholder text |
| `rules.CREATE` | Editability + optionality when creating the visitor record |
| `rules.UPDATE` | Editability + optionality when updating |
| `hideOnWalkin` | `true` = field hidden on the walk-in form; `false` = shown |

#### `hideOnWalkin` usage in the reference schema

In the captured sample for `businessGuests` and `contractor`:
- `phoneNumber` → `hideOnWalkin: true`
- `phoneNumberCountryCode` → `hideOnWalkin: true`
- All other fields (name, lastName, email, company, designation) → `hideOnWalkin: false`

This means phone-number collection is skipped for walk-in visitors of these types (typically because walk-in visitors don't supply phone at the reception desk in the same flow as invited visitors).

#### Canonical field keys by visitor type (from SE reference sample)

| Field key | businessGuests | contractor | deliveryPersonnel |
|-----------|:--------------:|:----------:|:-----------------:|
| `name` | ✅ | ✅ | ✅ |
| `middleName` | ✅ | ✅ | — |
| `lastName` | ✅ | ✅ | ✅ |
| `email` | ✅ | ✅ | ✅ |
| `phoneNumber` | ✅ (hideOnWalkin) | ✅ (hideOnWalkin) | — |
| `phoneNumberCountryCode` | ✅ (hideOnWalkin) | ✅ (hideOnWalkin) | — |
| `company` | ✅ | ✅ | — |
| `designation` | ✅ | — | — |

> Note: "✅ (hideOnWalkin)" means the field exists but is hidden on the walk-in form.

#### Step C1 — Deploy the dynamic-field JSON

1. Obtain the complete `dynamicFields` / `visitorFormsMetaData` JSON from the SE team or the client's existing config (the SE sample is a reference, not a copy-paste template).
2. Validate JSON structure: each visitor type has a `fields` array, each field has `key`, `label`, `type`, `rules.CREATE`, `rules.UPDATE`, and `hideOnWalkin`.
3. Set via Consul (or the relevant PMS JSON property for the target client's deployment).
4. Confirm field keys match across `profileFieldsMetaData`, `formsMetaDataForWalkIn`, and `dynamicFields` for any field that appears in multiple flows.

---

## Screenshots
- `1s4xrLJFFehzcDlOPcnM8fFOIIubOXW_6TlAwO1jc5eY.docx` — "Custom Fields in Walk-in Setup" — short doc, text fully captured.
- `1pyPfofkI9yUedQs5b2EbtC9Xfk5MqL7ahQW_AxXntao.docx` — "DynamicFields JSON" — raw JSON reference (~14.7k chars); SE crawl extract is truncated. See raw file for complete schema.

## Validation
- Walk-in visitor form shows the configured custom fields under "other details".
- Belongings section appears on walk-in and all other flows where the client requires it.
- Per-visitor-type: create a test invite for each type (Business Guest, Contractor, Delivery Personnel) and confirm fields appear/hide correctly.
- Walk-in for a Contractor: confirm `phoneNumber` is hidden (per `hideOnWalkin: true`).

## Notes & Gotchas
- **Belongings must be consistent across all flows.** Missing a belonging entry in any one flow breaks the front-desk view for that visitor type.
- The dynamic-field JSON is a Consul-backed config, not a standard PMS property — it does not appear in the auto-generated PMS config table as a settable value (only `visitorFormsMetaData` is listed as the container, with a conflict note on its "Not in use" auto-gen description). See [[wiki/configs/visitor-management]] manual notes.
- `personalGuest` visitor type was referenced in the task brief but not present in the captured SE JSON extract — confirm with the owning team whether this type exists in the live schema.
- The `formsMetaDataForHostPWC` naming convention ("PWC") is a legacy artefact — it applies generically, not just to PWC/PricewaterhouseCoopers clients.

## Related Jira
—

## Linked Raw Evidence
- `raw/se-runbook/crawl/files/1s4xrLJFFehzcDlOPcnM8fFOIIubOXW_6TlAwO1jc5eY.docx` — "Custom Fields in Walk-in Setup (Master Property formsMetaData)"
- `raw/se-runbook/crawl/files/1pyPfofkI9yUedQs5b2EbtC9Xfk5MqL7ahQW_AxXntao.docx` — "DynamicFields JSON (businessGuests/contractor/deliveryPersonnel)" — NOTE: this doc was originally misfiled in the tags-desk-parking SE crawl batch and correctly excluded there; it is visitor-management scoped and belongs here.

_Source: [[sources/se-runbook-visitor-management]]_
