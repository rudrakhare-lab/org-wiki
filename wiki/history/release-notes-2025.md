---
type: release-notes
year: 2025
last_updated: 2026-06-30
source: "—"
---

# Release Notes — 2025

This page is a **dated changelog**, newest-first — it is the PM/sales source-of-truth for what shipped, not the authoritative current-behaviour reference. For authoritative config defaults and live behaviour, consult the relevant [[modules/]] or [[configs/]] pages. See [[history/release-notes]] for the full recency caveat.

---

### RN 15-2025

> raw evidence: `raw/se-runbook/crawl/files/1_WQvy6XL8l03wj4SdWyjKwjX6aA0G-xeMhubS1O1z94.pptx`

- **Admin Dashboard 2.0: Support for Cross-Office Bookings** — bookings created in an office by employees from other profile offices are now fully visible; desk-utilisation metrics correctly count cross-office bookings. [[modules/desk-management]] | Enablement: default when new admin dashboard is enabled | PB-60997. ⚠️ Superseded by RN 03-2026 (PB-63436) which added further slot-accuracy fixes to the same dashboard — see [[history/release-notes-2026]].

- **Locker Booking Workflow** — employees can reserve lockers as an add-on to their office booking; locker-booking visibility is config-gated. [[modules/desk-management]] | Property: `lockerBookingEnabled` (Emp Exp Common Config) | Enablement: SE ticket | PB noted in source deck (see raw evidence).

- **Desk Allocation Status Update File: Clear Error Context** — bulk-upload status files now include clearer error messages when a desk allocation fails, reducing SE escalations. [[modules/desk-management]] | Enablement: default | PB-60770.

- **Decoupled Office & Desk Check-in/Check-out Audit Logs** — when office and desk check-in are decoupled, each action now publishes its own audit log entry with accurate timestamps and channel; supported events: Desk Check-in/out, WFO Check-in/out. [[modules/desk-management]] | Enablement: default when decoupling is enabled | PB-58560.

- **Access Card Integration with Biostar** — desk bookings automatically define access-validity windows for entry and exit in the Biostar system (API-based push); booking updates immediately reflect in access permissions; entry buffers configurable. [[modules/access-management]] | Enablement: SE ticket (see raw evidence for config details) | PB-59370.

- **Access Card via API Enhancements** — clearer check-in display and improved exception management for API-mode access card integrations. [[modules/access-management]] | Enablement: default | PB noted in source deck (see raw evidence).

---

### RN 14-2025

> raw evidence: `raw/se-runbook/crawl/files/1dsaFMIOG1tXv9g0FLTSBewQo7LTdvT4G5B9yTDcqG1U.pptx`

- **Meeting Rooms Mobile: Native-Style Booking Form** — the meeting-room booking form on mobile is redesigned to match native mobile UI conventions. [[modules/meeting-rooms]] | Enablement: default.

- **Floor Kiosk: Email Notifications for Desk and Room Bookings** — users now receive booking confirmation emails when a desk or room is booked via the Floor Kiosk, identifying it as a kiosk-created booking. [[modules/floor-kiosk]] | Enablement: default.

- **ETS+WIS: Shift Visibility Parity (App vs Web)** — resolves a disparity where shift options visible on web were not shown consistently on the mobile app for ETS-integrated sites. [[modules/ets]] | Enablement: default | PB-58649.

- **`defaultLogoutShiftMinutes` on App & Web** — existing property `defaultLogoutShiftMinutes` is now honoured on both app and web surfaces to ensure shift auto-population for a configurable duration after logout. [[modules/ets]] | Property: `defaultLogoutShiftMinutes` | Enablement: existing property | PB-60351.

- **Visitor Management: Configurable Photo Capture on Self Check-in** — photo capture during visitor self check-in is now property-controlled; can be restricted to Visitor type, Employee type, or both. [[modules/visitor-management]] | Property: `isVisitorPhotoCaptureEnabled` (Array: `{Visitor, Employee}`) | Enablement: SE ticket | PB-60416.

- **WorkPlanner: Recurring Booking Support** — employees can create recurring bookings from the WorkPlanner surface (was desk-only previously); detailed enablement doc linked in source deck. [[modules/desk-management]] | Enablement: SE ticket | PB-60266.

