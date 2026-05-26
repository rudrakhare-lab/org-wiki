---
type: config
module: mobile-app
servers:
last_updated: 2026-05-26
sources:
  in: N/A
  com: N/A
---

# Mobile App Server Config — Config Properties

## Service
Mobile App Server Config. Linked module: [[modules/mobile-app]].

_Source: [[sources/N/A]]_

## Config Comparison

> **Server key:** ✅ = property present in that server's config list | — = absent
> **Description source:** `.com` description preferred; falls back to `.in`, PMS Description Cleaned, then `wis_unique_configs`.
> ⚠️ `undocumented` = no description found in any source — contact the owning team.

| Property Name | .in | .com | Data Type | Description |
|---------------|-----|------|-----------|-------------|
| `bookingListWindowDays` | — | — | — | Defines the number of future days from the current date for which bookings are allowed in the Employee App. |
| `indemnificationDeclineReasons` | — | — | — | Defines the predefined list of reasons available when declining indemnification consent. |
| `isSsoEnable` | — | — | — | Controls whether Single Sign-On (SSO) authentication is enabled for the mobile app. |
| `moveinsyncSenderEmail` | — | — | — | Defines the sender email address used for MoveInSync system communications. |
| `otpExpiryMinutes` | — | — | — | Defines the validity duration (in minutes) of generated OTPs before they expire. |
| `otpSenderEmail` | — | — | — | Defines the sender email address used for OTP-related communications. |
| `redirectUrl` | — | — | — | Defines the URL to which users are redirected after completing actions such as login or authentication. |
| `shiftAllowanceEnabledBuIds` | — | — | — | Defines the list of BUIDs for which shift allowance is enabled. |
| `socGenAllowanceShifts` | — | — | — | Defines the shift types eligible for SocGen allowance benefits (SocGen-only feature). |
| `workinsyncSenderEmail` | — | — | — | Defines the sender email address used for WorkInSync system communications. |

_Last updated: 2026-05-26_
_Source: [[sources/N/A]] | [[sources/N/A]]_
