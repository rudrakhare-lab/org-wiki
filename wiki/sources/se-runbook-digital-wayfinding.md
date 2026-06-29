---
type: source
raw_path: raw/se-runbook/crawl/files/1V5cNGQGUaYYBnOuZsZ9naI-v2vMLEfZI_VSnH9ZbEWQ.docx
ingested: 2026-06-29
doc_type: spec
---

# Source Summary — Digital Wayfinding (SE Runbook Ingest)

## Source Title
Multiple documents; three genuine wayfinding sources ingested; two noise documents cross-linked or skipped.

| Doc | File | Date | Used As |
|-----|------|------|---------|
| Digital Wayfinding Implementation SOP Document (v2.0) | `1V5cNGQGUaYYBnOuZsZ9naI-v2vMLEfZI_VSnH9ZbEWQ.docx` | 27 Feb 2024 | Primary — SOP steps for floor plan team + SE team |
| Digital Wayfinding Product Architecture Diagram (v1.0) | `1tPBe_9wZBzmvAckfuZMiXbIEQxr9AJs38vCyRnfCGOU.docx` | 17 Aug 2022 | Architecture context — diagram is an embedded image (not extracted as text) |
| "What if there could be a Google Maps, but for offices?" | `1iJGsGFvmvOtndlUajsYOO1t7eYXBEYejiFL3WOavKdI.docx` | not dated | Value/use-case concept doc |
| WorkInSync Floor plans - Add / Update SOP | `1jvoXYCrQ1nDeUY_onWR9r1ssQCqIfRr2BPqmLTWegUA.docx` | 26 Aug 2022 | NOISE — cross-linked to [[runbooks/floor-plan-upload]]; not re-ingested |
| Recommended Reading — Microsoft Azure Maps docs | external URL | n/a | OFF-TOPIC — skipped entirely |
| Ops Study xlsx (TABS: Ops Study, Office, etc.) | spreadsheet | n/a | OFF-TOPIC — skipped entirely |

## Date
- SOP v2.0: 27 February 2024 (latest; used as `last_updated` for module and runbook)
- Architecture diagram v1.0: 17 August 2022
- Value/use-case doc: undated

## Type
spec / SOP (primary); concept / marketing (value doc); architecture diagram (image-only)

## Key Takeaways

- Digital Wayfinding uses **QR codes** (not Bluetooth beacons) for location detection, reducing
  implementation cost significantly. WorkInSync CTO Akash Maheshwari: "our intervention and
  approach has been to make it accessible without investing millions."
- The **DIY Floorplanner (CADViewer)** is the internal tool used to convert CAD floor plans into
  interactive navigation graphs. It produces two files per floor: `.json` (graph) + `.svg` (visual).
- **Way Path upload must be done inside the tool** — it cannot be done via Postman or API. The
  'Upload Project' floorplan data can go via Postman; the Way Path cannot.
- **ENABLE_INDOOR_NAVIGATION** is the only documented config gate; it is disabled by default and
  enabled per BUID via SE ticket.
- **Parking support** was added in SOP v2.0 (Feb 2024): parking paths are unidirectional (unlike
  office paths which are bi-directional); car/bike/stacked slot types are configurable.
- The architecture diagram document (v1.0, Aug 2022) exists but its diagram is an embedded image —
  not extractable as text. The architecture flow was reconstructed from the SOP.
- The **productivity problem**: 2019 Senion survey — 39% of US employees waste ~60 min/week
  searching for meeting rooms/colleagues (~$27B/year national productivity loss).
- **Floor plans - Add/Update SOP** is a noise document for this ingest — it covers floor plan
  upload (not wayfinding path setup) and is already fully documented in [[runbooks/floor-plan-upload]].

## Entities Mentioned
- `premiseID` — floor-level identifier used by the Wayfinding service
- `parentPremiseID` — links a floor premise to its parent office premise
- `ENABLE_INDOOR_NAVIGATION` — config flag (master switch for the feature)
- `forceUpdateFloorPlan` — Postman parameter (always `false`)
- `wktDimensionInCm` — Postman parameter (`100`)
- `employeeFloorPlanUrl`, `adminFloorPlanUrl`, `adminAssignmentFloorPlanUrl` — employee-experience
  config keys for floor plan URL routing (first-time setup)

## Modules Mentioned
- [[modules/digital-wayfinding]] — primary module (this ingest)
- [[modules/mobile-app]] — wayfinding surface is exclusively mobile
- [[modules/parking-management]] — parking slots as navigable amenities (v2.0)
- [[modules/floor-kiosk]] — shares floor premise infrastructure

## Decisions Extracted
None formally documented. The QR-code-over-Bluetooth-beacon architectural choice is the most
significant implicit decision; it is noted as a product design choice in [[modules/digital-wayfinding]]
rather than as a separate decision page (insufficient detail for a full decision page).

## Noise Documents — Cross-links Applied
- **WorkInSync Floor plans - Add/Update SOP**: content cross-linked to [[runbooks/floor-plan-upload]].
  Not re-ingested — that runbook already documents floor plan upload fully.
- **Recommended Reading (Microsoft Azure Maps)**: off-topic external reference; skipped.
- **Ops Study xlsx**: off-topic operational data; skipped.

## Wiki Pages Created / Updated

| Page | Action |
|------|--------|
| [[modules/digital-wayfinding]] | Updated — added value/use-case, product architecture section, DIY tool concepts table, API endpoints, cross-module notes; appended source to frontmatter |
| [[runbooks/digital-wayfinding-setup]] | Created — SE implementation steps (upload JSON+SVG, enable flag, first-time URL check) |
| [[sources/se-runbook-digital-wayfinding]] | Created — this page |
