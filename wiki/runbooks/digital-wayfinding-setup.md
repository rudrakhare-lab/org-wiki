---
type: runbook
module: digital-wayfinding
team: SE (Service Engineering)
status: active
last_updated: 2024-02-27
source: "[[sources/se-runbook-digital-wayfinding]]"
raw_path: raw/se-runbook/crawl/files/1V5cNGQGUaYYBnOuZsZ9naI-v2vMLEfZI_VSnH9ZbEWQ.docx
---

# Runbook — Digital Wayfinding Setup

## Purpose & Scope

This runbook covers the **SE team steps** to activate Digital Wayfinding for a client: uploading
the wayfinding JSON+SVG files to the Wayfinding service and enabling the feature flag per BUID.

It is the **downstream continuation** of [[runbooks/floor-plan-upload]]. Floor premise creation
and floor plan upload (converting CAD → SVG/JSON) are covered there; this runbook picks up once
those files are ready.

> For pre-sales and floor-plan-team steps (DIY Floorplanner, path drawing, export), see
> [[modules/digital-wayfinding]] — Implementation Flow (Internal) and DIY Floorplanner Tool
> sections.

## When to Use This Runbook

- A client's floor plans have been processed by the floor plan team and the JSON+SVG files are
  ready for upload to the Wayfinding service.
- You need to activate wayfinding for a new BUID or a new floor at an existing BUID.
- You need to re-upload a floor plan after a navigation update (missing amenities, path changes).

## Prerequisites

1. **Floor plan processing complete** — the floor plan team (Vikas Upadhyay) has finished
   processing in the DIY Floorplanner (CADViewer), including:
   - All amenities marked with names and orientations
   - All walkway paths drawn and validated (no disconnected lines)
   - Way Path uploaded in the tool (this step cannot be done via Postman)
   - JSON + SVG files exported (two files per floor)
   - Environment selected: SG (Singapore) or EU (Europe)

2. **Floor premise exists** — the FloorPremiseID must already exist in the backend, created via
   [[runbooks/floor-plan-upload]] (Step A + B of that runbook).
   Have the FloorPremiseID ready before proceeding.

3. **Access** — Postman with Bearer token for `wis-premise.workinsync.io`.

4. **For first-time wayfinding at a site** — verify the floor plan URLs in the employee-experience
   config before or after upload (see Step 3 below).

> ⚠️ Cross-reference [[runbooks/floor-plan-upload]] if the floor premise has not been created yet.
> Do not proceed without a valid FloorPremiseID.

## Step-by-step

### Step 1 — Upload JSON + SVG to the Wayfinding service

For each floor, run the following Postman request:

**POST:**
```
https://wis-premise.workinsync.io/mis-security-guard/csv/upload/layout/<FloorPremiseID>
    ?forceUpdateFloorPlan=false
    &wktDimensionInCm=100
```

Replace `<FloorPremiseID>` with the actual floor's premiseID from [[runbooks/floor-plan-upload]]
Step B. Example value in SOP source: `4a8de968-2a38-49b9-9b32-ef6983bdb130` — this is an
example only; always use the client's actual ID.

**Fixed query parameters:**

| Key | Value |
|-----|-------|
| `forceUpdateFloorPlan` | `false` |
| `wktDimensionInCm` | `100` |

**Body — form-data:**

| Key | File |
|-----|------|
| `floorImage` | the `.svg` file for this floor |
| `floor` | the `.json` file for this floor |

Expected response: `200 OK` (typical response time ~7–8 s).

> ⚠️ `forceUpdateFloorPlan` must be `false` even on re-uploads. The source SOP explicitly states:
> "InCase of Floor plan Upload/REUPLOAD always keep `forceUpdateFloorPlan: false`."
> Do NOT set it to `true`.

> ⚠️ Do NOT send without updating the premiseID in the URL. The example ID in the SOP source is
> a placeholder — using it will silently upload to the wrong premise.

Repeat for every floor at the site.

_Source: SOP v2.0 (27 Feb 2024), section on SE team upload steps_

### Step 2 — Enable ENABLE_INDOOR_NAVIGATION for the BUID

Once all floors are uploaded, raise an SE ticket to enable the wayfinding feature flag:

