---
type: source
ingested: 2026-06-29
doc_type: misc
---

# Source Summary: MS Teams Integration — SE Runbook

## Source Title

Two documents ingested together under this source page:

| # | Document Title | Version / Date | Raw Path |
|---|---|---|---|
| 1 | WorkInSync - Microsoft Teams App Universe (For CS/Sales) | Undated | `raw/se-runbook/crawl/files/1Y1sPEoN5JIu7LNWc1U3WJ2LnTp6ss9Iv1yRefd2eus0.docx` |
| 2 | WorkInSync - Microsoft Teams Integration (Control Document) | v1.1, 2022-06-20 | `raw/se-runbook/crawl/files/1pbXxmjFFlL_c1rwchY8vAhcCNUEKwRbWjZxm69CzRFE.docx` |

Doc 1 is a **CS/Sales source-of-truth index** — primarily a navigation page listing related specs
(Transactable SaaS offer, Road to 100K roadmap, permissions doc) with minimal standalone content.
Doc 2 is the **rich operational document** and is the primary source for this ingest.

## Date

- Doc 1: undated (internal CS/Sales deck)
- Doc 2: v1.0 authored 2022-03-08, v1.1 approved 2022-06-20 (inclusion of Transactable SaaS)

## Type

misc (CS/Sales value overview + internal control document)

## Key Takeaways

- **Two onboarding pathways** exist: (A) existing Stratus clients install the Free Teams app and log in with existing credentials — no re-payment, Teams is a direct port of Stratus; (B) new clients discovered via Teams choose a plan (Free/Standard/Professional), make a one-time purchase via Teams Marketplace or AppSource, and are onboarded via a landing page.
- **License management** is split across two systems: individual user assignment uses the WorkInSync portal (People → Employees); org-level seat-count changes use the Microsoft Admin Center (individual assignment is not possible there).
- **Admin consent vs. per-user consent**: an Azure AD admin can grant one-time org-wide consent so no individual user sees a consent prompt; without admin action, each user is prompted on first use.
- **Feature set in Teams** (as of 2022): Employee features (desk booking, WFH check-in/out, presence/teammate-finder, broadcast work location); People Manager features (start/end-of-day notifications, booking notifications, create/view bookings, team activity); conversational bot (book/fetch/modify/cancel seat, check-in/out, find teammate); Personal Tabs (Bookings Tab, Team Activity Tab); Team Tab (Team Activity Tab in shared channel).
- **Teams mobile auto-propagation**: installing the app via Teams web or desktop client automatically propagates to the Teams mobile client (this is Microsoft's Teams mobile, not the WIS `mobile-app` module).
- **Free plan cap**: the Free tier supports up to 50 users; Standard and Professional are the upgrade paths.
- **Doc 1 (CS/Sales)** serves as an internal index of related resources — it names but does not contain the Transactable SaaS spec, Road to 100K roadmap, and Permissions & Security doc (already ingested separately as `[[sources/ms-teams-app-permissions-security]]`).
- **Source is old (2022)**: the feature list, bot commands, tab structure, pricing plans, and consent UX should be verified against the current product before client-facing use.

## Entities Mentioned

(none — no new WorkInSync data entities are defined in these documents)

## Modules Mentioned

- [[modules/ms-teams-integration]] — primary subject of both documents
- [[modules/sso]] — implicit (existing Stratus credentials used; Azure AD SSO path)
- [[modules/desk-management]] — desk booking via bot / Teams app
- [[modules/employee-experience]] — WFH check-in/out, presence/broadcast features

## Decisions Extracted

None — no architecture decisions or explicit trade-offs documented. The two-pathway onboarding
model is a product design fact, not a recorded decision in these docs.

## Config / Feature Notes

- No PMS config properties mentioned in either document.
- Pricing tier feature-gating (what is paywalled at Free vs Standard vs Professional) defers
  to the "WiS Pricing Page" — not reproduced in these documents. This remains an open question
  in the module page.

## Secrets Redacted

**NONE.** No tokens, bearer credentials, client secrets, or real credentials appear in either
source document. `xyz@workinsync.io` appears in Doc 2 as an **explicitly illustrative placeholder**
(the text reads "xyz@workinsync.io" to represent a generic Stratus domain) — it is not a real
credential or email address and does not require redaction.

## Wiki Pages Created / Updated

| Action | Page |
|---|---|
| AUGMENTED | [[modules/ms-teams-integration]] — added `## Onboarding Pathways`, `## Features Exposed in Teams` (employee, people manager, bot commands, tabs); updated Open Question #1 from fully-open to partially-resolved; appended `[[sources/se-runbook-ms-teams]]` to frontmatter `source:` field; `last_updated` preserved at `2024-01-08` |
| CREATED | [[runbooks/ms-teams-integration-setup]] — IT-admin onboarding + install + consent + license-management runbook |
| CREATED | [[sources/se-runbook-ms-teams]] — this page |
