---
type: source
raw_path: raw/modules/visitor-management/Copy of Visitor Management PRD.docx
ingested: 2026-04-28
doc_type: PRD
---

# Visitor Management PRD

## Source Title
Visitor Management PRD (v1.4 → v1.5)

## Date
v1.0: Oct 2021; v1.4: 11/07/2023; v1.5: updated by Vaishnavi Raghav

## Type
PRD

## Key Takeaways
- VMS manages the full lifecycle of office visitor access — from invite creation to check-in, check-out, and badge printing.
- **4 Personas**: Employee/Host (creates invite), Visitor (accepts, completes profile), Receptionist/Front Desk (manages check-in), Security Guard (first gate check), Admin (configs + reports).
- **Two visitor types**: Invited (scheduled, email-based) and Walk-in (managed at reception, OTP-based identity verification).
- **Invite lifecycle**: Host creates invite → Visitor receives email → Accepts + completes profile → Receives Digipass (QR code) → Security gate scan → Front desk check-in → Badge printed.
- **Digipass** (`VISITOR_DIGIPASS`): QR code emailed to visitor post-profile-completion. Configurable per office. Auto-send option (`digipassAutoSend`) skips waiting for visitor acceptance.
- **2-step check-in**: (1) Security gate — guard scans digipass, marks "Security Complete"; (2) Front desk — receptionist verifies ID, allows entry, prints badge. Time between gates tracked; "Delayed Check-in" status if visitor takes > N min.
- **Manager approval workflow**: Invite can require manager approval before visitor is notified. Auto-approve or auto-reject after timeout (configurable).
- **Walk-in flow**: Receptionist enters visitor details, OTP sent to visitor for identity; host approval optional (`Employee_Approve_WalkInVisitor`). Walk-in vs. scheduled stored per record.
- **Temporary check-out** (`Visitor_Temp_Check_Out`): Visitor can step out (lunch/meeting) and return without re-creating booking.
- **Visitor parking** (built, V1): Dedicated "Visitor"-tagged parking slots, auto-allocated by VMS. Invisible to regular employees. Controlled by `Visitor_Parking_Auto_Allocation`.
- **Dynamic fields** (`enableDynamicField`): Configurable additional fields for visitor profile capture (text, boolean, numeric, date, binary).
- **Badge printing** (`Print_Visitor_Badge`): Receptionist prints badge at check-in. Configurable logo. Audit: who printed, when, how many times.
- **NDA validity**: Configurable N-day NDA reuse for repeat visitors (not forced to re-sign every visit).
- **GDPR**: Visitor PII stored separately, forgotten after X days (configurable). Visitor data can optionally be saved for future invites (employee opt-in).
- **Recurring invites**: Max 90 days into future (BUID-level, `recurringInviteMaxDays`). Supports Daily/Weekly/Monthly/Custom patterns.
- V2 (not yet built): desk booking for visitor, meeting room booking for visitor, self-check-in, mobile/SMS notifications.

## Entities Mentioned
- [[entities/visitor-invite]]
- [[entities/visitor-profile]]

## Modules Mentioned
- [[modules/visitor-management]] (primary)
- [[modules/parking-management]] (visitor parking slot auto-allocation)
- [[modules/guard-app-kiosks]] (security guard uses guard app to scan visitor digipass)

## Decisions Extracted
- [[decisions/2026-04-28-vms-2step-checkin]]
- [[decisions/2026-04-28-vms-digipass-as-primary-auth]]

## Wiki Pages Created/Updated
- Created: [[modules/visitor-management]]
- Created: [[entities/visitor-invite]]
- Created: [[entities/visitor-profile]]
- Created: [[cross-module/vms-parking-management]]
- Created: [[cross-module/vms-guard-app]]

_Source: [[sources/vms-prd]]_
