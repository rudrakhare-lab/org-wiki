---
type: config
module: none
servers:
  - in
  - com
last_updated: 2026-05-26
sources:
  in: "[[sources/pms-configs-in-all-wis-configs]]"
  com: "[[sources/pms-configs-com-wis-service-configs]]"
---

# Project Management Service (PMS) — Config Properties

## Service
Project Management Service (PMS). Linked module: `pms` (no module page yet — needs stub).

_Source: [[sources/pms-configs-in-all-wis-configs]] | [[sources/pms-configs-com-wis-service-configs]]_

## Config Comparison

> **Server key:** ✅ = property present in that server's config list | — = absent
> **Description source:** `.com` description preferred; falls back to `.in`, PMS Description Cleaned, then `wis_unique_configs`.
> ⚠️ `undocumented` = no description found in any source — contact the owning team.

| Property Name | .in | .com | Data Type | Description |
|---------------|-----|------|-----------|-------------|
| `admin` | ✅ | ✅ | LIST | Configures Admin role access. |
| `ADMIN_FRONT_DESK` | ✅ | ✅ | BOOLEAN | Enables Visitor Management for Admin Front Desk. |
| `AUDIT_HISTORY` | ✅ | ✅ | BOOLEAN | Enable Audit history on Sidenav. |
| `BOOKING_APPROVAL` | ✅ | ✅ | BOOLEAN | Enables the Booking Approval page. |
| `BOOKING_HISTORY` | ✅ | ✅ | BOOLEAN | Enables the Booking History option. |
| `BOOKING_UPLOAD_ENABLED` | ✅ | ✅ | BOOLEAN | Enables Booking bulk upload option. |
| `BULK_OPERATION_VISITOR_BOOKING` | ✅ | ✅ | BOOLEAN | Enables bulk upload of visitor lists on the Invite Visitor page. |
| `CATERING_AUDIT_HISTORY` | ✅ | ✅ | BOOLEAN | Enables audit history for Catering Orders. |
| `CATERING_DASHBOARD` | ✅ | ✅ | BOOLEAN | Enables the Catering Dashboard in the sidenav. |
| `COMMUNICATION_CONSOLE_ENABLED` | ✅ | ✅ | BOOLEAN | Enables the Broadcast feature. |
| `configuration.registration.dashboard` | ✅ | ✅ | STRING | Controls whether the employee self-registration experience is exposed via the dashboard for a given site/BUID. |
| `CONFIGURATIONS_ENABLED` | ✅ | ✅ | BOOLEAN | Enables the Configurations page under Settings. |
| `dashboard` | ✅ | ✅ | BOOLEAN | Enables the Dashboard option under Team Manager Dashboard. |
| `DASHBOARD_ENABLED` | ✅ | ✅ | BOOLEAN | Enables the Home Dashboard. |
| `delegation` | ✅ | ✅ | JSON | Enables the Delegation feature in the sidenav. |
| `DESK_AUDIT` | ✅ | ✅ | BOOLEAN | Enables Desk Audit section. |
| `DESK_TAGGING_ENABLED` | ✅ | ✅ | BOOLEAN | Enables the Desk Tagging feature. |
| `employee` | ✅ | ✅ | LIST | Configures ETS Employee role access. |
| `EMPLOYEE` | ✅ | ✅ | LIST | Configures WIS Employee role access. |
| `EMPLOYEE_CHECKIN` | ✅ | ✅ | BOOLEAN | Enables the My Bookings page in the sidenav. |
| `EMPLOYEE_PROFILE_AUDIT` | ✅ | ✅ | BOOLEAN | Enables Employee Profile audit history under Audit History section on sidenav. |
| `EMPLOYEE_TAGGING_ENABLED` | ✅ | ✅ | BOOLEAN | Enables the Employee Tagging feature. |
| `EMPLOYEE_WEB_EXPERIENCE` | ✅ | ✅ | BOOLEAN | Enables the Employee Home page for specified roles. |
| `EMPLOYEES_ENABLED` | ✅ | ✅ | BOOLEAN | Enables the People > Employees page. |
| `ENABLE_HELP_SECTION` | ✅ | ✅ | BOOLEAN | Enables the Help section in the sidenav. |
| `ENABLE_HIERARCHY_PAGE` | ✅ | ✅ | BOOLEAN | Enables the People > Hierarchy page in the sidenav. |
| `ENABLE_MIS` | ✅ | ✅ | BOOLEAN | Enables the switch to ETS option in the sidenav for a specific role. |
| `ENABLE_TAG_MANAGEMENT` | ✅ | ✅ | BOOLEAN | Activates self-service Tag Management module on sidenav. |
| `ENABLE_WIS` | ✅ | ✅ | BOOLEAN | Enables the WorkInSync button in the Transport Dashboard. |
| `FILE_BASED_UPLOAD` | ✅ | ✅ | BOOLEAN | Enables Desk bulk upload option in Seat Management. |
| `FORECAST_ENABLED` | ✅ | ✅ | BOOLEAN | Enables the Desk Forecasting feature. |
| `FRONT_DESK` | ✅ | ✅ | BOOLEAN | Enables Visitor Management for Front Desk. |
| `GLOBAL ADMIN` | ✅ | ✅ | LIST | Configures Global Admin role access. |
| `HR MANAGER` | ✅ | ✅ | LIST | Configures HR Manager role access. |
| `hr_manager` | ✅ | ✅ | LIST | Configures HR Manager role access. |
| `INVITE_VISITOR` | ✅ | ✅ | BOOLEAN | Enables the Visitor Management > Invite Visitor page in the sidenav. |
| `isBookingForNonRegisteredEmpBySpocConfigEnabled` | ✅ | ✅ | BOOLEAN | Controls whether a SPOC is allowed to create bookings for non-registered employees via SPOC flows (Work Planner / Booking for Someone Else flow). |
| `LOAD_COMMON_PROFILE_PAGE` | ✅ | ✅ | BOOLEAN | Enables the default WIS profile page. |
| `MEETING_ROOM_ENABLED` | ✅ | ✅ | BOOLEAN | Enables the Meeting Room option under Team Manager Dashboard. |
| `MSU` | ✅ | ✅ | LIST | Configures MSU role access. |
| `MULTIPLE_BOOKINGS_ENABLED` | ✅ | ✅ | BOOLEAN | Enables creation of multiple bookings from Work Planner. |
| `MY_BOOKINGS_ENABLED` | ✅ | ✅ | BOOLEAN | Enables the My Bookings option under Team Manager Dashboard. |
| `new_seat_booking_url` | ✅ | ✅ | STRING | Defines the new Seat Booking URL. |
| `OFFICE ADMIN` | ✅ | ✅ | LIST | Configures Office Admin role access. |
| `OFFICE_SELECTION_ENABLED` | ✅ | ✅ | BOOLEAN | Enables Office Selection under Team Manager Dashboard. |
| `old_seat_booking_url` | ✅ | ✅ | STRING | Defines the old Seat Booking URL. |
| `PARKING_ALLOCATION` | ✅ | ✅ | BOOLEAN | Enables the Parking Allocation page in the sidenav. |
| `PARKING_TAGGING_ENABLED` | ✅ | ✅ | BOOLEAN | Enables the Parking Tagging option. |
| `PREMISES_ENABLED` | ✅ | ✅ | BOOLEAN | Enables the Premises page in the sidenav. |
| `projectmgr` | ✅ | ✅ | LIST | Configures Project Manager role access. |
| `RECENT_ACTIVITY_ENABLED_FOR_ADMIN` | ✅ | ✅ | BOOLEAN | Enables Recent Activity on the Admin Dashboard. |
| `RECEPTIONIST` | ✅ | ✅ | LIST | Configures Receptionist role access. |
| `REPORTS_ENABLED` | ✅ | ✅ | BOOLEAN | Enables the Reports section. |
| `RESOURCE_APPROVALS_PAGE tooltip` | — | — | — | Controls whether the tooltip is displayed on the Resource Approvals page. |
| `RESOURCE_REQUESTS_PAGE tooltip` | — | — | — | Controls whether the tooltip is displayed on the Resource Requests page. |
| `ROOM_TAGGING_ENABLED` | ✅ | ✅ | BOOLEAN | Enables the Room Tagging option on the Bulk Operations page. |
| `SAFE_REACH_ENABLED` | ✅ | ✅ | BOOLEAN | Enables the Safe Reach dashboard in the WIS sidenav. |
| `SANITISATION_STATUS_ENABLED` | ✅ | ✅ | BOOLEAN | Enables sidenav section of seat sanitization status (covid feature) |
| `SEAT_AUTO_ALLOCATION` | ✅ | ✅ | BOOLEAN | Enables Desk Auto Allocation. |
| `SEAT_FORECASTING_ENABLED tooltip` | — | — | — | Controls whether the tooltip is displayed for the Seat Forecasting feature. |
| `SEAT_MANAGEMENT_ENABLED` | ✅ | ✅ | BOOLEAN | Enables the Seat Bookings option under Team Manager Dashboard. |
| `SEAT_UTILIZATION_ENABLED` | ✅ | ✅ | BOOLEAN | Enables the Desk Utilization option in Seat Management. |
| `SETTINGS_ENABLED` | ✅ | ✅ | BOOLEAN | Enables the Settings option in the sidenav with Configurations and Roles & User Groups pages. |
| `siteadmin` | ✅ | ✅ | LIST | Configures Site Admin role access. |
| `SUPPORT USER EDIT` | ✅ | ✅ | LIST | Configures Support-SSO (mistm) role access. |
| `SUPPORT USER VIEW` | ✅ | ✅ | LIST | Configures Support-SSO (mistm) role access. |
| `TEAM MANAGER` | ✅ | ✅ | LIST | Configures Team Manager role access. |
| `team_manager` | ✅ | ✅ | LIST | Configures Team Manager role access. |
| `transport-dashboard` | ✅ | ✅ | BOOLEAN | Defines the landing dashboard page used for transport operations (legacy or modern) for a given site/BUID. This key is typically configured to point the landing/transport dashboard to the correct ETS dashboard URL, and works together with the ENABLE_NEW_TRANSPORT_DASHBOARD flag. |
| `UPCOMING_VISITOR` | ✅ | ✅ | BOOLEAN | Enables Visitor Management. |
| `VACCINATION_STATUS` | ✅ | ✅ | BOOLEAN | Enables the Vaccination page in the sidenav. |
| `WORK_PLANNER_ENABLED` | ✅ | ✅ | BOOLEAN | Enables the Work Planner option in the sidenav. |
| `Workspace Manager` | ✅ | ✅ | LIST | Configures Workspace Manager role access. |
| `WORKSPACE_MANAGER` | ✅ | ✅ | LIST | Configures Workspace Manager role access. |
| `active-bu` | — | ✅ | STRING | - |
| `ANALYTICS` | — | ✅ | LIST | Enables the Reports page in the sidenav. |
| `Analytics` | — | ✅ | LIST | Enables the Reporting page. |
| `bookingForNonRegisteredEmpBySpoc` | — | ✅ | BOOLEAN | - |
| `Create_Meeting_Room` | — | ✅ | BOOLEAN | Enables meeting room creation button from meeting room planner page. |
| `EAManager` | — | ✅ | LIST | Configures EAManager role access. |
| `ENABLE_MEETING_CATERING` | — | ✅ | BOOLEAN | Enables catering requests option for meeting room bookings. |
| `IMPLEMENTATION_HEAD` | — | ✅ | LIST | Configures Implementation Head role access. |
| `Leadership` | — | ✅ | LIST | Configures Leadership role access. |
| `request` | — | ✅ | BOOLEAN | - |
| `RESOURCE_APPROVALS_PAGE` | — | ✅ | BOOLEAN | For approval Workflow |
| `RESOURCE_REQUESTS_PAGE` | — | ✅ | BOOLEAN | booking request page |
| `ROOM_ALLOCATION_ENABLED` | — | ✅ | BOOLEAN | Enables the Room Allocation option in the Bulk Operations section. |
| `SCHEDULE_MANAGER` | — | ✅ | LIST | Configures Schedule Manager role access. |
| `schedules` | — | ✅ | BOOLEAN | - |
| `SEAT_FORECASTING_ENABLED` | — | ✅ | BOOLEAN | To enable Desk Forecasting Feature |
| `security-supervisor` | — | ✅ | LIST | Configures Security Supervisor role access. |
| `TEAM_MANAGER_COLUMNS` | — | ✅ | STRING | Configures columns on the People > Employees page. |
| `TransportManager` | — | ✅ | LIST | Configures Transport Manager role access. |
| `transportmanager-nobilling` | — | ✅ | LIST | Configures Transport Manager (No Billing) role access. |
| `transportmgr` | — | ✅ | LIST | Configures Transport Manager role access. |
| `VACCINATION_REVIEW` | — | ✅ | BOOLEAN | ⚠️ undocumented |
| `VENDOR_DASHBOARD` | — | ✅ | BOOLEAN | Enables the Vendor Dashboard entry (for cafeteria/meals) in their UI. |

