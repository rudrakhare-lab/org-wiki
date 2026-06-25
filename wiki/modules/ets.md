---
type: module
status: stub
owner: unknown
depends_on: []
used_by: [desk-management, guard-app-kiosks, parking-management]
last_updated: 2026-06-25
source: "[[sources/se-runbook-ets-office-premise]]"
---

# ETS Module (Employee Transport Service)

## Overview
**ETS** (Employee Transport Service) is the operations/engineering-side admin system that holds the **office, shift, and premise** source data WorkInSync builds on. In the SE configuration workflow it is the upstream system: the office and its shifts are created in ETS first, then the WorkInSync premise (and its booking capacity) are created at the backend referencing the ETS office GUID. ETS also exposes an office API (`/ets/apis/office`) that returns the `guid`/`address`/`geoCord` SE engineers copy into the WIS-Configurations sheet.

> Note: this page was created from the SE runbook (office-premise sections). It is a **stub** — much of ETS's broader behaviour (transport, commute, cabs) is documented only in Jira today (see Open Questions and CLAUDE.md ETS notes).

## Purpose & Scope
- Owns the **office** and **shift** records (created via the ETS admin UI) that premises map to.
- Provides the **office GUID** (`buIdOfficeGuid`) that ties a WorkInSync premise to its ETS office.
- Boundary: ETS does **not** own the WorkInSync premise/capacity records themselves — those live in the security-guard/premise service and are created via the WIS-Configurations tool. ETS is the upstream identity/source for offices.

## Key Features
- **Manage Office** — ETS → MISADMIN → Data Upload → Manage Office (create/edit offices: Site No, Office Name, Geocords).
- **Manage Shifts** — ETS → Site Administrator → Scheduling Management → Manage Shifts (login shifts feed capacity math for DB-client sites).
- **Office API** — `GET /ets/apis/office` returns office `guid`, `address`, `geoCord`.
- ETS operation/engineering settings are configured via a dedicated **config spreadsheet** (`1WpEu4vW…`, 11 tabs).

## Data Entities Used
- Office (ETS) — `guid`, `address`, `geoCord` → maps to WorkInSync premise via `buIdOfficeGuid`
- Shift (ETS) — login shifts used in capacity calculation
- (premise / premise-capacity entities are owned downstream by the security-guard service)

## Dependencies on Other Modules
None established from this source — ETS is an upstream source system.

## Used By
- [[modules/desk-management]] — office premise + capacity feed seat booking
- [[modules/guard-app-kiosks]] — premise + guard-user mapping build on the office premise
- [[modules/parking-management]] — parking premises are created under the office premise

## API Endpoints
| Method | Path | Description | Auth Required |
|--------|------|-------------|---------------|
| GET | `/<TENANT>/ets/apis/office` | List offices with `guid`/`address`/`geoCord` | yes (tenant-scoped) |

## Related Runbooks
- [[runbooks/ets-office-premise-setup]] — create/edit office premise + capacity

## Open Questions
- ETS full scope (transport / commute / cabs) is not covered by this source — properties like `indemnifyOfficeBookingTransport`, `commuteMandatory`, `showCabs` are Jira-only (CLAUDE.md §1 ETS notes, PB-52960). To be enriched when the ETS config spreadsheet (`1WpEu4vW…`) is ingested by the crawler.
- Owner team unknown.
- Is the capacity `shifts × seats` multiply DB-client-only or universal? (⚠️ conflict flagged in [[runbooks/ets-office-premise-setup]].)

## Last Updated
2026-06-25 — source: [[sources/se-runbook-ets-office-premise]]
