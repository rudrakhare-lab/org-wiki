---
type: source
raw_path: raw/modules/employee-experience/Digital Wayfinding - Implementation SOP Document.docx
ingested: 2026-04-28
doc_type: spec
---

# Digital Wayfinding — Implementation SOP

## Source Title
Digital Wayfinding Implementation SOP Document (v2.0)

## Date
v1.0: 17 August 2022; v2.0: 27 February 2024 (added parking support)

## Type
spec (internal implementation SOP)

## Key Takeaways
- Digital Wayfinding (also called Indoor Navigation) allows employees to navigate to desks, parking slots, meeting rooms, and other amenities within an office floor plan on the mobile app.
- Feature flag: `ENABLE_INDOOR_NAVIGATION` (default: false, enabled via SE ticket per BUID).
- **Floor plan pipeline**: Client provides DWG/PNG/PDF → Floor plan team imports into **DIY Floorplanner (CADViewer)** → marks amenities → draws paths → exports JSON+SVG → SE team uploads to Wayfinding service via Postman.
- **Amenity types** that can be marked: desks, parking slots (with vehicle type: 2-wheeler/4-wheeler, slot type: hatchback/sedan/SUV), meeting rooms, washrooms, lifts, cafeteria, entry/exit, reception.
- **Reception** = source (de-facto starting point for navigation). Multiple receptions on a floor allowed; only 1 is the navigation source.
- **DWG → SVG** must be < 2 MB after conversion. If larger, convert to PNG first.
- **CADViewer tools**: direction selector (bi-directional for office, unidirectional for parking), amenity selector, path validation, Sync UUID (use when amenities change), Upload Project, Upload Way Path.
- **Path drawing**: top-down approach (longest walkways first). Paths connect amenities to walkways; validated before upload.
- **Multi-floor**: stairs/elevators must use same name across floors for connectivity.
- **Meeting room names must match Outlook/Google calendar names** exactly.
- v2.0 change: added support for parking floor plans (unidirectional paths, stacked/bike slot types).
- Navigation updates: re-generate paths, sync UUID, re-export JSON, re-upload to Wayfinding service.

## Entities Mentioned
- None new.

## Modules Mentioned
- [[modules/digital-wayfinding]] (primary)
- [[modules/employee-experience]] (filed under emp-exp in Drive; surface in mobile app)
- [[modules/parking-management]] (parking slot amenities added in v2.0)
- [[modules/mobile-app]] (wayfinding displayed on mobile app)

## Decisions Extracted
- None.

## Wiki Pages Created/Updated
- Created: [[modules/digital-wayfinding]]

_Source: [[sources/digital-wayfinding-sop]]_
