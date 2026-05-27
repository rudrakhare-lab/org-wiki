---
type: entity
owned_by: employee-provisioning
used_by: [delegation, visitor-management, meal-management, parking-management, meeting-rooms, access-management, employee-experience, implementation, desk-management, mobile-app]
last_updated: 2026-05-27
source: "[[sources/emp-data-sync-scim-azure]], [[sources/emp-data-sync-scim-okta]], [[sources/emp-data-sync-sftp]]"
---

# Employee (Entity)

## Description
The **employee** is WorkInSync's foundational identity record — the person who books desks,
parking, meals, and meeting rooms; hosts visitors; delegates privileges; and carries an RFID
access card. Employee records are loaded into WorkInSync via [[modules/employee-provisioning]]
(SCIM 2.0 from an IdP, or SFTP CSV batch) and are then referenced by essentially every feature
module. This page synthesizes the **cross-module** view — the curated core fields plus the
semantic **roles** an employee plays across modules. The complete sync schema (full SCIM
attribute mapping + all 23 SFTP CSV fields) lives in [[modules/employee-provisioning]] and is
not duplicated here.

## Core Identity Fields
_Curated core; full SCIM/SFTP schema in [[modules/employee-provisioning]]._

| Field | Type | Source | Notes |
|---|---|---|---|
| `userName` | String | provisioning (SCIM) | Primary unique ID in WorkInSync (from userPrincipalName) |
| `EmployeeId` | String (1-20) | provisioning (SFTP / SCIM employeeNumber) | HRMS employee ID; SFTP-mandatory, SCIM-optional |
| `email` | String | provisioning (SCIM/SFTP) + access-management | Unique; also an employee-resolution key in access-management `filter` |
| `displayName` | String | provisioning (SCIM) / EmployeeName (SFTP) | Falls back to givenName + familyName if absent |
| `externalId` | String | provisioning (SCIM) | SCIM protocol field (from mailNickname) |
| `rfid` | String (≤50) | access-management | RFID/HID access-card identifier; requires an RFID→employee mapping |

## Organizational Fields
| Field | Type | Source | Notes |
|---|---|---|---|
| `manager` / `RMID` | FK / Numeric | provisioning (SCIM / SFTP) | ⚠️ **Dual representation**: SCIM `manager` = FK to the manager's user object; SFTP `RMID` = the reporting manager's numeric employee ID. Same concept, two encodings |
| `department` / `ProjectTeam` | String | provisioning (SCIM / SFTP) | ⚠️ **Dual naming**: SCIM `department` and SFTP `ProjectTeam` both map to the WIS team field |
| `OfficeName` / office | String | provisioning (SFTP / SCIM) | SFTP `OfficeName` must already exist in MoveInSync; SCIM maps physicalDeliveryOfficeName |
| `CostCenter` | String (1-50) | provisioning (SFTP) | Auto-created if unknown; carries an activation date |
| `BusinessUnit` | String (1-50) | provisioning (SFTP) | Auto-created if unknown; carries an activation date |

## Entitlement / Access Fields
| Field | Type | Source | Notes |
|---|---|---|---|
| `RemoveEmployee` | Active / Inactive | provisioning (SFTP) | Activation/deactivation status flag |
| `Subscribe{Email,MobileApp,SMS}` | 1 / 0 | provisioning (SFTP) | Per-channel notification opt-ins |
| Parking employee-tags | tag pairs | parking-management | Vehicle-build (SUV/Sedan/Hatchback), PWD, `BLOCK_HOTSEAT` — matched against slot tags for booking access |
| Meeting-room employee-tags | tag pairs | meeting-rooms | e.g. `isExecutive` (MECE values) — matched against room tags (Native Rooms only) |
| Meal entitlement | reference | meal-management | Employee is the meal-booking holder / cafeteria consumer |

## ETS-era / Commute Fields ⚠️
These fields are **transport/commute-era** (cab routing, billing zones) and apply mainly to
ETS/commute clients — for pure-WorkInSync deployments a large subset is irrelevant (same caveat
as the provisioning SFTP schema and the M9 ELC Guide):

- `GeoCode` (x,y coordinate), `Nodal`, `ShuttlePoint`, `Locality` (driver-routing landmark), `EmployeeBillingZone` (transport billing)
- SCIM "commute clients only" attributes: street address, city, state, postalCode, country, telephoneNumber

_Full ETS-era field list (SFTP CSV schema) → [[modules/employee-provisioning]]._

## Relationship Roles
The employee's cross-module **semantic roles** — these are not a single stored column, but how
modules use the employee record:

- **Delegator / Delegatee** — an employee can delegate booking/management privileges to another employee and act on a delegator's behalf via profile-switch ([[modules/delegation]])
- **Visitor Host + Employee Self-Check-in** — an employee is the `host` on a [[entities/visitor-invite]]; separately, an employee has a distinct self-check-in path at the VMS kiosk (≠ visitor check-in) ([[modules/visitor-management]])
- **RFID Card Holder** — an employee maps to an RFID/HID access card (`rfid`), used for badge-based access and meal check-in ([[modules/access-management]])
- **Booking Holder** — an employee holds [[entities/booking]], [[entities/parking-booking]], and [[entities/meal-booking]] records ([[modules/parking-management]], [[modules/meal-management]], [[modules/meeting-rooms]], [[modules/desk-management]])
- **Meeting Organizer** — an employee organizes meetings and catering ([[modules/meeting-rooms]])
- **Manager in hierarchy** — an employee may be another's reporting manager (`manager` FK / `RMID`) ([[modules/employee-provisioning]])
- **Onboarding unit** — during client onboarding, employees are counted and configured per-client (user count, org structure) ([[modules/implementation]])

## Modules That Reference This Entity
- [[modules/delegation]] — delegator / delegatee
- [[modules/visitor-management]] — visitor host + employee self-check-in
- [[modules/meal-management]] — meal-booking holder
- [[modules/parking-management]] — parking-booking holder + employee tags
- [[modules/meeting-rooms]] — room-booking holder, meeting organizer + employee tags
- [[modules/access-management]] — RFID card holder (`rfid` / `filter`)
- [[modules/employee-experience]] — foundational host service for employee-facing features
- [[modules/implementation]] — employee as onboarding unit
- [[modules/desk-management]] — desk-booking holder _(stub)_
- [[modules/mobile-app]] — app identity / booking surface _(stub)_

## Source of Truth
Employee records enter WorkInSync via [[modules/employee-provisioning]] — the inbound
system-of-record sync surface (SCIM 2.0 or SFTP CSV). _`owned_by` reflects the WIS
sync/ingestion surface: the **canonical** employee record is defined by the organization's HR
system or IdP; employee-provisioning is the WIS boundary where it enters._

⚠️ **Dual primary key across sync modes**: SCIM keys on `userName` (userPrincipalName) as the
primary unique ID; the SFTP CSV mode keys on `EmployeeId`. The two ingestion modes use different
primary identifiers — relevant when reconciling records or debugging a sync.

## Open Questions
- Which fields apply to **workplace-only** (non-commute) clients vs ETS/commute clients? The commute/workplace boundary is unspecified (echoes the provisioning Open Questions).
- Is there a single canonical employee ID across modules, given the SCIM `userName` vs SFTP `EmployeeId` dual-key split?
- Downstream reciprocity: each referencing module's "Data Entities Used" should back-link this entity (deferred to the graph sweep, endgame step B).

## Last Updated
2026-05-27 — _Source: [[sources/emp-data-sync-scim-azure]], [[sources/emp-data-sync-scim-okta]], [[sources/emp-data-sync-sftp]]_
