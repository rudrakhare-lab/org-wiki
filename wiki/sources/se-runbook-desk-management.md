---
type: source
ingested: 2026-06-29
doc_type: misc
---

# SE Runbook — Desk Management Source Summary

## Source Title

SE Runbook Phase D — Desk Management topic (6 source documents)

## Date

2024-08-25 (Booking API doc, most recent); 2021-09-20 (oldest — digi-pass pptx)

## Type

misc (SE runbook crawl — mix of docx, xlsx, pptx)

## Source Documents Covered

| # | Title | raw_path | Date | Format |
|---|-------|----------|------|--------|
| 1 | WorkInSync Booking API Document | `raw/se-runbook/crawl/files/1cHii4_pj5EOySHb6rBM5NRR3iKGYQVd5KYD7YWVP__U.docx` | 2024-08-25 | docx |
| 2 | Enablement of Recurring Booking in Workplanner | `raw/se-runbook/crawl/files/1u5OPZ5bOqVUR7g6L7jrh31WmSxWh31Vs9hlpceJGH8g.docx` | (undated) | docx |
| 3 | MODULE 2: Desk Booking Solution / Space Management | `raw/se-runbook/crawl/files/1pTkjoLBq-lXXb_DSdeUH1IZiWDMv9_yTdySr_2NhQCw.docx` | (undated) | docx |
| 4 | WIS Configurations for Desk Booking (xlsx) | `raw/se-runbook/crawl/files/1Z4BOVZYcN41r9zlK5X2wH2mG3ZUAbu9NCO-xaYZ7SNs.xlsx` | (undated) | xlsx |
| 5 | Booking Approval (Powered by Camunda) | `raw/se-runbook/crawl/files/1cYJIABt29kUBtZhNUXSVAPzgCkt4hMzezLonW_guyVQ.docx` | (undated) | docx |
| 6 | Perpetual digi pass for dedicated seats (**OLD 2021**) | `raw/se-runbook/crawl/files/1mEe0EWKYr7ZXr99-k4ZFYKS_HjNrpo9z.pptx` | 2021-09-20 | pptx |

## Key Takeaways

- **Desk Management is the central WFO booking module.** Employees book desks on a per-day basis. Admins control inventory allocation by floor, team, BU, or individual. Hot-desks, dedicated seats, and LOB-based allocation hierarchies are all supported.
- **External integration API exists (2024, current).** Four REST endpoints allow third-party systems to query bookings, list offices, and check resource availability. Auth uses OAuth2 client-credentials (Bearer token, 48-hour validity). The API covers desks, rooms, and parking in a unified response structure.
- **Booking approval is Camunda-driven.** Manager-approval workflows are encoded in a DMN decision table deployed on `wis-camunda-engine.workinsync.io`. Adding a new BUID requires downloading, editing, and re-uploading the `.dmn` file. Criteria include booking type, weekly/monthly limits, and employee tags.
- **Recurring bookings require three Booking-Rule-Engine properties.** `enableRecurrenceOnTeamPlanner` (Boolean) is the master switch; `workplannerNotificationControl` (JSON) governs per-event notifications; `workplannerRecurrenceMaxDays` (Integer, on EMP-EXP-COMMON-CONFIG) caps the booking window.
- **Desk allocation supports non-team hierarchies.** Large enterprises can allocate desks by Cost Centre, Line of Business (LOB), or Sub-LOB. The hierarchy is auto-populated from employee data or manually configured in Settings.
- **Tags drive advanced booking controls.** Desk tags and employee tags (managed by [[modules/tags-desk-parking]]) are used for allocation restrictions, approval-flow routing, and amenity searches.
- **The 2021 "Perpetual Digi Pass" pptx is historical context only.** It describes the dedicated-seat auto-check-in feature (property-based, enabled via TO ticket) and an earlier non-Camunda approval workflow. The Camunda-based approval is the current implementation.

## Entities Mentioned

- [[entities/booking]] — BookingID, requestStatus/bookingStatus, startTime, endTime, premiseType, resourceName, officeName, floorName
- [[entities/employee]] — email, RMID (reporting manager), team, BU, office assignment
- **Desk/Seat** — seat name, floor, amenities, allocation type (no entity page yet)
- **Tag** — desk-level and employee-level (managed by [[modules/tags-desk-parking]])

## Modules Mentioned

- [[modules/desk-management]] — primary subject
- [[modules/tags-desk-parking]] — desk/employee tag management
- [[modules/meal-management]] — meal booking linked to WFO; meal mandate and cutoff
- [[modules/floor-kiosk]] — floor plan upload and FloorPremiseID (prerequisite)
- [[modules/access-management]] — card-swipe check-in creates/signs-in a booking
- [[modules/employee-provisioning]] — employee data sync prerequisite

## Decisions Extracted

