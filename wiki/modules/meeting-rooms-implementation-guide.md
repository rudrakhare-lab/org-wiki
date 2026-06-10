---
type: implementation-guide
module: meeting-rooms
last_updated: 2026-06-10
---

# Meeting Rooms — End-to-End Implementation Guide

## Overview

Meeting Rooms is WorkInSync's room booking and management module. It covers the full lifecycle
of a room reservation — from discovery and booking to check-in, auto-release, catering, and
maintenance. It works across four surfaces: **web**, **mobile app**, **kiosk**, and
**Outlook/Google calendar**.

This guide covers everything needed to implement Meeting Rooms for a new client: setup types,
mandatory configs, RBAC privileges, surface-specific configs, and known reference tickets.

---

## 1. Setup Types

There are two deployment modes. You must determine this first — it changes the entire config set.

| Type | Description | Key indicator |
|---|---|---|
| **Native (WIS Calendar)** | Rooms created and managed entirely in WorkInSync. No Outlook/Google sync. | `IS_WIS_CALENDAR = true` |
| **Integrated (Outlook/Google)** | Rooms exist in Exchange/Google Workspace. WIS syncs bidirectionally via the `outlook` service. | `IS_WIS_CALENDAR = false`, `CONSENT_TYPE` required |

> **Hybrid** (`OutlookNativeRoomSetup = true`) also exists for clients who want both native and integrated rooms in the same BUID.

---

## 2. Master Switch — Enable Meeting Rooms

Set at BUID level on both `.in` and `.com` servers.

```
MEETING_ROOM_ENABLED = true
```

This is the first thing to set. Nothing works without it. Also enable at the Project Management
Service level so the Meeting Room option appears in the Team Manager Dashboard:

```
MEETING_ROOM_ENABLED = true   (PROJECT-MANAGEMENT-SERVICE)
```

---

## 3. Core Booking Configs

These apply to all setup types.

| Config | Type | Default | Description |
|---|---|---|---|
| `advanceBookingLimitInMinutes` | INTEGER | — | How far ahead users can book a room |
| `maxDurationInMinutes` | INTEGER | — | Maximum duration of a single booking |
| `minDurationInMinutes` | INTEGER | — | Minimum duration of a single booking |
| `meetingStartTimeCuttoffInMinutes` | INTEGER | — | How close to start time a booking can be created |
| `room_cancel_cutoff` | INTEGER | — | Cancellation cut-off in minutes before meeting start |
| `beginHour` | INTEGER | — | Start of bookable hours (0–24), room-level |
| `endHour` | INTEGER | — | End of bookable hours (0–24), room-level |
| `weekdays` | LIST | — | Working days for the office |
| `timezone` | STRING | — | Office timezone |
| `rommEnabled` | BOOLEAN | — | Enables/disables a specific room for booking |
| `AD_HOC_MEETING` | INTEGER | — | Auto check-in window for ad-hoc bookings (minutes) |
| `recurringBookings` | BOOLEAN | — | Enables recurring booking flow (.com only) — see PB-62637 |
| `smartRoomRecommendation` | BOOLEAN | — | AI-based room recommendation (.com only) |

---

## 4. Check-in & Auto-release Configs

Auto-release is one of the most important and most misconfigured features. Get this right.

| Config | Type | Default | Recommended | Description |
|---|---|---|---|---|
| `RELEASE_MEETING_ROOM` | BOOLEAN | false | true | Master switch — must be true for auto-release to work |
| `MEETING_ROOM_RELEASE_IF_NO_CHECKIN` | INTEGER | 180 min | **15 min** | Minutes after meeting start before room is released if no check-in |
| `enableCheckInForMeetingRoom` | BOOLEAN | — | true | Enables check-in button on web and app (.com only) |
| `meetingRoomCheckInCutOff` | INTEGER | — | — | Cutoff for check-in button visibility on web/app |
| `enableCheckInReminderEmailForRoom` | BOOLEAN | — | true | Sends reminder email before check-in deadline |
| `enableCheckInReminderNotificationForRoom` | BOOLEAN | — | true | Sends push notification reminder |
| `RELEASE_ROOM_CANCEL_MEETING` | BOOLEAN | — | — | If true, releasing a room also cancels the calendar event |
| `releaseRoomEmailList` | LIST | — | — | Additional recipients notified when a room is auto-released |
| `ReleaseRoom` | BOOLEAN | — | — | Room-level override for release functionality |

