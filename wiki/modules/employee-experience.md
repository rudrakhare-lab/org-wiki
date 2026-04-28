---
type: module
status: active
owner: unknown
depends_on: []
used_by: [delegation, digital-wayfinding]
last_updated: 2026-04-28
source: "[[sources/delegation-prd]], [[sources/digital-wayfinding-sop]]"
---

# Employee Experience Module (emp-exp)

## Overview
`emp-exp` (Employee Experience) is the backend service that hosts cross-cutting employee-facing
features that don't belong to a specific resource module. Currently documented as the host for:
- **Delegation** — profile switching and booking privilege delegation
- **Digital Wayfinding** — indoor navigation (filed under employee-experience in Drive)

This module page will be expanded as more emp-exp docs are ingested.

## Known Features
- Delegation workflow (Profile switcher, delegatee rights management) — see [[modules/delegation]]
- Digital Wayfinding / Indoor Navigation — see [[modules/digital-wayfinding]]

## Dependencies on Other Modules
- None identified yet.

## Used By
- [[modules/delegation]] — lives in `emp-exp` service
- [[modules/digital-wayfinding]] — filed under employee-experience in Drive

## Open Questions
- What other features live in the emp-exp service?
- Is "Employee Web" (mentioned as a delegatable resource) a distinct module or part of emp-exp?

## Last Updated
2026-04-28 — _Source: [[sources/delegation-prd]], [[sources/digital-wayfinding-sop]]_
