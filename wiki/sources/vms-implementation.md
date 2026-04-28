---
type: source
raw_path: raw/modules/visitor-management/Copy of VMS Implementation Doc.docx
ingested: 2026-04-28
doc_type: spec
---

# VMS Implementation Doc

## Source Title
VMS Implementation Doc (discovery + setup + config reference)

## Date
Unknown (regularly updated; references 2023 sprint scope)

## Type
spec (implementation SOP + configuration reference)

## Key Takeaways
- Serves as the implementation guide for sales/SE teams onboarding a client to VMS.
- **Discovery questions**: covers current process, visitor volume/types, integrations, security requirements, notifications, PII handling.
- **Setup steps**: (1) Move client to latest deployment; (2) Upload VMS email templates to DB via SE ticket; (3) Enable VMS tabs and configs per office.
- **All VMS configs are office-level** (not BUID-level) — different offices of the same org can have different VMS configs.
- **Config raised via SE ticket** (not self-serve admin UI for most properties).

### Key Config Properties (full list in source doc)
| Property | Default | What it does |
|---|---|---|
| `VISITOR_DIGIPASS` | True | Digipass emailed to invited visitor |
| `digipassAutoSend` | False | Auto-send digipass without waiting for visitor acceptance |
| `digipassAutoSendBuffer` | 0 min | Delay before auto-send |
| `enableNoninteractiveVisitorInvite` | False | Generic info email, no Accept/Decline buttons |
| `scheduleInviteEnabled` | — | Scheduled invite button on front desk page (RBAC) |
| `walkInEnabled` | — | Walk-in button on front desk page (RBAC) |
| `Guest_Bulk_Upload` | False | Bulk upload of visitors in invite form |
| `enableCalendarInvite` | False | Adds invite to host calendar (Outlook/Google) |
| `Visitor_Profile_ID` | True | Requires visitor to upload identity proof |
| `Visitor_Profile_ID_Document_Upload_Field_Inputs` | False | Configures which ID document types to accept |
| `visitorProfilePhotoUpload` | False | Requires visitor to upload profile photo |
| `enableDynamicField` | False | Enables extra dynamic fields on invite/walk-in flow |
| `NDA` | True | NDA shown on visitor registration form |
| `Print_Visitor_Badge` | False | Badge printing at front desk |
| `identification` | True | ID verification tab on front desk dashboard |
| `Visitor_Parking_Auto_Allocation` | False | Enables parking booking in visitor invite |
| `Visitor_Temp_Check_Out` | — | Enables temporary check-out at front desk |
| `Employee_Approve_WalkInVisitor` | — | Approval workflow for walk-in visitor |
| `otpApprovalFlow` | False | OTP to host in walk-in workflow |
| `recurringInviteMaxDays` | 90 days | Max days for recurring invite pattern |
| `allowBookingsForOthers` | False | Allow employee to book invite for someone else |

## Entities Mentioned
- [[entities/visitor-invite]]

## Modules Mentioned
- [[modules/visitor-management]] (primary)

## Decisions Extracted
- None new — confirms existing decisions.

## Wiki Pages Created/Updated
- Updated: [[modules/visitor-management]] (configs section)

_Source: [[sources/vms-implementation]]_
