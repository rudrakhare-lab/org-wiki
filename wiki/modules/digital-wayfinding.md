---
type: module
status: active
owner: Aditya Dutta / Ujjwal Trivedi (floor plan team lead: Vikas Upadhyay)
depends_on: [mobile-app, parking-management]
used_by: []
last_updated: 2026-04-28
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
- **Floor plan pipeline**: CAD files (DWG/PNG/PDF) → DIY Floorplanner tool (CADViewer) → marked amenities + drawn paths → JSON+SVG export → Wayfinding service (uploaded by SE team via Postman).
- **Amenity types**: desks, parking (car/bike, stacked, vehicle type: Hatchback/Sedan/SUV), meeting rooms, washrooms, lifts, entry/exit, reception, cafeteria, stairs.
- **Reception as navigation source**: one reception per floor plan marked as de-facto starting point.
- **Multi-floor support**: amenities spanning floors (stairs, elevators) use the same name across all floors.
- **Meeting room names must match Outlook/Google calendar** exactly (critical for correct mapping).
- **Parking support** (v2.0 added Feb 2024): parking floor plan paths are unidirectional (cars flow one-way); stacked/bike slot types configurable.
- **Path direction**: office = bi-directional; parking = unidirectional.

## Implementation Flow (Internal)
```
1. Pre-sales: Collect DWG/PNG/PDF floor plans from client → upload to floor plan team (Vikas Upadhyay)
2. Floor plan team: Import into DIY Floorplanner (CADViewer)
   - Mark all amenities (desks, rooms, exits, lifts, parking, etc.)
   - Draw walkway paths (top-down approach; bi-dir for office, uni-dir for parking)
   - Validate paths (Path Validation button); sync UUID if amenities changed
   - Export JSON + SVG (2 files per floor)
   - Upload Way Path to Wayfinding service (must be done in tool — not API)
3. SE team: Upload SVG + JSON via Postman to Wayfinding service per floor
4. SE team: Enable ENABLE_INDOOR_NAVIGATION via SE ticket for the BUID
```

## Key Configurations
| Config Key | Default | Description |
|---|---|---|
| `ENABLE_INDOOR_NAVIGATION` | false | Master switch — shows wayfinding on mobile app (SE ticket to enable) |

## Dependencies on Other Modules
- [[modules/mobile-app]] — wayfinding is a feature inside the mobile app
- [[modules/parking-management]] — parking slots are navigable amenities on floor plans (v2.0)

## Open Questions
- Is wayfinding viewable on the web app or only mobile? (SOP only mentions mobile.)
- How are floor plan updates handled when desk allocations change?

## Last Updated
2026-04-28 — _Source: [[sources/digital-wayfinding-sop]]_
