---
type: module
status: active
owner: unknown
depends_on: []
used_by: []
last_updated: 2025-03-06
source: "[[sources/emp-data-sync-scim-azure]], [[sources/emp-data-sync-scim-okta]], [[sources/emp-data-sync-sftp]], [[sources/se-runbook-employee-provisioning]]"
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
- **Stratus Direct API mode** (WorkInSync-only sites): client server pushes employee records via REST (`POST /{buid}/employees`); supports batch payloads, `ext` tag objects, and a team-management endpoint (`POST /{buid}/teams`). Introduced 2025-03-06.
- **Stratus role & privilege model**: Stratus tenants have four built-in user groups (`admins`, `users`, `managers`, `guards`) with per-group privilege defaults. Custom user groups can be created by admins. Distinct from IdP groups — Stratus groups are WorkInSync-native access-control constructs, not synced from the IdP.

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

**Stratus Direct API mode** (WorkInSync-only sites, 2025):

| Method | Path | Description | Auth |
|---|---|---|---|
| `POST` | `/auth/token` | Get Bearer token (`client_credentials`) | `Authorization: Basic <base64(user:pass)>` |
| `POST` | `/{buid}/employees` | Create or update employee records (batch array) | Bearer token |
| `POST` | `/{buid}/teams` | Create or update team records | Bearer token |

Base URLs:

| Environment | Auth | Data |
|---|---|---|
| UAT | `https://apistage.moveinsync.com/` | `https://data-uat.moveinsync.com/` |
| Production | `https://apistage.moveinsync.com/` | `https://dataapi.moveinsync.com/` |

Token is short-lived (`expires_in: 172799` seconds ≈ 48 hours). Refresh via `/auth/token` when expired.

> ⚠️ This API is for **WorkInSync-only (Stratus) sites only**. ETS/transport sites use the separate ETS data sync flow — see [[runbooks/ets-data-sync]].

_Source: [[sources/se-runbook-employee-provisioning]]_

## Sync Schema

Three integration modes, each with its own schema.

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

### Stratus Direct API employee fields (WorkInSync-only sites)

Mandatory fields are marked `*`. Source: "MoveInSync Employee Data Sync API Document (WorkInSync only)" v1.0, Mar 6, 2025.

| Field | Format | Max length | Notes |
|---|---|---|---|
| `employeeId` * | String | 25 | Unique per client |
| `employeeName` * | String | 100 | |
| `email` * | String | 80 | Must contain `@`; unique per client |
| `office` * | String | 120 | Mandatory when multiple offices exist for the BUID |
| `team` | String | 120 | Optional |
| `phoneNumber` | String | 7–10 | |
| `reportingManagerName` | String | — | Must be a valid `employeeId` already in the system |
| `removeEmployee` | `ACTIVE` / `INACTIVE` | — | Send `INACTIVE` for employee exits |
| `businessLine` | String | — | Mandatory paired with `subBusinessLine` (both or neither) |
| `subBusinessLine` | String | — | Mandatory paired with `businessLine` |
| `extras` | String (key-value pair) | — | Stored as-is; not validated |
| `ext` | List of `{type, value}` objects | — | Tag objects: `VACCINATED`, `SYSTEM_COMPLIANCE`, `SEAT_BOOKING`, `CABIN_SEAT` |

**Tag defaults** (Stratus): `VACCINATED=null`, `SEAT_BOOKING=null`, `SYSTEM_COMPLIANCE=null`, `CABIN_SEAT=null`.

**SCIM vs Stratus API mandatory field difference:**
- Stratus SCIM: mandatory field is **Email** only. Missing office/team → provisioned to default office/team.
- Stratus Direct API: **Email + EmployeeName + EmployeeId** mandatory; **Office** mandatory when the BUID has multiple offices.
- ETS/transport mode (SFTP/API): **EmployeeId** mandatory (not just email).

Team model fields (`POST /{buid}/teams`): `teamName` (`projectName`), `teamDescription` (`projectDescription`), `teamManagers` (list of employee IDs, must already exist).

_Source: [[sources/se-runbook-employee-provisioning]]_

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

## Stratus Role & Privilege Model

Applies to Stratus (WorkInSync-only) tenants. Source: "Role and Privilege Management in Stratus" (undated, confirmed in provisioning runbook batch).

### Key Concepts

