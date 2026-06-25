---
type: runbook
module: guard-app-kiosks
team: SE (Service Engineering)
status: active
last_updated: 2026-06-25
source: "[[sources/se-runbook-ets-office-premise]]"
raw_path: raw/se-runbook/WIS-Configurations-ETS-EmployeeApp-GuardApp-SanitisationApp.docx
---

# Runbook — Guard App Setup

## Purpose & Scope
Covers Guard App access links (non-IOT manual temperature entry and IOT auto-capture), the deprecated old Guard App link, amenities configuration via Postman, and a set of operational useful links for cache eviction and eligibility/willingness/COVID-declaration checks. Guard User creation is a separate runbook. Floor-kiosk, parking, and ETS office premise setup are also separate runbooks (see Configuration Flow below).

_Source: [[sources/se-runbook-ets-office-premise]]_

---

## Prerequisites
- A configured BUID for the target customer
- The appropriate Guard App `premiseId` (UUID) for amenities operations
- Postman (or equivalent HTTP client) for the Amenities API call
- Bearer token / admin credentials for PMS APIs where required
- Confirm which server the client is on (`.com` / `.in` / `.eu`) before using any URL — see Notes & Gotchas

---

## Configuration Flow (where this fits)

```
ETS Office Premise Setup
        ↓
Parking Premise Setup
        ↓
Guard App Setup   ← THIS RUNBOOK
        ↓
Guard User Creation  (separate runbook)
        ↓
Floor Kiosk Setup    (separate runbook)
```

---

## Step-by-step

### A — Choose the correct Guard App link (non-IOT vs IOT)

Two separate Guard App URLs exist for different deployment modes. Choose based on whether an IOT temperature device is present.

#### Mode 1 — Manual app: Without IOT device (temperature manual entry)

The guard enters temperature manually.

**App URL:**
```
https://wis-reception.workinsync.io/
```

**Login flow (in order):**
1. Open the URL above on the guard's device
2. Enter mobile number
3. Tap **Get OTP**
4. Enter the OTP received
5. Select Office
6. Choose Gate
7. Tap **Start Duty**

_Source: [[sources/se-runbook-ets-office-premise]] sec30_

---

#### Mode 2 — With IOT device (temperature auto-captured)

Temperature is captured automatically from the connected IOT device. The guard does not enter temperature manually.

**App URL:**
```
https://mis-security-beta.moveinsync.com/
```

> ⚠️ This URL contains `-beta` in the hostname. Confirm with the implementation team that this is the intended production endpoint for the client's IOT-enabled guard setup — the source section labels it as the IOT device link without further qualification.

_Source: [[sources/se-runbook-ets-office-premise]] sec31_

---

### B — Deprecated old Guard App link

> ⚠️ **DEPRECATED / OLD LINK** — The source document marks this section explicitly as "OLD Guard App Link". Do not share this URL with clients for new setups. It is retained here for historical reference only.

**Old URL (do not use for new clients):**
```
https://mis-security.moveinsync.com
```

The current links are in Step A above (`wis-reception.workinsync.io` for non-IOT, `mis-security-beta.moveinsync.com` for IOT).

_Source: [[sources/se-runbook-ets-office-premise]] sec32_

---

### C — Amenities Setup

Amenities define seat-level attributes (e.g. monitor count, standing desk, cabin) that employees can filter on when booking via Employee Experience. This step configures amenities for premises using the Guard Security API.

**Related Employee Experience config flag:**
```
isAmenitiesFilter=true
```
Set this flag on the client's Employee Experience config to enable amenity filtering in the booking UI.

For a full module-level doc on Amenities and QR codes, see [[modules/guard-app-kiosks]] (linked: "Module wise doc on Amenities & QR code").

#### C1 — Call the Amenities API

**Method:** `PUT`
**Use case:** Add new amenities or delete existing ones for a premise.
**Tool:** Postman (or equivalent)

