# Glossary
_All terms, abbreviations, and naming conventions. Updated on every ingest._

| Term | Definition | Module Context | Notes |
|------|-----------|----------------|-------|
| Auto-release | Automatic room reclamation when no check-in occurs within `MEETING_ROOM_RELEASE_IF_NO_CHECKIN` minutes of booking start. Organizer is notified; calendar event is NOT cancelled. | [[modules/meeting-rooms]] | Config flag `RELEASE_MEETING_ROOM` must be true to activate. |
| BUID | Business Unit ID. Tenant/customer identifier used to scope feature flags and configuration in WorkInSync. | All modules | Equivalent to "tenant ID". |
| Booking | A meeting room reservation tying a Room to a time slot and organizer. One Meeting ID per booking (stable across edits). | [[modules/meeting-rooms]] | See [[entities/booking]] |
| Cafeteria | A food-service premise with configurable menu categories and items. Used for both Meeting Rooms catering and Meal Management. | [[modules/meeting-rooms]], [[modules/meal-management]] | Ownership between modules TBD. See [[entities/cafeteria]] |
| CateringOrder | A food/beverage order attached to a meeting room booking. Multiple Order IDs possible per meeting (one per cafeteria × delivery slot). | [[modules/meeting-rooms]] | See [[entities/catering-order]] |
| Dynamic Policy | Tag-based access control for meeting rooms. Employees can only book rooms if their EmployeeTag values match the RoomTag values. Powered by the tag engine owned by `tags-desk-parking`. | [[modules/meeting-rooms]], [[modules/tags-desk-parking]] | Applies to native rooms only — not Outlook/Google integrated rooms. |
| EmployeeTag | A label assigned to an employee profile to define attributes (e.g. department, role). Evaluated against RoomTags at booking time. | [[modules/tags-desk-parking]] | See [[entities/room-tag]] |
| Floor Kiosk | A shared tablet device deployed per meeting room or per floor. Meeting Rooms Kiosk is one use case of the broader Floor Kiosk infrastructure. | [[modules/floor-kiosk]] | See [[cross-module/meeting-rooms-floor-kiosk]] |
| Integrated Room | A meeting room whose calendar is managed by Outlook or Google Calendar rather than WIS natively. WIS cannot apply Dynamic Policy to integrated rooms. | [[modules/meeting-rooms]] | Contrast with Native Room. |
| MaintenancePeriod | A scheduled downtime window on a meeting room. Can optionally block new bookings during that window. Max 90 days. | [[modules/meeting-rooms]] | See [[entities/maintenance-period]] |
| MDM | Mobile Device Management. Required for Meeting Rooms Kiosk deployment — enforces single-app mode, push updates, supervised mode. | [[modules/floor-kiosk]] | Apple/Android supervised mode. |
| Meeting ID | The stable identifier for a meeting room booking. Persists across booking edits. Distinct from Order IDs (catering). | [[modules/meeting-rooms]] | See [[entities/booking]] |
| MS Graph API | Microsoft Graph API — used for Outlook/Google Calendar integration, room mailbox sync, and user resolution in Meeting Rooms. | [[modules/ms-teams-integration]] | Requires delegated + application permissions; admin consent required. |
| Native Room | A meeting room whose availability is managed entirely by WIS (not synced to external calendar). Dynamic Policy can be applied to native rooms. | [[modules/meeting-rooms]] | Contrast with Integrated Room. |
| Order ID | The identifier for a specific catering sub-order (per cafeteria × delivery slot). Reminted when an order is cancelled and recreated. | [[modules/meeting-rooms]] | See [[entities/catering-order]] |
| Pairing Code | Alphanumeric code used to pair a kiosk tablet device to a specific meeting room. Generated in the admin panel. | [[modules/meeting-rooms]] | Used alongside admin email during kiosk setup. |
| PIN (Kiosk) | One-time PIN emailed to the meeting organizer, used to authenticate cancel/end-meeting actions on the room kiosk. | [[modules/meeting-rooms]] | Controlled by `MEETING_EMAIL_OTP_TO_AUTHENTICATE`. |
| RoomTag | A label assigned to a meeting room to restrict which employees can book it (Dynamic Policy). Must match EmployeeTag type + value. | [[modules/tags-desk-parking]] (owner), [[modules/meeting-rooms]] (consumer) | See [[entities/room-tag]] |
| Tag Engine | The shared system owned by `tags-desk-parking` that creates, manages, and evaluates tags. Reused by Meeting Rooms for Dynamic Policy. | [[modules/tags-desk-parking]] | See [[cross-module/meeting-rooms-tags-desk-parking]] |
| BLOCK_HOTSEAT | Special dynamic policy tag for parking. When applied to an employee, prevents them from booking any hotslot — forces use of only their dedicated or tagged slot. | [[modules/parking-management]] | Applied via Employee Tagging bulk upload. |
| Digipass | A digital pass generated on the mobile app to authenticate check-in at premises (parking, office, cafeteria). | [[modules/parking-management]], [[modules/mobile-app]] | Alternative to QR code scan. |
| Hotslot | A parking slot open for any employee to book (default assignment type). | [[modules/parking-management]] | Contrast with Employee/Team/Blocked slot types. |
| Parking Waitlist | IRCTC-style FCFS queue for when all parking slots on a level are full. Real-time position number shown to employee. | [[modules/parking-management]] | Level-based; multi-level joining supported. |
| WFO Booking | Work From Office booking — the parent booking record an employee creates when planning an office day. Parking and desk are add-ons to WFO booking. | [[modules/desk-management]] | Entry point for parking booking. |
| WIS | WorkInSync — the product. | All | |
| SCIM | System for Cross-domain Identity Management, RFC 7644; protocol for IdP-driven user provisioning to WorkInSync via SCIM 2.0 endpoints. | [[modules/employee-provisioning]] | Azure AD / Okta / any SCIM-compliant IdP. Users only — Groups not supported. |
| SSO | Single Sign-On; WorkInSync acts as Service Provider, supporting SAML 2.0 and OAuth 2.0/OIDC. | [[modules/sso]] | Web + mobile SSO. |
| SAML | Security Assertion Markup Language 2.0; XML-based SSO via IdP/SP metadata exchange; WIS uses `<client>.workinsync.io` as SP. | [[modules/sso]] | IdP guides: Azure AD, Okta. |
| OAuth | OAuth 2.0 / OpenID Connect SSO via the `auth.moveinsync.com/mis-auth` service; BUID as registration-id. | [[modules/sso]] | Scopes: openid, email. |
| IdP | Identity Provider (also: Asserting Party). System that authenticates users and issues assertions. Examples: Azure AD, Okta, Google. | [[modules/sso]] | Contrast with SP. |
| SP | Service Provider (also: Relying Party). System that consumes IdP assertions to authenticate users. WorkInSync acts as SP in SAML flows. | [[modules/sso]] | Contrast with IdP. |
