---
type: runbook
module: floor-kiosk
status: active
owner: WorkInSync Implementation Team
last_updated: 2026-06-29
sources:
  - raw/se-runbook/crawl/files/1V2f7ByWFnZAxqI4dwlslVdJsGotwXUmAiVLAfUryCjY.docx
  - raw/se-runbook/crawl/files/1JiKa1u42kbRJyms6__aFusHxhX9DGFlnDyQ1ZY_qZ-0.docx
  - raw/se-runbook/crawl/files/1_zYUYUOE_l9tDU2_VIL20Hwr2-nLsflw20cy8lxRSqU.docx
related_runbooks:
  - runbooks/floor-plan-upload
related_modules:
  - modules/floor-kiosk
  - modules/meeting-rooms
---

# Runbook — Floor Kiosk Device Setup (Scalefusion MDM)

## Purpose & Scope

This runbook covers the SE/implementation steps to:
1. Procure a compliant Android (or iPad) device
2. Factory-reset and enroll it into Scalefusion MDM
3. Grant required permissions and name the device
4. Enable remote monitoring (RemoteCast) for ongoing support

**Scope:** Generic Android kiosk and iPad devices managed by Scalefusion.
The enrollment procedure is the same whether the device will run the
**floor kiosk** or any other WorkInSync kiosk app — the app loaded depends on how
the device is configured in the Scalefusion dashboard after enrollment.

> ⚠️ **Meeting-room kiosk devices** follow the same enrollment procedure but use a
> different device naming convention and a different QR code. See [[modules/meeting-rooms]]
> and the "Meeting Room Kiosk Setup" doc (cross-link only — not duplicated here).

---

## Prerequisites

Before starting enrollment:

- [ ] Device meets the hardware spec — see [[modules/floor-kiosk]] §Hardware Specifications
  - Android 12.0+ (Android 10 or below: **not supported**)
  - 6 GB RAM minimum (12 GB optimal)
  - GPU: Adreno 640+ (Adreno 619 or below, Mali-400/450/T720/T760, Rockchip RK30xx, older MTK: **not supported**)
- [ ] Stable 24×7 internet connection available at the install location
- [ ] Wi-Fi credentials for the office network
- [ ] **Scalefusion QR code** — obtain from the WorkInSync Implementation Team
  (the QR code encodes the MDM enrollment policy and Scalefusion account)
- [ ] Device is **factory-reset** before starting (critical — a dirty device can cause enrollment failures)

---

## Android Device Enrollment

