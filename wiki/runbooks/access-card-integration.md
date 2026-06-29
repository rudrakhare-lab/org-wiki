---
type: runbook
module: access-management
last_updated: 2026-06-29
source: "[[sources/se-runbook-access-card]]"
---

# Runbook: Access Card Integration Setup

SE-facing setup guide for onboarding a client onto WorkInSync access-card check-in/out
integration. Two modes: REST API (real-time, since 2022) and SFTP file-based (batch, since
Feb 2025). Choose based on client capability — REST is preferred for real-time accuracy;
SFTP is the fallback for clients whose access-management system cannot make outbound REST calls.

## Mode 1 — REST API Integration

### Prerequisites (collect from client before starting)
- Vendor/client system that can make outbound REST HTTP calls
- Decision on regional server: `.com` (`api.moveinsync.com`) or `.in` (`api.moveinsync.in`)
- RFID card numbers mapped to employee IDs (if using RFID-based lookup — optional)
- Reader device IDs for device-to-office/floor mapping (required for per-floor reporting)

### Step 1 — Register client in the API Gateway

WorkInSync registers the integration client in the API Gateway and issues a client-specific
`client_id` and `client_secret`. Share ONLY `client_id` and `client_secret` with the vendor —
never share or log actual Bearer tokens.

> ⚠️ Credentials are client-specific. Each integration (even for the same BUID) gets its own
> credential pair. Do not reuse credentials across clients.

### Step 2 — Auth token exchange (vendor's responsibility; document for them)

Before calling any check-in/out API, the vendor must obtain a Bearer token:

```
POST {baseUrl}/auth/token
Authorization: Basic <base64(client_id:client_secret)>
Content-Type: application/x-www-form-urlencoded

grant_type=client_credentials
```

`baseUrl`:
- Global (`.com`): `https://api.moveinsync.com`
- IND region (`.in`): `https://api.moveinsync.in`

Response: `{ "access_token": "<bearer-token>", "token_type": "Bearer", "expires_in": 172799 }`

Token TTL is ~48 hours. The vendor must re-fetch when expired (HTTP 401 is returned on expiry).
The Bearer token is passed as `Authorization: Bearer <bearer-token>` on every subsequent call.

> ⚠️ Do NOT paste actual `eyJ…` tokens in tickets, wiki pages, or runbooks. Use `<bearer-token>` as
> placeholder.

### Step 3 — Device-to-office/floor mapping (one-time)

For per-office and per-floor utilization reports, each reader device must be mapped to an
office and floor in WorkInSync (PB-45283). Upload a CSV with the device-to-floor mapping:

```
POST https://stage.moveinsync.com/mis-security-guard/csv/sta…
Authorization: Bearer <bearer-token>
Content-Type: multipart/form-data

file: <device-mapping.xlsx>
```

Template columns: device ID, office ID, floor ID (exact column names — obtain from the
template shared internally). This is a one-time upload per client onboarding; re-upload only
if the client adds new reader devices.

### Step 4 — Check-in / check-out API (vendor calls)

```
POST {baseUrl}/integration/bookings/ci-co
Authorization: Bearer <bearer-token>
Content-Type: application/json

{
  "bookingStatus": "SIGNED_IN",       // or "SIGNED_OUT"
  "epochTime": <epoch-ms>,            // timestamp of the swipe in epoch milliseconds
  "filter": "<employee-id-or-email>", // leave blank if using rfid
  "rfid": "<card-number>",            // optional; requires RFID→employee mapping
  "readerId": "<device-id>",          // use ONE of: readerId / officeName / premiseId
  "officeName": "",
  "premiseId": ""
}
```

`bookingStatus` values:
- `SIGNED_IN` — checks the employee into their booking; if `createBookingWhenCheckinReceived` is enabled and no booking exists, creates one first
- `SIGNED_OUT` — checks the employee out of their existing booking

Response:

| Field | Type | Meaning |
|-------|------|---------|
| `status` | Integer | `200` = success, `1001` = internal failure |
| `data` | UUID | Booking ID |
| `message` | String | Human-readable result |

> ⚠️ HTTP status is always `200`; check the `status` body field to detect failures. HTTP `401`
> means the Authorization header is missing or the token has expired.

### Step 5 — Enable and configure PMS properties

Set the following on the BUID via PMS (service: `BOOKING-RULE-ENGINE`, `.com` server unless noted):

| Property | Value to set | Notes |
|----------|-------------|-------|
| `recordCheckInOutViaAccessCardAPI` | `true` | Enables API-based check-in recording |
| `createBookingWhenCheckinReceived` | `true` (optional) | Auto-creates booking if employee has none |
| `defaulBookingHoursIfExtCheckin` | `<hours>` (DOUBLE) | Duration of auto-created booking; required if above is true. Default not documented — confirm with team |
| `extCheckinToBookingBuffer` | `<hours>` (DOUBLE) | Buffer window for check-in to match a booking (both servers) |
| `showFirstCheckInRecord` | `true` (optional) | Only first check-in counts in reports (PB-48998) |

Set the following **per office** (not per BUID) based on client's check-in UX preference:

