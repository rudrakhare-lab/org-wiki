---
type: module
status: active
owner: unknown
depends_on: []
used_by: [desk-management, guard-app-kiosks, parking-management, meal-management, floor-kiosk]
last_updated: 2026-06-29
source: "[[sources/se-runbook-ets]], [[sources/se-runbook-ets-office-premise]]"
---

# ETS Module (Employee Transport Service)

## Overview
**ETS** (Employee Transport Service) is the upstream admin system that owns the canonical **office**, **shift**, and **premise** records WorkInSync builds on. Before any WorkInSync booking module can operate, an office and its shifts must be created in ETS; the SE team then creates the WorkInSync premise referencing the ETS-issued office GUID. ETS also manages **employee data sync** — pushing employee records (identity, team, home geocode, transport assignment) into WorkInSync via SFTP or API — and historically provided commute/transport features (cabs, shuttles, nodal routing) that intersect with some WorkInSync configs. The mobile app bundle ID `com.moveinsync.ets` confirms ETS is the native mobile app host for both transport and workplace features on ETS-tenanted sites.

_Source: [[sources/se-runbook-ets]]_

## Purpose & Scope
- Owns **office records** (name, geocoords, GUID) and **shift records** (login/logout times) that WorkInSync premises reference.
- Provides the **office GUID** (`buIdOfficeGuid`) required when creating WorkInSync premises via the WIS-Configurations tool.
- Provides the **employee data sync** pipeline: client HRMS/IdP data flows into WorkInSync through ETS-managed SFTP or API channels.
- Boundary: ETS does **not** own the WorkInSync premise/capacity records themselves — those live in the security-guard/premise service and are created in a downstream step. ETS is the upstream identity and scheduling source.
- Transport-era features (commute routing, nodal/shuttle points, cabs) are scoped to ETS; WorkInSync workplace modules cross-reference them via PMS configs (see ETS Configs section below).

_Source: [[sources/se-runbook-ets]]_

## Key Features

### Office & Shift Management
- **Manage Office** — ETS → MISADMIN → Data Upload → Manage Office. Creates/edits offices with Site No, Office Name, Geocords. This is a **pre-requisite** for raising an SE ticket — offices and shifts must exist before WIS setup begins.
- **Manage Shifts** — ETS → Site Administrator → Scheduling Management → Manage Shifts. Login shift records feed capacity calculations for DB-client sites.
- **Office API** — `GET /<TENANT>/ets/apis/office` returns each office's `guid`, `address`, and `geoCord` — SE engineers copy these into the WIS-Configurations tool to create the WorkInSync premise.
- **Engineering/operation configs** — a dedicated Google Sheet (`1WpEu4vW…`, 11 tabs: Properties, Booking Service, Emp Ex, Mobile-App, Datasync, Guard endpoints) holds ETS operation and engineering-side configuration values.

### Employee Data Sync
ETS supports two integration channels for pushing employee records from client HRMS/IdP into WorkInSync:

**SFTP (bulk CSV upload):**
- Client drops a CSV file to a MoveInSync-hosted SFTP server; DevOps runs automated processing scripts.
- Use cases: employee joins, leaves, or changes home address.
- Errors are emailed to a configured address with row-level detail.
- SFTP credentials, DNS, port, and folder details are provisioned by MoveInSync DevOps via a TechOps ticket.
- Pre-requisites: SSH public key + IP range from the client; requested via TechOps ticket to `integrations@moveinsync.com`.
- Data sync logs retained 30 days on the dashboard; older logs available in backend only.

**API Sync (push per-employee):**
- Client server pushes employee records using a Bearer-token REST API.
- Auth: `POST /auth/token` with `Authorization: Basic <base64(username:password)>` and `grant_type=client_credentials` → returns short-lived `access_token` (expires in ~172,799 s / 48 hr).
- Token must be refreshed when expired; passed as `Bearer <token>` on all subsequent calls.
- Use cases: employee joins (POST with all mandatory fields), update details (POST with delta fields + EmployeeId), employee leaves (`RemoveEmployee=INACTIVE`).
- Errors returned per-employee with field-level error codes; caller must re-push corrected records.

**Employee data fields (key fields — full schema in [[modules/employee-provisioning]]):**

