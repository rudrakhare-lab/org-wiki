---
type: config
module: visitor-management
servers:
  - in
  - com
last_updated: 2026-05-26
sources:
  in: "[[sources/pms-configs-in-all-wis-configs]]"
  com: "[[sources/pms-configs-com-wis-service-configs]]"
---

# Visitor Management Service (VMS) — Config Properties

## Service
Visitor Management Service (VMS). Linked module: [[modules/visitor-management]].

_Source: [[sources/pms-configs-in-all-wis-configs]] | [[sources/pms-configs-com-wis-service-configs]]_

## Config Comparison

> **Server key:** ✅ = property present in that server's config list | — = absent
> **Description source:** `.com` description preferred; falls back to `.in`, PMS Description Cleaned, then `wis_unique_configs`.
> ⚠️ `undocumented` = no description found in any source — contact the owning team.

| Property Name | .in | .com | Data Type | Description |
|---------------|-----|------|-----------|-------------|
| `addCustomFieldsWithVisitorBulkUpload` | ✅ | ✅ | BOOLEAN | Adds custom fields to visitor bulk upload headers. |
| `addRoomWithVisitorBulkUpload` | ✅ | ✅ | BOOLEAN | Adds room details to visitor bulk upload headers. |
| `approvalFlowEmailExpiryTimeInMinutes` | ✅ | ✅ | INTEGER | Defines approval email expiry time in minutes. |
| `approveEntryFromFrontdesk` | ✅ | ✅ | BOOLEAN | Allows visitor approval or rejection from Front Desk. |
| `approveMsTeamsTemplate` | ✅ | ✅ | JSON | Defines MS Teams template for approval notifications. |
| `checkinBufferFromKiosk` | ✅ | ✅ | INTEGER | Defines buffer time (in minutes) for active booking check-in via kiosk. |
| `checkoutPageRedirectionTimeout` | ✅ | ✅ | INTEGER | Defines redirection timeout (in minutes) after self check-in completion. |
| `configureVisitorKiosk` | ✅ | ✅ | BOOLEAN | Controls visibility of Configure Visitor Kiosk button on Front Desk. |
| `controlSearchSections` | ✅ | ✅ | LIST | Controls visibility of sections in Front Desk search dropdown. |
| `creatorNotifications` | ✅ | ✅ | JSON | Controls creator notifications (backend property). |
| `defaultInviteTitle` | ✅ | ✅ | STRING | Defines default title for Invite Form. |
| `defaultKioskBookingDurationInMinutes` | ✅ | ✅ | INTEGER | Defines fixed visit duration for each visitor check-in. |
| `defaultVisitTypeSelection` | ✅ | ✅ | BOOLEAN | Controls default selection behavior for Type of Visit field. |
| `digipass` | ✅ | ✅ | LIST | Controls DigiPass visibility across email and badge channels. |
| `enableCalendarInvite` | ✅ | ✅ | BOOLEAN | Creates calendar event in host email upon invite creation. |
| `enabledBuidForVisitorConfigs` | ✅ | ✅ | LIST | Enables visitor notification page. |
| `enableOTPValidationSelfCheckinList` | ✅ | ✅ | LIST | Enables OTP validation in kiosk self check-in flow. |
| `enablePrintBadgeForInviteFlow` | ✅ | ✅ | BOOLEAN | Enables badge printing for visitors via Invite flow. |
| `enableVisitorParking` | ✅ | ✅ | BOOLEAN | Enables parking for visitors (currently not in use). |
| `entryTimeInLimit` | ✅ | ✅ | INTEGER | Defines buffer time for entry in the 2-step check-in/checkout process. |
| `externalEmployeeList` | ✅ | ✅ | LIST | Stores external stakeholder email and name details. |
| `floorKioskConfigs` | ✅ | ✅ | JSON | Defines Floor Kiosk configurations in Settings. |
| `forms_configurations` | ✅ | ✅ | JSON | Controls belongings configuration for VMS self check-in flow. |
| `formsMetaDataForHost` | ✅ | ✅ | JSON | Controls host-side custom fields in invited flow. |
| `formsMetaDataForHostPWC` | ✅ | ✅ | JSON | Handles host-side custom fields and belongings in invited flow (PWC). |
| `formsMetaDataForVisitor` | ✅ | ✅ | JSON | Controls visitor-side custom fields in invited flow. |
| `formsMetaDataForVisitorPWC` | ✅ | ✅ | JSON | Handles visitor-side custom fields and belongings in invited flow (PWC). |
| `formsMetaDataForWalkIn` | ✅ | ✅ | JSON | Handles custom fields and belongings for Walk-in flow. |
| `front_desk_configurations` | ✅ | ✅ | JSON | Defines core functionalities visible on Front Desk. |
| `GUEST_BULK_UPLOAD` | ✅ | ✅ | BOOLEAN | Enables bulk upload option for visitors. |
| `hostNotifications` | ✅ | ✅ | JSON | Controls host notifications (backend property). |
| `identification` | ✅ | ✅ | BOOLEAN | Allows enablement of identification on front desk |
| `inviteFormDefaultOfficeSelection` | ✅ | ✅ | BOOLEAN | Defines default office selection in Invite Visitor form. |
| `is2StepCheckInEnabled` | ✅ | ✅ | BOOLEAN | Enables 2-step check-in and check-out process. |
| `isEditEndTimeOnFrontDeskEnabled` | ✅ | ✅ | BOOLEAN | Enables editing of invite end time on Front Desk. |
| `isEmployeeFlowEnabled` | ✅ | ✅ | BOOLEAN | Enables employee check-in flow on kiosk. |
| `IsGuestWifiEnabled` | ✅ | ✅ | BOOLEAN | Enables or disables Guest Wi-Fi. |
| `isTemporaryCheckoutEnabled` | ✅ | ✅ | BOOLEAN | Enables temporary checkout option on Front Desk. |
| `isVisitorCheckinMsTeamsNotificationEnabled` | ✅ | ✅ | BOOLEAN | Enables visitor check-in notifications via email and MS Teams. |
| `isVisitorCheckoutMsTeamsNotificationEnabled` | ✅ | ✅ | BOOLEAN | Controls visitor check-out notifications on MS Teams. |
| `kioskInviteOptions` | ✅ | ✅ | LIST | Controls QR-based check-in and check-out options on kiosk. |
| `ndaCheckbox` | ✅ | ✅ | BOOLEAN | Controls NDA checkbox visibility. |
| `ndaCheckboxContent` | ✅ | ✅ | STRING | Defines content displayed below NDA checkbox. |
| `notesToAdmins` | ✅ | ✅ | BOOLEAN | Enables optional notes to admins via email. |
| `noteToFrontDesk` | ✅ | ✅ | BOOLEAN | Enables optional notes to receptionist/security via email. |
| `notificationConfigs` | ✅ | ✅ | JSON | Defines notification page configuration values. |
| `notificationMetaData` | ✅ | ✅ | JSON | Defines metadata configuration for notification page. |
| `overStayAlertBuffer` | ✅ | ✅ | INTEGER | Defines buffer time (in minutes) after end time to trigger overstay alerts. |
| `overStayAlertMsTeamsTemplate` | ✅ | ✅ | JSON | Defines MS Teams template for overstay alerts. |
| `overStayAlertRecipients` | ✅ | ✅ | LIST | Defines recipient list for overstay alerts. |
| `overstayTriggerList` | ✅ | ✅ | LIST | Defines channels (MS Teams/Email) for overstay alerts. |
| `preFillVisitorPhotoForExistingVisitor` | ✅ | ✅ | BOOLEAN | Allows pre-filling of visitor photo for existing visitors. |
| `Print_Visitor_Badge` | ✅ | ✅ | BOOLEAN | Enables Print Badge button on Front Desk dashboard. |
| `profileFieldsMetaData` | ✅ | ✅ | LIST | Handles profile fields configuration for invited flow. |
| `SafeReachInputFields` | ✅ | ✅ | LIST | Defines customizable fields in Safe Reach form. |
| `SafeReachVmsTimeInMin` | ✅ | ✅ | INTEGER | Defines Safe Reach trigger time in minutes. |
| `selfCheckinSuccessMessage` | ✅ | ✅ | STRING | Defines success message displayed after visitor self check-in. |
| `sendHostEmailsToDelegate` | ✅ | ✅ | BOOLEAN | Sends all host-triggered emails to the delegate as well. |
| `sendHostMsTeamsNotificationToDelegate` | ✅ | ✅ | BOOLEAN | Controls whether MS Teams notifications are sent to delegate. |
| `sendInviteEmail` | ✅ | ✅ | JSON | Defines default state of visitor, host, and creator email checkboxes. |
| `showDefaultInviteTitle` | ✅ | ✅ | BOOLEAN | Enables default invite title on Invite Visitor page. |
| `tempEntryTimeLimit` | ✅ | ✅ | INTEGER | Defines buffer time for entry after temporary checkout in the 2-step check-in/checkout process. |
| `visitDurationHours` | ✅ | ✅ | INTEGER | Defines dropdown options for visit duration. |
| `Visitor_Document_Storage` | ✅ | ✅ | BOOLEAN | Enables visitor document storage configuration. |
| `Visitor_Document_Storage_Document_Type` | ✅ | ✅ | LIST | Defines document types applicable for visitor data storage. |
| `Visitor_Document_Storage_Duration` | ✅ | ✅ | INTEGER | Defines retention period (in days) for visitor data storage. |
| `VISITOR_PROFILE_ID` | ✅ | ✅ | BOOLEAN | Controls whether visitor identity proof upload is required. |
| `Visitor_Profile_ID_Document_Upload_Field_Inputs` | ✅ | ✅ | LIST | Defines allowed document types for visitor upload. |
| `visitor_wifi_name` | ✅ | ✅ | STRING | Stores client Wi-Fi name. |
| `visitorApprovalMsTeamsNotification` | ✅ | ✅ | BOOLEAN | Controls visitor approval notification on MS Teams. |
| `visitorBulkUploadData` | ✅ | ✅ | JSON | Defines headers and data rules for visitor bulk upload; must comply with profileFieldsMetaData. |
| `visitorBulkUploadFields` | ✅ | ✅ | JSON | Defines headers and default values for visitor bulk upload. |
| `visitorCheckinMsTeamsTemplate` | ✅ | ✅ | JSON | Defines visitor check-in email template. |
| `visitorCheckoutMsTeamsTemplate` | ✅ | ✅ | JSON | Defines MS Teams template for visitor check-out notification. |
| `visitorFormsMetaDataPWC` | ✅ | ✅ | LIST | Handles profile and custom fields in VMS self check-in flow (PWC). |
| `visitorKioskConfigs` | ✅ | ✅ | JSON | Handles UI formatting for VMS self check-in flow. |
| `visitorProfileFields` | ✅ | ✅ | JSON | Controls visitor profile fields for Walk-in flow. |
| `visitorProfilePhotoUpload` | ✅ | ✅ | BOOLEAN | Controls whether profile photo is mandatory in invited flow. |
| `visitorWidgetEnabled` | ✅ | ✅ | BOOLEAN | Controls visibility of VMS widget on Employee Home. |
| `vmsInviteTrigger` | ✅ | ✅ | LIST | Triggers visitor invite based on configured list. |
| `vmsQrCodeTrigger` | ✅ | ✅ | LIST | Controls sending DigiPass and checkout QR via SMS or email. |
| `mandateAcceptNda` | ✅ | — | — | NDA mandatory? |
| `ndaPagePosition` | ✅ | — | — | Position of NDA. |
| `<p>Iagreethatalldetailssharedbymearecorrect</p>` | — | ✅ | STRING | - |
| `absoluteVisitDurationHours` | — | ✅ | LIST | This is list of option for time duration selection in vms kiosk in min |
| `addCustomFieldsForBulkUpload` | — | ✅ | BOOLEAN | Determines whether custom fields are included in bulk upload header. |
| `allowBookingsForOthers` | — | ✅ | BOOLEAN | Allows booking on behalf of others in visitor flow. |
| `autofillCustomFields` | — | ✅ | BOOLEAN | Auto-populates custom fields for returning visitors. |
| `blacklistKioskPopup` | — | ✅ | JSON | Defines heading and subheading for blacklist popup on kiosk. |
| `BULK_OPERATION_VISITOR_BOOKING` | — | ✅ | BOOLEAN | Enables visitor bulk operation. |
| `cancelInviteMsTeamTemplateForHost` | — | ✅ | JSON | Defines MS Teams template for host when invite is canceled. |
| `cancelInviteNotifications` | — | ✅ | LIST | Notifies host when invite is canceled from Front Desk. |
| `canteenKioskConfigs` | — | ✅ | JSON | Contains all the configs related for Canteen Kiosk |
| `checkoutOnFDEmployee` | — | ✅ | BOOLEAN | Shows checkout CTA for employee flow on Front Desk. |
| `consentCheckboxContentSafeReach` | — | ✅ | STRING | Defines consent checkbox content for Safe Reach kiosk. |
| `DefaultEndTimeOfEmployeeBooking` | — | ✅ | INTEGER | Defines default end time for employee booking. |
| `digipassAutoSend` | — | ✅ | BOOLEAN | Automatically sends DigiPass. |
| `digipassAutoSendBuffer` | — | ✅ | INTEGER | Defines buffer time for sending DigiPass after booking creation. |
| `DynamicFields` | — | ✅ | LIST | Not in use. |
| `emailListToAdmin` | — | ✅ | LIST | Defines email list for admin notes. |
| `emailListToReceptionist` | — | ✅ | LIST | Defines email list for receptionist/security notes. |
| `employeeCheckinMsTeamsTemplateAdmin` | — | ✅ | JSON | Defines MS Teams template for admin employee check-in notifications. |
| `employeeCheckinMsTeamsTemplateCreator` | — | ✅ | JSON | Defines MS Teams template for employee self check-in notifications. |
| `employeeCheckoutPrompt` | — | ✅ | LIST | Defines confirmation modal checklist for employee checkout. |
| `employeeFaceOnboardingForRecognition` | — | ✅ | BOOLEAN | Onboards employee photos into face recognition service. |
| `employeeFlowWithoutVisitor` | — | ✅ | BOOLEAN | enabling employee flow without visitor |
| `enableBlacklistVisitorProfiles` | — | ✅ | BOOLEAN | Enables visitor blacklist feature. |
| `enableConsentCheckboxSafeReach` | — | ✅ | BOOLEAN | Enables additional consent checkbox in Safe Reach form. |
| `enableDynamicFields` | — | ✅ | BOOLEAN | Not in use. |
| `enableEmployeeEmailNotification` | — | ✅ | BOOLEAN | Enables check-in notifications to employees. |
| `enableEmployeeMSTeamNotification` | — | ✅ | BOOLEAN | Enables MS Teams notifications for employee check-in flow. |
| `enableNoninteractiveVisitorInvite` | — | ✅ | BOOLEAN | Enables non-interactive email notifications. |
| `enableOtpOverride` | — | ✅ | BOOLEAN | Enables OTP override flow on VMS kiosk. |
| `enableOTPValidationSelfCheckin` | — | ✅ | BOOLEAN | Enables OTP validation on kiosk. |
| `enableScrollToConsentEnforcement` | — | ✅ | BOOLEAN | This property controlled whether user have to scroll till end to enable the CTA's or not |
| `enableSelfRegistrationOnKiosk` | — | ✅ | BOOLEAN | Enables employee self-registration on kiosk. |
| `enableSignatureForConsentSafeReach` | — | ✅ | BOOLEAN | Requires signature-based consent in Safe Reach form. |
| `enableWalkInEmail` | — | ✅ | BOOLEAN | Not in use. |
| `entryApprovalFromFrontdesk` | — | ✅ | BOOLEAN | Not in use. |
| `externalEmailIdsMapToTriggerOnVisitorCheckin` | — | ✅ | JSON | Not in use. |
| `externalEmailIdsToTriggerOnVisitorCheckin` | — | ✅ | LIST | Not in use. |
| `externalNotifications` | — | ✅ | JSON | Controls external notifications (backend property). |
| `FDReportColumnsEmployee` | — | ✅ | JSON | Defines configurable columns for Employee Front Desk report. |
| `FDReportColumnsVisitor` | — | ✅ | JSON | Defines configurable columns for Visitor Front Desk report. |
| `finalScreenCTATextSelfCheckInFlow` | — | ✅ | JSON | This property controlled what to show as the end button text in different flows |
| `floorKioskAllowOfficeCheckin` | — | ✅ | LIST | New property for controlling office check-in via Floor Kiosk. |
| `frontDeskColumns` | — | ✅ | LIST | Controls column dropdown configuration on Front Desk. |
| `GUEST_POLICY_HEADER` | — | ✅ | STRING | Adds a customizable guest policy header. |
| `HOST_POLICY_HEADER` | — | ✅ | STRING | Adds a customizable host policy header. |
| `isVisitorPhotoCaptureEnabled` | — | ✅ | LIST | Controls whether photo capture is required during self check-in. |
| `kioskEmployeeRegistrationFields` | — | ✅ | JSON | Controls fields displayed in kiosk employee self-registration form. |
| `kioskRequireOTPBeforeRegister` | — | ✅ | BOOLEAN | Enables OTP validation before kiosk employee registration. |
| `KioskSafeReachInterval` | — | ✅ | LIST | Defines Safe Reach interval (in minutes) for VMS kiosk. |
| `NDA` | — | ✅ | BOOLEAN | Not in use. |
| `ndaScreenHeader` | — | ✅ | STRING | This property controlled nda screen header text |
| `otpApprovalFlow` | — | ✅ | BOOLEAN | Not in use. |
| `printerConnectionModes` | — | ✅ | LIST | Defines available printer connection modes. |
| `qrCheckInBufferTime` | — | ✅ | INTEGER | Defines buffer time (in minutes) before booking start when QR check-in is allowed. |
| `safeReachConsentContent` | — | ✅ | STRING | Defines consent statement with checkbox in Safe Reach kiosk form. |
| `safeReachFailedVerificationTrigger` | — | ✅ | INTEGER | Defines trigger conditions for Safe Reach escalation email. |
| `safeReachManualVerificationTrigger` | — | ✅ | INTEGER | Defines timeout for Safe Reach Level 2 escalation. |
| `safeReachSecurityTeamContacts` | — | ✅ | LIST | Defines security contacts for Safe Reach Level 1 escalation. |
| `sendVisitorInviteEmail` | — | ✅ | BOOLEAN | DTO key for sending visitor invite emails. |
| `showBelongings` | — | ✅ | BOOLEAN | Not in use. |
| `showDelegateeBookForSomeoneElse` | — | ✅ | LIST | Displays delegatees in host search for booking on behalf. |
| `triggerExternalEmails` | — | ✅ | LIST | Triggers emails to designated roles such as Global Admin. |
| `triggerListForLandlords` | — | ✅ | JSON | Defines external stakeholder email trigger list. |
| `triggerSafeReachForFemaleOnly` | — | ✅ | BOOLEAN | Triggers Safe Reach for female visitors only. |
| `triggerVisitorEmailsFromRooms` | — | ✅ | BOOLEAN | Controls visitor email triggers in Meeting Rooms workflow. |
| `vendorKioskConfigs` | — | ✅ | JSON | Contains all the configs related for Vendor Kiosk |
| `VISITOR_DIGIPASS` | — | ✅ | BOOLEAN | Not in use. |
| `visitorCheckinMsTeamsBodyTemplate` | — | ✅ | STRING | Defines body template for MS Teams visitor check-in notification. |
| `visitorCheckinMsTeamsHeaderTemplate` | — | ✅ | STRING | Defines salutation header for MS Teams visitor check-in notification. |
| `visitorFormsMetaData` | — | ✅ | LIST | Not in use. |
| `visitorNotifications` | — | ✅ | JSON | Controls visitor notifications. |
| `visitorSelfCheckOutDigiPass` | — | ✅ | BOOLEAN | Not in use. |
| `walkInEnabled` | — | ✅ | BOOLEAN | Not in use. |