**Endpoint — SG & Normal WIS sites (.com / .in):**
```
https://mis-security.moveinsync.com/mis-security-guard/api/amenities/premises?buid=wfosa-wfoza&requestorGUID=admin
```
Replace `wfosa-wfoza` with the client's BUID (example — replace with the client's).

**Endpoint — EU sites:**
```
https://mis-security.eu.moveinsync.com/mis-security-guard/api/amenities/premises?buid={BUID}&requestorGUID=admin
```
Replace `{BUID}` with the client's BUID (example — replace with the client's).

**Request body — Raw JSON format:**
```json
[
  {
    "amenities": [
      {
        "name": "DESKTOP",
        "polygonType": "SEAT"
      },
      {
        "name": "Window seat",
        "polygonType": "SEAT"
      },
      {
        "name": "Phone/Speaker",
        "polygonType": "SEAT"
      },
      {
        "name": "1 Monitor",
        "polygonType": "SEAT"
      },
      {
        "name": "2 Monitors",
        "polygonType": "SEAT"
      },
      {
        "name": "Printer/Scanner",
        "polygonType": "SEAT"
      },
      {
        "name": "CABIN",
        "polygonType": "SEAT"
      },
      {
        "name": "Standing Desk",
        "polygonType": "SEAT"
      },
      {
        "name": "IP Phone",
        "polygonType": "SEAT"
      }
    ],
    "premiseId": "c7e25c88-4620-4b88-a48e-bfac7d7391c8"
  }
]
```
Replace `premiseId` value with the actual premise UUID for the client (example — replace with the client's).

> ⚠️ The source JSON contains a stray `[` after `"Printer/Scanner",` — this is a typo in the original source document. The corrected JSON above (with the stray bracket removed) is the intended valid payload.

**Screenshot reference:** `raw/se-runbook/images/sec33_img040.png` — shows Postman configured for this PUT request with the URL, Body tab selected, raw JSON format, and the "Send" button. The `buid` query parameter is left empty in the screenshot; populate it before sending.

#### C2 — Seat Tag Amenity Bulk Upload (template download)

If assigning amenities via bulk seat-tag upload:

**Template download link:**
```
http://staging2.moveinsync.com:9095/mis-security-guard/seat/downloadFile/template
```

> ⚠️ This URL uses `staging2.moveinsync.com` on port `9095`. The source document does not clarify whether a production equivalent exists — use only if confirmed applicable by the implementation team. (Example — replace with the environment's actual host if different.)

_Source: [[sources/se-runbook-ets-office-premise]] sec33_

---

## Useful Links

These operational links are used by SE for cache eviction and eligibility/willingness/declaration checks. Replace BUID placeholders with the client's actual BUID before use.

### Cache eviction (Booking Rule Engine)

**Issue:** If created Shifts are not syncing in the front end, evict the cache using these links (change BUID as needed):

| Purpose | URL |
|---------|-----|
| Evict premise cache | `https://bookingrule.moveinsync.com/booking-rule-engine/cahce/wis-WISAUS/evict/premise` |
| Evict shifts cache (LOGOUT) | `https://bookingrule.moveinsync.com/booking-rule-engine/cahce/wis-WISAUS/evict/shifts/LOGOUT` |
| Evict shifts cache (LOGIN) | `https://bookingrule.moveinsync.com/booking-rule-engine/cahce/wis-WISAUS/evict/shifts/LOGIN` |

Replace `wis-WISAUS` with the client's BUID (example — replace with the client's).

> ⚠️ The URLs above contain `cahce` (not `cache`) — this is the exact spelling from the source document. Use as-is; do not correct when calling the endpoint.

### Employee Experience — eligibility / willingness / COVID declaration checks

Replace `airtel-APOC` with the client's BUID (example — replace with the client's).

