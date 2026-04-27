---
type: source
raw_path: raw/modules/meeting-rooms/Copy of Dynamic Policy for Meeting Rooms.docx
ingested: 2026-04-27
doc_type: spec
---

# Dynamic Policy for Meeting Rooms

## Source Title
Dynamic Policy for Meeting Rooms

## Date
Unknown (no date on document)

## Type
spec

## Key Takeaways
- Extends the WorkInSync **tag engine** (originally built for desks and parking) to meeting rooms.
- **Tags** restrict room access: an employee can book a room only if their Employee-Tags match the Room-Tags.
- Tags have type, MECE values, and a start/end date. Default rule: matching tag value = access granted; no tag on room = open to all.
- **Bulk upload** via Excel (`Room Tagging` section) — columns: Office, Floor, Room Name, Tag Name, Start Date, End Date, Tag Value.
- Setting Tag Value to `Null` in bulk upload removes the tag association from a room.
- Admin use cases: create/update/delete tags, assign rooms to employees or teams/BL/SubBL.
- **Applies only to Native Rooms** — not Outlook or Google integrated rooms (WIS has no control over those bookings).
- Reuses tags already created for desk/parking — explicit cross-module dependency on `tags-desk-parking`.

## Entities Mentioned
- [[entities/room]]
- [[entities/room-tag]]

## Modules Mentioned
- [[modules/meeting-rooms]] (primary)
- [[modules/tags-desk-parking]] (shared tag engine — explicit reuse)

## Decisions Extracted
- None specific — tag reuse is an existing architectural pattern, not a new decision.

## Wiki Pages Created/Updated
- Updated: [[modules/meeting-rooms]]
- Updated: [[entities/room-tag]]
- Created: [[cross-module/meeting-rooms-tags-desk-parking]]

_Source: [[sources/dynamic-policy-meeting-rooms]]_
