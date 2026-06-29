---
type: release-notes
year: 2023
last_updated: 2026-06-30
source: "—"
---

# Release Notes — 2023

This page is part of the [[history/release-notes]] history layer. Entries are distilled from the PM/sales-facing release-note decks ingested via the SE-runbook crawl. **Recency caveat:** these notes describe behaviour at ship time; consult [[modules/]] and [[configs/]] pages for current authoritative state. Conflicts with curated pages are flagged with ⚠️ inline.

_All 14 decks present in the crawl: 01-2023 through 08-2023, 09&10-2023 (combined), 11-2023 through 15-2023. No gaps._

---

### RN 15-2023

- **User Group Sync via Azure AD (SCIM)** — admins can provision WorkInSync user groups from Azure AD by creating groups there and providing a JSON mapping file; user groups reflect in the WorkInSync UI on each regular SCIM sync. → [[modules/employee-provisioning]]. `ssoDisplayName` n/a — group mapping uploaded to S3 via TO ticket. Properties: n/a. Enablement: TO ticket + S3 upload | PB-33797 ⚠️ This is the 2023 initial ship; by 2024/2025 the SCIM provisioning flow was further enhanced.
- **Visitor Management Experience Enhancers** — three UX fixes: (1) "Cancelled" badge status added to Invite Dashboard so front desk can see invite cancellations clearly; (2) mobile-responsive visitor registration accept-invite flow; (3) default country code on VMS pages now determined by the user's mapped office geography (not hardcoded to +91). → [[modules/visitor-management]]. Enablement: NA (default on)
- **Search Room API Performance — Meeting Rooms** — Search Room API optimized from ~7 s to <200 ms across meeting-room home page, configuration page, kiosk config page, and Outlook Add-in. → [[modules/meeting-rooms]]. Enablement: NA
- **Handling Bookings When Deactivating Meeting Rooms** — admins can now deactivate a meeting room without deleting its existing/future bookings; previously deactivation removed all associated bookings. → [[modules/meeting-rooms]]. Enablement: NA (default on)
- **Download Meeting Room Details** — admins can download a CSV of room details (amenities, capacity, etc.) from the meeting rooms admin page. → [[modules/meeting-rooms]]. Enablement: NA

---

### RN 14-2023

- **Wayfinding — Office-Level Configuration** — wayfinding was previously BU-level; now configurable per office so it only surfaces for offices where it is actually set up, eliminating a misleading experience for offices without a floor plan. → [[modules/digital-wayfinding]]. Enablement: default on; if not present raise TO to enable "Wayfinding office configuration" | PB-34705
- **Configurable Parking Disclaimer Message** — admins can configure a custom parking message (title + body + CTA) shown to employees during desk booking, e.g. fuel reimbursement instructions or parking coordination info. `parkingDisclaimer` (default: False). → [[modules/parking-management]]. Enablement: SE ticket | PB-34698
- **Booking Disclaimer for Desk Bookings** — a separate configurable disclaimer message can be shown on the desk/office booking form. `bookingDisclaimers`. → [[modules/desk-management]]. Enablement: SE ticket with "Title", "Message", "CTA Name"
- **Visitor Management Experience Enhancers (RN14)** — multiple smaller VMS UX improvements (see raw evidence for full list; slide text partially truncated). → [[modules/visitor-management]]. Enablement: NA
- **Cost Centres for Meeting Room Catering** — meeting room organisers can now attach a cost centre to their catering bookings for billing/audit tracking. `Cost_Center_Catering` (default: False). → [[modules/meeting-rooms]]. Enablement: SE ticket

---

### RN 13-2023

- **Checkout Confirmation Prompt for Desk/Remote Bookings** — employees are prompted with a confirmation dialog before checking out of an office or remote booking, preventing accidental check-outs. → [[modules/desk-management]]. Enablement: NA (default on) ⚠️ The 2025 "Separation of Office and Desk Check-in" (RN 05-2025) further evolved check-in/check-out UX — consult [[modules/desk-management]] for current state.
- **Swipe-to-Type / Auto-Complete on Mobile App** — keyboard auto-complete and swipe-typing enabled across all iOS and Android text input flows (reviews, feedback, info submission). → [[modules/mobile-app]]. Enablement: NA (Premium Offering)
- **Outlook Add-in Performance — Edit Meeting with Catering** — Outlook Add-in load time when editing a meeting with a catering order reduced from >20 s to an acceptable duration via API optimization. → [[modules/meeting-rooms]]. Enablement: NA
- **VMS Configurations at Office Level** — visitor management configurations previously applied at BU level can now be set per office, enabling different VMS policies for different offices of the same tenant. → [[modules/visitor-management]]. Enablement: SE ticket
- **VMS User Experience Enhancements** — multiple improvements to visitor flow UX (see raw evidence for full detail; slide text partially truncated). → [[modules/visitor-management]]. Enablement: NA

