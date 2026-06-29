---
type: release-notes
year: 2024
last_updated: 2026-06-30
source: "—"
---

# Release Notes — 2024

This page is part of the [[history/release-notes]] history layer. Entries are distilled from the PM/sales-facing release-note decks ingested via the SE-runbook crawl. **Recency caveat:** these notes describe behaviour at ship time; consult [[modules/]] and [[configs/]] pages for current authoritative state. Conflicts with curated pages are flagged with ⚠️ inline.

_RN 09-2024 is not present in the crawl — gap noted. Decks present: 01, 02, 03&04, 05, 06, 07, 08, 10, 11, 12, 13, 14, 15, 16._

---

### RN 16-2024

- **Office Eligibility Mapping — Transport Restriction** — restrict which offices employees can select during booking creation based on a mapping; prevents selection of unmapped offices for transport. `preventTransportSelectionOutsideMappedOfficesFor` → [[modules/ets]], [[modules/employee-experience]]. Enablement: SE ticket | PB-47440
- **Ad-Hoc Shifts on WiS-ETS Sites (Web)** — ad-hoc shifts previously only worked on mobile; now supported on web for WiS-ETS sites. Also allows weekly-off selection during recurring booking when `enableWeeklyOffBookings` is enabled. → [[modules/ets]]. Enablement: SE ticket | `preventTransportSelectionOutsideMappedOfficesFor` | PB-47435 / PB-47717
- **Admin Dashboard UI Improvements** — desk occupancy metric title wrapping fix; "Not yet planned" default-selection fix in Attendance graph; report schedule page now shows office column for easier identification. → [[modules/desk-management]]. Enablement: Default | PB-48032 / PB-45847
- **Flexible Desk Allocation for Multi-Team Collaboration** — desks can now be allocated to multiple employees, teams, or hierarchies simultaneously (floor-view only); multi-allocated seat shown with distinct representation. `enableMultiAllocation = ['DESK']` → [[modules/desk-management]]. Enablement: SE ticket | PB-40526
- **Custom Fields in Walk-in Visitor Flow** — visitor type–specific custom fields (e.g. company name, contractor phone) configurable for the walk-in registration form. `formsMetaDataForWalkIn` → [[modules/visitor-management]]. Enablement: SE ticket | PB-47400
- **Invite Cancellation from Front Desk Dashboard** — front desk users can now cancel visitor invites directly from the dashboard without depending on the host. → [[modules/visitor-management]]. Enablement: SE ticket (see raw evidence)

---

### RN 15-2024

- **RFID Number on Stratus Sites** — RFID as a UI/bulk-upload field for user profiles on Stratus sites (previously backend-only, unlike WiS-ETS sites). `enableEmployeeRFIDColumn` → [[modules/access-management]]. Enablement: SE ticket | PB-46385
- **API-Based Access Card Integration Enhancements** — configurable check-in/check-out workflows for API-based access card integration; expanded workflow support beyond the prior fixed flow. → [[modules/access-management]]. Enablement: SE ticket (see raw evidence) | PB-46384
- **Parking ANPR (Automatic Number Plate Recognition)** — consume ANPR camera feed for seamless parking check-in; eliminates manual ScanQR/DigiPass step for vehicle entry. `parkingoverstayenabledfor` → [[modules/parking-management]]. Enablement: SE ticket (see raw evidence)
- **Parking Vehicle Overstay Notifications** — real-time alerts when a vehicle exceeds its booking duration; notifies next-booking holder proactively. → [[modules/parking-management]]. Enablement: SE ticket (see raw evidence)

---

### RN 14-2024