- **Config key:** `ENABLE_INDOOR_NAVIGATION`
- **Service:** not documented in PMS config sources — confirm service name with the owning team
- **Level:** BUID
- **Value:** `true`

This is the master switch that shows wayfinding in the mobile app. It is disabled by default.

> ⚠️ Enable this only after all floor uploads for the site are complete. Enabling mid-upload
> may expose an incomplete navigation graph to employees.

### Step 3 — First-time site: verify floor plan URLs in employee-experience config

For the **very first** wayfinding deployment to a site, check that the floor plan URL configs
are set in the employee-experience service. Run the following Postman requests:

**Check current values (GET):**
```
GET https://empexp.moveinsync.com/employee-exp/<BUID>/configurations/common
```
Replace `<BUID>` with the client's BUID (example in source: `freshworks-FRPOC` — placeholder).

Verify that these three keys are present and correctly set:

| Key | Expected value |
|-----|----------------|
| `employeeFloorPlanUrl` | `https://empexp.moveinsync.com/employee-exp/static/pages/page/#/employee-view` |
| `adminFloorPlanUrl` | `https://empexp.moveinsync.com/employee-exp/static/pages/page/#/admin-view` |
| `adminAssignmentFloorPlanUrl` | `https://empexp.moveinsync.com/employee-exp/static/pages/page/#/assignment-view` |

**Update if missing or incorrect (PUT):**
```
PUT https://empexp.moveinsync.com/employee-exp/<BUID>/update-config?feature=common
```
Body (JSON):
```json
{
  "employeeFloorPlanUrl": "https://empexp.moveinsync.com/employee-exp/static/pages/page/#/employee-view",
  "adminFloorPlanUrl": "https://empexp.moveinsync.com/employee-exp/static/pages/page/#/admin-view",
  "adminAssignmentFloorPlanUrl": "https://empexp.moveinsync.com/employee-exp/static/pages/page/#/assignment-view"
}
```

_Source: SOP v2.0 — "First-time DIY upload — additional URL check" section_

## Validation Checklist

- [ ] All floors uploaded — one POST per floor, all returned 200 OK
- [ ] `forceUpdateFloorPlan=false` confirmed on every upload
- [ ] `ENABLE_INDOOR_NAVIGATION` enabled via SE ticket for the BUID
- [ ] (First-time only) Floor plan URL configs verified in employee-experience service
- [ ] Mobile app tested — wayfinding visible, QR scan resolves location, navigation renders

## Notes & Gotchas

1. **Way Path is not uploadable via Postman.** The floor plan team uploads the Way Path inside
   the DIY Floorplanner tool only. The SE team's Postman upload covers the floor plan data
   (JSON + SVG) but not the Way Path. Confirm with the floor plan team that the Way Path was
   uploaded before proceeding.

2. **Environment selection (SG / EU) is set by the floor plan team**, not the SE team, during
   Way Path upload inside the tool. Verify with the floor plan team which environment was
   selected — it must match the customer's site URL.

3. **Parking paths are unidirectional.** Parking floor plan paths flow one-way (RTL or LTR per
   segment). If parking navigation appears broken, confirm the path direction was set correctly
   during floor plan processing.

4. **Meeting room names must match calendar exactly.** If meeting rooms are not resolving
   correctly in wayfinding, confirm the room names in the floor plan match the names in
   Outlook/Google calendar exactly (case-sensitive).

5. **Amenities spanning floors (stairs, lifts) must have the same name across all floors.**
   If cross-floor navigation is broken, check that stairwell/elevator names are identical across
   all floor exports.

6. **UUID integrity on re-upload.** If any amenities were added or changed since the last
   export, the floor plan team must run Sync UUID before exporting. Skipping this step breaks
   unique-identifier references in the navigation graph.

## Related

- Module: [[modules/digital-wayfinding]]
- Upstream runbook (floor premise + plan upload): [[runbooks/floor-plan-upload]]
- Upstream (parking premise, if applicable): [[runbooks/parking-premise-setup]]
- Upstream (office premise): [[runbooks/ets-office-premise-setup]]

## Last Updated
2024-02-27 — _Source: [[sources/se-runbook-digital-wayfinding]] (SOP v2.0)_