- **Visitor Management: QR Code Scanning Fix on Android** — QR code generation and scanning experience on Android kiosk devices is fixed to achieve parity with iOS; enables reliable badge-based check-ins/check-outs on Android. [[modules/visitor-management]] | Enablement: default | PB-60406.

---

### RN 13-2025

> raw evidence: `raw/se-runbook/crawl/files/13t75A9uMbBXxuXxigL9Zpio46olyUyoTPwnrvBnJ58g.pptx`

- **Vendor Meals Dashboard** — a dedicated dashboard for meal vendors to view and manage meal orders; access controlled by a dedicated privilege. [[modules/meal-management]] | Property: `enableVendorMealDashboard` (TMS Service, Boolean) | Privilege: `vendor_meal_dashboard` | Enablement: SE ticket | PB-53150.

- **Proactive Email Alerts on Client-Side Datasync Failure** — when the datasync service detects a sync failure for a BUID, a configurable email recipient list is notified automatically. [[modules/employee-provisioning]] | Properties: `SYNC_FAILURE_BUID_LIST`, `SYNC_FAILURE_EMAIL_LIST` (DATASYNC_API service via PMS) | Enablement: PMS config.

- **App vs Web Shift Visibility Disparity Fix** — general fix for shift option display inconsistency between app and web (non-ETS context). [[modules/employee-experience]] | Enablement: default.

- **User Groups ↔ Resource Groups: Improved Employee Booking Workflow** — user-group to resource-group mappings are now correctly consumed in the employee booking form; groups are matched and shown in priority order. [[modules/desk-management]] | Property: `userResourceGroupMappingEnabled` | Enablement: SE ticket | PB-59552.

---

### RN 12-2025

> raw evidence: `raw/se-runbook/crawl/files/1V9JAWIRKyBY6IrTYDzUMi6AQ3sJijgaUl-MJfJVHm-g.pptx`

- **Access Card Check-In Enhancements** — improvements to the access-card check-in flow for better reliability and UX (details in source deck). [[modules/access-management]] | Enablement: default | PB-57033.

- **Priority-Based Parking Slot Auto-Allocation** — parking slots are auto-allocated based on a configurable priority order across employee groups or tags. [[modules/parking-management]] | Property: `enablePriorityWiseAutoSlotAllocate` (Booking Rule Engine) | Enablement: SE ticket (mention priority config).

- **Resource Release Audits in Booking History** — when a resource (desk/room/parking) is released, the release event is now recorded in the booking history audit trail. [[modules/desk-management]] | Enablement: default | PB-58592.

- **Improved Error Messaging for MSU Desk Allocation** — clearer error messages shown to MSU (multi-site user) role when a desk allocation is unavailable. [[modules/desk-management]] | Enablement: default for MSU role | PB-55466.

- **Meeting Rooms Outlook Add-In: Native Rooms Support** — the Outlook Add-In now supports the Native WIS Meeting Rooms view (room tags, room allocation, dynamic policy); Outlook 2019 not supported. [[modules/meeting-rooms]] | Property: `IS_WIS_CALENDAR` (Meeting Rooms Service, must be true) | Enablement: publish Add-In Manifest after enabling | PB-59218. ⚠️ This feature was further enhanced in RN 02-2026 (Outlook Add-In enhancements, PB-62938) — see [[history/release-notes-2026]].

---

### RN 11-2025

> raw evidence: `raw/se-runbook/crawl/files/1Izh_YQlnfDzw1sJVjtMHg48wMnayn8u9aJDgJ0b1Glg.pptx`

- **Custom Branding: Client-Configurable Colors Across WIS Modules** — clients can apply custom brand colours across the WorkInSync UI; configured via Emp Exp Common Config. [[modules/employee-experience]] | Property: `enableWisThemeColors` (Emp Exp Common Config) | Enablement: SE ticket.

- **Floor Kiosk: Auto Check-in for Desk and Room Bookings** — the Floor Kiosk can now automatically check in a user when they approach a kiosk with an existing desk or room booking. [[modules/floor-kiosk]] | Property: `autoCheckinEnableFloorKiosk` (Array: `["DESK","ROOM"]`, BU-level, Booking Rule Engine) | Enablement: SE ticket | PB-56933.

