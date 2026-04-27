# Activity Log
Append-only. Format: `## [YYYY-MM-DD HH:MM] <operation> | <title>`

---

## [RESET 2026-04-27] Wiki reset for real ingest
- All test pages cleared. Ready to ingest real WorkInSync feature docs.
- Per-feature folders created under `raw/modules/` matching the Conwo WorkInSync Docs Drive structure.

---

## [INGEST 2026-04-27 17:45] INGEST | meeting-rooms — 8 source documents

**Sources ingested:**
1. `Meeting Rooms App PRD.docx` → [[sources/meeting-rooms-app-prd]]
2. `Copy of Kiosk - Meeting Rooms PRD.docx` → [[sources/kiosk-meeting-rooms-prd]]
3. `Copy of Dynamic Policy for Meeting Rooms.docx` → [[sources/dynamic-policy-meeting-rooms]]
4. `Copy of Meeting Rooms Catering PRD.docx` → [[sources/meeting-rooms-catering-prd]]
5. `Copy of Meeting Rooms - Room Maintenance Workflow.docx` → [[sources/meeting-rooms-room-maintenance]]
6. `Copy of Meeting Rooms - Outlook Integration Permissions Explanation.docx` → [[sources/outlook-integration-permissions]]
7. `Copy of Meeting Rooms_Setting up Outlook Add-in for Outlook Integration.docx` → [[sources/outlook-addin-setup]]
8. `Copy of Meeting Rooms Resources.docx` → [[sources/meeting-rooms-resources]]

**Pages created:**
- `wiki/modules/meeting-rooms.md` (new)
- `wiki/entities/room.md` (new)
- `wiki/entities/booking.md` (new)
- `wiki/entities/catering-order.md` (new)
- `wiki/entities/cafeteria.md` (new)
- `wiki/entities/room-tag.md` (new)
- `wiki/entities/maintenance-period.md` (new)
- `wiki/cross-module/meeting-rooms-tags-desk-parking.md` (new)
- `wiki/cross-module/meeting-rooms-floor-kiosk.md` (new)
- `wiki/cross-module/meeting-rooms-mobile-app.md` (new)
- `wiki/decisions/2026-04-27-meeting-room-auto-release.md` (new)
- `wiki/decisions/2026-04-27-kiosk-pin-auth-over-login.md` (new)
- `wiki/decisions/2026-04-27-catering-order-id-model.md` (new)
- All 8 source pages in `wiki/sources/`

**Pages updated:**
- `wiki/glossary.md` — 18 terms added
- `wiki/index.md` — 22 pages indexed
- `wiki/overview.md` — meeting-rooms summarised; entity ownership map started
- `wiki/cross-module/overview.md` — 3 cross-module connections documented
- `wiki/log.md` (this entry)

**Open questions flagged:**
- `Cafeteria` entity ownership conflict with `meal-management` module
- `MEETING_ROOM_RELEASE_IF_NO_CHECKIN` default inconsistency (180 min vs. 15 min)
- Outlook integration service ownership (`ms-teams-integration` vs. standalone `outlook` service)
- Module owner team name not stated in any source doc
