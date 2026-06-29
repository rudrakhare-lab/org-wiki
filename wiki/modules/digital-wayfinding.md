---
type: module
status: active
owner: "Aditya Dutta / Ujjwal Trivedi (floor plan team lead: Vikas Upadhyay)"
depends_on: [mobile-app, parking-management, floor-kiosk]
used_by: []
last_updated: 2024-02-27
source: "[[sources/digital-wayfinding-sop]], [[sources/se-runbook-digital-wayfinding]]"
---

# Digital Wayfinding Module (Indoor Navigation)

## Overview
Digital Wayfinding provides turn-by-turn indoor navigation on the mobile app, helping employees
navigate to desks, parking slots, meeting rooms, washrooms, lifts, cafeterias, and other amenities
within an office floor plan. Visible only on mobile (config-gated: `ENABLE_INDOOR_NAVIGATION`).

WorkInSync's implementation replaces costly Bluetooth beacon infrastructure with QR codes for
location detection, making indoor navigation accessible without large capital investment. The
product traces the shortest path to any destination on interactive floor plans derived from
client-supplied CAD drawings.

_Source: [[sources/se-runbook-digital-wayfinding]] — "What if there could be a Google Maps, but for offices?" concept doc_

## Purpose & Scope
Owns the indoor navigation feature — floor plan ingestion pipeline, wayfinding path computation,
and mobile surface for navigation. Does **not** own floor plan storage for booking purposes (that
belongs to desk/meeting room modules); this module owns the navigation graph specifically.

### Value Proposition
Indoor navigation is a historically costly problem: a 2019 Senion survey found 39% of US
employees waste ~60 mins/week searching for meeting rooms and colleagues, representing ~$27B/year
in lost productivity nationally. Traditional indoor navigation required Bluetooth beacons with
significant installation and maintenance costs. WorkInSync's approach uses QR codes for
localization + algorithmic shortest-path routing on SVG floor plans, bringing down the cost of
entry substantially.

Target users: newly-joined employees unfamiliar with the office layout, remote employees
visiting infrequently, and employees who move between buildings or offices in different cities.

_Source: [[sources/se-runbook-digital-wayfinding]] — value/use-case doc_

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

## Product Architecture

The architecture document (v1.0, 17 August 2022, authors Aditya Dutta / Ujjwal Trivedi) describes
the information flow in the WorkInSync application for the Digital Wayfinding module. The diagram
itself is an embedded image in the source and was not extractable as text; the description below
is reconstructed from the SOP and related sources.

```
Client CAD assets (DWG / PNG / PDF)
        │
        ▼
DIY Floorplanner / CADViewer (internal tool)
  ├── Amenity marking (desks, rooms, lifts, parking, etc.)
  ├── Walkway path drawing (bi-dir: office; uni-dir: parking)
  ├── Seat Paths: maps each amenity node → drawn path
  ├── Path Validation: verifies graph connectivity
  └── Export → JSON (graph data) + SVG (visual layer)
        │
        ├─── Upload Way Path (IN TOOL ONLY — cannot use Postman)
        │         Select environment: SG (Singapore) or EU (Europe)
        │
        ▼
Wayfinding service  (also called "Premise service" in older docs)
  ├── Stores premiseID + parentPremiseID per floor
  ├── Holds navigation graph for path computation
  └── Feeds shortest-path responses to mobile app
        │
        ▼
Mobile App (WorkInSync)
  └── ENABLE_INDOOR_NAVIGATION = true → shows interactive floor plan
        └── Employee scans QR code → current location resolved
              └── Selects destination amenity → shortest path rendered
```

**Key service identifiers:**
- The JSON+SVG is uploaded via SE team Postman to `wis-premise.workinsync.io` (the Wayfinding /
  Premise service).
- `premiseID` identifies a floor; `parentPremiseID` links it to the office premise.
- Environment selection (SG / EU) at upload time routes the data to the correct regional endpoint.

> ⚠️ The architecture diagram image was not extractable from the source document
> (`1tPBe_9wZBzmvAckfuZMiXbIEQxr9AJs38vCyRnfCGOU.docx`). The above is reconstructed from
> the SOP and related sources. If you need the original diagram, open the source doc.

_Source: [[sources/se-runbook-digital-wayfinding]] — architecture diagram doc + SOP_

## DIY Floorplanner Tool — Key Concepts

The DIY Floorplanner (CADViewer) is the internal tool used by the floor plan team to convert
raw CAD floor plans into interactive navigation graphs.

