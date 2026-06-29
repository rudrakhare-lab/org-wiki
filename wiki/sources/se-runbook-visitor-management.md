---
type: source
raw_path: raw/se-runbook/crawl/files/
ingested: 2026-06-29
doc_type: misc
---

# SE Runbook — Visitor Management (VMS) Topic

## Source Title
SE Runbook — Visitor Management (Phase D, 2026-06-29 ingest). Six source documents bundled under this topic; see doc table below.

## Date
Various (2024 primary config doc; other docs undated in SE crawl).

## Type
misc (SE operational runbooks / configuration guides)

## Source Document Table

| # | Doc label | raw_path | Notes |
|---|-----------|----------|-------|
| 1 | Visitor Management — Configuration (2024) | `raw/se-runbook/crawl/files/1dO-uRIGCdv-U531pRMhzE6Dv9AWMX0tFgcsQ3LIQ1YI.docx` | Screenshot-heavy; text extract captured badge-printer specs only. Full office-config setup in screenshots. Author: Kavya Sridharan; approved by: Ujjwal Trivedi; v1.0, 2024-03-12. |
| 2 | VMS Notifications on UI + Property-Controlled Notification | `raw/se-runbook/crawl/files/1jLLg-rKq-7rKXoE1r6S9vQ-ux3_mM-fS9e1-fZvDJ4M.docx` | Fully captured. Documents `enabledBuidForVisitorConfigs`, `notificationMetaData`, `notificationConfigs`, per-persona properties. |
| 3 | Steps to enable visitor-bulk-upload | `raw/se-runbook/crawl/files/11MeiqEXurvV4xIwgk5tic_bw2tZvfnGFD4H0hTMbeyU.docx` | Fully captured. Consul flag, role_access, profile-field matching gotcha, custom-field and room-column options. |
| 4 | Custom Fields in Walk-in Setup (Master Property formsMetaData) | `raw/se-runbook/crawl/files/1s4xrLJFFehzcDlOPcnM8fFOIIubOXW_6TlAwO1jc5eY.docx` | Short, fully captured. `formsMetaDataForWalkIn`; Belongings cross-flow consistency rule. |
| 5 | DynamicFields JSON (businessGuests/contractor/deliveryPersonnel) | `raw/se-runbook/crawl/files/1pyPfofkI9yUedQs5b2EbtC9Xfk5MqL7ahQW_AxXntao.docx` | ~14.7k chars; SE crawl extract truncated (~12.5k captured). `personalGuest` type not captured. ⚠️ **Re-homed here from tags-desk-parking batch** — this doc was misfiled in that batch and correctly excluded there (see log entry 2026-06-29 18:05); it is visitor-management scoped. |
| 6 | WorkInSync Invite Employees Guide | `raw/se-runbook/crawl/files/1CZB9gDUpTlIfGYz1YDfzK-ijjrEWmMXCMOESrWD2rJg.docx` | Light end-user guide. Steps to invite employees via the admin console (not a client-facing config doc). Noted here only; no standalone runbook warranted. |

## Key Takeaways
- **Doc 1 is badge-printer-focused, not general office-config.** The SE config doc's text extract covers only Brother QL-820NWB hardware specs (model, connectivity, roll sizes). Office-enablement steps are in the screenshots (not captured).
- **Bulk upload requires a Consul flag + role_access grant.** `BULK_OPERATION_VISITOR_BOOKING=true` at `teammanager/{buid}/configuration`; Stratus sites additionally need a named privilege. Max 100 visitors per file.
- **`profileFieldsMetaData` ↔ `visitorBulkUploadData` key matching is mandatory** — a mismatch breaks bulk upload without a clear error.
- **Notification property-control is opt-in per BUID** via `enabledBuidForVisitorConfigs`. The three per-persona props (`hostNotifications`, `creatorNotifications`, `externalNotifications`) are inactive until the BUID is opted in. `externalNotifications` is `.com` only.
- **`notificationMetaData` and `notificationConfigs` must be consistent** in grouping IDs and notification IDs — mismatch causes broken panel rendering.
- **Walk-in custom fields use `formsMetaDataForWalkIn`; invited-flow host fields use `formsMetaDataForHostPWC`.** Belongings live in `formsMetaDataForWalkIn` and must be consistent across all flows.
- **Dynamic field schema (`visitorFormsMetaData` / `dynamicFields`)** is Consul-backed JSON with per-visitor-type structure. `hideOnWalkin: true` suppresses fields on the walk-in form per field. `enableStandardWalkinVisitorForm` per visitor type controls whether the standard form is used.
- **Doc 5 was misfiled in the tags-desk-parking batch** and is re-homed here. The tags batch log entry (2026-06-29 18:05) documents the exclusion.

