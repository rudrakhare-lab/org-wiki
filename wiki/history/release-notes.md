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
| 2024 | — | Pending ingest |
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
