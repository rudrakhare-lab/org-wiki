---
type: entity
owned_by: visitor-management
used_by: [visitor-management, parking-management, guard-app-kiosks]
last_updated: 2026-04-28
source: "[[sources/vms-prd]], [[sources/vms-implementation]]"
---

# VisitorInvite

## Description
The core booking record in Visitor Management. A VisitorInvite is created by an Employee/Host
and associates an event with one or more Visitors. It tracks the full lifecycle from scheduling
through check-in and check-out, including manager approval state, parking allocation, and badge printing.

## Fields
| Field | Type | Description | Required |
|-------|------|-------------|----------|
| id | UUID | Unique invite identifier | Yes |
| event_title | string | Title of the visit event. Default: "Meeting with <Employee Name>" | Yes |
| host_id | UUID | FK → Employee who created the invite | Yes |
| office_id | UUID | FK → Office where visit occurs | Yes |
| visit_date | date | Scheduled visit date | Yes |
| start_time | time | Visit start time | Yes |
| end_time | time | Visit end time | Yes |
| visit_type | enum | Type of visit (Business Guest, Personal, Contract Employee, Delivery, etc.) | Yes |
| guests | VisitorGuest[] | List of visitors invited (name, email, phone) | Yes |
| approval_status | enum | `PENDING_APPROVAL`, `APPROVED`, `REJECTED`, `NOT_REQUIRED` | Yes |
| invite_type | enum | `SCHEDULED`, `WALK_IN` | Yes |
| parking_bookings | ParkingBooking[] | FK → visitor parking slots auto-allocated via VMS | No |
| note_to_guests | string | Free-text personal note shown in invite email | No |
| note_to_admin | string | Free-text note visible only to admin (triggers email to admin list) | No |
| is_recurring | boolean | Whether this is a recurring invite | No |
| recurrence_pattern | object | Pattern details (Daily/Weekly/Monthly/Custom + end date) | No |

## Visitor Status Values (per guest)
| Status | Description |
|--------|-------------|
| Invited | Invite sent, awaiting visitor response |
| Accepted | Visitor accepted invite |
| Rejected | Visitor rejected invite |
| Digipass Generated | Visitor completed profile; digipass emailed |
| Profile Completed | Profile complete (when digipass disabled) |
| Security Complete | Security guard scanned digipass (gate 1) |
| Delayed Check-in | Visitor took > N min to reach front desk after gate 1 |
| Checked-In | Front desk confirmed entry |
| Temp Check-Out | Visitor temporarily stepped out |
| Checked-Out | Final check-out |
| Overstay | Visitor stayed beyond end time |
| Canceled | Invite canceled by host |

## Used By
- [[modules/visitor-management]] — owns full lifecycle
- [[modules/parking-management]] — visitor parking booking linked to invite
- [[modules/guard-app-kiosks]] — security guard scans digipass via guard app

## Relationships to Other Entities
- [[entities/visitor-profile]] — each guest in the invite has a VisitorProfile
- [[entities/parking-booking]] — VisitorInvite can have visitor parking bookings

## Source of Truth
[[modules/visitor-management]] owns the VisitorInvite entity.

_Source: [[sources/vms-prd]], [[sources/vms-implementation]]_
