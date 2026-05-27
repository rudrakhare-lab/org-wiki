---
type: module
status: active
owner: unknown
depends_on: [tags-desk-parking, floor-kiosk, mobile-app, ms-teams-integration]
used_by: [meal-management, access-management, delegation]
last_updated: 2024-03-12
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
(name, capacity, amenities, images, calendar mapping) and the `Cafeteria` entity (via catering).

Does **not** own: the tag engine (owned by `tags-desk-parking`), the kiosk hardware/MDM layer
(shared with `floor-kiosk`), the mobile app container (owned by `mobile-app`), or the
Outlook/Google calendar sync connector (runs via the `wis-integration`/`outlook` service — see Dependencies).

## Key Features
- **Web booking**: search, filter (office/floor/capacity/amenity), sort, book, edit, cancel meeting rooms
- **Mobile App booking**: Book Now (instant, auto-check-in) and Book Later (calendar slot picker) via the WorkInSync mobile app
- **Kiosk view**: native tablet app per room — real-time status display, ad-hoc booking, check-in, extend/end meeting, find alternate room
- **Outlook/Google integration**: bidirectional calendar sync; bookings created in Outlook reflect in WIS and vice versa
- **Outlook Add-in**: WIS booking UI embedded in Outlook (web + desktop); deployed via manifest URL
- **Catering**: food/beverage ordering during booking — see the **Catering** section below
- **Dynamic Policy (tags)**: tag-based access control for native rooms — see the **Dynamic Policy (Meeting Rooms)** section below
- **Room Maintenance**: admins schedule maintenance periods (create/delete); advance-scheduling limit (default 90 days); optional booking block; email notifications to a configured list on create/delete; configurable user-facing message; notification banners across all channels
- **Auto-release**: rooms released if no check-in within configurable window (`MEETING_ROOM_RELEASE_IF_NO_CHECKIN`); organizer notified. Meeting start/end reminder notifications (`MEETING_START_NOTIFICATION` / `MEETING_END_NOTIFICATION`)
- **QR check-in**: employees scan room QR code via mobile app or kiosk to check in

## Catering
Food/beverage ordering attached to a meeting-room booking. _Source: [[sources/meeting-rooms-catering-prd]] (v2.3, 2024-03-12) — full UI / email / report detail lives there._

- **Cafeteria → office → room model**: an office can have multiple cafeterias (each with multiple menus); a room inherits all of its office's cafeterias by default, and an admin can remove a cafeteria from a specific room (which removes that menu for the room)
- **Menu structure**: cafeteria → menu → category → item; categories are configurable, **collapsible** groups (names client-configurable)
- **Cost display**: configurable — price is hidden on the front end when set to zero/negative
- **Multi-room ordering**: catering can be requested across multiple rooms in a single request
- **Delivery slots**: each order specifies a delivery time; orders are created per cafeteria + delivery time
- **Cut-off policy**: catering cannot be modified past the cut-off time — editing/deleting such a meeting shows _"This meeting contains catering request, which cannot be modified"_
- **Cancellation policy**: catering orders follow a defined cancellation policy (per the Catering PRD)
- **Catering dashboard**: a configured set of users views/manages catering orders
- **Config-management UI**: Manage Premise → set up cafeterias for an office → manage catering (menus) → add items to categories. Master switch `ENABLE_MEETING_CATERING`

## Dynamic Policy (Meeting Rooms)
Tag-based access control restricting which employees can book which rooms. _Source: [[sources/dynamic-policy-meeting-rooms]]._

- **⚠️ Applies only to Native Rooms** (rooms created in WorkInSync). It does **not** apply to Outlook/Google calendar rooms — WIS does not control those calendar systems, so a tag policy placed on an Outlook/Google room has no effect
- **Tag matching rule**: Employee-Tags are matched against Room-Tags. Same tag name **and** same value → the employee may book; mismatched value → blocked; **no tag on the room → bookable by anyone**; tag on the employee but not the room → bookable
- **Tags**: MECE-valued (e.g. `isExecutive` = Yes/No), carry start/end dates, and **reuse the same tag engine as desks and parking** ([[modules/tags-desk-parking]]) — desk/parking tags can be reused for rooms with no restriction
- **Bulk upload** ("Room Tagging" section): columns Office/Floor/Room Name, Tag Name (header), Tag Start/End Date (end optional; blank = 20 years), Tag Value. Tag value blank = no action; `Null` = delete the tag association

