---
type: cross-module
modules: [visitor-management, guard-app-kiosks]
last_updated: 2026-04-28
source: "[[sources/vms-prd]]"
---

# Visitor Management ↔ Guard App & Kiosks — Security Gate Check-In (Step 1 of 2)

## Summary
The Guard App (part of the `guard-app-kiosks` module) is the first touch point in VMS's
2-step check-in process. Security guards use the Guard App to scan the visitor's Digipass QR
code at the building entrance gate, marking "Security Complete" before the visitor proceeds
to the front desk for full check-in.

## Modules Involved
- [[modules/visitor-management]] — owns visitor data, digipass, and check-in status
- [[modules/guard-app-kiosks]] — provides the guard-facing app/device for digipass scanning

## How They Connect
```
[VMS]
  Digipass (QR code) emailed to visitor after profile completion
               │
               ▼
[Visitor at security gate]
  Shows digipass QR on phone
               │
               ▼
[Guard App (guard-app-kiosks)]
  Security guard scans QR → visitor record shown
  Guard can see: visitor name, event, host name, expected visit time
  Guard clicks "Allow Entry" → marks visitor status: Security Complete
               │
               ▼
[VMS]
  Visitor status updated to Security Complete
  Notification sent to host (email + SMS): "Visitor XXX has arrived at security gate"
  Notification sent to front desk: "Visitor XXX has entered, proceeding to front desk"
               │
               ▼
[Front Desk (VMS)]
  Tracks time from "Security Complete" to front desk arrival
  If > N min (configurable): status = "Delayed Check-in" → front desk alerted
```

## Potential Conflicts
- If the Guard App and VMS API are on different deployment versions, digipass scan may not correctly update visitor status.
- Dynamic fields (bag scan checklist, belongings list) documented in PRD as V2 — not yet built on guard app.

_Source: [[sources/vms-prd]]_
