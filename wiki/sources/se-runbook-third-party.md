---
type: source
ingested: 2026-06-29
doc_type: misc
---

# Source Summary — SE Runbook: Third-Party (Slack) Topic

> The SE-crawl Slack doc is the **docx variant** of the same document the
> `third-party` module is already sourced from ([[sources/wis-slack-integration]],
> a PDF in `raw/modules/third-party/`). Same content, version, and date — a Google
> Drive format duplicate. No new facts were added to the module; this ingest adds the
> missing operational install runbook and homes the crawl docx.

## Source Documents Covered

| Doc Title | Raw File | Version / Date | Type |
|-----------|----------|----------------|------|
| WorkInSync - Slack Integration (Document Control) | `raw/se-runbook/crawl/files/1JlkEkXtiVCSARAUJzf5iDjX0J4IFEn_gGRPIvOjimmQ.docx` | v1.0 / 2022-03-10 | docx |

**Canonical duplicate (already ingested):** `raw/modules/third-party/WiS - Slack Integration.pdf`
→ [[sources/wis-slack-integration]] (PDF variant, same v1.0 / 2022-03-10 content).

## Source Title
WorkInSync - Slack Integration

## Date
2022-03-10 (v1.0; author Aditya Dutta, approver Nitin Awasthi)

## Type
misc — product/integration control document (also a CS-facing install guide)

## Key Takeaways
- Slack workspace app exposing WorkInSync booking + presence from the **Home tab**
  (WFO/WFH booking, edit/cancel, colleague-location lookup, search).
- **Install flow** is a self-service 6-step end-user flow (search → install → Connect your
  account → review permissions → Allow); **workspace-admin approval** is required if the org
  restricts third-party apps.
- Pushes **check-in / clock-out notifications** and **auto-updates Slack status**
  ("Working from Home" / "Working from office").
- New WorkInSync users are **redirected to the signup page** for onboarding from the Slack app.
- Permissions are described **categorically** (name, email, Slack user ID, icon, User Access
  token, Bot token, Bot channel ID) — **no Slack OAuth scope names** are given.
- ⚠️ The doc contains **four mutually inconsistent data-storage statements** — not citable
  for compliance answers until engineering reconciles them (already flagged in
  [[modules/third-party]] Open Questions).
- Compliance certifications cited (SOC 2/3, ISO 27001, GDPR, configurable HIPAA/FINRA, EKM,
  Slack Connect) are **Slack's own** posture, not WorkInSync-specific claims.

## Entities Mentioned
- [[entities/booking]] — referenced implicitly via the Home-tab booking surface

## Modules Mentioned
- [[modules/third-party]] — primary module
- Implicit (unnamed in source): `desk-management` (WFO/WFH booking + check-in backend),
  possibly `employee-experience` (colleague presence)

## Decisions Extracted
None — operational/integration control doc, no architecture decisions.

## Config Properties Documented
None — no PMS config properties in this source.

## Secrets Redacted
None found. The extracted text contains no Slack tokens (`xoxb-`/`xoxp-`), no JWTs, no
`client_secret`, and no real credentials — permissions are described categorically only.

## Wiki Pages Created / Updated
- **Created:** [[runbooks/slack-workspace-install]]
- **Created:** [[sources/se-runbook-third-party]] (this page)
- **Updated:** [[modules/third-party]] — appended this source to `source:`; added a
  `## Related Runbooks` section linking the install runbook (no other prose changed;
  `last_updated` preserved at 2022-03-10)

## Open Questions
- Carried forward from [[modules/third-party]]: the 4-way data-storage contradiction, the
  unnamed backing modules for booking/check-in, the missing Slack OAuth scope names, and the
  2022 source freshness. No new evidence here resolves them.
