---
type: runbook
module: ets
last_updated: 2026-06-29
sources:
  - "[[sources/se-runbook-ets]]"
---

# Runbook — ETS Data Sync Integration

> **Scope:** This runbook covers the SE/TAM procedure for setting up and requesting SFTP or API-based employee data sync between a client's HRMS/IdP and WorkInSync via ETS. It does NOT cover the employee field contract in detail — see [[modules/employee-provisioning]] for the full field schema and SCIM channel.

## Purpose & Scope
Employee records (identity, team, home location, transport assignment) must flow from the client's HR system into WorkInSync so employees can make bookings. ETS supports two channels: **SFTP** (bulk CSV, DevOps-managed) and **API Sync** (client server pushes records via REST). This runbook covers the SE request process and integration steps for SFTP (the primary channel requiring DevOps involvement).

## When to Use This Runbook
- A new client needs employee data sync set up for the first time.
- An existing SFTP sync is failing and requires DevOps intervention (P0 escalation path).
- A client wants to migrate from SFTP to API sync.

## Prerequisites
- Client has an active WorkInSync URL (production/UAT/POC).
- Module POD has confirmed the basic functionality and requirements with the client.
- KAM or TAM has reviewed and approved the integration request.
- For SFTP: SSH public key from the client and the IP address/range of the client's network.

## Channel Comparison

| Dimension | SFTP | API Sync |
|-----------|------|----------|
| Integration method | Client drops CSV to MoveInSync SFTP server | Client server POSTs per-employee records via REST |
| Auth | SSH key-based | Bearer token (`POST /auth/token`, `client_credentials`) |
| Trigger | File drop; automated processing script | Client-driven; on any schedule |
| Error feedback | Email with row-level error dump | Per-call JSON error response with field-level codes |
| DevOps involvement | Required (SFTP provisioning + scripts) | Minimal (MoveInSync shares API contract only) |
| Suitable for | Bulk daily/weekly syncs | Real-time or event-driven sync |

## SFTP Integration Request Procedure (SOP)

**Step 1 — Validate the request (Module POD)**
- Confirm the requirement with the client; review the SFTP Datasync Ext.doc for scope.
- Obtain KAM/TAM approval before raising a ticket.

**Step 2 — Raise a TechOps ticket**
- Raise a TO ticket and send to: `integrations@moveinsync.com`
- Include in the ticket:
  - Site URL
  - Type of site: Production / POC / UAT
  - Integration method: SFTP
  - SSH Public Key from the client
  - IP address/range of the client network (for whitelist)
  - Requestor's name
- Note: if the site belongs to Rentlz, WIS, or Shuttle service, Steps 1–2 are handled by the respective service PODs.

**Step 3 — DevOps provisions SFTP access**
- DevOps shares the SFTP DNS name, port, credentials, and folder path via the TO ticket.
- Manual file sync validation is performed by DevOps before automation is enabled.
- All communications must go through the TO ticket for documentation.

**Step 4 — Test**
- Validate connectivity in UAT first.
- Test joiner, leaver, and address-change scenarios with sample records.
- Check for errors in the data sync dashboard (logs retained 30 days) or via email error reports.
- Plan phased rollout to production once UAT tests pass.

### SLAs

| Priority | SLA | Scope |
|----------|-----|-------|
| Major TO | 4 weeks | New development (new scripts, new preprocessing) |
| Minor TO | 2 weeks | Modify existing automation setup |
| P0 (Blocker) | 1 business day | Sync failing; requires approval from KDV/Charan + Dibyendu before escalating |

## API Sync Integration (no DevOps ticket needed)

1. MoveInSync shares the API contract with the client (endpoints, base URLs, sample calls, error codes).
2. Client calls `POST /auth/token` with `Authorization: Basic <base64(username:password)>` and `grant_type=client_credentials` to get a Bearer token.
3. Token is short-lived (~48 hours); client must refresh when expired.
4. Client POSTs employee records to the data sync API. Mandatory fields: `EmployeeId`, `Email`, `EmployeeName`, `ProjectTeam`, `Gender`, `OfficeName`.
5. For employee exit: POST with `RemoveEmployee=INACTIVE`.
6. Errors returned per-record with field-level codes; client re-pushes corrected records.

**Base URLs:**

| Environment | Auth endpoint | Data endpoint |
|-------------|--------------|---------------|
| UAT | `https://apistage.moveinsync.com/` | `https://data-uat.moveinsync.com/` |
| Production | `https://apistage.moveinsync.com/` | `https://dataapi.moveinsync.com/` |

> ⚠️ Never log or store Bearer tokens. Redact to `<token>` in all tickets and docs.

## Notes & Gotchas
- The SFTP employee schema includes transport-era fields (Nodal, ShuttlePoint, BillingZone) that are irrelevant for pure workplace-only clients. Only mandatory fields need to be populated.
- `OfficeName` in the sync must match an existing office name in ETS exactly — mismatches throw `INVALID_OFFICE`.
- `GeoCode` can be left blank; the Transport team can assign home geocodes later.
- If `ProjectTeam` doesn't exist, it is auto-created in WorkInSync — no pre-creation needed.
- Dummy email IDs are allowed for security escorts (e.g., `<empId>@clientdomain.com`).
- Address fields containing commas must be wrapped in double quotes in the CSV.

## Related
- [[modules/ets]] — ETS module overview, office API, config properties
- [[modules/employee-provisioning]] — SCIM / modern API provisioning (non-ETS channel; full field schema)
- [[runbooks/ets-office-premise-setup]] — prerequisite: create the office and shifts in ETS before data sync

## Last Updated
2026-06-29 — source: [[sources/se-runbook-ets]]
