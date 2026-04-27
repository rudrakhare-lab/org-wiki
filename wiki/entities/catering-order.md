---
type: entity
owned_by: meeting-rooms
used_by: [meeting-rooms]
last_updated: 2026-04-27
source: "[[sources/meeting-rooms-catering-prd]]"
---

# CateringOrder

## Description
Represents a single food/beverage order associated with a meeting room booking.
A Booking can have multiple CateringOrders — one per cafeteria × delivery slot combination.
The Meeting ID is stable; Order IDs are minted fresh when orders are created or re-created after cancellation.

## Fields
| Field | Type | Description | Required |
|-------|------|-------------|----------|
| order_id | UUID | Unique ID for this specific order. Reminted on cancel+recreate. | Yes |
| meeting_id | UUID | FK → [[entities/booking]].meeting_id. Stable across order edits. | Yes |
| room_id | UUID | FK → [[entities/room]] — the room this catering is for | Yes |
| cafeteria_id | UUID | FK → [[entities/cafeteria]] | Yes |
| delivery_time | timestamp | Requested delivery time (within meeting window) | Yes |
| items | CateringItem[] | Ordered items with quantity | Yes |
| status | enum | `Requested`, `Accepted`, `Rejected`, `Delivered`, `Canceled`, `Canceled - Short Notice` | Yes |
| cost_center | string | Optional cost center attribution | No |
| special_instructions | string | Delivery notes / dynamic field responses | No |
| created_at | timestamp | Order creation time (UTC) | Yes |

## Used By
- [[modules/meeting-rooms]] — creates, manages, and tracks catering orders; powers the catering dashboard

## Relationships to Other Entities
- [[entities/booking]] — CateringOrder belongs to a Booking (via meeting_id)
- [[entities/cafeteria]] — CateringOrder is fulfilled by a Cafeteria
- [[entities/room]] — CateringOrder is scoped to a Room

## Source of Truth
[[modules/meeting-rooms]] owns the CateringOrder entity (catering dashboard service).

_Source: [[sources/meeting-rooms-catering-prd]]_
