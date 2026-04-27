---
type: source
raw_path: raw/modules/meeting-rooms/Copy of Meeting Rooms Resources.docx
ingested: 2026-04-27
doc_type: misc
---

# Meeting Rooms Resources

## Source Title
Meeting Rooms Resources (deployment notes & links)

## Date
Unknown

## Type
misc (internal reference / link collection)

## Key Takeaways
- Deployment depends on 4 services: `floor-plan` (UI), `outlook` (backend), `booking-v2` (booking data), `kiosks-UI`.
- Tenant onboarding requires setting `MEETING_ROOM_ENABLED: true` for both Stratus and ETS.
- Default configuration block for a new tenant (key values):
  - `MEETING_ROOM_RELEASE_IF_NO_CHECKIN`: 180 min
  - `SHOW_UPCOMING_BOOKINGS_TIME`: 6 min
  - `RELEASE_MEETING_ROOM`: false
  - `MEETING_EMAIL_OTP_TO_AUTHENTICATE`: true
  - `CANCEL_EVENT_PIN_VERIFICATION_ENABLE`: false
  - `CONSENT_TYPE`: ADMIN
- Consent URL generation uses 4 params: `buid`, `emailId`, `onboardingType` (OUTLOOK/GSUITE), `role`.
- Document is primarily a link dump to other internal Google Docs/Figma/Sheets — does not contain new feature specs.

## Entities Mentioned
- None new.

## Modules Mentioned
- [[modules/meeting-rooms]] (primary)

## Decisions Extracted
- None.

## Wiki Pages Created/Updated
- Updated: [[modules/meeting-rooms]] (configurations section)

_Source: [[sources/meeting-rooms-resources]]_
