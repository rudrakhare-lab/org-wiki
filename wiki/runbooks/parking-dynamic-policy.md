---
type: runbook
module: parking-management
team: SE (Service Engineering)
status: active
last_updated: 2025-10-22
source: "[[sources/se-runbook-parking]]"
raw_paths:
  - raw/se-runbook/crawl/files/1liCPdzb7IIMbdWiLD3nBaEkyVGU4Ojg9K3Uvng63Qqo.docx
  - raw/se-runbook/crawl/files/1R1jA2bHvXtkT6uX2FEqVe3GuWEpgunDq8Ug-kfy7cfU.docx
---

# Runbook — Parking Dynamic Policy Setup

> SE / Implementation procedure to configure **dynamic policies** (tag-based access control)
> for parking slots.
> ⚠️ All GUIDs (`bff9f718-…`, `1e7919bf-…`), employee IDs, BUID tokens, and the `est-TakeASpin`
> URL segment are **examples / placeholders** from the source doc — replace with the client's
> actual values.
>
> _Sources: [[sources/se-runbook-parking]] — "Dynamic Policy for Parking" v1.3 (2025-10-22),
> "Parking Technical Document" v1.0 (2022-10-04)_

## Purpose & Scope

Covers the full lifecycle of parking dynamic-policy setup: what dynamic policies are, how to
create tags via API (SE-only), how to upload employee and parking tagging files (admin-facing),
key scenarios, SOPs for new employees/slots, and edge-case remediation.

**Not covered here:** premise creation (→ [[runbooks/parking-premise-setup]]),
vehicle sub-type creation (→ [[runbooks/parking-tag-and-vehicle-setup]]),
QR code generation (→ [[runbooks/parking-tag-and-vehicle-setup]]).

## Concept: What Are Dynamic Policies?

Dynamic policies restrict which employees can book which parking slots, most commonly by
**vehicle build** (Sedan, SUV, Hatchback) or employee category (Executive, PWD).

The system works by **dual mapping**: a policy must be assigned to both the employee profile
and the parking slot. The engine matches — a slot is only bookable by an employee when the
same policy value appears on both sides.

**Example:** Slot `L1-S69` tagged `Sedan = Yes` → only employees tagged `Sedan = Yes` can
book it. Untagged employees (no policy on their profile) cannot see that slot.

**Slots with no policy mapping** are bookable by anyone in the system (open hotslots).

_Source: [[sources/se-runbook-parking]] — "Parking Technical Document" v1.0_

## Step 1 — Decide the Policy Strategy

Before touching the system, agree with the client on their policy requirements:

- **Vehicle-build policies** (most common): Crossover/SUV/MUV | Sedan | Small/Hatchback |
  Micro/Hatchback
- **Category policies**: Executive-reserved, PWD-reserved, etc.
- **`BLOCK_HOTSEAT`**: blocks an employee from booking open hotslots; does **not** block
  policy-matched slots. Used to ensure only employees with a matching vehicle tag can park
  (they cannot fall back to a hotslot).

> ⚠️ `BLOCK_HOTSEAT` does NOT prevent booking slots that the user is tagged for.
> A user with `Sedan = Yes` + `BLOCK_HOTSEAT = Yes` can still book Sedan slots —
> they just cannot book untagged open hotslots.

**Scenario planning (from v1.2):**

| Scenario | Goal | Configuration |
|----------|------|---------------|
| Scenario 1 | Restrict each user to their vehicle type, block hotslots | Upload Employee Tagging with vehicle-type `Yes` + `BLOCK_HOTSEAT Yes`; upload Parking Tagging with matching vehicle type `Yes` per slot |
| Scenario 2 | Block users from ALL parking (non-compliance) | Upload Employee Tagging with vehicle-type set to `Null` for relevant users; `BLOCK_HOTSEAT` behaviour unchanged |
| Scenario 3 | Update a future-dated tag to today | Upload `Null` for affected tags first (removes earlier tag), then re-upload with correct start date |

## Step 2 — Create Tags via API (SE-only)

Tags are created via the `mis-floor-plan` API. This step is **SE-only** — clients do not
call these endpoints directly.

**Step 2a — Create the tags**

```
POST https://wis-premise.workinsync.io/mis-floor-plan/api/<BUID>/tags
Content-Type: application/json

[
  { "entityType": "EMPLOYEE", "tagName": "Executive", "tagType": "SINGLE_VALUED" },
  { "entityType": "EMPLOYEE", "tagName": "Visitor",   "tagType": "SINGLE_VALUED" },
  { "entityType": "EMPLOYEE", "tagName": "Specially Able Person", "tagType": "SINGLE_VALUED" }
]
```

> ⚠️ The source doc shows `est-TakeASpin` as the `<BUID>` segment in the URL — this is an
> **example BUID placeholder**, not a literal value. Substitute the client's actual BUID.
> Authentication uses `x-wis-token: <token>` — always use a valid token; never embed real
> tokens in wiki pages or tickets.

The response returns a **`buTagId`** (GUID) for each tag. **Copy these IDs** — required
for Step 2b.

**Step 2b — Map tag values to each tag**

```
POST https://wis-premise.workinsync.io/mis-floor-plan/api/<BUID>/tags/polygons
Content-Type: application/json

[
  { "buTagId": "<tag-id-executive>",          "tagValue": "Yes" },
  { "buTagId": "<tag-id-executive>",          "tagValue": "No"  },
  { "buTagId": "<tag-id-visitor>",            "tagValue": "Yes" },
  { "buTagId": "<tag-id-visitor>",            "tagValue": "No"  },
  { "buTagId": "<tag-id-specially-able>",     "tagValue": "Yes" },
  { "buTagId": "<tag-id-specially-able>",     "tagValue": "No"  }
]
```

