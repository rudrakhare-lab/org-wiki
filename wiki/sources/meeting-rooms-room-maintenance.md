---
type: source
raw_path: raw/modules/meeting-rooms/Copy of Meeting Rooms - Room Maintenance Workflow.docx
ingested: 2026-04-27
doc_type: spec
---

# Meeting Rooms — Room Maintenance Workflow

## Source Title
Meeting Rooms — Room Maintenance Workflow

## Date
Unknown (references Richemont and PwC India as first adopters; features reference 2026 dates in email templates)

## Type
spec

## Key Takeaways
- Admins can schedule maintenance periods on rooms (create/delete only — no edit). Max 90 days per period; no overlapping periods per room.
- **Two modes**: booking restriction enabled (blocks new bookings + notifies affected organizers) vs. disabled (shows banner only — room still bookable).
- **Maintenance activity list** is configurable per BUID (`roomMaintenanceList`); default values: Cleaning, Renovation, Missing Amenities, Amenities Not Working, Under Maintenance.
- 3 email templates: admin (created), user (booking affected — only if restriction enabled), admin (deleted). Recipient list configurable via `roomMaintenceEmalList`.
- **Room maintenance blocking** shows as **yellow** in the room calendar (distinct from booking colours).
- Applies across all channels: web, mobile, kiosk, floor kiosk, Outlook add-in.
- Feature is privilege-gated (`room_maintenance_meeting_rooms`) and BUID-level config-gated (`roomMaintenanceWorkflow` boolean).
- Audit log captures who created/deleted maintenance periods (emp GUID, timestamp UTC, room ID/name, before/after state).

## Entities Mentioned
- [[entities/room]]
- [[entities/maintenance-period]]
- [[entities/booking]]

## Modules Mentioned
- [[modules/meeting-rooms]] (primary)
- [[modules/floor-kiosk]] (channel — maintenance banner shown on floor kiosk)
- [[modules/mobile-app]] (channel — yellow maintenance banner on mobile)

## Decisions Extracted
- None new — follows existing audit/notification patterns.

## Wiki Pages Created/Updated
- Updated: [[modules/meeting-rooms]]
- Created: [[entities/maintenance-period]]

_Source: [[sources/meeting-rooms-room-maintenance]]_
