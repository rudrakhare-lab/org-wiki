---
type: module
status: active
owner: unknown
depends_on: [visitor-management]
used_by: []
last_updated: 2025-06-03
source: "[[sources/safe-reach-prd]]"
---

# Safe Reach Module

## Overview
**Safe Reach** is WorkInSync's late-departure safety workflow for employees leaving the
office after designated hours (e.g. 8 PM). It is initiated at the **VMS self check-in
kiosk** and orchestrates a notification chain (mobile app → IVR calls → escalation to
manual verification by security personnel) to confirm the employee's safe arrival at their
destination. WIS Safe Reach is **independent of company-provided transport** — unlike the
pre-existing ETS Safe Reach, which is tied to company cab bookings, this module operates
for employees using any mode of transport. Configuration is split across four PMS service
categories with office-level overrides of BUID-level defaults.

## Purpose & Scope
Owns the WIS-side Safe Reach workflow surface: VMS-kiosk-initiated checkout flow, the
configurable safety-information form, the gender-trigger logic, employee-selected ETA, NDA
consent capture (checkbox or signature), the WIS dashboard for office admins / security
teams, the failed-verification email pipeline, the WIS Safe Reach Report, and the dynamic
phone-number-sourcing logic.

Does **not** own: the **ETS Safe Reach** workflow (a separate, pre-existing implementation
tied to company cab bookings — not in the canonical `wiki/modules/` slug list), the
Employee Database (source of truth for prefilled employee data), the IVR infrastructure
(used but not owned), the email infrastructure (used but not owned), the Mobile Notification
System (used but not owned — possibly `mobile-app`, but the source does not explicitly map
this dependency), or the PMS service itself (owns the **config namespace** within PMS, but
not the PMS service).

## Key Features
- **VMS kiosk-initiated checkout** with three booking-state scenarios — pre-8PM booking (auto-checkout or manual), post-8PM booking, or no booking — all funnel relevant info to the Safe Reach module. Mixed visitor+employee records: employee flow takes precedence; visitor flow is ignored. Visibility of Safe Reach fields depends on time-of-day controlled by `SafeReachVmsTimeInMin`
- **Configurable safety-information form** via `SafeReachInputFields` JSON: Email / Name / Employee ID prefilled and locked; Mobile editable (but does not update Employee profile); Emergency Contact, Mode of Transport (dropdown + "Others" free text), Vehicle Details, Drop Location, Escort Required (with branching logic for "Escort Guard Name" + "Office Gate" or "Home Location" when Yes + non-personal transport)
- **Gender-based trigger** — `triggerSafeReachForFemaleOnly` (BUID-level Boolean) restricts the workflow to female employees only. Edge case: if gender is missing from the employee profile, Safe Reach will NOT be triggered for that employee
- **Employee-configurable ETA** — dropdown *"ETA to Reach Destination"* in the kiosk flow drives mobile-notification + IVR timing. Default 90 min if not selected. Source body references `safeReachETAOptions` for the dropdown values (see Open Questions for naming caveat)
- **NDA consent capture** — checkbox OR digital signature, switchable via `enableSignatureForConsentSafeReach`. Content provided by the client team
- **Sequential notification chain** — (a) VMS success message immediately on checkout (*"Safe reach has been initiated. You will receive a call in [Selected ETA or 90] mins to confirm if you have reached your destination."*); (b) mobile-app notification at user-selected ETA or default time; (c) **up to 3 IVR calls** if mobile fails (*"Press 1 to confirm you have reached, Press 2 if you are still traveling"*); (d) failed-verification email at configurable intervals
- **Real-time WIS dashboard** for office admins and security teams — accessible from WIS side nav. Refresh button retains all filters (status, date, employee search, BUID). Columns customized for WIS (ETS-irrelevant fields removed). "No data matching the filter" message when refresh returns empty
- **Failed-verification email pipeline** — multi-interval send (e.g. every 30 min) replaces the prior single 8 AM next-day run. Subject template: *"Alert: Unconfirmed Safe Arrival of {Employee Name} ({Employee ID}) - {Office Location Name}"*. Office-level CC list with BUID fallback via `safeReachCcList`. Reporting Manager removed from CC for WIS clients (ETS clients unaffected)
- **WIS Safe Reach Report** — 14 standard columns (Emp Id, Employee Email, Emp Name, Gender, Emp Contact, **Safe Reach Contact**, ETA to Destination, Time of Leaving Office, Verification Status, Verification Type, Verification Time, Verified By, Comment, **Drop Location (new)**) plus dynamic custom fields from `SafeReachInputFields`. Removals from the ETS-equivalent report: Shift Time, Confirmed-by THD/Co-Pax/Not-Travelled/TPT, Planned/Actual Sign-in Time, "P" prefix from visit time values, Drop Address from detail view. Renames: Planned Drop Time → Planned Arrival Time; Actual Drop Time → Confirmed Arrival Time
- **Office-level overrides of BUID defaults** — `KioskSafeReachInterval` (office-level Array) overrides the BUID-level Safe Reach trigger time. Fallback to BUID if office-level is not set
- **Dynamic phone-number sourcing** — Safe Reach uses the phone number entered at checkout, not the Employee DB record. Stored separately in the Safe Reach DB; **does not overwrite** the Employee profile. Reports flag phone-edited cases. Validation prevents invalid entries

