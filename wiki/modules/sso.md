---
type: module
status: active
owner: unknown
depends_on: []
used_by: [ms-teams-integration]
last_updated: 2024-09-25
source: "[[sources/sso-oauth-onboarding]], [[sources/sso-integration-sop]], [[sources/sso-okta]], [[sources/sso-azure-ad]], [[sources/se-runbook-sso]]"
---

# SSO Module

## Overview
SSO (Single Sign-On) is WorkInSync's authentication-integration surface. WorkInSync acts as
the **Service Provider (SP)** and federates authentication to a client's **Identity Provider
(IdP)**. Two protocols are supported: **SAML 2.0** (via per-client `workinsync.io` URLs) and
**OAuth 2.0 / OpenID Connect** (via the `auth.moveinsync.com/mis-auth` service). The
integration is IdP-agnostic — Azure AD, Okta, ADFS, Google, or any compliant SAML/OIDC
provider. Setup is coordinated through a TechOps ticket process owned by the
employee-experience (Emp-exp) POD.

## Purpose & Scope
Owns the SSO authentication surface: SAML 2.0 and OAuth 2.0/OIDC integration, SP-metadata
exchange, the IdP onboarding process, and mobile SSO.

Does **not** own: employee data provisioning ([[modules/employee-provisioning]] — SCIM/SFTP
sync is a separate concern from authentication), per-vendor access-control auth
([[modules/access-management]] uses its own client-specific Basic→Bearer token, NOT SSO), or
the downstream modules that rely on an authenticated session.

## Key Features
- **SAML 2.0 support** — SSO via per-client `workinsync.io` Service Provider URLs; IdP-agnostic (any SAML 2.0 IdP). WorkInSync is the SP / Relying Party
- **OAuth 2.0 / OIDC support** — SSO via the `auth.moveinsync.com/mis-auth` service; the client's BUID is the OAuth `registration-id`; uses `openid` + `email` scopes
- **Mobile SSO** — mobile-app SSO support, added in v1.2 of both the Okta and Azure AD SAML docs (Aditya Dutta, 27/06/2023)
- **Multiple IdP support** — documented setup guides for **Azure AD** and **Okta**; also names **ADFS**, Pingdom Federation, Shibboleth, and Google; works with any SAML/OIDC-compliant IdP
- **TechOps integration process** — SSO setup is requested via a TechOps (TO) ticket, owned by the **Emp-exp POD** per the SOP. Site types: **Production SG, POC, UAT, Production Mumbai** (distinct SP metadata per site). SLA tiers: Minor/Major/Critical TOs require 4 working days' notice; P0 (Blocker) requires 1 working day with KDV/charan/Dibyendu approval

## Data Entities Used
(none — SSO is authentication; SAML metadata, X509 certs, and OAuth client credentials are operational artifacts, not WorkInSync data entities)

## Dependencies on Other Modules
(none — SSO is foundational authentication; it does not consume other modules. Note: the SOP names the employee-experience "Emp-exp" team as the owning POD for SSO integration *requests* — that is org/process ownership, not a runtime module dependency)

## Used By
(none declared — see ⚠️ Bidirectional-link asymmetry in Open Questions: `ms-teams-integration` declares `depends_on: [sso]`, but the SSO source docs do not reciprocally reference MS Teams)

## Integration Surfaces
WorkInSync is the Service Provider in all SSO flows. Two protocol surfaces:

