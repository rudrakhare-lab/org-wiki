---
type: runbook
module: third-party
team: SE
status: active
last_updated: 2026-06-29
source: "[[sources/se-runbook-third-party]]"
raw_path: raw/se-runbook/crawl/files/1JlkEkXtiVCSARAUJzf5iDjX0J4IFEn_gGRPIvOjimmQ.docx
---

# Runbook — WorkInSync Slack App: Workspace Install & Account Connection

## Purpose
Install the WorkInSync app into a client's Slack workspace and connect each user's
WorkInSync account, so users can book WFO/WFH seats, look up colleague locations, and
receive check-in/clock-out notifications from the app's **Home tab**. This is a
**self-service end-user / CS-assisted** flow — there is no SE backend configuration step
in the source doc.

## Prerequisites
- The user belongs to a Slack workspace registered with their organization.
- The user has (or will create) an active WorkInSync account — users without one are
  redirected to the WorkInSync signup page from the Slack app during onboarding.
- ⚠️ If the organization **restricts third-party app installs**, a Slack **workspace admin**
  must approve/allow the WorkInSync app first. End users cannot self-install under that
  restriction.

## Ordered Steps
1. In the target Slack workspace, click the **+** icon next to **Apps**.
2. Search for the **WorkInSync** app, select the application card, and click **Install**.
3. Open the **Home** tab inside the WorkInSync app and click **Connect your account**.
4. On the page that opens, **review the requested permissions**, then click **Allow**.
5. The app reports it is **configured and ready to use**.
6. (New WorkInSync users only) If the Slack user has no active WorkInSync registered account,
   follow the **signup redirect** from the Slack app to onboard, then repeat step 3.

## Validation
- The Home tab loads with booking actions (Book a seat / WFH booking / Edit / Cancel) and
  the colleague-lookup search.
- Performing a check-in updates the user's **Slack status** to *"Working from Home"* or
  *"Working from office"*.
- Teammates receive check-in / clock-out notification messages.

## Notes & Gotchas
- ⚠️ **Source is 2022 (v1.0, 2022-03-10)** — the install UX, requested permissions, and
  feature set may have evolved. Confirm the current Slack app listing and permission prompts
  before walking a client through this.
- ⚠️ **Data-storage policy is unresolved in the source** — the 2022 doc contains four
  mutually inconsistent statements about whether WorkInSync stores user data via Slack
  (see [[modules/third-party]] Open Questions). **Do not make compliance/data-storage
  claims to a client from this doc** until engineering reconciles them.
- Slack OAuth **scope names** are not specified in the source (permissions are described
  categorically — name, email, Slack user ID, icon, User Access token, Bot token, Bot
  channel ID). Confirm exact scopes from the Slack app manifest if a client's security team
  asks.
- Compliance certifications cited (SOC 2/3, ISO 27001, GDPR, configurable HIPAA/FINRA,
  Enterprise Key Management, Slack Connect) are **Slack's own** posture — not
  WorkInSync-specific claims for this integration.

## Related Jira
—

## Linked Raw Evidence
- `raw/se-runbook/crawl/files/1JlkEkXtiVCSARAUJzf5iDjX0J4IFEn_gGRPIvOjimmQ.docx` — WorkInSync Slack Integration Control Doc (v1.0, 2022-03-10; docx variant)
- `raw/modules/third-party/WiS - Slack Integration.pdf` — same document, PDF variant (the module's canonical source)

_Source: [[sources/se-runbook-third-party]]_
