---
type: runbook
module: sso
team: SE
status: active
last_updated: 2026-06-29
source: "[[sources/se-runbook-sso]]"
raw_paths:
  - raw/se-runbook/crawl/files/1zf6BBHL5DjgGdrUW9oct5lTxi38oSu0jKcrWRInto2o.docx
  - raw/se-runbook/crawl/files/1zKkshEHwlJEcx7VmBoNLGTLgCaQUKbH5gD2ksZoOsn8.pptx
---

# SSO Integration Setup

End-to-end SE runbook for onboarding a client onto WorkInSync Single Sign-On (web and mobile).

## Purpose

This runbook guides an SE through the full SSO integration lifecycle: TechOps ticket intake, protocol selection, metadata exchange, IdP-specific configuration (SAML path), OAuth credential wiring (OAuth path), mobile enablement, validation, and cert-rotation handling. It distils the multi-source SSO documentation in [[modules/sso]] into an ordered SE checklist.

## Prerequisites

- You have login access to the TechOps (TO) ticketing portal.
- The client has an IdP (Azure AD, Okta, ADFS, Google, or another SAML/OIDC provider).
- You know which WorkInSync site type the client is on (see Step 1 intake).
- For SAML: the client's Azure AD admin (or IdP admin) is available to co-ordinate.
- For cert rotation: ≥2 weeks notice from client before the IdP cert expiry.

---

## Ordered Steps

### Step 1 — Raise the TechOps Ticket

Raise a ticket in the TO system before beginning any configuration work.

**Intake fields to capture:**

| Field | Values / Notes |
|-------|----------------|
| Site type | Production SG / Production Mumbai (.in) / POC / UAT |
| Protocol | SAML 2.0 OR OAuth 2.0 / OIDC |
| IdP tool | Azure AD / ADFS / Okta / Ping Identity / Shibboleth / Google / other |
| Username type | Email ID OR Employee ID (see ⚠️ gotcha in Notes) |
| Requestor | Client contact + internal SE owner |

**SLA tiers (4 working days default):**

| Priority | Condition | SLA |
|----------|-----------|-----|
| Minor | No active service disruption | 4 working days |
| Major | Partial service disruption | 4 working days |
| Critical | Full service down | 4 working days |
| P0 | Business-critical with approval | 1 working day |

_Source: [[sources/se-runbook-sso]]_

---

### Step 2 — Choose Protocol by IdP

| IdP / Scenario | Protocol |
|----------------|----------|
| Azure AD, ADFS | SAML 2.0 (FederationMetadata.xml shortcut available) |
| Okta | SAML 2.0 (App Integration Wizard path) |
| Ping Identity, Shibboleth | SAML 2.0 |
| Google OAuth, Azure App Registration (OAuth) | OAuth 2.0 / OIDC |
| Other OIDC-compliant provider | OAuth 2.0 / OIDC |

WorkInSync supports both protocols concurrently. Select the one matching the client's IdP and follow the corresponding path (Step 3 for SAML, Step 4 for OAuth).

_Source: [[sources/se-runbook-sso]]_

---

### Step 3 — SAML 2.0 Path

#### 3a. Select the correct SP metadata file by site type

MoveInSync operates four distinct SAML SP environments. Use the metadata file that matches the client's site:

| Site type | SP metadata file | SP Entity ID | ACS / Reply URL |
|-----------|-----------------|--------------|-----------------|
| Production (SG / global) | `moveinsync-sp.xml` | `moveinsync` | `https://accounts.moveinsync.com/saml/SSO/alias/moveinsync` |
| POC / pre-sales testing | `moveinsync-poc-sp.xml` | `moveinsync-poc` | `https://accountspoc.moveinsync.com/saml/SSO/alias/moveinsync-poc` |
| UAT (staging) | `moveinsync-uat-sp.xml` | `moveinsync-uat` | `https://serviceuat.moveinsync.com/accounts/saml/SSO/alias/moveinsync-uat` |
| Production Mumbai / `.in` | `moveinsync-mum-sp.xml` | `moveinsync-mum` | `https://accounts.moveinsync.in/saml/SSO/alias/moveinsync-mum` |

> ⚠️ Each site has a distinct SP metadata file. Using the wrong file for the client's environment will cause SSO to fail silently at the SAML trust validation step.

> ⚠️ The UAT environment (`serviceuat`) should be used for testing/sanity only — do not point a production client at UAT endpoints.

