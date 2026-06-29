---
type: runbook
module: meeting-rooms
team: SE
status: active
last_updated: 2026-06-29
source: "[[sources/se-runbook-meeting-rooms]]"
raw_path: raw/se-runbook/crawl/files/1qcf6HjovQ5MwBKnWWiLsYtqZghp7GC_s-c7gGyLbK6I.docx
---

# Runbook — Meeting Room Setup & Booking Configuration

## Purpose & Scope

End-to-end SE setup for enabling WorkInSync Meeting Rooms for a client. Covers:

1. Enabling the Meeting Rooms master switch
2. Creating meeting room resources (UI, bulk upload)
3. Configuring booking behaviour (advance limits, auto-release, check-in, notifications)
4. Enabling optional sub-features (QR check-in, app visibility, dynamic policy)
5. Room-level configuration (begin/end hours, time zones)

This runbook covers WIS-native ("native") rooms. Outlook/Google calendar-connected rooms are
covered in [[runbooks/outlook-room-integration]]. Catering setup is separate:
[[runbooks/meeting-room-catering-setup]].

> **Note:** The source document is a 52k-char control document (v1–1.4, 2023). The steps below
> cover the setup layer captured in the first ~13k chars. For exhaustive booking-UI use cases
> and acceptance criteria, consult the raw source and [[sources/meeting-rooms-app-prd]].

_Source: [[sources/se-runbook-meeting-rooms]]_

---

## Prerequisites

- Provisioned BUID for the target client
- Admin/global-admin access to the WIS admin portal for that BUID
- Office premise(s) already created (see [[runbooks/ets-office-premise-setup]])
- Floor plans uploaded if rooms are to appear on floor-plan views (see [[runbooks/floor-plan-upload]])
- Confirm whether rooms will integrate with Outlook/Google (if yes, complete [[runbooks/outlook-room-integration]] first before creating calendar-linked rooms)
- Confirm which server the client is on (`.com` / `.in`) before calling any API

---

## Configuration Flow

```
Office Premise exists (ets-office-premise-setup)
        ↓
Enable MEETING_ROOM_ENABLED (BUID level)       ← STEP 1
        ↓
Create Room Resources (UI or bulk upload)       ← STEPS 2–3
        ↓
Configure Booking Behaviour                     ← STEP 4
        ↓
Configure Notifications                         ← STEP 5
        ↓
Enable Optional Sub-Features                    ← STEP 6
        ↓
Validate bookings end-to-end                    ← STEP 7
```

---

## Ordered Steps

### Step 1 — Enable Meeting Rooms for the BUID

1. Navigate to **WIS Admin → Meeting Rooms Settings**.
2. Set the BUID-level PMS property `MEETING_ROOM_ENABLED` = `true`.
3. Confirm the Meeting Rooms tab/link becomes visible in the admin portal.

> ⚠️ Without `MEETING_ROOM_ENABLED = true`, no meeting room features are visible to employees or admins.

---

### Step 2 — Create Meeting Room Resources (UI)

Navigate to **WIS Admin → Meeting Rooms Settings → Create Room** (controlled by `Create_Meeting_Room` = `true`).

For each room:

1. **Room Name** — enter the display name.
2. **Office** — select the office premise this room belongs to.
3. **Floor** — select the floor within the office.
4. **Capacity** — set the headcount.
5. **Amenities** — select from the configured amenity list (projector, whiteboard, VC, etc.).
6. **Images** — upload room photos (optional).
7. **Calendar Type** — choose:
   - `NATIVE` — room is managed entirely in WIS (no Outlook/Google sync)
   - `OUTLOOK` / `GOOGLE` — room is backed by an Outlook/Google calendar resource mailbox
8. **Active Hours** — set `beginHour` (0–24) and end hour; controls the bookable time window displayed on the room timeline.
9. Save. The room is immediately visible in search results.

> ⚠️ For OUTLOOK/GOOGLE calendar type rooms, the room mailbox email address must be provided and Outlook integration must already be configured (see [[runbooks/outlook-room-integration]]).

---

### Step 3 — Bulk Upload Rooms

For large deployments use the bulk-upload flow (controlled by `BULK_UPLOAD_ENABLED` = `true`):

1. Navigate to **WIS Admin → Meeting Rooms Settings → Bulk Upload**.
2. Download the template (column headers defined by `BULK_UPLOAD_HEADERS` — do not alter these headers).
3. Fill in room data (name, office, floor, capacity, amenities, calendar type).
4. Upload the file. The system processes and creates all rooms.

> ⚠️ `BULK_UPLOAD_HEADERS` is a system-controlled LIST property — never modify it in PMS directly. If headers need changing, raise with the product team.

---

### Step 4 — Configure Booking Behaviour

Set the following BUID-level PMS properties (via WIS Admin or PMS config API):