| # | Purpose | URL |
|---|---------|-----|
| 1 | Check Eligibility with default content | `https://empexp.moveinsync.com/employee-exp/static/in-app-popup/static/index.html#/eligibility?buid=airtel-APOC` |
| 2 | Check Willingness with default content | `https://empexp.moveinsync.com/employee-exp/static/in-app-popup/static/index.html#/willingness?buid=airtel-APOC` |
| 3 | Check COVID Declaration with default content | `https://empexp.moveinsync.com/employee-exp/static/in-app-popup/static/index.html#/covid-declaration?buid=airtel-APOC` |

### Check premise details via API

```
GET https://mis-security.moveinsync.com/mis-security-guard/premise/dafeaf24-bfed-7b9679077ed0
```
Replace the UUID (`dafeaf24-bfed-7b9679077ed0`) with the actual `premiseId` (example — replace with the client's).

_Source: [[sources/se-runbook-ets-office-premise]] sec34_

---

## Screenshots

| File | Section | What it shows |
|------|---------|---------------|
| `raw/se-runbook/images/sec33_img040.png` | sec33 — Amenities | Postman PUT request to the amenities endpoint: method selector (PUT), URL bar with `buid` and `requestorGUID` params, Body tab (raw JSON), example amenities payload, and the Send button. Numbered callouts 1–6 guide the user step-by-step. |

No screenshots exist for sec30 (non-IOT app), sec31 (IOT app), sec32 (old link), or sec34 (useful links) — text-only sections.

---

## Validation checklist

- [ ] Non-IOT: `https://wis-reception.workinsync.io/` loads and the OTP flow completes successfully
- [ ] IOT: `https://mis-security-beta.moveinsync.com/` loads on the guard's device
- [ ] Amenities PUT returns HTTP 200; amenities appear in Employee Experience booking UI (requires `isAmenitiesFilter=true`)
- [ ] Cache eviction links return success for the client's BUID when shifts are not syncing

---

## Notes & Gotchas

1. **Two distinct Guard App URLs exist** — `wis-reception.workinsync.io` (non-IOT, manual temperature) vs `mis-security-beta.moveinsync.com` (IOT, auto-captured temperature). Using the wrong one will result in an app that doesn't match the hardware setup.

2. **Old link still resolves** — `https://mis-security.moveinsync.com` (sec32) is labelled "OLD" in the source. It may still be live but should not be shared for new client setups. Prefer the links in Step A.

3. **EU clients need a different amenities endpoint** — `mis-security.eu.moveinsync.com` instead of `mis-security.moveinsync.com`. Always confirm region before sending.

4. **`cahce` is not a typo in the cache-eviction URLs** — the Booking Rule Engine path literally contains `cahce` (misspelled in the service's URL). Copy the URL exactly; do not "fix" the spelling.

5. **`premiseId` in the amenities JSON** — the example body contains `"premiseId": "c7e25c88-4620-4b88-a48e-bfac7d7391c8"` which is a sample value from the source. Replace with the actual premise UUID. The GET premise-details link in Useful Links can retrieve the `premiseId` for a given BUID.

6. **Staging bulk-upload template** — the seat-tag amenity bulk-upload template URL (`staging2.moveinsync.com:9095`) points to a staging host. Confirm a production equivalent exists before using for a live client.

7. **`isAmenitiesFilter=true`** — without this Employee Experience config flag, the amenity filter will not appear in the booking UI even if amenities are configured via the API.

8. **`requestorGUID=admin`** — required query parameter for the amenities PUT. The OCR confirms the `Authorization` tab is visible (8 headers pre-configured in the Postman screenshot) but the source does not document what those headers are — confirm with the platform team if auth failures occur.

---

## Related

- [[modules/guard-app-kiosks]] — parent module page
- [[runbooks/ets-office-premise-setup]] — ETS office premise (prerequisite context)
- [[runbooks/parking-premise-setup]] — Parking premise setup
- [[modules/employee-experience]] — `isAmenitiesFilter` config flag lives here
- [[modules/booking-rule-engine]] — cache eviction URLs target this service

### Related Jira
None linked in the source sections (sec30–34).

---

## Last Updated
2026-06-25 — source: [[sources/se-runbook-ets-office-premise]], sections sec30–sec34
