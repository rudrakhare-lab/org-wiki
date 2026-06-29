---
type: source
raw_path: raw/se-runbook/crawl/files/1zf6BBHL5DjgGdrUW9oct5lTxi38oSu0jKcrWRInto2o.docx
ingested: 2026-06-29
doc_type: misc
---

# SE Runbook — SSO Integration Sources

## Source Documents

| # | Title | Date | raw_path |
|---|-------|------|----------|
| 1 | MoveInSync Web Single Sign-On — Complete Guide (v1.2) | 2024-04-30 | `raw/se-runbook/crawl/files/1zf6BBHL5DjgGdrUW9oct5lTxi38oSu0jKcrWRInto2o.docx` |
| 2 | Login seamlessly on MoveInSync app via SSO (mobile) | undated (pptx) | `raw/se-runbook/crawl/files/1zKkshEHwlJEcx7VmBoNLGTLgCaQUKbH5gD2ksZoOsn8.pptx` |

---

## Source Title

1. **MoveInSync Web Single Sign-On (Complete Guide)** — v1.2, Last Modified 30/04/2024
2. **Login seamlessly on the MoveInSync app via Single Sign-on (SSO)** — mobile, PowerPoint (undated)

## Date

1. 30 April 2024 (document control table: v1.2 approved by Bhargav G on 30/04/2024; v1.0 Arun 24/02/2022; v1.1 Nitin Awasthi 28/02/2022)
2. Undated — pptx slide deck

## Type

misc (SE operational guides)

---

## Key Takeaways

- **Comprehensive Azure AD SAML guide (2024):** Doc 1 is the current comprehensive SAML/Azure AD SSO setup guide (v1.2, April 2024). It supersedes earlier fragmented docs for the Azure AD path and is the recommended reference for new SAML onboardings.
- **Four distinct SP environments with separate metadata files:** Production SG (`moveinsync-sp.xml`, `accounts.moveinsync.com`), POC (`moveinsync-poc-sp.xml`, `accountspoc.moveinsync.com`), UAT (`moveinsync-uat-sp.xml`, `serviceuat.moveinsync.com/accounts/...`), and Mumbai/`.in` (`moveinsync-mum-sp.xml`, `accounts.moveinsync.in`). Each environment requires a distinct SP metadata file.
- **Username type evolution — conflict to flag:** The 2024 Complete Guide (v1.2) explicitly lists **both** "Email ID" and "Employee ID" as supported username types. This contradicts the older Azure AD SSO PDF ("only Email ID supported, Employee ID not supported as of now") that is currently documented as an open conflict in [[modules/sso]] Open Questions. The 2024 guide is newer and more comprehensive; the conflict should be reconciled by the module owner.
- **Cert rotation procedure documented:** Certificate rotation is a parallel activity (MIS + client simultaneously), requires the latest IdP metadata XML, and requires a 15–30 minute downtime window with at least 2 weeks advance notice from the client.
- **Mobile SSO enablement:** `EnableSsoOnMobile` (default False) enables SSO on mobile. `ssoMandatory` (default False) removes the OTP fallback option. Both are SE-ticket controlled; TO assistance may be required. Original feature: PB-25542.
- **Supported SAML IdPs:** OpenSAML 2.0 with POST SAML profile — compatible with Azure AD, ADFS, Okta (App Integration Wizard), Ping Identity, Shibboleth, and any compliant SAML/OIDC provider.
- **FederationMetadata.xml shortcut:** Azure AD and ADFS clients can share the `FederationMetadata.xml` file (or App Federation Metadata URL) instead of extracting individual SAML fields — this is the preferred intake path for these IdPs.
- **Note on doc scope:** Doc 1 focuses entirely on SAML 2.0 / Azure AD. It does **not** cover the OAuth 2.0 / OIDC path (`auth.moveinsync.com/mis-auth`). The existing "OAuth doc is undated" open question in [[modules/sso]] therefore remains open — this doc is not a substitute for `MIS_OAuth_OnBoarding.pdf`.

---

## Entities Mentioned

No data-model entities (users, rooms, bookings) are described. SSO deals with authentication artifacts:
- SP metadata XML (per-environment)
- IdP metadata XML / FederationMetadata.xml
- X509 certificate
- Relay State (= tenantID)
- OAuth `<client_id>` / `<client_secret>` (placeholders only — not reproduced)

---

## Modules Mentioned

- [[modules/sso]] — primary module documented
- [[modules/employee-experience]] — Emp-exp POD named as owning POD in related SOP (prior sources)
- [[modules/ms-teams-integration]] — implicitly: Azure AD is the IdP for Teams integration

---

## Decisions Extracted

None. No architecture or technology decisions are made in these docs; they document an existing integration surface. The protocol choice (SAML vs OAuth) is a client-driven selection based on IdP compatibility, not a WIS architectural decision.

---

## Config / Surface Notes

**SAML surface** (from Doc 1):
- SP Entity IDs and ACS URLs confirmed per environment (see Key Takeaways table above).
- Relay State = `tenantID` (client's WorkInSync tenant identifier).

**Mobile PMS properties** (from Doc 2):

| Property | Default | Notes |
|----------|---------|-------|
| `EnableSsoOnMobile` | `False` | Enables SSO on mobile app |
| `ssoMandatory` | `False` | Removes OTP fallback option from SSO page |

---

## Secrets Redacted

**NONE found.** Both source documents were scanned clean of credentials before extraction:
- No OAuth `client_secret` values, no `GOCSPX-...` Google secrets, no `*.apps.googleusercontent.com` ClientIds.
- No X509 certificate blocks (`-----BEGIN CERTIFICATE-----`).
- No JWT tokens (`eyJ...`), Bearer tokens, or Base64-encoded credentials.
- No real email addresses (test-user emails are described by role, not reproduced).

Note: the existing `wiki/modules/sso.md` OAuth section already documents that the original `MIS_OAuth_OnBoarding.pdf` source contained "Sample Data" values resembling real Google OAuth credentials — those were not reproduced in the prior ingest and are not present in this source either. The OAuth section in the module correctly shows `<client_id>` / `<client_secret>` placeholders.

---

## Wiki Pages Created / Updated

- **CREATED:** [[runbooks/sso-integration-setup]] — new end-to-end SE SSO onboarding runbook
- **CREATED:** [[sources/se-runbook-sso]] — this source summary
- **AUGMENTED:** [[modules/sso]] — added `## Related Runbooks` section; appended `[[sources/se-runbook-sso]]` to frontmatter `source:` string; updated OAuth open question with note that the 2024 guide exists but is SAML-only; `last_updated` preserved at `2024-09-25` (April 2024 Complete Guide is older)
- **UPDATED:** [[index]] — header counts 145→147, Runbooks 27→28, Sources 50→51; added 1 Runbooks row + 1 Sources row

_Source: [[sources/se-runbook-sso]]_