---

### RN 12-2023

- **Dynamic Fields for Office Booking Form** — the desk/office booking form now has an "Other Details" section powered by dynamic fields; admins can configure text, boolean, numeric, or object fields to collect employee data (e.g., commute mode) surfaced in booking reports. → [[modules/tags-desk-parking]], [[modules/desk-management]]. Properties: `dynamicFields` config via TO ticket. Enablement: TO ticket | PB-34704 ⚠️ Dynamic fields were first introduced for meeting rooms, then VMS (RN 11-2023); this is the desk booking extension. Further extended in 2025.
- **Booking Nudge Notification** — email and mobile push notifications can be sent to employees who have not created an office booking for the upcoming week, nudging them to book. `isBuNudgeNotifEnabled` (default: False). → [[modules/employee-experience]]. Enablement: SE ticket | PB-31888
- **Separate Web and App Check-in Modes** — `officeCheckInModeWeb` and `officeCheckInModeApp` can now be configured independently; values: `directCheckIn` / `digiPass` / `scanQR` / `noCheckIn`. Existing clients retain their previous value as default. → [[modules/desk-management]]. Enablement: SE ticket ⚠️ This is the 2023 origin of the check-in mode split; superseded/extended by RN 05-2025 "Separation of Office and Desk Check-in" and RN 03-2025 "QR Scan: Relaxed Office Check-in Mode" — consult [[modules/desk-management]] for authoritative current values.
- **VMS Reporting Enhancements** — check-in and check-out timestamps now accurately captured across all three VMS check-in/out types (front desk, security guard, self-service) and correctly populated in VMS reports. → [[modules/visitor-management]]. Enablement: NA (Premium Offering)
- **VMS Front Desk Identification Protocol Fix** — after verifying one identification field (photo or ID), subsequent fields are now saved incrementally; front desk no longer has to restart the entire verification flow if they take another action mid-process. → [[modules/visitor-management]]. Enablement: NA (Premium Offering)
- **Team and Organisation/Business Line Management — Unified View** — admins can now manage teams and organisation/business lines from a single consolidated admin page. → [[modules/admin-experience]]. Enablement: NA ⚠️ `admin-experience` is a known module in CLAUDE.md but has no page yet — flagged.

---

### RN 11-2023

- **Real-Time Meal Availability Count** — employees see a live count of remaining meals per meal type (Veg/Non-Veg/Vegan) on the booking form, with colour coding (green = available, red = sold out); first-come-first-served allocation. `showMealCountOnBookingForm` (default: False). → [[modules/meal-management]]. Enablement: SE ticket with meal types + counts | PB-33347 (Premium Offering)
- **Dynamic Fields for VMS — Invited and Walk-in Flows** — dynamic text, boolean, numeric, and data fields can now be added to the visitor management invite and walk-in flows to capture custom visitor data. → [[modules/tags-desk-parking]], [[modules/visitor-management]]. Enablement: TO ticket (Premium Offering) ⚠️ Dynamic fields first shipped for meeting rooms; this is the VMS extension; desk booking extension shipped in RN 12-2023.
- **Optional Visitor Profile Photo** — the VMS system no longer mandates a profile photo for all visitors; admins can configure photo capture as optional to suit their policy. → [[modules/visitor-management]]. Enablement: TO ticket (Not Premium)
- **VMS Persistence Error Fix on New Sites** — "Persistence Error" that appeared on new site setup when attempting to add/search a guest in VMS is resolved via a migration fix. → [[modules/visitor-management]]. Enablement: NA (default on, Not Premium)
- **Kiosk Application Consolidation** — multiple environment-specific kiosk apps consolidated into a single application v2.0; admins link the kiosk to a specific meeting room via a 6-digit PIN from meeting room settings; iOS-first with Android to follow. → [[modules/meeting-rooms]], [[modules/floor-kiosk]]. Enablement: NA (app download from App Store)
- **Manage Premises — Alphabetical Sorting** — office names on the Manage Premises page are now sorted alphabetically to improve discoverability. → [[modules/admin-experience]]. Enablement: NA (Premium Offering) ⚠️ `admin-experience` has no wiki page yet — flagged.

