---
type: source
raw_path: raw/modules/access-management/WorkInSync Access Card Management Integration - API based [Client shareable].pdf
ingested: 2026-05-27
doc_type: spec
---

# Access Card Management Integration — API based (global)

## Source Title
WorkInSync Access Card Management Integration - API based

## Date
Jul 19, 2024 (v1.2). Version history: v1.0 Rahul Agrawal / approved Ujjwal Trivedi / 28-Jun-2022 ("Initial Doc"); v1.1 Binoy Dedhia / Ujjwal Trivedi / 29-Nov-2022 ("Updated version (with actual API signature)"); v1.2 Aditya Dutta / Ujjwal Trivedi / 19-Jul-2024 ("Addition of RFID"). Classification: **Confidential**.

## Type
spec

## Key Takeaways
- **Purpose** (source quote): *"This document explains the process and data required for integrating WorkInSync system with client's own/third party access management vendors using APIs."*
- **Authentication**: Bearer-token mechanism. Client-specific username/password is exchanged for a short-lived access token via `POST {baseUrl}/auth/token` with header `Authorization: Basic <base64(client_id:client_secret)>` and form body `grant_type=client_credentials`. Response carries `access_token` (Bearer), `token_type`, `expires_in: 172799` (~48 hours). baseUrl for global clients: `https://api.moveinsync.com`.
- **Primary endpoint**: `POST {baseUrl}/integration/bookings/ci-co` with `Authorization: Bearer <token>`.
- **Request fields** (7): `filter` (String, Max 50 — EmployeeID / EmployeeName / EmployeeEmailID, unique per employee), `officeName` (String, Max 100), `bookingStatus` (String, Max 50 — `SIGNED_IN` / `SIGNED_OUT`), `epochTime` (Long, ms), `premiseId` (String, Max 50 — *"The unique ID associated with the location where the action was performed. It may be an office or specific floor location."*), `readerId` (String, Max 50 — device ID at entry point), `rfid` (string, Max 50 — card identifier; filter can be skipped if rfid is passed).
- **Response**: `status` (Integer — API status code; 200 success, 1001 internal failure), `data` (UUID — Booking Id), `message` (String). 401 returned only when the Authorization header is missing.
- **⚠️ `premiseId` semantics CONTRADICT the IND-region doc.** This global doc describes `premiseId` as: *"The unique ID associated with the location where the action was performed. It may be an office or specific floor location."* The IND-region doc (`access-mgmt-integration-api-based-ind`) describes the SAME field as: *"Type of booking that is requested ... Possible Values OFFICE, PARKING, PARKING_TWO, PARKING_FOUR, MEALS, MEETING"*. These are mutually incompatible semantics for the same field name. **Do not select an interpretation from these sources alone — engineering must clarify which is canonical.**
- **Actions**: check-in/check-out to an employee's existing booking; if `createBookingIfNotPresent` is true, create an office booking for employees with no booking based on scan time + end time.
- **⚠️ Drive duplicate**: a second file `WorkInSync Access Card Management Integration - API based [Client shareable] (4).pdf` exists in `raw/`. Its extracted content is byte-near-identical to this doc (same v1.2, same Document/Version Control, same per-page content). The "(4)" suffix is a Google Drive re-upload revision marker, NOT a content version. It is **not separately ingested**. **Precedent: Drive "(N)" revision artifacts are silently deduplicated unless their content differs meaningfully.**
- **Sample cURL** in the source includes auth tokens and base64 credentials — NOT reproduced here per the safety rule (tokens/credentials are never copied into the wiki, even from sample docs).

## Entities Mentioned
(none — integration spec; no WorkInSync data entities introduced. References the existing booking concept.)

## Modules Mentioned
- [[modules/access-management]] (primary subject)

## Decisions Extracted
(none — records implementation choices (Bearer token, API Gateway pattern) without alternatives + rationale)

## Wiki Pages Created/Updated
- Created: [[modules/access-management]]
- Updated: [[index]], [[log]]

_Source: [[sources/access-mgmt-integration-api-based]]_