Two enrollment methods are available. Method 1 (afw#mobilock) is preferred for new Android devices; Method 2 (APK install) is the fallback.

### Method 1 — afw#mobilock (recommended)

1. Power on the device and connect to Wi-Fi.
2. When prompted for a Google account, type `afw#mobilock` in the Gmail ID field instead of an email address.
3. Wait for the Scalefusion MDM agent to download and install automatically.
4. The Scalefusion client opens and shows the Camera view — scan the **QR code** provided by the WorkInSync Implementation Team.
5. Complete the setup wizard.
6. **Grant static permissions**: on the permissions screen, toggle on each permission card and click **Next**.
   - Ensure the **Remote Sharing** permission is enabled (required for RemoteCast).
7. When prompted for group enrollment, click **Scan QR icon** and scan the **same QR code** again.
8. Enter the **device name** (see §Device Naming below).
9. Click **Submit**.
10. Verify the device shows both the **Remote Sharing** (RemoteCast) application and the **MoveInSync Workplace** application.

### Method 2 — APK install (fallback)

Use when the device has an existing Android setup and cannot reach the afw#mobilock step.

1. Factory-reset the device.
2. Boot normally (no Google account needed — skip adding one).
3. Screen lock is optional; advised not to enable one.
4. Enable a stable 24×7 internet connection.
5. Enable screen rotation on the device.
6. After restart, install the **Scalefusion APK** from the official Scalefusion link
   (obtain the URL from the WorkInSync Implementation Team — not hardcoded here).
7. Open the Scalefusion app → tap **Scan QR Code** → scan the QR code.
8. Grant all requested permissions. Skip "Disable Assist App" if prompted.
9. Click **Next** and complete setup.
10. On the group enrollment screen, enter:
    - **Group Enrollment Code**: `<enrollment-code>` (provided by WorkInSync Implementation Team — treat as a credential; do not store in wiki)
    - Click **Scan QR icon** → scan the same QR code again.
11. Enter the **device name** (see §Device Naming below).
12. Click **Submit**.

---

## Device Naming Convention

> ⚠️ The source doc's example uses meeting-room naming (`WorkInSync - Audi - MR Kiosk`).
> For floor kiosk devices, confirm the naming convention with the Implementation Team — a
> floor-kiosk-specific pattern (e.g. `<OrgName> - Floor <N> FK`) has not been documented yet.

Suggested pattern (meeting-room source example, adapt for floor kiosk):

```
<Organization Name> - <Location/Floor Identifier> - <Device Type>
Example (MR): WorkInSync - Audi - MR Kiosk
Example (FK): <OrgName> - Floor <N> - FK  ← placeholder; confirm with owning team
```

---

## iPad Device Enrollment

### iOS 12.2 and newer

1. Open the **Camera** app.
2. Scan the QR code provided by WorkInSync Implementation Team.
3. When prompted, tap to **Launch Safari**.
4. Download the **Configuration profile**.
5. Open the **Settings** app → tap **Profile Downloaded** → tap **Install**.
6. Follow onscreen prompts → tap **Done** when complete.

### iOS 12.2 and older

1. Open the **Camera** app → scan the QR code.
2. When prompted, **Launch Safari** → tap **Allow** to open Settings.
3. Tap **Install** → follow onscreen instructions → tap **Done**.

---

## Enabling Remote Monitoring (RemoteCast)

RemoteCast allows the Implementation Team to screen-cast and debug devices remotely from the Scalefusion Dashboard. Set this up immediately after enrollment.

1. **Exit the kiosk app first**: swipe from the **bottom-left** of the screen to the **center** of the screen (this gesture is specific to Scalefusion's guided mode).
2. Navigate to the last option in the menu → select **"Exit Scalefusion"**.
3. On the device home screen, open the **RemoteCast** app.
4. Grant all permissions requested by RemoteCast.
5. Confirm all permissions are granted.
6. Remote casting is now available from the Scalefusion Dashboard.

> ⚠️ Known field observations (from source doc, treat as context not guaranteed spec):
> - Devices left in sleep mode overnight may not pick up app updates pushed via Scalefusion — the device-level sleep settings and overlay permissions should be verified.
> - If a device shows no responsiveness to touch, check overlay permissions in Scalefusion for that device.
> - RemoteCast must be set up per device; it does not auto-configure from the MDM policy alone (unconfirmed — verify with Scalefusion support).

---

## Post-Enrollment Verification

- [ ] Device is visible in the Scalefusion Dashboard under the correct group
- [ ] MoveInSync Workplace app is installed and launches correctly
- [ ] RemoteCast / Remote Sharing is enabled and visible in the dashboard
- [ ] Kiosk mode is active — back button is disabled, URL bar is not accessible
- [ ] Device name matches naming convention (see §Device Naming)

---

## Related

- **Floor plan upload:** [[runbooks/floor-plan-upload]] — after device setup, upload the floor plan before going live
- **Meeting room kiosk devices:** [[modules/meeting-rooms]] — same enrollment procedure, different QR code and app configuration
- **Hardware requirements:** [[modules/floor-kiosk]] §Hardware Specifications — verify device before purchasing

---

## Open Questions

- Floor kiosk device naming convention — the source only shows the MR Kiosk example naming. Confirm the FK naming pattern with the Implementation Team.
- Scalefusion QR code provisioning process — who generates it and where is it stored? Not documented in source.
- Group enrollment code — is it per-client or per-MDM-group? Source shows a blank placeholder; treat as credential.
- Sleep mode + update issue: is there a Scalefusion policy override for devices left idle? Source flags this as a known problem without a confirmed fix.

## Last Updated

2026-06-29 — _Source: [[sources/se-runbook-floor-kiosk]]_
