---
type: runbook
module: desk-management
team: SE
status: active
last_updated: 2026-06-29
source: "[[sources/se-runbook-desk-management]]"
raw_path: raw/se-runbook/crawl/files/1Z4BOVZYcN41r9zlK5X2wH2mG3ZUAbu9NCO-xaYZ7SNs.xlsx
---

# Runbook — Desk Booking Setup (Space Management)

## Purpose & Scope

End-to-end setup of desk booking for a new client or a new office/floor. Covers the full SE workflow from discovery questions through office/shift configuration, floor-plan upload, desk allocation, bulk upload, and configuration values. Use this runbook alongside [[runbooks/floor-plan-upload]] (floor premise creation and floor-plan file upload, which must happen first).

## Prerequisites

- Client BUID is live on the target server (`.com` or `.in`).
- Office premises have been created (see [[runbooks/ets-office-premise-setup]]).
- Floor premises and floor plans are uploaded (see [[runbooks/floor-plan-upload]]). Seats/desks must be visible in the WIS admin Desk Management screen before proceeding with allocation.
- Employee data is synced (profiles exist in the system — see [[modules/employee-provisioning]]).
- SE has completed the discovery questionnaire (see Step 1 below).
- PMS access to set configs on the `WIS-SEAT-BOOKING` service (and `BOOKING-RULE-ENGINE` if advanced rules are needed).

## Ordered Steps

### Step 1 — Discovery: gather client requirements

Before any configuration, confirm the following with the client:

**Org structure & allocation:**
- What is the structure of the organisation? (Teams, Business Lines, Cost Centres, Departments, LOBs?)
- Do some employees have dedicated (fixed) desks? How many?
- Are desks allocated to teams/BUs, or is every desk a hot-desk?
- Do employees with dedicated desks still make WFO bookings?

**Booking rules:**
- Do employees need to book a desk when coming to office?
- Can employees book desks with specific amenities (dual monitors, height-adjustable, etc.)?
- Are there restrictions on which employees can book which desks (e.g. only VP+ can book cabins)?
- Is there a no-show / auto-cancellation requirement? If yes: after how many hours post-login-time?
- Should there be a booking edit cutoff? A cancellation cutoff?

**Shifts & offices:**
Collect the following per office (use the xlsx discovery template):

| Sr. # | Office Name | Geo Code | Address |
|-------|-------------|----------|---------|
| 1.0 | (fill) | | |

Collect shift timings per office:

| Shift | Office A | Office B | … |
|-------|----------|----------|---|
| (fill) | | | |

**Employee data columns** (for bulk upload later):
Confirm headers: `EmployeeId`, `Email`, `EmployeeName`, `ProjectTeam`, `Business line`, `Organization`, `Gender`, `PhoneNumber`, `OfficeName`, `RMID` — and any additional custom columns.

### Step 2 — Configure offices and shifts in WIS

Using the WIS admin dashboard:
1. Verify each office premise exists with correct geocode and address.
2. Configure shifts per office (login time, logout time, working days).
3. Set `Booking on Weekly offs` — confirm whether users should be blocked from booking on weekoffs.

### Step 3 — Upload or sync employee data

1. Use the employee bulk-upload Excel template with the confirmed headers (Step 1).
2. Columns: `EmployeeId | Email | EmployeeName | ProjectTeam | Business line | Organization | Gender | PhoneNumber | OfficeName | RMID`.
3. Map `OfficeName` values exactly to the office names configured in Step 2.
4. For LOB/Sub-LOB hierarchies (seat assignment by non-team parameters): configure User Groups, Resource Groups, and User Group Permissions under **Settings** before running the upload.

### Step 4 — Upload floor plan and confirm seat inventory

Follow [[runbooks/floor-plan-upload]] to upload the floor plan file and create the floor premise. After upload, verify:
- Seats are visible in **Admin → Desk Management** under the correct floor.
- Seat names (e.g. `WS-123`) match the client's naming scheme.

### Step 5 — Desk allocation

Allocate desks to teams/employees/BUs from the admin Desk Management screen. Three allocation levels:

| Level | When to use |
|-------|------------|
| Office | Allocate a block of seats to a BU across the office |
| Floor | Allocate specific floor sections to a team |
| Team | Assign specific named desks to team members |

Actions available per desk: **Allocate to Team**, **Allocate to Employee**, **Make Hot-Desk**, **Block**, **Unallocate**.

For dedicated (fixed) seats: allocate to the specific employee. If the client uses the Perpetual Digi Pass feature (auto-check-in on scan for dedicated-seat employees), raise a TO ticket to enable the property — the current enablement process is unclear as of 2021 documentation; confirm with the WIS desk-booking team before promising this to a client.

### Step 6 — Desk Bulk Upload (optional, for large inventories)

Use the bulk-upload Excel template for large-scale allocation. Column format:

