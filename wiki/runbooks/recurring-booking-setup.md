---
type: runbook
module: desk-management
team: SE
status: active
last_updated: 2026-06-29
source: "[[sources/se-runbook-desk-management]]"
raw_path: raw/se-runbook/crawl/files/1u5OPZ5bOqVUR7g6L7jrh31WmSxWh31Vs9hlpceJGH8g.docx
---

# Runbook — Recurring Booking Setup (WorkPlanner)

## Purpose & Scope

Enable recurring desk/WFO bookings for a BUID via the WorkPlanner feature. When enabled, an employee (or their SPOC) can create a repeating booking across a date range in a single action rather than booking day-by-day. This runbook covers the four Booking Rule Engine and Employee Experience properties that control the feature and its notification behaviour.

## Prerequisites

- BUID is live with desk booking configured (see [[runbooks/desk-booking-setup]]).
- PMS access to set properties on the `BOOKING-RULE-ENGINE` service and the `EMP-EXP-COMMON-CONFIG` service.
- Confirmed with the client: maximum recurrence window (days) they want to allow between first booking and "Repeat till" date.

## Ordered Steps

### Step 1 — Enable recurring booking on the BUID

Set the master switch on the `BOOKING-RULE-ENGINE` service:

| Property | Service | Type | Value to set |
|----------|---------|------|--------------|
| `enableRecurrenceOnTeamPlanner` | BOOKING-RULE-ENGINE | Boolean | `true` |

> ⚠️ Setting this to `true` activates the "Create Recurring Booking" option in WorkPlanner for all employees under this BUID.

### Step 2 — Configure the notification matrix (optional)

Control which personas receive notifications on recurring-booking create, update, and cancel events.

Set `workplannerNotificationControl` on `BOOKING-RULE-ENGINE` (Type: JSON):

```json
{
  "CREATE": ["CREATOR", "EMPLOYEE"],
  "UPDATE": ["CREATOR", "EMPLOYEE"],
  "CANCEL": ["CREATOR", "EMPLOYEE"]
}
```

**Value meanings:**

| Value | Who gets notified |
|-------|-------------------|
| `CREATOR` | The SPOC or manager who created the recurring booking on behalf of the employee |
| `EMPLOYEE` | The employee for whom the booking was created |

If only one persona is listed (e.g. `["EMPLOYEE"]`), only that persona is notified. Omitting a key entirely suppresses all notifications for that action.

> ⚠️ Confirm with the client whether SPOCs (WorkPlanner creators) should receive notifications — some clients prefer notifications to go only to employees.

### Step 3 — Set the maximum recurrence window

Set the upper limit on how far in advance a recurring series can be scheduled:

| Property | Service | Type | Meaning |
|----------|---------|------|---------|
| `workplannerRecurrenceMaxDays` | EMP-EXP-COMMON-CONFIG | Integer | Maximum number of days between the first booking date and the "Repeat till" date |

No default is stated in the source. Confirm the value with the client (common choices: 30, 60, or 90 days).

> ⚠️ This property belongs to `EMP-EXP-COMMON-CONFIG`, **not** `BOOKING-RULE-ENGINE`. Set it on the correct service.

### Step 4 — Enable auto-desk allocation (optional)

If the client wants desks to be automatically assigned when a recurring booking is created (rather than employee-selected):

| Property | Service | Type | Value to set |
|----------|---------|------|--------------|
| `autoAllocate` | BOOKING-RULE-ENGINE | Boolean | `true` |

Only set this if the client has a defined desk allocation policy (teams/floors mapped to employees). Auto-allocation picks from the employee's allocated desk pool.

### Step 5 — Validate

- [ ] Employee logs in to WorkPlanner and sees the "Recurring Booking" option.
- [ ] Employee creates a recurring WFO booking — individual booking records appear for each date in the series.
- [ ] Notifications are received by the correct persona(s) on creation.
- [ ] Attempt to set a "Repeat till" date beyond `workplannerRecurrenceMaxDays` — the UI should reject or cap it.
- [ ] (If `autoAllocate` = true) Confirm desks are automatically assigned from the employee's allocation pool.

## Notes & Gotchas

- **`enableRecurrenceOnTeamPlanner` is a BUID-level property** on the `BOOKING-RULE-ENGINE` service, not `WIS-SEAT-BOOKING`. Ensure you are setting it on the correct service.
- **`workplannerRecurrenceMaxDays` is on `EMP-EXP-COMMON-CONFIG`** — it is easy to set it on the wrong service. Double-check before saving.
- **Notification matrix is optional.** If `workplannerNotificationControl` is not set, the default notification behaviour applies (defaults not documented in source — raise a TO ticket or check with the emp-exp team if the client has specific requirements).
- **Recurring bookings and approval flow:** if the BUID also has booking approval enabled (see [[runbooks/booking-approval-camunda]]), each recurring booking in the series will individually enter the approval queue unless exempted by the Camunda decision table. Confirm with the client whether recurring bookings should bypass approval.

## Related Jira

—

## Linked Raw Evidence

- `raw/se-runbook/crawl/files/1u5OPZ5bOqVUR7g6L7jrh31WmSxWh31Vs9hlpceJGH8g.docx` — Enablement of Recurring Booking in Workplanner