> **Decision (2026-04-27):** If no check-in within `MEETING_ROOM_RELEASE_IF_NO_CHECKIN` minutes,
> the room is released and the organiser is notified — but the **calendar event is NOT cancelled**.
> The deployment default is 180 minutes; the team-recommended setting is **15 minutes**.
> Reference: `decisions/2026-04-27-meeting-room-auto-release`

---

## 5. Notification Configs

| Config | Type | Default | Description |
|---|---|---|---|
| `MEETING_START_NOTIFICATION` | INTEGER | 5 min | Reminder notification before meeting starts |
| `MEETING_END_NOTIFICATION` | INTEGER | 10 min | Notification before meeting ends |
| `organiserPersonaMeetingRooms` | JSON | — | Email notification settings for organiser (.com only) |
| `participantPersonaMeetingRooms` | JSON | — | Email notification settings for participants (.com only) |
| `otherUsersPersonaMeetingRooms` | JSON | — | Email notification settings for other users (.com only) |
| `organiserBookingEmailsMeetingRooms` | BOOLEAN | — | Whether organiser receives booking emails |
| `sendRoomBookingEmailToAllParticipants` | BOOLEAN | — | Send booking email to all participants |
| `RoomBookingEmailEnabled` | BOOLEAN | — | Enables emails to additional recipients |
| `roomBookingsEmailList` | LIST | — | Additional recipients for booking emails |
| `SEND_INVITE_TO_ALL_EMPLOYEES` | BOOLEAN | — | Controls recipients of native room booking emails |
| `MEETING_ROOM_SYNC_JOB_EMAIL_LIST` | LIST | — | Recipients for sync job notifications |
| `MEETING_ROOM_SUBSCRIPTION_JOB_EMAIL_LIST` | LIST | — | Recipients for subscription status emails (.com only) |

---

## 6. Kiosk Configs

The Meeting Rooms Kiosk is a native tablet app mounted outside each room. It is paired to a
specific room via a pairing code. It shares MDM infrastructure with the Floor Kiosk module.

### Kiosk UI Visibility Controls

| Config | Type | Description |
|---|---|---|
| `HideCheckInButton` | BOOLEAN | Hide check-in button on kiosk screen |
| `HideCancelButton` | BOOLEAN | Hide cancel button on kiosk screen |
| `HideEndButton` | BOOLEAN | Hide End Now button |
| `HideExtendButton` | BOOLEAN | Hide Extend button |
| `HideStartMeetingButton` | BOOLEAN | Hide Start Meeting button |
| `HideOrganizerName` | BOOLEAN | Hide organiser name on kiosk |
| `HideMeetingTitle` | BOOLEAN | Hide meeting title on kiosk |
| `textOnKiosk` | BOOLEAN | Show additional text on kiosk screen |
| `textMessageForKiosk` | JSON | Text content displayed on kiosk (.com only) |
| `noAutoCheckinKiosk` | BOOLEAN | Disable auto check-in when check-in button is hidden (.com only) |
| `roomCheckinQrOnKiosk` | BOOLEAN | Show QR code on kiosk for check-in (.com only) |
| `roomStatsKiosk` | BOOLEAN | Show room stats on kiosk (.com only) |
| `colorVCStatsIconsKiosk` | STRING | Color for VC stats on kiosk (.com only) |

