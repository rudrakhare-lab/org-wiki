---
type: release-notes
year: 2022
last_updated: 2026-06-30
source: "—"
---

# Release Notes — 2022

This page is part of the [[history/release-notes]] history layer. Entries are distilled from the PM/sales-facing release-note decks ingested via the SE-runbook crawl. **Recency caveat:** these notes describe behaviour at ship time; consult [[modules/]] and [[configs/]] pages for current authoritative state. Conflicts with curated pages are flagged with ⚠️ inline.

_This page covers the **earliest** release notes, before the NN-YYYY numbering scheme began in 2023. Two notes are explicitly dated 2022 in their titles ("Nov (2022)", "Dec (2022)"). The undated monthly notes (Apr–Oct) are grouped here as **2022 by inference** from the pre-numbering scheme and the sequential context — year is not explicitly stated in those source documents. Undated named/feature notes are listed separately at the bottom of the page. One entry ("tabs Setup URLs Demo Script Release Notes Repo…") was identified as a repo/navigation index tab and **skipped** (see note at end of page)._

---

## Dated 2022

### RN Dec-2022

_Source: `raw/se-runbook/crawl/files/1HS15LPBKqTjJC-qvnd6PLusD7OCAYqENSAt9j2Z0Z_w.pptx`_

- **Mobile App: No-Internet Handling Overhaul** — technical architecture redesign for offline/low-connectivity scenarios on mobile; now checks OS-level network state (not just TCP/IP) to handle edge cases like "connected to Wi-Fi but not authenticated". Properties: none (infrastructure change). Enablement: N/A → [[modules/mobile-app]]

- **Team Calendar & Booking Form Parity** — Team Calendar now honours future-booking date restrictions (e.g. 30-day window) previously enforced only by the booking form; users can no longer create past-date bookings via Team Calendar. Enablement: N/A → [[modules/employee-experience]], [[modules/desk-management]]

- **Direct-Open Office Booking Form (Office-Only Clients)** — for clients with only one booking type enabled (office only or remote only), the booking form opens directly without an intermediate pop-up selection step; reduces a redundant click. Enablement: N/A (auto-configured by client profile) → [[modules/employee-experience]]

---

### RN Nov-2022

_Source: `raw/se-runbook/crawl/files/13du69PZ2aXC4175OBTU9a_MDD4nCLmExrqdamapaQXc.pptx`_

- **Configurable Check-in Modes (Mobile)** — property-driven configuration supporting multiple check-in modes on the mobile app: ScanQR only, DigiPass only, Simple Check-in (direct), Geofence on, Geofence off, or None (no check-in button). Properties: `officeCheckInMode` (`directCheckIn` / `digiPass` / `scanQR` / `noCheckIn`) · Service: `emp-exp`. Enablement: SE ticket → [[modules/employee-experience]], [[modules/mobile-app]] ⚠️ Superseded/extended by RN 12-2023 (`officeCheckInModeWeb`/`officeCheckInModeApp` split) and further refined in RN 03-2025 and RN 05-2025.

- **Employee Deactivation: Resource Cleanup + Notifications** — on deactivating an employee, all upcoming bookings are cancelled, desk allocations are released (status → unallocated), parking and meal bookings freed, meeting room bookings released, manager receives email notification, and Audit is updated. Properties: none (automatic). Enablement: N/A | PB-26803 → [[modules/employee-experience]], [[modules/desk-management]], [[modules/meeting-rooms]], [[modules/parking-management]]

- **Filter Cancelled Bookings Toggle** — user-facing toggle to show/hide cancelled bookings on web and mobile; if property not enabled, cancelled bookings display by default (legacy behaviour). Properties: `showBookingFilter` · Default: `False` · Service: `emp-exp`. Enablement: SE ticket | PB-26997 → [[modules/employee-experience]]

- **GDPR Compliance Pop-up on Mobile App** — GDPR consent pop-up (previously web-only) now surfaces on mobile before all order-of-challenges; appears once per user. Properties: `isGDPRCookiePolicyEnabled` · Default: `False` (enabled by default for EU clients). Enablement: property flag → [[modules/mobile-app]]