- **Hide Parking Slot Visibility from Employees** — admin can hide slot-level detail from employees when demand greatly exceeds supply, preventing frustration from seeing unavailable slots. `hideParkingSlotInfo` → [[modules/parking-management]]. Enablement: SE ticket | PB-45830
- **Multi and Recurring Booking Enhancements** — multi-day booking summary now shows count of successful/unsuccessful bookings created. → [[modules/desk-management]]. Enablement: Default | PB-45824
- **Support for Overlapping Desk Bookings** — multiple employees can book the same desk during the same time window (configurable). `overlappingTimeInMinutes` → [[modules/desk-management]]. Enablement: SE ticket | PB-46012
- **Streamlined Check-in Workflow (Dedicated Flow)** — dedicated check-in workflow for employees; replaces implicit check-in on booking start. → [[modules/desk-management]], [[modules/employee-experience]]. Enablement: SE ticket | PB-45884
- **Client-Configurable Check-In Reminder Templates on MS Teams** — admins can customize the check-in reminder notification template (office/remote/room) with their own placeholders instead of the fixed default. → [[modules/ms-teams-integration]]. Enablement: SE ticket (see raw evidence)
- **Include Timezone Abbreviations in Booking Emails** — booking confirmation emails now include the timezone abbreviation to reduce confusion for global/distributed teams. → [[modules/employee-experience]]. Enablement: Default | PB-45843
- **External Office and Team-Wise Desk Utilisation APIs** — additional external booking APIs exposing raw office/team-level desk utilisation data for custom dashboards. → [[modules/desk-management]]. Enablement: SE ticket (see raw evidence)

---

### RN 13-2024

- **Carbon Footprint Tracking for Parking Commute** — employees specify fuel type and home location; the system computes carbon emissions per commute and shows a widget (app & web) with monthly emissions, last commute, total parking bookings, and office-level carbon total. Vehicle colour field added as free-text. `enableCarbonFootprintTrackingInParking`, `enableColorInParkingVehicleCreation` → [[modules/parking-management]]. Enablement: SE ticket | PB-45070
- **Office-Level Check-In Mode Configuration** — office check-in mode (ScanQR / DigiPass / Direct / No Check-In) previously BUID-level; now configurable per individual office. `officeCheckInModeWeb`, `officeCheckInModeApp` → [[modules/desk-management]], [[modules/employee-experience]]. Enablement: SE ticket | PB-45183
- **Access Card Device-to-Floor Mapping (SFTP)** — SFTP-based access card integration now supports device→floor premise mapping (previously only device→office). → [[modules/access-management]]. Enablement: TO ticket | PB-45283
- **Badge Number Field on Front Desk** — front desk can record the temporary access card/badge number issued to a visitor during check-in. `badgeNumberOnFrontdesk` (within `front_desk_configurations`) → [[modules/visitor-management]]. Enablement: SE ticket | PB-45277
- **Front Desk Approval/Rejection of Visitor Entry** — front desk personnel can now approve or reject visitor entry (previously only the host could); parallel approval path. `approveEntryFromFrontdesk` → [[modules/visitor-management]]. Enablement: SE ticket | PB-45278
- **Type of Visitor & Flow Info on Front Desk Dashboard** — front desk dashboard now shows visit type and flow type per visitor record to reduce ambiguity. → [[modules/visitor-management]]. Enablement: Default | PB-4529x (see raw evidence)

---

### RN 12-2024

- **Delegation on Mobile App** — delegation previously web-only; users can now switch to a delegator profile from the mobile app sidenav and create bookings on their behalf. `isDelegationEnabled` (grant from web; enable Mobile App privilege) → [[modules/delegation]], [[modules/mobile-app]]. Enablement: SE ticket | PB-44346
- **Accessibility Improvements for Visually-Impaired Users** — web and app improvements based on visually-impaired user feedback; includes floor plan accessibility mode. `enableFloorPlanAccessibility` → [[modules/employee-experience]], [[modules/mobile-app]]. Enablement: SE ticket | PB-44343
- **Team/Hierarchy Legends — Enhanced Visibility** — seat legends now work correctly when `enableProjectColor = false`; standardised team colour palette introduced. `enableProjectColor`, `standardTeamColor` → [[modules/desk-management]]. Enablement: SE ticket | PB-44671
- **VMS Report Enhancements — Column Additions** — detailed VMS report now includes additional visitor/booking columns; guest Wi-Fi columns visible when feature is enabled. → [[modules/visitor-management]]. Enablement: Default | PB-42654
- **Invite Visitors on Behalf of Someone Else** — a user (with privilege) can invite visitors on behalf of another employee. `allowBookingsForOthers`; requires privilege `invite_for_someone_else_vms` → [[modules/visitor-management]]. Enablement: SE ticket | PB-43308
- **Allow Front Desk to Edit Invite End Time** — front desk can extend/edit the end time of a visitor invite for visitors arriving outside scheduled windows. → [[modules/visitor-management]]. Enablement: SE ticket (see raw evidence)

