---
type: source
raw_path: raw/modules/parking-management/MoveInSync Workplace - Dynamic Policy for Parking.docx
ingested: 2026-04-28
doc_type: spec
---

# Dynamic Policy for Parking

## Source Title
Dynamic Policy for Parking (v1.3)

## Date
v1.0: 10-07-2024; v1.3: 22-10-2025

## Type
spec (admin SOP + feature explanation)

## Key Takeaways
- Extends the tag engine (same as desks and meeting rooms) to parking slots for vehicle-type-based access control.
- **Two-pronged upload**: "Employee Tagging" file (assigns policies to users) + "Parking Tagging" file (assigns policies to slots). Both uploaded via Desk Bulk Upload section.
- **Policy values**: `Yes` = grant access, `Null/null` = remove policy, `blank` = no change to existing policy.
- **BLOCK_HOTSEAT** policy: when applied to an employee, prevents them from booking hotslots — forces them to only book slots they're directly tagged to.
- Real-world example: vehicle build types (Hatchback, Sedan, SUV/Crossover) as tag values — employees tagged with a vehicle type can only book slots tagged for that vehicle type.
- **Edge case handling**: if tag start date gets corrupted during upload (future date), fix by uploading null for all affected tags first, then re-uploading with correct dates.
- **New slot onboarding** requires email to MoveInSync team for backend addition — **not self-serve**.
- SOP for adding new employees and new slots is documented in this spec.

## Entities Mentioned
- [[entities/parking-slot]]

## Modules Mentioned
- [[modules/parking-management]] (primary)
- [[modules/tags-desk-parking]] (tag engine — explicitly the same system)

## Decisions Extracted
- None new — tag pattern is consistent with desks and meeting rooms.

## Wiki Pages Created/Updated
- Updated: [[modules/parking-management]]
- Updated: [[cross-module/parking-tags-desk-parking]]

_Source: [[sources/dynamic-policy-parking]]_