### Kiosk Authentication

| Config | Type | Default | Description |
|---|---|---|---|
| `MEETING_EMAIL_OTP_TO_AUTHENTICATE` | BOOLEAN | true | Send OTP via email to verify cancel/end actions on kiosk |
| `CANCEL_EVENT_PIN_VERIFICATION_ENABLE` | BOOLEAN | false | Require PIN verification to cancel a meeting on kiosk |
| `EnableMRMailCancel` | BOOLEAN | — | Send email to organiser on kiosk cancellation |
| `EnableMROTPCancel` | BOOLEAN | — | OTP verification on kiosk cancellation |

> ⚠️ `CANCEL_EVENT_PIN_VERIFICATION_ENABLE` and `MEETING_EMAIL_OTP_TO_AUTHENTICATE` must be
> consistent. A mismatch causes confusing auth prompts on kiosk.

### Kiosk Display

| Config | Type | Description |
|---|---|---|
| `SHOW_UPCOMING_BOOKINGS_TIME` | INTEGER | Minutes before meeting start when kiosk screen turns yellow |
| `kioskDefaultImage` | STRING | Default image displayed on kiosks across the BUID |
| `KIOSK_IMAGE_FOR_OFFICE` | STRING | Kiosk image applied at office level |
| `iadeaLightsBrightness` | JSON | LED light color and brightness for IADEA devices |
| `Room_Kiosk_With_Cisco` | BOOLEAN | Enable Cisco-specific fields in kiosk settings |
| `showWisLogo` | BOOLEAN | Show/hide MoveInSync logo on kiosk |
| `Room_As_Organizer` | BOOLEAN | Enable room as organiser workflow on kiosk |

### Kiosk Status Colours

| Colour | Meaning |
|---|---|
| Green | Available |
| Orange | Meeting starting within 30 minutes |
| Red | In use / Booked |
| Yellow | Under maintenance |

---

## 7. Mobile App Configs

| Config | Type | Description |
|---|---|---|
| `showMeetingRoomOnApp` | BOOLEAN | Shows Meeting Rooms section in the mobile app |
| `showQRScannerMeetingCheckIn` | BOOLEAN | Enables QR scanner for room check-in via app |

The mobile app provides:
- **Book Now** — instant booking with auto check-in
- **Book Later** — calendar slot picker
- **QR scan check-in** — camera-based
- **Push notifications** — booking confirmations, auto-release alerts, maintenance banners

---

## 8. Outlook / Google Calendar Integration Configs

Only relevant for **Integrated** setup (`IS_WIS_CALENDAR = false`).

| Config | Type | Default | Description |
|---|---|---|---|
| `IS_WIS_CALENDAR` | BOOLEAN | — | false = integrated setup |
| `CONSENT_TYPE` | STRING | ADMIN | Who grants Outlook consent: ADMIN or USER |
| `ENABLE_WITH_PRINCIPAL_NAME` | BOOLEAN | true | Use email prefix as display name when name unavailable |
| `OUTLOOK_WO_ADMIN_CONSENT` | BOOLEAN | — | Controls room email ID field in settings (needed for integrated setup) |
| `OutlookNativeRoomSetup` | BOOLEAN | — | Hybrid setup — both native and integrated rooms (.com only) |
| `ENABLE_AUTO_MEETING_ROOM_SYNC` | BOOLEAN | — | Auto-runs room sync when enabled |
| `SyncMeetingRooms` | BOOLEAN | — | Shows Sync Rooms button in settings (integrated setups) |
| `BLOCK_CALENDAR_FOR_X_MINS` | INTEGER | — | How long the room calendar is blocked around a meeting |
| `BUILDING_PREMISE_NAME` | STRING | — | Entity name used in Outlook on Stratus sites |
| `OFFICE_PREMISE_NAME` | STRING | — | Office mapping for meeting room sync |
| `FLOOR_PREMISE_NAME` | STRING | — | Floor-level name for sync |
| `room_name` | STRING | — | Room name mapping via Outlook sync |
| `CREATE_PREMISE_IF_IT_DOESNT_EXIST` | BOOLEAN | — | Create premise automatically if not found |
| `MULTI_DOMAIN` | BOOLEAN | — | Multiple domains in a single BUID (e.g. MAF) |
| `showOrganiserNameAddInTimeline` | BOOLEAN | — | Show organiser name on Outlook Add-in timeline |
| `INVITE_VISITOR_ROOMS` | BOOLEAN | — | Enable Invite Visitor tab in Outlook Add-in |
| `IT_REQUEST_OUTLOOK_ADDIN` | BOOLEAN | — | Enable IT request in Outlook Add-in (.com only) |

