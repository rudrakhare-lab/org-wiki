---
type: module
status: active
owner: Aditya Dutta / Ujjwal Trivedi
depends_on: [ets]
used_by: [meeting-rooms, digital-wayfinding, visitor-management, implementation, meal-management]
last_updated: 2026-02-02
source: "[[sources/diy-floor-planner-prd]], [[sources/floor-kiosk-device-spec]], [[sources/floor-plan-sop]], [[sources/se-runbook-floor-kiosk]]"
---

# Floor Kiosk Module

## Overview
The Floor Kiosk module is the infrastructure layer that powers:
1. **Physical kiosk devices** — large-format Android tablets deployed in offices for room/floor-level interactions (meeting room kiosk, guard app kiosk, etc.)
2. **DIY Floor Planner** — internal tool for creating, editing, and versioning interactive floor plan SVGs from client CAD files
3. **Floor plan data pipeline** — process for ingesting client floor plans into the WorkInSync system

Other modules (Meeting Rooms, Guard App, Digital Wayfinding) depend on this infrastructure.

## Key Features

### Device Infrastructure
- **Hardware spec**: Android 12.0+, 25"+ screen, 12GB RAM, 128GB ROM, Wi-Fi 6, Bluetooth 5, capacitive 10-point touch
- **Kiosk mode**: guided mode — disables back button, restricts URL exit, locks to single app
- **MDM**: manages device enrollment, updates, and policy enforcement
- **Pairing**: each device paired to a specific room or floor via a pairing code + admin email

### DIY Floor Planner (Internal Tool)
- Converts client DWG/CAD files to interactive SVG format
- Marks amenities (desks, meeting rooms, parking slots, washrooms, lifts, cafeteria, exits)
- Draws walkway paths for navigation (top-down approach; bi-directional for office, uni-directional for parking)
- **Why version control**: preserves floor-plan development effort, allows restoring a prior version when a client changes requirements (e.g. remove 10 seats → add a meeting room), and enables auditing of who changed what (accountability on large MNC floor plans)
- **Phase 1** (completed): ported into the WorkInSync ecosystem — scope limited to `workinsync.io`; accessible by the **Global Admin** role only, via a new sidenav item. Closes the prior security gap (the tool was previously a public website with no authentication, exposing client floor plans)
- **Phase 2** (planned): version control — DWG + JSON saved to an **S3 bucket** (replacing the prior ~5 GB server folder), versioned by timestamp with a `[v1, v2…vN]` naming scheme. Importing a DWG with an existing name shows an overwrite prompt; a **'Restore JSON'** CTA restores mappings by timestamp/name
- **Appendix QoL** (related to the tool, not core version control): highlight unlabelled seats (name = `null`) in red; warn on duplicate seat names at save; UI grouping of common buttons (`PB-218870`)

### Floor Plan Data Pipeline
```
Client provides DWG/PNG/PDF
    → Floor plan team cleans and imports into DIY Floorplanner
    → Mark all amenities + draw paths
    → Verify/validate paths ('Verify Data' button)
    → Export JSON + SVG
    → SE team uploads via Postman to Wayfinding service (JSON) and Premise service
    → SE ticket to enable feature flag per BUID
```
- DWG → SVG must be < 2 MB (else use PNG)
- Every seat must have a name and an orientation (angle); meeting room names must match Outlook/Google calendar names exactly
- Export feeds the Premise service (older name for the Wayfinding service), which uses `premiseID` / `parentPremiseID` for path computation
- Floor plan updates: re-draw affected paths → re-export JSON → re-upload

#### SE upload endpoints (from the SE runbook — see [[runbooks/floor-plan-upload]])
- **Method A — file-based:** `POST https://mis-security.moveinsync.com/mis-security-guard/csv/upload/floorplan?floorType=WITH_FLOOR_PLAN&forceUpdateFloorPlan=false&premiseId=<FloorPremiseID>`
- **Method B — background image + file:** `POST https://mis-security.moveinsync.com/mis-security-guard/csv/upload/floorplan?floorType=WITH_BACKGROUND_IMAGE…`
- **Method C — DIY (JSON + SVG):** `POST https://wis-premise.workinsync.io/mis-security-guard/csv/upload/layout/<premiseId>?forceUpdateFloorPlan=false&wktDimensionInCm=100`
- Prerequisite: `seatValidation=true` in the Booking service before floor-plan work begins; the floor premise is `premiseType: 4`.
- First DIY upload requires setting `employeeFloorPlanUrl` / `adminFloorPlanUrl` / `adminAssignmentFloorPlanUrl` in the `empexp` service.
- ⚠️ The seat-UUID change API in the runbook uses a `serviceuat.moveinsync.com` (UAT) host while other uploads are production — confirm with owning team.
- _Source: [[sources/se-runbook-ets-office-premise]]_

## Hardware Specifications

Two source documents exist. Spec Sheet v1.0 (2026-02-02) and the Device Specification Datasheet are largely aligned; divergences are called out.

