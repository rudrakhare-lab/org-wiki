---
type: module
status: active
owner: unknown
depends_on: [parking-management, guard-app-kiosks, ms-teams-integration]
used_by: []
last_updated: 2023-07-11
source: "[[sources/vms-prd]], [[sources/vms-implementation]]"
---

# Visitor Management Module (VMS)

## Overview
Visitor Management handles the complete lifecycle of visitor access to office premises.
It supports two visitor types — **Invited** (scheduled in advance by an employee) and
**Walk-in** (handled at the reception desk on arrival). The system manages invites,
visitor registration/profile, manager approval workflows, digipass generation, 2-step check-in
(security gate + front desk), badge printing, visitor parking, and compliance/GDPR.

## Purpose & Scope
Owns: VisitorInvite and VisitorProfile entities, all check-in/out lifecycle, digipass generation,
NDA management, badge printing, visitor parking auto-allocation, notifications (email/SMS),
and reporting.

Does **not** own: the parking slot infrastructure (owned by `parking-management`), the guard
scanning device/app (owned by `guard-app-kiosks`), or the calendar/Teams connector for host
calendar invites and MS Teams notifications (owned by `ms-teams-integration`).

## Key Features
- **Scheduled invite**: Employee creates event, invites visitors by email/bulk upload → Visitors accept, complete profile → Receive Digipass → 2-step check-in
- **Walk-in visitor**: Receptionist captures visitor details at desk, OTP sent to visitor phone/email for identity; optional host approval via OTP
- **2-step check-in**: (1) Security gate — guard scans visitor digipass via Guard App; (2) Front desk — receptionist verifies ID/photo, allows entry, prints badge
- **Digipass**: QR code emailed to visitor post-profile-completion. Configurable per office. Auto-send available (skip accept step)
- **Manager approval workflow**: Invite can require manager sign-off before visitor is notified. Auto-approve or auto-reject on timeout
- **Visitor parking**: VMS auto-allocates visitor-tagged parking slots (separate from employee slots, invisible to employees). Receptionist notes parking slot at check-in
- **Badge printing**: Configurable badge with org logo. Audit trail per print (who, when, count)
- **NDA management**: Configurable NDA display on registration form. NDA validity reusable for N days for repeat visitors
- **Temporary check-out**: Visitor can step out and return without full re-checkin
- **Recurring invites**: Up to 90 days ahead; Daily/Weekly/Monthly/Custom patterns
- **Dynamic fields**: Extra configurable fields on invite form (host-side and visitor-side)
- **Reporting**: Summary view (invites by date/office/organizer) + Detailed view (per visitor: check-in/out times, duration, status, parking data)
- **GDPR**: PII stored separately; forgotten after X configurable days (see `Visitor_Document_Storage`)
- **Self Check-in (Kiosk)**: self-service kiosk check-in for invited/walk-in/employee visitors — see the **Self Check-in (Kiosk)** section below
- **Visitor blacklisting**: admins can blacklist visitor profiles — blacklisted visitors cannot be invited, checked in (QR / walk-in / self check-in), or bulk-uploaded; future bookings are cancelled
- **OTP-failure override**: when self-check-in/walk-in OTP fails, front desk can issue a 6-digit override PIN (15-min, single-use) or skip OTP (walk-in)
- **MS Teams notifications**: visitor check-in and approval/reject notifications delivered to the host's MS Teams (via [[modules/ms-teams-integration]])
- **Face-recognition employee check-in (⚠️ POC)**: kiosk face-match check-in for employees — POC phase, **not GA**

## Self Check-in (Kiosk)
A self-service kiosk flow distinct from the 2-step (guard + front-desk) flow — a visitor or
employee checks themselves in at a VMS kiosk device.

- **Three flow types**: **invited** visitor, **walk-in** visitor, and **employee** self check-in (the employee flow is separate from the visitor flows)
- **OTP validation**: configurable per channel (`enableOTPValidationSelfCheckinList` — phone / email)
- **Photo capture**: configurable for Visitor and/or Employee (`isVisitorPhotoCaptureEnabled`)
- **Default visit duration**: 30 minutes (`defaultKioskBookingDurationInMinutes`)
- **Face recognition (⚠️ POC, not GA)**: `faceRecognitionEnabled` replaces the employee kiosk flow with face-match check-in (camera matches against employee records) — POC phase only
- **Statuses**: the lifecycle adds `SELF CHECK-IN` / `SELF CHECK-OUT` (alongside QR / security / reception statuses)
- **Safe Reach hook**: the self-check-in kiosk checkout is the **initiation point for [[modules/safe-reach]]** (the late-departure emergency check-in continuation begins from the VMS kiosk)

## Data Entities Used
- [[entities/visitor-invite]] — owns this entity. Carries a `host` field referencing the inviting **employee** — a real relationship between the employee entity and the visitor flow
- [[entities/visitor-profile]] — owns this entity

_Note: the Self Check-in kiosk has a distinct **employee** check-in path separate from the invited/walk-in visitor flows — relevant to the employee-vs-visitor entity boundary._

## Dependencies on Other Modules
- [[modules/parking-management]] — visitor-tagged parking slots auto-allocated at invite creation; parking module owns the slot and booking infrastructure
- [[modules/guard-app-kiosks]] — security guard uses guard app to scan visitor digipass at gate 1 of 2-step check-in
- [[modules/ms-teams-integration]] — host calendar invites (Outlook/Google via `enableCalendarInvite`) and MS Teams visitor check-in / approval notifications (`isVisitorCheckinMsTeamsNotificationEnabled`, `visitorApprovalMsTeamsNotification`)

