---
type: release-notes
last_updated: 2026-06-29
source: "—"
---

# Release Notes — Index

## How to read this layer

The release-notes history layer is a **dated changelog** ingested from the PM/sales-facing release-note decks. Each per-year page lists what shipped, newest-first, with the properties and SE-ticket enablement steps noted per feature.

**Recency caveat (read before citing anything here):**
- Release notes are a point-in-time changelog. A note saying "property X defaults to false" describes the behaviour at ship time. Later releases or per-customer configuration changes may have altered the default.
- For authoritative current behaviour — including live defaults — consult the relevant [[modules/]] or [[configs/]] pages, and cross-check Jira for recent changes.
- Screenshots in the source decks intentionally excluded from wiki content; they may depict stale or pre-GA UI. The raw `.pptx` files linked at the bottom of each year page are the screenshot source.
- If a release note contradicts a module/config page, the module/config page wins unless the RN is newer and no subsequent wiki update has been made. Such conflicts are flagged inline with ⚠️ on the year page.

## Years

| Year | Page | Status |
|------|------|--------|
| 2026 | [[history/release-notes-2026]] | Done — RN 01-2026 through RN 05-2026 |
| 2025 | [[history/release-notes-2025]] | Done — RN 01-2025 through RN 15-2025 (incl. 09&10 combined) |
| 2024 | [[history/release-notes-2024]] | Done — RN 01-2024 through RN 16-2024 (excl. RN 09 — absent from crawl; RN 03&04 combined) |
| 2023 | — | Pending ingest |
| 2022 | — | Pending ingest |

## 2025 Feature → Module Quick Map