- **Floor Kiosk: Office Check-in/Check-out Support** — the Floor Kiosk can now handle office-level check-in and check-out events in addition to desk/room; configurable per office. [[modules/floor-kiosk]] | Property: `floorKioskAllowOfficeCheckin` (Array: `["CHECKIN","CHECKOUT"]`, office-level, Visitor Management Service; default: `[]`) | Enablement: SE ticket | PB-57598.

- **Enhanced Booking Audits for WorkPlanner** — when check-in/check-out is enabled, WorkPlanner bookings now generate accurate audit log entries including timestamps. [[modules/desk-management]] | Enablement: default when check-in/check-out is enabled | PB-57719.

- **Admin Dashboard 2.0: Attendance & Chart Improvements** — attendance metrics and chart rendering improvements in the new admin dashboard (cross-office and time-range accuracy fixes). [[modules/desk-management]] | Enablement: default | PB-57718 & PB-56728.

- **Premises Floor View: Desk Allocation Visibility Enhancements** — admin floor-view pages show more accurate desk allocation states including cross-team and time-based allocation colouring. [[modules/desk-management]] | Enablement: default | PB-56956.

---

### RN 09&10-2025

> raw evidence: `raw/se-runbook/crawl/files/1fAhTrPe7KkTcVlEca0DQd0IAIepSwFgK9OkMBe8cmGo.pptx`

- **Stacked Parking Slot Booking** — employees can book stacked parking slots (tandem/multi-level); availability depends on how parking allocation is set up. [[modules/parking-management]] | Enablement: default when stacked slots are configured in Parking Allocation | PB-56396.

- **Parking Details Hidden When Office Booking Is Absent** — when an employee is marked absent on their office booking, associated parking details are automatically hidden from the view. [[modules/parking-management]] | Enablement: default (Boolean, default: false) | PB-56588.

- **Desk Icon Revamp on Grid Plan** — refreshed desk icon design on the grid floor-plan view for improved clarity. [[modules/desk-management]] | Enablement: default | PB-56702.

- **Generate Parking QR Codes from UI** — admins can now generate QR codes for parking slots directly from the admin UI without needing a manual backend operation. [[modules/parking-management]] | Enablement: default | PB-57039.

- **Team & Hierarchy-Wise Desk Utilisation Reports** — the `DESK_UTILIZATION` report can now be aggregated at team and hierarchy levels (in addition to office), with configurable aggregation levels. [[modules/desk-management]] | Property: `DESK_UTILIZATION` report; `reportAggregationLevels: ["OFFICE","TEAM","HIERARCHY"]` | Enablement: SE ticket | PB-45109.

- **Delegate Information in Booking Audits (Mobile App)** — when a booking is made via a delegate, the delegate's identity is now recorded in the booking audit trail on mobile. [[modules/delegation]] | Enablement: default | PB-56951.

---

### RN 08-2025

> raw evidence: `raw/se-runbook/crawl/files/1oUO8hHxpVmOR-jnyNiUPlltuFUQFRIPS-DOB47G1WxM.pptx`

- **Meal: Limit Items to "N" Selections** — admins can configure a maximum number of meal items a user may select per booking; enforced via config or privilege. [[modules/meal-management]] | Enablement: SE ticket (config value or privilege) | PB-55121.

- **Mandatory Booking Required for Meal Counter QR Scan** — clients can require employees to have an office booking before they can scan the cafeteria counter QR code for meal check-in. [[modules/meal-management]] | Property: `mandatoryBookingRequiredForCounterScan` (office-level, backend config) | Enablement: SE ticket.

- **Employee Home Widgets: Reorder and Resize** — employees can now reorder and resize the widgets on their home dashboard to personalise the view. [[modules/employee-experience]] | Enablement: default | PB-55688.

- **Vehicle Parking Report: New Columns** — additional columns are available in the Vehicle Parking report; admins specify which columns to include via SE ticket. [[modules/parking-management]] | Enablement: SE ticket (specify required columns).

