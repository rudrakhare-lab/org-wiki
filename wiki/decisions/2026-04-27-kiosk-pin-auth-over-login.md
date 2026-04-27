---
type: decision
module: meeting-rooms
date: 2026-04-27
status: active
---

# Decision: Use PIN/OTP authentication on kiosk instead of user login

## Context
The Meeting Rooms Kiosk is a shared tablet device mounted in a public area outside a room.
It needs to allow meeting cancellation and end-meeting actions but cannot ask every user to log
in — that would be slow and friction-heavy for a device used in passing.

## Decision
The kiosk uses a **PIN code** (emailed to the meeting organizer) as the authentication method
for sensitive actions (cancel meeting, end meeting early).
- PIN is generated and emailed to the organizer's work email from `no-reply@workinsync.io`.
- PIN is single-use and time-scoped to the meeting.
- Config key `MEETING_EMAIL_OTP_TO_AUTHENTICATE` controls whether PIN email is triggered (default: true).
- Config key `CANCEL_EVENT_PIN_VERIFICATION_ENABLE` additionally gates cancel-specifically.

## Alternatives Considered
- **Full user login** on kiosk (rejected — high friction, session management on shared device is risky)
- **QR code scan via phone** (partially used — QR is used for check-in; PIN kept for cancel/end to not require phone proximity)
- **No authentication** (rejected — room squatting and accidental cancellations are a real risk)

## Trade-offs
- PIN sent to organizer's email — if organizer is not the person at the kiosk (e.g. delegate), they need to forward the PIN or phone the organizer. No documented delegate flow.
- Email delivery latency could delay PIN arrival. No retry / resend mechanism documented.
- Admins can disable PIN auth entirely via config — reduces friction but removes the security gate.

## Source
[[sources/kiosk-meeting-rooms-prd]]
