---
type: cross-module
modules: [meeting-rooms, mobile-app]
last_updated: 2026-04-27
source: "[[sources/meeting-rooms-app-prd]], [[sources/meeting-rooms-room-maintenance]]"
---

# Meeting Rooms ↔ Mobile App — Booking Surface

## Summary
Meeting Rooms is surfaced in the WorkInSync mobile app as a booking surface. The Mobile App
module provides the container, navigation, and device capabilities (camera/GPS); Meeting Rooms
provides the data, booking logic, and business rules. The two are decoupled — Meeting Rooms
is a feature gate inside the Mobile App.

## Modules Involved
- [[modules/meeting-rooms]] — data and logic owner (room catalog, booking engine, auto-release)
- [[modules/mobile-app]] — container and device capability owner (camera for QR scan, GPS, push notifications)

## How They Connect
The Meeting Rooms section of the mobile app is controlled by the feature flag `showMeetingRoomOnApp`.
When enabled, the app renders:
1. A meeting room card on the Home screen (count of today's meetings)
2. A dedicated Meeting Rooms section (discover, filter, book)
3. QR scanner for check-in (controlled by `showQRScannerMeetingCheckIn` flag)

The Mobile App provides:
- **Camera** — for QR code scanning at room check-in
- **GPS** — optionally enforced at check-in to verify user is physically at the room
- **Push notifications** — for booking confirmations, auto-release alerts, maintenance banners

## Shared Data Flows

```
[meeting-rooms backend]
   Room catalog (name, capacity, amenities, availability)
   Config flags: showMeetingRoomOnApp, showQRScannerMeetingCheckIn
             │
             ▼
[mobile-app container]
   Renders Meeting Rooms section if flag = true
   Renders QR scanner if flag = true
   Provides camera + optional GPS for check-in
             │
             ▼
[booking events written to meeting-rooms backend]
   Book Now → booking created + user auto-checked-in
   Book Later → calendar slot picker → booking created
   QR scan → check-in event
   GPS validation (if enabled) → check-in allowed/denied
```

## Maintenance Banners
When a [[entities/maintenance-period]] is active, the mobile app displays a yellow banner on
the room's booking card. This banner is data-driven from the maintenance period record — the
Mobile App only renders it; Meeting Rooms owns the state.

## Potential Conflicts
- **GPS enforcement** — if enabled at BUID level but GPS is unavailable (indoors), check-in fails silently or shows confusing error. No documented fallback.
- **Auto-release timer (`MEETING_ROOM_RELEASE_IF_NO_CHECKIN`)** — when Mobile App's push notification is delayed, users may miss the check-in reminder and have their room released before they see it.

_Source: [[sources/meeting-rooms-app-prd]], [[sources/meeting-rooms-room-maintenance]]_