> Consent URL generation requires 4 params: `buid`, `emailId`, `onboardingType`
> (OUTLOOK or GSUITE), `role`. Runs via `wis-integration.workinsync.io/outlook/...`

---

## 9. Catering Configs

Catering must be enabled separately from Meeting Rooms. Master switch first.

| Config | Type | Description |
|---|---|---|
| `ENABLE_MEETING_CATERING` | BOOLEAN | Master switch — enables catering in room booking form |
| `cateringLimits` | LIST | Cut-off times for modifying/cancelling orders by participant count (.com only) |
| `CATERING_ORDER_STATUS_LIST` | JSON | Configurable status labels for the catering dashboard |
| `mealMailList` | STRING | Email recipients for catering communications |
| `Meeting_Title_Catering_Order` | BOOLEAN | Show meeting title in catering dashboard detail view |
| `Cost_Center_Catering` | BOOLEAN | Show cost centre field in catering workflow |
| `Cost_Center_Max_Len` | INTEGER | Max characters for cost centre input |
| `Cost_Center_Min_Len` | INTEGER | Min characters for cost centre input |
| `dynamicFieldsConfigForRooms` | LIST | Custom fields for catering workflow |
| `dynamicFieldOnRooms` | BOOLEAN | Show dynamic fields on room booking form |
| `dynamicFieldLabel` | JSON | Label text for the meeting request section |
| `dynamicFieldUserEmails` | LIST | Email recipients for dynamic field notifications |
| `endTimeBufferRoomBookingBuidLevel` | BOOLEAN | End time buffer at BUID level for catering/IT request (.com only) |
| `endTimeBufferRoomBookingRoomLevel` | INTEGER | End time buffer at room level (.com only) |
| `startTimeBufferRoomBookingBuidLevel` | BOOLEAN | Start time buffer at BUID level (.com only) |
| `startTimeBufferRoomBookingRoomLevel` | INTEGER | Start time buffer at room level (.com only) |
| `facilityMailList` | STRING | Email recipients for IT request workflow (.com only) |
| `itemsDynamicFields` | LIST | Dynamic fields for IT request (.com only) |

---

## 10. Room Approval Workflow Configs

| Config | Type | Description |
|---|---|---|
| `roomWithApproval` | BOOLEAN | Enables approval workflow for room bookings (.com only) |
| `roomWithApprovalBuidLevel` | BOOLEAN | Enables approval workflow at BUID level (.com only) |
| `maxApprovalRequest` | INTEGER | Max overlapping approval requests per user (.com only) |
| `defaultAdvanceBookingLimitForBypass` | INTEGER | Advance booking limit bypass threshold (.com only) |
| `defaultMaxDurationForBypass` | INTEGER | Max duration bypass threshold (.com only) |

---

## 11. Dynamic Policy (Tag-based Access Control)

Tag-based access restricts which employees can book which rooms.

**⚠️ Applies to Native Rooms only.** Does NOT apply to Outlook/Google calendar rooms.

**Tag matching rule:**
- Same tag name AND same value → employee can book
- Mismatched value → blocked
- No tag on the room → bookable by anyone
- Tag on the employee but not the room → bookable

