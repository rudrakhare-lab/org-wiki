---
type: runbook
module: meeting-rooms
team: SE
status: active
last_updated: 2026-06-29
source: "[[sources/se-runbook-meeting-rooms]]"
raw_paths:
  - raw/se-runbook/crawl/files/1w63IH9n7w28kJCKljb5kUvJhJGtcdt-WDeD8hkUcB54.pptx
  - raw/se-runbook/crawl/files/1qcf6HjovQ5MwBKnWWiLsYtqZghp7GC_s-c7gGyLbK6I.docx
---

# Runbook — Meeting Room Catering Setup

## Purpose & Scope

SE steps to enable and configure the catering sub-feature within Meeting Rooms for a client. Covers:

1. Enabling the catering master switch (`ENABLE_MEETING_CATERING`)
2. Creating cafeteria(s) for an office
3. Configuring menus, categories, and items
4. Setting delivery slots and cut-off/booking-deadline policies
5. Configuring the catering dashboard access
6. Optional: customisable time-range per item, cost-center workflow

This runbook is the **operational setup layer**. For full feature behaviour (email flows, order
lifecycle, report exports, multi-room ordering UI), see the curated
[[modules/meeting-rooms]] Catering section and [[sources/meeting-rooms-catering-prd]] (PRD v2.3,
2024-03-12).

_Sources: [[sources/se-runbook-meeting-rooms]] (catering slides, pptx) + [[sources/meeting-rooms-catering-prd]]_

---

## Prerequisites

- Meeting Rooms enabled for the BUID (`MEETING_ROOM_ENABLED` = `true`) — see [[runbooks/meeting-room-setup]]
- At least one office premise with rooms created
- Admin access to WIS admin portal (**Manage Premise** section)
- Catering dashboard user accounts identified (email IDs to grant dashboard access)
- Menu/item list from the client (category names, item names, prices, delivery slots, cut-off times)

---

## Configuration Flow

```
Meeting Rooms enabled (meeting-room-setup)
        ↓
Enable ENABLE_MEETING_CATERING (BUID level)     ← STEP 1
        ↓
Create Cafeteria for the Office                 ← STEP 2
        ↓
Configure Menus → Categories → Items            ← STEPS 3–4
        ↓
Set Delivery Slots & Cut-off / Deadlines        ← STEP 5
        ↓
Grant Catering Dashboard Access                 ← STEP 6
        ↓
Optional: Cost-center, Time-range per item      ← STEP 7
        ↓
Validate end-to-end catering order              ← STEP 8
```

---

## Ordered Steps

### Step 1 — Enable Catering Master Switch

Set PMS property at BUID level:

| Property | Value |
|---|---|
| `ENABLE_MEETING_CATERING` | `true` |

The catering section now appears in the meeting booking form for rooms under this BUID.

---

### Step 2 — Create a Cafeteria

Navigate to **WIS Admin → Manage Premise → [Select Office] → Set Up Cafeterias**.

1. Click **Add Cafeteria**.
2. Enter cafeteria name and any descriptive details.
3. Save. The cafeteria is now associated with the office.

By default, **all rooms in that office inherit all of its cafeterias**. To remove a specific cafeteria
from a specific room, navigate to the room settings and de-select the cafeteria.

> ⚠️ A cafeteria must be mapped to an office (not a floor or room directly). Room-level cafeteria
> exclusions are possible but cafeteria creation always starts at the office level.

---

### Step 3 — Create Menus within the Cafeteria

Navigate to **Manage Premise → [Office] → Manage Catering → [Cafeteria]**.

1. Click **Add Menu**.
2. Enter menu name (e.g., "Breakfast", "Lunch", "All Day").
3. Save the menu.

Each cafeteria can have multiple menus.

---

### Step 4 — Create Categories and Items

Within each menu:

1. Click **Add Category**. Enter category name (e.g., "Hot Beverages", "Sandwiches"). Categories are **collapsible** groups; names are client-configurable.
2. Within each category, click **Add Item**:
   - Item name
   - Price (set to `0` or a negative value to hide price on the front end)
   - **Availability time range** (optional) — the window during which this item is available for ordering. Example: pizza available 12:00–15:30 only. This is the **Customizable Catering Time Range** feature; it can be enabled per item.
   - **Booking deadline** (optional) — how far in advance the item must be ordered. If an organizer tries to book past the deadline, the item is greyed out/unavailable.