- **Parking Floor Plan** — visual floor-plan view for parking slots (alongside existing grid/auto-allocation); employees can book a slot by its location on the floor plan; supports car, bike, stacked, and tagged (e.g. PWD) slots. Waitlist not supported in this version. Enablement: SE ticket (client provides DWG file); same process as desk floor plan → [[modules/parking-management]]

- **SSO on Mobile App** — SSO authentication flow on MoveInSync mobile app; on launch, if SSO is enabled, user is redirected to a mobile-responsive SSO web page; falls back to OTP if SSO not enabled. Properties: `EnableSsoOnMobile` · Default: `False`; `AllowOtpBasedLoginWithSso` · Default: `False`. Enablement: SE ticket | PB-25542 → [[modules/sso]], [[modules/mobile-app]] ⚠️ Extended in RN 04-2023 (Mobile SSO for Stratus) and RN 09&10-2023 (SSO configuration enhancements).

- **Meal Consumption Workflow (Vendor Billing on Actuals)** — workflow enabling enterprises to bill cafeteria vendors on actual consumption rather than estimates; designed for post-pandemic variable headcount. Enablement: configuration-based (details in source deck) → [[modules/meal-management]]

---

## Monthly Notes (2022, inferred)

_Year not explicitly stated in these source documents. Grouped here as 2022 by inference from the pre-numbering scheme and sequential month ordering in the crawl._

---

### RN Oct.2 _(undated — 2022 inferred)_

_Source: `raw/se-runbook/crawl/files/1qTmpgLXrpCDFynrEOoKdi_6rEQBqB5tSAL4RLkWJWMw.pptx`_

- **Welcome to WorkInSync Email (Employees)** — upon completing onboarding, employees now receive a welcome email introducing WorkInSync features (previously only admins received it). Enablement: N/A (auto-sent on onboarding completion) → [[modules/employee-experience]], [[modules/employee-provisioning]]

- **Auto-Onboard Employees** — property-based configuration that automatically marks all employees in the system as "Onboarded" state; health risk and preferences values unaffected. Enablement: property-based (details in source deck) → [[modules/employee-provisioning]]

- **Bookings on Non-Working Days / Weekly Offs** — allows single-day bookings on weekly-offs/non-working days; recurring bookings on such days must be created manually. Properties: `enableWeeklyOffBookings` · Default: `False`. Enablement: SE ticket. Note: available on mobile with Oct.2, web with Nov (2022) → [[modules/desk-management]], [[modules/employee-experience]] ⚠️ Extended in RN 04-2025 (Weekly Off/Holiday Booking on Work Planner).

- **WFH Renamed to "Remote"** — "Work From Home" label replaced with "Remote" across the WorkInSync system. Emails and mobile notifications not yet updated (planned Dec 2022). Enablement: N/A → [[modules/employee-experience]]

- **Separate Parking Days-in-Advance Window** — independent configuration for how many days in advance a parking booking can be made, decoupled from office/meal booking windows; info banner and icon updated to reflect the parking-specific window. Properties: `parkingScheduleCutoff`. Enablement: SE ticket → [[modules/parking-management]]

---

### RN Oct.1 _(undated — 2022 inferred)_

_Source: `raw/se-runbook/crawl/files/18E9PEhXNQs7gIf8MgdK_FHueqObRmrHP9wQjrhipV84.pptx`_

- **Meal Booking Mandatory** — meal selection becomes a mandatory field in the booking form; employees must choose an option (including "Not Required") for every meal type in their booking period. Properties: `mealPlanningMandatory` · Default: `False`; also requires `mealPlanningEnabled = true`. Enablement: property flag → [[modules/meal-management]]

- **Shuttle Demand Generation** — property-based configuration replacing the cab icon with a shuttle icon in the booking form for clients wanting shuttle demand data rather than cab bookings; helps measure shuttle demand. Enablement: SE ticket → [[modules/ets]]

- **Auto-Population of Booking Form (Web)** — when user preferences are unset or inapplicable, the booking form pre-fills from past booking history; falls back to next available shift; falls back to empty if no shifts available. Properties: `autoPopulateBookingForm` · Default: `True`. Note: mobile rollout ~15 November. Enablement: default-on → [[modules/employee-experience]]

- **Mobile Accessibility — Tracking & Trip Feedback** — screen-reader compliance (VoiceOver on iOS, TalkBack on Android) for Tracking and Trip Feedback workflows; enabled by default → [[modules/mobile-app]]

