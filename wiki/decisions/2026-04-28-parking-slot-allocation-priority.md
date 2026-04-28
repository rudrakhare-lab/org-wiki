---
type: decision
module: parking-management
date: 2026-04-28
status: active
---

# Decision: Slot allocation priority — Employee dedicated > Team > Hotslot, with graceful cascade

## Context
When multiple slot types are available (dedicated employee slot, team slot, hotslot), the system
needs a rule for which slot to assign first in auto-allocation mode.

## Decision
Auto-allocation priority is:
1. **Employee dedicated slot** — if the employee has a dedicated slot for the requested vehicle type, assign that first.
2. **Team slot** — if the employee is in a team with reserved slots and the team slot is available, assign from there.
3. **Hotslot** — fallback for all employees with no dedicated or team slot (or when higher-priority slots are all taken).
4. **No slot available** — show message "No parking slots available for ## wheeler".

**Cascade rule**: if a higher-priority slot is unavailable (e.g. team slots all taken), the system cascades to the next tier and informs the employee ("All the slots for your team are booked").

**Grid-based mode** mirrors this — slots not accessible to the employee are greyed out rather than hidden.

## Alternatives Considered
- First-come-first-serve across all slot types (rejected — defeats the purpose of reserved/dedicated slots)
- Block booking entirely if dedicated slot is unavailable (rejected — too restrictive; hotslot cascade is a usability improvement)

## Trade-offs
- If an employee with a 2-wheeler dedicated slot tries to book a 4-wheeler, the system falls back to hotslots for the 4-wheeler — their 2-wheeler slot is not reused. Multiple dedicated slots per employee (one per vehicle type) partially addresses this.
- Grid-based mode shows employees only slots accessible to them (greys out others) — some employees may not realize additional slots exist that are restricted to others.

## Source
[[sources/parking-prd]]
