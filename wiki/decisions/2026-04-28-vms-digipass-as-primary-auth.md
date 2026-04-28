---
type: decision
module: visitor-management
date: 2026-04-28
status: active
---

# Decision: Digipass (QR code) as primary visitor authentication credential

## Context
Visitors need a credential to enter the building and be identified by the Guard App and Front Desk.
The credential must be: shareable before arrival, scannable quickly, forgeable-resistant enough,
and functional for someone who may not have a corporate login.

## Decision
VMS issues a **Digipass** — a QR code emailed to the visitor after profile completion — as the
primary entry credential. Controlled by `VISITOR_DIGIPASS` (default: true).

The Digipass email includes: QR code to scan, event name/date/time, location, general instructions, visitor photo (if uploaded), and parking slot (if allocated).

Optional enhancement: `digipassAutoSend = true` sends Digipass immediately after invite creation,
without waiting for visitor to accept the invite (useful for conferences, mass events).

When digipass is disabled (`VISITOR_DIGIPASS = false`), visitor goes through profile completion
but receives a confirmation email with instructions to report directly to front desk (no QR scan
at security gate — guard app step is bypassed or manual).

## Alternatives Considered
- **Hard-copy pass** (rejected — no real-time revocation, printing bottleneck)
- **Login to WIS on visitor's phone** (rejected — frictionful, requires visitor to create an account)
- **Manual ID check only** (available as fallback when digipass disabled)

## Trade-offs
- Digipass email could be forwarded by visitor or impersonated. Mitigated by front desk identity verification step (photo ID match).
- Visitors who don't receive email in time (spam filters, slow delivery) can't enter via guard gate. Auto-send (`digipassAutoSend`) reduces this risk for known events.
- When digipass is disabled, guard app step is effectively bypassed — reduces 2-step check-in to 1-step.

## Source
[[sources/vms-prd]]