- **Parking Booking Waitlist** — employees can join a waitlist when parking slots are full; slots allocated on first-come-first-served basis as cancellations occur; real-time waitlist position shown. Properties: `enableWaitlistBooking`, `enableJoinAllWaitlist`. Enablement: SE ticket → [[modules/parking-management]] ⚠️ Waitlist expiry feature added in RN 01-2026.

- **Parking Booking Reminder Notification** — configurable notification + email sent X minutes before parking booking start time; message is BU-configurable. Properties: `triggerNotificationReminderTime`. Enablement: SE ticket → [[modules/parking-management]]

- **Walk-in Visitor Entry (Receptionist)** — front desk can enter walk-in visitors via OTP verification (email/phone); capture visitor photo, ID, personal belongings; host email lookup for OTP share. Enablement: SE ticket → [[modules/visitor-management]] ⚠️ Walk-in visitor workflow significantly extended in RN 03&04-2024 (Host Approval Workflow) and RN 05-2024 (Self Check-in Kiosk).

---

### RN Aug.1 _(undated — 2022 inferred)_

_Source: `raw/se-runbook/crawl/files/1M5dCSilxkUbVF9FLh2sqP7BTkvxaPt8AMhNdzhOsSlY.pptx`_

- **Office Address Display During Booking** — search bar and scrollable office list showing address for each office, helping employees in multi-office cities select the correct location; search by office name only (case-insensitive). Properties: `showOfficeInfoOnBookingForm` · Default: `False` · Service: Employee Experience. Enablement: SE ticket (with office names & addresses) → [[modules/employee-experience]]

- **Search by Desk Number on Floor Plan** — property-based configuration enabling desk search in the floor plan search bar; configurable to search colleagues only, desks only, or both. Properties: `showSeatSearchOnSeatBooking`, `showEmployeeSearchOnSeatBooking` · Default: `True`. Enablement: SE ticket → [[modules/desk-management]]

- **Employee Profile Audit History (Bookings + Profile)** — new "Audit History" section in side nav with two sub-sections: Employee Bookings and Employee Profile; searchable by employee name and date range for a customisable period; available on web only (Stratus + ETS). Enablement: released to all customers by default → [[modules/employee-experience]]

- **WiS MS Teams App — Side Navigation** — static side-nav integrated into the WiS MS Teams App giving access to all WorkInSync modules enabled for the organisation (Meeting Rooms, VMS, Desk Management, etc.); role-based feature visibility; web only, not mobile. Enablement: released to all WiS-property-enabled customers → [[modules/ms-teams-integration]] ⚠️ Superseded/extended repeatedly in subsequent years (VMS on Outlook Add-In RN 02-2024, client-configurable reminder templates RN 14-2024, etc.).

---

### RN Jul.1 _(undated — 2022 inferred)_

_Source: `raw/se-runbook/crawl/files/1Ico0VbvqY5OVtUL29fRVOfiajVNOg0O7Npv2rLZSZ2w.pptx`_

- **Meeting Rooms Multi-Timezone Support** — meetings now load in the user's profile office timezone by default; user can change timezone and all meetings update accordingly; Outlook/GSuite meetings honour the user's domain timezone. Limitation: honored for web and kiosk, not meeting-rooms mobile app at this time. Enablement: released to all customers → [[modules/meeting-rooms]]

- **Meeting Rooms Booking Form Redesign** — UX simplification: multi-date selection removed for single bookings; time picker optimised for backwards-scroll; office selection removed from form. Enablement: released to all customers → [[modules/meeting-rooms]]

- **Secure Cancel/End Meeting via Kiosk** — admin can cancel/end meetings using a static PIN; organisers/attendees can end via OTP sent by email (SMS coming later). Properties: `CANCEL_EVENT_PIN_VERIFICATION_ENABLE` (admin PIN), `EnableMRMailCancel` (send mail to organizer/attendees). Enablement: property flags → [[modules/meeting-rooms]], [[modules/floor-kiosk]]

- **Employee Check-out Location Capture** — check-out time and geo-location captured; admins can see geo-code violations (configurable radius, default 800m) in Booking Details Report; users informed at check-out if violation detected. Enablement: SE ticket (Report + geo-violation property) → [[modules/employee-experience]], [[modules/desk-management]]

