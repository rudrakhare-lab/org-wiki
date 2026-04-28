---
type: source
raw_path: raw/modules/parking-management/Copy of Copy of Parking PRD.docx
ingested: 2026-04-28
doc_type: PRD
---

# Parking Management PRD

## Source Title
Parking Management PRD (v1.2)

## Date
30/03/2022 (v1.0: Oct 2021, v1.2: Mar 2022)

## Type
PRD

## Key Takeaways
- Parking is surfaced as part of the **WFO (Work From Office) booking form** — employees add parking as an add-on when booking a desk/office day. Not a standalone booking flow.
- **Premise hierarchy**: Office → Parking Facility (Zone) → Floor (Level) → Slot. One office can have multiple zones; one zone can have multiple levels; each level has Car and Bike slots.
- **Slot assignment types**: Hotslot (open to all), Employee (dedicated to one person), Team (reserved for team members), Blocked, Unallocated. Default is Hotslot.
- **Two booking modes**: Auto Allocation (system picks slot sequentially) and Grid-based (employee picks visually from floor plan). Both respect assignment type rules and tag policies.
- **Allocation priority** (auto mode): Dedicated Employee slot → Team slot → Hotslot. Overflow cascades down.
- Vehicle number stored per booking (not overwriting profile default). Both car and bike registration storable in profile.
- **Default loading**: pre-fills previous booking's zone/level (up to last 30 days) to reduce friction.
- **Check-in**: QR code scan at premise or Digipass from mobile app. Check-in is premise-configurable — parking check-in and office check-in can be independent or chained.
- **Tag-based access control** (same pattern as meeting rooms): admin creates tag type–value pairs, assigns to employees and slots; system matches at booking time.
- **BLOCK_HOTSEAT** special policy tag: prevents employee from booking hotslots (forces them to their dedicated/tagged slot only).
- Buffer times: `MM` minutes before login time and after logout time for parking slot availability (configurable).
- Slot numbers shown in summary and drill-down views; QR code per zone/level for check-in.

## Entities Mentioned
- [[entities/parking-slot]]
- [[entities/parking-booking]]

## Modules Mentioned
- [[modules/parking-management]] (primary)
- [[modules/tags-desk-parking]] (tag engine reused)
- [[modules/mobile-app]] (booking surface)
- [[modules/desk-management]] (WFO booking form context)

## Decisions Extracted
- [[decisions/2026-04-28-parking-slot-allocation-priority]]

## Wiki Pages Created/Updated
- Created: [[modules/parking-management]]
- Created: [[entities/parking-slot]]
- Created: [[entities/parking-booking]]

_Source: [[sources/parking-prd]]_