| Feature | RN | Module(s) |
|---------|----|-----------|
| IT Requests for Meeting Room Bookings (Outlook + Dashboard) | RN 01-2025 | [[modules/meeting-rooms]] |
| Preferences Parity (Web & App) | RN 01-2025 | [[modules/employee-experience]] |
| Multi-Day Remote Booking Emails | RN 01-2025 | [[modules/employee-experience]] |
| Access Card SFTP: Check-out Flow | RN 01-2025 | [[modules/access-management]] |
| Flexible Desk Allocation (Multi-Team) | RN 01-2025 | [[modules/desk-management]] |
| Showing Unallocated Desks | RN 01-2025 | [[modules/desk-management]] |
| Hierarchy Search Usability Fix | RN 01-2025 | [[modules/employee-experience]] |
| IT Request Dashboard Enhancements | RN 02-2025 | [[modules/meeting-rooms]] |
| Hierarchy Search Limit Raised to 100 | RN 02-2025 | [[modules/employee-experience]] |
| Partial Desk Name Search | RN 02-2025 | [[modules/desk-management]] |
| Office-Level "Add Desk" + Room Booking Toggle | RN 03-2025 | [[modules/desk-management]], [[modules/meeting-rooms]] |
| QR Scan: Relaxed Office Check-in Mode | RN 03-2025 | [[modules/desk-management]] |
| RBAC for Parking Booking | RN 03-2025 | [[modules/parking-management]] |
| Parking Allocation: Single-Shift Enhancement | RN 03-2025 | [[modules/parking-management]] |
| Parking Allocation Report | RN 04-2025 | [[modules/parking-management]] |
| Payments with Meal Bookings | RN 04-2025 | [[modules/meal-management]] |
| Attendance Tracking on Team Calendar & Work Planner | RN 04-2025 | [[modules/employee-experience]] |
| Weekly Off/Holiday Booking on Work Planner | RN 04-2025 | [[modules/desk-management]], [[modules/employee-experience]] |
| VMS Front Desk: Search by Meeting Title | RN 04-2025 | [[modules/visitor-management]] |
| Access Card SFTP: Use Last Check-out Time | RN 05-2025 | [[modules/access-management]] |
| Admin View for Delegation | RN 05-2025 | [[modules/delegation]] |
| Separation of Office and Desk Check-in | RN 05-2025 | [[modules/desk-management]] |
| CAD Tool: Seat Type Mapping | RN 05-2025 | [[modules/floor-kiosk]] |
| Smarter Desk Search (Booking & Admin Views) | RN 05-2025 | [[modules/desk-management]] |
| Property-Controlled Desk Search & Legend on Admin Pages | RN 05-2025 | [[modules/desk-management]] |
| Individual Resource Check-out (Resource-Level) | RN 06-2025 | [[modules/desk-management]] |
| Cancel All Resources on Allocation Change | RN 06-2025 | [[modules/desk-management]] |
| Meal Day-Wise Availability View | RN 06-2025 | [[modules/meal-management]] |
| Enhanced Resource Release: Preserve Booking Context | RN 06-2025 | [[modules/desk-management]] |
| OTP Validation Property-Controlled in VMS Self Check-in | RN 06-2025 | [[modules/visitor-management]] |
| User Groups ↔ Resource Groups: Booking Form Consumption | RN 07-2025 | [[modules/desk-management]] |
| Stratus Welcome Email for WIS-ETS Sites | RN 07-2025 | [[modules/ets]] |
| Smarter Asset Colouring on Floor Plans (Time-Based) | RN 07-2025 | [[modules/desk-management]] |
| Chargeback Report: Holiday-Aware Calculations | RN 07-2025 | [[modules/meal-management]] |
| Time-Based Desk Allocation: QR Booking Enforcement | RN 07-2025 | [[modules/desk-management]] |
| Tag Management: Smarter Bulk Uploads & Role-Based Access | RN 07-2025 | [[modules/tags-desk-parking]] |
| Meal: Limit Items to "N" Selections | RN 08-2025 | [[modules/meal-management]] |
| Mandatory Booking for Meal Counter QR Scan | RN 08-2025 | [[modules/meal-management]] |
| Employee Home Widgets: Reorder & Resize | RN 08-2025 | [[modules/employee-experience]] |
| Vehicle Parking Report: New Columns | RN 08-2025 | [[modules/parking-management]] |
| Stacked Parking Slot Booking | RN 09&10-2025 | [[modules/parking-management]] |
| Parking Details Hidden When Office Booking Absent | RN 09&10-2025 | [[modules/parking-management]] |
| Desk Icon Revamp on Grid Plan | RN 09&10-2025 | [[modules/desk-management]] |
| Generate Parking QR Codes from UI | RN 09&10-2025 | [[modules/parking-management]] |
| Team & Hierarchy-Wise Desk Utilisation Reports | RN 09&10-2025 | [[modules/desk-management]] |
| Delegate Information in Booking Audits (Mobile) | RN 09&10-2025 | [[modules/delegation]] |
| Custom Branding: Client-Configurable Colors | RN 11-2025 | [[modules/employee-experience]] |
| Floor Kiosk: Auto Check-in for Desk and Room | RN 11-2025 | [[modules/floor-kiosk]] |
| Floor Kiosk: Office Check-in/Check-out Support | RN 11-2025 | [[modules/floor-kiosk]] |
| Enhanced Booking Audits for WorkPlanner | RN 11-2025 | [[modules/desk-management]] |
| Admin Dashboard 2.0: Attendance & Chart Improvements | RN 11-2025 | [[modules/desk-management]] |
| Premises Floor View: Desk Allocation Visibility | RN 11-2025 | [[modules/desk-management]] |
| Access Card Check-In Enhancements | RN 12-2025 | [[modules/access-management]] |
| Priority-Based Parking Slot Auto-Allocation | RN 12-2025 | [[modules/parking-management]] |
| Resource Release Audits in Booking History | RN 12-2025 | [[modules/desk-management]] |
| Improved Error Messaging for MSU Desk Allocation | RN 12-2025 | [[modules/desk-management]] |
| Meeting Rooms Outlook Add-In: Native Rooms Support | RN 12-2025 | [[modules/meeting-rooms]] |
| Vendor Meals Dashboard | RN 13-2025 | [[modules/meal-management]] |
| Proactive Datasync Failure Email Alerts | RN 13-2025 | [[modules/employee-provisioning]] |
| App vs Web Shift Visibility Fix | RN 13-2025 | [[modules/employee-experience]] |
| User Groups ↔ Resource Groups: Employee Booking Workflow | RN 13-2025 | [[modules/desk-management]] |
| Meeting Rooms Mobile: Native-Style Booking Form | RN 14-2025 | [[modules/meeting-rooms]] |
| Floor Kiosk: Email Notifications for Bookings | RN 14-2025 | [[modules/floor-kiosk]] |
| ETS+WIS: Shift Visibility Parity (App vs Web) | RN 14-2025 | [[modules/ets]] |
| `defaultLogoutShiftMinutes` on App & Web | RN 14-2025 | [[modules/ets]] |
| VMS: Configurable Photo Capture on Self Check-in | RN 14-2025 | [[modules/visitor-management]] |
| WorkPlanner: Recurring Booking Support | RN 14-2025 | [[modules/desk-management]] |
| VMS: QR Code Scanning Fix on Android | RN 14-2025 | [[modules/visitor-management]] |
| Admin Dashboard 2.0: Cross-Office Booking Support | RN 15-2025 | [[modules/desk-management]] |
| Locker Booking Workflow | RN 15-2025 | [[modules/desk-management]] |
| Desk Allocation Status File: Clear Error Context | RN 15-2025 | [[modules/desk-management]] |
| Decoupled Office & Desk Check-in/Check-out Audit Logs | RN 15-2025 | [[modules/desk-management]] |
| Access Card Integration with Biostar | RN 15-2025 | [[modules/access-management]] |
| Access Card via API Enhancements | RN 15-2025 | [[modules/access-management]] |

