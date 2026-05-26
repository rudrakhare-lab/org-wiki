---
type: config
module: employee-experience
servers:
  - in
  - com
last_updated: 2026-05-26
sources:
  in: "[[sources/pms-configs-in-all-wis-configs]]"
  com: "[[sources/pms-configs-com-wis-service-configs]]"
---

# Employee Experience — Internal Config — Config Properties

## Service
Employee Experience — Internal Config. Linked module: [[modules/employee-experience]].

_Source: [[sources/pms-configs-in-all-wis-configs]] | [[sources/pms-configs-com-wis-service-configs]]_

## Config Comparison

> **Server key:** ✅ = property present in that server's config list | — = absent
> **Description source:** `.com` description preferred; falls back to `.in`, PMS Description Cleaned, then `wis_unique_configs`.
> ⚠️ `undocumented` = no description found in any source — contact the owning team.

| Property Name | .in | .com | Data Type | Description |
|---------------|-----|------|-----------|-------------|
| `allowEmployeeToBooKAnySeatInB` | ✅ | ✅ | BOOLEAN | (Inferred) Allows employees to book any seat within their permitted Business Line (BL), bypassing stricter team allocations. |
| `allowEmployeeToBooKAnySeatInBL` | — | — | — | This property controls whether employees are allowed to book any seat assigned to their parent hierarchy. |
| `autoProvisionEnabled` | ✅ | ✅ | BOOLEAN | Enables auto registration process. |
| `bookingEnabledOnTag` | ✅ | ✅ | BOOLEAN | Controls whether booking is allowed based on a tag (e.g., even on weekly off, allow booking for employees/resources carrying a specific tag). |
| `bufferTimeInSecondsOfAarogyaSetuUser` | ✅ | ✅ | INTEGER | Controls the buffer time in seconds applied to Aarogya Setu user validation (covid feature). |
| `cabArrivalIVR` | ✅ | ✅ | JSON | (Inferred) JSON configuration for triggering automated IVR (Interactive Voice Response) phone calls to employees when their cab arrives. |
| `cacheTimeInHoursOfAarogyaSetuUserStatus` | ✅ | ✅ | INTEGER | Controls the cache duration in hours for Aarogya Setu user status (covid feature). |
| `cutoffTimeForSkipWISAppFeedback` | ✅ | ✅ | INTEGER | Defines the interval (in hours) after which the internal app feedback will appear post booking creation. |
| `districts` | ✅ | ✅ | LIST | (Inferred) Defines the list of approved districts/regions mapped to the office for transport routing and hiring boundaries. |
| `employeeStatusModuleEnabled` | ✅ | ✅ | BOOLEAN | When set true, starts using configuration under employeeStatusList. |
| `enableGeofenceCheckForCheckin` | ✅ | ✅ | BOOLEAN | Controls check-in from defined geofence limit from office. |
| `enableTimezoneWithOfficeName` | ✅ | ✅ | BOOLEAN | Controls whether the office name is displayed along with its timezone. |
| `isDynamicFieldsMandatory` | ✅ | ✅ | BOOLEAN | Makes dynamic field mandatory. |
| `madatoryFieldforScheduling` | ✅ | ✅ | LIST | (Inferred) Defines the list of mandatory fields (e.g., ADDRESS, GENDER, OFFICE, MOBILE) required when an employee is scheduling a trip/booking. |
| `meetingRoomsWidgetEnabled` | ✅ | ✅ | BOOLEAN | Controls whether the meeting rooms widget is displayed in the employee home page on web. |
| `parkingReminderEmailEnabled` | ✅ | ✅ | BOOLEAN | Controls whether parking reminder emails are enabled. |
| `radius` | ✅ | ✅ | DOUBLE | (Inferred) Defines the default radial distance limit (e.g., in km) used for transport geofencing or hiring boundaries. |
| `remoteSignCutoffInMinute` | ✅ | ✅ | INTEGER | Cutoff for contactless sign-in for Bus solution. |
| `seatBookingV2` | ✅ | ✅ | BOOLEAN | Enables seat booking v2. |
| `shareRideCallDriver` | ✅ | ✅ | BOOLEAN | (Inferred) Enables the ability for employees in shared rides to call the driver directly from the app. |
| `showLanguageOptionInHamburgerMenu` | ✅ | ✅ | BOOLEAN | (Inferred) Displays a language selection toggle in the mobile app's hamburger/side menu. |
| `showRegistrationNumberInputFieldForParking` | ✅ | ✅ | BOOLEAN | Enables field for entering registration number while selecting parking slots in booking form. |
| `singleShiftOperations` | ✅ | ✅ | BOOLEAN | Removes shift selection on booking form, sets booking time 00:00 to 23:59. Hides time components in Team Calendar (day/week view) and Preferences for single-shift environments. |
| `ssoExpiryInternalEmailRecipients` | ✅ | ✅ | LIST | (Inferred) Defines the internal MoveInSync/DevOps email list that receives alerts when a client's SSO certificate is about to expire. |
| `wfhClockinCutOffInMinute` | ✅ | ✅ | INTEGER | Controls the cutoff time in minutes for allowing WFH clock-in. |
| `wfhType` | ✅ | ✅ | STRING | Controls the default type of Work From Home booking. |
| `listPropertyExample` | — | ✅ | LIST | ⚠️ undocumented |
| `wisDropVerificationFailedEmail` | — | ✅ | BOOLEAN | Controls whether email is triggered when drop verification fails. |
| `wisDropVerificationManualSuccessEmail` | — | ✅ | BOOLEAN | Controls whether email is triggered when drop verification is manually marked successful. |
| `wisFailDropEmailSubject` | — | ✅ | STRING | Controls the email subject template used when Safe Reach drop verification fails. |
| `wisManualSuccessEmailSubject` | — | ✅ | STRING | Controls the email subject template used when Safe Reach confirmation is manually completed. |
| `wisSafeReachCcList` | — | ✅ | LIST | Controls the list of email IDs to be CC'd in Safe Reach communications. |
| `wisSafeReachReportingManagerEnabled` | — | ✅ | BOOLEAN | Controls whether Safe Reach notifications are sent to the reporting manager. |
| `xlEtsBuids` | — | ✅ | LIST | ⚠️ undocumented |

## .com-only Configs
_8 properties present on the `.com` server but absent from the `.in` config list._

- `listPropertyExample` — ⚠️ undocumented
- `wisDropVerificationFailedEmail` — Controls whether email is triggered when drop verification fails.
- `wisDropVerificationManualSuccessEmail` — Controls whether email is triggered when drop verification is manually marked successful.
- `wisFailDropEmailSubject` — Controls the email subject template used when Safe Reach drop verification fails.
- `wisManualSuccessEmailSubject` — Controls the email subject template used when Safe Reach confirmation is manually completed.
- `wisSafeReachCcList` — Controls the list of email IDs to be CC'd in Safe Reach communications.
- `wisSafeReachReportingManagerEnabled` — Controls whether Safe Reach notifications are sent to the reporting manager.
- `xlEtsBuids` — ⚠️ undocumented

## Missing Descriptions
_2 properties have no description in any source (PMS config files, PMS Description Cleaned, or wis_unique_configs)._
Contact the owning service team for documentation.

- `listPropertyExample`
- `xlEtsBuids`

_Last updated: 2026-05-26_
_Source: [[sources/pms-configs-in-all-wis-configs]] | [[sources/pms-configs-com-wis-service-configs]]_
