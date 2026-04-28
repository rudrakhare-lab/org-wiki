---
type: decision
module: visitor-management
date: 2026-04-28
status: active
---

# Decision: 2-step visitor check-in (Security gate → Front desk) over single-step

## Context
Organizations need to balance visitor flow speed with security compliance. A single check-in at
the front desk provides no early visibility of visitor arrival. A pure security-gate scan with no
front desk step doesn't allow for identity verification, badge printing, or NDA collection.

## Decision
VMS implements a **2-step check-in**:
1. **Step 1 — Security Gate**: Guard App scans visitor Digipass → status = "Security Complete" → host and front desk notified.
2. **Step 2 — Front Desk**: Receptionist verifies photo ID, collects NDA (if required), captures photo, allows entry → status = "Checked-In" → badge printed.

A configurable timer between steps allows the front desk to be alerted if the visitor is delayed ("Delayed Check-in" status if visitor takes > N minutes to reach reception after gate 1).

## Alternatives Considered
- Single check-in at front desk only (rejected — security cannot be staffed at all gates; no advance alert to front desk)
- Self-check-in via kiosk (documented as V2 / not yet built)
- Single check-in at security gate only (rejected — no front desk paper trail, no badge printing, no NDA)

## Trade-offs
- Adds friction for visitor — two stops. Mitigated by Digipass QR making both steps fast.
- Requires Guard App to be deployed and staffed. Not all clients have security staff at the gate (walk-in flow handles this).
- Step ordering is fixed — guard always before front desk. Not configurable to swap order.

## Source
[[sources/vms-prd]]