## .com-only Configs
_23 properties present on the `.com` server but absent from the `.in` config list._

- `active-bu` — -
- `ANALYTICS` — Enables the Reports page in the sidenav.
- `Analytics` — Enables the Reporting page.
- `bookingForNonRegisteredEmpBySpoc` — -
- `Create_Meeting_Room` — Enables meeting room creation button from meeting room planner page.
- `EAManager` — Configures EAManager role access.
- `ENABLE_MEETING_CATERING` — Enables catering requests option for meeting room bookings.
- `IMPLEMENTATION_HEAD` — Configures Implementation Head role access.
- `Leadership` — Configures Leadership role access.
- `request` — -
- `RESOURCE_APPROVALS_PAGE` — For approval Workflow
- `RESOURCE_REQUESTS_PAGE` — booking request page
- `ROOM_ALLOCATION_ENABLED` — Enables the Room Allocation option in the Bulk Operations section.
- `SCHEDULE_MANAGER` — Configures Schedule Manager role access.
- `schedules` — -
- `SEAT_FORECASTING_ENABLED` — To enable Desk Forecasting Feature
- `security-supervisor` — Configures Security Supervisor role access.
- `TEAM_MANAGER_COLUMNS` — Configures columns on the People > Employees page.
- `TransportManager` — Configures Transport Manager role access.
- `transportmanager-nobilling` — Configures Transport Manager (No Billing) role access.
- `transportmgr` — Configures Transport Manager role access.
- `VACCINATION_REVIEW` — ⚠️ undocumented
- `VENDOR_DASHBOARD` — Enables the Vendor Dashboard entry (for cafeteria/meals) in their UI.

## Missing Descriptions
_1 properties have no description in any source (PMS config files, PMS Description Cleaned, or wis_unique_configs)._
Contact the owning service team for documentation.

- `VACCINATION_REVIEW`

_Last updated: 2026-05-26_
_Source: [[sources/pms-configs-in-all-wis-configs]] | [[sources/pms-configs-com-wis-service-configs]]_