---

### RN Jun.2 _(undated — 2022 inferred)_

_Source: `raw/se-runbook/crawl/files/1vRSkJlP93fgMkCbTqZEnKoJRgOc_wg2nUDV7Ikh8vEc.pptx`_

- **Dynamic Policy Engine for Parking (Tag-Based Slot Allocation)** — dynamic tag system allowing admins to assign tags to parking slots and employees via bulk upload; employees can only book slots mapped to their tag(s); hotslots (untagged slots) visible to all or restricted to tagged employees only. Limitations: two different values of the same tag cannot map to the same slot or employee. Enablement: not configuration-based (one-time setup) → [[modules/parking-management]], [[modules/tags-desk-parking]] ⚠️ RBAC for Parking Booking added in RN 03-2025.

- **Real-Time Integration with Third-Party Vendors via APIs** — booking-detail export API enabling client systems (boom barriers, access cards) to consume WorkInSync booking data (office, parking, meal) filtered by employee ID/email/phone or time range. Note: does not create bookings or check-in/out. Enablement: one-time setup with client (not property-based) → [[modules/third-party]]

- **QR Codes for Parking Slots** — scannable QR codes at each parking slot enabling: check-in to parking, verification that employee is in the correct slot, or walk-in parking booking creation. Enablement: SE ticket → [[modules/parking-management]]

---

### RN Jun.1 _(undated — 2022 inferred)_

_Source: `raw/se-runbook/crawl/files/1Pltey8615EGIv8KOnIrWJKgrPWM7yXBQg_dioYBC098.pptx`_

- **Customisable Email Sender IDs** — configurable sender email address for all WorkInSync emails (e.g. `admin@clientco.com` instead of `noreply@workinsync.io`); falls back to Stratus default (`noreply@workinsync.io`) or non-Stratus default (`transport@moveinsync.com`) if no custom email configured. Enablement: SE ticket | PB-22330 → [[modules/employee-experience]]

- **Audit History of Employee Profile** — UI for admin/WIS-internal users to view history of changes to employee profiles; searchable by name + date range; downloadable report. Enablement: released to all customers → [[modules/employee-experience]]

- **Team Seat Highlighting on Floor Plan** — team-assigned desks highlighted in yellow with 3-second blinking animation and tooltip on floor plan load; nudges employees to book their team seats over hot seats. Enablement: by default for all applicable clients → [[modules/desk-management]]

- **Office Admin Role — Configuration Management** — global admins can assign users to Office Admin role for specific offices; office admins can change office-level and meeting-room configurations for their assigned offices; confirmation email sent to all office admins + global admins on config change. Limitations: office admin can only manage specific offices, not "All offices"; meeting room config changes do not specify which config changed in email. Enablement: requires Office Admin role creation per BU → [[modules/admin-experience]] ⚠️ `admin-experience` module referenced in CLAUDE.md but no wiki page exists — not auto-created per Rule 6.

- **Max Bookings per Week/Month Applies to Recurring + Multi-Day** — the existing max-bookings-per-period rule now also applies to recurring and multi-day bookings, not just single-day. Limitation: Stratus only; global level only in this version. Enablement: configurations page (booking policy section) → [[modules/desk-management]]

- **Restrict Manager from Employee Create/Edit** — "Create Employee" and "Edit" employee details UI options hidden for Team Manager and Project Manager roles; hover tooltip explains lack of authorization. Enablement: default-on for all applicable clients → [[modules/employee-provisioning]], [[modules/admin-experience]] ⚠️ `admin-experience` module referenced but no wiki page exists.

---

### RN Apr.1 & May.1 _(undated — 2022 inferred)_

_Source: `raw/se-runbook/crawl/files/1sZ3Wp2C1avQNW5FfJ5XuxOxhLvCczEGMZYnkwOm5_N4.pptx`_

- **Audit History of Employee Profile** — first ship of admin UI for viewing history of employee profile changes; searchable by name and date range; downloadable; covers name, email, ID, phone, gender, office, team, reporting manager. Enablement: released to all customers (no property needed) → [[modules/employee-experience]] ⚠️ Expanded in Aug.1 to include Employee Bookings alongside Employee Profile.

