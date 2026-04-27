---
type: entity
owned_by: meeting-rooms
used_by: [meeting-rooms, floor-kiosk, mobile-app, ms-teams-integration]
last_updated: 2026-04-27
source: "[[sources/meeting-rooms-app-prd]], [[sources/meeting-rooms-catering-prd]], [[sources/kiosk-meeting-rooms-prd]]"
---

# Booking (Meeting)

## Description
Represents a meeting room reservation. A Booking ties a Room to a time slot and an organizer.
Bookings can originate from: WIS Web, Mobile App, Kiosk, or Outlook/Google Add-in.
Syncs bidirectionally with the organizer's and room's calendar (Outlook/Google for integrated rooms).

## Fields
| Field | Type | Description | Required |
|-------|------|-------------|----------|
| meeting_id | UUID | Unique identifier for this booking (stable across edits) | Yes |
| room_id | UUID | FK → [[entities/room]] | Yes |
| organizer_id | UUID | FK → User (employee) | Yes |
| title | string | Meeting title. Default: `<FirstName>'s meeting` | Yes |
| start_time | timestamp | Meeting start (UTC) | Yes |
| end_time | timestamp | Meeting end (UTC) | Yes |
| attendees | string[] | List of attendee emails | No |
| description | string | Optional meeting description | No |
| special_request | string | Optional special request text | No |
| source | enum | `WIS_WEB`, `MOBILE`, `KIOSK`, `OUTLOOK`, `GSUITE` | Yes |
| check_in_status | enum | `NOT_CHECKED_IN`, `CHECKED_IN`, `NO_SHOW` | Yes |
| checked_in_by | UUID | User ID of whoever checked in (if checked in) | No |
| is_released | boolean | Whether room was auto-released due to no check-in | No |
| catering_order_ids | UUID[] | FK → [[entities/catering-order]] (one per cafeteria × delivery slot) | No |

## Used By
- [[modules/meeting-rooms]] — creates, manages, cancels bookings
- [[modules/floor-kiosk]] — displays today's bookings on kiosk
- [[modules/mobile-app]] — shows meetings in user's calendar view; supports check-in
- [[modules/ms-teams-integration]] — bidirectional sync with Outlook/Google calendar

## Relationships to Other Entities
- [[entities/room]] — each Booking belongs to one Room
- [[entities/catering-order]] — a Booking can have multiple CateringOrders (same Meeting ID, different Order IDs)

## Source of Truth
[[modules/meeting-rooms]] owns the Booking entity (booking-v2 service).

_Source: [[sources/meeting-rooms-app-prd]], [[sources/meeting-rooms-catering-prd]], [[sources/kiosk-meeting-rooms-prd]]_