---

### RN 09&10-2023

- **SSO Display Name Customization** — SSO login page can show a custom display name for each BU (e.g. "Mercedes Benz — Bangalore" instead of "mercedesbenz_1") while the backend identifier is unchanged. `ssoDisplayName`. → [[modules/sso]]. Enablement: SE ticket with BU name and desired display name | PB-32357 (Not Premium)
- **Mobile SSO Configuration Enhancements** — `mobileSSOMandatory` behaviour refined: if a user has access to multiple sites and only one has `mobileSSOMandatory` enabled, the "Continue with OTP" option still appears so internal users can log in to other sites; OTP is only hidden when all accessible sites have the property enabled. → [[modules/sso]]. Properties: `mobileSSOMandatory`. Enablement: property behaviour change only — no new enablement step | TB-20488 (Not Premium)
- **"Not Ready" Widget Deprecated** — the "Not Ready" widget on the employee Employees page has been removed from the product. → [[modules/employee-experience]]. Enablement: NA (Not Premium)
- **Check-in / Sign-in Verbiage Standardised** — "Sign-in" replaced with "Check-in" consistently across premises, landing dashboard, and reports to eliminate terminology confusion. → [[modules/employee-experience]]. Enablement: NA (Not Premium)
- **Team Calendar — Streamlined Time Zone Handling** — team calendar now shows a team member's booking details first in the viewer's local timezone, then in the booking member's timezone, enabling accurate cross-timezone planning. → [[modules/employee-experience]]. Enablement: NA (Not Premium)
- **Team Color-Coding on Employee Booking View** — unique colors assigned to each team on the desk booking floor map; a legend shows colors + per-team booking counts per floor. `SHOW_TEAM_COLOR_BOOKING = "ENABLED"`. → [[modules/desk-management]]. Enablement: property-based (Premium Offering)
- **RBAC for Dashboard, Premises, VMS, and Catering Dashboard** — role-based access control extended to Dashboard, Premises, VMS, and Catering Dashboard modules with Read / Edit / Create / Disable permission levels per feature. → [[modules/visitor-management]], [[modules/meal-management]], [[modules/admin-experience]]. Enablement: NA (Not Premium) ⚠️ `admin-experience` has no wiki page yet — flagged.

---

### RN 08-2023

- **Visitor Parking Integration** — hosts can now assign parking slots to visitors when creating invitations; visitors receive parking details in their invite email; receptionist sees parking info on the front desk view. `enableVisitorParking` (default: False). → [[modules/visitor-management]], [[modules/parking-management]]. Enablement: TO ticket
- **ETS — Flexible Office Naming** — ETS sites previously required office names to follow a specific nomenclature; admins can now configure any office name and map it to the ETS-configured name via a TO ticket (actual office name + name on ETS site). → [[modules/ets]]. Enablement: TO ticket with actual office name and ETS-configured name
- **Kiosk — Configurable UI Components** — admins can show or hide individual kiosk UI components (buttons, panels) to control the flow visible to visitors; UI configuration available from the admin kiosk settings. → [[modules/floor-kiosk]], [[modules/meeting-rooms]]. Enablement: UI-level configuration (default on for all components)
- **"Teams" Meeting Option in Room Booking** — option to create a Microsoft Teams meeting alongside a WorkInSync room booking; visible only for Outlook clients. → [[modules/meeting-rooms]], [[modules/ms-teams-integration]]. Enablement: Enabled for all by default (Outlook clients only)
- **Meeting Rooms API — GraphQL Migration** — meeting room APIs migrated to GraphQL, reducing initial load time from >50 s to an acceptable level; catering and participant details no longer pre-loaded at initial render. → [[modules/meeting-rooms]]. Enablement: NA (infrastructure change)
- **RBAC for Meeting Rooms** — role-based access control introduced for meeting rooms with Read / Edit / Create / Disable permission levels per feature/resource. → [[modules/meeting-rooms]]. Enablement: NA (default on)

---

### RN 07-2023