---

### RN 11-2024

- **Indemnification Support for WiS-ETS Sites** — indemnification pop-up (when transport is cancelled or removed from office booking) now works on WiS-ETS sites, not only legacy ETS sites. `indemnifyOfficeBookingTransport` (and related indemnification properties) → [[modules/ets]], [[modules/employee-experience]]. Enablement: SE ticket | PB-42901
- **Booking Cancellation Reason Capture** — admins can mandate a reason when users cancel office or room bookings; reasons are configurable; new Booking Cancellation Reasons Report. `enableBookingCancellationReasonsFor` (values: `["OFFICE", "ROOM"]`) → [[modules/desk-management]], [[modules/meeting-rooms]]. Enablement: SE ticket | PB-43310
- **Limit Meals During Booking Creation** — cap the number of meal items a user can select during the booking flow. `limitMealDuringBookingCreation` → [[modules/meal-management]]. Enablement: SE ticket | PB-43491
- **Auto Tag Assignment Mapping** — when new employees are added via data sync, tags are automatically assigned based on their designation or other attributes per a configurable mapping. `autoTagAssignmentMapping` (JSON) → [[modules/tags-desk-parking]], [[modules/employee-provisioning]]. Enablement: SE ticket | PB-43363

---

### RN 10-2024

- **Parking — Prevent Editing of Vehicle Information + RBAC for Vehicle Creation** — admins can restrict employees from editing vehicle details post-creation; RBAC controls who can create vehicles. → [[modules/parking-management]]. Enablement: SE ticket | PB-42733
- **Parking — Slot Count Visible in Booking Form Filter** — available slot count shown per filter category (e.g. BIKE 20, CAR 24) on the parking booking form. → [[modules/parking-management]]. Enablement: Default if parking is enabled
- **Transport Info on Employee Profile — Configurable** — pickup/drop point, nodal point, trip reminder toggle, and shuttle points on the mobile app employee profile are now hideable for ETS clients that don't need transport features. `disableTransportFeaturesOnProfile` → [[modules/ets]], [[modules/mobile-app]]. Enablement: SE ticket | PB-42803
- **Post-Start-Time Booking Cancellation** — users can cancel a desk/room/remote booking after its start time has passed if they have not yet checked in. → [[modules/desk-management]], [[modules/meeting-rooms]]. Enablement: SE ticket | PB-42648
- **Report Scheduling Experience Improvement** — report scheduling UI and email now shows report type and filters for easy identification. → [[modules/employee-experience]]. Enablement: Default | PB-42637
- **Audit for Meeting Rooms** — audit log for changes to meeting room bookings and room types, surfaced in admin view. → [[modules/meeting-rooms]]. Enablement: SE ticket (see raw evidence)

---

### RN 08-2024

- **Commute Mandatory (Anti Ghost-Booking)** — prevents creation of office bookings with no resource; users must select either parking or transport. `commuteMandatory` → [[modules/ets]], [[modules/employee-experience]]. Enablement: SE ticket | PB-39414
- **DigiPass Configurable to New Levels** — `showSeparateDigipassFor` can now be scoped to specific resource types only (OFFICE / MEALS / PARKING) rather than all. `showSeparateDigipassFor` → [[modules/visitor-management]], [[modules/meal-management]], [[modules/parking-management]]. Enablement: SE ticket | PB-40516
- **Bookings for Someone Else (Web)** — `allowOfficeBookingForOthers` re-shipped with Stratus/ETS + web/app/MS Teams scope in this cycle. `allowOfficeBookingForOthers` → [[modules/desk-management]], [[modules/employee-experience]]. Enablement: SE ticket | PB-41536 ⚠️ Also shipped in RN 06-2024 (PB-39288); RN 08 extends or re-announces with broader platform scope — treat RN 08 as the fuller ship.
- **N-Level Desk Allocation Hierarchy** — clients can define arbitrary-depth org hierarchy for desk allocation (teams/divisions), replacing fixed-level structure. → [[modules/desk-management]]. Enablement: SE ticket (detailed release notes) | PB-40525

