---
title: "Meal Cutoff Reference"
type: answer
module: meal-management
last_updated: 2026-05-25
server: com
confidence: medium
sources:
  - "[[configs/meal-properties-qa-log.md]]"
  - "[[configs/meal-properties-qa-matrix.md]]"
  - "[[entities/meal-booking.md]]"
  - "[[cross-module/meal-desk-management.md]]"
  - "[[decisions/2026-04-28-standalone-meal-booking-constraint.md]]"
jira_refs:
  - SE-53863
  - SE-57733
  - SE-57577
  - TS-43120
  - TB-24134
---

# Meal Cutoff Reference

This page consolidates all known configuration properties, behaviours, known gaps, and
operational notes related to meal booking and cancellation cutoffs in WorkInSync.

---

## Quick-Reference Table

| Purpose | Property | Type | Service | Server | Reference Point |
|---|---|---|---|---|---|
| **Booking creation cutoff** | `mealCutoffInMinutes` | DOUBLE | Emp Exp Common Config | `.com` + `.in` | Minutes from **00:00 of booked date** (confirmed) |
| **Booking cancellation cutoff** | `mealCancelCutoffInMinutes` | INTEGER | Booking Rule Engine | `.com` only | Time-of-day based; exact mapping partially clarified |
| **Edit cutoff** | *(no PMS config property found)* | — | — | — | Separate internal value; not exposed via PMS |

---

## mealCutoffInMinutes — Creation Cutoff

### Definition
`mealCutoffInMinutes` defines the deadline by which employees must create a meal booking
for a given day. The cutoff is **midnight-based**: the value is the number of minutes
elapsed since 00:00 of the **booked date** (not the current date).

**Example:** `mealCutoffInMinutes = 480` → cutoff is 8:00 AM on the day of the booking.

### Key Facts

| Attribute | Value |
|---|---|
| Property name | `mealCutoffInMinutes` |
| Type | DOUBLE |
| Service | Emp Exp Common Config |
| Server | Both `.com` and `.in` |
| Reference point | **00:00 of booked date** (minutes from midnight) |
| Positive value | Absolute time-of-day (e.g. 720 = noon) |
| Zero (`0`) | Effectively no same-day booking allowed (cutoff = midnight of that day) |
| Negative values | Seen in production (e.g. `-1350`) but exact behaviour of negatives is **not confirmed** |

### Reference Point Confirmation
Confirmed via Jira ticket **TO-14035** ("mealCutoffInMinutes as 480 min i.e. 8 AM") and
multiple SE tickets (SE-53863, SE-57733, SE-46550, SE-36995, SE-41016) that all set the
property to create an absolute AM/PM cutoff.

- `480` → 8:00 AM
- `720` → 12:00 PM (noon)
- `1350` → 10:30 PM
- `0` → 12:00 AM (midnight — no same-day booking)

> ⚠️ **Negative value caveat:** SE-53863 set `mealCutoffInMinutes = -1350` in production.
> SE-57733 set it to 22.5 hours (1350 min). The semantics of negative values are
> **not documented** — do not use negative values without confirming with the owning team.

### Booking-for-tomorrow behaviour
The cutoff is evaluated against the **booked date**, not the current date. If a user books
a meal for tomorrow, the cutoff window resets from tomorrow's 00:00 — the user can book
any time today.

---

## mealCancelCutoffInMinutes — Cancellation Cutoff

### Definition
`mealCancelCutoffInMinutes` defines the deadline by which an employee may cancel an
existing meal booking. The property is conditional on `enableSeparateMealOption = true`:
if that parent property is `false`, the system falls back to `employeeCancelCutOff` instead.

### Key Facts

| Attribute | Value |
|---|---|
| Property name | `mealCancelCutoffInMinutes` |
| Type | INTEGER |
| Service | Booking Rule Engine |
| Server | `.com` only |
| Reference point | Time-of-day based (partially clarified) |
| Common values seen | `-1440` (–24 h), `0`, `-60` |
| Default | Not documented |

### Reference Point — Partial Clarification
**PB-64722** provided a concrete example: "Meal cancellation cut-off is 10:00 AM." A desk
transfer at 11:30 AM could not cancel the meal because the cutoff had already passed.
This is consistent with a midnight-based (absolute time-of-day) calculation — **same
convention as `mealCutoffInMinutes`**.

However, the precise mapping from integer value to absolute time-of-day is **not confirmed**
for this property. Specifically:
- Whether negative values represent "N minutes before midnight" or use some other convention
  is unconfirmed.
- See TS-43120 for a live bug: when `mealCancelCutoffInMinutes = 0`, the expected cutoff
  message is "12:00 AM of the booked date" — but due to a timezone bug, "11:00 PM" was
  displayed. Fix expected by end of May 2026.

### Parent Property Dependency
> ⚠️ **Critical:** `mealCancelCutoffInMinutes` is **only honoured** when
> `enableSeparateMealOption = true`.
>
> If `enableSeparateMealOption = false`, the system uses `employeeCancelCutOff` instead.
> This was confirmed via TS-43120 (comment by Praveen Agarwal, 2026-05-20).

### Common values and their meaning

| Value | Interpretation |
|---|---|
| `0` | Cancellation cutoff = 12:00 AM of the booked date (effectively no same-day cancellation) |
| `-1440` | Commonly used; likely means 24 h before midnight of the booked date (i.e. by midnight the prior day). **Not officially confirmed.** |
| `-60` | Likely 60 minutes before some reference point. Exact meaning unconfirmed. |

---

## Edit Cutoff

No dedicated PMS config property for meal **edit** cutoff was found in any config source.

