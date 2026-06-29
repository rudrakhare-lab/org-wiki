---
type: source
ingested: 2026-06-29
doc_type: misc
raw_paths:
  - raw/se-runbook/crawl/files/1MrkujYyng73AOyPajtVU1rSWS-2-bFsk2MEbPvB0yzM.docx
  - raw/se-runbook/crawl/files/1EEGOioCsfA6gg1tBj6hH4Mw7thsXT9hUX1AJFYv_3GE.docx
  - raw/se-runbook/crawl/files/1y0KGfTzmCU-PG8D6FWq4m6DkZT7EBpUE4Lq0D4lkiKY.docx
---

# Source — SE Runbook: Kiosk Topic (Phase D)

## Source Title

Three SE operational documents covering kiosk and shared security-guard service infrastructure:

| # | Title | Version / Date | Raw path |
|---|-------|---------------|----------|
| 1 | Prod URL — Security-guard (production endpoints reference) | undated | `raw/se-runbook/crawl/files/1MrkujYyng73AOyPajtVU1rSWS-2-bFsk2MEbPvB0yzM.docx` |
| 2 | Meeting Room Kiosk Setup — Control Document | v1.1 / 2022-10-21 (last extracted 2025) | `raw/se-runbook/crawl/files/1EEGOioCsfA6gg1tBj6hH4Mw7thsXT9hUX1AJFYv_3GE.docx` |
| 3 | Meeting Room Kiosk — Scalefusion Prerequisites | undated | `raw/se-runbook/crawl/files/1y0KGfTzmCU-PG8D6FWq4m6DkZT7EBpUE4Lq0D4lkiKY.docx` |

## Date

- Doc 1: undated reference sheet
- Doc 2: v1.1, approved 2022-10-21; referenced as "2025" in the SE crawl batch label (last-active date)
- Doc 3: undated

## Type

misc (SE operational runbook / reference)

## Key Takeaways

- **Production backend host confirmed (Doc 1):** The `mis-security-guard` service production host is `wis-premise.workinsync.io/mis-security-guard/`. The beta host is `mis-security-beta1.moveinsync.com/mis-security-guard/`. EU-green is `mis-security-green.eu.moveinsync.com/mis-security-guard/`. These are **backend service endpoints**, not the front-end Guard App UI URL.
- **Meeting-room kiosk has two setup paths (Doc 2):** (a) Without MDM — manual app install + device lockdown; (b) With Scalefusion MDM (recommended for production) — managed enrollment + remote access.
- **Room pairing is pin-based (Docs 2 + 3):** A 6-digit pin generated from the admin site Meeting Rooms Settings (Kiosk Mapping column) pairs the tablet to a specific room. The pin is single-use per pairing event.
- **Kiosk URLs are region-specific (Doc 2):** SG-Blue, EU-Blue, EU-Green, and India regions each have a distinct kiosk URL for URL-based MDM lockdown. The team must confirm which URL applies per client.
- **Scalefusion MDM enrollment for meeting-room kiosk uses a different QR code than floor kiosk (Doc 3):** Same MDM procedure but a separate Scalefusion policy group. Device naming convention: `<Organization Name> - <Meeting Room Name> MR Kiosk`.
- **RemoteCast is required for support (Doc 3):** Must be enabled before going live. Exit the MR app via a swipe gesture, grant all RemoteCast permissions, then re-enter Scalefusion.
- **Doc 1 is a backend-service reference, not the Guard App front-end (Doc 1):** The production IOT Guard App front-end URL ambiguity (the `-beta` hostname question) is NOT resolved by this document — Doc 1 confirms only the backend `mis-security-guard` service host. Front-end IOT URL question remains open.

## Entities Mentioned

- Meeting room (room premise), Tablet/device (kiosk device), Guard App backend (mis-security-guard service), Scalefusion MDM policy group

## Modules Mentioned

- [[modules/guard-app-kiosks]] — production backend service host confirmed (Doc 1)
- [[modules/meeting-rooms]] — meeting-room kiosk setup, pairing, config keys (Docs 2 + 3)
- [[modules/floor-kiosk]] — shared MDM enrollment procedure referenced (Doc 3)

## Decisions Extracted

None — these are operational how-to documents, not architecture or product decisions.

## Config / Endpoints Documented

### Production vs. Beta Service Endpoints — `mis-security-guard` (Doc 1)

| Environment | Host |
|-------------|------|
| Production | `wis-premise.workinsync.io/mis-security-guard/` |
| Beta | `mis-security-beta1.moveinsync.com/mis-security-guard/` |
| EU-Green | `mis-security-green.eu.moveinsync.com/mis-security-guard/` |

Additional services documented in Doc 1 (not meeting-room specific):

| Service | Production host |
|---------|----------------|
| SeatBooking | `wis-seat.moveinsync.com/wisSeatBooking/` |
| SeatBooking Beta | `wis-seat-beta.moveinsync.com/wisSeatBooking/` |
| SeatBooking EU-Green | `wis-seat-green.eu.moveinsync.com/wisSeatBooking/` |

### Meeting-Room Kiosk Config Keys (Docs 2 + 3)

| Config Key | Kiosk relevance |
|---|---|
| `MEETING_ROOM_ENABLED` | Must be `true`; kiosk pairing fails if false |
| `SHOW_UPCOMING_BOOKINGS_TIME` | Minutes before booking start shown on kiosk check-in prompt |
| `MEETING_EMAIL_OTP_TO_AUTHENTICATE` | PIN email for kiosk cancel/end |
| `CANCEL_EVENT_PIN_VERIFICATION_ENABLE` | PIN required before cancellation on kiosk |
| `RELEASE_MEETING_ROOM` + `MEETING_ROOM_RELEASE_IF_NO_CHECKIN` | Auto-release settings; 15 min recommended |

Full config table: [[modules/meeting-rooms]] §Key Configurations

### Kiosk Web URLs by Region (Doc 2)

| Region | Kiosk URL |
|--------|-----------|
| SG-Blue | `ui.moveinsync.com/kiosk/#/kiosk-dashboard` |
| EU-Blue | `ui.eu.workinsync.io/kiosk/#/meeting-room/` |
| EU-Green | `green-ui.eu.workinsync.io/kiosk/#/meeting-room/` |
| India | `https://ui.moveinsync.in/kiosk/#/meeting-room/setup` |

## Secrets Redacted

None. All URLs and hostnames are operational service endpoints, not credentials. Source material was scanned clean of JWTs, bearer tokens, base64 credentials, and personal email addresses before extraction. Output verified clean.

## Wiki Pages Created / Updated

- **Created:** [[runbooks/meeting-room-kiosk-setup]] — new full runbook (Docs 2 + 3)
- **Created:** [[sources/se-runbook-kiosk]] — this page
- **Updated:** [[modules/guard-app-kiosks]] — production backend endpoint note added under Key Features + API Endpoints; Open Questions updated to distinguish backend (now confirmed) from front-end IOT URL (still open); `source:` frontmatter appended; `last_updated` bumped to 2026-06-29
- **Updated:** [[modules/meeting-rooms]] — `[[runbooks/meeting-room-kiosk-setup]]` added to Related Runbooks; `source:` frontmatter appended with `[[sources/se-runbook-kiosk]]`; no other changes
