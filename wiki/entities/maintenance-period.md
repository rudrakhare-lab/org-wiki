---
type: entity
owned_by: meeting-rooms
used_by: [meeting-rooms, floor-kiosk, mobile-app]
last_updated: 2026-04-27
source: "[[sources/meeting-rooms-room-maintenance]]"
---

# MaintenancePeriod

## Description
A scheduled maintenance window for a meeting room. Admins create MaintenancePeriods to communicate
room downtime to users and optionally block bookings during that window.
Architecture is at the resource level — designed to extend to desks and parking in future.

## Fields
| Field | Type | Description | Required |
|-------|------|-------------|----------|
| id | UUID | Unique identifier | Yes |
| room_id | UUID | FK → [[entities/room]] | Yes |
| activity | string | Maintenance activity type (from `roomMaintenanceList` config) | Yes |
| start_datetime | timestamp | Maintenance start (stored UTC; displayed in office timezone) | Yes |
| end_datetime | timestamp | Maintenance end. Max span: 90 days. | Yes |
| booking_allowed | boolean | If false, bookings are blocked during this period | Yes |
| description | string | Optional free-text description (max ~120 chars) | No |
| created_by | UUID | Admin user who created the period (emp GUID) | Yes |
| created_at | timestamp | Creation timestamp (UTC) | Yes |
| deleted_by | UUID | Admin user who deleted (if deleted) | No |
| deleted_at | timestamp | Deletion timestamp (if deleted) | No |

## Used By
- [[modules/meeting-rooms]] — creates and manages maintenance periods; blocks bookings; sends email notifications
- [[modules/floor-kiosk]] — displays maintenance banner during active window
- [[modules/mobile-app]] — shows yellow maintenance banner in booking card

## Relationships to Other Entities
- [[entities/room]] — each MaintenancePeriod belongs to one Room
- [[entities/booking]] — when booking_allowed=false, existing Bookings during this period trigger organizer notifications

## Source of Truth
[[modules/meeting-rooms]] owns the MaintenancePeriod entity (stored in floor-plan service / PMS).

_Source: [[sources/meeting-rooms-room-maintenance]]_
