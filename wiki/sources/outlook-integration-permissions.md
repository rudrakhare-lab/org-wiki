---
type: source
raw_path: raw/modules/meeting-rooms/Copy of Meeting Rooms - Outlook Integration Permissions Explanation.docx
ingested: 2026-04-27
doc_type: spec
---

# Outlook Integration Permissions Explanation

## Source Title
Outlook Permissions — Meeting Rooms Integration

## Date
Unknown

## Type
spec

## Key Takeaways
- Documents every Microsoft Graph API permission required for WIS Outlook integration, the data it exposes, and why it is critical.
- **Delegated permissions** (user-context): `profile`, `openid`, `offline_access`, `Calendars.ReadWrite`, `Place.Read.All`, `Place.ReadWrite.All` — used when user interacts with the booking UI.
- **Application permissions** (system/background): `Place.Read.All`, `User.Read.All`, `Calendars.ReadWrite`, `AccessReview.Read.All` — used by background sync engine, nightly room catalog jobs, webhook handling.
- `offline_access` is operationally critical: allows token refresh without requiring user re-login — enables bi-directional sync when user is offline.
- `User.Read.All` (application): broad permission (admin consent required) — needed to resolve meeting organizer identity and support delegate bookings.
- `Calendars.ReadWrite` (application): high-impact — reads room mailbox calendars, writes booking updates, handles conflict resolution. Required for kiosk-initiated bookings.
- Two categories of permissions must be consented to separately: delegated (user or admin consent) vs. application (admin consent only).

## Entities Mentioned
- [[entities/booking]]
- [[entities/room]]

## Modules Mentioned
- [[modules/meeting-rooms]] (primary)
- [[modules/ms-teams-integration]] (Outlook/MS ecosystem dependency)

## Decisions Extracted
- None new — documents existing integration design.

## Wiki Pages Created/Updated
- Updated: [[modules/meeting-rooms]]
- Updated: [[wiki/glossary]] (delegated vs. application permissions)

_Source: [[sources/outlook-integration-permissions]]_