- **Chargeback Report: Holiday-Aware Calculations** — the Chargeback report (PwC custom) now correctly excludes holidays from cost calculations. [[modules/meal-management]] | Enablement: default when Chargeback report is enabled | PB-53019. ⚠️ This feature also appears in RN 07-2025 (same PB-53019) — the RN 08 deck appears to reference the same fix; treat RN 07 as the ship date.

---

### RN 07-2025

> raw evidence: `raw/se-runbook/crawl/files/10qp3tDZH6v65g5hNcde2CiMdgLD6KYA9J2saOs4Q18I.pptx`

- **User Groups ↔ Resource Groups: Booking Form Consumption** — mappings between user groups and resource groups are now correctly consumed on the booking form; relevant groups are shown based on the employee's assigned user group. [[modules/desk-management]] | Enablement: SE ticket (assign privilege to role for user group creation) | PB noted in source deck (see raw evidence).

- **Stratus Welcome Email for WIS-ETS Sites** — the Stratus welcome email flow is now extended to WIS-ETS integrated sites. [[modules/ets]] | Enablement: SE ticket | PB-56750 (original PB-26615).

- **Enhanced Resource Release: Preserve Booking Context Post-Release** — when a resource (desk, room, parking) is auto-released, the booking context (who booked, when, for what) is retained in the audit trail for reporting purposes. [[modules/desk-management]] | Enablement: default | PB-51044. ⚠️ Same fix referenced in RN 06-2025 (PB-51044) — RN 06 is the earlier ship date.

- **Smarter Asset Colouring on Floor Plans (Time-Based Desk Allocation)** — introduced a clear priority logic for floor-plan desk colour when multiple team/hierarchy allocations apply during the same time window. [[modules/desk-management]] | Enablement: default when `enableTimeBasedAllocation = true` | PB-53018.

- **Chargeback Report: Holiday-Aware Calculations** — the Chargeback report correctly excludes holidays from cost calculations (PwC custom report). [[modules/meal-management]] | Enablement: default when Chargeback report is enabled | PB-53019.

- **Time-Based Desk Allocation: QR Desk Booking Enforcement** — when a desk is scanned via QR, time-based allocation rules are now enforced (was previously skipped); includes overnight booking next-day allocation logic; if a booking exists, user can check in directly. [[modules/desk-management]] | Enablement: default when time-based desk allocation is enabled | PB-54918.

- **Tag Management: Smarter Bulk Uploads & Role-Based Access** — newly created tags from the UI now appear in bulk upload templates; tag search and role-based access controls are privilege-gated. [[modules/tags-desk-parking]] | Enablement: privilege-controlled | PB noted in source deck (see raw evidence).

---

### RN 06-2025

> raw evidence: `raw/se-runbook/crawl/files/1L5kO3D4OZcjhzb33fhNxn9FF3FzHorcwGr7xmWmihZM.pptx`

- **Individual Resource Check-out (Resource-Level)** — employees can check out individual resources (desk, room) independently when office and desk check-in are decoupled; extends the `allowOfficeCheckInWithoutDesk` behaviour. [[modules/desk-management]] | Property: `allowOfficeCheckInWithoutDesk` (Booking Rule Engine) | Enablement: SE ticket | PB-54141.

- **Cancel All Resources on Allocation Change** — when a desk allocation changes, all resources associated with the booking (desk, room, parking) can be automatically cancelled to avoid orphaned bookings. [[modules/desk-management]] | Property: `seatAllocationAction = CANCEL_ALL_RESOURCES` | Enablement: SE ticket | PB-51954.

- **Meal Day-Wise Availability View** — employees can see meal availability and a summary view on a day-by-day basis before booking. [[modules/meal-management]] | Property: `enableMealDayWiseAvailability` (Boolean, true) | Enablement: SE ticket | PB-53113.

- **Enhanced Resource Release: Preserve Booking Context Post-Release** — when a desk/room/parking resource is auto-released, booking context is retained in audit logs. [[modules/desk-management]] | Enablement: default | PB-51044.

