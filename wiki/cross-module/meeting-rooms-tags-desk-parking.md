---
type: cross-module
modules: [meeting-rooms, tags-desk-parking]
last_updated: 2026-04-27
source: "[[sources/dynamic-policy-meeting-rooms]]"
---

# Meeting Rooms ↔ Tags & Desk/Parking — Dynamic Policy Engine

## Summary
The WorkInSync tag engine, owned by the `tags-desk-parking` module, is explicitly reused by
Meeting Rooms to implement Dynamic Policy — tag-based access control that restricts which
employees can book which rooms. This is the only known case where a resource module (Meeting Rooms)
imports an access-control primitive from another resource module (Tags/Desk/Parking).

## Modules Involved
- [[modules/meeting-rooms]] — consumer of the tag engine for room access control
- [[modules/tags-desk-parking]] — owner of the tag creation/management engine

## How They Connect
Meeting Rooms' Dynamic Policy reads employee tags (set on the employee profile) and room tags
(assigned to rooms via bulk upload or API) and evaluates a match rule:

```
if EmployeeTag.type == RoomTag.type AND EmployeeTag.value == RoomTag.value
  → allow booking
else
  → deny booking
```

No tag on room = open to all. Tag on employee but not room = open to all.

Tags themselves are **created and managed** by the `tags-desk-parking` module. Meeting Rooms
does not have its own tag admin UI — it reuses whatever tags are already defined there.

## Shared Data Flows

```
[tags-desk-parking module]
   Admin creates Tag Type + Values ("isExecutive": Yes/No)
   Admin assigns tags to employee profiles
             │
             ▼
[tags-desk-parking Tag Engine]  ←── shared entity: [[entities/room-tag]]
             │
             ▼
[meeting-rooms module]
   Admin bulk-uploads Room-Tags via Excel (Room Tagging section)
   At booking time: EmployeeTag vs RoomTag evaluated
   Access granted or denied
```

## Potential Conflicts
- **Applies to Native Rooms only** — Outlook/Google integrated rooms are not controlled by WIS tags. Employees can bypass Dynamic Policy by booking via Outlook directly.
- Tag names on rooms and employees must match exactly — any naming drift between what `tags-desk-parking` creates and what room admin uploads will silently deny bookings.
- No documented rollback/audit on tag assignment changes in Meeting Rooms context.

_Source: [[sources/dynamic-policy-meeting-rooms]]_
