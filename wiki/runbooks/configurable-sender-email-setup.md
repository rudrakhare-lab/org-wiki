---
type: runbook
module: employee-experience
team: SE
status: active
last_updated: 2026-06-29
source: "[[sources/se-runbook-employee-experience]]"
raw_path: raw/se-runbook/crawl/files/1ZIujGX_qSsMDIJNMwZXYPKsvUjDwbrgs8RAJgqQKW6E.docx
---

# Runbook — Configurable Sender Email (per-BUID outbound email "from" address)

## Purpose
Set the outbound **sender ("from") email address** used for a BUID's WorkInSync emails, via
the `emp-exp` service. Lets a client receive WorkInSync emails from a chosen address (e.g.
`noreply@workinsync.io` or a client-configured address) instead of the default
`transport@moveinsync.com`. Reference ticket: **PB-22330**.

## Prerequisites
- The BUID is known.
- A valid `x-wis-token` for the `emp-exp` service (`empexp.moveinsync.com`).
- The desired sender email address (URL-encode the `@` as `%40` in the query string).
- To use a *custom* configurable address (TC_2 below), an entry for that BUID must exist in
  the `configurable_emails` table — confirm/seed this with the owning team if absent.

## Ordered Steps
1. Decide the target sender address for the BUID (e.g. `noreply@workinsync.io`).
2. Call the configure-sender API via Postman (GET):
   ```
   GET https://empexp.moveinsync.com/employee-exp/buid/{buid}/status/update
       ?buid=<BUID>
       &configEmail=<url-encoded-email>     # e.g. noreply%40workinsync.io
       &wisBuEnabled=true
   Header: x-wis-token: <token>
   Header: accept: */*
   ```
3. Confirm the response indicates success.
4. Validate by triggering a WorkInSync email for that BUID and checking the **From** address
   (see Validation).

## Sender-address resolution precedence
The effective "from" address resolves by this precedence (from the PB-22330 test cases):

| # | Condition | Resulting sender |
|---|-----------|------------------|
| TC_1 | BUID is **Stratus-enabled** | `noreply@workinsync.io` |
| TC_2 | Not Stratus-enabled **and** `wisBuEnabled=true` **and** a `configurable_emails` entry exists for the BUID | the **configurable email** |
| TC_3 | Not Stratus-enabled **and** `wisBuEnabled=false` | `transport@moveinsync.com` (default) |
| TC_4 | BUID is **neither Stratus nor wis** (empty / not authentic) | `transport@moveinsync.com` (default) |

> ⚠️ A Stratus-enabled BUID always sends via `noreply@workinsync.io` (TC_1) — the
> `configEmail` value only takes effect for **non-Stratus** BUIDs with `wisBuEnabled=true`
> and a matching `configurable_emails` table entry (TC_2).

## Validation
- Trigger any WorkInSync email for the BUID and confirm the **From** header matches the
  expected address per the precedence table above.

## Notes & Gotchas
- `noreply@workinsync.io` and `transport@moveinsync.com` are **system sender addresses**
  (documented product behavior), not credentials.
- URL-encode the email's `@` as `%40` in the query string.
- The `x-wis-token` is service-scoped and must be kept secret — never paste a real token into
  the wiki or a shared doc.

## Related Jira
- PB-22330 — Configurable sender email API

## Linked Raw Evidence
- `raw/se-runbook/crawl/files/1ZIujGX_qSsMDIJNMwZXYPKsvUjDwbrgs8RAJgqQKW6E.docx` — PB-22330 configurable sender email (API + test cases)

_Source: [[sources/se-runbook-employee-experience]]_
