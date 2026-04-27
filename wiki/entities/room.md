---
type: entity
owned_by: meeting-rooms
used_by: [meeting-rooms, floor-kiosk, mobile-app, tags-desk-parking]
last_updated: 2026-04-27
source: "[[sources/meeting-rooms-app-prd]], [[sources/kiosk-meeting-rooms-prd]], [[sources/dynamic-policy-meeting-rooms]]"
---

# Room

## Description
A physical meeting room resource in the WorkInSync system. Rooms can be integrated with
Outlook/Google calendars (integrated rooms) or managed natively by WIS (native rooms).
Owned and mastered by the Meeting Rooms module.

## Fields
| Field | Type | Description | Required |
|-------|------|-------------|----------|
| id | UUID | Unique room identifier | Yes |
| name | string | Display name of the room | Yes |
| office_id | UUID | FK → Office (premise) | Yes |
| floor_id | UUID | FK → Floor | Yes |
| capacity | integer | Max occupancy | Yes |
| amenities | string[] | List of amenities (TV, VC, whiteboard, etc.) | No |
| images | string[] | URLs of room images (uploaded by admin) | No |
| is_enabled | boolean | Whether the room is active and bookable | Yes |
| calendar_type | enum | `NATIVE`, `OUTLOOK`, `GSUITE` | Yes |
| calendar_email | string | Room mailbox address (for integrated rooms) | No |
| qr_code | string | Unique QR code identifier for kiosk/app check-in | No |
| tags | RoomTag[] | Dynamic policy tags attached to this room | No |

## Used By
- [[modules/meeting-rooms]] — owns entity; manages bookings, policies, maintenance
- [[modules/floor-kiosk]] — displays room status and bookings on kiosk
- [[modules/mobile-app]] — shows rooms in app booking flow
- [[modules/tags-desk-parking]] — tag engine applies to rooms (reused from desks/parking)

## Relationships to Other Entities
- [[entities/booking]] — a Room has many Bookings
- [[entities/room-tag]] — a Room can have many RoomTags (dynamic policy)
- [[entities/maintenance-period]] — a Room can have scheduled MaintenancePeriods
- [[entities/cafeteria]] — a Room is mapped to one or more Cafeterias (for catering)

## Source of Truth
[[modules/meeting-rooms]] is the canonical owner of the Room entity.

_Source: [[sources/meeting-rooms-app-prd]], [[sources/kiosk-meeting-rooms-prd]], [[sources/dynamic-policy-meeting-rooms]]_