- **OTP Validation Property-Controlled in VMS Self Check-in** — OTP verification during visitor self check-in is now config-gated; clients with expensive international SMS costs can disable it. [[modules/visitor-management]] | Property: `kioskRequireOTPBeforeRegister` | Enablement: SE ticket | PB noted in source deck (see raw evidence). ⚠️ OTP override handling was further enhanced in RN 01-2026 (`enableOtpOverride`, `failureReasonsOtp`) — see [[history/release-notes-2026]].

---

### RN 05-2025

> raw evidence: `raw/se-runbook/crawl/files/1sshHDOWIBY-IEm0J6yJoy7m1S5K358UH_GVy7-LJOKM.pptx`

- **Access Card via SFTP: Use Last Check-out Time Instead of First** — for SFTP-mode access card integrations, the final check-out swipe of the day is used for official booking records rather than the first. [[modules/access-management]] | Enablement: none (automatic fix) | PB-52218.

- **Admin View for Delegation** — admins can now set delegates on behalf of employees from the Employee Information section, without the delegator needing to log in. [[modules/delegation]] | Property: `enableDelegationForAdmins` (Emp Exp Service, Boolean true/false) | Requires `isDelegationEnabled` | Enablement: SE ticket | PB-51959.

- **Separation of Office and Desk Check-in** — a new config requires a separate desk check-in even if the office booking has already been checked in; prevents automatic desk check-in on WFO. [[modules/desk-management]] | Property: `allowOfficeCheckInWithoutDesk` (Booking Rule Engine, true) | Enablement: SE ticket | PB-51953. ⚠️ This property is also referenced in RN 06-2025 (PB-54141) for individual resource check-out — the two features share the same enabling property.

- **CAD Tool: Seat Type Mapping** — the CAD tool now supports mapping seat types directly from the floor plan upload workflow, enabling more accurate desk categorisation. [[modules/floor-kiosk]] | Enablement: SE ticket | PB-52062.

- **Smarter Desk Search Across Booking & Floor Plan Admin Views** — partial-name desk search improved (e.g., "025" matches "WS025"); results sorted alphabetically. Applies across Employee Booking Form, Premises Floor View, Desk Allocation Floor View. [[modules/desk-management]] | Enablement: default | PB-52060.

- **Property-Controlled Desk Search & Legend on Admin Pages** — desk search on admin floor-view pages is now gated by `showSeatSearchOnAdminPages` (default: false); "Multi-allocated Desk" legend entry only shown when `enableMultiAllocation = ['DESK']`. [[modules/desk-management]] | Property: `showSeatSearchOnAdminPages` (BUID-level, Boolean, default: false) | Enablement: SE ticket | PB-52059.

---

### RN 04-2025

> raw evidence: `raw/se-runbook/crawl/files/1EQLASxeYIhPIfpxtlQHMMVofE0ZjiO_Cb2Hl_Fv8-UU.pptx`

- **Parking Allocation Report** — a new report summarises parking slot allocation across zones/levels with date-range filtering, allocation type (unallocated, allocated, hotseat, blocked), and employee/team attribution. [[modules/parking-management]] | Property: `Parking Allocation Report` (TO ticket) | Enablement: TO ticket | PB-47438.

- **Payments with Meal Bookings** — employees can pay for meals at the time of office booking via an integrated payment gateway (config-based); payments also available retrospectively via Booking History; refunds handled by vendor. [[modules/meal-management]] | Properties: `showMealPaymentCTA`, `enableMealCartView` (enable together) | Enablement: SE ticket | PB-46357 & PB-49901.

- **Improved Attendance Tracking on Team Calendar and Work Planner** — check-in and check-out times of bookings (created by user or admin/manager) are now shown in Team Calendar (day/week view) and Work Planner. [[modules/employee-experience]] | Enablement: default | PB-50984.

- **Allow Weekly Off/Holiday Booking on Work Planner & Team Calendar** — employees can now create bookings on weekly offs or holidays from Work Planner and Team Calendar when the relevant configs are enabled. [[modules/desk-management]] / [[modules/employee-experience]] | Properties: `enableWeeklyOffBookings`, `enableBookingsOnHolidays` | Enablement: SE ticket | PB-50986.