| Field | Type | Required (Add) | Notes |
|-------|------|----------------|-------|
| `EmployeeId` | String (1–20) | Mandatory | Unique per client; primary key |
| `Email` | String (5–60) | Mandatory | Must contain `@`; unique per client |
| `EmployeeName` | String (1–100) | Mandatory | Concatenate first+last if split |
| `ProjectTeam` | String (1–50) | Mandatory | Auto-created if not present |
| `Gender` | M/F | Mandatory* | Used for safe-reach/escort logic |
| `OfficeName` | String (1–120) | Optional | Must match an office in ETS |
| `GeoCode` | String (7–30) | Optional | Home geocoords `"lat,lng"`; Transport team assigns if blank |
| `Nodal` | String (1–500) | Optional | Nodal point for cab routing; Transport team assigns |
| `ShuttlePoint` | String | Optional | Fixed-point shuttle pickup/drop |
| `CostCenter` | String (1–50) | Optional | Auto-created if not present |
| `RemoveEmployee` | ACTIVE/INACTIVE | — | Set INACTIVE to deactivate |

> ⚠️ The SFTP schema carries transport-era fields (Nodal, ShuttlePoint, GeoCode, BillingZone, CostCenter, BusinessUnit). For pure workplace-only (non-commute) deployments many of these are irrelevant. See [[modules/employee-provisioning]] for the full field contract and SCIM/Azure-AD equivalent schema (different channel, same downstream target).

**Datasync SOP (SE process for requesting SFTP integration):**
- Module POD validates the requirement and gets KAM/TAM approval.
- Module POD raises a TechOps ticket and emails `integrations@moveinsync.com` with: site URL, environment (Prod/POC/UAT), integration method (SFTP), SSH public key, client IP range.
- DevOps provides SFTP folder path details via the TO ticket.
- SLA: Major TO (new script development) = 4 weeks; Minor TO (modify existing automation) = 2 weeks; P0 (sync failing/blocker) = 1 business day with KDV/Charan + Dibyendu approval.

_Source: [[sources/se-runbook-ets]]_

## Data Entities Used
- **Office (ETS)** — `guid`, `address`, `geoCord`; maps to WorkInSync premise via `buIdOfficeGuid`
- **Shift (ETS)** — login/logout shift definitions; used in capacity calculations on DB-client sites
- **Employee record** — EmployeeId, Email, Team, GeoCode, transport assignment fields; synced into WorkInSync via SFTP/API. Full entity definition: [[modules/employee-provisioning]]
- (WorkInSync premise/capacity entities are owned downstream by the security-guard/premise service, not ETS)

_Source: [[sources/se-runbook-ets]]_

## Dependencies on Other Modules
None established — ETS is the upstream source system. Other modules depend on ETS, not the reverse.

_Source: [[sources/se-runbook-ets]]_

## Used By
- [[modules/desk-management]] — office premise + capacity feed seat booking
- [[modules/parking-management]] — parking premises are created under the office premise; `showCabs` config (BookingRuleEngine) ties to ETS cab availability
- [[modules/guard-app-kiosks]] — premise + guard-user mapping built on top of the office premise
- [[modules/meal-management]] — office premise is the parent entity for meal booking location
- [[modules/floor-kiosk]] — floor premises are created under the office premise (premiseType: 4)

> ⚠️ Reciprocal `depends_on` links on the above module pages are **pending the graph-consistency sweep** — do not edit those pages now.

> ⚠️ **Setup-time vs runtime dependency (Open Question):** ETS office/shift records are needed at setup time (SE configuration) before WorkInSync modules can operate. Whether ETS is also queried at booking runtime (e.g. live shift lookup) is not confirmed by current sources. The dependency direction above reflects the setup-time relationship. See Open Questions.

_Source: [[sources/se-runbook-ets]]_

## API Endpoints

### ETS Office Query (used by SE during setup)
| Method | Path | Description | Auth Required |
|--------|------|-------------|---------------|
| GET | `/<TENANT>/ets/apis/office` | List offices with `guid`, `address`, `geoCord` | Yes (tenant-scoped) |

Example call during office-premise setup:
```
GET: https://tata.moveinsync.com/TCPOC/ets/apis/office
```
Returns fields SE needs: `"guid": "LOtata…"`, `"address": "…"`, `"geoCord": "13.05,77.59"`.

### Employee Data Sync — Auth (ETS API channel)
| Method | Path | Description | Auth Required |
|--------|------|-------------|---------------|
| POST | `/auth/token` | Get Bearer access token | Basic (username:password) |

