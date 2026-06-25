---
type: runbook
module: ets
team: SE (Service Engineering)
status: active
last_updated: 2026-06-25
source: "[[sources/se-runbook-ets-office-premise]]"
raw_path: raw/se-runbook/WIS-Configurations-ETS-EmployeeApp-GuardApp-SanitisationApp.docx
---

# Runbook — ETS Office Premise Setup

> SE procedure to **create, edit, and set the booking capacity of an Office premise** in the WorkInSync backend, using the **WIS-Configurations Google sheet** (`1FyWuDnS…`) + **Postman** + **G-Tool**.
> ⚠️ Every concrete value below (`tata-TCPOC`, GUIDs like `LOtataTC-POC$-…`, geocodes, premiseIds) is an **EXAMPLE / placeholder** — replace with the client's actual values. Nothing here is literal config.
> _Source: [[sources/se-runbook-ets-office-premise]] (raw doc sections 1–10)_

## Purpose & Scope
Covers the Office-premise slice of ETS premise configuration: prerequisites in ETS, creating the office premise, validating it, editing name/geocode/geofence, and adding/editing booking capacity. Parking, floor, guard, amenities, sanitization, and meal setup are separate runbooks (see Configuration Flow below).

## Prerequisites
Before raising the SE ticket, the **requestor** must already have created, inside **ETS**:
- **Office** — ETS → switch to **MISADMIN** → **Data Upload** → **Manage Office** (the *Manage Offices* screen lists Site No · Office Name · Geocords · Edit/Delete, with an **Add New Office** button).
- **Shifts** — ETS → **Site Administrator** → **Scheduling Management** → **Manage Shifts**.

Only after the office + shifts exist should the requestor raise the SE ticket with the requirement.

## Configuration Flow (where this fits)
`Office Premise creation → Add Capacity to Office → Parking Premise → Parking Capacity → Floor premise → Upload Floor → Guard User → Amenity → Seat Sanitization → Meal Booking.`
Each uses **G-Tool and/or Postman**. **This runbook = Office premise + capacity.**

## Step-by-step

### A — Create the Office premise
1. **Get the office GUID.** In Postman: `GET https://<tenant>.moveinsync.com/<TENANT>/ets/apis/office` _(example: `tata.moveinsync.com/TCPOC/ets/apis/office`)_. Save `guid`, `address`, `geoCord` to Notepad _(example `guid: LOtataTC-POC$-0000-0000-000000000001`, `geoCord: 13.051826,77.595410`)_.
2. **Fill the WIS-Configurations sheet** (`1FyWuDnS…`) and click **Submit**. Columns:
   | Column | Value | Note |
   |--------|-------|------|
   | `Buid` | client BUID | e.g. `tata-TCPOC` |
   | `Service/Feature` | `premise` | |
   | `premiseType` | `2` | **2 = office** |
   | `parentPremise` | _(blank)_ | leave blank at this stage |
   | `premiseName` | office name | |
   | `geoCode` | office geocode | |
   | `techparkId` | _(blank)_ | leave blank at this stage |
   | `buIdOfficeGuid` | from Notepad (step 1) | |
   | `City` / `Country` | | |
3. **Clear cache** — in a browser open `https://bookingrule.moveinsync.com/booking-rule-engine/cahce/<OFFICE_GUID>/evict/premise` using the office GUID from step 1.

### B — Validate the premise
`GET https://mis-security.moveinsync.com/mis-security-guard/premise/buid/<BUID>` → `Ctrl+F` the `premiseName` to confirm it exists. Note the returned `premiseId` (needed for capacity).

### C — Edit PremiseName / geoCode / geofenceDistance
1. `GET …/mis-security-guard/premise/buid/<BUID>` → copy the premise JSON object (**copy to the end; drop the trailing `,` comma**).
2. `PUT https://mis-security.moveinsync.com/mis-security-guard/premise` with that JSON, changing `premiseName`, `geoCode`, and/or `geofenceDistance` to the new values.
3. Clear cache (same evict URL as A.3).

### D — Add Office booking capacity
Use the WIS-Configurations sheet with `Service/Feature = premise capacity`. Fields: `capacity`, `startDate`, `endDate`, `startMinOfDay = 0`, `endMinOfDay = 1439`, `premiseId` (from B).
- **Capacity calculation:** for **DB client sites**, `capacity = login shifts × seats per shift` (e.g. `10 × 50 = 500`). For **all other clients**, enter the requested number directly (no multiply).

