---
type: source
raw_path: raw/modules/delegation/Delegation PRD.docx
ingested: 2026-04-28
doc_type: PRD
---

# Delegation PRD

## Source Title
Delegation PRD (v1.2)

## Date
v1.0: 10/12/2022; v1.2: 31/01/2023

## Type
PRD

## Key Takeaways
- Delegation allows an employee (Delegator) to grant resource booking rights to another employee (Delegatee) — enabling executive assistants or team managers to book on behalf of others.
- Feature is config-gated: `isDelegationEnabled` (default: false).
- **Delegatee cap**: one employee can be a delegatee for a max of 10 people. No limit on how many delegatees a delegator can add.
- **Scope of delegatable resources** (v1): Admin Dashboard, Employee Web, Work Planner, Premises, Meeting Rooms, Desk Management, Reports, Visitor Management, Vaccination Review, Broadcast Message, Mobile App. Only resources enabled for that BUID are available.
- **Profile switcher**: Delegatee sees a "Switch Profile" button in the sidenav; can act as the delegator across allowed modules. Delegator's personal profile is read-only to delegatee.
- **Session behaviour**: On re-login, delegatee always loads their own profile (not delegator's) — stateless delegation.
- **Audit**: "Updated By" column in audit logs and reports reflects the delegatee's name, not the delegator's.
- **Email notifications**: Delegatee notified on assignment (`blockDelegationEmail = false` to send). Delegator gets emails when delegatee acts (`emailSentOnDelegateeActions = true`).
- **Meeting Rooms + Calendar**: On the backend, meeting organized by delegatee correctly reflects "creator ≠ organizer". Delegatee excluded from meeting attendee list or email.
- Lives in `emp-exp` service (`Project Management Service > delegation` config).
- Note: `emp-exp-delegation.txt` in employee-experience folder is a duplicate copy of the same doc.

## Entities Mentioned
- None formal — Delegation is a cross-cutting permission layer, not an entity.

## Modules Mentioned
- [[modules/delegation]] (primary)
- [[modules/employee-experience]] (host service: emp-exp)
- [[modules/meeting-rooms]] (delegatable resource)
- [[modules/visitor-management]] (delegatable resource)
- [[modules/desk-management]] (delegatable resource)

## Decisions Extracted
- [[decisions/2026-04-28-delegation-stateless-session]]

## Wiki Pages Created/Updated
- Created: [[modules/delegation]]
- Updated: [[modules/employee-experience]]

_Source: [[sources/delegation-prd]]_
