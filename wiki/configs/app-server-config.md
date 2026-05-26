---
type: config
module: none
servers:
  - in
  - com
last_updated: 2026-05-26
sources:
  in: "[[sources/pms-configs-com-wis-service-configs]]"
  com: "[[sources/pms-configs-com-wis-service-configs]]"
---

# App Server Config — Config Properties

## Service
App Server Config. Linked module: `app-server-config` (no module page yet — needs stub).

_Source: [[sources/pms-configs-com-wis-service-configs]] | [[sources/pms-configs-com-wis-service-configs]]_

## Config Comparison

> **Server key:** ✅ = property present in that server's config list | — = absent
> **Description source:** `.com` description preferred; falls back to `.in`, PMS Description Cleaned, then `wis_unique_configs`.
> ⚠️ `undocumented` = no description found in any source — contact the owning team.

| Property Name | .in | .com | Data Type | Description |
|---------------|-----|------|-----------|-------------|
| `ACCESS_TOKEN_EXPIRY_IN_SECONDS` | ✅ | ✅ | INTEGER | ⚠️ undocumented |
| `ADHOC_BOOKINGS_BOTTOM_SHEET_DESCRIPTION` | ✅ | ✅ | STRING | ⚠️ undocumented |
| `APP_FEEDBACK_EXPRESSIONS` | ✅ | ✅ | LIST | ⚠️ undocumented |
| `APP_GRAND_LAUNCH_CONTENT` | ✅ | ✅ | LIST | This property defines the context displayed to the user when grand launch is enabled |
| `APP_UPDATE_CONTENT` | ✅ | ✅ | JSON | This property is used to define the content that will be displayed to the user once he click on app update |
| `appVersionSupportedAndroid` | ✅ | ✅ | STRING | ⚠️ undocumented |
| `appVersionSupportedIOS` | ✅ | ✅ | STRING | ⚠️ undocumented |
| `B2B2C` | ✅ | ✅ | JSON | ⚠️ undocumented |
| `BOOKING` | ✅ | ✅ | JSON | This property controls app-side configs for seat and WFH booking rules, checkin cutoff timings, permissions, eligibility settings, and feature configurations within the booking module. |
| `CARBON_SAVINGS_CONTENT` | ✅ | ✅ | JSON | The property will define the context shown to the user on the basis of their carbon savings |
| `CLICK_TO_CALL` | ✅ | ✅ | JSON | ⚠️ undocumented |
| `COMMUNICATIONREGISTRY` | ✅ | ✅ | JSON | ⚠️ undocumented |
| `CONFIGURABLEFEATURE` | ✅ | ✅ | JSON | ⚠️ undocumented |
| `DEVICECONFIGURATIONS` | ✅ | ✅ | JSON | This property controls mobile device authentication, SSO settings, session expiry rules, app security options, and related access configurations. |
| `DYNAMIC_TRIP_FEEDBACK_URL` | ✅ | ✅ | STRING | ⚠️ undocumented |
| `ENGINEERING` | ✅ | ✅ | JSON | ⚠️ undocumented |
| `FAB_ITEMS_DISPLAY_ORDER_LIST` | ✅ | ✅ | LIST | This property controls the FAB button menu in app. |
| `FRESHCHATCONFIGURATIONS` | ✅ | ✅ | JSON | ⚠️ undocumented |
| `GRAND_LAUNCH_ENABLED` | ✅ | ✅ | BOOLEAN | This property will be used to enable the feature grand launch communication |
| `GRAND_LAUNCH_END_TIME` | ✅ | ✅ | STRING | ⚠️ undocumented |
| `GRAND_LAUNCH_START_TIME` | ✅ | ✅ | STRING | ⚠️ undocumented |
| `IVR` | ✅ | ✅ | JSON | ⚠️ undocumented |
| `LATEST_ANDROID_APP_VERSION` | ✅ | ✅ | STRING | Used to define the latest app version |
| `LATEST_IOS_APP_VERSION` | ✅ | ✅ | STRING | Used to define latest ios app version |
| `PRE_SIGNED_URL_EXPIRATION_SECONDS` | ✅ | ✅ | INTEGER | ⚠️ undocumented |
| `privilegedPhoneNumbers` | ✅ | ✅ | LIST | ⚠️ undocumented |
| `PROFILE` | ✅ | ✅ | JSON | This property controls user profile settings, address edit permissions, transport visibility options, profile validation, completion rules, and related display configurations within the application. |
| `REFRESH_TOKEN_EXPIRY_IN_SECONDS` | ✅ | ✅ | INTEGER | ⚠️ undocumented |
| `SAFETY` | ✅ | ✅ | JSON | ⚠️ undocumented |
| `SAFETY_TOOLKIT_MODEL` | ✅ | ✅ | JSON | ⚠️ undocumented |
| `SCHEDULE` | ✅ | ✅ | JSON | This property controls app-side employee shift future scheduling rules, edit/cancel permissions, adhoc and bulk scheduling options, multi-office support, transport integrations, notifications, indemnification rules, and related schedule feature configurations. |
| `SEAT_BELT_NON_FUNCTIONING_AND_REPORTING_REASONS` | ✅ | ✅ | JSON | ⚠️ undocumented |
| `SEAT_BELT_REPORT_BUTTON_COOLDOWN_DURATION_MINUTES` | ✅ | ✅ | INTEGER | ⚠️ undocumented |
| `SHUTTLE_TRACKING_PROPERTIES` | ✅ | ✅ | JSON | ⚠️ undocumented |
| `SOS` | ✅ | ✅ | JSON | ⚠️ undocumented |
| `SPOT` | ✅ | ✅ | JSON | ⚠️ undocumented |
| `TRIP_CARD_FLOW` | ✅ | ✅ | JSON | This property defines the card flow displayed to the user on click of info button on the card |
| `TRIP_DETAILS` | ✅ | ✅ | JSON | ⚠️ undocumented |
| `TRIP_FEEDBACK_MODEL` | ✅ | ✅ | JSON | ⚠️ undocumented |
| `TRIP_HISTORY` | ✅ | ✅ | JSON | ⚠️ undocumented |
| `VEHICLE_TRACKING` | ✅ | ✅ | JSON | ⚠️ undocumented |
| `VERSION_STATS` | ✅ | ✅ | JSON | ⚠️ undocumented |
| `PROJECT_MAPPING_NOT_FOUND_MESSAGE` | ✅ | — | — | update |
| `BUSINESS_UNIT_CITY_MAPPING` | — | ✅ | JSON | ⚠️ undocumented |
| `COUNTRY_CODES_FOR_WHATSAPP_OTP` | — | ✅ | LIST | ⚠️ undocumented |
| `LOG_UPLOAD_RECIPIENTS` | — | ✅ | LIST | ⚠️ undocumented |
| `OFFICE_NAME_MAPPING` | — | ✅ | JSON | ⚠️ undocumented |
| `OFFICE_WISE_SHIFT_MAPPING` | — | ✅ | JSON | ⚠️ undocumented |
| `TRIP_MISMATCH_COMPONENT` | — | ✅ | LIST | ⚠️ undocumented |

