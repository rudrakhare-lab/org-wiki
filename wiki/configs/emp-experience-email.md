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

# Employee Experience — Email Service — Config Properties

## Service
Employee Experience — Email Service. Linked module: [[modules/employee-experience]].

_Source: [[sources/pms-configs-in-all-wis-configs]] | [[sources/pms-configs-com-wis-service-configs]]_

## Config Comparison

> **Server key:** ✅ = property present in that server's config list | — = absent
> **Description source:** `.com` description preferred; falls back to `.in`, PMS Description Cleaned, then `wis_unique_configs`.
> ⚠️ `undocumented` = no description found in any source — contact the owning team.

| Property Name | .in | .com | Data Type | Description |
|---------------|-----|------|-----------|-------------|
| `CAB_ARRIVAL_MESSAGE_FOR_NOTIFICATION` | ✅ | ✅ | STRING | The push notification text sent to an employee when their cab reaches the pickup point (includes driver wait time). |
| `CAB_ARRIVAL_TITLE_FOR_NOTIFICATION` | ✅ | ✅ | STRING | The title/header for the cab arrival push notification. |
| `LOGOUT_CANCELLED_HEADER` | ✅ | ✅ | STRING | The subject line/header for the automatic logout cancellation notification. |
| `LOGOUT_CANCELLED_MESSAGE` | ✅ | ✅ | STRING | The body text for the automatic logout cancellation push notification. |
| `LOGOUT_SCHEDULE_CANCELLATION` | ✅ | ✅ | STRING | Defines the email template notifying an employee that their Evening (Logout) cab was auto-canceled because they didn't show up for their Morning (Login) cab. |
| `MASS_MAIL_SENDER_LIST` | ✅ | ✅ | STRING | Mass mail sender list. |
| `MONTHLY_NO_SHOW_ACTION_EMAIL` | ✅ | ✅ | STRING | Defines the penalty email template tied to exceeding the monthly No-Show limit. |
| `MONTHLY_NO_SHOW_WARNING_EMAIL` | ✅ | ✅ | STRING | Defines the warning email template specifically tied to the monthly No-Show threshold (rather than a rolling date range). |
| `NO_SHOW_ACTION_AT_MONTH_END_BANNER_MESSAGE` | ✅ | ✅ | STRING | The warning banner displayed inside the employee app regarding impending month-end No-Show penalties. |
| `NO_SHOW_ACTION_EMAIL` | ✅ | ✅ | STRING | Defines the email template notifying an employee that their future schedules have been deleted and/or scheduling rights revoked due to exceeding the No-Show limit. |
| `NO_SHOW_AUTO_APPROVAL_EMAIL` | ✅ | ✅ | STRING | Defines the email template notifying an employee that their transport scheduling rights have been successfully restored. |
| `NO_SHOW_POLICY_RE_INSTANTIATION_EMAIL` | ✅ | ✅ | STRING | Defines the email template sent to a manager/admin requesting approval to restore an employee's transport rights after a suspension. |
| `NO_SHOW_WARNING_EMAIL` | ✅ | ✅ | STRING | Defines the email template warning an employee that they are approaching the maximum allowed No-Shows before penalties apply. |
| `OFFICE_TO_HOME_DISTANCE_VALIDATION_FAILED_MESSAGE` | ✅ | ✅ | STRING | Error message displayed when the actual driving route distance exceeds the company's allowed limit. |
| `RADIAL_DISTANCE_VALIDATION_FAILED_MESSAGE` | ✅ | ✅ | STRING | Error message displayed when an employee's address exceeds the maximum allowed straight-line (radial) distance from the office. |
| `RESTRICTED_AREA_VALIDATION_FAILED_MESSAGE` | ✅ | ✅ | STRING | Error message displayed when an employee tries to book a cab to/from a blacklisted zone (e.g., forests, water bodies, unsafe areas). |
| `SCHEDULE_REMINDER_NOTIFICATION_BODY` | ✅ | ✅ | STRING | The body text for the commute schedule reminder notification. |
| `SCHEDULE_REMINDER_NOTIFICATION_SUBJECT` | ✅ | ✅ | STRING | The subject line reminding an employee to create their commute schedule before the cutoff time. |
| `SEAT_BELT_NON_COMPLIANCE_EMAIL_SUBJECT` | ✅ | ✅ | STRING | The subject line for the automated safety alert regarding seatbelt violations. |
| `SEAT_BELT_NON_COMPLIANCE_EMAIL_TEMPLATE` | ✅ | ✅ | STRING | Defines the warning email template sent to employees flagged by the vehicle's monitoring system for not wearing a seatbelt. |
| `SPECIAL_SCHEDULE_MESSAGE_TEMPLATE` | ✅ | ✅ | STRING | The default body text for "On-demand" cab booking notifications. |
| `SPECIAL_SCHEDULE_TITLE_TEMPLATE` | ✅ | ✅ | STRING | The default header for ad-hoc or "On-demand" cab booking notifications. |
| `ssoExpiryEmailBodyTemplate` | ✅ | ✅ | STRING | Defines the email template warning IT admins of an impending SSO certificate expiration (prevents login outages). |
| `ssoExpiryEmailHeaderTemplate` | ✅ | ✅ | STRING | Subject line for the initial warning email that the site's SSO (Single Sign-On) metadata file is expiring soon. |
| `ssoExpiryFollowUpEmailBodyTemplate` | ✅ | ✅ | STRING | Defines the follow-up email template for SSO expiration. |
| `ssoExpiryFollowUpEmailHeaderTemplate` | ✅ | ✅ | STRING | Subject line for the urgent follow-up warning regarding SSO expiration. |
| `TRANSPORT_BOUNDARY_VALIDATION_FAILED_MESSAGE` | ✅ | ✅ | STRING | Error message displayed when an employee tries to set a home address outside the company's approved transport geofence. |
| `NO_SHOW_PERMISSION_ACTION_EMAIL` | ✅ | — | — | Defines the email template notifying an employee of the Approved/Rejected status of their No-Show enforcement appeal. |
| `employeeDeactivationEmailSubject` | — | ✅ | STRING | ⚠️ undocumented |
| `FELLOW_PASSENGER_BOARDED_HEADER` | — | ✅ | STRING | ⚠️ undocumented |
| `FELLOW_PASSENGER_NO_SHOW_HEADER` | — | ✅ | STRING | ⚠️ undocumented |
| `MONTH_END_NO_SHOW_ACTION_EMAIL` | — | ✅ | STRING | ⚠️ undocumented |
| `MONTH_END_NO_SHOW_ACTION_EMAIL_SUBJECT` | — | ✅ | STRING | ⚠️ undocumented |
| `MONTH_END_NO_SHOW_FUTURE_SCHEDULE_REMOVED_MESSAGE` | — | ✅ | STRING | ⚠️ undocumented |
| `MONTH_END_NO_SHOW_FUTURE_SCHEDULES_REMOVED_TITLE` | — | ✅ | STRING | ⚠️ undocumented |
| `MONTH_END_NO_SHOW_SCHEDULE_EDIT_PERMISSION_REVOKED_MESSAGE` | — | ✅ | STRING | ⚠️ undocumented |
| `MONTH_END_NO_SHOW_SCHEDULE_EDIT_PERMISSION_REVOKED_TITLE` | — | ✅ | STRING | ⚠️ undocumented |
| `MONTHLY_NO_SHOW_FUTURE_SCHEDULES_REMOVED_MESSAGE` | — | ✅ | STRING | ⚠️ undocumented |
| `MONTHLY_NO_SHOW_SCHEDULE_EDIT_PERMISSION_REVOKED_MESSAGE` | — | ✅ | STRING | ⚠️ undocumented |
| `MONTHLY_NO_SHOW_WARNING_MESSAGE` | — | ✅ | STRING | ⚠️ undocumented |
| `NO_SHOW_ACTION_EMAIL_AT_MONTH_END_SUBJECT` | — | ✅ | STRING | ⚠️ undocumented |
| `NO_SHOW_ACTION_EMAIL_FUTURE_SCHEDULE_REMOVAL_AND_SCHEDULE_EDIT_REVOKED_SUBJECT` | — | ✅ | STRING | ⚠️ undocumented |
| `NO_SHOW_ACTION_EMAIL_FUTURE_SCHEDULE_REMOVAL_SUBJECT` | — | ✅ | STRING | ⚠️ undocumented |
| `NO_SHOW_AUTO_APPROVAL_SUBJECT` | — | ✅ | STRING | ⚠️ undocumented |
| `NO_SHOW_EMPLOYEE_BOARDED_NOTIFICATION` | — | ✅ | STRING | ⚠️ undocumented |
| `NO_SHOW_FUTURE_SCHEDULES_REMOVED_MESSAGE` | — | ✅ | STRING | ⚠️ undocumented |
| `NO_SHOW_FUTURE_SCHEDULES_REMOVED_TITLE` | — | ✅ | STRING | ⚠️ undocumented |
| `NO_SHOW_SCHEDULE_EDIT_PERMISSION_REVOKED_MESSAGE` | — | ✅ | STRING | ⚠️ undocumented |
| `NO_SHOW_SCHEDULE_EDIT_PERMISSION_REVOKED_TITLE` | — | ✅ | STRING | ⚠️ undocumented |
| `NO_SHOW_WARNING_EMAIL_SUBJECT` | — | ✅ | STRING | ⚠️ undocumented |
| `NO_SHOW_WARNING_MESSAGE` | — | ✅ | STRING | ⚠️ undocumented |
| `NO_SHOW_WARNING_TITLE` | — | ✅ | STRING | ⚠️ undocumented |
| `noShowActionAtMonthEndBannerMessage` | — | ✅ | STRING | ⚠️ undocumented |
| `PLANNED_EMPLOYEE_BOARDED_NOTIFICATION` | — | ✅ | STRING | ⚠️ undocumented |
| `recurringBookingCreatorCancelTemplate` | — | ✅ | STRING | Template for recurring booking cancel email for creator. |
| `recurringBookingCreatorCreateTemplate` | — | ✅ | STRING | Template for work planner recurring booking creation email. |
| `recurringBookingCreatorUpdateTemplate` | — | ✅ | STRING | Template for recurring workplanner booking update email. |
| `REQUEST_APPROVAL_SUBJECT` | — | ✅ | STRING | Stratus access request subject. |
| `REQUEST_APPROVAL_TEMPLATE` | — | ✅ | STRING | Mail request to a list of approvers. |
| `REQUEST_APPROVED_SUBJECT` | — | ✅ | STRING | Admins approved support user request subject. |
| `REQUEST_APPROVED_TEMPLATE` | — | ✅ | STRING | Request approved email template to support user. |
| `REQUEST_REJECTED_SUBJECT` | — | ✅ | STRING | Stratus support user request rejected email subject. |
| `REQUEST_REJECTED_TEMPLATE` | — | ✅ | STRING | Stratus support user request rejection template. |
| `SEAT_ALLOCATION_COMMUNICATION_BODY` | — | ✅ | STRING | Allocation details email body HTML. |
| `SEAT_ALLOCATION_COMMUNICATION_HEADER` | — | ✅ | STRING | Allocation details email subject. |
| `SUPPORT_USER_ADMINS_LIST` | — | ✅ | LIST | List of admins who will receive the approval request mail. |

