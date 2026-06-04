---
last_updated: '2025-06-03'
modules:
- safe-reach
- visitor-management
relationship: safe-reach depends_on visitor-management
source: '[[sources/safe-reach-prd]]'
type: cross-module
---

# Safe Reach ↔ Visitor Management — VMS Kiosk as Safe Reach Entry Point

## Relationship

**Safe Reach** (`modules/safe-reach`) depends on **Visitor Management** (`modules/visitor-management`). The VMS self check-in kiosk is the sole named primary interface through which Safe Reach is initiated.

> _Source (PRD Dependencies/Integrations section):_ **"VMS Kiosk: Primary interface for employee checkout and Safe Reach initiation."**

See also: [`modules/safe-reach`](../modules/safe-reach.md) · [`modules/visitor-management`](../modules/visitor-management.md)

---

## Checkout Flow Handoff

Safe Reach is triggered exclusively through the VMS kiosk checkout path:

1. Employee selects **"I am an Employee"** on the VMS kiosk.
2. Employee selects **"Checkout"**, enters email/phone + OTP, and is validated against Employee DB.
3. On successful checkout validation, VMS hands off to the **Safe Reach Core Module** — but only if the current time is within the Safe Reach activation window (governed by `SafeReachVmsTimeInMin`).
4. If Safe Reach is active, the employee is presented with the configurable Safe Reach additional-information form (`SafeReachInputFields`) and, where applicable, the NDA consent screen.
5. On form submission, VMS displays a success/confirmation message and the backend notifies the Safe Reach pipeline.

---

## Three Booking-State Scenarios

The PRD defines three states that affect how checkout data is routed to Safe Reach:

| Scenario | Condition | Handling |
|---|---|---|
| **Pre-8 PM booking** | Employee has a cab booking scheduled before 8 PM | Auto-checkout eligible; manual checkout also supported |
| **Post-8 PM booking** | Employee has a cab booking scheduled after 8 PM | Manual checkout at kiosk; Safe Reach form shown if within time window |
| **No booking** | Employee has no cab booking at all | Manual checkout at kiosk; Safe Reach form shown if within time window |

All three scenarios funnel employee data into the Safe Reach module upon checkout completion.

---

## Employee-vs-Visitor Precedence Rule

When a single kiosk session contains both a **visitor record** and an **employee record** (mixed check-in/checkout):

- The **employee checkout flow takes precedence** and the Safe Reach form is presented for the employee.
- The visitor flow is **ignored** for Safe Reach purposes in that session.

---

## Time-of-Day Gating

Safe Reach is not shown at all hours. Visibility of Safe Reach fields at the kiosk is controlled by:

| Config Property | Scope | Description |
|---|---|---|
| `SafeReachVmsTimeInMin` | BUID-level (Visitor Service) | Time threshold (in minutes, offset from a reference time) after which the Safe Reach form is displayed at checkout |
| `KioskSafeReachInterval` | Office-level override | Allows individual offices to override the BUID-level `SafeReachVmsTimeInMin` window |

The office-level `KioskSafeReachInterval` takes precedence over the BUID-level setting when set.

---

## Shared Config Properties in the VMS Namespace That Govern Safe Reach

The following configuration properties live in the **Visitor Service** PMS config category but directly control Safe Reach behaviour at the kiosk interface:

| Property | Type | Scope | Description |
|---|---|---|---|
| `enableSafeReachForBookingTypes` | Boolean | BUID | Master boolean — governs the overall enablement of Safe Reach. ⚠️ See open question on dual master switches in source warnings. |
| `SafeReachInputFields` | JSON | BUID | Defines the Safe Reach additional-information form fields shown at the kiosk. Email, Name, Employee ID are prefilled and locked; Mobile is editable but does not update the Employee DB record. Includes: Emergency Contact, Mode of Transport (dropdown + free-text "Others"), Vehicle Details, Drop Location, Escort Required (with branching logic). |
| `SafeReachVmsTimeInMin` | Integer | BUID | Time-of-day threshold controlling Safe Reach field visibility at checkout (see above). |
| `KioskSafeReachInterval` | Integer | Office | Office-level override for the Safe Reach time window (see above). |
| `enableSignatureForConsentSafeReach` | Boolean | BUID | Enables signature capture for NDA consent instead of a checkbox during Safe Reach checkout. ⚠️ Appears twice in source PRD Table 2 (rows 8 and 14) with differing descriptions — likely an editorial error. |
| `triggerSafeReachForFemaleOnly` | Boolean | BUID | When true, restricts the Safe Reach workflow to female employees only. |
| `safeReachConsentContent` | String/HTML | BUID | Content of the NDA/consent screen shown during Safe Reach checkout at the kiosk. |
| `safeReachCcList` | List | BUID | Email addresses CC'd on Safe Reach failed-verification notifications. |

> **Config pages:** All properties above are fully documented in [`configs/visitor-management`](../configs/visitor-management.md).

---

## Open Questions (Carried from Source Ingestion)

These are unresolved ambiguities in the source PRD — not introduced by this wiki page:

1. **Dual master switches**: `enableSafeReachForBookingTypes` (Visitor Service, described as _"Master boolean property that governs the overall functionality of Safe Reach"_) and `SAFE_REACH_ENABLED` (PMS, described as _"To enable safe reach dashboard"_) both appear to be master-level flags. The PRD does not clarify their relationship or priority order.
2. **Duplicate config row**: `enableSignatureForConsentSafeReach` appears twice in PRD Table 2 (rows 8 and 14) with different descriptions. Likely an editorial error in the source.
3. **Property name mismatch**: `safeReachETAOptions` is referenced in Use Case 1.3 body text but does not appear in the Key Configurations/Properties table. Closest match: `etaToReachDestination (Within SafeReachInputFields)`. May be the same property under two names.

---

## Source

- PRD: [[sources/safe-reach-prd]] — Safe Reach WIS PRD v1.0, 03/06/2025, author: Vaishnavi Raghav. ⚠️ Unapproved draft (blank "Approved by" / "Approved Date" cells).
- Note: The source PDF (`raw/modules/_uploads/0a5a3f58ab4f03be/Safe Reach PRD (WIS).pdf`) is a re-upload of the original `.docx` (`raw/modules/safe-reach/Safe Reach PRD (WIS).docx`). Content is identical.

