---
type: runbook
module: desk-management
team: SE
status: active
last_updated: 2026-06-29
source: "[[sources/se-runbook-desk-management]]"
raw_path: raw/se-runbook/crawl/files/1cYJIABt29kUBtZhNUXSVAPzgCkt4hMzezLonW_guyVQ.docx
---

# Runbook — Booking Approval Setup (Camunda)

## Purpose & Scope

Enable and configure the manager-approval workflow for desk/WFO/WFH bookings for a new BUID. When active, employees submit booking requests that their reporting manager must approve before the booking is confirmed. The approval logic is encoded in a Camunda DMN decision table (`bookingApproval-prod.dmn`) hosted on `wis-camunda-engine.workinsync.io`. This runbook covers adding the BUID to that decision table and setting the required PMS properties.

## Prerequisites

- BUID is live with desk booking configured (see [[runbooks/desk-booking-setup]]).
- Access to the Camunda cockpit at `https://wis-camunda-engine.workinsync.io/wisCamundaEngine/camunda/app/cockpit/`.
- PMS access to set properties on the `WIS-SEAT-BOOKING` service.
- Employee tags have been created and assigned (required for tag-based approval routing — Step 3).
- Reporting-manager (`RMID`) field is populated in employee profiles.

> ⚠️ The approval flow routes to the employee's **reporting manager as per the WIS employee profile** (`RMID`), regardless of team. Ensure `RMID` is populated correctly before enabling.

## Ordered Steps

### Step 1 — Download the current Camunda decision table

1. Navigate to: `https://wis-camunda-engine.workinsync.io/wisCamundaEngine/camunda/app/cockpit/default/#/decisions`
2. Go to **Deployments → Download `bookingApprovalConstraintProd`**.
3. Save the file as `bookingApproval-prod.dmn` locally.

### Step 2 — Add the BUID to the decision table

Open `bookingApproval-prod.dmn` in a DMN editor (Camunda Modeler or similar):

1. Locate the **"Business Unit"** column.
2. Add the new BUID to that column.
3. Also add the BUID to the **`BusinessUnitId`** column in the Booking Decision table.

> ⚠️ **CRITICAL: do NOT enter a space in the BUID field.** A trailing or leading space in the BU entry breaks the approval flow for **all clients** on the engine, not just the new one. Copy-paste the BUID exactly.

Fill in the decision criteria for this BUID:
- **Request Type:** which booking types trigger approval (WFO, WFH, or both).
- **Weekly Limit:** number of bookings of each type per week that proceed without approval. Booking #(limit+1) enters the approval flow.
- **Monthly Limit:** same logic per month.
- **Valid Tag:** employee tags that must be present for the flow to activate. If no tag is configured, approval is triggered automatically for every booking by this BUID.
- **Booking Valid:** True/False condition derived from the above rule combination.

### Step 3 — Upload the updated decision table

Use the following API call to deploy the updated DMN:

```
PUT https://wis-camunda-engine.workinsync.io/wisCamundaEngine/upload-file?userId=<userId>
Header: accept: */*
Header: Content-Type: multipart/form-data
Body (form-data): uploadFile = @"<local path to bookingApproval-prod.dmn>"
```

Replace `<userId>` with an authorised user email (contact the WIS backend team for the correct upload account).

Verify the deployment appeared in Camunda Cockpit → Deployments.

### Step 4 — Set WIS-SEAT-BOOKING properties for the BUID

Set the following properties on the `WIS-SEAT-BOOKING` service:

