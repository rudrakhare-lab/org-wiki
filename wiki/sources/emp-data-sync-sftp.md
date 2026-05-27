---
type: source
raw_path: raw/modules/employee-provisioning/SFTP - Data Sync Process Document.pdf
ingested: 2026-05-27
doc_type: spec
---

# Employee Data Sync — SFTP / CSV

## Source Title
Data Sync Integration (Process Document & Templates)

## Date
April-2020. No version/author control table in this source (older template than the SCIM docs). Classification: **Confidential**.

## Type
spec

## Key Takeaways
- **⚠️ TRANSPORT-ERA / ETS document.** This is the oldest provisioning doc (April 2020) and is heavily oriented toward MoveInSync's **transport (ETS) / commute** product, NOT pure workplace management. Evidence: the CSV schema carries cab-routing fields (`Nodal`, `ShuttlePoint`, `GeoCode`, `EmployeeBillingZone`, `BusinessUnit`, `CostCenter`); the doc references **ETS** directly (*"F89 does not exist in ETS"*) and "the Transport team" repeatedly. For pure-WorkInSync (non-commute) clients, a significant part of this schema is irrelevant. Treat transport-specific fields as ETS-legacy.
- **Mechanism**: client pushes a **CSV file to an SFTP server**; MoveInSync polls the directory on a configurable frequency and processes the data. Setup needs the client's SSH public key + IP whitelist; MoveInSync provides DNS name, username, sync folder, port, and the CSV template.
- **Delta-file model** (quote): *"This file will contain only delta information, i.e. additions, deletions, change in employee information."* Only changed fields need to be pushed, along with `EmployeeId` and `RemoveEmployee`.
- **23-field CSV schema**: EmployeeId, Email, EmployeeName, ProjectTeam, Gender, Address, GeoCode, PhoneNumber, AlternatePhoneNumber, Nodal, ShuttlePoint, Locality, SubscribeEmail, SubscribeMobileApp, SubscribeSMS, CostCenter, EmployeeCostCenterActivationDate, BusinessUnit, BusinessUnitActivationDate, EmployeeBillingZone, OfficeName, RemoveEmployee, RMID. Full table is on the module page's Sync Schema section.
- **Use cases documented**: employee joins (all mandatory fields), employee leaves (`RemoveEmployee=Inactive` + minimal fields), address change (geocodes handled manually by Transport team). Errors are emailed back with row/field/description; client fixes and re-uploads via SFTP or the data-upload interface.
- **Auto-creation behaviors**: unknown `ProjectTeam`, `CostCenter`, or `BusinessUnit` values are auto-created in MoveInSync rather than erroring; unknown `Nodal`/`ShuttlePoint`/`OfficeName`/`BillingZone` throw errors (must pre-exist).

## Entities Mentioned
(none ingested — `entities/employee.md` deferred to Tier 2.5)

## Modules Mentioned
- [[modules/employee-provisioning]] (primary subject)

## Decisions Extracted
(none)

## Wiki Pages Created/Updated
- Created: [[modules/employee-provisioning]]
- Updated: [[index]], [[log]], [[glossary]]

_Source: [[sources/emp-data-sync-sftp]]_
