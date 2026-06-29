---
type: module
status: active
owner: unknown
depends_on: []
used_by: [delegation]
last_updated: 2024-02-27
source: "[[sources/delegation-prd]], [[sources/digital-wayfinding-sop]], [[sources/se-runbook-employee-experience]]"
---

# Employee Experience Module (emp-exp)

## Overview
`emp-exp` (Employee Experience) is the backend service that hosts cross-cutting employee-facing
features that don't belong to a specific resource module. Currently documented as the host for:
- **Delegation** — profile switching and booking privilege delegation
- **Digital Wayfinding** — indoor navigation (filed under employee-experience in Drive)

This page is intentionally thin: the only emp-exp-specific document in Drive ("Employee
Experience – Delegation") is a copy of the [[sources/delegation-prd]], so delegation detail lives
on [[modules/delegation]] and is not duplicated here. The page will be expanded if/when a
distinct emp-exp service doc (beyond the hosted features) is ingested.

## Known Features
- Delegation workflow (Profile switcher, delegatee rights management) — see [[modules/delegation]]
- Digital Wayfinding / Indoor Navigation — see [[modules/digital-wayfinding]]
- **Configurable sender email** (per-BUID outbound "from" address) — the `emp-exp` service sets the sender address used for a BUID's WorkInSync emails; resolves by precedence (Stratus-enabled → `noreply@workinsync.io`; non-Stratus + `wisBuEnabled` + table entry → configurable email; else default `transport@moveinsync.com`). Ref PB-22330. See [[runbooks/configurable-sender-email-setup]]. _Source: [[sources/se-runbook-employee-experience]]_

## Configuration
The emp-exp service exposes three PMS config surfaces (dual-server `.in` / `.com`):
- [[configs/emp-experience-email]] — Email Emp Experience service configs
- [[configs/emp-experience-internal]] — Emp Exp Internal Config service configs
- [[configs/emp-experience-common]] — Emp Exp Common Config service configs

Delegation's feature flags run under this service (`Service: emp-exp`): `isDelegationEnabled`
(default False), `enableDelegationForAdmins` (default True), `blockDelegationEmail` (default
False). See [[modules/delegation]] for the full delegation config set.

## Dependencies on Other Modules
- None identified yet — emp-exp is a foundational host service.

## Used By
- [[modules/delegation]] — delegation feature and its config flags live in the `emp-exp` service
- [[modules/digital-wayfinding]] — filed under employee-experience in Drive. ⚠️ Filing-based link only: digital-wayfinding's module dependencies are `mobile-app` + `parking-management`, not emp-exp. Flagged for the graph-reconciliation sweep to resolve (drop the link, or establish a real dependency).

## Data Entities Used
- [[entities/employee]] — employee identity record (identity, entitlements, relationships)

## Related Runbooks
- [[runbooks/configurable-sender-email-setup]] — set the per-BUID outbound sender ("from") email address (PB-22330)

## Open Questions
- What other features live in the emp-exp service (beyond delegation, wayfinding, and the configurable sender email documented above)? Partially answered as more SE material is ingested.
- Is "Employee Web" (mentioned as a delegatable resource in the Delegation PRD) a distinct module or part of emp-exp?

## Last Updated
2024-02-27 — _Source: [[sources/delegation-prd]], [[sources/digital-wayfinding-sop]]_
