---
type: runbook
module: visitor-management
team: SE
status: active
last_updated: 2026-06-29
source: "[[sources/se-runbook-visitor-management]]"
raw_path: raw/se-runbook/crawl/files/1dO-uRIGCdv-U531pRMhzE6Dv9AWMX0tFgcsQ3LIQ1YI.docx
---

# Visitor Badge Printer Setup

## Purpose
Configure the recommended thermal label printer for visitor badge printing at the front desk. Covers hardware selection, connectivity, and roll specification. The broader VMS office config enablement (kiosk URLs, module toggles) lives primarily in screenshot-heavy sections of the source doc not captured in the text extract — see Linked Raw Evidence below.

## Prerequisites
- VMS enabled for the BUID (front-desk badge printing feature active).
- Physical access to the front desk workstation that will drive the printer.
- Wi-Fi / wired LAN credentials for the office network.

## Ordered Steps

### 1. Procure the recommended printer
The SE-recommended badge printer model is the **Brother QL-820NWB Professional Label Printer**.

| Attribute | Value |
|-----------|-------|
| Company | Brother |
| Model | QL-820NWB |
| Printing technology | Direct thermal (2-colour capable: red + black) |
| Compatibility | Android, iOS, laptops, tablets |
| Connectivity | USB, Wi-Fi (including AirPrint), wired Ethernet, Bluetooth |
| Suggested roll sizes | 62×100 mm continuous roll; sticker roll |

> Note: Other printer models may work but are not SE-tested. The QL-820NWB is the only model in the SE configuration SOP.

### 2. Load the correct label roll
- Use **62×100 mm continuous roll** for standard visitor badges.
- Sticker rolls are an alternative if adhesive badges are required.
- Install the roll according to Brother's hardware guide (see raw doc for diagrams).

### 3. Connect the printer to the workstation
Choose one connectivity method:
1. **USB** — plug directly into the front-desk workstation. Simplest; no network config needed.
2. **Wi-Fi** — join the same Wi-Fi network as the workstation. Supports AirPrint for iPad kiosks.
3. **Wired Ethernet** — connect to office LAN switch. Most reliable for high-traffic lobbies.
4. **Bluetooth** — use for tablet-driven setups; pair with the front-desk tablet.

### 4. Install Brother driver / app
- Windows/Mac front-desk: install the Brother QL series driver from Brother support.
- iOS/Android kiosk tablets: use the Brother iPrint&Label app.

### 5. Configure the badge template in WorkInSync
- Badge template (org logo, fields) is configured via the WIS admin console under Visitor Management → Badge Settings.
- Ensure the template dimensions match the loaded roll (62×100 mm).
- Test-print a sample badge to confirm alignment.

### 6. Validate end-to-end
- Check in a test visitor through the front desk.
- Confirm the badge prints with correct visitor name, photo (if configured), and org logo.
- Verify the audit trail entry appears (who printed, timestamp, count = 1).

## Screenshots
The source document (`1dO-uRIGCdv-U531pRMhzE6Dv9AWMX0tFgcsQ3LIQ1YI.docx`) contains full-page screenshots of the WIS admin badge-configuration UI and additional office-enablement steps. The text extract captured only the printer hardware specs; refer to the raw file for the visual walkthroughs.

## Validation
- Badge prints without errors from the front-desk workstation.
- Print audit log is visible in Visitor Management → Reports.
- Badge dimensions match the roll (no clipping or overflow).

## Notes & Gotchas
- The QL-820NWB supports 2-colour printing (red + black) — useful for VIP visitor badging if the template uses colour.
- AirPrint works only when the printer is on Wi-Fi; USB-only mode disables AirPrint.
- If using an iPad kiosk for badge printing, Bluetooth pairing must be done fresh after any iOS update resets Bluetooth state.
- ⚠️ The broader VMS office-config setup (enabling kiosk flows, setting PMS properties for the office) is documented in the source doc's screenshot sections — not captured in the SE crawl text extract. Contact the SE team for the full visual SOP.

## Related Jira
—

## Linked Raw Evidence
- `raw/se-runbook/crawl/files/1dO-uRIGCdv-U531pRMhzE6Dv9AWMX0tFgcsQ3LIQ1YI.docx` — "Visitor Management - Configuration of Badge Printer" (v1.0, 2024-03-12, author: Kavya Sridharan, approved by: Ujjwal Trivedi). Contains full admin-UI screenshots not captured in text extract.

_Source: [[sources/se-runbook-visitor-management]]_