| Property | Recommended / Default | Notes |
|---|---|---|
| `advanceBookingLimitInMinutes` | Client-specific | Controls how far in advance employees can book |
| `MEETING_ROOM_RELEASE_IF_NO_CHECKIN` | **15** (deployment default: 180) | Minutes after start before unchecked room is released; 15 min strongly recommended |
| `RELEASE_MEETING_ROOM` | `true` | Must be `true` to activate auto-release |
| `AD_HOC_MEETING` | Client-specific | Minutes window enabling auto check-in for rooms (ad-hoc mode) |
| `BLOCK_CALENDAR_FOR_X_MINS` | Client-specific | Blocks calendar before/after meeting |
| `ALLOW_ONLY_ONE_MEETING_ROOM_AT_ONCE` | `true` (default) | Set `false` only if client needs multi-room bookings per meeting |
| `BOOK_MEETING_ROOM_BY_EMPLOYEES` | `true` (default) | Set `false` to restrict employee self-service booking |
| `SHOW_SPECIAL_REQUEST_ON_MEETING` | Client-specific | Shows a special-request text field on the booking form |

---

### Step 5 — Configure Notifications

| Property | Default | Notes |
|---|---|---|
| `MEETING_START_NOTIFICATION` | `5` (min) | Reminder before meeting start |
| `MEETING_END_NOTIFICATION` | `10` (min) | Reminder before meeting end (next-meeting warning) |
| `MEETING_EMAIL_OTP_TO_AUTHENTICATE` | `true` | PIN email sent for kiosk cancel/end |
| `CANCEL_EVENT_PIN_VERIFICATION_ENABLE` | `false` | Require PIN to cancel event on kiosk |

> ⚠️ `RELEASE_MR_NOTIFICATION` controls the push notification triggered when a room is auto-released due to no check-in. Confirm this is enabled if clients need visibility into released rooms.

---

### Step 6 — Enable Optional Sub-Features

| Sub-feature | Config Key | Value | Notes |
|---|---|---|---|
| Mobile app visibility | `showMeetingRoomOnApp` | `true` | Shows Meeting Rooms on the WIS mobile app |
| QR code check-in (app) | `showQRScannerMeetingCheckIn` | `true` | Employees scan room QR via app; if `false`, direct check-in button |
| Room maintenance workflow | `roomMaintenanceWorkflow` | `true` | Enables maintenance scheduling section in admin |
| Catering | `ENABLE_MEETING_CATERING` | `true` | See [[runbooks/meeting-room-catering-setup]] |
| Kiosk check-in prompt | `SHOW_UPCOMING_BOOKINGS_TIME` | `6` (min, default) | Minutes before start to show check-in prompt on kiosk display |

---

### Step 7 — Validate

- [ ] Meeting Rooms tab is visible in admin portal
- [ ] At least one room appears in the employee booking interface with correct capacity/amenities
- [ ] A test booking can be created and confirmed
- [ ] Auto-release triggers after `MEETING_ROOM_RELEASE_IF_NO_CHECKIN` minutes without check-in
- [ ] Release notification email/push is sent to the organizer
- [ ] QR check-in works (if `showQRScannerMeetingCheckIn` = `true`)
- [ ] Meeting start/end reminder notifications fire at configured intervals

---

## Screenshots / Evidence

See raw source for Figma links and UI screenshots:
- Booking UI: `https://www.figma.com/file/KSI9qUFiNlzl9AC6Iunk8Z/Employee-Meeting-rooms`
- Admin status view: `https://www.figma.com/file/DfTPJBr97QvlYQGqrz4MXL/Meeting-rooms...`

Raw evidence file: `raw/se-runbook/crawl/files/1qcf6HjovQ5MwBKnWWiLsYtqZghp7GC_s-c7gGyLbK6I.docx`

---

## Notes & Gotchas

- **Native vs calendar-integrated rooms**: `NATIVE` rooms have no Outlook/Google sync. Dynamic Policy (tag-based access control) applies **only** to native rooms — it has no effect on Outlook/Google calendar rooms.
- **BUID-level vs room-level configs**: `beginHour`/end hour are room-level configurations. Most other properties are BUID-level. Check scope before setting.
- **Admin vs employee cancel**: Only admins can release/cancel a booking from the Meeting Rooms card. Employees who try see "You do not have permissions to release the meeting room."
- **Guest invite workflow**: Meeting organizers can invite external guests; guest availability is shown only if their calendar is synced. If not synced, "Calendar not available" is displayed.
- **Source doc coverage**: The control document is 52k chars; only the first ~13k were captured in the SE crawl input. For exhaustive acceptance criteria on booking edge cases (timezone, recurring meetings, edit/extend logic), consult the raw file directly.

---

## Related Jira

—

---

## Linked Raw Evidence

- [[sources/se-runbook-meeting-rooms]] — SE control document (2023)
- [[sources/meeting-rooms-app-prd]] — PRD: booking UI, use cases, notification design
- [[sources/meeting-rooms-resources]] — deployment block with operational config defaults
- [[sources/meeting-rooms-room-maintenance]] — room maintenance config reference