- **Meeting Rooms on Mobile App** — employees can search available rooms, book now or for future use, and view all room bookings from the mobile app. Properties: `showMeetingRoomOnApp` (enables "Book Room Now" on FAB and "Meeting Room" in hamburger menu). Limitations: no filters or cross-office navigation in this version. Enablement: SE ticket → [[modules/meeting-rooms]], [[modules/mobile-app]]

- **Workplace Insights Dashboard** — dashboard with key work-pattern insights for hybrid workplace decisions: Employee Office Visits, Workday Preferences, Office Space Usage (3 of 6 planned sections). Enablement: TO ticket → [[modules/admin-experience]] ⚠️ `admin-experience` module referenced but no wiki page exists.

- **App Lock-Screen** — native OS screen lock integrated into MoveInSync app; protects sensitive personal data stored in the app; configurable per BU. Properties: `enableAppLock` · Default: `False`. Enablement: SE ticket → [[modules/mobile-app]]

- **Admin Configuration UI (Empowering Admins)** — global admins can now manage Global, Office-level, and Meeting Room configurations from the Configurations tab in the UI. Limitation: Stratus sites only by default. Enablement: Stratus sites default-on → [[modules/admin-experience]] ⚠️ `admin-experience` module referenced but no wiki page exists.

- **Disable Overlapping Bookings** — prevents simultaneous WFO and WFH/Remote bookings with overlapping shift times. Properties: `disableWfhWfoOverlapping` · Default: `False`. Enablement: SE ticket → [[modules/desk-management]], [[modules/employee-experience]]

- **Employee Reactivation from UI** — admins can reactivate deactivated employees directly from the UI (previously required backend CS intervention). Limitation: reactivation details overwrite employee details at deactivation time. Enablement: UI feature → [[modules/employee-provisioning]]

---

## Named / Feature Notes (undated)

_These notes have no month or year in their titles. Based on feature context and ordering in the crawl, they are most likely pre-2023 (consistent with the 2022 pre-numbering era) but the year is not asserted._

---

### N-Level Hierarchy — Desk Allocation _(undated)_

_Source: `raw/se-runbook/crawl/files/1xHVOKaUMAe41U2jAJOkeQxar_ejOeZUVJuHPc1ckc7g.pptx`_

- **N-Level Hierarchy Desk Allocation** — desk allocation system upgraded from fixed 2-level (Organization + Business Line) to arbitrary-depth hierarchy; admin can assign desks to any level via "Assign to Hierarchy" modal with full path display and hierarchy-level disambiguation; applies to Desk Allocation (list view, floor view), Home Dashboard, Premises, and Employees pages; hierarchy legends on floor view. Properties (consul): `isBlSubblBuid=true`, Guard App `groupTypes` and `FLOOR_VIEW` updated. Sample ticket: SE-38594. Enablement: SE ticket → [[modules/desk-management]], [[modules/employee-experience]] ⚠️ N-Level Hierarchy further extended in RN 08-2024 (N-Level Desk Allocation Hierarchy, PB-40525) and RN 02-2024 (Team Calendar Custom Hierarchy Views).

- **Employee DataSync Bulk Upload Template — Hierarchy Column** — bulk upload template updated for both ETS and Stratus sites; new `Hierarchy` column accepts pipe-separated (`|`) hierarchy path (e.g. `IFS|India IT|IT Procurement and Support`); existing 2-level `Organization` / `Business Line` columns still supported on ETS for backwards compatibility. Enablement: SE ticket → [[modules/employee-provisioning]]

---

### Parking — Vehicle Creation _(undated)_

_Source: `raw/se-runbook/crawl/files/1Vj6Ledb1l_MqjQ-5rt5X7AtHZ0xlebdOZhPFB8STI3I.pptx`_