#### 3b. SP metadata exchange

**What WorkInSync provides to the client:**

| Item | Value |
|------|-------|
| SP metadata XML | Site-specific file from table above |
| Relay URL | Client's WorkInSync site URL |
| Target URL | SAML response endpoint |
| Redirect URL | Post-auth landing = Relay URL |
| Relay State | Client's WorkInSync `tenantID` |

**What the client provides to WorkInSync:**

| Item | Notes |
|------|-------|
| IdP metadata (file or link) | Issuer / Entity ID, Redirect URLs (login + logout), X509 Certificate — OR for Azure AD / ADFS: `FederationMetadata.xml` or App Federation Metadata URL |
| Username type | Email ID or Employee ID (see ⚠️ note in Step 2) |
| Downtime window | 15–30 minutes for server restart during certificate upload |
| Test user profile | A user available in the MoveInSync ETS application to validate login |

#### 3c. IdP-specific setup — Okta

1. In Okta admin → **Applications** → **Create App Integration**.
2. Select **SAML 2.0**.
3. Upload the `moveinsync-sp.xml` (or site-appropriate file).
4. Set **Relay State** = client tenantID.
5. Download the Okta IdP metadata XML and send to the MoveInSync TO team.

#### 3d. IdP-specific setup — Azure AD

1. Sign in to **portal.azure.com** with an Azure AD administrator account.
2. Navigate to **Azure Active Directory → Enterprise Applications → New Application → Create your own application**.
3. Name the application (e.g., "MoveInSync SSO").
4. Under **Single Sign-On**, select **SAML**.
5. Upload the SP metadata file (e.g., `moveinsync-sp.xml`) via **Upload metadata file**.
6. Confirm the Basic SAML Configuration fields are pre-populated from the metadata.
7. Set **Relay State** = client tenantID.
8. Navigate to **SAML Signing Certificate** → download **Federation Metadata XML** (or copy the **App Federation Metadata URL**).
9. Share the downloaded file / URL with the MoveInSync TO team.

_Source: [[sources/se-runbook-sso]]_

---

### Step 4 — OAuth 2.0 / OIDC Path

The OAuth surface uses `auth.moveinsync.com/mis-auth` (not the `workinsync.io` SP domain).

**Endpoints:**

| Environment | OAuth Redirect URI |
|-------------|-------------------|
| Production | `https://auth.moveinsync.com/mis-auth/login/oauth2/code/{registration-id}` |
| Stage (sanity only) | `https://stage.moveinsync.com/mis-auth/login/oauth2/code/{registration-id}` |
| Logout (optional) | `https://auth.moveinsync.com/mis-auth/sso/logout` |

`registration-id` = the client's BUID (shared by the MoveInSync team at onboarding).

**What the client provides:**

| Item | Notes |
|------|-------|
| `<client_id>` | OAuth client ID issued by the IdP |
| `<client_secret>` | OAuth client secret (treat as credential — never log or commit) |
| Scopes | Minimum required: `openid`, `email` |
| Authorization URL | IdP's OAuth authorization endpoint |
| Token URL | IdP's token exchange endpoint |
| JWK Set URL | IdP's public key endpoint (for token validation) |
| UserInfo URL | Optional — IdP's userinfo endpoint |

> ⚠️ OAuth `<client_secret>` is client-specific and highly sensitive. Do not reproduce it in any ticket, wiki page, or log entry. Handle via secure channel to the TO team only.

_Source: [[sources/se-runbook-sso]]_

---

### Step 5 — Mobile SSO Enablement

Mobile SSO is disabled by default and must be enabled separately via a Consul/PMS property.

**Properties to set:**

| Property | Default | Description |
|----------|---------|-------------|
| `EnableSsoOnMobile` | `False` | Enables SSO on the mobile app. When true, app launch navigates to the SSO web page instead of OTP flow. |
| `ssoMandatory` | `False` | Removes the OTP login option from the SSO page, making SSO the only auth path. |

**Enablement procedure:**

1. Raise an SE ticket to enable `EnableSsoOnMobile` (TO assistance may be required in some cases).
2. Validate the mobile web SSO page is accessible and responsive on the client's device.
3. If the client wants to remove OTP as a fallback, set `ssoMandatory = True` as a follow-up config change.

**Behaviour:**
- When `EnableSsoOnMobile = True` and SSO is enabled: app launch → mobile-responsive SSO web page → authenticate → access granted.
- When `EnableSsoOnMobile = False` (or SSO disabled): existing OTP workflow is triggered.

