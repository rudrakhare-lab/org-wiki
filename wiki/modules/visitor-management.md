---
type: module
status: active
owner: unknown
depends_on: [parking-management, guard-app-kiosks]
used_by: []
last_updated: 2026-04-28
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
scanning device/app (owned by `guard-app-kiosks`), or the calendar integration for host
calendar invites (MS/Google calendar — handled via `ms-teams-integration` connector).

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
- **GDPR**: PII stored separately; forgotten after X configurable days

## Data Entities Used
- [[entities/visitor-invite]] — owns this entity
- [[entities/visitor-profile]] — owns this entity

## Dependencies on Other Modules
- [[modules/parking-management]] — visitor-tagged parking slots auto-allocated at invite creation; parking module owns the slot and booking infrastructure
- [[modules/guard-app-kiosks]] — security guard uses guard app to scan visitor digipass at gate 1 of 2-step check-in

## Key Configurations (all office-level, set via SE ticket)
| Config Key | Default | Description |
|---|---|---|
| `VISITOR_DIGIPASS` | True | Whether invited visitor receives a digipass via email |
| `digipassAutoSend` | False | Auto-send digipass without waiting for visitor acceptance |
| `digipassAutoSendBuffer` | 0 min | Delay in minutes before auto-send |
| `enableNoninteractiveVisitorInvite` | False | Non-interactive invite email (info only, no Accept/Decline) |
| `scheduleInviteEnabled` | — | Enables scheduled invite button (RBAC) |
| `walkInEnabled` | — | Enables walk-in button (RBAC) |
| `Guest_Bulk_Upload` | False | Bulk upload of visitors in invite form (max 100 per upload) |
| `enableCalendarInvite` | False | Add invite to host's Outlook/Google calendar |
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

## Open Questions
- Who is the module owner team? (Authors include Jovil Nazareth, Kavya Sridharan, Vaishnavi Raghav)
- V2 features (desk booking and meeting room booking for visitors) — are these in roadmap or deferred?
- How does `enableCalendarInvite` interact with `ms-teams-integration`? Same connector?

## Last Updated
2026-04-28 — _Source: [[sources/vms-prd]], [[sources/vms-implementation]]_
