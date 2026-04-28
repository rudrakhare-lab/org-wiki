---
type: module
status: active
owner: unknown
depends_on: [tags-desk-parking, floor-kiosk, mobile-app, ms-teams-integration]
used_by: [meal-management]
last_updated: 2026-04-27
source: "[[sources/meeting-rooms-app-prd]], [[sources/kiosk-meeting-rooms-prd]], [[sources/meeting-rooms-catering-prd]], [[sources/dynamic-policy-meeting-rooms]], [[sources/meeting-rooms-room-maintenance]], [[sources/outlook-integration-permissions]], [[sources/outlook-addin-setup]], [[sources/meeting-rooms-resources]]"
---

# Meeting Rooms Module

## Overview
Meeting Rooms is WorkInSync's room booking and management module. It allows employees to
discover, book, check-in, and manage meeting room usage across web, mobile app, kiosk, and
Outlook/Google calendar. It is one of the most feature-rich modules in the product with several
sub-systems: catering, dynamic access policy (tags), kiosk view, room maintenance, and
Outlook/Google calendar integration.

## Purpose & Scope
Owns the full lifecycle of meeting room reservations — from discovery and booking to check-in,
auto-release, catering requests, and maintenance scheduling. Also owns the room resource catalog
(name, capacity, amenities, images, calendar mapping).

Does **not** own: the tag engine (owned by `tags-desk-parking`), the kiosk hardware/MDM layer
(shared with `floor-kiosk`), the mobile app container (owned by `mobile-app`), or the
Outlook/Google sync connector (related to `ms-teams-integration`).

## Key Features
- **Web booking**: search, filter (office/floor/capacity/amenity), sort, book, edit, cancel meeting rooms
- **Mobile App booking**: Book Now (instant, auto-check-in) and Book Later (calendar slot picker) via the WorkInSync mobile app
- **Kiosk view**: native tablet app per room — real-time status display, ad-hoc booking, check-in, extend/end meeting, find alternate room
- **Outlook/Google integration**: bidirectional calendar sync; bookings created in Outlook reflect in WIS and vice versa
- **Outlook Add-in**: WIS booking UI embedded in Outlook (web + desktop); deployed via manifest URL
- **Catering**: food/beverage ordering during booking; multi-delivery slots; cafeteria → category → item hierarchy; cut-off policies; catering dashboard
- **Dynamic Policy (tags)**: tag-based access control for native rooms; employee tags matched against room tags; reuses tag engine from `tags-desk-parking`
- **Room Maintenance**: admins schedule maintenance periods (create/delete); optional booking block; user notification banners across all channels
- **Auto-release**: rooms released if no check-in within configurable window (`MEETING_ROOM_RELEASE_IF_NO_CHECKIN`); organizer notified
- **QR check-in**: employees scan room QR code via mobile app or kiosk to check in

## Data Entities Used
- [[entities/room]] — owns this entity
- [[entities/booking]] — owns this entity
- [[entities/catering-order]] — owns this entity
- [[entities/cafeteria]] — owns this entity (⚠️ shared with `meal-management` — ownership TBD)
- [[entities/maintenance-period]] — owns this entity
- [[entities/room-tag]] — consumes from `tags-desk-parking`

## Dependencies on Other Modules
- [[modules/tags-desk-parking]] — borrows the tag engine for Dynamic Policy; employee and resource tags are created and owned there, reused here for room access control
- [[modules/floor-kiosk]] — shares kiosk infrastructure (MDM, device pairing, QR codes, tablet app framework) for the Meeting Rooms Kiosk experience
- [[modules/mobile-app]] — Meeting Rooms booking is a feature surface inside the WIS mobile app
- [[modules/ms-teams-integration]] — Outlook/Google Calendar integration for bidirectional booking sync; uses MS Graph API permissions managed in that module's context

## Used By
- [[modules/meal-management]] — shares the `Cafeteria` entity (catering configurations)

## API Endpoints
| Method | Path | Description | Auth Required |
|--------|------|-------------|---------------|
| GET | /meeting-rooms | List available rooms (filter: office, floor, capacity, amenity) | Yes |
| POST | /meeting-rooms/book | Create a room booking | Yes |
| PUT | /meeting-rooms/bookings/:id | Edit a booking | Yes |
| DELETE | /meeting-rooms/bookings/:id | Cancel a booking | Yes |
| POST | /meeting-rooms/bookings/:id/checkin | Check-in to a meeting room (QR/GPS) | Yes |
| POST | /meeting-rooms/bookings/:id/release | Manually release a room | Yes |
| POST | /meeting-rooms/catering | Create catering order for a booking | Yes |
| GET | /meeting-rooms/catering/dashboard | View catering orders (admin) | Yes (admin) |
| POST | /meeting-rooms/maintenance | Create maintenance period (admin) | Yes (admin) |
| DELETE | /meeting-rooms/maintenance/:id | Delete maintenance period (admin) | Yes (admin) |

_Note: Exact paths not confirmed from docs — above is inferred. Update when API spec is ingested._

## Key Configurations (BUID-level unless noted)
| Config Key | Type | Default | Description |
|---|---|---|---|
| `MEETING_ROOM_ENABLED` | boolean | false | Master switch to enable Meeting Rooms |
| `MEETING_ROOM_RELEASE_IF_NO_CHECKIN` | integer (min) | 180 (deployment default); **15 min recommended setting** | Minutes before auto-releasing unchecked room |
| `RELEASE_MEETING_ROOM` | boolean | false | Whether auto-release is active |
| `SHOW_UPCOMING_BOOKINGS_TIME` | integer (min) | 6 | Minutes before start to show check-in prompt on kiosk |
| `MEETING_EMAIL_OTP_TO_AUTHENTICATE` | boolean | true | Whether PIN email is sent for kiosk cancel/end |
| `ENABLE_MEETING_CATERING` | boolean | — | Master switch for catering sub-feature |
| `roomMaintenanceWorkflow` | boolean | — | Enables room maintenance section |
| `showMeetingRoomOnApp` | boolean | — | Shows meeting rooms on mobile app |
| `showQRScannerMeetingCheckIn` | boolean | — | QR scan check-in vs. direct check-in on app |
| `CONSENT_TYPE` | string | `ADMIN` | Who grants Outlook consent |

## Open Questions
- Who is the **owner team** for Meeting Rooms? (Jovil Nazareth, Kavya S, Manvi Chandra mentioned as authors but team name not stated)
- `Cafeteria` entity is shared with `meal-management` — which module owns it? ⚠️
- `MEETING_ROOM_RELEASE_IF_NO_CHECKIN` default is 180 min in deployment resources but 15 min in the App PRD — which is the actual default? ⚠️
- Is the Outlook/Google integration connector managed inside `ms-teams-integration` or is it a separate service (`outlook` service)?

## Last Updated
2026-04-27 — _Source: [[sources/meeting-rooms-app-prd]], [[sources/kiosk-meeting-rooms-prd]], [[sources/meeting-rooms-catering-prd]], [[sources/dynamic-policy-meeting-rooms]], [[sources/meeting-rooms-room-maintenance]], [[sources/outlook-integration-permissions]], [[sources/outlook-addin-setup]], [[sources/meeting-rooms-resources]]_
