---
type: source
ingested: 2026-06-29
doc_type: misc
---

# Source Summary — SE Runbook: Employee Experience Topic

> Distilled from the emp-exp-specific SE crawl material. The `employee-experience` module is
> a thin host service; the one concrete new capability found in the SE crawl is the
> **configurable sender email** (PB-22330). Other emp-exp-adjacent crawl hits are release
> notes or belong to other modules (VMS notifications → [[modules/visitor-management]];
> indemnification form → safe-reach/ETS) and are not modelled here.

## Source Documents Covered

| Doc Title | Raw File | Date | Type |
|-----------|----------|------|------|
| PB-22330 — Configurable sender email (API + test cases) | `raw/se-runbook/crawl/files/1ZIujGX_qSsMDIJNMwZXYPKsvUjDwbrgs8RAJgqQKW6E.docx` | (undated) | docx |

## Source Title
PB-22330 — Configurable sender email

## Date
Undated (ticket-derived note).

## Type
misc — operational SE note (API + QA test cases).

## Key Takeaways
- The `emp-exp` service exposes a **configurable sender ("from") email** per BUID via
  `GET empexp.moveinsync.com/employee-exp/buid/{buid}/status/update?buid=&configEmail=&wisBuEnabled=`.
- **Sender-address resolution precedence**: Stratus-enabled BUID → `noreply@workinsync.io`
  (always); non-Stratus + `wisBuEnabled=true` + `configurable_emails` table entry → the
  configurable email; otherwise → `transport@moveinsync.com` (default).
- The `configEmail` value only takes effect for **non-Stratus** BUIDs (Stratus BUIDs always
  use `noreply@workinsync.io`).
- `noreply@workinsync.io` and `transport@moveinsync.com` are **system sender addresses**
  (product behavior), not credentials.
- A custom configurable address requires a `configurable_emails` table entry for the BUID.

## Entities Mentioned
- [[entities/employee]] — referenced via the emp-exp service context

## Modules Mentioned
- [[modules/employee-experience]] — primary (the emp-exp service hosts this capability)

## Decisions Extracted
None — operational/QA note, no architecture decision.

## Config Properties Documented
None as a PMS property — this is an **API capability** (per-BUID configurable sender email),
not a config-table row. Related config service: `EMAIL-EMP-EXPERIENCE`
([[configs/emp-experience-email]]).

## Secrets Redacted
**1 HS512 `x-wis-token` JWT** in the PB-22330 curl example → redacted to
`<HS512 JWT — redacted>` before ingestion. No other credentials present (the sender email
addresses shown are system addresses / product behavior, not secrets).

## Wiki Pages Created / Updated
- **Created:** [[runbooks/configurable-sender-email-setup]]
- **Created:** [[sources/se-runbook-employee-experience]] (this page)
- **Updated:** [[modules/employee-experience]] — added the configurable-sender-email capability
  to Known Features; appended this source; partially resolved Open Question #1 (other emp-exp
  features). `last_updated` preserved at 2024-02-27 (no newer dated source).

## Open Questions
- The PB-22330 note is undated — confirm current behavior with the owning team before client use.
- What other features live in the emp-exp service beyond delegation, wayfinding, and
  configurable sender email? (Carried forward from the module page.)
