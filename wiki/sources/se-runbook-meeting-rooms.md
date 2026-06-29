---
type: source
ingested: 2026-06-29
doc_type: misc
---

# Source Summary — SE Runbook: Meeting Rooms

## Source Documents

| Title | Date | Type | raw_path |
|---|---|---|---|
| Meeting Rooms Booking — Control Document (v1–1.4) | 2023 | SE control doc (internal) | `raw/se-runbook/crawl/files/1qcf6HjovQ5MwBKnWWiLsYtqZghp7GC_s-c7gGyLbK6I.docx` |
| Outlook Room Booking Integration — Pre-Implementation Discovery | 2021 | SE pre-impl discovery (internal) | `raw/se-runbook/crawl/files/1z5F39r8hNTWzmsK_OCHAo5K4yBB2nzskUTvcdqffX0o.docx` |
| Meeting Room Catering (slides) | undated (v2.2–2.3 era) | SE feature walkthrough (pptx) | `raw/se-runbook/crawl/files/1w63IH9n7w28kJCKljb5kUvJhJGtcdt-WDeD8hkUcB54.pptx` |

---

## Key Takeaways

- **Control doc (2023)** is the primary SE operational reference for Meeting Rooms setup. It covers room creation (UI + bulk upload), booking behaviour configs, check-in/auto-release, notifications, and multi-version booking use cases. The full doc is ~52k chars; the SE crawl captured the first ~13k.
- **Outlook Pre-Impl Discovery (2021)** provides a structured questionnaire covering Exchange/M365 configuration for bidirectional sync and the WIS Outlook Add-in. Discovery areas include: email identity, privacy labels, booking approval, timezone, room access control, sync edge cases, and Add-in client compatibility.
- **Catering slides** cover the three key features: flexible delivery slots (user-selectable within meeting window), customisable per-item availability time ranges (SE-enablement required), and booking deadlines per item. The catering dashboard consolidates order tracking, allergy info, and service requests.
- **`MEETING_ROOM_RELEASE_IF_NO_CHECKIN`** recommended value is **15 minutes** (deployment default is 180 — explicitly flagged in the control doc as a recommended setting change).
- **`ALLOW_ONLY_ONE_MEETING_ROOM_AT_ONCE`** defaults to `true`; set to `false` only if the client needs multi-room per booking.
- **Outlook 2021 source is dated** — consent-URL paths and permission scopes should be verified against current wis-integration service documentation before client use.
- **Dynamic Policy does not apply to Outlook/Google calendar rooms** — tag-based access control affects only WIS-native rooms.
- **`cateringLimits`** (cut-off by participant count) is a `.com`-only config; `.in` server clients cannot configure it via this property.

---

## Entities Mentioned

- [[entities/room]] — room resource creation, bulk upload, calendar type
- [[entities/booking]] — booking lifecycle, check-in, auto-release, edit/extend
- [[entities/catering-order]] — delivery slots, cut-off, booking deadlines, dashboard
- [[entities/cafeteria]] — admin setup via Manage Premise → cafeterias → menus → items

---

## Modules Mentioned

- [[modules/meeting-rooms]] — primary subject
- [[modules/floor-kiosk]] — kiosk check-in, QR code scanning
- [[modules/mobile-app]] — mobile booking surface, QR scan check-in
- [[modules/ms-teams-integration]] — adjacent; note that Outlook calendar sync runs via the separate `wis-integration`/`outlook` service

---

## Decisions Extracted

None. The SE control doc is an operational procedures document, not an architecture decision record.

---

## Config Properties Documented

Properties with concrete values or notes confirmed by SE sources (not previously in wiki):

| Property | Value / Default confirmed | Source | Notes |
|---|---|---|---|
| `MEETING_ROOM_RELEASE_IF_NO_CHECKIN` | Recommended **15 min** (deployment default 180) | Control doc (2023) | Module page already had this — SE doc confirms 15 min is the recommended operational setting |
| `ALLOW_ONLY_ONE_MEETING_ROOM_AT_ONCE` | Default `true` | Control doc (2023) | New: SE doc confirms the default and the flag name `ALLOW_ONLY_ONE_MEETING_ROOM_AT_ONCE` |
| `BOOK_MEETING_ROOM_BY_EMPLOYEES` | Default `true` (internal property) | Control doc (2023) | New: SE doc surfaces this property name |
| `SHOW_SPECIAL_REQUEST_ON_MEETING` | Configurable (boolean) | Control doc (2023) | New: SE doc confirms this controls the special-request text box on the booking form |
| `ENABLE_REMINDER_NOTIFCATION` | Default `true` (note: typo in source — single 'I') | Control doc (2023) | New: SE doc surfaces this property name and confirms the default; preserve exact spelling from source |
| `RELEASE_MR_NOTIFICATION` | Configurable (boolean) | Control doc (2023) | New: SE doc surfaces this property name for the auto-release push notification |
| `ENABLE_NEXT_MEETING_REMINDER` | Default `true` | Control doc (2023) | New: SE doc surfaces this property name for next-meeting reminder (5 min before end) |

---

## Secrets Redacted

None. The inputs file was scanned clean. No JWTs, Bearer tokens, Base64 credentials, client secrets, or `@moveinsync.com`/`@workinsync.io` credential-context email addresses were found in the source material or in this output.

---

## Wiki Pages Created / Updated

**Created:**
- [[runbooks/meeting-room-setup]] — SE room/resource creation + booking configuration
- [[runbooks/meeting-room-catering-setup]] — cafeteria/menu/catering enablement steps
- [[runbooks/outlook-room-integration]] — Outlook calendar integration setup (⚠️ 2021 source)
- [[sources/se-runbook-meeting-rooms]] — this page

**Updated (augmented):**
- [[modules/meeting-rooms]] — added `## Related Runbooks` section; appended `[[sources/se-runbook-meeting-rooms]]` to `source:` frontmatter