- **Customizable Checkout Message on Front Desk** — the receptionist's checkout confirmation message (text and checklist items in the modal) is now configurable at office level rather than hardcoded. `Reception_Dashboard_Check_Out_Message` (default: False). → [[modules/visitor-management]]. Enablement: TO ticket with desired text
- **Default Office Pre-filled in Visitor Invite Form** — when employees create visitor invitations, the form now pre-populates the employee's default (mapped) office in the office filter, eliminating repetitive selection. → [[modules/visitor-management]]. Enablement: NA (default on)
- **Workspace Manager Role** — a new role below global admin and above office admin; Workspace Managers can access desk management (allocation, utilization, bulk ops), premises, meeting rooms, parking allocation, reports, dashboards, employees & teams (read), and all employee privileges. Available on Stratus sites only (not ETS). → [[modules/desk-management]], [[modules/admin-experience]]. Enablement: SE ticket ⚠️ `admin-experience` has no wiki page yet — flagged.

---

### RN 06-2023

- **Women's Safety Handbook — Mobile App** — the Women's Safety Handbook document (required for safety/compliance) is now accessible within the mobile app for ETS/commute clients. `showWomenSafetyInSideMenu` (default: False for new; enabled by default for applicable commute clients). → [[modules/safe-reach]], [[modules/mobile-app]]. Enablement: SE ticket for non-default sites; Service: Default/emp-exp commons
- **SFTP Check-in Flow Enhancement** — three improvements: (1) SFTP now accepts CSV files in addition to `.xlsx` (resolves Microsoft license requirement); (2) `showFirstCheckInRecord` property controls whether the first or latest check-in time is shown (first is useful for attendance/audit); (3) success/failure notification emails sent to clients on every SFTP file upload, including an error file when records have errors. `showFirstCheckInRecord` (default: False). → [[modules/access-management]]. Enablement: SE ticket for `showFirstCheckInRecord`; CSV support and notifications enabled by default
- **Desk Booking Enhancement — Override Allocated Desk** — employees with an allocated desk can optionally book a different (unallocated) desk if the admin enables this override. → [[modules/desk-management]]. Enablement: SE ticket ⚠️ Desk booking flexibility was further extended in 2025 RN 01-2025 (Flexible Desk Allocation Multi-Team) and RN 05-2025 (Showing Unallocated Desks) — consult [[modules/desk-management]] for current policy.
- **Walk-in Visitor Registration UX Redesign** — the front desk walk-in registration flow received a design refresh for easier receptionist use. → [[modules/visitor-management]]. Enablement: NA (default on)
- **Tenant Logo in Visitor Registration Screens** — the tenant/client logo is now shown on visitor self-registration screens (kiosk or web) for a branded experience. → [[modules/visitor-management]]. Enablement: NA (default on)
- **Visitor Photo Retake** — front desk and security can retake a visitor's profile photo without restarting the entire check-in flow. → [[modules/visitor-management]]. Enablement: NA (default on)
- **Customisable Profile ID Document Types for Visitors** — admins can configure which ID document types (e.g. National Identity Card, Passport, Resident Permit, Work Permit, Social Security Card) are accepted for visitor verification. `Visitor_Profile_ID_Document_Upload_Field_Inputs`. → [[modules/visitor-management]]. Enablement: TO ticket listing which document types to enable
- **Extended Booking History — 30-Day Chunks, 90-Day Range** — employees can view booking history in 30-day increments across a total 90-day date range (up from a shorter window). → [[modules/employee-experience]]. Enablement: NA (default on)

---

### RN 05-2023

- **Customizable Kiosk UI Components** — admins can show or hide individual UI components on the meeting room kiosk to control the kiosk flow visible to visitors. → [[modules/meeting-rooms]], [[modules/floor-kiosk]]. Enablement: TO ticket to enable this; Aditya Dutta contact for queries
- **Visitor Email Revamp — Reduced Email Volume** — visitor invitation emails consolidated and streamlined; fewer emails sent to visitors for a cleaner communication experience. → [[modules/visitor-management]]. Enablement: NA (default on)
- **Printed Visitor Badges** — professional printed visitor badges can be generated for visitors. → [[modules/visitor-management]]. Enablement: TO ticket
- **WiS+ETS — Office Creation with Special Characters** — office names on WiS+ETS combined sites can now include special characters (previously rejected). → [[modules/ets]]. Enablement: NA (default on)
- **MS Teams Chatbot Booking Form Customization** — information fields on the WiS MS Teams chatbot booking form (e.g. `showCabs`, cab-related fields) are now configurable; unwanted fields can be hidden. → [[modules/ms-teams-integration]]. Enablement: SE ticket listing which fields to enable/disable
- **Service Partners — External Employee Access** — external employees (contractors, partners) can be granted Catering Manager, Receptionist, or Visitor Security Guard roles in WorkInSync without being a full internal employee. → [[modules/visitor-management]], [[modules/meal-management]]. Enablement: TO ticket
- **Meeting ID on Meeting Booking Card** — a Meeting ID is now shown on the meeting booking card to help identify catering bookings associated with specific meetings. → [[modules/meeting-rooms]]. Enablement: NA (default on)