**Step 2c — Verify tags are created**

```
GET https://wis-premise.workinsync.io/mis-floor-plan/api/<BUID>/tags?entityType=PARKING
x-wis-token: <token>
```

Confirm the tags appear in the response. Once tags exist, they will be visible in the
bulk-upload template download.

> ⚠️ The source notes that this tag-creation step is also used for desk tags (the tag
> engine is shared). See [[modules/tags-desk-parking]].

_Raise an SE ticket to perform this step. Confirm tags appear in the bulk upload template
before proceeding to Step 3._

## Step 3 — Upload Employee Tagging File

1. Navigate to **Sidenav → Desk Allocation → Desk Bulk Upload → Employee Tagging**.
2. Download the sample file. It will have a column for each tag created in Step 2.
3. Fill the file:
   - One row per employee (use employee ID as identifier).
   - For each tag column: `Yes` (assign), `Null` (remove), or leave blank (no change).
   - Set the `start_date` trigger correctly — see Edge Cases below.
4. Upload the filled file. On success, the policies appear in the employee's **Other
   Details** section in their profile.

**Value semantics:**

| Value in column | Meaning |
|-----------------|---------|
| `Yes` (or any non-null value) | Assign this policy to the employee |
| `Null` / `null` | Remove this policy from the employee |
| _(blank)_ | Leave existing policy unchanged |

## Step 4 — Upload Parking Tagging File

1. Navigate to **Sidenav → Desk Allocation → Desk Bulk Upload → Parking Tagging**.
2. Download the sample file.
3. Fill the file:
   - One row per parking slot (identified by slot name/ID).
   - For each policy column: `Yes` (slot accessible only to matching users), `Null`
     (remove policy from slot), or blank (no change).
4. Upload the file.

**Available vehicle-build policies** (pre-configured in WIS):
`Crossover,SUV,MUV` | `Sedan` | `Small,Hatchback` | `Micro,Hatchback`

## SOP — New Employee Added

When a new employee joins and needs parking access:

1. Gather the new employee's vehicle type.
2. Add a new row in the Employee Tagging file with:
   - Employee ID
   - Correct start date
   - `Yes` under the appropriate vehicle-type column
   - Optionally `Yes` under `BLOCK_HOTSEAT` (if the client wants to prevent hotslot access)
3. Upload via **Desk Bulk Upload → Employee Tagging**.

## SOP — New Parking Slot Added

1. **Raise an email to the MoveInSync team** with: Office, Zone, Level, Slot number.
   The MoveInSync backend team adds the slot from the server side — this is not self-serve.
2. Once the slot is confirmed added, upload a Parking Tagging file with the new slot entry
   and the appropriate tag assignment(s) and start date.

## Edge Case — Future-dated Tag Applied with Wrong Date

If a tagging upload applied a future start date due to a spreadsheet formatting issue,
the tags are not yet active. Users see incorrect slot availability.

**Remediation:**

1. Upload Employee Tagging with `Null` for all affected tag columns for the affected users.
   This removes the incorrectly-dated tags.
2. Upload a fresh Employee Tagging file with `Yes` for the correct tags and the correct
   start date in the right format.

_Source: "Dynamic Policy for Parking" v1.3, section "Edge Cases"._

## Validation Checklist

- [ ] Policy strategy agreed with client (vehicle types, BLOCK_HOTSEAT y/n)
- [ ] Tags created via API and visible in bulk-upload template download
- [ ] Employee Tagging file uploaded — confirm policies appear in user profiles under "Other Details"
- [ ] Parking Tagging file uploaded — confirm tagged slots show correct restriction
- [ ] Test booking: employee with `Sedan` tag can book a `Sedan` slot; cannot book `SUV` slot or hotslot (if BLOCK_HOTSEAT applied)
- [ ] New employee SOP run if applicable
- [ ] Edge-case date verified — start date format is correct in all upload files

## Notes & Gotchas

1. **Tags are shared with desk/meeting-room tagging** — the `mis-floor-plan` tag engine
   is the same for all booking types. Do not accidentally modify desk tags when operating
   on parking tags. See [[modules/tags-desk-parking]].

2. **Raise an SE ticket for tag creation** — the API calls in Step 2 require backend access.
   Confirm the tags are visible in the bulk-upload template before handing over to the
   client admin.

3. **Slot-level open slots (no policy)** remain bookable by everyone — only slots
   explicitly tagged with a vehicle/category policy are restricted. If a client wants
   ALL slots restricted, every slot must appear in the Parking Tagging file.

4. **`BLOCK_HOTSEAT` does not restrict policy slots.** This is a common misconception —
   it only blocks untagged (hotslot) bookings, not slots where the employee already has
   a matching vehicle policy.

5. **Blank vs. Null**: blank leaves existing mapping untouched; `Null` actively removes
   the mapping. Using blank when you intend to remove is a common error.

6. **Production host**: source doc shows `wis-premise.workinsync.io` for tag APIs. Confirm
   this is the correct production host for the client's server (`.com` vs. `.in`) before
   running Step 2.

## Related

- Module: [[modules/parking-management]]
- Premise setup (prerequisite): [[runbooks/parking-premise-setup]]
- Vehicle sub-type setup: [[runbooks/parking-tag-and-vehicle-setup]]
- Tag engine: [[modules/tags-desk-parking]]

## Last Updated

2026-06-29 — source: [[sources/se-runbook-parking]]
("Dynamic Policy for Parking" v1.3 dated 2025-10-22,
"Parking Technical Document" v1.0 dated 2022-10-04)