- **Vehicle Creation for Parking** — users can now save vehicle profiles (name, registration number, vehicle build type for 4-wheelers: Hatchback/Sedan/SUV; 2-wheelers supported) and select a saved vehicle during parking booking; slot availability is filtered by vehicle build type mapped to slot types by admin. Multiple vehicles per user supported; vehicle creation accessible from booking form or user profile. RBAC-controlled: role determines read/create/edit/delete access. Properties: `vehicleCreationDuringParkingFor` (`["CAR","BIKE"]`, `["CAR"]`, `["BIKE"]`, or `[]`) | Web RBAC: `vehicle_creation_for_parking` | Mobile: `allowEditDeleteForVehicleCreation`. Enablement: SE ticket | PB-35751 → [[modules/parking-management]] ⚠️ Prevent editing of vehicle info (RBAC restriction) re-shipped in RN 10-2024 (PB-42733) as a separate feature reinforcing edit/delete control.

---

### Recurring Bookings _(undated)_

_Source: `raw/se-runbook/crawl/files/1yVLbX83WWvjWbCjqcrRq4drtQjbp1DITSbCewfUYJ4g.docx`_

- **Recurring Bookings (Work-from-Office)** — employees can create recurring WFO bookings by selecting an end date; repetition by weekday or number of days; failed bookings listed in confirmation pop-up; individual bookings within a recurring set can be cancelled or the entire set cancelled. Properties: `recurrenceBookingEnabled = TRUE`. Enablement: SE ticket → [[modules/desk-management]], [[modules/employee-experience]] ⚠️ Recurring booking for Work Planner added in RN 14-2025.

- **Meal Booking Time Windows** — configurable availability windows for each meal type (e.g. breakfast 7–10 AM); only meal options overlapping with the booking time slot are selectable. Enablement: TO ticket (with meal types and timings) → [[modules/meal-management]]

- **Booking Cut-Off by Shift** — booking cut-off time configurable per shift (e.g. no bookings after 10 PM for night shift). Enablement: TO ticket → [[modules/desk-management]]

---

### Indemnification Form _(undated)_

_Source: `raw/se-runbook/crawl/files/1lx6Qa0LJDpDVZ_sADfwnCVhoQENq0yL3CL9HY-4PDsA.docx`_

- **Indemnification Form for Women's Transport** — when a female employee cancels a shift that falls within a configured late-night transport window, she receives an indemnification form to document self-travel plans; the form opens in a new tab, captures travel details, and submissions are persisted in a report for the transport team. The form link is also accessible from the employee profile. Organisation is indemnified for 24 hours from the date of self-travel. Properties: `FEATURE_INDEMNIFICATION_AGREEMENT_ENABLE` (feature toggle), `INDEMNITEE_COMPANY` (text field), `WOMEN_EMPLOYEE_SIGN_IN_ALERT_START_24_HOUR_FORMAT`, `WOMEN_EMPLOYEE_SIGN_IN_ALERT_STOP_24_HOUR_FORMAT`, `INDEMNIFICATION_EMAIL_CC_RECIPIENTS`, `INDEMNIFICATION_EMAIL_ENABLED`, `INDEMNIFICATION_EMAIL_SIGNATURE_TEAM_NAME`. Enablement: SE ticket → [[modules/safe-reach]], [[modules/ets]] ⚠️ Indemnification extended in RN 11-2024 (Indemnification Support for WiS-ETS Sites, PB-42901) and further referenced in RN 01-2026 context — this is the original ship. The ETS extension confirms the feature spans both [[modules/safe-reach]] and [[modules/ets]].

---

### Seat Assignment — New Features _(undated)_

_Source: `raw/se-runbook/crawl/files/1RckM3pU5zf-vt7XWe7dTNOy9JqjQmczb.pptx`_

- **Employee Preferences (Booking Form)** — employees can save check-in/check-out, transport, meals, and seat preferences; preferences auto-populate the booking form; preferences can be updated inline. Enablement: released to all → [[modules/employee-experience]]

- **Seat Assignment on Floor Plan View** — admin can select multiple seats on the floor plan and assign them as hot seats, blocked, or allocated to teams/employees (previously grid-only). Available out of the box for all floors. Enablement: default-on → [[modules/desk-management]]

- **Meal Booking from Mobile App** — employees can book meals (Breakfast, Lunch, etc.; Veg/Non-Veg/Vegan/Gluten-free etc.) from the mobile app during booking creation; meal data downloadable for vendor reporting. Enablement: TO ticket → [[modules/meal-management]]

- **Desk Utilisation Dashboard** — admin dashboard tracking seat allocation status (weekly/monthly), teams with max/min seats, utilisation of assigned seats, hot-seat booking trends. Accessible per office and per floor. Enablement: released to all → [[modules/desk-management]]