---

### RN 04-2023

- **Team Calendar — Fixes and Rename** — Team Calendar now shows the employee's actual preferred shift time (not hardcoded); blank if no preference set. "Max Overlap" renamed to "Popular Day". Day-view navigation bug fixed. → [[modules/employee-experience]], [[modules/desk-management]]. Enablement: NA (default on)
- **Kiosk Provisioning — Secure Link/Delink** — meeting room kiosk setup secured: unique per-room 5-minute OTP replaces a static BU-wide PIN; admins can link/delink from the meeting rooms settings page without developer intervention; security enforced via admin web portal login. → [[modules/meeting-rooms]], [[modules/floor-kiosk]]. Enablement: default on | PB-29734
- **Mobile SSO for Stratus Sites** — SSO login flow extended to Stratus sites (previously limited). `EnableSsoOnMobile` (default: False). `ssoMandatory` (default: False; removes OTP option from SSO login page). → [[modules/sso]]. Enablement: SE ticket; TO assistance may be required
- **Client Logo on WorkInSync Pages** — the client/company logo is displayed prominently on WorkInSync web pages. → [[modules/employee-experience]]. Enablement: NA (default on)
- **Multi-Office Visitor Management** — receptionist dashboard now supports managing visitors across multiple offices in a single view; office filter allows switching between offices. → [[modules/visitor-management]]. Enablement: NA (default on) ⚠️ This was an early multi-office VMS capability; VMS office-level configurations were further extended in RN 13-2023.
- **Catering Order Progress Email** — employees are notified via email about the progress/status of their catering order. → [[modules/meal-management]]. Enablement: SE team enable (Please reach out to SE team)

---

### RN 03-2023

- **Delegation** — employees can delegate WorkInSync actions (meeting room booking, work planner, employee web) to colleagues; delegatee receives an email and can switch to the delegator's profile to act on their behalf. `isDelegationEnabled` (default: False). → [[modules/delegation]]. Enablement: SE ticket | PB-16556 ⚠️ 2023 initial ship covering Meeting Rooms, Work Planner, Employee Web. By RN 05-2025 (Admin View for Delegation) admin visibility was added — consult [[modules/delegation]] for current scope.
- **Kiosk — Configurable Background Image and Overlay** — admins can upload a custom background image for the meeting room kiosk; can choose between a state-color overlay (green/yellow/red) or no overlay with a colored border only. → [[modules/meeting-rooms]], [[modules/floor-kiosk]]. Properties: none (UI-level setting). Enablement: default on for all
- **Visitor Additional Information Field** — receptionists can enter free-text additional information (badge number, parking slot, special requests) against each visitor on the front desk dashboard; editable until visitor checks out; captured in admin reports. `Visitor_Details_Text_Box` (default: False). → [[modules/visitor-management]]. Enablement: TO ticket
- **Bulk Upload of Visitors** — admins/receptionists can upload multiple visitors at once via bulk upload (see raw evidence for full enablement flow). → [[modules/visitor-management]]. Enablement: TO ticket

---

### RN 02-2023

- **ETS Shift-Pairing for WiS-ETS Clients** — shift-pairing (linking a logout shift to a specific login shift so transport is only bookable for matched pairs) extended from Mobility-only to WiS-ETS clients. `FEATURE_SCHEDULING_WITH_SHIFT_PAIR_ENABLED` (default: False). → [[modules/ets]]. Enablement: SE ticket | PB-28493 ⚠️ Shift-pairing was previously a Mobility-only feature; this is the 2023 WiS-ETS extension.
- **Host Notifications for Visitor Check-in** — email and SMS notifications sent to the host when: (1) an invited visitor scans their DigiPass at the security gate; (2) a visitor (invited or walk-in) is marked "Allowed Entry" by front desk. → [[modules/visitor-management]]. Enablement: NA (default on); per-host notification preferences planned for roadmap
- **VMS — Time Zone Awareness** — visitor management timestamps and invite flows are now correctly time-zone sensitive for global clients. → [[modules/visitor-management]]. Enablement: NA (default on)
- **Meeting Room Catering — Availability Windows** — caterers can configure availability windows (time slots) for specific menu items (e.g. pizza available only 12pm–3:30pm); items are hidden outside their window. → [[modules/meal-management]]. Enablement: SE team enable
- **Meeting Room Catering — Booking Deadlines** — caterers can set per-item booking deadlines so employees must order in advance; items unavailable past their deadline. → [[modules/meal-management]]. Enablement: SE team enable
- **Catering Dashboard** — a dedicated dashboard for caterers to manage and view all catering orders associated with meeting room bookings. → [[modules/meal-management]]. Enablement: SE team enable

