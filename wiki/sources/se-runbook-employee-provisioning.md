---
type: source
raw_path: raw/se-runbook/crawl/files/
ingested: 2026-06-29
doc_type: spec
---

# Source: SE Runbook — Employee Data Sync (SCIM / Stratus API)

## Source Title
Multiple documents ingested as a batch for the employee-provisioning SCIM/Stratus topic.

## Documents Ingested (canonical filenames from raw/se-runbook/crawl/files/)

| Document | Version / Date | Authors | Scope |
|---|---|---|---|
| MoveInSync Employee Data Sync API Doc - Stratus (`1-ywmGHA5hYo8kw17GyDUcsWpSHFFmKYD-VSgURdgUoA.docx`) | v1.0, Mar 6, 2025 | Aditya Dutta; approved Ujjwal Trivedi | Stratus Direct API (WorkInSync-only sites) |
| Employee Data Sync with SCIM to WorkInSync/Moveinsync (OKTA) | v1.1, Jul 15, 2022 | Rishabh; approved Ujjwal | Okta SCIM setup |
| Employee Data Sync with SCIM to MoveInSync/WorkInSync — Azure AD | v1.1, Sep 15, 2021 | Nitin Awasthi, Rishabh M; approved Ujjwal Trivedi | Azure AD SCIM setup |
| Employee Datasync via SCIM Troubleshooting Guide (Internal) | v1.0, Aug 31, 2024 | Aditya Dutta; approved Ujjwal Trivedi | Internal SCIM troubleshooting (SE/support) |
| Role and Privilege Management in Stratus (`1g-F8sUXCjkxtxhPo86kRKMsLEd89MpFBdbnsGx8OvwE.docx`) | undated | — | Stratus RBAC model |
| MoveInSync Employee Data Sync API Document (v1.3, Apr 1, 2022 / v1.4 May 2, 2025) | v1.4, May 2, 2025 | Deepanshu Tyagi, Nitin Awasthi, Rahul Agrawal; approved Ujjwal Trivedi / Akhilesh Kumar Maurya | General (ETS + WorkInSync) data sync API |

## Documents Excluded as Noise (cross-linked, not ingested here)

| Document | Reason | Cross-linked to |
|---|---|---|
| Steps to enable visitor-bulk-upload | Visitor module content | [[modules/visitor-management]] |
| WorkInSync Meeting Rooms Setup For Implementation Team | Meeting rooms module | [[modules/meeting-rooms]] |
| Recommended Reading: Microsoft Azure SCIM docs | External Microsoft URL, not WorkInSync content | — |
| PB-22330 — Configurable sender email API | Off-topic: sender email config, not provisioning | — (contains a real JWT in source; excluded) |
| WorkInSync Single Sign On | Pure SSO doc | [[modules/sso]] |
| SSO With WorkInSync using OKTA | Pure SSO doc | [[modules/sso]] |
| WorkInSync - Microsoft Teams Integration | MS Teams module | [[modules/ms-teams-integration]] |
| Document Control — Meeting Room Onboarding | Meeting rooms onboarding | [[modules/meeting-rooms]] |

## Date
Earliest: Sep 15, 2021 (Azure SCIM). Latest: Mar 6, 2025 (Stratus API). Troubleshooting guide: Aug 31, 2024.

## Type
spec / SE runbook (multiple docs)

## Key Takeaways

- WorkInSync SCIM endpoints: `https://scim.workinsync.io/scim/v2` (Singapore) and `https://scim.eu.workinsync.io/scim/v2/` (EU). **Region mismatch is the #1 cause of "Test Connection" failures.**
- SCIM syncs **Users only** — Groups are explicitly not supported. Stratus role/privilege groups are WorkInSync-native and are NOT synced from the IdP.
- Stratus mandatory field for SCIM provisioning is **Email only**; missing office/team → provisioned to default. ETS sites require Employee ID as mandatory.
- The `active` attribute **must be mapped** in both Azure AD and Okta to enable deprovisioning. Missing mapping = silent deprovisioning failure.
- Azure AD quarantine occurs when the same provisioning error repeats in a short span. Resolution: diagnose logs, fix root cause, retry.
- The 2025 Stratus Direct API (`POST /{buid}/employees`) is a REST alternative for WorkInSync-only sites (not ETS). Supports batch payloads, `ext` tag objects, and a team endpoint.
- Stratus RBAC has four built-in groups (`admins`, `users`, `managers`, `guards`). Super admin is irremovable except by transferring the role via email verification. Custom groups supported.
- A known internal WiS SCIM failure mode exists: SCIM server ↔ PII service cache mismatch. Escalation path: Deepanshu/Tushar Tyagi (SCIM), Yogesh (PII), then request cache clear.
- The PB-22330 doc in source contained a real JWT token. That document was excluded from ingestion as off-topic noise; the token is NOT reproduced anywhere in wiki pages.

## Entities Mentioned
- Employee (sync schema owner: this module)
- Team (`projectName`/`projectDescription`/`listOfSpocs`)

## Modules Mentioned
- [[modules/employee-provisioning]] (primary)
- [[modules/sso]] (IdP auth — separate from SCIM)
- [[modules/ms-teams-integration]] (Azure AD shared IdP)
- [[modules/visitor-management]] (noise cross-link only)
- [[modules/meeting-rooms]] (noise cross-link only)

## Decisions Extracted
None requiring a formal decision page — the 2025 Stratus API introduction is an evolution (Stratus vs ETS split) already noted in the module's Open Questions.

## Wiki Pages Created/Updated
- Updated: [[modules/employee-provisioning]] — added Stratus Direct API section, Stratus Role/Privilege section, new Key Features, augmented API Endpoints table, updated sources + last_updated
- Created: [[runbooks/employee-data-sync-scim]] — Azure AD + Okta SCIM setup + troubleshooting runbook
- Created: [[sources/se-runbook-employee-provisioning]] — this page
