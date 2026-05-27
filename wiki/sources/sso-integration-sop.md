---
type: source
raw_path: raw/modules/sso/SSO Integration Process (Ext)  ( SOP ).pdf
ingested: 2026-05-27
doc_type: SOP
---

# SSO Integration Process (SOP)

## Source Title
SSO Integration Process ( SOP )

## Date
25-09-2024 (v1.0, approved 04-10-2024). Author: Shruthi Naik / approved Dheeraj. Classification: Internal. **Most recent of the SSO source docs.**

## Type
SOP

## Key Takeaways
- **Internal TechOps process** for requesting SSO integration support — NOT a technical setup guide. Quote (Scope): *"This procedure applies to all requests for SSO technical integrations SAML & API based"* — confirms WorkInSync SSO offers BOTH SAML and OAuth ("API based") methods.
- **Owning POD: Emp-exp** (employee-experience). Quote: *"All technical integration requests should originate from the respective module PODs (Emp-exp)"*.
- **Workflow**: requestor emails support@moveinsync.com → module POD validates (IdP metadata, downtime, username type, test users) → KAM/TAM approval → POD raises a TechOps (TO) ticket to integrations@moveinsync.com.
- **TO ticket fields**: Site URL, site type (Production/POC/UAT), integration method (SAML / API-based), IdP metadata file, downtime (15-20 min), username type, test profiles, requestor name.
- **Site types** (quote): *"Production SG / POC / UAT / Production Mumbai"* — distinct SP metadata files per site type.
- **SLAs**: Minor/Major/Critical TOs — inform 4 working days prior; P0 (Blocker) — 1 working day with KDV/charan + Dibyendu approval.

## Entities Mentioned
(none)

## Modules Mentioned
- [[modules/sso]] (primary subject)
- [[modules/employee-experience]] (named as the "Emp-exp" owning POD for SSO integration requests — org/process ownership, not a runtime dependency)

## Decisions Extracted
(none)

## Wiki Pages Created/Updated
- Created: [[modules/sso]]
- Updated: [[index]], [[log]], [[glossary]]

_Source: [[sources/sso-integration-sop]]_