| Term | Definition |
|---|---|
| **Privilege** | An atomic operation permission (Read / Create / Edit / Delete / Deactivate / Cancel on a specific entity) |
| **Role** | A named collection of privileges, optionally scoped to a resource or resource group |
| **User Group** | A collection of users; bulk permission management unit |
| **Resource** | An entity such as Office, Team, Shift |
| **Resource Group** | A named set of resources (e.g. "All India Offices") for scoped role assignment |

### Built-in User Groups (cannot be disabled or deleted)

| Group | Default resource scope | Default access |
|---|---|---|
| `admins` | `*.office`, `*.Team`, `*.Shift` | Unrestricted — all actions |
| `users` (employees) | None | Read-only on self booking, PII data |
| `managers` | `*.office`, `*.Team`, `*.Shift` | Read + edit on reportees |
| `guards` | — | Guard-specific access |

Every user is automatically added to the `users` group. Users can belong to multiple groups.

### Super Admin
- Created automatically when the account is first set up.
- Has unrestricted access to all actions; no other user can restrict super admin privileges.
- If the super admin leaves, they can transfer super admin status to another user via email verification; the original super admin then loses the role.

### Global Admins
An in-built group. Members added by super admin or another admin with the access. Separate from the general `admins` group.

### Custom User Groups
Admins can create custom groups with a unique name and optional description. Custom groups can have arbitrary privilege + resource-group scope. A user group **cannot** be nested (a group cannot be a member of another group).

> ⚠️ Stratus role/privilege groups are **WorkInSync-native** access-control constructs. They are NOT IdP groups and are not synced from Azure AD / Okta. IdP groups are explicitly NOT supported by SCIM provisioning.

_Source: [[sources/se-runbook-employee-provisioning]]_

## Open Questions
- **Foundational `entities/employee.md` is deferred** — will be created during Tier 2.5 synthesis when downstream modules' employee-record semantics are also evident. These provisioning docs define the *sync schema* (what the IdP/HRMS pushes), not the full employee data model used across WorkInSync.
- ⚠️ **SFTP mode is transport-era (April 2020) and ETS-laden.** Its CSV schema carries cab-routing fields (Nodal, ShuttlePoint, GeoCode, BillingZone, CostCenter, BusinessUnit) and references ETS + the Transport team directly. For pure-WorkInSync (non-commute) deployments, a large part of the SFTP schema is likely irrelevant. Engineering should clarify which SFTP fields apply to workplace-only clients.
- ⚠️ **EU vs AWS-Singapore hosting split** — SCIM tenant URL differs by region (`scim.workinsync.io` vs `scim.eu.workinsync.io`). Clients must configure the correct regional endpoint; wrong region = failed sync.
- **Downstream consumers not named** — employee records feed essentially every module (booking identity, etc.), but no provisioning doc names a specific consuming module. `used_by` is left empty until consumers are confirmed.
- **Module owner not named** — authors across docs: Nitin Awasthi, Rishabh M, Rishabh (SCIM); Aditya Dutta (Stratus API, 2025); SFTP doc has no author table. Approver Ujjwal Trivedi across docs. No owning team stated.
- **SCIM-Okta version metadata inconsistency** — the Okta doc header says v1.1 but its Version Control table lists only v1.0. Minor documentation-hygiene issue.
- **SCIM "commute clients only" attributes** — several address/phone SCIM attributes are flagged "Applicable only for commute clients", echoing the transport/ETS split seen in the SFTP doc. The boundary between commute and workplace-only provisioning is not fully specified.
- **SCIM server vs PII service mismatch** — the internal troubleshooting guide notes a known internal failure mode where SCIM server and PII service fall out of sync; cache-clear is the resolution. Internal owner: SCIM server — Deepanshu & Tushar Tyagi; PII service — Yogesh (names as of 2024).
- **Stratus Direct API scope** — the 2025 API doc is explicitly "WorkInSync only sites". It is unclear whether this supersedes the older ETS API doc for non-transport clients, or if both coexist. See [[runbooks/ets-data-sync]] for the ETS-side process.

## Related Runbooks
- [[runbooks/employee-data-sync-scim]] — SE setup guide for SCIM (Azure AD / Okta) + troubleshooting
- [[runbooks/ets-data-sync]] — ETS-side SFTP/API data sync process (TechOps request flow; not SCIM)

## Last Updated
2025-03-06 — _Source: [[sources/emp-data-sync-scim-azure]], [[sources/emp-data-sync-scim-okta]], [[sources/emp-data-sync-sftp]], [[sources/se-runbook-employee-provisioning]]_