## .in-only Configs
_1 properties present on the `.in` server but absent from the `.com` config list._

- `NO_SHOW_PERMISSION_ACTION_EMAIL` — Defines the email template notifying an employee of the Approved/Rejected status of their No-Show enforcement appeal.

## .com-only Configs
_38 properties present on the `.com` server but absent from the `.in` config list._

- `employeeDeactivationEmailSubject` — ⚠️ undocumented
- `FELLOW_PASSENGER_BOARDED_HEADER` — ⚠️ undocumented
- `FELLOW_PASSENGER_NO_SHOW_HEADER` — ⚠️ undocumented
- `MONTH_END_NO_SHOW_ACTION_EMAIL` — ⚠️ undocumented
- `MONTH_END_NO_SHOW_ACTION_EMAIL_SUBJECT` — ⚠️ undocumented
- `MONTH_END_NO_SHOW_FUTURE_SCHEDULE_REMOVED_MESSAGE` — ⚠️ undocumented
- `MONTH_END_NO_SHOW_FUTURE_SCHEDULES_REMOVED_TITLE` — ⚠️ undocumented
- `MONTH_END_NO_SHOW_SCHEDULE_EDIT_PERMISSION_REVOKED_MESSAGE` — ⚠️ undocumented
- `MONTH_END_NO_SHOW_SCHEDULE_EDIT_PERMISSION_REVOKED_TITLE` — ⚠️ undocumented
- `MONTHLY_NO_SHOW_FUTURE_SCHEDULES_REMOVED_MESSAGE` — ⚠️ undocumented
- `MONTHLY_NO_SHOW_SCHEDULE_EDIT_PERMISSION_REVOKED_MESSAGE` — ⚠️ undocumented
- `MONTHLY_NO_SHOW_WARNING_MESSAGE` — ⚠️ undocumented
- `NO_SHOW_ACTION_EMAIL_AT_MONTH_END_SUBJECT` — ⚠️ undocumented
- `NO_SHOW_ACTION_EMAIL_FUTURE_SCHEDULE_REMOVAL_AND_SCHEDULE_EDIT_REVOKED_SUBJECT` — ⚠️ undocumented
- `NO_SHOW_ACTION_EMAIL_FUTURE_SCHEDULE_REMOVAL_SUBJECT` — ⚠️ undocumented
- `NO_SHOW_AUTO_APPROVAL_SUBJECT` — ⚠️ undocumented
- `NO_SHOW_EMPLOYEE_BOARDED_NOTIFICATION` — ⚠️ undocumented
- `NO_SHOW_FUTURE_SCHEDULES_REMOVED_MESSAGE` — ⚠️ undocumented
- `NO_SHOW_FUTURE_SCHEDULES_REMOVED_TITLE` — ⚠️ undocumented
- `NO_SHOW_SCHEDULE_EDIT_PERMISSION_REVOKED_MESSAGE` — ⚠️ undocumented
- `NO_SHOW_SCHEDULE_EDIT_PERMISSION_REVOKED_TITLE` — ⚠️ undocumented
- `NO_SHOW_WARNING_EMAIL_SUBJECT` — ⚠️ undocumented
- `NO_SHOW_WARNING_MESSAGE` — ⚠️ undocumented
- `NO_SHOW_WARNING_TITLE` — ⚠️ undocumented
- `noShowActionAtMonthEndBannerMessage` — ⚠️ undocumented
- `PLANNED_EMPLOYEE_BOARDED_NOTIFICATION` — ⚠️ undocumented
- `recurringBookingCreatorCancelTemplate` — Template for recurring booking cancel email for creator.
- `recurringBookingCreatorCreateTemplate` — Template for work planner recurring booking creation email.
- `recurringBookingCreatorUpdateTemplate` — Template for recurring workplanner booking update email.
- `REQUEST_APPROVAL_SUBJECT` — Stratus access request subject.
- `REQUEST_APPROVAL_TEMPLATE` — Mail request to a list of approvers.
- `REQUEST_APPROVED_SUBJECT` — Admins approved support user request subject.
- `REQUEST_APPROVED_TEMPLATE` — Request approved email template to support user.
- `REQUEST_REJECTED_SUBJECT` — Stratus support user request rejected email subject.
- `REQUEST_REJECTED_TEMPLATE` — Stratus support user request rejection template.
- `SEAT_ALLOCATION_COMMUNICATION_BODY` — Allocation details email body HTML.
- `SEAT_ALLOCATION_COMMUNICATION_HEADER` — Allocation details email subject.
- `SUPPORT_USER_ADMINS_LIST` — List of admins who will receive the approval request mail.