---

### RN 01-2023

- **Contextual Error Messages** — error messages across the system improved with dynamic variables and contextual wording to help users understand what happened and why, rather than generic messages. → [[modules/employee-experience]]. Enablement: NA (default on)
- **Privacy Settings on Mobile App** — employees can now update their privacy settings (visibility to team, booking preferences) from the mobile app, not just the web portal. → [[modules/mobile-app]]. Enablement: NA (default on)
- **Parking Slot Allocation — Teams / Employees / Block / Open** — admins can assign parking slots to specific teams or individual employees, mark slots as open, or block them; assignments can be time-bounded (start and end time for specific days). Note: Tags not handled in this version; waitlist allows joining any queue but actual allotment is team-aware. → [[modules/parking-management]]. Enablement: (enablement in source deck — see raw evidence) ⚠️ This is the 2023 initial parking allocation ship; superseded by RN 03-2025 (RBAC for Parking Booking) and RN 04-2025 (Parking Allocation Report) — consult [[modules/parking-management]] for current state.

---

## Linked Raw Evidence

| RN | raw_path |
|----|---------|
| RN 01-2023 | `raw/se-runbook/crawl/files/11M8_tH8Obv1NVkRuTIkMiquu3LWH11Id4B9Q7SU8-1g.pptx` |
| RN 02-2023 | `raw/se-runbook/crawl/files/1YtfCUbdOPYmpuPmDFgIkwBiPykFbnxUnoEwM09poHIE.pptx` |
| RN 03-2023 | `raw/se-runbook/crawl/files/1SPyK351rtiuSAgn6Gjb1-smziTqRmxeQqcUFd4ULP7M.pptx` |
| RN 04-2023 | `raw/se-runbook/crawl/files/1j91xsqIA76QvA9cYsbq2E6lfQRjxHHGMr6XpI6qh2WQ.pptx` |
| RN 05-2023 | `raw/se-runbook/crawl/files/1IMb8dD6fbQHgClJYUToZj0yQ7rAAsZ1jYNNh80Tx0mU.pptx` |
| RN 06-2023 | `raw/se-runbook/crawl/files/1CcHEQrqb4Mjxo2b_GrEd8KfRYV5BUUom95wU51dVAiM.pptx` |
| RN 07-2023 | `raw/se-runbook/crawl/files/1O19IA_BzEBUuHYPRzFL7rwkRlztiZPowo9yTYhCI9_o.pptx` |
| RN 08-2023 | `raw/se-runbook/crawl/files/16EJ6TxgBDQbzsjtohaXzOq6Pm8KbdAgcdkBcjw1h6xU.pptx` |
| RN 09&10-2023 | `raw/se-runbook/crawl/files/1qk8tiw-49BiUliL5zYyoSUGf8pZUtZQHqbHylgJpaBI.pptx` |
| RN 11-2023 | `raw/se-runbook/crawl/files/1GVkUDYpPYNv08oeH7SYTxi-_DknumMixSTIMRAUD_OI.pptx` |
| RN 12-2023 | `raw/se-runbook/crawl/files/1azH69W2yHh5WxjVkvV5NNgY0U7kNHrMtQ56hEwcpkfo.pptx` |
| RN 13-2023 | `raw/se-runbook/crawl/files/1dRxsdVU60prKJjhbpPQRrbsvkC4l3rtapKL-IPc6QBk.pptx` |
| RN 14-2023 | `raw/se-runbook/crawl/files/1TZI81E4Iev1C6uO8fxI4IOLLp3j3Km5Rupk6PJ-93GM.pptx` |
| RN 15-2023 | `raw/se-runbook/crawl/files/1GD82jI_XnMHdDVA6KRNCGOwSPgDIIc5VyXwKLC5hHj4.pptx` |
