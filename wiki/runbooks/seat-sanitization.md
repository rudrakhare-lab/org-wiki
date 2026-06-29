---
type: runbook
module: sanitization
team: SE (Service Engineering)
status: active
last_updated: 2026-06-29
source: "[[sources/se-runbook-sanitization]]"
raw_path: raw/se-runbook/_extract/sections/
---

# Runbook — Seat Sanitization Setup

## Purpose
Step-by-step procedure for an SE engineer to set up the Seat Sanitization feature for a new BUID. Covers: enabling the UI view (TO team dependency), creating HOUSEKEEPER users, toggling QR-code scan enforcement, and setting the sanitization cut-off time.

Run this when:
- A client is being onboarded with a sanitization requirement
- A client requests housekeeping staff access to mark seats clean
- QR-code scan mode is being enabled or disabled for an existing sanitization deployment

## Prerequisites
- Postman (or equivalent API client) with a valid auth token for `mis-security-guard`
- BUID for the client
- Phone numbers for each HOUSEKEEPER user to be created
- Frappe Tool access (SG or EU region, for config verification)
- Consul access (for TO team step — raise a TO ticket if you don't have direct access)
- Sanitization URL: `https://mis-premise.moveinsync.com/mis-floor-plan/#/sanitisation`

## Configuration Flow Context
In the broader SE onboarding flow, Seat Sanitization sits after Guard User creation:

```
Office Premise creation
Add Capacity to Office
Floor premise creation
Guard User creation
→ Seat Sanitization — HOUSEKEEPER User creation  ← this runbook
Meal Booking — Create Cafeteria premise
```

## Ordered Steps

### Step 1 — Enable the sanitization status UI view [TO team]

> **This step is performed by the TO (Technical Operations) team, not SE.** Raise a TO ticket to have them complete it before proceeding.

- Path: Consul → TeamManager Service → `{buid}` config
- Set: `"SANITISATION_STATUS_ENABLED": true`

Once enabled, the sanitization status column appears on the admin floor view and the employee booking card.

---

### Step 2 — Create one or more HOUSEKEEPER users [SE team]

For each housekeeping staff member who will scan and mark seats:

**Tool:** Postman

**Endpoint:** `POST https://mis-security.moveinsync.com/mis-security-guard/user`

**Request body** _(all values below are examples/placeholders — substitute real values)_:
```json
{
  "phoneNumber": "<housekeeper-phone-number>",
  "role": "3",
  "buid": "<client-buid>",
  "name": "<housekeeper-name>",
  "status": "ACTIVE",
  "type": "HOUSEKEEPER"
}
```

> Example from source (do not copy literally): `"phoneNumber": "1234567890"`, `"buid": "eu-TestBed"`, `"name": "Jovil"` — observed in SE runbook as illustration only.

**Expected response (HTTP 200)**:
```json
{
  "userId": "<generated-uuid>",
  "phoneNumber": "<housekeeper-phone-number>",
  "role": "WORKER",
  "buid": "<client-buid>",
  "superVisorId": null,
  "name": "<housekeeper-name>",
  "serviceStartTime": null,
  "serviceEndTime": null,
  "status": "ACTIVE",
  "type": "HOUSEKEEPER"
}
```

Note: `role` resolves to `"WORKER"` in the response even though `"3"` was sent in the request body.

**To verify an existing HOUSEKEEPER/Guard user by phone number:**
```
GET https://mis-security.moveinsync.com/mis-security-guard/login/phoneNumber/<phone-number>
```
Use this to check whether a user already exists before creating a duplicate.

---

### Step 3 — Enable or disable QR-code scan for seat sanitization [SE team]

**Tool:** Frappe Tool (SG or EU region) or Postman

**Service:** `mis-security-guard`

**Config key:** `enableQrCodeForSeatSanitize`

- Set to `true` to require housekeepers to scan a QR code attached to the seat/floor
- Set to `false` to allow housekeepers to select a floor manually and mark all seats without scanning

> **Gotcha:** If QR codes are not yet printed and affixed to seats, leave `enableQrCodeForSeatSanitize` as `false` until physical QR deployment is complete. Enabling it before QR codes are in place will block housekeepers from marking any seats.

---

### Step 4 — Set the sanitization cut-off time [SE team]

**Tool:** Frappe Tool (SG or EU region) or Postman

**Service:** `mis-security-guard`

**Config key:** `seatSanitizeCuttoffInMinute`

Set this to the number of minutes after a booking start (or booking end + sign-out) at which the seat is flagged as requiring sanitization.

> **Anomaly note:** The source runbook shows `"seatSanitizeCuttoffInMinute": true` (boolean) rather than a numeric value. The property name implies a duration in minutes (DOUBLE type per KB). The `: true` appearance in the source is likely a copy error in the runbook example — confirm the correct numeric value with the owning team before setting.

## Screenshots
- `sec49_img045.png` — Vaccination Center premise creation screen; shows Consul/Postman setup for `vaccinationBookingEnabled`. Not directly part of seat sanitization flow but filed adjacent in the source.

## Validation
- [ ] Hit `GET .../mis-security-guard/login/phoneNumber/<phone>` for each created HOUSEKEEPER user — confirm response returns the user with `"type": "HOUSEKEEPER"` and `"status": "ACTIVE"`
- [ ] Log in to the sanitization URL (`https://mis-premise.moveinsync.com/mis-floor-plan/#/sanitisation`) using a HOUSEKEEPER phone + OTP — confirm the scanner/floor-selection page loads
- [ ] On the admin floor view, confirm the sanitization status column is visible (requires Step 1 complete)
- [ ] Make a test desk booking and verify the last sanitization time of the target seat is displayed

## Notes & Gotchas
- **HOUSEKEEPER vs. Guard user:** Both are provisioned via `mis-security-guard`, but `type: HOUSEKEEPER` is distinct from `type: GUARD`. Do not use a guard user account for sanitization workflows.
- **`seatSanitizeCuttoffInMinute` spelling:** The property name contains a double-`t` (`Cuttoff`) — preserve this exact spelling when setting config. Using `Cutoff` (single `t`) will not match the expected key.
- **`SANITISATION_STATUS_ENABLED` spelling:** British English spelling (`SANITISATION`, not `SANITIZATION`) — preserve verbatim.
- **Non-QR fallback:** If `enableQrCodeForSeatSanitize` is false, housekeepers select a floor from a list and can bulk-mark all seats on that floor as sanitized. Useful for clients who haven't deployed physical QR codes.
- **Role field:** The `role: "3"` in the request resolves to `"WORKER"` in the response — this is expected behaviour observed in the source runbook example.
- **Frappe Tool regions:** Use SG or EU as appropriate for the client's data residency.

## Related Jira
_(No specific Jira tickets cited in source for this procedure — raise SE ticket for setup requests.)_

## Linked Raw Evidence
- `raw/se-runbook/_extract/sections/35-9-seat-sanitization-setup-workflow.md` — section header + sanitization URL
- `raw/se-runbook/_extract/sections/36-enabling-the-ui-view-of-seat-sanitizat.md` — Step 1 (TO team, SANITISATION_STATUS_ENABLED)
- `raw/se-runbook/_extract/sections/37-creating-a-housekeeper-user---done-by.md` — Step 2 (HOUSEKEEPER user creation API)
- `raw/se-runbook/_extract/sections/38-enabling---disabling-qr-code-scan-for.md` — Step 3 (enableQrCodeForSeatSanitize)
- `raw/se-runbook/_extract/sections/39-4--seat-sanitization-cut-off-time-in-m.md` — Step 4 (seatSanitizeCuttoffInMinute)
- `raw/se-runbook/crawl/files/13REpLmnrhY3LhLAlj3iiWm3R0qag6SoFA6pulRjBh50.docx` — Seat Sanitization workflow Problem statement PRD

## Related
- [[modules/sanitization]] — parent module page
- [[modules/desk-management]] — desk booking context
- [[modules/guard-app-kiosks]] — shared `mis-security-guard` service

## Last Updated
2026-06-29 — source: [[sources/se-runbook-sanitization]]

_Source: [[sources/se-runbook-sanitization]]_