> ⚠️ Enabling per-item time ranges requires this feature to be toggled on for the client (SE team action — confirm with PM whether it is already enabled for the BUID).

---

### Step 5 — Configure Delivery Slots and Cut-off Policy

**Delivery slots** are the time windows users can select within their meeting's start–end range.

- Slots are automatically derived from the meeting time window; no fixed list to configure by default.
- For all-day meetings, multiple delivery slots can be selected (e.g., 9am breakfast, 1pm lunch, 4pm snacks).
- Users cannot currently be restricted to a specific number of delivery slots (by design, as of pptx v1).

**Cut-off (cateringLimits)** — set per participant count tier via the `cateringLimits` config (`.com` server only):

- Defines the cut-off time before which catering can be modified/cancelled.
- After the cut-off, editing or deleting a meeting with a catering order shows: _"This meeting contains catering request, which cannot be modified."_

| Property | Server | Notes |
|---|---|---|
| `cateringLimits` | `.com` only | JSON/LIST defining cut-off times per participant band |
| `CATERING_ORDER_STATUS_LIST` | both | JSON defining custom status labels on the catering dashboard |

> ⚠️ `cateringLimits` is a `.com`-only config. For `.in` server clients, cut-off behaviour follows
> system defaults — confirm expected behaviour with the product team before go-live.

---

### Step 6 — Grant Catering Dashboard Access

The catering dashboard (order management, delivery tracking, allergy info, cleaning/staff requests)
is visible only to users who have been granted access.

1. Navigate to **WIS Admin → Meeting Rooms Settings → Catering Dashboard Users**.
2. Add the email IDs of users who should have dashboard access.
3. Save.

These users can view delivery status, individual orders, allergy notes, and additional organizer
requests (room cleaning, service staff).

---

### Step 7 — Optional: Cost-Center Workflow

If the client requires cost-center capture on catering orders:

| Property | Value | Notes |
|---|---|---|
| `Cost_Center_Catering` | `true` | Shows the cost-center input field on the catering request form |
| `Cost_Center_Min_Len` | integer | Minimum character length for the cost-center field |
| `Cost_Center_Max_Len` | integer | Maximum character length for the cost-center field |

---

### Step 8 — Validate

- [ ] Catering section appears in the meeting booking form for a test room
- [ ] Menu categories and items are visible and selectable
- [ ] A delivery slot can be chosen within the meeting time window
- [ ] Test order placed successfully; order appears on the catering dashboard
- [ ] Cut-off enforcement: attempt to edit a meeting with a past-cut-off catering order — confirm the blocking message appears
- [ ] Catering dashboard user can view the test order with delivery time, location, cost
- [ ] If cost-center enabled: field appears on booking form with correct min/max length validation

---

## Screenshots / Evidence

Catering feature walkthrough (slides): `raw/se-runbook/crawl/files/1w63IH9n7w28kJCKljb5kUvJhJGtcdt-WDeD8hkUcB54.pptx`

Full catering PRD (UI flows, email templates, report exports): [[sources/meeting-rooms-catering-prd]] (v2.3, 2024-03-12)

---

## Notes & Gotchas

- **`cateringLimits` is `.com`-only.** `.in` server clients cannot configure participant-count-based cut-offs via this property.
- **Time-range per item is an opt-in feature.** It is not on by default — requires SE enablement. "Can the admin set two different time ranges for one item?" — No, only one time range per item is supported (as of pptx Q&A).
- **Slot count restriction is not supported.** Admins cannot cap the number of delivery slots a user selects per booking (by product design, as of pptx Q&A).
- **Multi-room catering**: a single booking can include catering across multiple rooms (feature from PRD v1.1+). Each room's associated cafeteria(s) are shown.
- **Price display**: set item price to `0` or negative to hide it from employees on the front end.
- **Cafeteria → room inheritance**: adding a new cafeteria to an office automatically makes it available in all rooms. Exclusions must be done per-room.

---

## Related Jira

—

---

## Linked Raw Evidence

- [[sources/se-runbook-meeting-rooms]] — SE pptx (catering feature slides) + control document
- [[sources/meeting-rooms-catering-prd]] — full catering PRD (v2.3, 2024-03-12; UI flows, email, reports)
