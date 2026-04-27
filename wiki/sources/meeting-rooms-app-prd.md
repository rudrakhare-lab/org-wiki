---
type: source
raw_path: raw/modules/meeting-rooms/Meeting Rooms App PRD.docx
ingested: 2026-04-27
doc_type: PRD
---

# Meeting Rooms App PRD

## Source Title
Meeting Rooms App PRD

## Date
11/04/2022 (v1.0 approved 23-Apr-2022; v1.1 approved 31-May-2022)

## Type
PRD

## Key Takeaways
- Defines the mobile app experience for meeting room discovery, booking, and check-in within the WorkInSync app.
- Two booking flows: **Book Now** (start meeting immediately, user auto-checked-in) and **Book Later** (calendar slot picker).
- Rooms are shown with availability calendar component (3.5-hour rolling window); unavailable/disabled rooms are greyed out.
- **QR code check-in** — user scans room QR via app camera; GPS can optionally be enforced (config-gated). If no check-in within `MEETING_ROOM_RELEASE_IF_NO_CHECKIN` minutes, room is auto-released and organizer notified.
- Default meeting title: `<FirstName>'s meeting` — other attendees see "Busy".
- Filter/sort: by office (single-select), floor (multi), capacity (multi), amenities (multi). Infinite scroll, 10 rooms per load.
- Home screen shows count of meetings for the day against office booking card.
- Two config flags gate the feature: `showMeetingRoomOnApp`, `showQRScannerMeetingCheckIn`.

## Entities Mentioned
- [[entities/room]]
- [[entities/booking]]

## Modules Mentioned
- [[modules/meeting-rooms]] (primary subject)
- [[modules/mobile-app]] (surface this feature lives in)

## Decisions Extracted
- [[decisions/2026-04-27-meeting-room-auto-release]]

## Wiki Pages Created/Updated
- Updated: [[modules/meeting-rooms]]
- Updated: [[entities/room]]
- Updated: [[entities/booking]]

_Source: [[sources/meeting-rooms-app-prd]]_