---

### RN 07-2024

- **DigiPass for Meals** — DigiPass check-in extended to meal bookings (previously only desks and parking); demand and check-in tracked in Meal Booking Details, Summary, and Summary Meal Consumption reports. `showSeparateDigipassFor` (values: `["OFFICE", "MEALS", "PARKING"]`) → [[modules/meal-management]]. Enablement: SE ticket | PB-37554
- **Meal Bookings via Work Planner** — meals can now be booked through the Work Planner view (previously not supported), useful for manufacturing/bulk-planning clients. `mealPlanningEnabled` → [[modules/meal-management]]. Enablement: SE ticket | PB-40125
- **Remove Meal Selection on Holiday/Weekly Off** — meals automatically de-selected when the booking falls on a configured holiday or weekly off day. `removeMealSelectionOnHolidayAndWeeklyOff` → [[modules/meal-management]]. Enablement: SE ticket | PB-40128
- **Delegation Email Notifications** — email sent to delegatee when a delegation action is performed on their behalf. `emailSentOnDelegateeActions` → [[modules/delegation]]. Enablement: SE ticket | PB-40570
- **Time-Based Desk Allocation** — desks allocated based on shift/time windows rather than fixed full-day. `enableTimeBasedDeskAllocation`, `enableNewAllocationFlow` → [[modules/desk-management]]. Enablement: SE ticket | PB-40251

---

### RN 06-2024

- **Bookings for Someone Else** — employees can create office/desk bookings on behalf of a colleague (web, app, MS Teams; Stratus/ETS). `allowOfficeBookingForOthers` → [[modules/desk-management]], [[modules/employee-experience]]. Enablement: SE ticket | PB-39288
- **Meeting Rooms + Catering: Trigger Emails on Order Update** — catering manager notified by email when items are added to or removed from an existing order (previously only on initial creation). → [[modules/meeting-rooms]]. Enablement: SE ticket (catering setup)
- **Meeting Rooms: Block Calendar for X Minutes** — when a booking is created, the calendar invite can block for a configured number of minutes rather than the full booking duration. `BlockCalendarForXmins` → [[modules/meeting-rooms]]. Enablement: SE ticket
- **VMS: Email Notification to Host on Security Check-in** — host receives email when visitor checks in at the security gate. → [[modules/visitor-management]]. Enablement: Default (NA)
- **VMS: Allow Entry for Pending-Status Visitors** — visitors with "Pending" invite status can be permitted entry at the front desk. → [[modules/visitor-management]]. Enablement: Default (NA)
- **Meeting Rooms + Catering: Participant List in Catering Dashboard** — catering dashboard detailed view shows the full participant list (not just count) for the meeting. → [[modules/meeting-rooms]]. Enablement: Default (NA)

---

### RN 05-2024

