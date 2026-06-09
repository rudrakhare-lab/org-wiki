---
title: "WIS Seat Booking — Config Properties"
service: WIS-SEAT-BOOKING
total_configs: 35
servers: [in, com]
generated: 2026-06-09
type: config
module: wis-seat-booking
---

# WIS Seat Booking — Config Properties

Auto-generated on 2026-06-09. Total configs: **35**.

| Property | Description | Type | Default | Server |
|----------|-------------|------|---------|--------|
| `amenitiesBulkUpload` | Enables bulk upload flow for amenities | BOOLEAN |  | both |
| `approvalFlowInInWfhEnabled` | Controls whether the approval workflow is enabled for Work From Home bookings. | BOOLEAN |  | both |
| `approvalFlowInWfoEnabled` | Controls whether the approval workflow is enabled for Work From Office bookings. | BOOLEAN |  | both |
| `approvedRequestNotificationEnabled` | Controls whether notifications are sent for approved booking approval requests. | BOOLEAN |  | both |
| `autoExpireBeforeNoOfdays` | - | INTEGER |  | .com only |
| `autoExpireHour` | Defines at what period hour your booking request expires | STRING |  | both |
| `autoRequestApprovalEnabled` | Controls whether booking requests are automatically approved without manual intervention. | BOOLEAN |  | both |
| `bookingApprovalEmailsEnabled` | Controls whether email notifications are sent for booking approvals. | BOOLEAN |  | both |
| `bookingRequestApprovalFlowEnabled` | Controls whether the booking request approval workflow is enabled. | BOOLEAN |  | both |
| `buidsEnabledForSeatBookingPMS` | Defines service availaibility on PMS | LIST |  | both |
| `cancelSchedulesEnabled` | Defines whether it should allow cancellation of commute service | BOOLEAN |  | both |
| `deskTagHeaders` | Headers for desk tag | LIST |  | both |
| `dynamicData` | Defines configurable dynamic fields displayed in the booking form. | LIST |  | .com only |
| `DynamicData` | Defines dynamic field setup for seat booking | LIST |  | .com only |
| `dynamicData / DynamicData` | Defines configurable dynamic fields displayed in the booking form (e.g., Waiter needed, Reimbursement, Allergies, Commute method). |  |  | .in only |
| `employeeTagHeaders` | Headers for employee tag | LIST |  | both |
| `expiredRequestNotificationEnabled` | Controls whether notifications are sent when booking approval requests expire. | BOOLEAN |  | both |
| `expiryCutOffInMinutes` | Controls when a pending seat booking request should be treated as expired | STRING |  | both |
| `expiryNotificationCutOffInMinutes` | Defines how many minutes before a booking approval request expires, used in conjunction with expiryCutOffInMinutes for approval-flow reminders. | STRING |  | both |
| `forecastingColumns` | Defines the column mapping and labels used in forecasting reports. | JSON |  | both |
| `landingPlanHeaders` | Headers for landing plan | LIST |  | both |
| `parkingTagHeaders` | Headers for parking tag | LIST |  | both |
| `pendingRequestsNotificationEnabled` | Controls whether notifications are sent for pending booking approval requests. | BOOLEAN |  | both |
| `rejectedRequestNotificationEnabled` | Controls whether notifications are sent for rejected booking approval requests. | BOOLEAN |  | both |
| `roomTagHeaders` | Headers for room tag | LIST |  | both |
| `seatBookingUrl` | Defines the Seat Booking service URL. | STRING |  | both |
| `seatingPlanHeaders` | Headers for seating plan | LIST |  | both |
| `seatTagHeaders` | Headers for seat tag | LIST |  | .com only |
| `tagsEnabled` | Defines the list of enabled booking tags (e.g. WFO, WFH). | LIST |  | both |
| `TEST` | - | BOOLEAN |  | .com only |
| `TestPropertySeatBooking` | Defines whether the PMS is working on the wisseatbooking service | BOOLEAN |  | both |
| `wfhMonthlyLimit` | Defines the maximum number of Work From Home bookings allowed per month. | INTEGER |  | both |
| `wfhWeeklyLimit` | Defines the maximum number of Work From Home bookings allowed per week. | INTEGER |  | both |
| `wfoMonthlyLimit` | Defines the maximum number of Work From Office bookings allowed per month. | INTEGER |  | both |
| `wfoWeeklyLimit` | Defines the maximum number of Work From Office bookings allowed per week. | INTEGER |  | both |