> ⚠️ `ssoMandatory = True` removes the OTP fallback entirely. Ensure SSO is fully stable before setting this; a misconfigured IdP will lock users out of the mobile app.

_Source: [[sources/se-runbook-sso]]_ (mobile doc) — see also Jira PB-25542 for original feature tracking.

---

### Step 6 — Validation

**Per site type checklist:**

- [ ] Production: test login via `accounts.moveinsync.com` with a test user profile the client has provided.
- [ ] POC: test login via `accountspoc.moveinsync.com`.
- [ ] UAT: test login via `serviceuat.moveinsync.com` — note this is a stage environment, sanity only.
- [ ] Mumbai (.in): test login via `accounts.moveinsync.in`.
- [ ] Mobile (if enabled): validate SSO web page on iOS + Android for the client's IdP.
- [ ] Confirm the post-auth landing URL is correct (= Relay URL / client site URL).
- [ ] Confirm the Relay State (tenantID) is correctly configured — mismatched tenantID causes a successful SAML assertion but a failed WorkInSync session lookup.

---

## Screenshots / Visual Evidence

Screenshots for Azure AD configuration steps (Enterprise Applications panel, SAML setup dialog, Federation Metadata download) are in the raw source document. See raw evidence link below.

---

## Validation

After configuration, the TO team performs:
1. Certificate upload on the WorkInSync server.
2. Server restart (15–30 minute downtime window — schedule with client in advance).
3. Test login with the client-provided test user to confirm SSO authentication end-to-end.

A successful test is required before closing the TO ticket.

---

## Notes & Gotchas

1. **Username type — open conflict, do not assume Email-ID-only.** The older Azure AD SSO PDF states "only Email ID is supported (Employee ID not supported as of now)." The 2024 Complete Guide (v1.2, April 2024) lists **both** Email ID and Employee ID as supported username types. This conflict is documented in [[modules/sso]] Open Questions. Until the module page is updated with a confirmed resolution, capture the client's username type as a TO-ticket intake field and let the TO team validate against the current server configuration.

2. **Distinct SP metadata per site type.** Prod / POC / UAT / Mumbai are four separate SAML SPs. Always confirm which environment the client is being onboarded to before sharing a metadata file.

3. **OAuth `<client_secret>` is client-specific.** Never reproduce an OAuth client secret in any wiki page, ticket description, or log entry. Share only via secure channel (encrypted email or secrets manager).

4. **FederationMetadata.xml shortcut for ADFS/Azure.** For ADFS and Azure AD clients, they can share the `FederationMetadata.xml` file (or App Federation Metadata URL) in lieu of extracting the Issuer/Entity ID, Redirect URLs, and X509 certificate individually. This is the preferred path for Azure AD.

5. **Network whitelist.** The client's network may need to allowlist `code.jquery.com` for the SSO web pages to function correctly.

6. **Cert rotation (recurring activity).** When the IdP SAML certificate is approaching expiry:
   - Client must notify MoveInSync **at least 2 weeks before expiry**.
   - Client provides the latest IdP metadata XML (updated certificate).
   - MIS and client perform the certificate rotation **in parallel** — both sides update simultaneously.
   - MoveInSync side requires a server restart (15–30 min downtime — schedule downtime window with client).

7. **`ssoMandatory` lock-out risk.** Setting `ssoMandatory = True` on mobile before SSO is fully validated can lock users out of the mobile app with no OTP fallback.

8. **Stage URL for sanity only.** The `stage.moveinsync.com` OAuth redirect URI is for internal sanity testing. Do not share it with clients as a production configuration.

---

## Related Jira

- **PB-25542** — Original feature tracking for mobile SSO (`EnableSsoOnMobile` / `ssoMandatory`) enablement.

---

## Linked Raw Evidence

- `raw/se-runbook/crawl/files/1zf6BBHL5DjgGdrUW9oct5lTxi38oSu0jKcrWRInto2o.docx` — MoveInSync Web SSO Complete Guide (v1.2, 30/04/2024)
- `raw/se-runbook/crawl/files/1zKkshEHwlJEcx7VmBoNLGTLgCaQUKbH5gD2ksZoOsn8.pptx` — Login seamlessly on MoveInSync app via SSO (mobile)

_Source: [[sources/se-runbook-sso]]_
