---
type: source
raw_path: raw/modules/floor-kiosk/Copy of WorkInSync Floor plan - Add | Update - SOP.docx
ingested: 2026-04-28
doc_type: spec
---

# Floor Plan — Add/Update SOP

## Source Title
WorkInSync Floor Plans — Add | Update SOP (v1.0)

## Date
26 August 2022

## Type
spec (internal SOP)

## Key Takeaways
- Earlier version of the floor plan pipeline SOP (predates digital wayfinding SOP v2.0 which added parking support).
- **Pipeline**: receive DWG from client → clean + digitize → upload to DIY Floorplanner → mark amenities (meeting rooms, washrooms, lifts, cafeteria, desks) → draw walkway paths → click 'Seat Paths' → click 'Verify Data' → export as JSON → feed to **Premise service** (not Wayfinding service — older naming).
- Premise service stores `premiseID` and `parentPremiseID` for path computation.
- Meeting room names **must match** Google/Outlook calendar names exactly.
- Every seat must have a name + orientation (angle).
- Paths drawn top-down (longest walkways first); any disconnected paths cause re-work.
- If floor plan needs updating: re-draw paths, re-generate, export JSON, re-upload.
- Compare with [[sources/digital-wayfinding-sop]] (v2.0) — adds parking support, direction control, CADViewer UUID sync, SVG export, and Wayfinding service naming.

## Entities Mentioned
- None.

## Modules Mentioned
- [[modules/floor-kiosk]] (primary)
- [[modules/digital-wayfinding]] (downstream consumer of floor plan data)

## Decisions Extracted
- None.

## Wiki Pages Created/Updated
- Updated: [[modules/floor-kiosk]]

_Source: [[sources/floor-plan-sop]]_
