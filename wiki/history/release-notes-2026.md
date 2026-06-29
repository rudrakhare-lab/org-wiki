---
type: release-notes
year: 2026
last_updated: 2026-06-29
source: "—"
---

# Release Notes — 2026

This page is a **dated changelog**, newest-first — it is the PM/sales source-of-truth for what shipped, not the authoritative current-behaviour reference. For authoritative config defaults and live behaviour, consult the relevant [[modules/]] or [[configs/]] pages. See [[history/release-notes]] for the full recency caveat.

---

### RN 05-2026

> raw evidence: `raw/se-runbook/crawl/files/1lzPEF4pq0HZh7NObrD_YFcj8x56MWg7GJ1CO5wbR4Zo.pptx`

- **Room Maintenance Workflow** — admins schedule maintenance periods with activity details, optional booking block, banners across web/mobile/kiosk/Outlook, automated emails, and audit logs. [[modules/meeting-rooms]] | Properties: `roomMaintenanceWorkflow`, `roomMaintenceEmalList`, `roomMaintenanceAdvanceScheduleAllowed`, `roomMaintenanceMessage`, `roomMaintenanceList`, `maintenanceWindow`, `slotStepMs` (Meeting Rooms Service) | Enablement: Meeting Rooms Service config | PB-64433. ⚠️ The [[entities/maintenance-period]] entity was already documented in the wiki (via meeting-rooms runbook ingest); the RN confirms GA — no contradiction, but this is the canonical ship date.

- **Room Deactivation** — admins deactivate rooms via a dedicated workflow; a configurable email list receives notification. [[modules/meeting-rooms]] | Property: `deactivatedRoomsEmailList` (default: empty, Meeting Rooms Service) | Enablement: Meeting Rooms Service config | PB-65206.

- **Room Deactivation Enhancements** — follow-on UX improvements to the deactivation flow (default-on). [[modules/meeting-rooms]] | Enablement: NA (by default) | PB-64592.

- **Floor Kiosk UI improvements** — quick-session login and auto-end-session controls for better kiosk UX. [[modules/floor-kiosk]] | Properties: `quickSessionLogin`, `autoEndSession` (default: false) | PB-65149.

- **Meeting Rooms: Set Favourite Rooms** — employees can mark rooms as favourites; surfaced in the booking flow. [[modules/meeting-rooms]] | Property: `setFavoriteRooms` (default: false, Booking Rule Engine Service) | PB-65174.

- **Meeting Rooms: Show `beginHour`/`endHour` on timeline** — greys out non-bookable slots on web and mobile timeline views; validation prevents booking outside configured hours (UI-only change, no new properties). [[modules/meeting-rooms]] | Properties: `beginHour`, `endHour` (Meeting Rooms Service, already documented) | PB-65147.

- **Meeting Rooms Reports: Room Name filter** — adds a room-name filter to the Meeting Room Detailed and Summary reports for finer data funnel. [[modules/meeting-rooms]] | Enablement: details in source deck (slide truncated in extracted text; see raw evidence).

---

### RN 04-2026

> raw evidence: `raw/se-runbook/crawl/files/1H_LkfIQRvcFU8xz6pU3UiAYeUfHuKibS0hBmUAgOBO8.pptx`

- **Meeting Room Kiosk: Improved button visibility (accessibility)** — higher-contrast button colours on Meeting Room Display kiosks (MRDs); ships by default. [[modules/meeting-rooms]] | Enablement: NA (by default) | PB-64672.

- **Floor Kiosk: Configurable default booking duration** — `defaultBookingDuration` (default: 60 min) on Visitor Service / FK configs; end time auto-clips to next existing booking if shorter. [[modules/floor-kiosk]] | Property: `defaultBookingDuration` (Visitor Service FK configs, default: 60) | PB-64446.

- **Meeting Rooms Mobile: Timezone picker** — configurable timezone selector in the mobile room-booking flow; dual time-zone display (profile TZ + selected TZ) on booking cards. [[modules/meeting-rooms]] | Properties: `timeZoneMobileView` (default: false), `showTimeZoneOnCards` (default: false) — Meeting Rooms Service | PB-64441.

- **Meal Photo Display in Cafeteria Kiosk** — meal images uploaded per item are shown on the kiosk during selection. [[modules/meal-management]] | Property: `enableMealImageIn` (Employee_Exp_common_config); requires `Cafeteria_Meal_Photo_Upload` read+write privilege | Enablement: SE ticket | PB-64474.

