---
type: module
status: active
owner: Aditya Dutta / Ujjwal Trivedi
depends_on: []
used_by: [meeting-rooms, digital-wayfinding, visitor-management]
last_updated: 2026-04-28
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
- **Phase 1** (completed): integrated into WorkInSync ecosystem — accessible by Global Admin only in sidenav
- **Phase 2** (planned): version control — DWG + JSON versioned by timestamp and stored in S3
- **Security**: previously publicly accessible — Phase 1 integration added WIS auth

### Floor Plan Data Pipeline
```
Client provides DWG/PNG/PDF
    → Floor plan team cleans and imports into DIY Floorplanner
    → Mark all amenities + draw paths
    → Verify/validate paths
    → Export JSON + SVG
    → SE team uploads via Postman to Wayfinding service (JSON) and Premise service
    → SE ticket to enable feature flag per BUID
```
- DWG → SVG must be < 2 MB (else use PNG)
- Meeting room names must match Outlook/Google calendar names exactly
- Floor plan updates: re-draw affected paths → re-export JSON → re-upload

## Hardware Specifications
| Parameter | Specification |
|-----------|--------------|
| Screen | 25"+ / 16:9 |
| OS | Android 12.0+ |
| RAM | 12 GB+ |
| Storage | 128 GB |
| Wi-Fi | Wi-Fi 6 (2.4 GHz + 5 GHz) |
| Bluetooth | BT 5 |
| Touch | Capacitive, 10-point |
| Kiosk mode | Guided lock mode — disables back button |

## Used By
- [[modules/meeting-rooms]] — room-level kiosk (status, booking, check-in, extend/cancel) uses this hardware + MDM + pairing infrastructure
- [[modules/digital-wayfinding]] — floor plan data produced by DIY Floorplanner powers indoor navigation
- [[modules/visitor-management]] — guard app kiosk device may share the same hardware spec

## Open Questions
- Is the DIY Floor Planner accessible as a self-serve feature for clients today (upsell), or still internal-only?
- Has Phase 2 (version control + S3 storage) been shipped?

## Last Updated
2026-04-28 — _Source: [[sources/diy-floor-planner-prd]], [[sources/floor-kiosk-device-spec]], [[sources/floor-plan-sop]]_
