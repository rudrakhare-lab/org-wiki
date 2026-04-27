# WorkInSync Product Overview
_Maintained by AI. Last updated: 2026-04-27_

---

## What We're Building
WorkInSync is a **workplace management platform** that helps organizations manage physical
resources (desks, meeting rooms, parking, visitor access, meals) and the employee experience
around them. The product runs on Web, iOS/Android mobile app, tablet kiosks, and integrates
with Outlook/Google Calendar.

Current ingests cover: **Meeting Rooms** (full — 8 source docs).
Remaining ~21 modules TBD as docs are uploaded.

---

## Core Modules
| Module | Purpose | Status |
|--------|---------|--------|
| [[modules/meeting-rooms]] | Room booking, check-in, kiosk, Outlook sync, catering, dynamic policy, maintenance | active |
| modules/desk-management | Desk booking and employee seating management | _not yet ingested_ |
| modules/parking-management | Parking bay allocation | _not yet ingested_ |
| modules/visitor-management | Visitor registration, access control | _not yet ingested_ |
| modules/meal-management | Cafeteria meal bookings | _not yet ingested_ |
| modules/mobile-app | iOS/Android app container for all WIS features | _not yet ingested_ |
| modules/floor-kiosk | Kiosk hardware/MDM layer (shared by meeting-rooms, guard-app) | _not yet ingested_ |
| modules/tags-desk-parking | Tag engine (access control primitives, dynamic policy) | _not yet ingested_ |
| modules/ms-teams-integration | Outlook/Teams/Google Calendar integration | _not yet ingested_ |
| modules/employee-provisioning | Employee onboarding to WIS | _not yet ingested_ |
| modules/sso | Single Sign-On integration | _not yet ingested_ |
| modules/access-management | Physical access/badge management | _not yet ingested_ |

---

## Key Architecture Decisions
| Decision | Summary |
|----------|---------|
| [[decisions/2026-04-27-meeting-room-auto-release]] | Rooms auto-release on no-show; calendar event preserved |
| [[decisions/2026-04-27-kiosk-pin-auth-over-login]] | PIN email auth on kiosk instead of user login |
| [[decisions/2026-04-27-catering-order-id-model]] | Meeting ID stable across edits; Order IDs reminted on cancel+recreate |

---

## Entity Ownership Map
| Entity | Owner Module |
|--------|-------------|
| [[entities/room]] | meeting-rooms |
| [[entities/booking]] | meeting-rooms |
| [[entities/catering-order]] | meeting-rooms |
| [[entities/cafeteria]] | meeting-rooms ⚠️ (shared with meal-management — ownership TBD) |
| [[entities/room-tag]] | tags-desk-parking |
| [[entities/maintenance-period]] | meeting-rooms |

---

## Cross-Module Dependency Summary
_See [[cross-module/overview]] for the full dependency graph._

Known dependencies discovered so far:
- [[modules/meeting-rooms]] → [[modules/tags-desk-parking]] (borrows tag engine for Dynamic Policy)
- [[modules/meeting-rooms]] → [[modules/floor-kiosk]] (shares kiosk device infrastructure)
- [[modules/meeting-rooms]] → [[modules/mobile-app]] (feature surface inside mobile app)
- [[modules/meeting-rooms]] → [[modules/ms-teams-integration]] (Outlook calendar sync)

---

## Open Questions
- Who owns the `Cafeteria` entity — `meeting-rooms` or `meal-management`?
- `MEETING_ROOM_RELEASE_IF_NO_CHECKIN` default discrepancy: 180 min (resources doc) vs. 15 min (App PRD).
- Is Outlook calendar integration managed inside `ms-teams-integration` or a standalone `outlook` backend service?
- Meeting Rooms module owner team name is not mentioned in any ingested doc.