| Config | Type | Description |
|---|---|---|
| `ROOM_TAGGING_ENABLED` | BOOLEAN | Enables tag-based access control for rooms |
| `Show_Room_If_Not_Eligible` | BOOLEAN | Controls whether ineligible rooms are visible |

Tags are created and owned by the Tags/Desk/Parking module and reused here.

---

## 12. Room Maintenance Configs

| Config | Type | Default | Description |
|---|---|---|---|
| `roomMaintenanceWorkflow` | BOOLEAN | — | Enables room maintenance scheduling section |
| `roomMaintenanceAdvanceScheduleAllowed` | INTEGER | 90 days | How far ahead maintenance can be scheduled |
| `roomMaintenanceList` | JSON | — | Stored maintenance periods (held in floor-plan service) |
| `roomMaintenanceMessage` | JSON | "Contact your administrator" | Message shown to users for rooms under maintenance |
| `roomMaintenceEmalList` | LIST | [] | Email recipients for maintenance create/delete notifications (note: "Emal" is the actual PMS key — not a typo in this doc) |

---

## 13. Admin & Settings Configs

| Config | Type | Description |
|---|---|---|
| `BULK_UPLOAD_ENABLED` | BOOLEAN | Enables bulk room upload in Meeting Rooms Settings |
| `BULK_UPLOAD_HEADERS` | LIST | Column headers for bulk upload (do not alter) |
| `Create_Meeting_Room` | BOOLEAN | Controls visibility of Create Room button in settings |
| `DEACTIVATION_TYPE` | STRING | Controls deactivation behaviour for a room |
| `CheckOutCTARooms` | BOOLEAN | Controls checkout button visibility (.com only) |
| `meetingRoomCost` | BOOLEAN | Show/hide meeting room cost in UI |
| `IS_RICHEMONT` | BOOLEAN | Enables Richemont-specific workflow |
| `office_name` | STRING | Office label to scope rooms and configs |

---

## 14. RBAC — Privileges

The following privileges control Meeting Rooms access. These are configured in the RBAC/Privilege
settings for each role (Employee, Office Admin, Team Manager, etc.).

| Privilege | Description | Reference |
|---|---|---|
| `Book_Meeting_Room` | Allows a user to book meeting rooms | Core privilege |
| `Cancel_Meeting_Room` | Allows cancellation of room bookings | Core privilege |
| `Manage_Meeting_Room` | Admin-level — create, edit, delete rooms and settings | Core privilege |
| `View_Catering_Dashboard` | View and manage catering orders | Catering workflow |
| `Approve_Meeting_Room` | Approve/reject room booking requests | Approval workflow |
| `Bypass_Advance_Booking_Limit` | Book beyond the normal advance booking window | PB-61845 |
| `Bypass_Max_Duration` | Book rooms beyond the max duration limit | PB-61845, TB-45947 |
| `Front_Desk_View_Meeting_Rooms` | View meeting rooms from front desk | Front desk role |
| `Room_As_Organizer` | Allows the room itself to be set as the meeting organiser | Kiosk workflow |

> Reference tickets for RBAC:
> - **PB-61845** — Booking Window and Max Duration limitation by privilege (Native + Old room)
> - **TB-45947** — Handle Max Duration, Max Duration Limit on kiosk by privilege
> - **PB-64585** — RBAC for Room Booking within admin purview (PwC India)
> - **PB-68531** — Hover state on room name based on privilege (Rhino)

---

## 15. New Client Onboarding — Minimum Config Checklist