### SAML 2.0
- **Base domain**: `<client>.workinsync.io` (per-client SP URL)
- **SP metadata exchange**: WorkInSync and the IdP exchange metadata to establish trust
- **Client provides**: Issuer ID / Entity ID, Redirect URLs (login + logout), X509 Certificate, and which IdP tool (ADFS / Pingdom / Shibboleth / etc.) — OR, for ADFS / Azure AD, just the `FederationMetadata.xml` file (shortcut)
- **WorkInSync provides**: Relay URL (client site URL), Target URL (SAML response endpoint), Redirect URL (post-auth landing = Relay URL), Relay State (= the client's WorkInSync tenantID)
- **Username type**: Email ID (see Open Questions — the Azure doc states only Email ID is supported)
- **Network whitelist**: `code.jquery.com`
- IdP setup guides: Okta (App Integration Wizard → SAML 2.0) and Azure AD (Enterprise Applications → SAML → upload SP metadata)

### OAuth 2.0 / OIDC
- **Base URL**: `https://auth.moveinsync.com/mis-auth/login/oauth2/code/{registration-id}` (prod); `https://stage.moveinsync.com/mis-auth/login/oauth2/code/{registration-id}` (stage — testing/sanity only)
- **Logout URL** (optional): `https://auth.moveinsync.com/mis-auth/sso/logout`
- **registration-id** = the client's BUID, shared by the MoveInSync team
- **Client provides**: ClientId (`<client_id>`), Client Secret (`<client_secret>`), Scopes (`"openid"`, `"email"`), Authorization URL, Token URL, JWK Set URL, UserInfo URL (optional)
- Worked example uses Google as the IdP; Azure App Registration screenshots are included for OAuth setup

_Note: OAuth ClientId and Client Secret are shown as placeholders — the source's "Sample Data" values look like real Google OAuth credentials and are not reproduced in the wiki._

## Related Runbooks
- [[runbooks/sso-integration-setup]] — end-to-end SE onboarding flow: TechOps intake, SAML/OAuth path selection, SP metadata exchange, IdP-specific steps (Okta, Azure AD), mobile SSO enablement, validation, cert rotation

## Open Questions
- ⚠️ Bidirectional-link asymmetry — ms-teams-integration declares depends_on: [sso] (grounded in the Teams doc's explicit Azure AD identity reference), but the SSO source docs do not reciprocally mention MS Teams. Source-fidelity prevails over mechanical bidirectionality. The link is real; the SSO docs simply predate or don't address the Teams integration. Tier 2.5 endgame should reconcile all such one-sided links (including visitor-management ↔ safe-reach noted from Wave A.3).
- **Username-type — resolved by recency (both Email ID and Employee ID supported):**
  - **Current (2024):** the MoveInSync Web SSO Complete Guide (v1.2, 2024-04-30) explicitly supports **both Email ID and Employee ID** as username types. _Source: [[sources/se-runbook-sso]]._
  - **Previously (2023):** the Azure SAML doc stated *"WorkInSync currently supports only one username type: i.e. Email ID (Other username type e.g. employee ID are not supported as of now)"* — superseded by the newer 2024 guide.
  - The SOP's TO-ticket intake field *"UserName Type: Email ID or Employee ID?"* is consistent with the current (both-supported) behavior.
  - ⚠️ The Integration Surfaces section above still reads `Username type: Email ID` (from the older 2023 doc) — flagged for the graph/recency sweep to update the SAML surface line to reflect both types.
- ⚠️ **Okta doc "SCIM" misnomer** — the Okta SAML doc's Document-Name field reads "SSO with SCIM to WorkInSync (OKTA)", but its content is unambiguously SAML 2.0 SSO. SCIM is the *provisioning* protocol (covered by [[modules/employee-provisioning]]), not SSO. Template residue; do not conflate.
- **OAuth-vs-SAML protocol coexistence** — WorkInSync SSO supports BOTH SAML 2.0 (workinsync.io SP) and OAuth 2.0/OIDC (auth.moveinsync.com/mis-auth). The sources do not rank one as "standard" vs "alternate"; both are offered. Implementers must pick the protocol matching their IdP and use the correct service surface.
- **OAuth doc is undated** — MIS_OAuth_OnBoarding.pdf has no version/date/control table. Freshness unknown; treat as a bare integration guide. Note: a 2024 Complete Guide now exists (v1.2, 30/04/2024) — see [[sources/se-runbook-sso]] — but it covers SAML/Azure AD only and does not address the OAuth surface, so this question remains open.
- **Regional site types** — the SOP names Production SG and Production Mumbai (plus POC/UAT) with distinct SP metadata files per site (parallels the .com/.in split elsewhere). Clients must use the SP metadata matching their site.
- **Duplicate filing** — "WorkInSync SSO integration - Azure AD.pdf" exists identically in both `raw/modules/sso/` and `raw/modules/employee-provisioning/`. The `sso/` copy is canonical (ingested here). The `employee-provisioning/` copy is left in place (documentation-hygiene item for a future pass; not deleted).
- **Module owner not named** — authors across docs: Manvi, Nitin Awasthi, Aditya Dutt (SAML); Rishabh (Okta); Shruthi Naik (SOP). Approvers: Nitin Awasthi, Akash M, Ujjwal Trivedi, Dheeraj. The SOP names Emp-exp as the owning POD, but no single owner team is stated for the module.

## Last Updated
2024-09-25 — _Source: [[sources/sso-oauth-onboarding]], [[sources/sso-integration-sop]], [[sources/sso-okta]], [[sources/sso-azure-ad]]_
