---
type: source
raw_path: raw/modules/access-management/WorkInSync Access Card Management Integration - API based IND Region [MUM] - Client shareable.pdf
ingested: 2026-05-27
doc_type: spec
---

# Access Card Management Integration — API based (IND Region [MUM])

## Source Title
WorkInSync Access Card Management Integration - API based IND Region [MUM]

## Date
Jul 19, 2024 (v1.2). Version history identical (author/approver/date/description) to the global API doc — see Open Questions on the global module page for a documentation-hygiene note. Classification: **Confidential**.

## Type
spec

## Key Takeaways
- Same product as the global API-based integration, but **regionally deployed**: baseUrl is `https://api.moveinsync.in/integration/` (vs `https://api.moveinsync.com` for global). Same Bearer-token auth flow, same `POST /integration/bookings/ci-co` endpoint, same request/response field set.
- Names the operation explicitly: *"AccessCardCheckIn: CheckIn to an existing booking"* (the global doc does not use this naming).
- **⚠️ `premiseId` semantics CONTRADICT the global doc.** This IND doc describes `premiseId*` as: *"Type of booking that is requested ... Possible Values OFFICE, PARKING, PARKING_TWO, PARKING_FOUR, MEALS, MEETING"* (Max 50). The global doc describes the SAME field as: *"The unique ID associated with the location where the action was performed. It may be an office or specific floor location."* These are mutually incompatible semantics for the same field name. **Do not select an interpretation from these sources alone — engineering must clarify which is canonical.**
- Same response model (`status` / `data` / `message`), same status codes (200 / 1001 / 401), same `createBookingIfNotPresent` behavior.
- Sample cURLs target `https://api.moveinsync.in/auth/token` and `https://api.moveinsync.in/integration/bookings/ci-co`. Auth tokens and base64 credentials in the samples are NOT reproduced here per the safety rule.

## Entities Mentioned
(none)

## Modules Mentioned
- [[modules/access-management]] (primary subject)

## Decisions Extracted
(none)

## Wiki Pages Created/Updated
- Created: [[modules/access-management]]
- Updated: [[index]], [[log]]

_Source: [[sources/access-mgmt-integration-api-based-ind]]_