| Office Name | Floor Name | Seat Name | Start Date (DD-MM-YYYY) | End Date (DD-MM-YYYY) | Action | Team Name / Employee Id / bl / subbl | Amenities |
|-------------|------------|-----------|--------------------------|------------------------|--------|--------------------------------------|-----------|
| Office A | Floor 10 | WS-123 | 23-04-2024 | 2025-12-05 00:00:00 | Employee | emp1234 | Dual Monitor, Height adjustable desk, Printer |
| Office B | Floor 11 | WS-120 | 23-04-2024 | 2025-12-05 00:00:00 | Team | HR | Dual Monitor, Height adjustable desk, Testing kit |

**Action values:** `Team`, `Employee`, `Hotseat`, `Unallocate`, `Block`, `bl` (Business Line), `subbl` (Sub-Business Line).

Upload via **Admin → Desk Management → Desk Bulk Upload → Desk Assignment**.

### Step 7 — Set desk and employee tags (optional)

If the client uses tag-based booking restrictions (e.g. restrict Cabin desks to VP+):
1. Create desk tags in WIS and assign to the relevant desks.
2. Create employee tags and assign to the relevant employee segments.
3. Configure tag-based rules in `BOOKING-RULE-ENGINE` — see [[configs/booking-rule-engine]].

See [[modules/tags-desk-parking]] for tag management detail.

### Step 8 — Set WIS-SEAT-BOOKING configuration properties

Set the following on the `WIS-SEAT-BOOKING` service for the BUID. Confirm with the client before enabling:

| Property | Effect | Default |
|----------|--------|---------|
| `bookingRequestApprovalFlowEnabled` | Master switch for Camunda approval flow | (not stated) |
| `approvalFlowInWfoEnabled` | Enable approval for WFO bookings | (not stated) |
| `approvalFlowInInWfhEnabled` | Enable approval for WFH bookings | (not stated) |
| `autoRequestApprovalEnabled` | Auto-approve requests if manager doesn't act | (not stated) |
| `expiryCutOffInMinutes` | Minutes before booking start when pending requests expire | (not stated — example: `50`) |
| `expiryNotificationCutOffInMinutes` | Minutes before expiry to send reminder notification | (not stated — example: `40`) |
| `wfhWeeklyLimit` | Max WFH bookings per week before approval is required | (integer, ≥0) |
| `wfhMonthlyLimit` | Max WFH bookings per month before approval is required | (integer, ≥0) |
| `amenitiesBulkUpload` | Enable bulk upload flow for amenities | (not stated) |

Full config reference: [[configs/wis-seat-booking]].

> ⚠️ For the booking approval workflow, also see [[runbooks/booking-approval-camunda]] — the BUID must be added to the Camunda decision table in addition to setting the properties above.

### Step 9 — Validate

- [ ] Admin → Desk Management screen shows seats on the correct floor with correct names.
- [ ] Allocation is visible: team/employee/hot-desk designations appear as configured.
- [ ] Employee can log in and see available desks for their assigned office.
- [ ] Employee can create a WFO booking and the booking appears in their Upcoming Bookings.
- [ ] (If approval enabled) Employee booking triggers a manager notification and appears in the manager's Approvals queue.
- [ ] Bulk-uploaded amenities are shown on the correct desks.
- [ ] Reports → Seat Booking report returns data for the test booking date.

## Screenshots

Source screenshots are in the raw evidence files. See **Linked Raw Evidence** below for file paths.

## Notes & Gotchas

- **Shift times are per-office.** If a client has multiple offices in different time zones, shifts must be configured separately per office.
- **LOB/Sub-LOB hierarchy** is created automatically from employee data if the hierarchy fields are present in the upload. It can also be created manually under Settings → User Groups, Resource Groups, User Group Permissions.
- **Booking Autocancellation:** if enabled, desks are released after `x` hours following login time — confirm the value with the client and set accordingly.
- **Meal booking mandate** and **meal booking cutoff** are configured separately on the `MEAL-MANAGEMENT` service but are surfaced in the WIS Configurations xlsx alongside desk configs — do not set them here.
- **ORG and BL mapping:** if the client has hierarchy levels beyond team (Cost Centre, LoB, etc.), confirm the mapping before the employee data upload. Hierarchy must be in the employee profile data before allocation can reference it.
- **Do not enter a space in the BUID field** in the Camunda decision table — it breaks the approval flow for all clients on the engine.

## Related Jira

—

## Linked Raw Evidence

- `raw/se-runbook/crawl/files/1Z4BOVZYcN41r9zlK5X2wH2mG3ZUAbu9NCO-xaYZ7SNs.xlsx` — WIS Configurations for Desk Booking (discovery template + config fields across Basic, Office, Shifts, Employee data, Floor plan, Desk Allocation tabs)
- `raw/se-runbook/crawl/files/1pTkjoLBq-lXXb_DSdeUH1IZiWDMv9_yTdySr_2NhQCw.docx` — MODULE 2: Desk Booking Solution / Space Management (canonical product overview)
