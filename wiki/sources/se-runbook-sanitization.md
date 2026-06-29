---
type: source
raw_path: raw/se-runbook/_extract/sections/35-9-seat-sanitization-setup-workflow.md
ingested: 2026-06-29
doc_type: misc
---

# Source Summary — SE Runbook: Seat Sanitization

## Source Title
SE Runbook — Section 9: Seat Sanitization Setup Workflow (+ related crawled docs)

## Date
Unknown (SE runbook is a living operational document; crawled PRD dated approximately 2021 based on vaccination v1 context)

## Type
Operational runbook (SE procedure) + PRD problem statement + feature spec

## Key Takeaways
- Seat sanitization is a facilities-management capability within WorkInSync: housekeeping staff are onboarded as a special `HOUSEKEEPER` user type in `mis-security-guard`, scan QR codes on desks, and mark them clean
- The UI view (sanitisation status column on floor map) is enabled by the TO team via Consul (`SANITISATION_STATUS_ENABLED`), while the HOUSEKEEPER user creation, QR scan toggle, and cut-off time are owned by SE
- QR-code scan is optional (`enableQrCodeForSeatSanitize`); without it, housekeepers select a floor manually and bulk-mark seats
- The sanitization cut-off time property (`seatSanitizeCuttoffInMinute`) carries a non-standard double-`t` spelling — preserve verbatim
- Vaccination Status Feature (v1) is a related but distinct return-to-office safety feature: employee declares vaccination status, optionally uploads a certificate, admin reviews; `blockUserIfNotVaccinated` gates bookings for unvaccinated users
- The PRD problem statement (crawled doc) confirms the initial scope: QR-code printing, housekeeper onboarding, scan → mark sanitized, last-sanitization-time in floor view + booking view + admin report
- Vaccination Center premise creation uses `premiseType: 10` and is set up via Postman; capacity can be global (date-range) or slot-level (by minute-of-day)
- `sanitisationStatus` (camelCase) maps to `SANITISATION_STATUS_ENABLED` (Consul flag) — same feature, two config surfaces

## Entities Mentioned
- [[entities/user]] — HOUSEKEEPER subtype
- [[entities/seat]] — desk/seat polygon with QR code
- [[entities/premise]] — floor and vaccination-center premise types

## Modules Mentioned
- [[modules/sanitization]] — primary subject
- [[modules/desk-management]] — seat/booking context
- [[modules/guard-app-kiosks]] — shared `mis-security-guard` service

## Decisions Extracted
_(No explicit architecture decisions extracted — the source is operational procedure, not a design doc)_

## Wiki Pages Created/Updated
- Created: [[modules/sanitization]]
- Created: [[runbooks/seat-sanitization]]
- Created: [[sources/se-runbook-sanitization]] (this page)

_Source: raw/se-runbook/_extract/sections/35-9-seat-sanitization-setup-workflow.md and adjacent sections (36–39, 49, 59) + crawled PRD_
