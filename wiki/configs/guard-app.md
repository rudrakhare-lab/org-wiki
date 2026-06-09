---
title: "Guard App — Config Properties"
service: GUARD-APP
total_configs: 34
servers: [in, com]
generated: 2026-06-09
type: config
module: guard-app-kiosks
---

# Guard App — Config Properties

Auto-generated on 2026-06-09. Total configs: **34**.

| Property | Description | Type | Default | Server |
|----------|-------------|------|---------|--------|
| `checkInBookingsType` | Controls which booking types are auto-checked-in together when one check-in action happens. | LIST |  | .com only |
| `enableCarbonFootprintTrackingInParking` | Enables carbon footprint tracking for employee commutes and displays emissions metrics. | BOOLEAN |  | .com only |
| `enableOfficeCheckInWithParkingCheckIn` | Controls whether office check-in is automatically completed along with parking check-in. | BOOLEAN |  | .com only |
| `enableParkingCheckOutWithOfficeCheckOut` | Controls whether parking checkout is automatically performed along with office checkout. | BOOLEAN |  | both |
| `enableQrCodeForSeatManagement` | Enables QR based validation for check in | BOOLEAN |  | both |
| `enableQrCodeForSeatSanitize` | Enables or disables QR code scanning for seat sanitization. | BOOLEAN |  | both |
| `entryType` | - | STRING |  | both |
| `env` | Defines the environment to which the site is mapped. | JSON |  | both |
| `featureBookingBuids` | - | STRING |  | both |
| `featurePhoneEnabled` | - | DOUBLE |  | both |
| `FLOOR_VIEW` | Controls the group type configuration for hierarchy setup on the floor plan. | JSON |  | both |
| `forecastingColumns` | Defines the set of data columns displayed in forecasting reports. | JSON |  | both |
| `groupTypes` | Defines the group types used for hierarchy setup. | JSON |  | both |
| `guardAppCutOffTime` | Defines the cutoff time for guard application actions such as entry validation. | STRING |  | both |
| `isAutoEntryAllowed` | Automatically switches to the next DigiPass scan mode after the first scan is completed. | BOOLEAN |  | both |
| `isCoreBuid` | Tells the Guard service which BUID is the primary (default) site for that Guard configuration block. | BOOLEAN |  | both |
| `isMultipleScan` | Controls whether a QR code can be scanned multiple times for the same context. | BOOLEAN |  | both |
| `isSendEmailOnHighTemperature` | Sends email notifications to configured stakeholders when an employee's temperature meets or exceeds the maximum threshold during guard app check-in. | BOOLEAN |  | both |
| `isSummedFloorCapacity` | When enabled, the system calculates total seat capacity by summing floor capacities; when disabled, seat capacity can be manually defined. | BOOLEAN |  | both |
| `isTemperatureScanEnabled` | Enables the temperature scan feature. | BOOLEAN |  | both |
| `listOfIpsWithRange` | Defines whitelisted IP addresses or IP ranges for office check-in restrictions. | LIST |  | both |
| `maintenanceWindow` | Controls the maintenance event suggestion window. | JSON |  | .com only |
| `maxTemperatureAllowed` | Defines the maximum temperature threshold allowed for entry validation. | DOUBLE |  | both |
| `minTemperatureAllowed` | Defines the minimum temperature threshold allowed for entry validation. | DOUBLE |  | both |
| `neighbourSeatsRadius` | Defines the radius within which a seat cannot be booked. | INTEGER |  | both |
| `pmsEnabled` | Controls whether the Property Management System (PMS) integration is enabled. | BOOLEAN |  | both |
| `qrImageClientLogoUrl` | Controls the URL of the client logo displayed on generated QR codes. | STRING |  | both |
| `qrImagefooterUrl` | Controls the URL of the footer image displayed on generated QR codes. | STRING |  | both |
| `receiverEmailId` | List of email IDs to which notifications or communication should be sent from the Guard App. | LIST |  | both |
| `roomMaintenanceNotificationEmails` | Controls the email recipient list of room maintenance events. | LIST |  | .com only |
| `scanInterval` | Defines the minimum time interval required between consecutive scans. | DOUBLE |  | both |
| `seatMetricsTimes` | Defines configured time intervals used for calculating seat utilization and booking metrics. | LIST |  | both |
| `seatSanitizeCuttoffInMinute` | Defines the seat sanitization cutoff time in minutes. | DOUBLE |  | both |
| `smsTriggerTime` | Defines the configured time at which SMS notifications are triggered. | STRING |  | both |
