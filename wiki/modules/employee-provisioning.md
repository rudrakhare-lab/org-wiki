---
type: module
status: active
owner: unknown
depends_on: []
used_by: []
last_updated: 2022-07-15
source: "[[sources/emp-data-sync-scim-azure]], [[sources/emp-data-sync-scim-okta]], [[sources/emp-data-sync-sftp]]"
---

# Employee Provisioning Module

## Overview
Employee Provisioning is the inbound data-sync surface that loads employee records from a
client's identity provider (IdP) or HRMS into WorkInSync. It supports two integration
mechanisms: **SCIM 2.0** (IdP-driven, real-time-ish — Azure AD, Okta, or any SCIM-compliant
source) and **SFTP CSV file transfer** (an older, transport-era batch mode). Both keep the
WorkInSync employee directory in sync with the client's source-of-truth system, including
additions, updates, and deactivations.

## Purpose & Scope
Owns the inbound employee-data sync: the SCIM API surface, the SFTP file-exchange procedure,
the attribute/field mapping from source systems to WorkInSync, and sync cadence/retry.

Does **not** own: the full employee data model (this module defines the *sync schema*, not
the complete employee entity — see Open Questions on the deferred `entities/employee.md`),
the downstream modules that consume employee records (not named in any source), or
authentication / SSO (a separate concern — SCIM uses a WIS-issued secret token, not the
`sso` module; the Azure-AD **SSO** doc that also sits in this raw folder is handled under
[[modules/sso]], not here).

## Key Features
- **SCIM 2.0 provisioning**: IdP-driven user sync via a SCIM-compliant API (RFC 7644). Setup guides exist for **Azure AD** and **Okta**, but any SCIM-compliant IdP / HRMS works
- **Users-only**: SCIM syncs Users; **Groups are explicitly NOT supported**
- **Regional SCIM endpoints**: `https://scim.workinsync.io/scim/v2` (AWS Singapore) and `https://scim.eu.workinsync.io/scim/v2/` (EU)
- **Secret-token auth**: SCIM connection uses a unique token generated and shared by the WorkInSync account manager (not SSO, not per-user)
- **40-minute default sync cadence** with a Provisioning status/error overview and per-record "Provision on Demand" retry (SCIM mode)
- **SFTP CSV mode**: alternative batch integration — client pushes a delta CSV to an SFTP server; WorkInSync polls on a configurable frequency. Setup needs SSH public key + IP whitelist
- **Delta-file model (SFTP)**: only changed fields are pushed, with `EmployeeId` and `RemoveEmployee` always included; errors are emailed back per row/field for correction and re-upload
- **Auto-creation (SFTP)**: unknown `ProjectTeam` / `CostCenter` / `BusinessUnit` values are auto-created; unknown `Nodal` / `ShuttlePoint` / `OfficeName` / `BillingZone` throw errors