| Property | Type | Value | Notes |
|----------|------|-------|-------|
| `bookingRequestApprovalFlowEnabled` | Boolean | `true` | Master switch — must be true |
| `approvalFlowEnabled` | Boolean | `true` | Enables the approval UI in the employee app |
| `approvalFlowInWfoEnabled` | Boolean | `true` / `false` | Enable for WFO bookings |
| `approvalFlowInInWfhEnabled` | Boolean | `true` / `false` | Enable for WFH bookings |
| `autoRequestApprovalEnabled` | Boolean | `true` / `false` | Auto-approve if manager doesn't act before deadline |
| `expiryCutOffInMinutes` | String | e.g. `"50"` | Pending requests expire this many minutes before booking start |
| `expiryNotificationCutOffInMinutes` | String | e.g. `"40"` | Reminder notification sent this many minutes before expiry |
| `pendingRequestsNotificationEnabled` | Boolean | `true` | Notify manager of pending requests |
| `expiredRequestNotificationEnabled` | Boolean | `true` | Notify on expired requests |
| `bookingApprovalEmailsEnabled` | Boolean | `true` | Send email notifications for approvals |
| `wfhWeeklyLimit` | Integer (≥0) | confirm with client | WFH bookings per week before approval kicks in |
| `wfhMonthlyLimit` | Integer (≥0) | confirm with client | WFH bookings per month before approval kicks in |
| `autoExpireHour` | Integer | e.g. `1` | Hour at which pending requests auto-expire |
| `cancelSchedulesEnabled` | Boolean | `false` | Whether commute cancellation is allowed |
| `tagsEnabled` | JSON array | e.g. `["WFO","WFH"]` | Booking types subject to tag-based rules |

> ⚠️ The `wfhWeeklyLimit` and `wfhMonthlyLimit` values set on `emp-exp` **override** the values configured in the Camunda decision table. Set them consistently or omit them from emp-exp if Camunda should govern.

### Step 5 — Create employee tag assignment (via TO ticket)

Employee tags are required for per-employee approval routing. Raise a TO ticket assigned to the emp-exp team (POCs as of source document: Karthik Sharma, Aniket Dixit, Harsh Raj, Kuljeet Singh, Monit Dangi — verify current contacts):

- Specify the BUID.
- List the employee IDs or segments that need the approval tag.
- Reference past examples: `TO-11354`, `TO-11436`.

### Step 6 — Validate

- [ ] Employee creates a WFO or WFH booking — status shows "PENDING" rather than "CONFIRMED".
- [ ] Reporting manager receives a notification for the pending request.
- [ ] Manager navigates to Approvals (hamburger menu) and sees the pending bookings list.
- [ ] Manager approves with a reason — employee's booking status changes to "CONFIRMED"; employee is notified.
- [ ] Manager rejects — employee is notified with the rejection reason.
- [ ] Create a booking that falls under the weekly/monthly limit — it should be CONFIRMED immediately without approval.
- [ ] Create a booking #(limit+1) in the week — it should enter the approval flow.
- [ ] Pending request that expires before manager action: confirm auto-approve or auto-reject behaviour matches client expectation.
- [ ] Verify no extra space was added to the BUID in the DMN — confirm other clients are unaffected (check one other BUID booking flow).

## Notes & Gotchas

- **Reporting-manager routing:** approval goes to the employee's `RMID` as stored in the WIS employee profile, not the team manager. If `RMID` is missing or wrong, approvals may route incorrectly or fail silently.
- **No tag = auto-approval:** if an employee has no approval tag and the BUID is in the decision table, the `bookingApprovalConstraintEnabled` check from `emp-exp` applies. If the tag check yields no match, the system auto-approves. Confirm this is the desired behaviour before go-live.
- **`bookingApprovalConstraintEnabled`** is a property on `emp-exp` (not `WIS-SEAT-BOOKING`). It is part of the decision table evaluation logic.
- **Previously (2021):** The approval workflow existed before Camunda as a simpler "Booking Authorization" flow (referenced in the Sep 2021 release notes pptx). That earlier implementation had the same high-level UX (employee submits reason, manager approves/rejects, auto-approve/reject deadline) but was not DMN-based. The Camunda DMN implementation is the current approach.

## Related Jira

—

## Linked Raw Evidence

- `raw/se-runbook/crawl/files/1cYJIABt29kUBtZhNUXSVAPzgCkt4hMzezLonW_guyVQ.docx` — Booking Approval (Powered by Camunda)
- `raw/se-runbook/crawl/files/1mEe0EWKYr7ZXr99-k4ZFYKS_HjNrpo9z.pptx` — Perpetual digi pass / Release Notes Sep 2021 (historical context for approval workflow)