| Parameter | Spec Sheet v1.0 (2026-02-02) | Device Datasheet |
|-----------|------------------------------|------------------|
| Screen size | 25"+ recommended | 25"–27" recommended; 32"+ not optimal (needs MIS testing) |
| Aspect ratio | 16:9 | 16:9 |
| OS | Android 12.0+ | Android 12.0+ |
| Chipset | Qualcomm | Qualcomm Snapdragon 7-series / 8-series equivalent |
| CPU architecture | Quad-core / ARM Cortex | Octa-core ARM Cortex (4× A76 + 4× A55) or higher |
| Working frequency | ~2.1–3.7 GHz (Ryzen 5 baseline) | Up to 2.4 GHz (high-performance cores) ⚠️ values differ |
| RAM | 12 GB+ | 12 GB optimal; 8 GB recommended; 6 GB minimum |
| Storage (ROM) | 128 GB | 128 GB recommended; 64 GB minimum |
| GPU min | Adreno 619 ⚠️ | Adreno 640 or equivalent (manageable); Adreno 650+ recommended ⚠️ values differ |
| GPU requirements | — | Must support OpenGL ES 3.2, Vulkan 1.1, hardware-accelerated WebView rendering |
| Recommended combination | — | CPU: Snapdragon 778G / 7 Gen1 / 8 Gen1; GPU: Adreno 642+ / 660 |
| Wi-Fi | Wi-Fi 6 — 802.11 b/g/n/a/ac/ax (2.4 GHz + 5 GHz) | Same; built-in Wi-Fi 6 module |
| Bluetooth | BT 5 (2.4 GHz, 0–10 m) | Not required for floor kiosk; okay to have |
| LAN / Ethernet | To be supported | Gigabit Ethernet (10/100/1000 Mbps) — RJ45; 1 port |
| Touch | Capacitive, 10-point | Capacitive, 10-point multi-touch |
| Speakers | 2 × 5W (2 sound tracks) | — |
| USB | USB 3.0 ×1; USB-C ×1 (full-featured, no charging) | USB 3.0 ×1; USB-C ×1 (full-featured, data only — no charging) |
| Other ports | Audio Out ×1 (3.5 mm); DC-IN ×1 | Audio Out ×1 — 3.5 mm (Optional); DC Power Input ×1 |
| Patch updates | Supported without forced restarts (configurable) | Same |
| App support | — | Google Apps |
| Kiosk mode | Guided lock mode — disables back button, restricts URL exit, locks to single app | Same |

### Unsupported Hardware (from Device Datasheet)

Do not procure devices with any of the following components:

| Component | Disqualified values |
|-----------|-------------------|
| GPU | Mali-400, Mali-450, Mali-T720, Mali-T760, or older ARM GPUs |
| Processor | Rockchip RK30xx series; older MediaTek MT65xx / MT67xx |
| RAM | Less than 6 GB |
| Android version | Android 10 or below |

_Source: [[sources/floor-kiosk-device-spec]], [[sources/se-runbook-floor-kiosk]]_

## Scalefusion MDM