None extracted — sources are operational runbooks, not architecture decision records.

## Config Properties Documented

Properties from doc 2 (Recurring Booking) and doc 5 (Booking Approval):

| Property | Service | Type | Default | Notes |
|----------|---------|------|---------|-------|
| `enableRecurrenceOnTeamPlanner` | BOOKING-RULE-ENGINE | Boolean | (not stated) | Master switch for WorkPlanner recurring bookings |
| `workplannerNotificationControl` | BOOKING-RULE-ENGINE | JSON | (not stated) | Notification matrix for CREATE/UPDATE/CANCEL events |
| `autoAllocate` | BOOKING-RULE-ENGINE | Boolean | (not stated) | Auto-assign desk from allocation pool on booking creation |
| `workplannerRecurrenceMaxDays` | EMP-EXP-COMMON-CONFIG | Integer | (not stated) | Max days between first booking and "Repeat till" date |
| `bookingRequestApprovalFlowEnabled` | WIS-SEAT-BOOKING | Boolean | (not stated) | Master switch for approval workflow |
| `approvalFlowEnabled` | WIS-SEAT-BOOKING | Boolean | (not stated) | Enables approval UI in employee app |
| `approvalFlowInWfoEnabled` | WIS-SEAT-BOOKING | Boolean | (not stated) | Enable approval for WFO bookings |
| `approvalFlowInInWfhEnabled` | WIS-SEAT-BOOKING | Boolean | (not stated) | Enable approval for WFH bookings |
| `autoRequestApprovalEnabled` | WIS-SEAT-BOOKING | Boolean | (not stated) | Auto-approve if manager does not act before deadline |
| `expiryCutOffInMinutes` | WIS-SEAT-BOOKING | String | (not stated; example: `"50"`) | Minutes before booking start when pending request expires |
| `expiryNotificationCutOffInMinutes` | WIS-SEAT-BOOKING | String | (not stated; example: `"40"`) | Reminder sent this many minutes before expiry |
| `pendingRequestsNotificationEnabled` | WIS-SEAT-BOOKING | Boolean | (not stated) | Notify manager of pending requests |
| `expiredRequestNotificationEnabled` | WIS-SEAT-BOOKING | Boolean | (not stated) | Notify on expired requests |
| `bookingApprovalEmailsEnabled` | WIS-SEAT-BOOKING | Boolean | (not stated) | Email notifications for approvals |
| `wfhWeeklyLimit` | WIS-SEAT-BOOKING | Integer (≥0) | (not stated) | WFH bookings/week before approval required; overrides Camunda value |
| `wfhMonthlyLimit` | WIS-SEAT-BOOKING | Integer (≥0) | (not stated) | WFH bookings/month before approval required; overrides Camunda value |
| `autoExpireHour` | WIS-SEAT-BOOKING | Integer | (not stated; example: `1`) | Hour at which pending requests auto-expire |
| `cancelSchedulesEnabled` | WIS-SEAT-BOOKING | Boolean | (not stated) | Allow commute cancellation |
| `tagsEnabled` | WIS-SEAT-BOOKING | JSON array | (not stated; example: `["WFO","WFH"]`) | Booking types subject to tag-based approval rules |
| `bookingApprovalConstraintEnabled` | EMP-EXP (service not specified) | Boolean | (not stated) | Part of Camunda decision table evaluation |

For the full `WIS-SEAT-BOOKING` config catalogue (35 properties), see [[configs/wis-seat-booking]].
For `BOOKING-RULE-ENGINE` properties, see [[configs/booking-rule-engine]].

## Secrets Redacted

The Booking API document (doc 1) originally contained two RS256 JWT access tokens in example responses. These were **pre-redacted** in the input to `<RS256 JWT — redacted>` before ingestion.

The document also contained a Base64-encoded Basic-auth credential in a curl example (`Authorization: Basic <…>`). This was **not** pre-redacted in the input — it has been replaced with `Authorization: Basic <base64(username:password)>` in all wiki pages written from this source. No raw credential appears in any wiki page.

The Camunda doc (doc 5) contained a real internal email address used as a `userId` parameter in a curl example. This has been replaced with `<userId>` in the runbook. The Camunda cockpit demo credentials shown in the source doc are omitted from all wiki pages.

Token re-scan result: **CLEAN** — no `eyJ…` JWTs, no `Bearer <real-token>`, no `client_secret`, no real cookies in any wiki page written from these sources.

## Wiki Pages Created / Updated

- Created: [[modules/desk-management]] (stub → active; 69 lines → 157 lines)
- Created: [[runbooks/desk-booking-setup]]
- Created: [[runbooks/recurring-booking-setup]]
- Created: [[runbooks/booking-approval-camunda]]
- Created: [[sources/se-runbook-desk-management]] (this page)