Request: `Authorization: Basic <base64(username:password)>`, body: `grant_type=client_credentials`.  
Response includes `access_token: "<token>"`, `token_type: "bearer"`, `expires_in: 172799`.

> ⚠️ Actual token values are credentials — never log or commit. Represented as `<token>` throughout.

**UAT base URLs:** Authentication: `https://apistage.moveinsync.com/`; Data: `https://data-uat.moveinsync.com/`  
**Production base URLs:** Authentication: `https://apistage.moveinsync.com/`; Data: `https://dataapi.moveinsync.com/`

_Source: [[sources/se-runbook-ets]]_

## ETS Configs

Three transport-adjacent PMS config properties are referenced in source material for ETS-tenanted sites. These were previously **Jira-only** (CLAUDE.md §1, Jira PB-52960); two now have source-document evidence:

| Property | Service | Type | Default | Notes |
|----------|---------|------|---------|-------|
| `indemnifyOfficeBookingTransport` | ETS (Jira-only) | BOOLEAN | `false` | Cited in Jira PB-52960, SE-51628, SE-47565. **Not found in any ingested config sheet or release note.** |
| `commuteMandatory` | ETS / Emp-Ex (inferred) | BOOLEAN | not documented | Appears as example value `true` in SE runbook (sec63) in a parking/booking context. Default not documented. |
| `showCabs` | `BOOKING-RULE-ENGINE` | BOOLEAN | not documented | Appears in SE runbook floor-premise section: "To remove office cabs option from Parking page: Bookingruleengine: showCabs - false". Note: attributed to BookingRuleEngine service, not ETS service. Default not documented. |

> ⚠️ The "Indemnification Form" release note (file `1lx6Qa0L….docx`) documents a **different** set of properties: `FEATURE_INDEMNIFICATION_AGREEMENT_ENABLE`, `INDEMNITEE_COMPANY`, `WOMEN_EMPLOYEE_SIGN_IN_ALERT_START/STOP_24_HOUR_FORMAT`, `INDEMNIFICATION_EMAIL_*`. These are the indemnification agreement feature for women employees' transport cancellation — they are transport-adjacent but are ETS-side configs, not PMS configs. They are noted here for discoverability but are not yet ingested into a config page.

> ⚠️ `LEVEL_3_USER_PROFILE_PICTURE_ENABLED_FOR` (ETS service on PMS) controls profile picture visibility on the ETS side. Supported values: `MARSHAL`, `EMPLOYEE`, `BOTH`, `NONE`. Default: `NONE`. Sourced from face-recognition onboarding doc (crawl); confirmed ETS-service PMS property.

_Source: [[sources/se-runbook-ets]]_

## Related Runbooks
- [[runbooks/ets-office-premise-setup]] — Step-by-step: create/edit office premise + add booking capacity (SE procedure)
- [[runbooks/ets-data-sync]] — SFTP/API employee data sync: SE request procedure and integration channels (see note in that file)

## Open Questions
- **Owner team unknown.** Doc authors: Anushka Verma, Shruthi Naik (datasync docs). No owning team named.
- **Setup-time vs runtime dependency** — current sources confirm ETS office/shift data is required at setup time. Whether downstream modules query ETS at booking runtime (live shift resolution, cab availability check) is not confirmed. Affects whether `depends_on` should be in frontmatter of consuming modules.
- **Is capacity `shifts × seats` multiply DB-client-only or universal?** (⚠️ conflict flagged in [[runbooks/ets-office-premise-setup]].)
- **ETS full transport scope** not yet covered — cabs, shuttle, nodal routing, safe-reach, indemnification workflow. ETS config spreadsheet (`1WpEu4vW…`) not yet fully ingested. Enrich when that sheet is processed.
- **`indemnifyOfficeBookingTransport`** — not found in any ingested config source. Source remains Jira only (PB-52960). Will be resolved when ETS config spreadsheet is ingested.
- **`commuteMandatory` and `showCabs` defaults** — example values seen in SE runbook; no documented defaults in config sheets.
- **Employee data sync channel** — the "Data Sync Process Document for ETS" (2022, v1.0) is the ETS-era employee sync contract. SCIM/API provisioning via `employee-provisioning` may have superseded the SFTP channel for non-transport clients. Confirm which channel applies to pure-workplace (non-ETS) deployments.

## Last Updated
2026-06-29 — source: [[sources/se-runbook-ets]]
