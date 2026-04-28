---
type: decision
module: meal-management
date: 2026-04-28
status: active
---

# Decision: One meal booking per day — WFO-integrated and standalone are mutually exclusive

## Context
Meal Management has two booking paths: (1) meal added as part of a WFO/office booking, and
(2) the new standalone meal booking. An employee could potentially use both on the same day,
leading to double-counting of meal consumption and cafeteria inventory planning issues.

## Decision
Only **one active meal booking** is allowed per employee per day. The two types are mutually exclusive:
- If a WFO booking already includes a meal → standalone meal booking is blocked
- If a standalone meal booking exists → WFO booking cannot include meals (that option is disabled)

## Alternatives Considered
- Allow both (rejected — leads to double meal allocation and cafeteria inventory discrepancy)
- Allow override with admin confirmation (not documented; potentially a v2 option)

## Trade-offs
- An employee whose WFO booking includes a meal cannot separately book a meal via the RFID path (e.g. if they want to order a second meal or a different cafeteria). They would need to remove the meal from the WFO booking first.
- The mutual-exclusivity check must happen cross-booking type — requires Meal Management to query both WFO booking and standalone booking records for the same date.

## Source
[[sources/meal-checkin-prd]]
