---
type: source
ingested: 2026-06-29
doc_type: misc
---

# Source — SE Runbook: Tags, Desk-Parking Dynamic Fields & SeatTypeMapping

## Source Documents

| # | Title | raw_path | Format |
|---|-------|----------|--------|
| 1 | Parking Tag Creation | `raw/se-runbook/crawl/files/1mMSOXCgRID30nmg5jTm9ZoL6jQSLuR7OisW-YCeU_I8.docx` | docx |
| 2 | Tagging & DynamicFields config — get and update | `raw/se-runbook/crawl/files/1iRcMK_MLGkablzqN7siw5HvnmlFhZcoI5BgBnN78tU0.docx` | docx |
| 3 | SeatTypeMapping | `raw/se-runbook/crawl/files/1PClIGPq7kwnhOAb1ovyq0yjKnJZ9u9Jeklz7LmiOLgw.xlsx` | xlsx |
| 4 | DynamicFields JSON config (businessGuests label …) | `raw/se-runbook/crawl/files/1pyPfofkI9yUedQs5b2EbtC9Xfk5MqL7ahQW_AxXntao.docx` | docx |

## Date

Not explicitly dated in any source document. Ingest date: 2026-06-29.

## Type

misc — SE (Service Engineering) operational runbook snippets and reference configs

## Key Takeaways

- **Tag creation is via `mis-floor-plan`** — Tags are created with `entityType`, `tagName`, `tagType` via `POST .../mis-floor-plan/api/<BUID>/tags`; the API returns `buTagId` GUIDs which must then be mapped to `tagValue` strings via a separate `POST .../tags/polygons` call. This is the same API used for parking, desk, and meeting-room tags — the engine is shared across all booking surfaces.
- **Dynamic-fields config lives in Consul, accessed via `wisSeatBooking`** — The `consulConfiguration/dynamicFields` endpoint GET/PUT manages the `DynamicData` array. Each field carries `fieldType`, `configName`, `backedFieldType`, `validators`, `itemsList`, and optional `subFields` for conditional nested inputs. Source shows a "Mode of Transport" + "License No." example for a desk-booking context.
- **PUT is a full replacement** — The dynamicFields PUT replaces the entire `DynamicData` array; it is not a patch. The GET response must be fetched and preserved before any update.
- **SeatTypeMapping is a tabular seat-classification config** — Columns: `Office Name | Floor Name | Seat Name | Seat Type`. Known seat types in the SE source: `Workstation`, `Partner Cabin`, `Director Cubicle/ Cabin`. The upload/apply mechanism is not documented in the source material.
- **Doc 4 is visitor-management scoped, not desk/parking** — The `businessGuests` JSON config (doc 4) defines visitor-type dynamic fields (`businessGuests`, `contractor`, `deliveryPersonnel`, `personalGuest`) with `hideOnWalkin` and `enableStandardWalkinVisitorForm` flags. Zero desk/parking terms appear. This doc was bundled with the tags SE batch but belongs to visitor-management and should be ingested separately.
- **Parking tag creation (doc 1) is already covered** — The parking tag creation curl flow in doc 1 (`POST .../tags`, `POST .../tags/polygons`, `GET .../tags?entityType=PARKING`) is documented in full in [[runbooks/parking-dynamic-policy]] (Step 2). This source entry notes the overlap but does not duplicate the runbook.
- **Source host is beta** — Doc 2's GET/PUT curls reference `wis-seat-beta.moveinsync.com`. The production host for `.com` and `.in` environments is not stated; must be confirmed before SE use on live clients.

## Entities Mentioned

- [[entities/room-tag]] — the tag/value entity defined and managed by this module

## Modules Mentioned

- [[modules/tags-desk-parking]] — primary module documented; stub filled to active
- [[modules/parking-management]] — tag engine reuse for dynamic parking policy (doc 1 overlap)
- [[modules/desk-management]] — Consul dynamicFields config endpoint (`wisSeatBooking`) applies to desk booking surface (doc 2)
- [[modules/visitor-management]] — doc 4 (`businessGuests` JSON) is visitor-management scoped; flagged for separate ingest

## Decisions Extracted

None — these are operational how-to docs, not design/architecture decision records.

## Config Properties Documented

| Property / Config | Service | Default | Notes |
|-------------------|---------|---------|-------|
| `DynamicData` (array key in Consul config) | `wisSeatBooking` (`desk-management`) | (not stated) | Holds the full dynamic-fields schema for a BUID; managed via `consulConfiguration/dynamicFields` GET/PUT |
| `transport` (`configName` in DynamicData) | `wisSeatBooking` | (not stated) | "Mode of Transport" single-select field with `itemsList` options |
| `licenseNo` (`configName` in DynamicData, subField) | `wisSeatBooking` | (not stated) | License plate number; conditional sub-field, shown only when `transport = Personal Car` |

> ⚠️ These are `consulConfiguration` Consul-backed JSON fields, **not** PMS config xlsx properties. Do not look them up in the PMS config SQLite knowledge base.

## Secrets Redacted

The source documents contained HS512 JWT tokens in `x-wis-token` headers. These were pre-redacted to `<HS512 JWT — redacted>` before ingestion. Post-write scan verified: no raw JWT strings (the HS512 prefix pattern), no real Bearer tokens, no real MoveInSync email addresses, no Basic auth credential strings, and no OAuth client secret assignments appear in any wiki page produced from this source.

Additionally, the source URL for doc 2 contained a BUID UUID (`c9aa661f-0267-4cf2-a9f5-b88011619a84`) — treated as an example placeholder (not a real client BUID); replaced with `<BUID>` in all runbook pages.

## Wiki Pages Created/Updated

- **Created:** [[modules/tags-desk-parking]] — filled stub → active; all §2a sections complete
- **Created:** [[runbooks/tag-and-dynamic-fields-setup]] — GET/PUT dynamicFields config + SeatTypeMapping structure
- **Created:** [[sources/se-runbook-tags-desk-parking]] — this page