## Data Entities Used
(none yet — the foundational `entities/employee.md` is **deferred to Tier 2.5** so it can be synthesized from downstream modules' employee-record semantics too, not just the provisioning sync schema. The sync schema is documented inline below.)

## Dependencies on Other Modules
(none — provisioning is an upstream data-ingestion surface; it feeds WorkInSync rather than calling other modules)

## Used By
(none named in source — employee records are foundational and consumed broadly across modules, but no specific consuming module is named in any provisioning doc; see Open Questions)

## API Endpoints
**SCIM mode** — the client's IdP calls the WorkInSync SCIM endpoint:

| Endpoint | Region | Auth |
|---|---|---|
| `https://scim.workinsync.io/scim/v2` | AWS Singapore tenants | Secret token (Header Auth / Bearer), issued by WIS account manager |
| `https://scim.eu.workinsync.io/scim/v2/` | EU tenants | Secret token, issued by WIS account manager |

Supported provisioning actions: Create, Update, Delete (Users). The IdP (Azure AD / Okta) is configured to push to these endpoints.

**SFTP mode** — no HTTP API; the client pushes CSV files to a MoveInSync-provided SFTP directory (DNS name, username, port, folder supplied by MoveInSync; client supplies SSH public key + IP whitelist).

## Sync Schema

Two different schemas depending on the integration mode.

### SCIM attribute mapping (Azure AD / Okta)
Source IdP attribute → SCIM attribute → WorkInSync field. WorkInSync processes ONLY these mapped attributes; any extra field in the IdP mapping is ignored.

| Source (AD) attribute | SCIM attribute | WorkInSync field / use |
|---|---|---|
| `userPrincipalName` | `userName` | Primary unique ID in WorkInSync |
| `displayName` | `displayName` | Name field (falls back to givenName + familyName if absent) |
| `mail` | `emails[type eq "work"].value` | email |
| `givenName` | `name.givenName` | First name |
| `surname` | `name.familyName` | Last name |
| `physicalDeliveryOfficeName` | `addresses[type eq "work"].formatted` | office |
| `streetAddress` | `addresses[type eq "work"].streetAddress` | commute clients only |
| `city` | `addresses[type eq "work"].locality` | commute clients only |
| `state` | `addresses[type eq "work"].region` | commute clients only |
| `postalCode` | `addresses[type eq "work"].postalCode` | commute clients only |
| `country` | `addresses[type eq "work"].country` | commute clients only |
| `telephoneNumber` | `phoneNumbers[type eq "work"].value` | commute clients only |
| `mailNickname` | `externalId` | required by SCIM protocol |
| `employeeId` | `urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:employeeNumber` | Optional Employee ID (preferred for commute clients) |
| `department` | `urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:department` | team |
| `manager` | `urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:manager` | manager (FK to the user object) |

### SFTP CSV schema (transport-era — see Open Questions on ETS staleness)
Column headers must be maintained exactly. `Add` / `Update` / `Termination` columns indicate obligation per operation.

| Field | Type (length) | Add | Update | Termination | Notes |
|---|---|---|---|---|---|
| `EmployeeId` | String (1-20) | Mandatory | Mandatory | Mandatory | Unique; same as HRMS emp ID |
| `Email` | String (5-60) | Mandatory | Optional | Optional | Unique; triggers emails |
| `EmployeeName` | String (1-100) | Mandatory | Optional | Optional | |
| `ProjectTeam` | String (1-50) | Mandatory | Optional | Optional | Auto-created if unknown |
| `Gender` | M / F | Mandatory | Optional | Optional | |
| `Address` | String (1-500) | Optional | Optional | Optional | Wrap in double-quotes if it contains a comma |
| `GeoCode` | String (7-30) | Optional | Optional | Optional | "x,y" coordinate pair; falls back to office geocode |
| `PhoneNumber` | String (0-30) | Optional | Optional | Optional | India (+91) only |
| `AlternatePhoneNumber` | String (0-30) | Optional | Optional | Optional | India (+91) only |
| `Nodal` | String | Optional | Optional | Optional | Transport; must pre-exist or errors |
| `ShuttlePoint` | String | Optional | Optional | Optional | Transport; must pre-exist or errors |
| `Locality` | String (1-100) | Optional | Optional | Optional | Landmark for driver routing |
| `SubscribeEmail` | 1 / 0 | Mandatory | Optional | Optional | |
| `SubscribeMobileApp` | 1 / 0 | Mandatory | Optional | Optional | |
| `SubscribeSMS` | 1 / 0 | Mandatory | Optional | Optional | |
| `CostCenter` | String (1-50) | Optional | Optional | Optional | Auto-created if unknown |
| `EmployeeCostCenterActivationDate` | Date (dd-MM-yyyy / dd/mm/yyyy) | Optional | Optional | Optional | Not future-dated |
| `BusinessUnit` | String (1-50) | Optional | Optional | Optional | Auto-created if unknown |
| `BusinessUnitActivationDate` | Date | Optional | Optional | Optional | Not future-dated |
| `EmployeeBillingZone` | String | Optional | Optional | Optional | Transport billing; must pre-exist |
| `OfficeName` | String (1-20) | Optional | Optional | Optional | Must exist in MoveInSync |
| `RemoveEmployee` | Active / Inactive | Mandatory | Mandatory | Mandatory (Inactive) | Activation/deactivation flag |
| `RMID` | Numeric (1-20) | Optional | Optional | Optional | Reporting manager's employee ID |

## Open Questions
- **Foundational `entities/employee.md` is deferred** — will be created during Tier 2.5 synthesis when downstream modules' employee-record semantics are also evident. These provisioning docs define the *sync schema* (what the IdP/HRMS pushes), not the full employee data model used across WorkInSync.
- ⚠️ **SFTP mode is transport-era (April 2020) and ETS-laden.** Its CSV schema carries cab-routing fields (Nodal, ShuttlePoint, GeoCode, BillingZone, CostCenter, BusinessUnit) and references ETS + the Transport team directly. For pure-WorkInSync (non-commute) deployments, a large part of the SFTP schema is likely irrelevant. Engineering should clarify which SFTP fields apply to workplace-only clients.
- ⚠️ **EU vs AWS-Singapore hosting split** — SCIM tenant URL differs by region (`scim.workinsync.io` vs `scim.eu.workinsync.io`). Clients must configure the correct regional endpoint; wrong region = failed sync.
- **Downstream consumers not named** — employee records feed essentially every module (booking identity, etc.), but no provisioning doc names a specific consuming module. `used_by` is left empty until consumers are confirmed.
- **Module owner not named** — authors across docs: Nitin Awasthi, Rishabh M, Rishabh (SCIM); SFTP doc has no author table. Approver Ujjwal Trivedi (SCIM). No owning team stated.
- **SCIM-Okta version metadata inconsistency** — the Okta doc header says v1.1 but its Version Control table lists only v1.0. Minor documentation-hygiene issue.
- **SCIM "commute clients only" attributes** — several address/phone SCIM attributes are flagged "Applicable only for commute clients", echoing the transport/ETS split seen in the SFTP doc. The boundary between commute and workplace-only provisioning is not fully specified.

## Last Updated
2022-07-15 — _Source: [[sources/emp-data-sync-scim-azure]], [[sources/emp-data-sync-scim-okta]], [[sources/emp-data-sync-sftp]]_