## Data Entities Used
(none — this module describes a workflow + configuration namespace; the source introduces no formal data entities)

## Dependencies on Other Modules
- [[modules/visitor-management]] — the **VMS kiosk** is the named primary interface for Safe Reach initiation (Dependencies/Integrations section of source, line 159: *"VMS Kiosk: Primary interface for employee checkout and Safe Reach initiation."*)

## Used By
(none declared in source — no other module is named as a consumer of Safe Reach)

## API Endpoints
The PRD does **not** enumerate specific API endpoint paths. UC 3.0 (line 148 of extract) references *"API logic will be modified to fetch the dynamically updated phone number for call triggering"* without naming paths. **Update this section when an engineering reference is ingested.**

## Key Configurations

The source groups ~24 configurations across 4 PMS service categories. Both apparent editorial issues (the duplicated `enableSignatureForConsentSafeReach` row, the missing `safeReachETAOptions`) are surfaced faithfully — see Open Questions.

### Visitor Service Configurations
| Property | Description (from source) | Type & Scope |
|---|---|---|
| `SafeReachVmsTimeInMin` | Defines the time window (in minutes from 00:00 AM) after which Safe Reach specific fields and workflow are triggered on the VMS kiosk. | Array; office-level |
| `safeReachConsentContent` | Defines the consent statement content with a checkbox displayed at the end of the Safe Reach form on the VMS kiosk. | Array; office-level |
| `triggerSafeReachForFemaleOnly` | Boolean flag to enable Safe Reach workflow and field visibility only for female employees. | Boolean; BUID-level |
| `enableSafeReachForBookingTypes` | Master boolean property that governs the overall functionality of Safe Reach. If false, `triggerSafeReachForFemaleOnly` cannot be enabled. | Boolean; BUID-level |
| `SafeReachInputFields` | JSON structure to define custom input fields | JSON; office-level |
| `safeReachCcList` | List of email addresses to be CC'ed for failed Safe Reach verification emails. | Array; office-level |
| `enableSignatureForConsentSafeReach` | Boolean flag to enable signature capture for NDA consent instead of a checkbox during Safe Reach checkout. | Boolean; office-level |
| `etaToReachDestination` (within `SafeReachInputFields`) | Defines the configurable intervals for "ETA to Reach Destination" dropdown. | JSON; BUID-level |
| `enableSignatureForConsentSafeReach` | To introduce signature for consent | Boolean; office-level |
| `KioskSafeReachInterval` | To configure start and end time of safe reach trigger | Array; office-level |

⚠️ `enableSignatureForConsentSafeReach` appears twice in this group with different descriptions — see Open Questions.

### ETS-Side Configurations
| Property | Description (from source) | Type |
|---|---|---|
| Mobile App Notification | Enable/disable mobile app notifications for Safe Reach. | Boolean |
| IVR Verification | Enable/disable verification through IVR calls. | Boolean |
| Gender | Selection of gender(s) eligible for Safe Reach verification (if `triggerSafeReachForFemaleOnly` is false). | Single-select |
| Start IVR at Sign off | Boolean to immediately trigger IVR on checkout. | Boolean |
| Mobile Notification Trigger time in mins | Default time after checkout to trigger mobile notification if ETA is not selected by employee. | Integer |
| IVR Trigger Buffer Time in mins | Default time after which IVR should trigger if mobile notification is not set up and ETA is not provided. | Integer |
| Time Difference Between Mobile App Notification And First IVR Call Time | Configurable time difference between mobile notification and the first IVR call. | Integer |
| Difference Between Two Consecutive IVR Calls | Configurable time difference between sequential IVR calls. | Integer |
| Drop verification failed email ID | Default recipients for failed verification emails if `safeReachCcList` is not active for a specific BUID/Office. | List |

