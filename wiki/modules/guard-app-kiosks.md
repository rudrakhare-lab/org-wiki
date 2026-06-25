---
type: module
status: active
owner: unknown
depends_on: []
used_by: [visitor-management]
last_updated: 2026-06-25
source: "[[sources/se-runbook-ets-office-premise]]"
---

# Guard App + Kiosks

## Overview
The Guard App is the security-gate application guards use for visitor/employee check-in and (optionally) temperature capture. Guard **users** and their **premise mappings** are provisioned by the SE team via the WIS-Configurations Google sheet + the `mis-security-guard` backend service. Amenities (seat-level attributes surfaced in the employee app) are also configured through this service. First real source: the SE runbook (guard-user-creation + guard-app-setup).

## Purpose & Scope
- Provision guard **users** (phone + password) and map them to **office premises** (`premiseType: "2"`).
- Generate the **office QR string** used at the gate.
- Configure **amenities** per premise.
- Boundary: premise *creation* itself is the ETS/office-premise flow ([[runbooks/ets-office-premise-setup]]); this module covers guard users, mappings, the app, and amenities.

## Key Features
- **Two deployment modes:** non-IOT (manual temperature entry, app at `https://wis-reception.workinsync.io/`) and IOT (temperature auto-captured, app at `https://mis-security-beta.moveinsync.com/`). ⚠️ The IOT URL carries a `-beta` hostname — confirm it is the production IOT app (Open Questions).
- **Guard user creation + premise-user mapping** via the WIS-Configurations Google sheet SE tool (`Service/Feature = User Creation`, then premise-user mapping with `userId`/`premiseId`).
- **Office QR code** generation via `generate-qr-string`.
- **Amenities** configuration (DESKTOP, CABIN, Standing Desk, …) per premise; surfaced in Employee Experience when `isAmenitiesFilter=true`.

## Data Entities Used
- Guard user (`userId`, phoneNumber), Premise (`premiseType: "2"` office), Premise-user mapping, Amenity set

## Dependencies on Other Modules
- `mis-security-guard` backend service (`mis-security.moveinsync.com`); EU host `mis-security.eu.moveinsync.com`.
- Cache eviction for guard shifts routes through the **Booking Rule Engine** (see runbook Useful Links). ⚠️ Whether this is a modelled `depends_on` is pending the §7 graph sweep.

## Used By
- [[modules/visitor-management]] — Guard App scans the visitor digipass at the gate (see [[cross-module/vms-guard-app]]).

## API Endpoints
| Method | Path | Description | Auth Required |
|--------|------|-------------|---------------|
| GET | `/mis-security-guard/user` | List guard users; search by `phoneNumber` → `userId` | Yes |
| GET | `/mis-security-guard/premise/buid/<BUID>` | List premises under a BUID; filter `premiseType:"2"` for guard offices | Yes |
| GET | `/mis-security-guard/premise-user-mapping` | List premise-user mappings; validate by `userId` + `premiseId` | Yes |
| GET | `/mis-security-guard/premise/generate-qr-string?premiseId=<ID>` | Fetch the office QR string | Yes |
| GET | `/mis-security-guard/premise/<premiseId>` | Retrieve premise details by premiseId | Yes |
| PUT | `/mis-security-guard/premise` | Update an existing premise (full JSON body) | Yes |
| PUT | `/mis-security-guard/api/amenities/premises?buid=<BUID>&requestorGUID=admin` | Set premise amenities (EU host: `mis-security.eu.moveinsync.com`) | `requestorGUID=admin` |
| DELETE | `/mis-security-guard/premise/v2?premiseId=<ID>` | Delete a premise by `premiseId` (any type) | Yes |

## Related Runbooks
- [[runbooks/guard-user-creation]] — create guard user, validate, premise-user mapping, QR code, update/delete premise
- [[runbooks/guard-app-setup]] — app links (non-IOT/IOT), amenities, useful links

## Open Questions
- Which URL is the **production IOT** Guard App? Source labels `mis-security-beta.moveinsync.com` as IOT, but `-beta` is ambiguous. ⚠️
- Is the **OLD Guard App link** (`mis-security.moveinsync.com` front-end root) fully decommissioned, or still serving some clients? ⚠️
- The bulk amenities template is served from a **staging** URL (`staging2.moveinsync.com:9095/...`) — confirm the production template source. ⚠️
- Owner team unknown.

## Last Updated
2026-06-25 — source: [[sources/se-runbook-ets-office-premise]] (guard-user-creation + guard-app-setup runbooks). _Replaces the 2026-05-26 stub._
