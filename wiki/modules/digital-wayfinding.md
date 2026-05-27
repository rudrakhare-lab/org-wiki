---
type: module
status: active
owner: "Aditya Dutta / Ujjwal Trivedi (floor plan team lead: Vikas Upadhyay)"
depends_on: [mobile-app, parking-management, floor-kiosk]
used_by: []
last_updated: 2024-02-27
source: "[[sources/digital-wayfinding-sop]]"
---

# Digital Wayfinding Module (Indoor Navigation)

## Overview
Digital Wayfinding provides turn-by-turn indoor navigation on the mobile app, helping employees
navigate to desks, parking slots, meeting rooms, washrooms, lifts, cafeterias, and other amenities
within an office floor plan. Visible only on mobile (config-gated: `ENABLE_INDOOR_NAVIGATION`).

## Purpose & Scope
Owns the indoor navigation feature — floor plan ingestion pipeline, wayfinding path computation,
and mobile surface for navigation. Does **not** own floor plan storage for booking purposes (that
belongs to desk/meeting room modules); this module owns the navigation graph specifically.

## Key Features
- **Floor plan pipeline**: CAD files (DWG/PNG/PDF) → DIY Floorplanner (CADViewer) → marked amenities + drawn paths → JSON+SVG export → Wayfinding service (uploaded by SE team via Postman).
- **File-size constraint**: a DWG converted to SVG must be **< 2 MB**; if larger, convert it to PNG so floor plans do not take excessive time to load.
- **Amenity types**: desks, parking (car/bike, stacked, vehicle type: Hatchback/Sedan/SUV), meeting rooms, washrooms, lifts, entry/exit, reception, cafeteria, stairs.
- **Reception as navigation source**: one reception per floor plan marked as de-facto starting point. Multiple receptions may exist on a floor plan, but only one is treated as the source.
- **Multi-floor support**: amenities spanning floors (stairs, elevators) use the same name across all floors.
- **Meeting room names must match Outlook/Google calendar** exactly (critical for correct mapping).
- **Seat labeling**: every marked seat must have a name **and an orientation (angle)**. Client naming conventions (supplied via Excel or an image/PDF) are followed strictly; if none is given, the floor-plan team establishes a standard convention.
- **Parking support** (v2.0 added Feb 2024): parking floor plan paths are unidirectional (cars flow one-way); stacked/bike slot types configurable.
- **Path direction**: office = bi-directional; parking = unidirectional (each unidirectional path may be set RTL or LTR).

## Implementation Flow (Internal)
```
1. Pre-sales: Collect DWG/PNG/PDF floor plans from client → upload to floor plan team
   (Vikas Upadhyay) via the intake Google Form
   - A DWG converted to SVG must be <2 MB; otherwise convert to PNG (load-time)
2. Floor plan team: Import into DIY Floorplanner (CADViewer)
   - Mark all amenities (desks, rooms, exits, lifts, parking, etc.); each seat needs a name + orientation
   - Draw walkway paths (top-down approach; bi-dir for office, uni-dir for parking)
   - 'Seat Paths' maps amenities to the drawn paths; 'Path Validation' verifies before DB feed
   - Sync UUID if amenities changed (preserves unique-identifier integrity)
   - Export JSON + SVG (2 files per floor)
   - Upload Way Path — must be done IN THE TOOL, not via Postman
     (the 'Upload Project' floorplan data CAN go via Postman API; the Way Path cannot)
   - On upload, select environment SG / EU (Singapore or Europe, per customer site URL)
3. SE team: Upload SVG + JSON via Postman to Wayfinding service per floor
4. SE team: Enable ENABLE_INDOOR_NAVIGATION via SE ticket for the BUID
```
The exported JSON is fed to the **Wayfinding service** (older name: *Premise service*, per
[[sources/floor-plan-sop]]), which stores `premiseID` and `parentPremiseID` and uses them for
path computation.

## Key Configurations
| Config Key | Default | Description |
|---|---|---|
| `ENABLE_INDOOR_NAVIGATION` | false | Master switch — shows wayfinding on mobile app (SE ticket to enable) |

## Dependencies on Other Modules
- [[modules/mobile-app]] — wayfinding is a feature inside the mobile app
- [[modules/parking-management]] — parking slots are navigable amenities on floor plans (v2.0)

## Updating Navigation Data
If navigation must be updated (missing amenities or incorrect mappings): update the floor plans /
mappings / paths, re-generate the mappings, Sync UUID, and re-export the data as JSON — then feed
it back to the Wayfinding service. This is a manual re-export procedure.

## Open Questions
- **Web vs mobile**: SOP v2.0 documents the **mobile** surface only and gates it on `ENABLE_INDOOR_NAVIGATION`; whether wayfinding is viewable on the web app is unconfirmed (the source makes no positive or negative statement).
- **Realloc-triggered refresh**: floor-plan updates are a **manual** re-export (see Updating Navigation Data); the SOP does not describe any automatic propagation when desk allocations change in the booking system — so realloc-triggered refresh handling remains unconfirmed.

## Last Updated
2024-02-27 — _Source: [[sources/digital-wayfinding-sop]]_