- **Visitor Management: Office-Level Email Template Support** — email templates can be configured per office (previously BUID-level only). [[modules/visitor-management]] | Enablement: NA (by default) | PB-64463.

- **Visitor Management: Face-Based Check-in/Checkout Mode in Reports** — face-recognition check-in/checkout mode is now surfaced as a distinct mode in VMS Reports. [[modules/visitor-management]] | Enablement: NA | PB-64462.

- **Visitor Management: Scroll-Gated NDA Consent & Signature Capture (DPDPA)** — consent checkbox, signature pad, and submit CTA are disabled until the user scrolls to the end of NDA content; applies to Self Check-in, Invite, and Walk-in flows. [[modules/visitor-management]] | Enablement: part of the scroll-gate feature ship (details in raw deck, slide 18–19) | no separate PB listed (ships as part of DPDPA compliance track).

---

### RN 03-2026

> raw evidence: `raw/se-runbook/crawl/files/1rdqLHaGiArmQCmazU6oZ_S4w7zP2Hn04cnHtKjhutGs.pptx`

- **Meeting Rooms UX: "All Offices" filter on Outlook Add-In + image-upload guidance** — adds an opt-in "All Offices" filter in the Outlook Add-In room-booking flow; also surfaces file-format requirements on the MR image-upload UI. [[modules/meeting-rooms]] | Enablement: NA (by default) | PB-62941.

- **Emp Exp: Configurable Check-in-by-time chip on mobile home screen** — the "check-in by time" chip on mobile booking cards is now config-gated (default: false). [[modules/employee-experience]] | Property: `checkInByTimeChip` (default: false, Emp Exp Common Config, BU level) | PB-63400.

- **Shift-Based Booking (Shift Pair & Naming)** — admins define named shift combinations; employees book by shift name instead of manually entering start/end times; custom timing override during edit is configurable. [[modules/desk-management]] / [[modules/employee-experience]] | Properties: `isShiftPairingEnabled`, `isCustomShiftsRestricted`, `shouldAllowCustomTimingWhileEdit` | Enablement: SE ticket | PB-63381.

- **Parking Admin Dashboard 2.0: Cross-Office Booking & Slot Accuracy fixes** — corrects cross-office booking representation and slot-count accuracy in the new admin dashboard (default-on when the new dashboard is enabled). [[modules/parking-management]] | Enablement: default when new admin dashboard is enabled | PB-63436.

- **Meal Chargeback Report** — employee-level meal-consumption report with cost auto-calculation (cafeteria-wise, date-specific pricing), multi-day ranges, and support for inactive employees. [[modules/meal-management]] | Property: `MEAL_CHARGEBACK_REPORT` | Enablement: SE ticket | PB-63440.

- **Bulk Upload Template Upgrade** — versioned bulk-upload templates with improved clarity across modules; ships by default. [[modules/desk-management]] (and other modules) | Enablement: default | PB-63434.

- **Dynamic Label Configuration for Generic Resources** — desk/resource labels are now configurable via `dynamicDataForDesk` (allows renaming "Desk" across the product). [[modules/desk-management]] | Property: `dynamicDataForDesk` | Enablement: SE ticket | PB-63438.

---

### RN 02-2026

> raw evidence: `raw/se-runbook/crawl/files/1Yp3Cl0CP1c9-VMlPEsOeeNU79wBPxs-4HFYLgl2zeIU.pptx`

- **VMS: Employees may now check in as visitors** — employees visiting offices where they are not operationally mapped are treated as standard visitors and go through visitor policies; safeguards prevent real visitors from impersonating employees. [[modules/visitor-management]] | Enablement: NA (by default) | PB-62941.

- **VMS: Recurring visitor invites via Outlook** — Outlook-created recurring visitor invites are now fully supported with correct recurrence-pattern parsing, matching parity with web/mobile flows. [[modules/visitor-management]] / [[modules/ms-teams-integration]] | Enablement: NA | PB-61820.

- **Parking: Slot-level description on booking cards** — a text description can be attached to each parking slot (via `Description` column in `WITHOUT_FLOOR_PLAN` upload); shown on the employee booking card. [[modules/parking-management]] | Enablement: SE ticket + slot upload with Description column | PB-62503.