## 2026 Feature → Module Quick Map

| Feature | RN | Module(s) |
|---------|----|-----------|
| OTP Failure Handling & Front Desk Override | RN 01-2026 | [[modules/visitor-management]] |
| Safe Reach DPDP Compliance | RN 01-2026 | [[modules/safe-reach]] |
| VMS Structured Name Capture (Self Check-in) | RN 01-2026 | [[modules/visitor-management]] |
| DigiPass Auto-Send | RN 01-2026 | [[modules/visitor-management]] |
| Safe Reach Report: Checkout Office + Escalation Matrix | RN 01-2026 | [[modules/safe-reach]] |
| Parking Waitlist Expiry | RN 01-2026 | [[modules/parking-management]] |
| Employee Report RFID Column Fix | RN 01-2026 | [[modules/access-management]] |
| VMS Employee Check-in as Visitor | RN 02-2026 | [[modules/visitor-management]] |
| VMS Recurring Invite via Outlook | RN 02-2026 | [[modules/visitor-management]], [[modules/ms-teams-integration]] |
| Parking Slot-Level Description | RN 02-2026 | [[modules/parking-management]] |
| Meeting Rooms + Outlook Add-In Enhancements | RN 02-2026 | [[modules/meeting-rooms]] |
| Floor Kiosk Configurable URL | RN 02-2026 | [[modules/floor-kiosk]] |
| Meeting Rooms UX: All-Offices Filter + Image Upload Guidance | RN 03-2026 | [[modules/meeting-rooms]] |
| Configurable Check-in-by-Time Chip (mobile) | RN 03-2026 | [[modules/employee-experience]] |
| Shift-Based Booking | RN 03-2026 | [[modules/desk-management]], [[modules/employee-experience]] |
| Parking Admin Dashboard 2.0 Fixes | RN 03-2026 | [[modules/parking-management]] |
| Meal Chargeback Report | RN 03-2026 | [[modules/meal-management]] |
| Bulk Upload Template Upgrade | RN 03-2026 | [[modules/desk-management]] |
| Dynamic Label Config for Generic Resources | RN 03-2026 | [[modules/desk-management]] |
| Meeting Room Kiosk Button Visibility (Accessibility) | RN 04-2026 | [[modules/meeting-rooms]] |
| Floor Kiosk Default Booking Duration | RN 04-2026 | [[modules/floor-kiosk]] |
| Meeting Rooms Mobile Timezone Picker | RN 04-2026 | [[modules/meeting-rooms]] |
| Meal Photo Display in Cafeteria Kiosk | RN 04-2026 | [[modules/meal-management]] |
| VMS Office-Level Email Template Support | RN 04-2026 | [[modules/visitor-management]] |
| VMS Face-Based Check-in Mode in Reports | RN 04-2026 | [[modules/visitor-management]] |
| VMS Scroll-Gated NDA Consent (DPDPA) | RN 04-2026 | [[modules/visitor-management]] |
| Room Maintenance Workflow | RN 05-2026 | [[modules/meeting-rooms]] |
| Room Deactivation | RN 05-2026 | [[modules/meeting-rooms]] |
| Room Deactivation Enhancements | RN 05-2026 | [[modules/meeting-rooms]] |
| Floor Kiosk UI Improvements (quick session, auto end) | RN 05-2026 | [[modules/floor-kiosk]] |
| Set Favourite Rooms | RN 05-2026 | [[modules/meeting-rooms]] |
| Show `beginHour`/`endHour` on MR Timeline | RN 05-2026 | [[modules/meeting-rooms]] |
| Meeting Rooms Reports: Room Name Filter | RN 05-2026 | [[modules/meeting-rooms]] |

