---
type: entity
owned_by: tags-desk-parking
used_by: [meeting-rooms, tags-desk-parking]
last_updated: 2026-04-27
source: "[[sources/dynamic-policy-meeting-rooms]]"
---

# RoomTag / EmployeeTag

## Description
Tags are labels attached to meeting rooms (RoomTags) and employee profiles (EmployeeTags)
to implement Dynamic Policy — access control based on attribute matching rather than fixed groups.
The tag engine is owned by the `tags-desk-parking` module and **reused** by meeting rooms
(explicitly stated in the Dynamic Policy spec: *"Tags already created for desk/parking resources
can be reused in meeting rooms"*).

## Fields
| Field | Type | Description | Required |
|-------|------|-------------|----------|
| tag_type | string | Name of the tag (e.g. `isExecutive`, `allowed Room Booking`) | Yes |
| values | string[] | MECE set of possible values (e.g. `[Yes, No, Maybe]`) | Yes |
| target_type | enum | `ROOM`, `DESK`, `PARKING`, `EMPLOYEE` | Yes |
| target_id | UUID | ID of the room, desk, parking slot, or employee the tag is assigned to | Yes |
| start_date | date | Date from which tag is active (DD/MM/YYYY) | Yes |
| end_date | date | Date tag expires. Blank = 20 years from start_date. | No |
| value | string | Assigned value for this specific assignment | Yes |

## Used By
- [[modules/tags-desk-parking]] — creates, manages, and owns the tag engine
- [[modules/meeting-rooms]] — consumes tags via Dynamic Policy to restrict room access

## Relationships to Other Entities
- [[entities/room]] — RoomTags are applied to Rooms
- (future) Desk and Parking entities — EmployeeTags and resource tags also apply there

## Source of Truth
[[modules/tags-desk-parking]] is the canonical owner of the tag engine and RoomTag/EmployeeTag entity.
[[modules/meeting-rooms]] is a consumer.

_Source: [[sources/dynamic-policy-meeting-rooms]]_