## .in-only Configs
_2 properties present on the `.in` server but absent from the `.com` config list._

- `mandateAcceptNda` — NDA mandatory?
- `ndaPagePosition` — Position of NDA.

## .com-only Configs
_74 properties present on the `.com` server but absent from the `.in` config list._

- `<p>Iagreethatalldetailssharedbymearecorrect</p>` — -
- `absoluteVisitDurationHours` — This is list of option for time duration selection in vms kiosk in min
- `addCustomFieldsForBulkUpload` — Determines whether custom fields are included in bulk upload header.
- `allowBookingsForOthers` — Allows booking on behalf of others in visitor flow.
- `autofillCustomFields` — Auto-populates custom fields for returning visitors.
- `blacklistKioskPopup` — Defines heading and subheading for blacklist popup on kiosk.
- `BULK_OPERATION_VISITOR_BOOKING` — Enables visitor bulk operation.
- `cancelInviteMsTeamTemplateForHost` — Defines MS Teams template for host when invite is canceled.
- `cancelInviteNotifications` — Notifies host when invite is canceled from Front Desk.
- `canteenKioskConfigs` — Contains all the configs related for Canteen Kiosk
- `checkoutOnFDEmployee` — Shows checkout CTA for employee flow on Front Desk.
- `consentCheckboxContentSafeReach` — Defines consent checkbox content for Safe Reach kiosk.
- `DefaultEndTimeOfEmployeeBooking` — Defines default end time for employee booking.
- `digipassAutoSend` — Automatically sends DigiPass.
- `digipassAutoSendBuffer` — Defines buffer time for sending DigiPass after booking creation.
- `DynamicFields` — Not in use.
- `emailListToAdmin` — Defines email list for admin notes.
- `emailListToReceptionist` — Defines email list for receptionist/security notes.
- `employeeCheckinMsTeamsTemplateAdmin` — Defines MS Teams template for admin employee check-in notifications.
- `employeeCheckinMsTeamsTemplateCreator` — Defines MS Teams template for employee self check-in notifications.
- `employeeCheckoutPrompt` — Defines confirmation modal checklist for employee checkout.
- `employeeFaceOnboardingForRecognition` — Onboards employee photos into face recognition service.
- `employeeFlowWithoutVisitor` — enabling employee flow without visitor
- `enableBlacklistVisitorProfiles` — Enables visitor blacklist feature.
- `enableConsentCheckboxSafeReach` — Enables additional consent checkbox in Safe Reach form.
- `enableDynamicFields` — Not in use.
- `enableEmployeeEmailNotification` — Enables check-in notifications to employees.
- `enableEmployeeMSTeamNotification` — Enables MS Teams notifications for employee check-in flow.
- `enableNoninteractiveVisitorInvite` — Enables non-interactive email notifications.
- `enableOtpOverride` — Enables OTP override flow on VMS kiosk.
- `enableOTPValidationSelfCheckin` — Enables OTP validation on kiosk.
- `enableScrollToConsentEnforcement` — This property controlled whether user have to scroll till end to enable the CTA's or not
- `enableSelfRegistrationOnKiosk` — Enables employee self-registration on kiosk.
- `enableSignatureForConsentSafeReach` — Requires signature-based consent in Safe Reach form.
- `enableWalkInEmail` — Not in use.
- `entryApprovalFromFrontdesk` — Not in use.
- `externalEmailIdsMapToTriggerOnVisitorCheckin` — Not in use.
- `externalEmailIdsToTriggerOnVisitorCheckin` — Not in use.
- `externalNotifications` — Controls external notifications (backend property).
- `FDReportColumnsEmployee` — Defines configurable columns for Employee Front Desk report.
- `FDReportColumnsVisitor` — Defines configurable columns for Visitor Front Desk report.
- `finalScreenCTATextSelfCheckInFlow` — This property controlled what to show as the end button text in different flows
- `floorKioskAllowOfficeCheckin` — New property for controlling office check-in via Floor Kiosk.
- `frontDeskColumns` — Controls column dropdown configuration on Front Desk.
- `GUEST_POLICY_HEADER` — Adds a customizable guest policy header.
- `HOST_POLICY_HEADER` — Adds a customizable host policy header.
- `isVisitorPhotoCaptureEnabled` — Controls whether photo capture is required during self check-in.
- `kioskEmployeeRegistrationFields` — Controls fields displayed in kiosk employee self-registration form.
- `kioskRequireOTPBeforeRegister` — Enables OTP validation before kiosk employee registration.
- `KioskSafeReachInterval` — Defines Safe Reach interval (in minutes) for VMS kiosk.
- `NDA` — Not in use.
- `ndaScreenHeader` — This property controlled nda screen header text
- `otpApprovalFlow` — Not in use.
- `printerConnectionModes` — Defines available printer connection modes.
- `qrCheckInBufferTime` — Defines buffer time (in minutes) before booking start when QR check-in is allowed.
- `safeReachConsentContent` — Defines consent statement with checkbox in Safe Reach kiosk form.
- `safeReachFailedVerificationTrigger` — Defines trigger conditions for Safe Reach escalation email.
- `safeReachManualVerificationTrigger` — Defines timeout for Safe Reach Level 2 escalation.
- `safeReachSecurityTeamContacts` — Defines security contacts for Safe Reach Level 1 escalation.
- `sendVisitorInviteEmail` — DTO key for sending visitor invite emails.
- `showBelongings` — Not in use.
- `showDelegateeBookForSomeoneElse` — Displays delegatees in host search for booking on behalf.
- `triggerExternalEmails` — Triggers emails to designated roles such as Global Admin.
- `triggerListForLandlords` — Defines external stakeholder email trigger list.
- `triggerSafeReachForFemaleOnly` — Triggers Safe Reach for female visitors only.
- `triggerVisitorEmailsFromRooms` — Controls visitor email triggers in Meeting Rooms workflow.
- `vendorKioskConfigs` — Contains all the configs related for Vendor Kiosk
- `VISITOR_DIGIPASS` — Not in use.
- `visitorCheckinMsTeamsBodyTemplate` — Defines body template for MS Teams visitor check-in notification.
- `visitorCheckinMsTeamsHeaderTemplate` — Defines salutation header for MS Teams visitor check-in notification.
- `visitorFormsMetaData` — Not in use.
- `visitorNotifications` — Controls visitor notifications.
- `visitorSelfCheckOutDigiPass` — Not in use.
- `walkInEnabled` — Not in use.

_Last updated: 2026-05-26_
_Source: [[sources/pms-configs-in-all-wis-configs]] | [[sources/pms-configs-com-wis-service-configs]]_