- **Seat Assignment via File Upload** — bulk seat assignment via file upload (for high-volume assignments and new customer onboarding). Enablement: released to all (under Desk Management) → [[modules/desk-management]]

- **Sanitization Workflow** — housekeeping staff can log in via phone/OTP to a sanitization portal, scan a floor QR code, select seats, and mark them as sanitized; employees see sanitization time for their selected seat; admins see consolidated sanitization status per floor. Enablement: TO ticket (property-driven) → [[modules/desk-management]]

- **Geofence Violation for QR Code Scan** — prevents misuse of QR codes (e.g. scanning from home); two modes: allow scan but capture violation in report, or block scan and show error. Three new booking-report columns: Violation (Yes/No), Scan Geocodes, Violation Distance. Enablement: TO ticket → [[modules/desk-management]], [[modules/employee-experience]]

- **Shift-Based Self-Booking Control (App)** — shifts can be selectively enabled for employee self-booking on the app; some shifts can be manager-controlled (e.g. allowance-associated shifts). Enablement: TO ticket → [[modules/ets]], [[modules/employee-experience]]

---

## Linked Raw Evidence

| Note | Source file |
|------|------------|
| RN Dec-2022 | `raw/se-runbook/crawl/files/1HS15LPBKqTjJC-qvnd6PLusD7OCAYqENSAt9j2Z0Z_w.pptx` |
| RN Nov-2022 | `raw/se-runbook/crawl/files/13du69PZ2aXC4175OBTU9a_MDD4nCLmExrqdamapaQXc.pptx` |
| RN Oct.2 | `raw/se-runbook/crawl/files/1qTmpgLXrpCDFynrEOoKdi_6rEQBqB5tSAL4RLkWJWMw.pptx` |
| RN Oct.1 | `raw/se-runbook/crawl/files/18E9PEhXNQs7gIf8MgdK_FHueqObRmrHP9wQjrhipV84.pptx` |
| RN Aug.1 | `raw/se-runbook/crawl/files/1M5dCSilxkUbVF9FLh2sqP7BTkvxaPt8AMhNdzhOsSlY.pptx` |
| RN Jul.1 | `raw/se-runbook/crawl/files/1Ico0VbvqY5OVtUL29fRVOfiajVNOg0O7Npv2rLZSZ2w.pptx` |
| RN Jun.2 | `raw/se-runbook/crawl/files/1vRSkJlP93fgMkCbTqZEnKoJRgOc_wg2nUDV7Ikh8vEc.pptx` |
| RN Jun.1 | `raw/se-runbook/crawl/files/1Pltey8615EGIv8KOnIrWJKgrPWM7yXBQg_dioYBC098.pptx` |
| RN Apr.1 & May.1 | `raw/se-runbook/crawl/files/1sZ3Wp2C1avQNW5FfJ5XuxOxhLvCczEGMZYnkwOm5_N4.pptx` |
| N-Level Hierarchy | `raw/se-runbook/crawl/files/1xHVOKaUMAe41U2jAJOkeQxar_ejOeZUVJuHPc1ckc7g.pptx` |
| Parking — Vehicle Creation | `raw/se-runbook/crawl/files/1Vj6Ledb1l_MqjQ-5rt5X7AtHZ0xlebdOZhPFB8STI3I.pptx` |
| Recurring Bookings | `raw/se-runbook/crawl/files/1yVLbX83WWvjWbCjqcrRq4drtQjbp1DITSbCewfUYJ4g.docx` |
| Indemnification Form | `raw/se-runbook/crawl/files/1lx6Qa0LJDpDVZ_sADfwnCVhoQENq0yL3CL9HY-4PDsA.docx` |
| Seat Assignment — New Features | `raw/se-runbook/crawl/files/1RckM3pU5zf-vt7XWe7dTNOy9JqjQmczb.pptx` |

> **Skipped entry:** "tabs Setup URLs Demo Script Release Notes Repo Copy of Release Notes …" — this entry in the crawl is a Google Drive navigation/tab index (no `raw_path`, content is a list of spreadsheet tab names and Drive URLs). It is not a release note and was excluded from this page.
