---
type: source
raw_path: raw/modules/third-party/WiS - Slack Integration.pdf
ingested: 2026-05-26
doc_type: spec
---

# WiS — Slack Integration

## Source Title
WorkInSync - Slack Integration

## Date
10/03/2022 (v1.0 approved 10-Mar-2022; "Initial document"). **No subsequent revisions** — document is v1.0 only, ~3 years stale relative to the current product. Classification: **Confidential**.

## Type
spec

## Key Takeaways
- The WorkInSync app on Slack lets users **book WFO seats**, **create WFH bookings**, **edit/cancel bookings**, **find where colleagues are working today**, and **search colleagues** — all from the app's **Home tab** (page 3 of source).
- **Alerts and notifications** push messages when a teammate checks in (office or home) or clocks out (page 3 of source).
- **Automatic Slack status updates** — quote (page 4): *"WorkInSync updates your status as 'Working from Home' or 'Working from office' as you check-in for your colleagues to quickly see."*
- **Installation** is a 6-step Slack-workspace flow including a **"Connect your account"** step (page 2 of source). The source explicitly handles the case where the workspace admin has restricted third-party app installs — quote: *"please reach out to your workspace admin to allow installation of the WorkinSync app"*.
- **Onboarding for new users** — quote (page 4): *"If the user does not have an active WorkInSync registered account, they can perform onboarding from the Slack app which redirects them to the signup page."*
- **Permissions are described categorically, not by OAuth scope name** (page 4): *"Retrieval of user's name, email, Slack user ID and icon"* and *"Retrieval of User Access token, Bot token and Bot channel ID for a user from the Slack app."* The source does NOT name specific Slack OAuth scopes (e.g., `users:read`, `chat:write`).
- ⚠️ **DATA-STORAGE CONTRADICTION** — the source contains four statements about WorkInSync's data handling via Slack that are mutually inconsistent:
  1. Page 4 (lines 90–91 of extract): *"Security and a good user experience is always paramount at WorkInSync. Keeping that in mind, user details are only viewed and not stored."*
  2. Page 4 (lines 97–99 of extract): *"WorkInSync stores all PII (Personally Identifiable Information) in an encrypted format and is retained as long as it is necessary to achieve the purpose for which it was collected or received."*
  3. Page 5 (lines 110–112 of extract): *"WorkInSync as an organization does not collect any data via the Slack app. No personal information is ever transferred to affiliated entities, or to other third parties."*
  4. Page 5 (line 113 of extract): *"WorkInSync does not store any user data in persistent storage."*
  These cannot all be simultaneously true. "Viewed not stored" vs "stores all PII encrypted" vs "does not store... in persistent storage" vs "does not collect any data" must be reconciled before this doc is cited for any compliance-sensitive answer. **Do not select an interpretation from this source alone.**
- **Slack's own compliance posture** is cited (page 5) — **SOC 2**, **SOC 3**, **ISO/IEC 27001**; **GDPR compliant**; configurable for **HIPAA** and **FINRA**; **Enterprise Key Management** (admin control over data encryption); **Slack Connect** (cross-org channels). _Note:_ these are **Slack's** certifications, not WorkInSync-specific claims about the WIS Slack app itself.

## Entities Mentioned
(none — operational / promotional doc; no WorkInSync data entities introduced)

## Modules Mentioned
- [[modules/third-party]] (primary subject — Slack integration is under the canonical `third-party` slug)

## Decisions Extracted
(none — descriptive doc; no architectural decisions with alternatives + rationale)

## Wiki Pages Created/Updated
- Created: [[modules/third-party]]
- Updated: [[index]], [[log]]

_Source: [[sources/wis-slack-integration]]_