- **Front Desk Search on Meeting Title** — the VMS front-desk search can now search by meeting title, in addition to visitor name/phone; controlled by `controlSearchSections`. [[modules/visitor-management]] | Property: `controlSearchSections` (add `'Meeting Title'`) | Enablement: SE ticket | PB-49636.

---

### RN 03-2025

> raw evidence: `raw/se-runbook/crawl/files/1t4RxONDPjRFv1S1ER5eqNJ6xkhZzy1ksGUVA70yJzcc.pptx`

- **"Add Desk" and New Room Booking: Office-Level Configurability** — desk booking and room booking are now office-level configurations; each option only appears for employees at offices where it is explicitly enabled. [[modules/desk-management]] / [[modules/meeting-rooms]] | Properties: `seatBookingEnabled`, `allowRoomBookingWithOfficeBooking` | Enablement: SE ticket | PB-49825.

- **QR Scan: Relaxed Office Check-in Mode Checks** — a new property limits QR-scan-initiated check-in to the FAB button only, reducing unintended check-ins in QR-scan mode. [[modules/desk-management]] | Property: `restrictScanQROnFabButton` (Booking Rule Engine) | Enablement: SE ticket | PB-49826.

- **RBAC for Parking Booking** — a new privilege (`employee_Parking_Booking`) allows role-based access control for who can create parking bookings. [[modules/parking-management]] | Privilege: `employee_Parking_Booking` | Enablement: SE ticket | PB-49902.

- **Parking Allocation Enhancements for Single-Shift Operations** — past allocation times for the current day can now be configured as valid for single-shift clients, avoiding allocation gaps mid-day. [[modules/parking-management]] | Property: `allowPastAllocationTimesForCurrentDayFor` | Enablement: SE ticket.

---

### RN 02-2025

> raw evidence: `raw/se-runbook/crawl/files/1_HGGOoVUfS8wxUo8QxEec2MgrrjSRUIcQM-N34RqHMw.pptx`

- **IT Request Dashboard Enhancements** — enhancements to the IT Request Dashboard: search by Order ID, Organiser, and Meeting ID; status and office filters; real-time refresh; automated email notifications to organizers; store selection for IT resource items in Outlook bookings. [[modules/meeting-rooms]] | Properties: `IT_REQUEST_OUTLOOK_ADDIN`, `IT_REQUEST_DASHBOARD` | Enablement: SE ticket | PB noted in source deck (see raw evidence). ⚠️ IT Request was first introduced in RN 01-2025; this is a follow-on enhancement.

- **Catering/IT Resource Order Enhancements** — further improvements to ordering flow for catering and IT resources in meeting room bookings (details in source deck). [[modules/meeting-rooms]] | Enablement: details in source deck (see raw evidence).

- **Hierarchy Search Limit Increased to 100** — hierarchy search results increased from 10 to 100; results sorted by hierarchy level for better usability. [[modules/employee-experience]] | Enablement: default | PB-48836.

- **Partial Desk Name Search** — desk search supports partial matches (e.g., "025" finds "WS025"); results sorted by ASCII value for consistency. [[modules/desk-management]] | Enablement: default | PB noted in source deck (see raw evidence). ⚠️ This was further refined in RN 05-2025 (PB-52060) with broader admin-page coverage.

---

### RN 01-2025

> raw evidence: `raw/se-runbook/crawl/files/1VrTE5AB-YMA04snKz0GQR3TfaIibftein_oAdvZ--Rk.pptx`

- **IT Requests for Meeting Room Bookings (Outlook Add-In + Dashboard)** — employees can request IT equipment (projector, mic, speaker, monitor) when creating a meeting room booking in the Outlook Add-In; an IT Request Dashboard centralises management for admins. [[modules/meeting-rooms]] | Properties: `IT_REQUEST_OUTLOOK_ADDIN` (Outlook), `IT_REQUEST_DASHBOARD` (Dashboard) | Enablement: SE ticket | PB-47395. ⚠️ Superseded/enhanced by RN 02-2025 (search, filters, email notifications) — treat this as the initial ship.

