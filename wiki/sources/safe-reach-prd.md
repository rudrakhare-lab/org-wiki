---
type: source
raw_path: raw/modules/safe-reach/Safe Reach PRD (WIS).docx
ingested: 2026-05-26
doc_type: PRD
---

# Safe Reach — WIS PRD

## Source Title
SAFE REACH - WIS PRD

## Date
03/06/2025 (v1.0, "Initial Document"). **⚠️ UNAPPROVED**: the source's Version Control table has blank "Approved by" and "Approved Date" cells — this is an authored-but-not-formally-approved draft. Classification: **Internal**. Author: **Vaishnavi Raghav** (different from prior MoveInSync doc authors).

## Type
PRD

## Key Takeaways
- **WIS Safe Reach is distinct from ETS Safe Reach.** Source quote (line 25 of `/tmp/safe_reach_full_extract.txt`): *"Unlike the existing ETS Safe Reach which involves company cabs, WIS Safe Reach operates independently of company-provided transport, allowing employees to use their preferred mode of transport while ensuring their safety is still monitored by office admins and security teams."* The ETS variant is a separate, pre-existing implementation; this PRD describes only the WIS-side feature.
- **VMS-kiosk-initiated workflow for late-departure safety.** Employees check out at the VMS self check-in kiosk (`"I am an Employee" → "Checkout" → email/phone + OTP → DB validation`). The visibility of Safe Reach fields depends on time-of-day controlled by `SafeReachVmsTimeInMin`. Three booking-state scenarios handled (lines 49–55 of extract): pre-8PM booking (auto-checkout or manual), post-8PM booking, no booking — all funnel data to Safe Reach module. Mixed visitor+employee records: employee flow takes precedence; visitor flow ignored.
- **Three personas, ten use cases.** Employee persona (5.1) — kiosk init, additional-info form, gender trigger, ETA selection, NDA consent. Office Admin / Security Team (5.2) — dashboard, failed-verification emails, reports. System / Backend (5.3) — phone-number handling, office-level time window.
- **Configurable safety form** via `SafeReachInputFields` JSON (lines 64–72 of extract): Email/Name/Employee ID prefilled and locked; Mobile editable but does not update employee profile; Emergency Contact, Mode of Transport (dropdown + "Others" free text), Vehicle Details, Drop Location, Escort Required (with branching logic for "Escort Guard Name" and "Office Gate"/"Home Location" when Yes + non-personal transport).
- **Notification chain**: VMS success message on checkout → Mobile App notification at user-selected ETA (or default) → up to 3 IVR calls (*"Press 1 to confirm you have reached, Press 2 if you are still traveling"*) → failed-verification email at configurable intervals (e.g. every 30 min — replacing the previous single 8 AM next-day send).
- **WIS Safe Reach Report** with 14 standard columns + custom fields from `SafeReachInputFields`. Explicit removals from the ETS-equivalent report: Shift Time, "Confirmed by THD / Co-Pax / Not Travelled / TPT", Planned/Actual Sign-in Time, the "P" prefix from visit-time values, Drop Address from detail view. Renames: Planned Drop Time → Planned Arrival Time; Actual Drop Time → Confirmed Arrival Time.
- **~24 configurations across 4 PMS service categories** — Visitor Service Configurations (10 properties, 1 of which is duplicated), ETS-Side Configurations (9), Employee Experience Internal Configurations (6), Project Management Service Configurations (1). Office-level override of BUID-level for time-window settings via `KioskSafeReachInterval`. Dynamic phone-number sourcing: Safe Reach uses the checkout-provided number, stored separately, **does not overwrite** the Employee DB record.
- **⚠️ Configuration ambiguities surfaced by the source itself**: (a) **Two "master switches"** — `enableSafeReachForBookingTypes` (described as *"Master boolean property that governs the overall functionality of Safe Reach"*) AND `SAFE_REACH_ENABLED` (described as *"To enable safe reach dashboard"*). Source does not state which is THE master. (b) **`enableSignatureForConsentSafeReach` is listed twice in Table 2** with different descriptions (rows 8 and 14) — same name, same type, same scope — likely an editorial mistake but both rows surface verbatim. (c) **`safeReachETAOptions`** is referenced in body (line 83: *"refer to Key Configurations/Properties for safeReachETAOptions"*) but does NOT appear in Table 2. Closest match: `etaToReachDestination (Within SafeReachInputFields)`. Possible naming inconsistency between body prose and config table.

## Entities Mentioned
(none — the PRD describes a workflow and configuration namespace, not a formal entity schema)

## Modules Mentioned
- [[modules/safe-reach]] (primary subject)
- [[modules/visitor-management]] (VMS Kiosk is the named primary interface — Dependencies/Integrations line 159)

## Decisions Extracted
(none — the PRD records Problem→Solution pairs for several use cases [UC 2.1 reporting-manager removal, multi-interval email send, UC 3.0 phone-number sourcing, UC 3.1 office-level override] but does not provide the §2e schema's alternatives-considered + consequences. These are product-level changes, not architectural decisions)

## Wiki Pages Created/Updated
- Created: [[modules/safe-reach]]
- Updated: [[index]], [[log]]

_Source: [[sources/safe-reach-prd]]_