- **N Bookings per Period (Quota Limit)** — admins can configure the maximum number of office bookings a user can create in a rolling period. `limitEmployeeBookingDaysUnit` → [[modules/desk-management]]. Enablement: TO ticket | PB-38531
- **Project Code Field on Booking Form** — project/cost-code field added to office booking and meeting room creation forms; can be made mandatory per resource type. `enableProjectCodeFor`, `projectCodeMandatoryFor` (values: `"OFFICE"`, `"MEETING"`) → [[modules/desk-management]], [[modules/meeting-rooms]]. Enablement: SE ticket | PB-41380
- **VMS Self Check-in / Checkout Kiosk Workflow** — dedicated kiosk-mode visitor flow allowing visitors to register, check in, and check out without front desk intervention. → [[modules/visitor-management]]. Enablement: SE ticket + VMS Implementation Doc
- **Cisco Integration for Guest Wi-Fi (VMS)** — visitors are granted temporary guest Wi-Fi access via Cisco integration when visiting an office. `visitor_wifi_name` → [[modules/visitor-management]]. Enablement: SE ticket
- **Host Calendar Invite for Visitor Invitation** — `isCalendarInvite` controls whether the visitor invite is automatically added to host and visitor calendars. `isCalendarInvite` → [[modules/visitor-management]]. Enablement: SE ticket
- **Release Room: Cancel Associated Meeting** — when a room booking is released, the associated calendar meeting is also cancelled (previously room was released but meeting stayed). → [[modules/meeting-rooms]]. Enablement: SE ticket (see raw evidence)

---

### RN 03&04-2024

- **Advance Booking Window — Configurable Opening Time** — admins can set how many hours in advance the booking window opens each day. → [[modules/desk-management]]. Enablement: TO ticket | PB-37120
- **Remote Booking Enhancements: Auto-Cancellation + Check-in Buffer** — auto-cancellation of remote bookings after a configurable cutoff; check-in buffer for remote booking check-ins. → [[modules/desk-management]], [[modules/employee-experience]]. Enablement: SE ticket | PB-37038, PB-37177
- **Meal Feedback** — post-meal feedback collection; two question types configurable; results in Meal Feedback report. `mealFeedbackEnabled` → [[modules/meal-management]]. Enablement: SE ticket
- **Host Approval Workflow for Walk-in Visitors** — walk-in visitors require host approval before entry; host receives an approval request. `isApprovalFlowEnabled` → [[modules/visitor-management]]. Enablement: SE ticket
- **Standard Guest Form for Walk-in Visitors (OTP-less)** — simplified walk-in form without OTP requirement for low-security or internal visitor flows. → [[modules/visitor-management]]. Enablement: SE ticket (see raw evidence)
- **First Integration (see raw evidence)** — slide 16 text truncated in crawl; enablement not extractable — see `raw/se-runbook/crawl/files/1FFLlGmvrmUxbMAlIJGyI2cAPiw7V2nLjFKaXsj3DDoA.pptx`.

---

### RN 02-2024

- **Team Calendar — Custom Hierarchy Views** — users can filter Team Calendar by Office or by Colleague/Reporting-Manager hierarchy (Colleagues = sideways, Reportees = downward); addresses chaotic display for multi-level orgs. `enableTeamCalendarRMView` (default: false) → [[modules/employee-experience]]. Enablement: Property | PB-35293
- **Parking as Standalone Feature** — clients using only parking can enable a flow that shows "Parking" as the primary action in Employee Home and FAB, removing confusing "Office booking" label. `onlyParkingBookingEnabled` (default: false) → [[modules/parking-management]]. Enablement: Property
- **VMS on Outlook Add-In** — visitor invite tab added to the WorkInSync Outlook add-in; users can invite visitors when creating a calendar event without leaving Outlook. → [[modules/visitor-management]], [[modules/ms-teams-integration]]. Enablement: SE ticket (VMS config must be enabled)
- **Meeting Rooms + Catering: Default Status for Catering Orders** — admins can configure the default status for new catering orders (previously fixed as "Requested"). → [[modules/meeting-rooms]]. Enablement: SE ticket (catering setup)
- **Meeting Rooms + Catering: Preserve Items on Delivery-Time Change** — when organiser changes delivery time, items still available for the new time are preserved; unavailable items are flagged rather than resetting the full order. → [[modules/meeting-rooms]]. Enablement: Not applicable (default behaviour)
- **Meeting Rooms + Catering: Edit Flow Status Stability** — editing a catering order no longer resets the order status to default. → [[modules/meeting-rooms]]. Enablement: Not applicable (default behaviour)

---

### RN 01-2024

