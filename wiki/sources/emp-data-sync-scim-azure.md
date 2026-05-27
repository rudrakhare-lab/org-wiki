---
type: source
raw_path: raw/modules/employee-provisioning/Employee Data Sync with SCIM to MoveInSync_WorkInSync - Azure (1).pdf
ingested: 2026-05-27
doc_type: spec
---

# Employee Data Sync with SCIM — Azure AD

## Source Title
Employee Data Sync with SCIM to MoveInSync/WorkInSync - Azure AD

## Date
Sep 15, 2021 (v1.1). Version history: v1.0 Nitin Awasthi / approved Ujjwal Trivedi ("First Version"); v1.1 Rishabh M / Ujjwal Trivedi ("Added detailed process for Azure AD"). Classification: **Confidential**.

## Type
spec

## Key Takeaways
- **SCIM 2.0 (RFC 7644) employee data sync** from a client IdP into WorkInSync. Source quote: *"WorkInSync provides SCIM (System for cross domain identity management ...) compliant API interface for this purpose."* This doc is the **Azure AD** setup flavor; functionally **equivalent to the Okta flavor** ([[sources/emp-data-sync-scim-okta]]) — same protocol, same WIS endpoint, same attribute schema, different IdP front-end.
- **Entities supported: Users only. Groups are NOT supported** (quote: *"Entities not supported: 1. Groups"*).
- **Tenant endpoint (regional split)**: `https://scim.workinsync.io/scim/v2` for AWS-Singapore-hosted tenants; `https://scim.eu.workinsync.io/scim/v2/` for EU-hosted tenants. Auth via a **secret token** generated and shared by the WorkInSync account manager (no token value in the doc).
- **Attribute mapping** is the load-bearing content (page 9-10): AD attribute → SCIM attribute → WorkInSync field. Key mappings: `userPrincipalName`→`userName` (primary unique ID), `mail`→email, `givenName`/`surname`→first/last, `physicalDeliveryOfficeName`→office, `employeeId`→enterprise employeeNumber, `department`→team, `manager`→manager (FK). Address fields are *"Applicable only for commute clients"*. WorkInSync only processes mapped SCIM attributes; extra fields are ignored.
- **Sync cadence**: *"by default data is synced every 40 minutes"*. Azure provides a Provisioning overview + error view; per-record retry via "Provision on Demand".
- **Setup is via Azure Enterprise Applications** → Create your own application (Non-gallery) → Provisioning (Automatic) → Test connection → enable Users, disable Groups → review attribute mappings → turn on provisioning.
- **Screenshots present in the source are not captured in the text extract** — the substantive config (attribute table, tenant URLs, sync cadence, auth) is all textual; only the Azure-portal UI screenshots (images) are absent. No config data lost.

## Entities Mentioned
(none ingested — see the employee-provisioning module's Open Questions: foundational `entities/employee.md` is deferred to Tier 2.5)

## Modules Mentioned
- [[modules/employee-provisioning]] (primary subject)

## Decisions Extracted
(none — setup guide; no alternatives + rationale)

## Wiki Pages Created/Updated
- Created: [[modules/employee-provisioning]]
- Updated: [[index]], [[log]], [[glossary]]

_Source: [[sources/emp-data-sync-scim-azure]]_
