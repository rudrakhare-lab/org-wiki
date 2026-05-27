---
type: module
status: active
owner: Aditya Dutta / Rishabh M
depends_on: [employee-experience, meeting-rooms, visitor-management, desk-management, mobile-app]
used_by: []
last_updated: 2023-01-31
source: "[[sources/delegation-prd]]"
---

# Delegation Module

## Overview
Delegation is a cross-cutting feature that allows an employee (Delegator) to grant their
resource booking privileges to another employee (Delegatee). Common use cases: CXOs delegating
to executive assistants, team managers delegating to colleagues when unavailable.
The Delegatee acts on behalf of the Delegator by switching their profile in the sidenav.

## Purpose & Scope
Provides a permissions layer on top of all resource-booking modules — does not own any resource
entities itself. Lives in the `emp-exp` (Employee Experience) service.

Does **not** own: any booking entities. It is a permission/routing layer that grants delegatees
access to modules they would not otherwise see.

## Key Features
- **Profile switcher**: Delegatee sees a "Switch Profile" panel in sidenav listing all delegators. On switch, sidenav shows only the modules the delegator granted them. The page displays the first granted module; the "Switch to MIS" button is hidden while in a delegated profile.
- **Delegatable modules** (v1): Admin Dashboard, Employee Web, Work Planner, Premises, Meeting Rooms, Desk Management, Reports, Visitor Management, Vaccination Review, Broadcast Message, Mobile App.
- **Per-module enablement via PMS**: which modules are delegatable is controlled under `Project Management Service > delegation` as a JSON map. Documented keys: `MEETING_ROOM_ENABLED`, `WORK_PLANNER_ENABLED`, `BOOKING_HISTORY`, `UPCOMING_VISITOR` (Visitor Management), `FRONT_DESK`, `EMPLOYEE_WEB_EXPERIENCE`, `MOBILE_APP`.
- **Delegatee cap**: one employee can hold delegation rights from at most 10 people.
- **No limit** on how many delegatees a delegator can assign.
- **Partial save**: if some delegatees reach the cap, save partially succeeds (e.g. "1 user(s) successfully added. 2 user(s) were not successful") with a clear error message.
- **Delegator profile read-only**: delegatee cannot edit delegator's personal profile.
- **Session stateless**: on re-login, delegatee always loads their own profile (not delegator's).
- **Audit trail**: "Updated By" in all audit logs and reports shows delegatee's name.
- **Meeting Rooms integration**: backend correctly records meeting as created by delegatee; delegatee excluded from attendee list/calendar invite.
- **Email notifications** (configurable):
  - `blockDelegationEmail`: suppress assignment notification to delegatee
  - `delegatorDelegateeEmailsEnabled`: controls email to delegatee on actions
  - `emailSentOnDelegateeActions`: copies delegator on delegatee's actions

## Dependencies on Other Modules
- [[modules/employee-experience]] — delegation lives in the `emp-exp` service
- [[modules/meeting-rooms]], [[modules/visitor-management]], [[modules/desk-management]] — modules whose booking actions can be delegated
- [[modules/mobile-app]] — delegation (profile switch + delegated modules) is also surfaced on the mobile app (`MOBILE_APP` in the PMS delegation enablement map)

## Key Configurations
| Config Key | Default | Description |
|---|---|---|
| `isDelegationEnabled` | false | Master switch — enables delegation feature in UI |
| `enableDelegationForAdmins` | true | Shows delegation in Employee page for admins (service: `emp-exp`) |
| `blockDelegationEmail` | false | Suppresses assignment notification email to delegatee |
| `delegatorDelegateeEmailsEnabled` | — | Controls emails to delegatee on delegatee actions |
| `emailSentOnDelegateeActions` | — | Copies delegator on all delegatee actions |

_Module-level delegatability is configured separately under `Project Management Service > delegation` (a JSON map of module keys — see Key Features)._

## Data Entities Used
- [[entities/employee]] — employee identity record (identity, entitlements, relationships)

## Open Questions
- v2 scope listed as "to be updated later" — has time-bounded delegation (a validity window for delegated rights) been built since Jan 2023?
- How is delegation handled when a delegatee already has 10 people's rights and an 11th tries to assign?

## Last Updated
2023-01-31 — _Source: [[sources/delegation-prd]]_ (PRD v1.2)