## Key Configurations (all office-level, set via SE ticket)
The configs below are a **curated set spanning each feature category**. The full property
reference (~92 properties including operational defaults and edge-case behavior) lives in
[[sources/vms-implementation]].

| Config Key | Default | Description |
|---|---|---|
| `VISITOR_DIGIPASS` | True | Whether invited visitor receives a digipass via email |
| `digipassAutoSend` | False | Auto-send digipass without waiting for visitor acceptance |
| `digipassAutoSendBuffer` | 0 min | Delay in minutes before auto-send |
| `enableNoninteractiveVisitorInvite` | False | Non-interactive invite email (info only, no Accept/Decline) |
| `scheduleInviteEnabled` | — | Enables scheduled invite button (RBAC) |
| `walkInEnabled` | — | Enables walk-in button (RBAC) |
| `Guest_Bulk_Upload` | False | Bulk upload of visitors in invite form (max 100 per upload) |
| `enableCalendarInvite` | False | Add invite to host's Outlook/Google calendar (via ms-teams-integration) |
| `Visitor_Profile_ID` | True | Require visitor to upload identity proof |
| `Visitor_Profile_ID_Document_Upload_Field_Inputs` | False | Configures acceptable ID document types |
| `visitorProfilePhotoUpload` | False | Require visitor to upload profile photo |
| `enableDynamicField` | False | Enable configurable extra fields on invite/walk-in flow |
| `NDA` | True | Show NDA on visitor registration form |
| `Print_Visitor_Badge` | False | Enable badge printing at front desk |
| `Visitor_Parking_Auto_Allocation` | False | Enable visitor parking booking in invite |
| `Visitor_Temp_Check_Out` | — | Enable temporary check-out at front desk |
| `Employee_Approve_WalkInVisitor` | — | Approval workflow for walk-in visitors |
| `otpApprovalFlow` | False | OTP to host in walk-in approval flow |
| `recurringInviteMaxDays` | 90 | Max days ahead for recurring invite (BUID-level) |
| `defaultKioskBookingDurationInMinutes` | 30 min | _Self Check-in_: fixed visit duration applied to each kiosk visitor |
| `isVisitorPhotoCaptureEnabled` | {Visitor, Employee} | _Self Check-in_: whether photo capture is required for Visitor and/or Employee (array-based; does not affect invite/walk-in) |
| `faceRecognitionEnabled` | False | _Self Check-in_ (within `visitorKioskConfigs`): replaces the employee kiosk flow with face-match check-in. ⚠️ POC phase — not GA |
| `enableOTPValidationSelfCheckinList` | `["phoneNo","emailId"]` | _Self Check-in_: enable/disable OTP validation per channel |
| `finalScreenCTATextSelfCheckinFlow` | Kiosk: Submit / Invite: Accept Invite / Walk-in: Accept | _Self Check-in_: rename the final Submit/Accept CTA per flow |
| `isVisitorCheckinMsTeamsNotificationEnabled` | False | _Integration_: send visitor check-in trigger to host (+ office stakeholders) via MS Teams |
| `visitorApprovalMsTeamsNotification` | False | _Integration_: send approval/reject message to host's MS Teams (when approval flow on) |
| `Visitor_Document_Storage` (+ `Visitor_Document_Storage_Duration`) | False / 180 days | _Document storage_: enable timed retention of visitor documents (profile photo / identity proof); duration configurable (default 180 days) |
| `enableBlacklistVisitorProfiles` | False | _Governance_: admins can blacklist visitor profiles (cannot be invited/checked-in/bulk-uploaded); cancels future bookings |
| `enableOtpOverride` | False | _Governance_: OTP-failure fallback — front desk issues a 6-digit override PIN (15-min, single-use) for self check-in; walk-in can skip OTP |
| `entryApprovalFromFrontdesk` | False | _Governance_: front desk can approve/reject visitors arriving via the self check-in flow (privilege `Front_Desk_Approve_Reject_Entry`) |
| `digipass` | Null | _Governance_: multi-value control of digipass visibility per surface — `INVITE_EMAIL` / `INVITE_BADGE` / `SELF_CHECK_OUT_EMAIL` / `SELF_CHECK_OUT_BADGE` |

_Note on digipass: `VISITOR_DIGIPASS` (boolean — controls the invite-acceptance digipass email) and `digipass` (multi-value — controls digipass visibility on badges and self-check-out surfaces) **coexist**; they govern different scopes and are not a contradiction._

## Open Questions
- Who is the module owner team? (Authors include Jovil Nazareth, Kavya Sridharan, Vaishnavi Raghav; Ujjwal Trivedi is the recurring approver — but no single owner team is named.)
- V2 features (desk booking and meeting room booking for visitors) — are these in roadmap or deferred?

## Last Updated
2023-07-11 — _Source: [[sources/vms-prd]] (PRD v1.4), [[sources/vms-implementation]]_

_Module date reflects PRD v1.4 (2023-07-11). Operational configs and recent feature additions
(Self Check-in, MS Teams notifications, blacklisting, OTP override, face-recognition POC) are
tracked in the Implementation doc — a continuously-updated SOP without formal versioning._