WorkInSync uses [Scalefusion](https://scalefusion.com/) as the MDM (Mobile Device Management) platform to enroll, lock, and remotely manage Android and iPad kiosk devices.

### What Scalefusion manages
- Enforces guided kiosk mode (single-app lock; disables back button, URL exit)
- Pushes app updates without forced device restarts
- Provides remote monitoring and screen-casting via the **RemoteCast** app (called "Remote Sharing" in the enrollment flow)
- Manages permissions (overlay, accessibility, remote-sharing) centrally

### Enrollment overview
Two document types exist:
- **"Setting Up Scalefusion on Android and iPad Devices"** — generic enrollment doc (authored by WorkInSync Implementation Team); example device names in the doc use meeting-room naming (`MR Kiosk`) — cross-reference [[modules/meeting-rooms]] for MR-specific details.
- **"Meeting room kiosk Scalefusion"** — MR-specific variant; content is meeting-rooms noise, not duplicated here.

For the floor kiosk device setup procedure (Android enrollment, permissions, device naming, remote sharing), see **[[runbooks/floor-kiosk-device-setup]]**.

_Source: [[sources/se-runbook-floor-kiosk]]_

---

## Employee Flow Kiosk (`isEmployeeFlowEnabled`)

The **employee flow** is a mode of the visitor/self-checkin kiosk that presents employees (rather than external visitors) with a separate landing screen and action set.

### How to enable

`isEmployeeFlowEnabled` is a sub-key within the **`visitorKioskConfigs`** JSON blob in the VISITOR service. It is not a standalone PMS row.

```json
// Within visitorKioskConfigs — set this to true to activate employee flow
{ "isEmployeeFlowEnabled": true }
```

Alongside enabling the flag, configure the multilingual header text:

```json
"employeeDescriptionHeaderText": {
  "en": "Employee, please select an action below",
  "es": "Empleado, por favor seleccione una acción a continuación",
  "fr": "Employé, veuillez sélectionner une action ci-dessous",
  "nl": "Werknemer, selecteer alstublieft een actie hieronder"
}
```

Also set `DefaultEndTimeOfEmployeeBooking = 1439` (represents 23:59 — end of day).

### Custom fields in the employee flow

The employee flow supports custom profile fields via the same `subfields` mechanism used by the visitor forms (see §Self-Checkin Custom Forms below). Key rules from the source:

- Skip the first three sections of the `visitorFormsMetaData` config (those are profile fields: name, email, phone).
- Add required custom fields under `subfields`.
- Set `parentConfigValue` to `employee` for fields that should appear in the employee flow.
- `itemList` must **not** contain `employee`.

> ⚠️ `isEmployeeFlowEnabled` lives inside `visitorKioskConfigs` (VISITOR service), not as a top-level PMS property. See [[configs/visitor-management]] for the full VISITOR service config table. The `visitor-management.md` config page is auto-generated — if re-ingesting, this note should be preserved manually.

_Source: [[sources/se-runbook-floor-kiosk]]_

---

## Self-Checkin Tablet Flow & Custom Forms

The self-checkin tablet flow allows visitors to check themselves in at a kiosk (tablet device) without receptionist assistance. Custom fields are injected via the `visitorFormsMetaData` Consul JSON key in the VISITOR service.

### Form field structure (`visitorFormsMetaData`)

Each entry in the `visitorFormsMetaData` array defines one form field:

| JSON key | Type | Description |
|----------|------|-------------|
| `fieldType` | string | UI widget type: `"input"`, `"singleselect"`, etc. |
| `fieldInputType` | string | Input sub-type: `"text"`, `"number"`, `"email"`, etc. |
| `title` | string | Label shown to the visitor on the form |
| `configName` | string | Property name used internally (e.g. `"phoneNumber"`, `"emailId"`) |
| `subFieldValue` | boolean | Whether this is a sub-field of a parent selector |
| `backedFieldType` | string | Backend storage type: `"STRING"`, etc. |
| `validators` | array | Validation rules — `Required`, `MinLength` (with `value`), `Email`, etc. |
| `parentConfigValue` | string | Visitor type this field applies to (e.g. `"employee"`, `"businessGuest"`, `"contractor"`) |
| `itemList` | array | For `singleselect` fields: list of selectable items (must not include `"employee"` if used with employee flow) |

### Visitor type segmentation

Fields can be scoped to a visitor type via `parentConfigValue`. Known visitor type values referenced in the source: `businessGuest`, `contractor`, `delivery`, `partner`, `internal`. The employee flow uses `employee` — see §Employee Flow above.

### Example field types from source

The source doc shows a `visitorFormsMetaData` example with:
- Phone number — `fieldType: "input"`, `fieldInputType: "number"`, `configName: "phoneNumber"`, validators: Required + MinLength(10)
- Email ID — `fieldType: "input"`, `fieldInputType: "text"`, `configName: "emailId"`, validators: Required + Email format

> ⚠️ The full `visitorFormsMetaData` JSON lives in Consul/PMS under the VISITOR service (not in the floor-kiosk service). This is a cross-module integration point: the floor kiosk hardware renders the form, but the form schema is owned by the VISITOR service configuration.

_Source: [[sources/se-runbook-floor-kiosk]]_

---

## Dependencies on Other Modules
- [[modules/ets]] — _(setup-time)_ floor premises (`premiseType: 4`) are created under the ETS-issued office premise; the office must exist in ETS before floor plans can be uploaded.

## Used By
- [[modules/meeting-rooms]] — room-level kiosk (status, booking, check-in, extend/cancel) uses this hardware + MDM + pairing infrastructure
- [[modules/digital-wayfinding]] — floor plan data produced by DIY Floorplanner powers indoor navigation
- [[modules/visitor-management]] — guard app kiosk device may share the same hardware spec

## Open Questions
- Is the DIY Floor Planner accessible as a self-serve feature for clients today (upsell), or still internal-only?
- Has Phase 2 (version control + S3 storage) been shipped?
- Working frequency discrepancy between Spec Sheet ("~2.1–3.7 GHz, Ryzen 5 baseline") and Device Datasheet ("up to 2.4 GHz") — confirm authoritative value with hardware team.
- GPU minimum discrepancy: Spec Sheet lists Adreno 619; Datasheet lists Adreno 640 as minimum manageable — which is current?
- Is `isEmployeeFlowEnabled` documented in the auto-generated `configs/visitor-management.md`? If not, it should be added manually and protected from regen overwrites.
- The Scalefusion enrollment doc uses meeting-room device naming (`<OrgName> - <Room> MR Kiosk`) as its example — is there a separate naming convention for floor kiosk devices?

## Last Updated
2026-06-29 — _Sources: [[sources/diy-floor-planner-prd]], [[sources/floor-kiosk-device-spec]], [[sources/floor-plan-sop]], [[sources/se-runbook-ets-office-premise]] (SE upload endpoints), [[sources/se-runbook-floor-kiosk]] (Scalefusion MDM, employee flow, self-checkin, device datasheet)_
