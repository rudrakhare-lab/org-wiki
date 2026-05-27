---
type: source
raw_path: raw/modules/sso/SSO with WorkInSync (OKTA) (1).pdf
ingested: 2026-05-27
doc_type: spec
---

# SSO with WorkInSync — Okta (SAML 2.0)

## Source Title
SSO with WorkInSync (OKTA). NOTE: the doc-control Document-Name field reads "SSO with SCIM to WorkInSync (OKTA)" — see the SCIM-misnomer takeaway below.

## Date
Jul 15, 2022 (v1.1). Version history: v1.0 Rishabh / approved Ujjwal ("First Version"); v1.1 Aditya Dutta / Ujjwal / 27/06/2023 ("Mobile SSO section"). Classification: Confidential. The filename's "(1)" suffix is a Drive filename artifact, not a version indicator (actual version is 1.1).

## Type
spec

## Key Takeaways
- **⚠️ "SCIM" misnomer in the Document Name.** The doc-control Document-Name field reads *"SSO with SCIM to WorkInSync (OKTA)"*, but the content is **unambiguously SAML 2.0 SSO** (quote: *"Select SAML 2.0 as the Sign-on method"*). **SCIM is the PROVISIONING protocol** covered by [[modules/employee-provisioning]], NOT the SSO protocol. Template residue from earlier documentation — do not conflate this SAML SSO doc with SCIM provisioning.
- **Okta SAML 2.0 setup**: Admin Console → Applications → Create App Integration → SAML 2.0 → configure SAML settings → share metadata back to WorkInSync.
- **SAML config fields**: Single sign-on URL (= ACS URL for the SP), Audience URI (SP Entity ID), Default RelayState (post-login landing page), Name ID format (default Unspecified), Application username.
- **Functionally parallel to the Azure AD SAML doc** ([[sources/sso-azure-ad]]) — same SAML 2.0 protocol, same SP-metadata exchange, different IdP front-end (Okta App Integration Wizard vs Azure Enterprise Applications).
- v1.1 added a Mobile SSO section. Screenshot-heavy (Okta UI steps; some pages are images not captured in text). Links to Okta's official SAML wizard documentation.

## Entities Mentioned
(none)

## Modules Mentioned
- [[modules/sso]] (primary subject)
- [[modules/employee-provisioning]] (referenced only to disambiguate the "SCIM" misnomer — SCIM provisioning lives there, not in SSO)

## Decisions Extracted
(none)

## Wiki Pages Created/Updated
- Created: [[modules/sso]]
- Updated: [[index]], [[log]], [[glossary]]

_Source: [[sources/sso-okta]]_