Evidence from Jira (TS-27912, SE-30443) **confirms** that a separate meal edit cutoff
exists and is distinct from the cancel cutoff:
- TS-27912 recorded "Meal edit cutoff = 660 mins" as a separate state from cancel cutoff
- SE-30443 listed "Meal Edit cut off - 6hrs" and "Meal Cancel cutoff - 2 hrs" as separate items

**The property name is unknown.** It may be a service-internal or DB-level value not
exposed via PMS configuration. Do not attempt to configure via PMS until confirmed.

---

## Interaction Between Creation and Cancellation Cutoffs

When `mealCutoffInMinutes` (creation) fires **before** `mealCancelCutoffInMinutes`
(cancellation), there exists a window where:
- New meal bookings **cannot** be created (creation cutoff passed)
- Existing meal bookings **can still** be cancelled (cancellation cutoff not yet reached)

This is expected behaviour for most booking systems and is consistent with the documented
property designs. The exact ordering depends on the (partially undocumented) reference
point of `mealCancelCutoffInMinutes`.

---

## Known Gaps & Open Issues

| Gap | Status | Evidence |
|---|---|---|
| `mealCutoffInMinutes` reference point | ✅ **CONFIRMED** — midnight-based (minutes from 00:00) | TO-14035, SE-53863 |
| `mealCancelCutoffInMinutes` reference point | ⚠️ **PARTIALLY CLARIFIED** — appears time-of-day based | PB-64722, TS-43120 |
| `mealCancelCutoffInMinutes` negative value mapping | ❌ **UNKNOWN** | No source doc |
| `mealCancelCutoffInMinutes` default value | ❌ **UNKNOWN** | Not in config CSVs |
| Edit cutoff property name | ❌ **UNKNOWN** — value exists internally, PMS property not found | TS-27912, SE-30443 |
| `mealCancelCutoffInMinutes` description/type conflict | ❌ **UNRESOLVED** — description uses boolean language, type is INTEGER | configs/meal-properties-qa-log Q51 |
| Timezone handling in cancellation message | 🐛 **BUG OPEN** — TS-43120; fix expected ≤ 2026-05-30 | TS-43120 |

---

## Configuration Quick Guide

### Set a Noon Creation Cutoff
```
Service: Emp Exp Common Config
Property: mealCutoffInMinutes
Value: 720
```
Employees can create meal bookings up until 12:00 PM on the day of their booking.

### Set a Zero Cancellation Cutoff (No Same-Day Cancellation)
```
Service: Booking Rule Engine
Property: mealCancelCutoffInMinutes
Value: 0
Prerequisite: enableSeparateMealOption = true
```

### Enable Meal-Only Booking with Cancellation Control
All three properties must be set together:
```
mealPlanningEnabled = true          (Emp Exp Common Config — both servers)
enableSeparateMealOption = true     (Booking Rule Engine — .com only)
mealCancelCutoffInMinutes = <N>     (Booking Rule Engine — .com only)
```

> ⚠️ All three are required. Without `mealPlanningEnabled = true`, no meal booking
> flow is active. Without `enableSeparateMealOption = true`, `mealCancelCutoffInMinutes`
> is ignored.

---

## Server Scope Summary

| Property | `.com` | `.in` |
|---|---|---|
| `mealCutoffInMinutes` | ✅ | ✅ |
| `mealCancelCutoffInMinutes` | ✅ | ❌ (ignored) |
| `mealPlanningEnabled` | ✅ | ✅ |
| `enableSeparateMealOption` | ✅ | ❌ (ignored) |

---

## Related Properties (Not Cutoffs, but Affect Meal Booking Windows)

| Property | Type | Service | Description |
|---|---|---|---|
| `mealPlanningEnabled` | BOOLEAN | Emp Exp Common / BRE | Master switch — must be `true` for any meal cutoff to have effect |
| `enableSeparateMealOption` | BOOLEAN | Booking Rule Engine | Enables meal-only booking; required for `mealCancelCutoffInMinutes` to be honoured |
| `limitMealDuringBookingCreation` | BOOLEAN | Booking Rule Engine | Limits employee to one meal booking per day (both servers) |
| `mealPlanningMandatory` | BOOLEAN | — | Makes meal selection mandatory in office booking form |
| `hideBookingTimeMealOnly` | BOOLEAN | — | Hides login/logout fields in meal-only form; confirmed default = `false` (PB-65051) |

---

## Related Wiki Pages

- [[configs/meal-properties-qa-log.md]] — Full Q&A session with all 60 questions and Jira-confirmed updates
- [[configs/meal-properties-qa-matrix.md]] — QA test matrix with 167 test cases
- [[entities/meal-booking.md]] — MealBooking entity definition
- [[cross-module/meal-desk-management.md]] — Meal as add-on to WFO desk booking
- [[decisions/2026-04-28-standalone-meal-booking-constraint.md]] — One-meal-per-day constraint decision

---

## Key Jira References

| Ticket | Summary | Relevance |
|---|---|---|
| SE-53863 | Update mealCutoffInMinutes - SVB | Live cutoff change; confirms property is in Emp Exp Common Config |
| SE-57733 | Update mealCutoffInMinutes to 22.5h - ANKO | Confirms DOUBLE type allows fractional hour values |
| SE-57577 | Set meal cancellation cutoff to 0 - Support Ninja | Confirms `mealCancelCutoffInMinutes=0` is a valid production value |
| TS-43120 | Cancellation message showing incorrect cutoff - Support Ninja | Bug: timezone handling; confirms `mealCancelCutoffInMinutes` depends on `enableSeparateMealOption` |
| TB-24134 | Cutoffs for booking creation/cancellation need to be independent | Architectural context for cutoff decoupling |

_Last updated: 2026-05-25_
_Sourced from Q3 answer session + Jira research (36,741 tickets searched)._