## .in-only Configs
_1 properties present on the `.in` server but absent from the `.com` config list._

- `PROJECT_MAPPING_NOT_FOUND_MESSAGE` — update

## .com-only Configs
_6 properties present on the `.com` server but absent from the `.in` config list._

- `BUSINESS_UNIT_CITY_MAPPING` — ⚠️ undocumented
- `COUNTRY_CODES_FOR_WHATSAPP_OTP` — ⚠️ undocumented
- `LOG_UPLOAD_RECIPIENTS` — ⚠️ undocumented
- `OFFICE_NAME_MAPPING` — ⚠️ undocumented
- `OFFICE_WISE_SHIFT_MAPPING` — ⚠️ undocumented
- `TRIP_MISMATCH_COMPONENT` — ⚠️ undocumented

## Missing Descriptions
_36 properties have no description in any source (PMS config files, PMS Description Cleaned, or wis_unique_configs)._
Contact the owning service team for documentation.

- `ACCESS_TOKEN_EXPIRY_IN_SECONDS`
- `ADHOC_BOOKINGS_BOTTOM_SHEET_DESCRIPTION`
- `APP_FEEDBACK_EXPRESSIONS`
- `appVersionSupportedAndroid`
- `appVersionSupportedIOS`
- `B2B2C`
- `BUSINESS_UNIT_CITY_MAPPING`
- `CLICK_TO_CALL`
- `COMMUNICATIONREGISTRY`
- `CONFIGURABLEFEATURE`
- `COUNTRY_CODES_FOR_WHATSAPP_OTP`
- `DYNAMIC_TRIP_FEEDBACK_URL`
- `ENGINEERING`
- `FRESHCHATCONFIGURATIONS`
- `GRAND_LAUNCH_END_TIME`
- `GRAND_LAUNCH_START_TIME`
- `IVR`
- `LOG_UPLOAD_RECIPIENTS`
- `OFFICE_NAME_MAPPING`
- `OFFICE_WISE_SHIFT_MAPPING`
- `PRE_SIGNED_URL_EXPIRATION_SECONDS`
- `privilegedPhoneNumbers`
- `REFRESH_TOKEN_EXPIRY_IN_SECONDS`
- `SAFETY`
- `SAFETY_TOOLKIT_MODEL`
- `SEAT_BELT_NON_FUNCTIONING_AND_REPORTING_REASONS`
- `SEAT_BELT_REPORT_BUTTON_COOLDOWN_DURATION_MINUTES`
- `SHUTTLE_TRACKING_PROPERTIES`
- `SOS`
- `SPOT`
- `TRIP_DETAILS`
- `TRIP_FEEDBACK_MODEL`
- `TRIP_HISTORY`
- `TRIP_MISMATCH_COMPONENT`
- `VEHICLE_TRACKING`
- `VERSION_STATS`

_Last updated: 2026-05-26_
_Source: [[sources/pms-configs-com-wis-service-configs]] | [[sources/pms-configs-com-wis-service-configs]]_
