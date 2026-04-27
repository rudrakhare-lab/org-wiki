---
type: source
raw_path: raw/modules/meeting-rooms/Copy of Kiosk - Meeting Rooms PRD.docx
ingested: 2026-04-27
doc_type: PRD
---

# Kiosk — Meeting Rooms PRD

## Source Title
Kiosk — Meeting Rooms PRD (v1.1)

## Date
Version 1.1 (review comments incorporated)

## Type
PRD

## Key Takeaways
- Native tablet app (Android/iOS/FireOS) mounted outside each meeting room; scoped to current-day bookings only.
- Mapped to a specific room using a **tenant-specific pairing code** (alphanumeric) + admin email — no per-user login.
- Room status shown in real-time: green = available, orange = upcoming, red = booked/in-use. Colour-blind-accessible texture sidebar.
- **6 core use cases**: view status, ad-hoc booking (Book Now), book for later (current day only), upcoming check-in with countdown, extend meeting, find alternate room.
- Extend blocked if another meeting follows; system suggests alternate room by matching floor, amenities, capacity.
- PIN or QR code required to cancel or end a meeting. PIN emailed to organizer from `no-reply@workinsync.io`.
- Config key `MEETING_EMAIL_OTP_TO_AUTHENTICATE` controls whether PIN email is triggered (default: true).
- Auto-release after `MEETING_ROOM_RELEASE_IF_NO_CHECKIN` minutes; room removed from room calendar but meeting stays in organizer's calendar.
- MDM requirement: push updates, restrict to single app, API integration for policy/device management, support Apple/Android supervised mode.

## Entities Mentioned
- [[entities/room]]
- [[entities/booking]]

## Modules Mentioned
- [[modules/meeting-rooms]] (primary)
- [[modules/floor-kiosk]] (shared kiosk infrastructure)

## Decisions Extracted
- [[decisions/2026-04-27-meeting-room-auto-release]]
- [[decisions/2026-04-27-kiosk-pin-auth-over-login]]

## Wiki Pages Created/Updated
- Updated: [[modules/meeting-rooms]]
- Created: [[cross-module/meeting-rooms-floor-kiosk]]

_Source: [[sources/kiosk-meeting-rooms-prd]]_
