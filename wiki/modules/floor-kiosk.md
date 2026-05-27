---
type: module
status: active
owner: Aditya Dutta / Ujjwal Trivedi
depends_on: []
used_by: [meeting-rooms, digital-wayfinding, visitor-management, implementation, meal-management]
last_updated: 2022-08-26
source: "[[sources/diy-floor-planner-prd]], [[sources/floor-kiosk-device-spec]], [[sources/floor-plan-sop]]"
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

## Hardware Specifications
| Parameter | Specification |
|-----------|--------------|
| Screen | 25"+ / 16:9 |
| OS | Android 12.0+ |
| Chipset | Qualcomm |
| Core | Quad-core / ARM Cortex |
| GPU | Adreno 619 / 642 / 650 / 730 |
| Working frequency | ~2.1–3.7 GHz (Ryzen 5 baseline) |
| RAM | 12 GB+ |
| Storage (ROM) | 128 GB |
| Wi-Fi | Wi-Fi 6 — 802.11 b/g/n/a/ac/ax (2.4 GHz + 5 GHz) |
| Bluetooth | BT 5 (2.4 GHz, 0–10 m) |
| Touch | Capacitive, 10-point |
| Speakers | 2 × 5W (2 sound tracks) |
| Ports | USB 3.0 ×1; USB-C ×1 (full-featured, no charging); Audio Out ×1; DC-IN ×1; LAN (to be supported) |
| Patch updates | Supported without forced restarts (configurable) |
| Kiosk mode | Guided lock mode — disables back button, restricts URL exit, locks to single app |

## Used By
- [[modules/meeting-rooms]] — room-level kiosk (status, booking, check-in, extend/cancel) uses this hardware + MDM + pairing infrastructure
- [[modules/digital-wayfinding]] — floor plan data produced by DIY Floorplanner powers indoor navigation
- [[modules/visitor-management]] — guard app kiosk device may share the same hardware spec

## Open Questions
- Is the DIY Floor Planner accessible as a self-serve feature for clients today (upsell), or still internal-only?
- Has Phase 2 (version control + S3 storage) been shipped?

## Last Updated
2022-08-26 — _Source: [[sources/diy-floor-planner-prd]], [[sources/floor-kiosk-device-spec]], [[sources/floor-plan-sop]]_