## 2024 Feature → Module Quick Map

| Feature | RN | Module(s) |
|---------|----|-----------|
| Admin-Configurable Holidays/Non-Working Days | RN 01-2024 | [[modules/desk-management]], [[modules/employee-experience]] |
| Meal QR Scan Enhancements | RN 01-2024 | [[modules/meal-management]] |
| Parking Booking Mandatory | RN 01-2024 | [[modules/parking-management]] |
| Buffer Time for Parking Booking | RN 01-2024 | [[modules/parking-management]] |
| Multi-Day Visitor Invitations | RN 01-2024 | [[modules/visitor-management]] |
| Team Calendar Custom Hierarchy Views | RN 02-2024 | [[modules/employee-experience]] |
| Parking as Standalone Feature | RN 02-2024 | [[modules/parking-management]] |
| VMS on Outlook Add-In | RN 02-2024 | [[modules/visitor-management]], [[modules/ms-teams-integration]] |
| Meeting Rooms + Catering: Default Catering Order Status | RN 02-2024 | [[modules/meeting-rooms]] |
| Meeting Rooms + Catering: Preserve Items on Delivery-Time Change | RN 02-2024 | [[modules/meeting-rooms]] |
| Meeting Rooms + Catering: Edit Flow Status Stability | RN 02-2024 | [[modules/meeting-rooms]] |
| Advance Booking Window — Configurable Opening Time | RN 03&04-2024 | [[modules/desk-management]] |
| Remote Booking Enhancements: Auto-Cancellation + Check-in Buffer | RN 03&04-2024 | [[modules/desk-management]], [[modules/employee-experience]] |
| Meal Feedback | RN 03&04-2024 | [[modules/meal-management]] |
| Host Approval Workflow for Walk-in Visitors | RN 03&04-2024 | [[modules/visitor-management]] |
| Standard Guest Form for Walk-in Visitors (OTP-less) | RN 03&04-2024 | [[modules/visitor-management]] |
| N Bookings per Period (Quota Limit) | RN 05-2024 | [[modules/desk-management]] |
| Project Code Field on Booking Form | RN 05-2024 | [[modules/desk-management]], [[modules/meeting-rooms]] |
| VMS Self Check-in / Checkout Kiosk Workflow | RN 05-2024 | [[modules/visitor-management]] |
| Cisco Integration for Guest Wi-Fi (VMS) | RN 05-2024 | [[modules/visitor-management]] |
| Host Calendar Invite for Visitor Invitation | RN 05-2024 | [[modules/visitor-management]] |
| Release Room: Cancel Associated Meeting | RN 05-2024 | [[modules/meeting-rooms]] |
| Bookings for Someone Else | RN 06-2024 | [[modules/desk-management]], [[modules/employee-experience]] |
| Meeting Rooms + Catering: Email on Order Update | RN 06-2024 | [[modules/meeting-rooms]] |
| Meeting Rooms: Block Calendar for X Minutes | RN 06-2024 | [[modules/meeting-rooms]] |
| VMS: Email to Host on Security Check-in | RN 06-2024 | [[modules/visitor-management]] |
| VMS: Allow Entry for Pending-Status Visitors | RN 06-2024 | [[modules/visitor-management]] |
| Meeting Rooms + Catering: Participant List in Dashboard | RN 06-2024 | [[modules/meeting-rooms]] |
| DigiPass for Meals | RN 07-2024 | [[modules/meal-management]] |
| Meal Bookings via Work Planner | RN 07-2024 | [[modules/meal-management]] |
| Remove Meal Selection on Holiday/Weekly Off | RN 07-2024 | [[modules/meal-management]] |
| Delegation Email Notifications | RN 07-2024 | [[modules/delegation]] |
| Time-Based Desk Allocation | RN 07-2024 | [[modules/desk-management]] |
| Commute Mandatory (Anti Ghost-Booking) | RN 08-2024 | [[modules/ets]], [[modules/employee-experience]] |
| DigiPass Configurable to Specific Resource Types | RN 08-2024 | [[modules/visitor-management]], [[modules/meal-management]], [[modules/parking-management]] |
| Bookings for Someone Else (extended) | RN 08-2024 | [[modules/desk-management]], [[modules/employee-experience]] |
| N-Level Desk Allocation Hierarchy | RN 08-2024 | [[modules/desk-management]] |
| Parking — Prevent Vehicle Info Editing + RBAC | RN 10-2024 | [[modules/parking-management]] |
| Parking — Slot Count in Booking Form Filter | RN 10-2024 | [[modules/parking-management]] |
| Transport Info on Employee Profile — Configurable | RN 10-2024 | [[modules/ets]], [[modules/mobile-app]] |
| Post-Start-Time Booking Cancellation | RN 10-2024 | [[modules/desk-management]], [[modules/meeting-rooms]] |
| Report Scheduling Experience Improvement | RN 10-2024 | [[modules/employee-experience]] |
| Audit for Meeting Rooms | RN 10-2024 | [[modules/meeting-rooms]] |
| Indemnification Support for WiS-ETS Sites | RN 11-2024 | [[modules/ets]], [[modules/employee-experience]] |
| Booking Cancellation Reason Capture | RN 11-2024 | [[modules/desk-management]], [[modules/meeting-rooms]] |
| Limit Meals During Booking Creation | RN 11-2024 | [[modules/meal-management]] |
| Auto Tag Assignment Mapping | RN 11-2024 | [[modules/tags-desk-parking]], [[modules/employee-provisioning]] |
| Delegation on Mobile App | RN 12-2024 | [[modules/delegation]], [[modules/mobile-app]] |
| Accessibility Improvements for Visually-Impaired Users | RN 12-2024 | [[modules/employee-experience]], [[modules/mobile-app]] |
| Team/Hierarchy Legends — Enhanced Visibility | RN 12-2024 | [[modules/desk-management]] |
| VMS Report Enhancements — Column Additions | RN 12-2024 | [[modules/visitor-management]] |
| Invite Visitors on Behalf of Someone Else | RN 12-2024 | [[modules/visitor-management]] |
| Allow Front Desk to Edit Invite End Time | RN 12-2024 | [[modules/visitor-management]] |
| Carbon Footprint Tracking for Parking Commute | RN 13-2024 | [[modules/parking-management]] |
| Office-Level Check-In Mode Configuration | RN 13-2024 | [[modules/desk-management]], [[modules/employee-experience]] |
| Access Card Device-to-Floor Mapping (SFTP) | RN 13-2024 | [[modules/access-management]] |
| Badge Number Field on Front Desk | RN 13-2024 | [[modules/visitor-management]] |
| Front Desk Approval/Rejection of Visitor Entry | RN 13-2024 | [[modules/visitor-management]] |
| Type of Visitor & Flow Info on Front Desk Dashboard | RN 13-2024 | [[modules/visitor-management]] |
| Hide Parking Slot Visibility from Employees | RN 14-2024 | [[modules/parking-management]] |
| Multi and Recurring Booking Enhancements | RN 14-2024 | [[modules/desk-management]] |
| Support for Overlapping Desk Bookings | RN 14-2024 | [[modules/desk-management]] |
| Streamlined Check-in Workflow | RN 14-2024 | [[modules/desk-management]], [[modules/employee-experience]] |
| Client-Configurable Check-In Reminder Templates on MS Teams | RN 14-2024 | [[modules/ms-teams-integration]] |
| Timezone Abbreviations in Booking Emails | RN 14-2024 | [[modules/employee-experience]] |
| External Office and Team-Wise Desk Utilisation APIs | RN 14-2024 | [[modules/desk-management]] |
| RFID Number on Stratus Sites | RN 15-2024 | [[modules/access-management]] |
| API-Based Access Card Integration Enhancements | RN 15-2024 | [[modules/access-management]] |
| Parking ANPR (Automatic Number Plate Recognition) | RN 15-2024 | [[modules/parking-management]] |
| Parking Vehicle Overstay Notifications | RN 15-2024 | [[modules/parking-management]] |
| Office Eligibility Mapping — Transport Restriction | RN 16-2024 | [[modules/ets]], [[modules/employee-experience]] |
| Ad-Hoc Shifts on WiS-ETS Sites (Web) | RN 16-2024 | [[modules/ets]] |
| Admin Dashboard UI Improvements | RN 16-2024 | [[modules/desk-management]] |
| Flexible Desk Allocation for Multi-Team Collaboration | RN 16-2024 | [[modules/desk-management]] |
| Custom Fields in Walk-in Visitor Flow | RN 16-2024 | [[modules/visitor-management]] |
| Invite Cancellation from Front Desk Dashboard | RN 16-2024 | [[modules/visitor-management]] |
