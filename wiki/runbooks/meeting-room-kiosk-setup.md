---
type: runbook
module: meeting-rooms
team: SE
status: active
last_updated: 2026-06-29
source: "[[sources/se-runbook-kiosk]]"
raw_paths:
  - raw/se-runbook/crawl/files/1EEGOioCsfA6gg1tBj6hH4Mw7thsXT9hUX1AJFYv_3GE.docx
  - raw/se-runbook/crawl/files/1y0KGfTzmCU-PG8D6FWq4m6DkZT7EBpUE4Lq0D4lkiKY.docx
related_modules:
  - modules/meeting-rooms
  - modules/floor-kiosk
related_runbooks:
  - runbooks/floor-kiosk-device-setup
---

# Runbook — Meeting Room Kiosk Setup

## Purpose

This runbook covers SE/implementation setup of the **meeting-room kiosk** — a tablet mounted
outside each room that shows the room status and allows employees to check in, extend, or
cancel bookings.

There are two deployment paths:

| Path | MDM | Suitable for |
|------|-----|-------------|
| Without MDM | Manual device lockdown | Small deployments, quick pilots |
| With MDM (Scalefusion) | Managed enrollment + remote access | Production deployments (**recommended**) |

> ⚠️ This runbook covers meeting-room kiosk specifics. Device factory-reset and Scalefusion
> MDM enrollment follow the **same procedure** as floor kiosks — see
> [[runbooks/floor-kiosk-device-setup]] for the shared Android and iPad enrollment steps,
> RemoteCast setup, and post-enrollment checklist. Differences specific to meeting-room kiosks
> are called out below.

_Source: [[sources/se-runbook-kiosk]]_

---

## Prerequisites

Before starting:

- [ ] Confirm the client's site URL (e.g. `testsite.workinsync.io` or `test.moveinsync.com`)
  and which region/server they are on (see kiosk URL table in Step 4b)
- [ ] Have **Admin access** to the Meeting Rooms Settings page on the site URL
- [ ] Stable 24×7 internet and power available at the tablet's wall mount location
- [ ] Device is factory-reset — **do NOT skip** (dirty device causes enrollment failures)
- [ ] For Scalefusion path: obtain the **meeting-room kiosk QR code** from the Implementation
  Team (different QR code than the floor kiosk — do not mix them up)
- [ ] `MEETING_ROOM_ENABLED` PMS config is set to `true` for the BUID (prerequisite for kiosk
  pairing to work)

_Source: [[sources/se-runbook-kiosk]]_

---

## Ordered Steps

### Path A — Without MDM

**Step 1 — Install the app**

Download and install the **MoveInSync Workplace** app on the tablet:
- Android: Google Play Store
- iOS: Apple App Store

**Step 2 — Select Meeting Room mode**

Open the MoveInSync Workplace app → select the **Meeting Room** option.
The app will prompt for a **6-digit pin** to pair with a room.

**Step 3 — Generate the pairing pin (Admin action)**

On the admin site:
1. Open Site → Side Nav → **Meeting Rooms** → Settings icon (top right)
2. Under the **Kiosk Mapping** column, locate the target room
3. A room with no tablet shows "not linked"
4. Click the link icon (`🔗`) next to the room — a **6-digit pin** appears

**Step 4 — Pair the device**

Enter the 6-digit pin on the tablet screen → select **Map Room**. The device is now mapped to
that meeting room.

**Step 5 — Device lockdown (manual, without MDM)**

After pairing, enforce the following manually on the tablet:

- [ ] MoveInSync Workplace app set to run at all times (auto-launch on boot)
- [ ] Navigation bar and notification menu disabled
- [ ] Power button disabled or blocked (physically or via accessibility settings)
- [ ] Display set to **Always On** / "Never" timeout
- [ ] Screen Orientation: Auto-rotate
- [ ] 24×7 internet and power connection confirmed

---

### Path B — With MDM (Scalefusion, Recommended)

**Step 1 — Factory reset and MDM enrollment**

Follow **[[runbooks/floor-kiosk-device-setup]]** for:
- Factory reset procedure
- Scalefusion APK download and installation
- QR code scan to enroll into MDM
- Permission grants (skip "Disable Assist App")
- RemoteCast / Remote Sharing setup

**Differences from floor kiosk enrollment:**

| Item | Floor kiosk | Meeting room kiosk |
|------|-------------|-------------------|
| QR code | Floor kiosk QR | Meeting-room kiosk QR (obtain from Implementation Team separately) |
| Device naming | `<OrgName> - Floor <N> - FK` (TBD) | `<Organization Name> - <Meeting Room Name> MR Kiosk` |
| Naming example | — | `WorkInSync - Audi MR Kiosk` |

**Step 2 — Name the device**

During Scalefusion enrollment, at the **Device Name** prompt, enter:
```
<Organization Name> - <Meeting Room Name> MR Kiosk
```
Example: `WorkInSync - Audi MR Kiosk`

**Step 3 — Install the kiosk app via MDM**

Once enrolled, push the MoveInSync Workplace app to the device via Scalefusion.
Depending on the MDM policy, either:
- Upload the **APK file** (Android PWA) provided by the WorkInSync team, or
- Push from **Google Play Store** through the Scalefusion dashboard

For iOS devices:
- Upload the **.ipa file** (PWA) provided by the WorkInSync team, or
- Push from **Apple App Store** via Scalefusion

**Step 4 — Pair the device to a room (two sub-options)**

**Option 4a — Via App (recommended)**

1. Open MoveInSync Workplace app on the tablet → select **Meeting Room**
2. The app shows a 6-digit pin prompt
3. Generate the pin on the admin site: Site → Meeting Rooms → Settings → `🔗` icon next to
   the target room
4. Enter the pin on the tablet → **Map Room** → device paired

