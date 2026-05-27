---
type: source
raw_path: raw/modules/sso/MIS_OAuth_OnBoarding.pdf
ingested: 2026-05-27
doc_type: spec
---

# MIS OAuth Onboarding — OAuth 2.0 Integration Guide

## Source Title
OAuth 2.0 Integration Guide (MIS_OAuth_OnBoarding)

## Date
Undated — the source has no version/date/document-control table. Treat as a bare integration guide of unknown vintage.

## Type
spec

## Key Takeaways
- **OAuth 2.0 / OpenID Connect SSO** via MoveInSync's mis-auth service. Callback base URL: `https://auth.moveinsync.com/mis-auth/login/oauth2/code/{registration-id}` (prod) and a stage equivalent (testing/sanity only). Quote: *"registration-id is the buid that should be shared by the MoveInSync team"*.
- Optional logout URL: `https://auth.moveinsync.com/mis-auth/sso/logout`.
- **Details the client's Authorization Server must supply to MoveInSync**: ClientId, Client Secret, Scopes (`"openid"`, `"email"`), Authorization URL, Token URL, JWK Set URL, UserInfo URL (optional).
- The worked example uses **Google** as the IdP (accounts.google.com / googleapis.com endpoints); screenshots show OAuth SSO setup on **Microsoft Azure App Registration** (4 steps; page 4 is a screenshot not captured in text).
- **⚠️ Credentials redacted**: the source's "Sample Data" includes a Google-format ClientId and Client Secret. These look like real Google OAuth credentials and are NOT reproduced — rendered as `<client_id>` / `<client_secret>` per the wiki's no-credentials rule.
- This is the **OAuth / OIDC** path — distinct from the SAML 2.0 path in [[sources/sso-okta]] and [[sources/sso-azure-ad]].

## Entities Mentioned
(none)

## Modules Mentioned
- [[modules/sso]] (primary subject)

## Decisions Extracted
(none)

## Wiki Pages Created/Updated
- Created: [[modules/sso]]
- Updated: [[index]], [[log]], [[glossary]]

_Source: [[sources/sso-oauth-onboarding]]_
