---
type: source
raw_path: raw/modules/employee-provisioning/Employee Data Sync with SCIM to WorkInSync (OKTA).pdf
ingested: 2026-05-27
doc_type: spec
---

# Employee Data Sync with SCIM — Okta

## Source Title
Employee Data Sync with SCIM to WorkInSync/Moveinsync (OKTA)

## Date
Jul 15, 2022. **⚠️ Version metadata inconsistency**: the Document Control header says "Version No 1.1" but the Version Control table lists only v1.0 (Rishabh / approved Ujjwal). The v1.1 row is missing from the table. Classification: **Confidential**.

## Type
spec

## Key Takeaways
- **SCIM 2.0 employee data sync — Okta flavor.** Functionally **equivalent to the Azure AD flavor** ([[sources/emp-data-sync-scim-azure]]): same SCIM protocol, same WIS tenant endpoints, same attribute schema, same 40-minute sync cadence, same "Provision on Demand" retry. Only the IdP-side setup differs.
- **Okta-specific setup**: Okta Portal → Applications → Browse App Catalog → search "SCIM 2.0" → select **SCIM 2.0 Test App (Header Auth)** → Add integration → Provisioning tab → Configure API Integration. Quote: *"you see template applications for each of the three authentication methods ... Basic Auth, Header Auth, or OAuth Bearer Token. Please select SCIM 2.0 Test App (Header Auth)."*
- **Same tenant endpoints (regional split)**: `https://scim.workinsync.io/scim/v2` (AWS Singapore) / `https://scim.eu.workinsync.io/scim/v2/` (EU). Secret token from the WIS account manager.
- **Same attribute mapping table** as the Azure doc (userName, displayName, email, givenName/familyName, office, address fields for commute clients, externalId, employeeId, department→team, manager). WorkInSync only processes mapped SCIM attributes.
- **Entities supported: Users only; Groups NOT supported.**
- **Screenshots present in source but not in extract** — substantive config is textual; only Okta-portal UI screenshots are absent.

## Entities Mentioned
(none ingested — `entities/employee.md` deferred to Tier 2.5)

## Modules Mentioned
- [[modules/employee-provisioning]] (primary subject)

## Decisions Extracted
(none)

## Wiki Pages Created/Updated
- Created: [[modules/employee-provisioning]]
- Updated: [[index]], [[log]], [[glossary]]

_Source: [[sources/emp-data-sync-scim-okta]]_