- **Preferences Parity Across Web and App** — office selection and desk auto-population now work consistently across web and mobile; manual office changes persist across date changes; preferences take priority when enabled. [[modules/employee-experience]] | Enablement: default when preferences is enabled | PB-48102.

- **Multi-Day Remote Booking Emails** — a consolidated confirmation email is now sent when multiple single-day remote bookings are created in one action, matching the behaviour of bulk office bookings. [[modules/employee-experience]] | Enablement: default | PB-47713.

- **Access Card via SFTP: Check-out Flow** — access card check-out data now flows correctly through the SFTP integration channel; check-out timestamps appear in reports. [[modules/access-management]] | Enablement: default (automatic when SFTP mode is active) | PB-48425.

- **Flexible Desk Allocation for Multi-Team Collaboration** — enhancements to multi-allocation (`enableMultiAllocation = ['DESK']`): multiple teams or employees can be allocated to the same desk across different time windows. [[modules/desk-management]] | Property: `enableMultiAllocation = ['DESK']` | Enablement: SE ticket | PB-48220.

- **Showing Unallocated Desks** — unallocated desks are now visible on the floor plan (previously hidden); improves transparency of available desk inventory. [[modules/desk-management]] | Enablement: default | PB-48294.

- **Hierarchy Search Usability Fix** — hierarchy search result limit increased; results are sorted for better usability. [[modules/employee-experience]] | Enablement: default | PB-48836. ⚠️ Further improved in RN 02-2025 (limit raised to 100, sorted by hierarchy level).

---

## Linked Raw Evidence

| RN | raw_path |
|----|---------|
| RN 01-2025 | `raw/se-runbook/crawl/files/1VrTE5AB-YMA04snKz0GQR3TfaIibftein_oAdvZ--Rk.pptx` |
| RN 02-2025 | `raw/se-runbook/crawl/files/1_HGGOoVUfS8wxUo8QxEec2MgrrjSRUIcQM-N34RqHMw.pptx` |
| RN 03-2025 | `raw/se-runbook/crawl/files/1t4RxONDPjRFv1S1ER5eqNJ6xkhZzy1ksGUVA70yJzcc.pptx` |
| RN 04-2025 | `raw/se-runbook/crawl/files/1EQLASxeYIhPIfpxtlQHMMVofE0ZjiO_Cb2Hl_Fv8-UU.pptx` |
| RN 05-2025 | `raw/se-runbook/crawl/files/1sshHDOWIBY-IEm0J6yJoy7m1S5K358UH_GVy7-LJOKM.pptx` |
| RN 06-2025 | `raw/se-runbook/crawl/files/1L5kO3D4OZcjhzb33fhNxn9FF3FzHorcwGr7xmWmihZM.pptx` |
| RN 07-2025 | `raw/se-runbook/crawl/files/10qp3tDZH6v65g5hNcde2CiMdgLD6KYA9J2saOs4Q18I.pptx` |
| RN 08-2025 | `raw/se-runbook/crawl/files/1oUO8hHxpVmOR-jnyNiUPlltuFUQFRIPS-DOB47G1WxM.pptx` |
| RN 09&10-2025 | `raw/se-runbook/crawl/files/1fAhTrPe7KkTcVlEca0DQd0IAIepSwFgK9OkMBe8cmGo.pptx` |
| RN 11-2025 | `raw/se-runbook/crawl/files/1Izh_YQlnfDzw1sJVjtMHg48wMnayn8u9aJDgJ0b1Glg.pptx` |
| RN 12-2025 | `raw/se-runbook/crawl/files/1V9JAWIRKyBY6IrTYDzUMi6AQ3sJijgaUl-MJfJVHm-g.pptx` |
| RN 13-2025 | `raw/se-runbook/crawl/files/13t75A9uMbBXxuXxigL9Zpio46olyUyoTPwnrvBnJ58g.pptx` |
| RN 14-2025 | `raw/se-runbook/crawl/files/1dsaFMIOG1tXv9g0FLTSBewQo7LTdvT4G5B9yTDcqG1U.pptx` |
| RN 15-2025 | `raw/se-runbook/crawl/files/1_WQvy6XL8l03wj4SdWyjKwjX6aA0G-xeMhubS1O1z94.pptx` |