- **Meeting Rooms + Outlook Add-In enhancements** — includes showing organiser name on the Add-In timeline (config-gated). [[modules/meeting-rooms]] | Property: `showOrganiserNameAddInTimeline` (Meeting Rooms Service) | Enablement: SE ticket for organiser-name config | PB-62938.

- **Floor Kiosk: Configurable Floor Kiosk URL** — `floorKioskURL` (Emp Exp Common Config) can be set at BUID level to point the kiosk module at a different instance; default is the instance URL. [[modules/floor-kiosk]] | Property: `floorKioskURL` (Emp Exp Common Config, BUID level) | Enablement: SE ticket | PB-62657.

---

### RN 01-2026

> raw evidence: `raw/se-runbook/crawl/files/1K3-5yXJaRsuA78h-e-3XFlU7DSLaYQ_Y1Y1kXO3h7w8.pptx`

- **Visitor Management: OTP Failure Handling & Front Desk Override** — when self-check-in OTP delivery fails, visitors can indicate failure; front desk issues a time-bound (15-min, single-use) override PIN or skips OTP for walk-ins; OTP failure reasons captured in reports. [[modules/visitor-management]] | Properties: `enableOtpOverride` (enable the flow), `failureReasonsOtp` (configure reason list) | Enablement: SE ticket | PB-61863. ⚠️ The existing [[modules/visitor-management]] page already documents `enableOtpOverride` and the override-PIN mechanism — consistent, no contradiction. The RN adds `failureReasonsOtp` as a companion property not previously called out on the module page.

- **Safe Reach: DPDP compliance** — explicit consent capture with scroll/acknowledge requirement; signatures stored with timestamps; consent URL is privilege-gated; master phone numbers locked from employee edits; alternate-number capture added. [[modules/safe-reach]] | Properties: `enableConsentCheckboxSafeReach`, `consentCheckboxContentSafeReach`, `enableAlternatePhoneNumber`, `alternateNumberCheckboxContent` | Enablement: SE ticket | PB-61833.

- **Visitor Management: Structured name capture in Self Check-in** — First Name / Middle Name / Last Name fields added to the self-check-in flow (was single free-text field), matching Invite and Walk-in flows. [[modules/visitor-management]] | Property: `visitorFormsMetaDataPWC` | Enablement: SE ticket | PB-61818.

- **Visitor Management: Configurable DigiPass auto-send** — DigiPass (QR entry pass) can now be sent automatically on invite creation, without waiting for visitor acceptance; configurable immediate or buffered send. [[modules/visitor-management]] | Properties: `digipassAutoSend`, `digipassAutoSendBuffer` | Enablement: SE ticket | PB-61094.

- **Safe Reach Report: Checkout office & escalation matrix columns** — the Safe Reach report now exposes the office from which the employee checked out and details of escalation-matrix execution (calls/emails triggered). [[modules/safe-reach]] | Enablement: SE ticket to enable the required columns | PB-61094.

- **Parking: Waitlist expiry when booking start time elapses** — parking waitlists auto-expire once the booking start time passes; expiry shown in UI and mobile push; audit log entry created. [[modules/parking-management]] | Property: `Waitlist_Expiry_Enabled` | Enablement: SE ticket | PB-57576.

- **Employee Report: RFID column regression fix** — the RFID column (when RFID support is enabled) was missing from the downloaded Employee report due to a regression; now restored. [[modules/access-management]] | Enablement: no config change needed (bug fix) | PB in source deck (slide truncated in extracted text; see raw evidence).

---

## Linked Raw Evidence

| RN | raw_path |
|----|---------|
| RN 01-2026 | `raw/se-runbook/crawl/files/1K3-5yXJaRsuA78h-e-3XFlU7DSLaYQ_Y1Y1kXO3h7w8.pptx` |
| RN 02-2026 | `raw/se-runbook/crawl/files/1Yp3Cl0CP1c9-VMlPEsOeeNU79wBPxs-4HFYLgl2zeIU.pptx` |
| RN 03-2026 | `raw/se-runbook/crawl/files/1rdqLHaGiArmQCmazU6oZ_S4w7zP2Hn04cnHtKjhutGs.pptx` |
| RN 04-2026 | `raw/se-runbook/crawl/files/1H_LkfIQRvcFU8xz6pU3UiAYeUfHuKibS0hBmUAgOBO8.pptx` |
| RN 05-2026 | `raw/se-runbook/crawl/files/1lzPEF4pq0HZh7NObrD_YFcj8x56MWg7GJ1CO5wbR4Zo.pptx` |