## Missing Descriptions
_26 properties have no description in any source (PMS config files, PMS Description Cleaned, or wis_unique_configs)._
Contact the owning service team for documentation.

- `employeeDeactivationEmailSubject`
- `FELLOW_PASSENGER_BOARDED_HEADER`
- `FELLOW_PASSENGER_NO_SHOW_HEADER`
- `MONTH_END_NO_SHOW_ACTION_EMAIL`
- `MONTH_END_NO_SHOW_ACTION_EMAIL_SUBJECT`
- `MONTH_END_NO_SHOW_FUTURE_SCHEDULE_REMOVED_MESSAGE`
- `MONTH_END_NO_SHOW_FUTURE_SCHEDULES_REMOVED_TITLE`
- `MONTH_END_NO_SHOW_SCHEDULE_EDIT_PERMISSION_REVOKED_MESSAGE`
- `MONTH_END_NO_SHOW_SCHEDULE_EDIT_PERMISSION_REVOKED_TITLE`
- `MONTHLY_NO_SHOW_FUTURE_SCHEDULES_REMOVED_MESSAGE`
- `MONTHLY_NO_SHOW_SCHEDULE_EDIT_PERMISSION_REVOKED_MESSAGE`
- `MONTHLY_NO_SHOW_WARNING_MESSAGE`
- `NO_SHOW_ACTION_EMAIL_AT_MONTH_END_SUBJECT`
- `NO_SHOW_ACTION_EMAIL_FUTURE_SCHEDULE_REMOVAL_AND_SCHEDULE_EDIT_REVOKED_SUBJECT`
- `NO_SHOW_ACTION_EMAIL_FUTURE_SCHEDULE_REMOVAL_SUBJECT`
- `NO_SHOW_AUTO_APPROVAL_SUBJECT`
- `NO_SHOW_EMPLOYEE_BOARDED_NOTIFICATION`
- `NO_SHOW_FUTURE_SCHEDULES_REMOVED_MESSAGE`
- `NO_SHOW_FUTURE_SCHEDULES_REMOVED_TITLE`
- `NO_SHOW_SCHEDULE_EDIT_PERMISSION_REVOKED_MESSAGE`
- `NO_SHOW_SCHEDULE_EDIT_PERMISSION_REVOKED_TITLE`
- `NO_SHOW_WARNING_EMAIL_SUBJECT`
- `NO_SHOW_WARNING_MESSAGE`
- `NO_SHOW_WARNING_TITLE`
- `noShowActionAtMonthEndBannerMessage`
- `PLANNED_EMPLOYEE_BOARDED_NOTIFICATION`

_Last updated: 2026-05-26_
_Source: [[sources/pms-configs-in-all-wis-configs]] | [[sources/pms-configs-com-wis-service-configs]]_
