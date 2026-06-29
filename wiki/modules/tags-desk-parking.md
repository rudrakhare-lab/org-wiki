---
type: module
status: active
owner: unknown
depends_on: []
used_by: [meeting-rooms, parking-management, desk-management]
last_updated: 2026-06-29
source: "[[sources/se-runbook-tags-desk-parking]]"
---

# Tags — Desk + Parking | Dynamic Policy Engine

## Overview

The Tags & Dynamic Policy Engine is a foundational shared service that powers tag-based access control across desk booking, parking, and meeting rooms. It owns the lifecycle of tag definitions (creating tags, mapping values, assigning tags to employees and resources), the `SeatTypeMapping` configuration that classifies seats by type, and the `consulConfiguration/dynamicFields` schema that renders custom data-capture fields at booking time. Downstream modules consume these capabilities via the `mis-floor-plan` tag API and the `wisSeatBooking` Consul config API without re-implementing them.

_Source: [[sources/se-runbook-tags-desk-parking]]_

## Purpose & Scope

**Owns:**
- Tag definitions: `tagName`, `tagType` (`SINGLE_VALUED`), `entityType` (confirmed in SE source: `EMPLOYEE`, `PARKING`; additional entity types likely exist for desk/room surfaces but are not enumerated in source) — created via `POST /mis-floor-plan/api/<BUID>/tags`
- Tag value mappings (`tagValue` → `buTagId`) — created via `POST /mis-floor-plan/api/<BUID>/tags/polygons`
- `SeatTypeMapping` — a per-BUID configuration mapping individual seat names to named seat types (e.g. Workstation, Partner Cabin, Director Cubicle/Cabin); consumed by the floor-plan and allocation layers
- `consulConfiguration/dynamicFields` — the per-service Consul-backed JSON schema for dynamic booking fields (e.g. mode of transport, license plate); managed via the `wisSeatBooking` Consul config API
- Bulk upload templates for employee tagging and resource (slot/desk) tagging

**Does NOT own:**
- The booking logic that enforces tag-based policies (owned by the respective module: desk-management, parking-management, meeting-rooms)
- Floor plan creation or premise setup (owned by floor-kiosk / runbooks)
- Visitor-management dynamic fields (a structurally similar but separate JSON config owned by visitor-management — see Open Questions)
- Booking Rule Engine evaluation (separate service)

_Source: [[sources/se-runbook-tags-desk-parking]]_

## Key Features

- **Tag creation via API (SE-only):** Tags are created through the `mis-floor-plan` REST API with `entityType`, `tagName`, and `tagType`. A `buTagId` GUID is returned and must be captured for subsequent value mapping.
- **Tag value mapping:** After tag creation, `tagValue` strings are mapped to each tag's `buTagId` via the polygons endpoint. In the SE source, example `tagName` values include `Executive`, `Visitor`, `Specially Able Person`; each such tag name is associated with `Yes`/`No` tag values — tag names and tag values are distinct concepts.
- **Multi-domain tag reuse:** The same tag engine serves all three booking surfaces — desks, parking slots, and meeting rooms — with no per-domain fork. Tags created for parking can reference the same `entityType=EMPLOYEE` definitions used by desk/room policies.
- **SeatTypeMapping configuration:** Classifies each seat (by exact name) into a seat type. Columns: `Office Name | Floor Name | Seat Name | Seat Type`. Known types in the SE source: `Workstation`, `Partner Cabin`, `Director Cubicle/ Cabin`. Upload/apply mechanism not documented in SE sources — flagged as Open Question.
- **Dynamic booking fields (`consulConfiguration/dynamicFields`):** A Consul-backed JSON payload (`DynamicData` array) stored per-service (e.g. `wisSeatBooking`) that configures which additional fields employees must fill at booking time. Each field object carries `fieldType`, `configName`, `backedFieldType`, `validators`, `itemsList`, and optional `subFields` for conditional nested inputs.
- **Bulk upload support:** Tag assignments to employees and resources are applied in bulk via upload files (employee tagging file, parking/desk tagging file). See [[runbooks/parking-dynamic-policy]] for the parking-specific workflow.

_Source: [[sources/se-runbook-tags-desk-parking]]_

## Data Entities Used

- [[entities/room-tag]] — the canonical tag/value entity owned by this module; consumed by meeting-rooms, parking-management, and desk-management for Dynamic Policy evaluation

_Source: [[sources/se-runbook-tags-desk-parking]]_

## Dependencies on Other Modules

None — this is a foundational engine module. It depends on no other wiki module.

`depends_on: []` confirmed. The `mis-floor-plan` service and `wisSeatBooking` Consul API are backend services, not wiki-level module dependencies.

_Source: [[sources/se-runbook-tags-desk-parking]]_

## Used By

