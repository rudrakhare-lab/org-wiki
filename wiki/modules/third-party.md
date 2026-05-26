---
type: module
status: active
owner: unknown
depends_on: []
used_by: []
last_updated: 2022-03-10
source: "[[sources/wis-slack-integration]]"
---

# Third-Party Integrations Module — Slack

## Overview
**WorkInSync's Slack integration** is a Slack-workspace app that exposes WorkInSync booking
and presence inside the user's Slack client. From the app's **Home tab**, users can book
WFO seats, create work-from-home bookings, edit or cancel bookings, find where colleagues
are working today, and search colleagues. The app pushes **alerts and notifications** when
teammates check in (office or home) or clock out, and **automatically updates the user's
Slack status** to *"Working from Home"* or *"Working from office"* on check-in. The Slack
app is installed at the workspace level with a per-user account-connection step.

## Purpose & Scope
Owns the Slack-app surface: the workspace installation flow, the user account-linkage
("Connect your account") step, the Home tab feature set, the push-notification channel
for check-in/clock-out events, and the Slack-status update mechanic.

Does **not** own: the underlying booking systems (the Slack app surfaces WFO booking, WFH
booking, edit, cancel — those operations are owned by other WorkInSync modules; the source
does not name which), Slack workspace identity itself (handled by Slack's own OAuth /
"Allow" flow at install time, NOT by the WorkInSync `sso` module), or the WorkInSync
account-creation pipeline (the onboarding redirect leads to the WorkInSync signup page —
not described in this source).

⚠️ **Source contains four mutually inconsistent data-storage statements** — see Open
Questions. This module page does not make a claim about WorkInSync's actual data-storage
practice via Slack; the source's own statements must be reconciled with engineering before
this can be answered.

## Key Features
- **Workspace install with per-user account connection**: 6-step Slack-workspace flow (page 2 of source) — search WorkInSync in the Slack apps directory, install, click `Connect your account` on the Home tab, review permissions, click `Allow`. On completion the app is configured and ready
- **Workspace-admin restriction handling**: if the organization restricts third-party app installs, the user is instructed to *"reach out to your workspace admin to allow installation of the WorkinSync app"* (quote from page 2)
- **WFO and WFH booking from the Home tab**: book a seat in office for in-office work, create a work-from-home booking, edit or cancel an existing booking
- **Colleague location lookup**: find where a colleague is working today; search colleagues; view booking details; create a new booking from a colleague's context
- **Check-in / clock-out notifications**: receive Slack messages when teammates check in (office or home) or when teammates clock out
- **Automatic Slack status updates**: WorkInSync updates the user's Slack status to *"Working from Home"* or *"Working from office"* on check-in, visible to colleagues
- **Onboarding redirect for new WorkInSync users**: if the Slack user does not have an active WorkInSync registered account, the Slack app redirects them to the WorkInSync signup page for onboarding
- **Inherits Slack's compliance posture**: by virtue of running on Slack's infrastructure, the integration inherits Slack's certifications — **SOC 2**, **SOC 3**, **ISO/IEC 27001**, **GDPR compliant**; configurable for **HIPAA** and **FINRA**; supports **Enterprise Key Management** (admin-controlled encryption) and **Slack Connect** (cross-org channels). _Note:_ these are Slack's own claims; the source does NOT make WorkInSync-specific compliance claims for the Slack app (no Publisher-Attested-equivalent for this integration)

## Data Entities Used
(none — this module is a Slack-surface integration; existing entities like [[entities/booking]] are referenced only implicitly through the booking-surface features above)

## Dependencies on Other Modules
(none declared in frontmatter — see Open Questions for the implicit module dependencies the source describes but does not name)

## Used By
(none declared in frontmatter — see Open Questions for the implicit upstream consumers that push check-in/clock-out events to this integration)

## API Endpoints
This module does **not** expose WorkInSync HTTP endpoints. It consumes Slack APIs under the data-retrieval permission categories named in the source (page 4):

| Permission category (as-named in source) | Use |
|---|---|
| User's **name** | User identity in Slack |
| User's **email** | WorkInSync account lookup; account creation on missing match |
| User's **Slack user ID** | Slack-side identification |
| User's **icon** | Profile picture |
| **User Access token** | OAuth user token for the WorkInSync app's API calls on behalf of the user |
| **Bot token** | OAuth bot token for the WorkInSync app's bot-mode operations |
| **Bot channel ID** | Channel identifier for bot-context messaging |

_Note: the source describes permissions **categorically** (what data is retrieved) rather than by Slack OAuth scope name. Specific Slack scopes (e.g., `users:read`, `users:read.email`, `chat:write`, `team:read`) are NOT named in this source. Update this table when an engineering reference or the Slack app manifest is ingested._

## Open Questions
- ⚠️ **DATA-STORAGE CONTRADICTION** — the source contains four mutually inconsistent statements about WIS's data handling via Slack:
  1. Page 4 of source (line 90–91 of `/tmp/third_party_full_extract.txt`): *"Security and a good user experience is always paramount at WorkInSync. Keeping that in mind, user details are only viewed and not stored."*
  2. Page 4 of source (line 97–99 of extract): *"WorkInSync stores all PII (Personally Identifiable Information) in an encrypted format and is retained as long as it is necessary to achieve the purpose for which it was collected or received."*
  3. Page 5 of source (line 110–112 of extract): *"WorkInSync as an organization does not collect any data via the Slack app. No personal information is ever transferred to affiliated entities, or to other third parties."*
  4. Page 5 of source (line 113 of extract): *"WorkInSync does not store any user data in persistent storage."*
  These cannot all be simultaneously true. **Do not cite this doc for compliance answers** until engineering reconciles the four statements.
- ⚠️ **Source freshness** — this is the **only** version of the doc (v1.0, dated 2022-03-10). It is ~3 years old. The Slack integration's feature set, permissions, and storage practices may have evolved since. The module page does not assume current accuracy.
- **Implicit module dependencies not named** — the Slack app surfaces WFO seat booking, WFH booking, edit/cancel, and colleague location lookup. These features must be backed by WorkInSync backend APIs in other modules (likely `desk-management` for WFO/WFH booking; possibly `employee-experience` for colleague-presence). The source does NOT name which modules provide these capabilities.
- **Implicit upstream consumers not named** — check-in and clock-out events must be pushed to this integration from some upstream module (likely `desk-management` for check-in, possibly others for clock-out). The source does NOT name which modules push these events.
- **WorkInSync account linkage mechanism** — the source mentions a "Connect your account" step and a signup redirect for users without a WIS account, but does NOT describe the account-matching logic (email match? manual entry on the signup page?).
- **Slack OAuth scope names** absent — see API Endpoints `_Note:_` above. Specific Slack scopes are not in this source and would need to be confirmed from the Slack app manifest or engineering reference.
- **Module owner** — author **Aditya Dutta** (same as MS Teams doc), approver **Nitin Awasthi**. No owning team named.
- **Inherited vs WIS-specific compliance** — Slack's certifications (SOC 2, SOC 3, ISO 27001, GDPR, configurable HIPAA/FINRA) are cited. The source does NOT make WorkInSync-specific compliance claims for the Slack app surface (no Publisher-Attested-equivalent claim). Readers should not attribute Slack's compliance posture to WorkInSync itself.

## Last Updated
2022-03-10 — _Source: [[sources/wis-slack-integration]]_ (v1.0)
