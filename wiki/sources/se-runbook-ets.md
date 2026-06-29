---
type: source
raw_path: raw/se-runbook/crawl/files/1dLTh6YeE8b0nxYuZ4exli4m9TMWpf9FA.docx
ingested: 2026-06-29
doc_type: spec
---

# Source: ETS Topic — SE Runbook + Data Sync Docs

## Source Title
Multiple ETS sources — ingested together as the ETS topic batch:

| Document | File / Path | Date | Type |
|----------|-------------|------|------|
| SE Runbook — ETS pre-requisites + office/engineering config sections | `raw/se-runbook/_extract/sections/01-pre-requisites.md`, `02-ets--operation---engineering-side-conf.md`, `04-1-office-premise-creation.md`, `14-5-floor-premise-creation.md` | 2024 (extract) | runbook sections |
| Data Sync Process Document for ETS | `raw/se-runbook/crawl/files/1dLTh6YeE8b0nxYuZ4exli4m9TMWpf9FA.docx` | 2022-03-07 (v1.0) | spec |
| Datasync Integration Process — SOP | `raw/se-runbook/crawl/files/1APfiqktv-jX9Lp9wXZ_5cKpLGZLWIwE99qfrb0HOv1Y.docx` | 2024-09-27 (v1.0) | SOP |
| Release notes — Indemnification Form | `raw/se-runbook/crawl/files/1lx6Qa0LJDpDVZ_sADfwnCVhoQENq0yL3CL9HY-4PDsA.docx` | undated | release note |

## Date
Primary doc (Data Sync Process Document for ETS): 2022-03-07. Datasync SOP: 2024-09-27. Indemnification release note: undated.

## Type
spec / SOP / release note

## Key Takeaways
- ETS is the **upstream source system** for offices, shifts, and employee records. WorkInSync premises, capacities, and booking modules cannot be set up until an office and shifts exist in ETS.
- **Two employee data sync channels** are documented: SFTP (bulk CSV, DevOps-managed automation) and API Sync (client pushes per-employee records with Bearer token auth). SFTP requires a TechOps ticket to `integrations@moveinsync.com`; the SOP defines validation steps, SLA tiers (Major=4wk, Minor=2wk, P0=1BD), and KAM/TAM approval gates.
- **Office API** (`GET /<TENANT>/ets/apis/office`) returns `guid`, `address`, `geoCord` — SE engineers use these values to create WorkInSync premises via the WIS-Configurations tool.
- **Employee data schema** is transport-era and carries commute fields (Nodal, ShuttlePoint, GeoCode, BillingZone) alongside workplace fields. For non-commute deployments most transport fields are irrelevant. SCIM channel (documented in [[modules/employee-provisioning]]) is the modern alternative.
- **Indemnification Form release note** documents ETS-side configs for a women's-transport-cancellation undertaking feature (`FEATURE_INDEMNIFICATION_AGREEMENT_ENABLE`, `INDEMNITEE_COMPANY`, `WOMEN_EMPLOYEE_SIGN_IN_ALERT_*`, `INDEMNIFICATION_EMAIL_*`). These are ETS-side, not PMS configs. The property `indemnifyOfficeBookingTransport` (Jira-only) is **not** in this release note.
- **`showCabs`** (BookingRuleEngine, not ETS service) and **`commuteMandatory`** (Emp-Ex inferred) appear in the SE runbook as example config values. Defaults not documented.
- **ETS config spreadsheet** (`1WpEu4vW…`, 11 tabs) holds all ETS operation/engineering configs — not yet fully ingested; referenced for future enrichment.

## Entities Mentioned
- Office (ETS) — guid, address, geoCord
- Shift (ETS) — login/logout scheduling
- Employee record — EmployeeId, Email, ProjectTeam, GeoCode, Nodal, ShuttlePoint, CostCenter, RemoveEmployee
- Premise (WorkInSync) — created downstream from ETS office data

## Modules Mentioned
- [[modules/ets]] — primary subject
- [[modules/employee-provisioning]] — cross-link: SCIM/API employee sync is the modern alternative to ETS SFTP sync; field schema lives there
- [[modules/desk-management]] — office premise feeds seat booking
- [[modules/parking-management]] — parking premise created under office premise; `showCabs` config intersection
- [[modules/guard-app-kiosks]] — guard user mapping built on office premise
- [[modules/meal-management]] — office premise is parent entity for meal location
- [[modules/floor-kiosk]] — floor premise (premiseType: 4) created under office premise

**Noise docs in the crawl — cross-linked, NOT ingested here:**
- Employee Data Sync API / SCIM / OKTA / Azure AD / Troubleshooting Guide → [[modules/employee-provisioning]] (employee SCIM is a distinct channel)
- Meeting Rooms Setup / Meeting Room Onboarding → [[modules/meeting-rooms]]
- WorkInSync Single Sign On → [[modules/sso]]
- Accessibility Conformance Report → off-topic, not ingested
- Face Recognition Onboarding Workflow → [[modules/floor-kiosk]] / [[modules/guard-app-kiosks]] (not ETS-specific)
- Microsoft Intune SDK Integration → [[modules/mobile-app]] (mobile app MDM, not ETS data sync)

## Decisions Extracted
None — no architecture decisions documented in these sources.

## Wiki Pages Created/Updated
- Updated: [[modules/ets]] — stub → active; added data sync, employee schema, API auth, ETS configs, indemnification note, floor-kiosk and meal-management to Used By
- Created: [[sources/se-runbook-ets]] (this page)
- Created: [[runbooks/ets-data-sync]] — data sync section folded into a lightweight runbook (see note)