| Property | Values | Notes |
|----------|--------|-------|
| `officeCheckInModeWeb` | `directCheckIn` / `digiPass` / `scanQR` / `noCheckIn` | Controls web app check-in mode |
| `officeCheckInModeApp` | `directCheckIn` / `digiPass` / `scanQR` / `noCheckIn` | Controls mobile app check-in mode |

> ⚠️ `officeCheckInModeWeb` and `officeCheckInModeApp` are **office-level** configs, not BUID-level.
> Set per office. For access-card integrations, `noCheckIn` disables the manual check-in button
> so employees only check in via the access card swipe. Verify the desired mode with the client
> before setting.

---

## Mode 2 — SFTP File-based Integration

Introduced Feb 2025 (v1.0 — Aditya Dutta / Ujjwal Trivedi).
Use when the client cannot push real-time REST calls. The client pushes a CSV of employee swipe
data to WorkInSync's SFTP server at an agreed frequency (e.g. hourly).

### Prerequisites (collect from client before starting)
- SSH (Secure Shell) public key
- IP addresses from which files will be pushed (for whitelisting)
- Encryption method used during file transfer (if any)
- Agreed push frequency (e.g. every 1 hour)

### Step 1 — SFTP configuration

Once the client provides the above, WorkInSync configures the SFTP server and shares back:
- SFTP port
- SFTP filepath / directory
- SFTP server hostname

Test the connection after configuration.

### Step 2 — File format handoff

WorkInSync shares the **employee swipe data file format template** with the client and requests
a sample file push. Verify the sample file is received and parseable before go-live.

> ⚠️ The exact CSV column schema for swipe data files is not fully documented in available sources.
> Obtain the template from the Access Management / Integration team before sharing with the client.

### Step 3 — Enable and configure PMS properties

| Property | Value | Service | Server |
|----------|-------|---------|--------|
| `externalChannelCheckIn` | `true` | BOOKING-RULE-ENGINE | .com only |
| `createBookingWhenCheckinReceived` | `true` (optional) | BOOKING-RULE-ENGINE | .com only |
| `showFirstCheckInRecord` | `true` (optional) | BOOKING-RULE-ENGINE | .com only |
| `lastSwipeAsCheckoutTimeForBUID` | `[<buid>]` (LIST) | EMP-EXP-COMMON-CONFIG | both |

> ⚠️ `lastSwipeAsCheckoutTimeForBUID` is a LIST. The BUID must be added to the list — do not
> overwrite existing entries. Exact format: confirm current value before editing.

### Step 4 — Verify reports

After the first file push, verify:
- Employee swipe events appear in the access card report
- Bookings created/checked-in correctly
- Anomaly report lists users who entered without a booking (if applicable)
- Device-to-floor mapping is correctly showing office/floor in reports

---

## Check-in Mode Reference

`officeCheckInModeWeb` and `officeCheckInModeApp` control the check-in UX for all employees
at a given office (not specific to access-card). Values:

| Value | Behavior |
|-------|----------|
| `directCheckIn` | Simple button — employee taps "Check In" → Yes/No confirmation |
| `digiPass` | Employee generates a DigiPass QR on the app; displays to reception scanner |
| `scanQR` | Employee scans the office/floor/desk QR code via FAB in the mobile app |
| `noCheckIn` | No check-in button; check-in/out times not recorded (used for access-card-only mode) |

For access-card integrations, `noCheckIn` is typically set so that manual check-in is disabled
and all check-ins are driven by the physical access-card swipe event.

> ⚠️ If `restrictScanQROnFabButton` is enabled on the BUID, the `officeCheckInModeApp` must
> also be set to `scanQR` — the config enforces consistency. (See [[configs/booking-rule-engine]].)

---

## Troubleshooting

| Symptom | Check |
|---------|-------|
| HTTP 401 on ci-co call | Bearer token expired — re-fetch via `/auth/token` |
| `status: 1001` in response body | Internal failure — check employee ID format, booking existence, office identifier passed |
| Employee not found | Verify `filter` value matches EmployeeID / EmployeeName / EmployeeEmailID exactly (max 50 chars); check RFID mapping if using `rfid` field |
| Check-in recorded but wrong office | Verify `readerId` → office mapping was uploaded; check `officeName` / `premiseId` field |
| No booking auto-created after check-in | Verify `createBookingWhenCheckinReceived = true` on the BUID; check `defaulBookingHoursIfExtCheckin` is set |
| SFTP files not processed | Verify IP is whitelisted; check encryption matches; confirm push frequency and file format |

_Source: [[sources/se-runbook-access-card]]_

## Related Pages
- [[modules/access-management]] — module overview, API contract, config properties
- [[configs/booking-rule-engine]] — full BRE property table (see `recordCheckInOutViaAccessCardAPI`, `externalChannelCheckIn`, `createBookingWhenCheckinReceived`, `defaulBookingHoursIfExtCheckin`, `extCheckinToBookingBuffer`, `officeCheckInModeWeb`, `officeCheckInModeApp`, `showFirstCheckInRecord`)
- [[configs/emp-experience-common]] — `lastSwipeAsCheckoutTimeForBUID`