| Tool Function | Description |
|---|---|
| Amenity markers | Place icons for desks, rooms, lifts, exits, reception, washrooms, cafeteria, stairs, parking slots |
| Seat name + orientation | Each desk/seat must have a name label AND an angle (orientation); both required |
| Draw line | Draws walkway paths; all lines must be fully connected (disconnected lines prevent path computation) |
| Edit line | Modifies existing paths |
| Disconnected lines indicator | Visual check — all lines must be connected before export |
| Seat Paths | Maps each amenity node to the walkway path network |
| Path Validation | Verifies graph connectivity; run before feeding to DB |
| Sync UUID | Re-syncs UUIDs when amenity set changes; preserves unique-identifier integrity |
| Upload Project | Uploads floor plan data to the service (can also be done via Postman API) |
| Upload Way Path | Uploads wayfinding graph data — **MUST be done in the tool; Postman cannot do this** |
| Export | Produces two files per floor: `.json` (graph) + `.svg` (visual) |

**Path direction rules:**
- Office/desk floors: **bi-directional** paths
- Parking floors: **unidirectional** paths (each segment can be set RTL or LTR)

**Reception as source:** Each floor plan has one reception designated as the de-facto navigation
starting point. Multiple receptions may appear on a floor, but only one is treated as the source.

**Multi-floor amenities:** Amenities that span floors (stairs, elevators) must carry the same name
across all floor plans for the path computation to chain correctly.

_Source: [[sources/se-runbook-digital-wayfinding]] — SOP v2.0_

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
| `ENABLE_INDOOR_NAVIGATION` | false | Master switch — shows wayfinding on mobile app; enabled per BUID via SE ticket |

No additional PMS config properties for wayfinding are documented in the PMS config sources.
The feature toggle is the only confirmed configuration gate.

_Source: [[sources/se-runbook-digital-wayfinding]]_

## Dependencies on Other Modules
- [[modules/mobile-app]] — wayfinding is a feature inside the mobile app; not available on web
- [[modules/parking-management]] — parking slots are navigable amenities on floor plans (added v2.0, Feb 2024)
- [[modules/floor-kiosk]] — shares the floor plan premise setup infrastructure (premiseID / parentPremiseID); floor plan upload runbook lives under floor-kiosk tooling — see [[runbooks/floor-plan-upload]]

## Used By
_(none confirmed — wayfinding is a terminal feature consumed by employees via mobile app)_

## Cross-Module Notes
- **Floor plan upload** is handled by the SE team using the floor-plan-upload runbook
  ([[runbooks/floor-plan-upload]]) — that runbook documents the floor premise creation and
  plan upload steps. The digital-wayfinding SOP's SE steps (uploading JSON+SVG to the
  Wayfinding service and enabling `ENABLE_INDOOR_NAVIGATION`) are the downstream continuation
  of that flow, documented separately in [[runbooks/digital-wayfinding-setup]].
- **Floor plans - Add | Update SOP** (noise doc in source) — this document covers floor plan
  upload only (not wayfinding path setup). Content cross-links to [[runbooks/floor-plan-upload]];
  it is not re-ingested here.

## Updating Navigation Data
If navigation must be updated (missing amenities or incorrect mappings): update the floor plans /
mappings / paths, re-generate the mappings, Sync UUID, and re-export the data as JSON — then feed
it back to the Wayfinding service. This is a **manual** re-export procedure; no automatic
propagation is triggered by booking-side changes.

_Source: [[sources/digital-wayfinding-sop]]_

## API Endpoints
| Method | Path | Description | Auth Required |
|---|---|---|---|
| POST | `https://wis-premise.workinsync.io/mis-security-guard/csv/upload/layout/<FloorPremiseID>` | Upload JSON+SVG floor plan data to Wayfinding service | Yes |

Query params: `forceUpdateFloorPlan=false`, `wktDimensionInCm=100`
Body: form-data — `floorImage` (`.svg`), `floor` (`.json`)

> ⚠️ `forceUpdateFloorPlan` must always be `false` even on re-uploads. Do NOT set to `true`.

> ⚠️ Way Path upload (navigation graph) must be done inside the DIY Floorplanner tool — it
> cannot be done via Postman or any API.

_Source: [[sources/se-runbook-digital-wayfinding]] — SOP v2.0_

## Open Questions
- **Web vs mobile**: SOP v2.0 documents the **mobile** surface only and gates it on `ENABLE_INDOOR_NAVIGATION`; whether wayfinding is viewable on the web app is unconfirmed.
- **Realloc-triggered refresh**: floor-plan updates are a **manual** re-export (see Updating Navigation Data); the SOP does not describe any automatic propagation when desk allocations change — realloc-triggered refresh handling remains unconfirmed.
- **Architecture diagram**: the architecture diagram in the product architecture doc is an embedded image and was not extracted as text. The reconstructed flow diagram above is inferred from SOP + related sources.
- **QR code scanning backend**: the value-prop doc states QR codes replace Bluetooth beacons for location detection, but the backend service that decodes QR scans into `premiseID`/location coordinates is not described in any of the ingested sources.

## Last Updated
2024-02-27 — sources:
- _[[sources/digital-wayfinding-sop]]_ (SOP v2.0, 27 Feb 2024 — latest)
- _[[sources/se-runbook-digital-wayfinding]]_ (architecture + value docs, Aug 2022)