### E — Validate capacity
`GET …/mis-security-guard/premise-capcity/buid/<BUID>?startTime=<ms>&endTime=<ms>` → `Ctrl+F` the `premiseId` → should display the capacity. Clear cache.

### F — Edit Office capacity
1. `GET …/premise/buid/<BUID>` → get the `premiseId`.
2. `GET …/premise-capcity/buid/<BUID>?startTime=<ms>&endTime=<ms>` → find the existing capacity record by `premiseId`; copy the JSON (drop trailing comma).
3. `PUT https://mis-security.moveinsync.com/mis-security-guard/premise-capcity` with the JSON, changing `capacity` to the new value.
4. Clear cache.

## Screenshots (transcribed; originals in the vault `raw/se-runbook/images/`)
- `sec01_img000` — ETS **Manage Offices** screen: table (Site No · Office Name · Geocords · Edit/Delete) + **Add New Office** button.
- `sec01_img001` — ETS **Manage Shifts** screen (Scheduling Management).
- `sec04_img002` — Postman: a new **GET** request (empty URL bar; Params/Authorization/Headers/Body tabs).
- `sec04_img003` — Postman response of `ets/apis/office` (the `guid`/`address`/`geoCord` to save).
- `sec04_img004` — **WIS-Configurations** sheet row + **Submit** (columns listed in step A.2).
- `sec04_img005`, `sec08_img008` — Postman `premise/buid/<BUID>` response (the premise JSON incl. `premiseId`).
- `sec05_img006` — Postman PUT for editing the premise.
- `sec07_img007` — WIS sheet **premise capacity** form.
- `sec09_img009` — Postman `premise-capcity` validation response.
- `sec10_img010`, `sec10_img011`, `sec10_img012` — Postman GET premise → GET capacity → PUT new capacity.

## Validation checklist
- [ ] Premise visible via `premise/buid/<BUID>` (Ctrl+F `premiseName`)
- [ ] Capacity visible via `premise-capcity/buid/<BUID>` (Ctrl+F `premiseId`)
- [ ] Cache evicted after **every** create/edit

## Notes & Gotchas
- **Always clear cache** after any premise/capacity create or edit, via `https://bookingrule.moveinsync.com/booking-rule-engine/cahce/<OFFICE_GUID>/evict/premise` (note the source's literal `cahce` spelling). Easy to forget — changes won't reflect otherwise.
- `premiseType = 2` means **office**.
- Leave `parentPremise` and `techparkId` **blank** at office-creation time.
- When copying a JSON object from a GET response into a PUT, **copy to the end and remove the trailing comma**.
- The evict-URL GUID `LOrandst-adRS-Ind$-…` shown in the source is itself an **example** — use the client's own office GUID.
- ⚠️ **Conflict in the source on the capacity multiply rule** — section "Premise Capacity" says the `shifts × seats` multiply applies to **DB-client sites only** (others enter the number directly), but section "TO Edit Office capacity" states a general "multiply requested capacity × shift count" (e.g. 25,000 × 5 = 125,000) with no DB-only qualifier. **Needs owning-team confirmation** of whether the multiply is DB-client-only or universal. _(Per Conflict & Recency policy — both statements preserved; not silently resolved.)_

## Related
- Module: [[modules/ets]]
- Tool: WIS-Configurations sheet (`1FyWuDnS…`)
- ETS operation/engineering settings live in the **ETS config spreadsheet** (`1WpEu4vW…`, 11 tabs: Properties, Booking Service, Emp Ex, Mobile-App, Datasync, guard-*-db-insert, guard*-endpoints) — to be ingested by the reference crawler; this runbook links to it.
- Downstream runbooks: `runbooks/parking-premise-setup`, `runbooks/floor-plan-upload`, `runbooks/guard-user-creation` (pending ingest).

## Related Jira
— none cited in sections 1–10; the reference crawler will link ETS tickets (e.g. PB-52960 per CLAUDE.md ETS notes).

## Last Updated
2026-06-25 — source: [[sources/se-runbook-ets-office-premise]] (raw: `raw/se-runbook/WIS-Configurations-ETS-EmployeeApp-GuardApp-SanitisationApp.docx`, sections 1–10)