```
# Step 1 — Enable the module
MEETING_ROOM_ENABLED = true                      (MEETING_ROOMS service)
MEETING_ROOM_ENABLED = true                      (PROJECT-MANAGEMENT-SERVICE)

# Step 2 — Set setup type
IS_WIS_CALENDAR = true    (Native)
IS_WIS_CALENDAR = false   (Integrated — also set CONSENT_TYPE and run consent flow)

# Step 3 — Booking limits
advanceBookingLimitInMinutes = <client requirement>
maxDurationInMinutes = <client requirement>
timezone = <office timezone>
weekdays = <working days>

# Step 4 — Auto-release (strongly recommended)
RELEASE_MEETING_ROOM = true
MEETING_ROOM_RELEASE_IF_NO_CHECKIN = 15          (recommended; deployment default is 180)
enableCheckInForMeetingRoom = true
enableCheckInReminderEmailForRoom = true

# Step 5 — Kiosk (if kiosks are being deployed)
SHOW_UPCOMING_BOOKINGS_TIME = 6                  (deployment default)
MEETING_EMAIL_OTP_TO_AUTHENTICATE = true         (deployment default)
CANCEL_EVENT_PIN_VERIFICATION_ENABLE = false     (deployment default)

# Step 6 — Mobile app (if mobile is enabled)
showMeetingRoomOnApp = true
showQRScannerMeetingCheckIn = true

# Step 7 — Catering (if catering is required)
ENABLE_MEETING_CATERING = true
mealMailList = <catering team email>
```

---

## 16. Services Involved in Deployment

Four backend services power Meeting Rooms:

| Service | Role |
|---|---|
| `floor-plan` | UI — room catalog, booking form, settings page |
| `outlook` | Outlook/Google sync connector (integrated setup only) |
| `booking-v2` | Booking data and business logic |
| `kiosks-UI` | Kiosk native app serving |

---

## 17. Reference Jira Tickets

| Ticket | Summary | Status |
|---|---|---|
| PB-62637 | Recurring booking support — create, edit, cancel (web + native) | Done |
| PB-61845 | Booking Window and Max Duration limitation by privilege | Done |
| TB-45947 | Handle Max Duration on kiosk by privilege | Done |
| PB-64585 | RBAC for Room Booking within admin purview — PwC India | Done |
| PB-68531 | Hover state on room name based on privilege (Rhino) | In progress |
| PB-68153 | Grid View compact view — approval workflow colour status (Rhino) | In progress |
| PB-68539 | UI changes for web view and approvals dashboard (Rhino) | In progress |
| PB-68450 | Catering Approval Flow | Done |
| TO-25999 | Blank kiosk screen on Cisco Room Navigator after wakeup — PwC | Done |
| TB-50416 | Latency check — meeting room page with 75k employees | Done |
| SE-58394 | Enable Meeting Room Inventory report | In progress |
| PB-68172 | Add multiple rooms in Add Room Modal — Native only (Rhino) | Done |

---

## 18. Known Issues & Gotchas

1. **Auto-release deployment default (180 min) is almost always wrong.** The team recommends
   15 minutes. Always override this for new clients.

2. **`RELEASE_MEETING_ROOM` must be explicitly set to `true`.** Default is false — auto-release
   does not activate even if `MEETING_ROOM_RELEASE_IF_NO_CHECKIN` is set.

3. **Dynamic Policy does not apply to Outlook/Google rooms.** Tag policies on integrated rooms
   have no effect. Native rooms only.

4. **`roomMaintenceEmalList`** — the PMS key has a typo ("Emal"). Use this exact spelling in PMS.

5. **Kiosk OTP configs must be consistent.** `CANCEL_EVENT_PIN_VERIFICATION_ENABLE` and
   `MEETING_EMAIL_OTP_TO_AUTHENTICATE` must not conflict — mismatch causes confusing auth on kiosk.

6. **GPS check-in indoors.** If GPS enforcement is enabled for mobile check-in and the room is
   indoors with poor GPS signal, check-in can fail silently. No documented fallback exists.

7. **Calendar event not cancelled on auto-release.** When a room is auto-released, attendees
   still have the calendar event — only the WIS room association is removed. Communication gap.