- **Admin-Configurable Holidays/Non-Working Days** — admins can create, edit, and delete holidays via UI (select office(s) + date(s) + description); holidays visible on Team Calendar, Work Planner; toast shown when holiday date selected. → [[modules/desk-management]], [[modules/employee-experience]]. Enablement: Default | PB-35169
- **Meal QR Scan Enhancements** — after scanning the cafeteria QR code, a persistent confirmation screen is shown so users can display proof of scan. `restrictMealScanToOne` (default: false — when true, limits to one scan per booking) → [[modules/meal-management]]. Enablement: Default | PB-35170
- **Parking Booking Mandatory** — admins can require all parking users to always create a booking (no ad-hoc parking without a booking). `parkingBookingMandatory` (default: false) → [[modules/parking-management]]. Enablement: Property | PB-35780
- **Buffer Time for Parking Booking (Office Config)** — configurable buffer time before and after booking start/end time during which a new booking cannot be created for the same slot; prevents overlap during travel time. → [[modules/parking-management]]. Enablement: TO ticket | PB-35971
- **Multi-Day Visitor Invitations** — VMS now supports multi-day visitor invites (previously single-day only). → [[modules/visitor-management]]. Enablement: Default (see raw evidence) | PB-35169 context

---

## Linked Raw Evidence

| RN | raw_path |
|----|---------|
| RN 01-2024 | `raw/se-runbook/crawl/files/1ZKsqvx7_cMMGOIPct7f5CRqGt3jg6k81HmDUuqCHfYQ.pptx` |
| RN 02-2024 | `raw/se-runbook/crawl/files/1Zink5hEllFGzcfnH2w9mVgLT0Rg5sht-N99Lst9-sIo.pptx` |
| RN 03&04-2024 | `raw/se-runbook/crawl/files/1FFLlGmvrmUxbMAlIJGyI2cAPiw7V2nLjFKaXsj3DDoA.pptx` |
| RN 05-2024 | `raw/se-runbook/crawl/files/1QVQvlA7eJm4ukuFy31VnPpNrQCTh5dYbZ2fIuXg-JS8.pptx` |
| RN 06-2024 | `raw/se-runbook/crawl/files/1lJmRZRvR6vQ5WbO1sUaNMgkyNDMQUuMIX4DCbg1t1t8.pptx` |
| RN 07-2024 | `raw/se-runbook/crawl/files/1490FMf5X_-GY8_kDCLql9OKhd1FRB2APIMIiIpohluM.pptx` |
| RN 08-2024 | `raw/se-runbook/crawl/files/1YsEfQuvd5VAP5yVoAS1R77hNcrePht5O6ExnXjvnVMo.pptx` |
| RN 10-2024 | `raw/se-runbook/crawl/files/1Wdgiqu8gvBXFqzq4UwE4bs1RfNmCo9n-lXqtyvbwdMg.pptx` |
| RN 11-2024 | `raw/se-runbook/crawl/files/1aFC8bjSekJwN7jjSqly3wc2Wajn62vKLeMQFZ863Ss8.pptx` |
| RN 12-2024 | `raw/se-runbook/crawl/files/11-KBBB0zZmuXor4PFPEd6ZCcBO0JwbDdpV16kWba9N4.pptx` |
| RN 13-2024 | `raw/se-runbook/crawl/files/1SAvyTe1YnqMtnCFbgH5uIpNhis1hk_KDkoMF_pnF_9c.pptx` |
| RN 14-2024 | `raw/se-runbook/crawl/files/15byOJtL3wOnNq1WsBXanawuAaYQGp_yh_aEmqmr4NSY.pptx` |
| RN 15-2024 | `raw/se-runbook/crawl/files/1jHzQXJubOfNdUm1Q-NYRDD629-jGr4zvgUBT9ivVZUU.pptx` |
| RN 16-2024 | `raw/se-runbook/crawl/files/1fmZhcjcBOyxC8Hkk3wmx5ZqBGEXRF4Iypj-LuQfHE6g.pptx` |