### Employee Experience Internal Configurations
| Property | Description (from source) | Type & Scope |
|---|---|---|
| `wisFailDropEmailSubject` | To define the subject line of failed verification email | String; BUID-level |
| `wisManualSuccessEmailSubject` | To define the subject line of manual successful email | String; BUID-level |
| `wisSafeReachReportingManagerEnabled` | Controls if reporting manager should be cc'ed or not in the failed verification email | Boolean; office-level |
| `wisSafeReachCcList` | Controls cc list of failed verification email | Array; office-level |
| `wisDropVerificationFailedEmail` | To enable failed verification email | Boolean; BUID-level |
| `wisDropVerificationManualSuccessEmail` | To enable manual successful email | Boolean; BUID-level |

### Project Management Service Configurations
| Property | Description (from source) | Type & Scope |
|---|---|---|
| `SAFE_REACH_ENABLED` | To enable safe reach dashboard | Boolean; BUID-level |

## Open Questions
- ⚠️ **Master-switch ambiguity** — two properties both claim master-like behavior:
  - `enableSafeReachForBookingTypes` (BUID-level Boolean, Visitor Service Configurations) — source quote: *"Master boolean property that governs the overall functionality of Safe Reach. If false, triggerSafeReachForFemaleOnly cannot be enabled."*
  - `SAFE_REACH_ENABLED` (BUID-level Boolean, Project Management Service Configurations) — source quote: *"To enable safe reach dashboard"*
  Unclear from this source whether one is the true master and the other is a derived flag, whether both must be on, or whether they govern different surfaces (workflow vs dashboard). **Do not assume an enablement order from this source alone.**
- ⚠️ **Duplicated `enableSignatureForConsentSafeReach` row in Table 2** — the property appears at row 8 (description: *"Boolean flag to enable signature capture for NDA consent instead of a checkbox during Safe Reach checkout."*) AND row 14 (description: *"To introduce signature for consent"*). Same name, same type (Boolean), same scope (office-level). Likely an editorial mistake in the source; both rows are preserved above for fidelity. Confirm with engineering whether there are truly two properties or one.
- ⚠️ **`safeReachETAOptions` referenced in body but missing from Table 2.** Use Case 1.3 (line 83 of extract) says: *"The dropdown values are configurable (refer to Key Configurations/Properties for safeReachETAOptions)."* The property name `safeReachETAOptions` does NOT appear in Table 2. Closest match in the table: `etaToReachDestination (Within SafeReachInputFields)`. Possible naming inconsistency — body and table may refer to the same property under different names.
- ⚠️ **Source v1.0 is UNAPPROVED.** Table 1 has blank "Approved by" and "Approved Date" cells. This is an authored-but-not-formally-approved draft. Consumers should treat the contents as a work-in-progress; the feature may have evolved or been revised before launch.
- **ETS Safe Reach is a separate feature.** Line 25 of extract: *"Unlike the existing ETS Safe Reach which involves company cabs, WIS Safe Reach operates independently..."* ETS Safe Reach is referenced but is NOT in the canonical `wiki/modules/` slug list (CLAUDE.md §1). Questions about "Safe Reach" generally may target either variant. No wiki module documents the ETS variant.
- **`SafeReachVmsTimeInMin` declared as Array** but described as a "time window" (singular). Possibly intended for multiple discrete trigger periods (per day-of-week? per shift?) but the body does not elaborate. Worth confirming.
- **`mobile-app` coupling unclear.** The PRD references "Mobile App Notification" and "Mobile Notification System" as a dependency, but does NOT explicitly name the `mobile-app` module as the surface. Could be a different notification subsystem. Frontmatter `depends_on` omits `mobile-app` for honesty; revise if engineering confirms.
- **API endpoints not enumerated.** The PRD references "API logic will be modified" (UC 3.0) without paths. Update API Endpoints section when an engineering reference is ingested.
- **Module owner** — author **Vaishnavi Raghav**; "Approved by" cell blank in Version Control. No owning team named. `owner: unknown`.

## Last Updated
2025-06-03 — _Source: [[sources/safe-reach-prd]]_ (v1.0, unapproved)