- [[modules/meeting-rooms]] — borrows the tag engine for Dynamic Policy room access control; employee and resource tags are created here and consumed there for room eligibility rules
- [[modules/parking-management]] — tag engine drives dynamic parking policy (vehicle-type-based slot access, `BLOCK_HOTSEAT`); same engine as desks and rooms
- [[modules/desk-management]] — desk tags and employee tags drive allocation rules, booking eligibility restrictions, and approval-flow tag checks

_Source: [[sources/se-runbook-tags-desk-parking]]_

## API Endpoints

The tag engine exposes two API surfaces: the `mis-floor-plan` tag management API (SE-only, for creating and querying tags) and the `wisSeatBooking` Consul config API (for reading and updating dynamic-fields configuration).

### mis-floor-plan Tag API (SE-only, `wis-premise.workinsync.io`)

| Method | Path | Description | Auth Required |
|--------|------|-------------|---------------|
| POST | `/mis-floor-plan/api/<BUID>/tags` | Create one or more tag definitions for a BUID; returns `buTagId` GUIDs | `x-wis-token: <token>` |
| POST | `/mis-floor-plan/api/<BUID>/tags/polygons` | Map `tagValue` strings to existing tag GUIDs (`buTagId`) | `x-wis-token: <token>` |
| GET | `/mis-floor-plan/api/<BUID>/tags?entityType=<TYPE>` | List tags for a BUID filtered by entity type (e.g. `PARKING`, `EMPLOYEE`) | `x-wis-token: <token>` |

> ⚠️ The source uses `est-TakeASpin` as the example `<BUID>` — substitute the actual client BUID. Host shown in the source (`wis-premise.workinsync.io`) should be confirmed for `.com` vs `.in` server environments before use.

### wisSeatBooking Consul Config API (SE-only, beta host in source)

| Method | Path | Description | Auth Required |
|--------|------|-------------|---------------|
| GET | `/wisSeatBooking/<BUID>/consulConfiguration/dynamicFields` | Fetch the current `DynamicData` dynamic-fields configuration for a BUID | `x-wis-token: <token>` |
| PUT | `/wisSeatBooking/<BUID>/consulConfiguration/dynamicFields` | Replace the `DynamicData` array with an updated dynamic-fields configuration | `x-wis-token: <token>` |

> ⚠️ The source host for this API is `wis-seat-beta.moveinsync.com` — a **beta** endpoint. Confirm the correct production host before using with live clients. The source includes a BUID UUID in the URL path that must be substituted with the actual client BUID.

_Source: [[sources/se-runbook-tags-desk-parking]]_

## Related Runbooks

- [[runbooks/parking-tag-and-vehicle-setup]] — Vehicle sub-type setup (SEDAN/SUV/etc.), BUID mapping, parking-tag creation via `mis-floor-plan`, QR code generation (level/slot)
- [[runbooks/parking-dynamic-policy]] — Dynamic parking policy end-to-end: tag creation, employee/slot bulk-upload, `BLOCK_HOTSEAT` policy, SOPs for new employees and slots
- [[runbooks/tag-and-dynamic-fields-setup]] — GET/PUT tagging config + dynamic-fields (`consulConfiguration/dynamicFields`) + SeatTypeMapping structure (desk/general)

## Open Questions

- **Who owns this module?** `owner: unknown` — no team name found in any SE source doc. Confirm with the platform/BE team.
- **SeatTypeMapping apply mechanism:** The source provides only the row-level data structure (Office/Floor/Seat/Seat Type columns); it does NOT document how the mapping file is uploaded or applied. Likely via a Consul config write or a dedicated API — confirm with owning team.
- **Production host for wisSeatBooking:** Source shows `wis-seat-beta.moveinsync.com`. Confirm the production endpoint (`.com` and `.in` variants) and whether the path structure (`/<BUID>/consulConfiguration/...`) is correct on production.
- **Doc 4 (visitor dynamic fields) cross-cutting scope:** The SE source batch includes a dynamic-fields JSON config (`raw/se-runbook/crawl/files/1pyPfofkI9yUedQs5b2EbtC9Xfk5MqL7ahQW_AxXntao.docx`) with top-level visitor-type keys (`businessGuests`, `contractor`, `deliveryPersonnel`, `personalGuest`) and `hideOnWalkin`/`enableStandardWalkinVisitorForm` flags. This is definitively **visitor-management** scoped (zero desk/parking terms), not part of this engine. It was landed in the SE runbook batch alongside tags docs but should be ingested separately into `wiki/modules/visitor-management.md`. Flagged for controller.
- **`room-tag` entity `used_by` completeness:** The entity page currently lists `used_by: [meeting-rooms, tags-desk-parking]` — should include `desk-management` and `parking-management` as both consume tags via this module. Flagged for the graph-consistency sweep.
- **Jira tickets:** No Jira search was run for this topic. A search on `mis-floor-plan tags` or `wisSeatBooking dynamicFields` or `consulConfiguration/dynamicFields` may surface relevant operational tickets.

## Last Updated

2026-06-29 — source: [[sources/se-runbook-tags-desk-parking]]