## Entities Mentioned
- [[entities/visitor-invite]]
- [[entities/visitor-profile]]

## Modules Mentioned
- [[modules/visitor-management]] — primary module for all 6 docs
- [[modules/ms-teams-integration]] — referenced by notification template properties
- [[modules/meeting-rooms]] — referenced by `addRoomWithVisitorBulkUpload` (native rooms only)
- [[modules/floor-kiosk]] — related to `visitorFormsMetaData` / kiosk self-checkin flow

## Decisions Extracted
None. These are operational setup guides, not architecture decisions.

## Config Properties Documented (concrete keys + SE context)

| Property | SE-confirmed behaviour | Server |
|----------|------------------------|--------|
| `BULK_OPERATION_VISITOR_BOOKING` | Consul flag to enable bulk upload; set via `teammanager/{buid}/configuration` | both (Consul-backed) |
| `enabledBuidForVisitorConfigs` | Master opt-in list; BUID must be here for per-persona notification props to activate | both |
| `hostNotifications` | Per-persona JSON — host notification routing | both |
| `creatorNotifications` | Per-persona JSON — creator notification routing | both |
| `externalNotifications` | Per-persona JSON — additional-recipient routing | .com only |
| `notificationMetaData` | Notification panel structure (groups, questions, option checkboxes) | both |
| `notificationConfigs` | Default checked state for each notification checkbox; IDs + grouping must match `notificationMetaData` | both |
| `PrivilegeConfigurations_Visitor_Management_Notifications` | Privilege required for UI notification settings access (Stratus/privilege-service, not a PMS property) | N/A |
| `formsMetaDataForWalkIn` | Walk-in custom fields + Belongings section | both |
| `formsMetaDataForHostPWC` | Host-side custom fields for invited flow; also drives bulk-upload custom columns | both |
| `profileFieldsMetaData` | Profile field definitions; `key` must match `visitorBulkUploadData` | both |
| `visitorBulkUploadData` | Header visibility/order for bulk upload template; `key` must match `profileFieldsMetaData` | both |
| `addCustomFieldsWithVisitorBulkUpload` | Adds `formsMetaDataForHostPWC` fields to bulk upload columns | both |
| `addRoomWithVisitorBulkUpload` | Adds native room column to bulk upload template | both |
| `visitorFormsMetaData` / `dynamicFields` | Per-visitor-type dynamic field schema (Consul JSON); `hideOnWalkin`, `enableStandardWalkinVisitorForm` per type | see configs page |

## Secrets Redacted
None. Source material scanned clean. No JWTs, Bearer tokens, Base64 credentials, or real `@moveinsync.com`/`@workinsync.io` credentials in the captured text. (`agilos.workinsync.io` in doc 6 is a tenant URL, not a credential.)

## Wiki Pages Created/Updated

### Created
- [[runbooks/visitor-badge-printer-setup]] — badge printer hardware setup + note re screenshot-only office config
- [[runbooks/visitor-bulk-upload]] — Consul flag enablement, role_access, profile/custom field column config
- [[runbooks/visitor-notifications-setup]] — property-controlled notification config (opt-in, per-persona, panel UI)
- [[runbooks/visitor-custom-fields-setup]] — walk-in custom fields, Belongings, per-visitor-type dynamic field schema
- [[sources/se-runbook-visitor-management]] — this page

### Augmented
- [[modules/visitor-management]] — appended `[[sources/se-runbook-visitor-management]]` to `source:` frontmatter; added `## Related Runbooks` section before `## Open Questions`
- [[configs/visitor-management]] — added `PrivilegeConfigurations_Visitor_Management_Notifications` note in manual notes block (only missing property from SE docs; all other properties already exist in the auto-gen table)

_Source: self_
