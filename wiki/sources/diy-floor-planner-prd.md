---
type: source
raw_path: raw/modules/floor-kiosk/Copy of Copy of DIY Floor Planner Version Control - PRD.docx
ingested: 2026-04-28
doc_type: PRD
---

# DIY Floor Planner Version Control PRD

## Source Title
DIY Floor Planner Version Control — PRD (v1.0)

## Date
17/06/2022

## Type
PRD

## Key Takeaways
- DIY Floor Planner is an **internal tool** that converts client floor plans (DWG/CAD) to interactive SVG format for use in WorkInSync.
- **Phase 1 — WorkInSync Integration**: Port the tool into WorkInSync ecosystem (adds auth — currently publicly accessible, a security risk). Accessible via sidenav to Global Admin only in `workinsync.io`.
- **Phase 2 — Version control**: Files versioned by timestamp + scheme (v1, v2…vN). DWG + JSON saved to S3 bucket (previously limited to ~5 GB server folder). Restoring a previous version resumes work from that point.
- **Restore JSON**: if a floor plan is opened without its JSON mappings, a "Restore JSON" CTA lets user select saved version by timestamp.
- **Appendix (quality issues)**: unlabelled seats highlighted in red; duplicate seat names flagged at save; UI button grouping improvements.
- Not yet a self-serve client tool — internal WIS team use only (upsell potential flagged in PRD).

## Entities Mentioned
- None.

## Modules Mentioned
- [[modules/floor-kiosk]] (primary — houses DIY Floor Planner tool)
- [[modules/digital-wayfinding]] (floor plans feed into wayfinding)

## Decisions Extracted
- None.

## Wiki Pages Created/Updated
- Updated: [[modules/floor-kiosk]]

_Source: [[sources/diy-floor-planner-prd]]_