**Option 4b — Via Web URL (if MDM supports URL-based kiosk lockdown)**

Use the kiosk URL appropriate for the client's region:

| Region | Kiosk URL |
|--------|-----------|
| SG-Blue | `ui.moveinsync.com/kiosk/#/kiosk-dashboard` |
| EU-Blue | `ui.eu.workinsync.io/kiosk/#/meeting-room/` |
| EU-Green | `green-ui.eu.workinsync.io/kiosk/#/meeting-room/` |
| India | `https://ui.moveinsync.in/kiosk/#/meeting-room/setup` |

> ⚠️ Use the URL confirmed by the WorkInSync team for the client — do not assume based on
> company name alone. Confirm which region server the client is on before setting the URL.

On opening the kiosk URL, enter the 6-digit pin generated from the admin site to pair the room.

**Step 5 — Enable RemoteCast (remote debugging)**

Follow **[[runbooks/floor-kiosk-device-setup]]** §Enabling Remote Monitoring (RemoteCast).

Meeting-room kiosk specific: to exit the MR app before enabling RemoteCast, swipe from the
**bottom-left of the screen to the center** → select **Exit Scalefusion** (back to home screen)
→ open RemoteCast app → grant all permissions → re-open Scalefusion and enter pairing pin +
email to complete setup.

---

## Relevant PMS Config Keys

These config properties directly affect kiosk behavior. All are BUID-level unless noted.
Full config table lives in [[modules/meeting-rooms]] §Key Configurations.

| Config Key | Type | Default | Kiosk Relevance |
|---|---|---|---|
| `MEETING_ROOM_ENABLED` | boolean | false | Master switch — kiosk pairing will not work if false |
| `SHOW_UPCOMING_BOOKINGS_TIME` | integer (min) | 6 | Minutes before booking start to show check-in prompt on kiosk screen |
| `MEETING_EMAIL_OTP_TO_AUTHENTICATE` | boolean | true | Whether a PIN email is sent to the organizer for kiosk cancel/end actions |
| `CANCEL_EVENT_PIN_VERIFICATION_ENABLE` | boolean | false | Require PIN verification before allowing a cancellation on the kiosk |
| `RELEASE_MEETING_ROOM` | boolean | false | Whether auto-release of unchecked rooms is active |
| `MEETING_ROOM_RELEASE_IF_NO_CHECKIN` | integer (min) | 180 | Minutes before auto-release; **15 min recommended** in production |

_Source: [[sources/se-runbook-kiosk]], [[modules/meeting-rooms]]_

---

## Screenshots

Visual step-by-step screenshots are embedded in the source document (Control Document 2025).
See raw evidence file: `raw/se-runbook/crawl/files/1EEGOioCsfA6gg1tBj6hH4Mw7thsXT9hUX1AJFYv_3GE.docx`

Key screenshots include: app Meeting Room selection screen, 6-digit pin prompt, admin Kiosk
Mapping table with link icon, Map Room confirmation, Scalefusion enrollment page.

---

## Validation

After setup, verify:

- [ ] Device appears in Scalefusion Dashboard under the correct group (MDM path only)
- [ ] Device name matches `<Org Name> - <Room Name> MR Kiosk` convention
- [ ] MoveInSync Workplace app is running in kiosk mode — navigation bar hidden, URL bar inaccessible
- [ ] Room shows as **linked** in Meeting Rooms Settings → Kiosk Mapping column
- [ ] Kiosk displays the room's upcoming booking schedule
- [ ] Check-in action works: tap check-in → booking marked active
- [ ] Cancel/end action works (verify PIN prompt if `CANCEL_EVENT_PIN_VERIFICATION_ENABLE=true`)
- [ ] RemoteCast is enabled and visible in Scalefusion dashboard (MDM path only)
- [ ] Display stays on — no timeout (auto-off confirmed disabled)

---

## Notes & Gotchas

- **QR codes are NOT interchangeable.** The meeting-room kiosk Scalefusion QR encodes a different
  MDM policy group than the floor kiosk QR. Using the wrong QR will enroll the device in the
  wrong Scalefusion group — re-enrollment required to fix.
- **Screen lock is optional but not recommended.** The Scalefusion prereq doc advises no screen
  lock on the tablet; a lock creates friction if a reboot requires manual unlock before kiosk
  mode resumes.
- **Google account not required.** Scalefusion manages app delivery; a personal Google account
  does not need to be signed in on the device.
- **Admin pin is single-use per pairing.** The 6-digit pairing pin generated in Meeting Rooms
  Settings is valid for one pairing. If a device needs to be re-paired (e.g. after factory
  reset), generate a new pin.
- **`MEETING_ROOM_ENABLED` must be true.** The kiosk pairing step will silently fail or show
  an error if Meeting Rooms is not enabled for the BUID. Confirm this config before onsite setup.
- **Kiosk URL path (Option 4b) requires MDM to support URL lockdown.** Scalefusion supports
  this; other MDMs may not. Confirm MDM capability before using the URL path.
- **Suggested mount:** the source doc references a mount link (hardware mount for the tablet
  on room door-frame); check raw file for the specific link — not reproduced here.

---

## Related Jira

—

---

## Linked Raw Evidence

| Doc | Raw path |
|-----|----------|
| Meeting Room Kiosk Setup — Control Document (2025, v1.1) | `raw/se-runbook/crawl/files/1EEGOioCsfA6gg1tBj6hH4Mw7thsXT9hUX1AJFYv_3GE.docx` |
| Meeting Room Kiosk — Scalefusion Prerequisites | `raw/se-runbook/crawl/files/1y0KGfTzmCU-PG8D6FWq4m6DkZT7EBpUE4Lq0D4lkiKY.docx` |

_Source: [[sources/se-runbook-kiosk]]_
