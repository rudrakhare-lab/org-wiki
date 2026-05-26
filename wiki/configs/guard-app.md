---
type: config
module: guard-app-kiosks
servers:
  - in
  - com
last_updated: 2026-05-26
sources:
  in: "[[sources/pms-configs-in-all-wis-configs]]"
  com: "[[sources/pms-configs-com-wis-service-configs]]"
---

# Guard App Service — Config Properties

## Service
Guard App Service. Linked module: [[modules/guard-app-kiosks]].

_Source: [[sources/pms-configs-in-all-wis-configs]] | [[sources/pms-configs-com-wis-service-configs]]_

## Config Comparison

> **Server key:** ✅ = property present in that server's config list | — = absent
> **Description source:** `.com` description preferred; falls back to `.in`, PMS Description Cleaned, then `wis_unique_configs`.
> ⚠️ `undocumented` = no description found in any source — contact the owning team.

| Property Name | .in | .com | Data Type | Description |
|---------------|-----|------|-----------|-------------|
| `enableParkingCheckOutWithOfficeCheckOut` | ✅ | ✅ | BOOLEAN | Controls whether parking checkout is automatically performed along with office checkout. |
| `enableQrCodeForSeatManagement` | ✅ | ✅ | BOOLEAN | Enables QR based validation for check in |
| `enableQrCodeForSeatSanitize` | ✅ | ✅ | BOOLEAN | Enables or disables QR code scanning for seat sanitization. |
| `entryType` | ✅ | ✅ | STRING | (Inferred) Defines the default physical entry categorization code logged during a guard scan. |
| `env` | ✅ | ✅ | JSON | Defines the environment to which the site is mapped. |
| `featureBookingBuids` | ✅ | ✅ | STRING | (Inferred) Defines specific Business Unit IDs (BUIDs) where Guard App feature booking is active. |
| `featurePhoneEnabled` | ✅ | ✅ | DOUBLE | (Inferred) Controls the enablement of phone/dialer features within the Guard App interface. |
| `FLOOR_VIEW` | ✅ | ✅ | JSON | Controls the group type configuration for hierarchy setup on the floor plan. |
| `forecastingColumns` | ✅ | ✅ | JSON | Defines the set of data columns displayed in forecasting reports. |
| `groupTypes` | ✅ | ✅ | JSON | Defines the group types used for hierarchy setup. |
| `guardAppCutOffTime` | ✅ | ✅ | STRING | Defines the cutoff time for guard application actions such as entry validation. |
| `isAutoEntryAllowed` | ✅ | ✅ | BOOLEAN | Automatically switches to the next DigiPass scan mode after the first scan is completed. |
| `isCoreBuid` | ✅ | ✅ | BOOLEAN | Tells the Guard service which BUID is the primary (default) site for that Guard configuration block. |
| `isMultipleScan` | ✅ | ✅ | BOOLEAN | Controls whether a QR code can be scanned multiple times for the same context. |
| `isSendEmailOnHighTemperature` | ✅ | ✅ | BOOLEAN | Sends email notifications to configured stakeholders when an employee's temperature meets or exceeds the maximum threshold during guard app check-in. |
| `isSummedFloorCapacity` | ✅ | ✅ | BOOLEAN | When enabled, the system calculates total seat capacity by summing floor capacities; when disabled, seat capacity can be manually defined. |
| `isTemperatureScanEnabled` | ✅ | ✅ | BOOLEAN | Enables the temperature scan feature. |
| `listOfIpsWithRange` | ✅ | ✅ | LIST | Defines whitelisted IP addresses or IP ranges for office check-in restrictions. |
| `maxTemperatureAllowed` | ✅ | ✅ | DOUBLE | Defines the maximum temperature threshold allowed for entry validation. |
| `minTemperatureAllowed` | ✅ | ✅ | DOUBLE | Defines the minimum temperature threshold allowed for entry validation. |
| `neighbourSeatsRadius` | ✅ | ✅ | INTEGER | Defines the radius within which a seat cannot be booked. |
| `pmsEnabled` | ✅ | ✅ | BOOLEAN | Controls whether the Property Management System (PMS) integration is enabled. |
| `qrImageClientLogoUrl` | ✅ | ✅ | STRING | Controls the URL of the client logo displayed on generated QR codes. |
| `qrImagefooterUrl` | ✅ | ✅ | STRING | Controls the URL of the footer image displayed on generated QR codes. |
| `receiverEmailId` | ✅ | ✅ | LIST | List of email IDs to which notifications or communication should be sent from the Guard App. |
| `scanInterval` | ✅ | ✅ | DOUBLE | Defines the minimum time interval required between consecutive scans. |
| `seatMetricsTimes` | ✅ | ✅ | LIST | Defines configured time intervals used for calculating seat utilization and booking metrics. |
| `seatSanitizeCuttoffInMinute` | ✅ | ✅ | DOUBLE | Defines the seat sanitization cutoff time in minutes. |
| `smsTriggerTime` | ✅ | ✅ | STRING | Defines the configured time at which SMS notifications are triggered. |
| `checkInBookingsType` | — | ✅ | LIST | Controls which booking types are auto-checked-in together when one check-in action happens. |
| `enableCarbonFootprintTrackingInParking` | — | ✅ | BOOLEAN | Enables carbon footprint tracking for employee commutes and displays emissions metrics. |
| `enableOfficeCheckInWithParkingCheckIn` | — | ✅ | BOOLEAN | Controls whether office check-in is automatically completed along with parking check-in. |
| `maintenanceWindow` | — | ✅ | JSON | Controls the maintenance event suggestion window. |
| `roomMaintenanceNotificationEmails` | — | ✅ | LIST | Controls the email recipient list of room maintenance events. |

## .com-only Configs
_5 properties present on the `.com` server but absent from the `.in` config list._

- `checkInBookingsType` — Controls which booking types are auto-checked-in together when one check-in action happens.
- `enableCarbonFootprintTrackingInParking` — Enables carbon footprint tracking for employee commutes and displays emissions metrics.
- `enableOfficeCheckInWithParkingCheckIn` — Controls whether office check-in is automatically completed along with parking check-in.
- `maintenanceWindow` — Controls the maintenance event suggestion window.
- `roomMaintenanceNotificationEmails` — Controls the email recipient list of room maintenance events.

_Last updated: 2026-05-26_
_Source: [[sources/pms-configs-in-all-wis-configs]] | [[sources/pms-configs-com-wis-service-configs]]_
