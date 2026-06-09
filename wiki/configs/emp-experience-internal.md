---
title: "Emp Exp Internal Config — Config Properties"
service: EMP-EXP-INTERNAL-CONFIG
total_configs: 33
servers: [in, com]
generated: 2026-06-09
type: config
module: employee-experience
---

# Emp Exp Internal Config — Config Properties

Auto-generated on 2026-06-09. Total configs: **33**.

| Property | Description | Type | Default | Server |
|----------|-------------|------|---------|--------|
| `allowEmployeeToBooKAnySeatInB` | - | BOOLEAN |  | both |
| `autoProvisionEnabled` | Enables auto registration process. | BOOLEAN |  | both |
| `bookingEnabledOnTag` | Controls whether booking is allowed based on a tag (e.g., even on weekly off, allow booking for employees/resources carrying a specific tag). | BOOLEAN |  | both |
| `bufferTimeInSecondsOfAarogyaSetuUser` | Controls the buffer time in seconds applied to Aarogya Setu user validation (covid feature). | INTEGER |  | both |
| `cabArrivalIVR` | - | JSON |  | both |
| `cacheTimeInHoursOfAarogyaSetuUserStatus` | Controls the cache duration in hours for Aarogya Setu user status (covid feature). | INTEGER |  | both |
| `cutoffTimeForSkipWISAppFeedback` | Defines the interval (in hours) after which the internal app feedback will appear post booking creation. | INTEGER |  | both |
| `districts` | - | LIST |  | both |
| `employeeStatusModuleEnabled` | When set true, starts using configuration under employeeStatusList. | BOOLEAN |  | both |
| `enableGeofenceCheckForCheckin` | Controls check-in from defined geofence limit from office. | BOOLEAN |  | both |
| `enableTimezoneWithOfficeName` | Controls whether the office name is displayed along with its timezone. | BOOLEAN |  | both |
| `isDynamicFieldsMandatory` | Makes dynamic field mandatory. | BOOLEAN |  | both |
| `listPropertyExample` | - | LIST |  | .com only |
| `madatoryFieldforScheduling` | - | LIST |  | both |
| `meetingRoomsWidgetEnabled` | Controls whether the meeting rooms widget is displayed in the employee home page on web. | BOOLEAN |  | both |
| `parkingReminderEmailEnabled` | Controls whether parking reminder emails are enabled. | BOOLEAN |  | both |
| `radius` | - | DOUBLE |  | both |
| `remoteSignCutoffInMinute` | Cutoff for contactless sign-in for Bus solution. | INTEGER |  | both |
| `seatBookingV2` | Enables seat booking v2. | BOOLEAN |  | both |
| `shareRideCallDriver` | - | BOOLEAN |  | both |
| `showLanguageOptionInHamburgerMenu` | - | BOOLEAN |  | both |
| `showRegistrationNumberInputFieldForParking` | Enables field for entering registration number while selecting parking slots in booking form. | BOOLEAN |  | both |
| `singleShiftOperations` | Removes shift selection on booking form, sets booking time 00:00 to 23:59. Hides time components in Team Calendar (day/week view) and Preferences for single-shift environments. | BOOLEAN |  | both |
| `ssoExpiryInternalEmailRecipients` | - | LIST |  | both |
| `wfhClockinCutOffInMinute` | Controls the cutoff time in minutes for allowing WFH clock-in. | INTEGER |  | both |
| `wfhType` | Controls the default type of Work From Home booking. | STRING |  | both |
| `wisDropVerificationFailedEmail` | Controls whether email is triggered when drop verification fails. | BOOLEAN |  | .com only |
| `wisDropVerificationManualSuccessEmail` | Controls whether email is triggered when drop verification is manually marked successful. | BOOLEAN |  | .com only |
| `wisFailDropEmailSubject` | Controls the email subject template used when Safe Reach drop verification fails. | STRING |  | .com only |
| `wisManualSuccessEmailSubject` | Controls the email subject template used when Safe Reach confirmation is manually completed. | STRING |  | .com only |
| `wisSafeReachCcList` | Controls the list of email IDs to be CC'd in Safe Reach communications. | LIST |  | .com only |
| `wisSafeReachReportingManagerEnabled` | Controls whether Safe Reach notifications are sent to the reporting manager. | BOOLEAN |  | .com only |
| `xlEtsBuids` | - | LIST |  | .com only |
