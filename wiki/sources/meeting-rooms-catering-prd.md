---
type: source
raw_path: raw/modules/meeting-rooms/Copy of Meeting Rooms Catering PRD.docx
ingested: 2026-04-27
doc_type: PRD
---

# Meeting Rooms Catering PRD

## Source Title
Meeting Rooms Catering PRD (multi-version: v1.0 → v2.3)

## Date
Initial: unknown; v2.3 updated 12-Mar-2024

## Type
PRD

## Key Takeaways
- Catering is a sub-feature of Meeting Rooms: employees request food/beverages when booking a room; facility managers track and deliver orders.
- **Cafeteria hierarchy**: Office → Cafeteria → Menu (category) → Menu Items (with veg/non-veg/vegan, price, prep time, availability time range, cut-off).
- **Order ID + Meeting ID system**: each meeting has 1 Meeting ID; multiple Order IDs are generated per cafeteria × delivery slot combination. Order IDs survive meeting edits unless room or date changes.
- **Delivery time flow (new)**: changing delivery time no longer clears selected items — system checks availability of each item at the new time and marks unavailable ones; items remain in cart if still available.
- **Cancellation policy**: cut-off varies by headcount (0–10 pax: 24h; 10–20: 48h; 20–50: 72h; >50: 7 days). Orders cancelled short-notice get status `Canceled - Short Notice`.
- **Catering UI management** (v2.3): admins manage cafeterias, categories and items directly on the Configurations page (RBAC-gated). Previously SE-team only via API.
- Applicable to: WIS Web (integrated + native), Outlook Add-in. Not on Mobile or Kiosk.
- Config flag: `ENABLE_MEETING_CATERING` (boolean). Cut-off: 60-min default per office.

## Entities Mentioned
- [[entities/catering-order]]
- [[entities/cafeteria]]
- [[entities/booking]]
- [[entities/room]]

## Modules Mentioned
- [[modules/meeting-rooms]] (primary)

## Decisions Extracted
- [[decisions/2026-04-27-catering-order-id-model]]

## Wiki Pages Created/Updated
- Updated: [[modules/meeting-rooms]]
- Created: [[entities/catering-order]]
- Created: [[entities/cafeteria]]

_Source: [[sources/meeting-rooms-catering-prd]]_
