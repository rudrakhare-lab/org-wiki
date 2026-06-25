---
type: source
raw_path: raw/se-runbook/WIS-Configurations-ETS-EmployeeApp-GuardApp-SanitisationApp.docx
ingested: 2026-06-25
doc_type: misc
---

# Source — WIS-Configurations (SE Runbook), sections 1–10: ETS Office Premise Setup

## Source Title
WIS-Configurations (ETS, Employee App, Guard app, Sanitisation App) — SE Service-Engineering runbook. 132-page, 34-tab Google Doc supplied by the WIS SE team. This source page covers **sections 1–10 only** (the ETS office-premise slice); remaining topics are ingested separately.

## Date
Document undated; ingested 2026-06-25. Live Google Doc id `1uwpRjNYuOGHMGtCmoeE1gbIt6l1eNeK9cO-7tJrOOTE` (verified byte-identical to the downloaded `.docx`).

## Type
misc (operational SE runbook — step-by-step configuration procedures).

## Key Takeaways
- Office premises are created at the WorkInSync backend using the **WIS-Configurations Google sheet** (`1FyWuDnS…`) + **Postman**, referencing an **ETS office GUID**.
- **Prerequisite:** the Office (Manage Office) and Shifts (Manage Shifts) must be created in **ETS** before raising the SE ticket.
- `premiseType = 2` denotes an office premise; `parentPremise`/`techparkId` are left blank at creation.
- Premise create/edit and capacity create/edit are done via security-guard endpoints (`/mis-security-guard/premise` and `/premise-capcity`), each followed by a **cache-evict** call to `booking-rule-engine/.../evict/premise`.
- **Capacity math:** DB-client sites = `login shifts × seats per shift`; other clients enter the number directly. ⚠️ The "edit capacity" section states a general multiply (requested × shift count) without the DB-only qualifier — flagged as an internal contradiction.
- All concrete values in the doc (`tata-TCPOC`, GUIDs, geocodes, premiseIds) are **illustrative placeholders**, not literal config.

## Entities Mentioned
- Office (ETS), Shift (ETS), Premise, Premise-capacity

## Modules Mentioned
- [[modules/ets]] (created), [[modules/desk-management]], [[modules/guard-app-kiosks]], [[modules/parking-management]]

## Decisions Extracted
- None (procedural runbook; no architecture decisions in these sections).

## Wiki Pages Created/Updated
- Created: [[runbooks/ets-office-premise-setup]], [[modules/ets]], this source page
- Updated: [[index]], [[log]]

## Open Flags
- ⚠️ Capacity multiply rule contradiction (DB-only vs universal) — see [[runbooks/ets-office-premise-setup]] Notes & Gotchas.
- Linked resources not yet fetched: ETS config sheet `1WpEu4vW…` (11 tabs), WIS-Configurations sheet `1FyWuDnS…` — pending reference crawler.
