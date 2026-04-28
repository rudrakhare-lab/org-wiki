---
type: decision
module: meeting-rooms
date: 2026-04-27
status: active
---

# Decision: Auto-release rooms on no-show rather than blocking them indefinitely

## Context
When an employee books a meeting room but doesn't show up, the room sits empty and blocked for
other potential users. The system needs a policy for reclaiming the resource.

## Decision
If no check-in is recorded within `MEETING_ROOM_RELEASE_IF_NO_CHECKIN` minutes of the meeting
start time, the room is **automatically released** and made available for new bookings.
The organizer receives an email notification that the room was released.
The meeting itself **is not cancelled** in the organizer's calendar — only the room association
is removed.

## Config
`MEETING_ROOM_RELEASE_IF_NO_CHECKIN` (integer, minutes)
- Deployment default (config baseline): **180 minutes**
- Recommended / suggested setting: **15 minutes** (confirmed by team)

`RELEASE_MEETING_ROOM` (boolean): Must be `true` to activate auto-release.

## Alternatives Considered
- Block room for full duration (rejected — too wasteful, especially for long bookings)
- Prompt organizer via push notification to extend or release (not documented, not implemented)
- Cancel the meeting entirely (rejected — organizer's calendar event is preserved by design)

## Trade-offs
- Organizer loses room mid-meeting if they are simply late. Mitigation: generous default window.
- Release does not cancel the calendar event — attendees may show up expecting a room that no longer has a WIS booking. Communication gap.

## Source
[[sources/meeting-rooms-app-prd]], [[sources/kiosk-meeting-rooms-prd]]
