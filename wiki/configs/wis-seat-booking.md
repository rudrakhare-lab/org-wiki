---
type: config
module: desk-management
servers:
  - in
  - com
last_updated: 2026-05-26
sources:
  in: "[[sources/pms-configs-in-all-wis-configs]]"
  com: "[[sources/pms-configs-com-wis-service-configs]]"
---

# WIS Seat Booking Service — Config Properties

## Service
WIS Seat Booking Service. Linked module: [[modules/desk-management]].

_Source: [[sources/pms-configs-in-all-wis-configs]] | [[sources/pms-configs-com-wis-service-configs]]_

## Config Comparison

> **Server key:** ✅ = property present in that server's config list | — = absent
> **Description source:** `.com` description preferred; falls back to `.in`, PMS Description Cleaned, then `wis_unique_configs`.
> ⚠️ `undocumented` = no description found in any source — contact the owning team.

| Property Name | .in | .com | Data Type | Description |
|---------------|-----|------|-----------|-------------|
| `amenitiesBulkUpload` | ✅ | ✅ | BOOLEAN | Enables bulk upload flow for amenities |
| `approvalFlowInInWfhEnabled` | ✅ | ✅ | BOOLEAN | Controls whether the approval workflow is enabled for Work From Home bookings. |
| `approvalFlowInWfoEnabled` | ✅ | ✅ | BOOLEAN | Controls whether the approval workflow is enabled for Work From Office bookings. |
| `approvedRequestNotificationEnabled` | ✅ | ✅ | BOOLEAN | Controls whether notifications are sent for approved booking approval requests. |
| `autoExpireHour` | ✅ | ✅ | STRING | Defines at what period hour your booking request expires |
| `autoRequestApprovalEnabled` | ✅ | ✅ | BOOLEAN | Controls whether booking requests are automatically approved without manual intervention. |
| `bookingApprovalEmailsEnabled` | ✅ | ✅ | BOOLEAN | Controls whether email notifications are sent for booking approvals. |
| `bookingRequestApprovalFlowEnabled` | ✅ | ✅ | BOOLEAN | Controls whether the booking request approval workflow is enabled. |
| `buidsEnabledForSeatBookingPMS` | ✅ | ✅ | LIST | Defines service availaibility on PMS |
| `cancelSchedulesEnabled` | ✅ | ✅ | BOOLEAN | Defines whether it should allow cancellation of commute service |
| `deskTagHeaders` | ✅ | ✅ | LIST | Headers for desk tag |
| `employeeTagHeaders` | ✅ | ✅ | LIST | Headers for employee tag |
| `expiredRequestNotificationEnabled` | ✅ | ✅ | BOOLEAN | Controls whether notifications are sent when booking approval requests expire. |
| `expiryCutOffInMinutes` | ✅ | ✅ | STRING | Controls when a pending seat booking request should be treated as expired |
| `expiryNotificationCutOffInMinutes` | ✅ | ✅ | STRING | Defines how many minutes before a booking approval request expires, used in conjunction with expiryCutOffInMinutes for approval-flow reminders. |
| `forecastingColumns` | ✅ | ✅ | JSON | Defines the column mapping and labels used in forecasting reports. |
| `landingPlanHeaders` | ✅ | ✅ | LIST | Headers for landing plan |
| `parkingTagHeaders` | ✅ | ✅ | LIST | Headers for parking tag |
| `pendingRequestsNotificationEnabled` | ✅ | ✅ | BOOLEAN | Controls whether notifications are sent for pending booking approval requests. |
| `rejectedRequestNotificationEnabled` | ✅ | ✅ | BOOLEAN | Controls whether notifications are sent for rejected booking approval requests. |
| `roomTagHeaders` | ✅ | ✅ | LIST | Headers for room tag |
| `seatBookingUrl` | ✅ | ✅ | STRING | Defines the Seat Booking service URL. |
| `seatingPlanHeaders` | ✅ | ✅ | LIST | Headers for seating plan |
| `tagsEnabled` | ✅ | ✅ | LIST | Defines the list of enabled booking tags (e.g. WFO, WFH). |
| `TestPropertySeatBooking` | ✅ | ✅ | BOOLEAN | Defines whether the PMS is working on the wisseatbooking service |
| `wfhMonthlyLimit` | ✅ | ✅ | INTEGER | Defines the maximum number of Work From Home bookings allowed per month. |
| `wfhWeeklyLimit` | ✅ | ✅ | INTEGER | Defines the maximum number of Work From Home bookings allowed per week. |
| `wfoMonthlyLimit` | ✅ | ✅ | INTEGER | Defines the maximum number of Work From Office bookings allowed per month. |
| `wfoWeeklyLimit` | ✅ | ✅ | INTEGER | Defines the maximum number of Work From Office bookings allowed per week. |
| `dynamicData / DynamicData` | ✅ | — | — | Defines configurable dynamic fields displayed in the booking form (e.g., Waiter needed, Reimbursement, Allergies, Commute method). |
| `autoExpireBeforeNoOfdays` | — | ✅ | INTEGER | - |
| `dynamicData` | — | ✅ | LIST | Defines configurable dynamic fields displayed in the booking form. |
| `DynamicData` | — | ✅ | LIST | Defines dynamic field setup for seat booking |
| `seatTagHeaders` | — | ✅ | LIST | Headers for seat tag |
| `TEST` | — | ✅ | BOOLEAN | - |

## .in-only Configs
_1 properties present on the `.in` server but absent from the `.com` config list._

- `dynamicData / DynamicData` — Defines configurable dynamic fields displayed in the booking form (e.g., Waiter needed, Reimbursement, Allergies, Commute method).

## .com-only Configs
_5 properties present on the `.com` server but absent from the `.in` config list._

- `autoExpireBeforeNoOfdays` — -
- `dynamicData` — Defines configurable dynamic fields displayed in the booking form.
- `DynamicData` — Defines dynamic field setup for seat booking
- `seatTagHeaders` — Headers for seat tag
- `TEST` — -

_Last updated: 2026-05-26_
_Source: [[sources/pms-configs-in-all-wis-configs]] | [[sources/pms-configs-com-wis-service-configs]]_