## Data Entities Used
- [[entities/room]] — owns this entity
- [[entities/booking]] — owns this entity
- [[entities/catering-order]] — owns this entity
- [[entities/cafeteria]] — **owned by meeting-rooms** (full catering management UI per Catering PRD v2.3: Manage Premise → cafeterias → menus → items); **consumed by [[modules/meal-management]]** (meal-consumption location reference)
- [[entities/maintenance-period]] — owns this entity
- [[entities/room-tag]] — consumes from `tags-desk-parking`
- [[entities/employee]] — employee identity record (identity, entitlements, relationships)

## Dependencies on Other Modules
- [[modules/tags-desk-parking]] — borrows the tag engine for Dynamic Policy; employee and resource tags are created and owned there, reused here for room access control
- [[modules/floor-kiosk]] — shares kiosk infrastructure (MDM, device pairing, QR codes, tablet app framework) for the Meeting Rooms Kiosk experience
- [[modules/mobile-app]] — Meeting Rooms booking is a feature surface inside the WIS mobile app
- [[modules/ms-teams-integration]] — the wiki-tracked module for MS-side integration. _Note: the Outlook/Google **calendar sync** itself runs via the separate `wis-integration`/`outlook` service (consent-URL endpoints under `wis-integration.workinsync.io/outlook/...`), which is NOT a wiki-tracked module — distinct from `ms-teams-integration`._

## Used By
- [[modules/meal-management]] — shares the `Cafeteria` entity (meeting-rooms owns it; meal-management consumes it)

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
_The configs below are a curated set. Operational defaults and granular settings live in
[[sources/meeting-rooms-resources]] (deployment block) and [[sources/meeting-rooms-room-maintenance]] (room maintenance configs)._

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
| `MEETING_START_NOTIFICATION` | integer (min) | 5 | Minutes before meeting start to send a reminder notification |
| `MEETING_END_NOTIFICATION` | integer (min) | 10 | Minutes before meeting end to send a reminder notification |
| `CANCEL_EVENT_PIN_VERIFICATION_ENABLE` | boolean | false | Require PIN verification to cancel an event |
| `ENABLE_WITH_PRINCIPAL_NAME` | boolean | true | Outlook integration uses the principal name |
| `roomMaintenanceAdvanceScheduleAllowed` | integer (days) | 90 | Advance-scheduling limit enforced by the maintenance date picker |
| `roomMaintenanceList` | JSON | — | Stored maintenance list (held in the floor-plan service) |
| `roomMaintenanceMessage` | JSON | "Contact your administrator" | Configurable message shown to users for a room under maintenance |
| `roomMaintenceEmalList` † | list | [empty] | Email IDs that receive room-maintenance emails when schedules are created/deleted |

† `roomMaintenceEmalList` — the source spells "Emal" (likely a typo); preserved **verbatim** because the PMS uses this exact key.

## Open Questions
- Who is the **owner team** for Meeting Rooms? (Jovil Nazareth, Kavya S, Manvi Chandra mentioned as authors but team name not stated.)
- The Outlook/Google calendar sync runs via the `wis-integration`/`outlook` service (per the Resources doc consent-URL endpoints). Should this be modeled as a distinct `outlook` integration page, or kept under [[modules/ms-teams-integration]]?

## Last Updated
2024-03-12 — _Source: [[sources/meeting-rooms-app-prd]], [[sources/kiosk-meeting-rooms-prd]], [[sources/meeting-rooms-catering-prd]], [[sources/dynamic-policy-meeting-rooms]], [[sources/meeting-rooms-room-maintenance]], [[sources/outlook-integration-permissions]], [[sources/outlook-addin-setup]], [[sources/meeting-rooms-resources]]_
