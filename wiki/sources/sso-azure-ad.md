---
type: source
raw_path: raw/modules/sso/WorkInSync SSO integration - Azure AD.pdf
ingested: 2026-05-27
doc_type: spec
---

# WorkInSync SSO — Azure AD (SAML 2.0)

## Source Title
WorkInSync Single Sign On - Azure AD (Applicable for workinsync.io based client urls)

## Date
v1.2 (Last Modified 01/02/2022; v1.2 dated 27/06/2023 "Mobile SSO section"). Version history: v1.0 Manvi / Nitin Awasthi / 15/12/2021 ("First version"); v1.1 Nitin Awasthi / Akash M / 01/02/2022 ("Title update"); v1.2 Aditya Dutt / Ujjwal / 27/06/2023 ("Mobile SSO section"). Classification: Internal.

## Type
spec

## Key Takeaways
- **SAML 2.0 SSO with WorkInSync as the Service Provider.** Quote: *"WorkInSync application supports SSO SAML 2.0 and can integrate with any Identity Provider ... WorkInSync is the Service provider or relying party"*.
- **Client provides**: Issuer/Entity ID, Login + Logout Redirect URLs, X509 Certificate, and which IdP tool (ADFS / Pingdom Federation / Shibboleth). **Shortcut for ADFS / Azure AD**: share only the `FederationMetadata.xml` file.
- **WorkInSync provides**: Relay URL (client site URL, e.g. `https://<client>.workinsync.io`), Target URL (SAML response endpoint), Redirect URL (post-auth landing, same as Relay URL), Relay State (= the client's WorkInSync tenantID).
- **⚠️ Username type: Email ID only.** Quote: *"WorkInSync currently supports only one username type: i.e. Email ID (Other username type e.g. employee ID are not supported as of now)"*. (See the SSO module Open Questions for the conflict with the SOP intake doc.)
- **Azure AD setup**: Enterprise Applications → Create your own application (Non-gallery) → Set up single sign-on → SAML → upload SP metadata file (`workinsync-prod-sp.xml` or similar) → fill reply URL + relay state (tenantID). Network whitelist: `code.jquery.com`.
- **⚠️ Duplicate filing**: this exact PDF (2,431,014 bytes) exists identically in BOTH `raw/modules/sso/` and `raw/modules/employee-provisioning/`. The `sso/` copy is canonical (content is unambiguously SSO/SAML) and is the source ingested here. The `employee-provisioning/` copy is left in place — a documentation-hygiene item for a future pass; NOT deleted (file-deletion is deliberately avoided in this codebase).

## Entities Mentioned
(none)

## Modules Mentioned
- [[modules/sso]] (primary subject)

## Decisions Extracted
(none)

## Wiki Pages Created/Updated
- Created: [[modules/sso]]
- Updated: [[index]], [[log]], [[glossary]]

_Source: [[sources/sso-azure-ad]]_
