---
title: "Visitor Management Service — Config Properties"
service: VISITOR
total_configs: 157
servers: [in, com]
generated: 2026-06-09
type: config
module: visitor-management
---

# Visitor Management Service — Config Properties

Auto-generated on 2026-06-09. Total configs: **157**.

| Property | Description | Type | Default | Server |
|----------|-------------|------|---------|--------|
| `<p>Iagreethatalldetailssharedbymearecorrect</p>` | - | STRING |  | .com only |
| `absoluteVisitDurationHours` | This is list of option for time duration selection in vms kiosk in min | LIST |  | .com only |
| `addCustomFieldsForBulkUpload` | Determines whether custom fields are included in bulk upload header. | BOOLEAN |  | .com only |
| `addCustomFieldsWithVisitorBulkUpload` | Adds custom fields to visitor bulk upload headers. | BOOLEAN |  | both |
| `addRoomWithVisitorBulkUpload` | Adds room details to visitor bulk upload headers. | BOOLEAN |  | both |
| `allowBookingsForOthers` | Allows booking on behalf of others in visitor flow. | BOOLEAN |  | .com only |
| `approvalFlowEmailExpiryTimeInMinutes` | Defines approval email expiry time in minutes. | INTEGER |  | both |
| `approveEntryFromFrontdesk` | Allows visitor approval or rejection from Front Desk. | BOOLEAN |  | both |
| `approveMsTeamsTemplate` | Defines MS Teams template for approval notifications. | JSON |  | both |
| `autofillCustomFields` | Auto-populates custom fields for returning visitors. | BOOLEAN |  | .com only |
| `blacklistKioskPopup` | Defines heading and subheading for blacklist popup on kiosk. | JSON |  | .com only |
| `BULK_OPERATION_VISITOR_BOOKING` | Enables visitor bulk operation. | BOOLEAN |  | .com only |
| `cancelInviteMsTeamTemplateForHost` | Defines MS Teams template for host when invite is canceled. | JSON |  | .com only |
| `cancelInviteNotifications` | Notifies host when invite is canceled from Front Desk. | LIST |  | .com only |
| `canteenKioskConfigs` | Contains all the configs related for Canteen Kiosk | JSON |  | .com only |
| `checkinBufferFromKiosk` | Defines buffer time (in minutes) for active booking check-in via kiosk. | INTEGER |  | both |
| `checkoutOnFDEmployee` | Shows checkout CTA for employee flow on Front Desk. | BOOLEAN |  | .com only |
| `checkoutPageRedirectionTimeout` | Defines redirection timeout (in minutes) after self check-in completion. | INTEGER |  | both |
| `configureVisitorKiosk` | Controls visibility of Configure Visitor Kiosk button on Front Desk. | BOOLEAN |  | both |
| `consentCheckboxContentSafeReach` | Defines consent checkbox content for Safe Reach kiosk. | STRING |  | .com only |
| `controlSearchSections` | Controls visibility of sections in Front Desk search dropdown. | LIST |  | both |
| `creatorNotifications` | Controls creator notifications (backend property). | JSON |  | both |
| `DefaultEndTimeOfEmployeeBooking` | Defines default end time for employee booking. | INTEGER |  | .com only |
| `defaultInviteTitle` | Defines default title for Invite Form. | STRING |  | both |
| `defaultKioskBookingDurationInMinutes` | Defines fixed visit duration for each visitor check-in. | INTEGER |  | both |
| `defaultVisitTypeSelection` | Controls default selection behavior for Type of Visit field. | BOOLEAN |  | both |
| `digipass` | Controls DigiPass visibility across email and badge channels. | LIST |  | both |
| `digipassAutoSend` | Automatically sends DigiPass. | BOOLEAN |  | .com only |
| `digipassAutoSendBuffer` | Defines buffer time for sending DigiPass after booking creation. | INTEGER |  | .com only |
| `DynamicFields` | Not in use. | LIST |  | .com only |
| `emailListToAdmin` | Defines email list for admin notes. | LIST |  | .com only |
| `emailListToReceptionist` | Defines email list for receptionist/security notes. | LIST |  | .com only |
| `employeeCheckinMsTeamsTemplateAdmin` | Defines MS Teams template for admin employee check-in notifications. | JSON |  | .com only |
| `employeeCheckinMsTeamsTemplateCreator` | Defines MS Teams template for employee self check-in notifications. | JSON |  | .com only |
| `employeeCheckoutPrompt` | Defines confirmation modal checklist for employee checkout. | LIST |  | .com only |
| `employeeFaceOnboardingForRecognition` | Onboards employee photos into face recognition service. | BOOLEAN |  | .com only |
| `employeeFlowWithoutVisitor` | enabling employee flow without visitor | BOOLEAN |  | .com only |
| `enableBlacklistVisitorProfiles` | Enables visitor blacklist feature. | BOOLEAN |  | .com only |
| `enableCalendarInvite` | Creates calendar event in host email upon invite creation. | BOOLEAN |  | both |
| `enableConsentCheckboxSafeReach` | Enables additional consent checkbox in Safe Reach form. | BOOLEAN |  | .com only |
| `enabledBuidForVisitorConfigs` | Enables visitor notification page. | LIST |  | both |
| `enableDynamicFields` | Not in use. | BOOLEAN |  | .com only |
| `enableEmployeeEmailNotification` | Enables check-in notifications to employees. | BOOLEAN |  | .com only |
| `enableEmployeeMSTeamNotification` | Enables MS Teams notifications for employee check-in flow. | BOOLEAN |  | .com only |
| `enableNoninteractiveVisitorInvite` | Enables non-interactive email notifications. | BOOLEAN |  | .com only |
| `enableOtpOverride` | Enables OTP override flow on VMS kiosk. | BOOLEAN |  | .com only |
| `enableOTPValidationSelfCheckin` | Enables OTP validation on kiosk. | BOOLEAN |  | .com only |
| `enableOTPValidationSelfCheckinList` | Enables OTP validation in kiosk self check-in flow. | LIST |  | both |
| `enablePrintBadgeForInviteFlow` | Enables badge printing for visitors via Invite flow. | BOOLEAN |  | both |
| `enableScrollToConsentEnforcement` | This property controlled whether user have to scroll till end to enable the CTA's or not | BOOLEAN |  | .com only |
| `enableSelfRegistrationOnKiosk` | Enables employee self-registration on kiosk. | BOOLEAN |  | .com only |
| `enableSignatureForConsentSafeReach` | Requires signature-based consent in Safe Reach form. | BOOLEAN |  | .com only |
| `enableVisitorParking` | Enables parking for visitors (currently not in use). | BOOLEAN |  | both |
| `enableWalkInEmail` | Not in use. | BOOLEAN |  | .com only |
| `entryApprovalFromFrontdesk` | Not in use. | BOOLEAN |  | .com only |
| `entryTimeInLimit` | Defines buffer time for entry in the 2-step check-in/checkout process. | INTEGER |  | both |
| `externalEmailIdsMapToTriggerOnVisitorCheckin` | Not in use. | JSON |  | .com only |
| `externalEmailIdsToTriggerOnVisitorCheckin` | Not in use. | LIST |  | .com only |
| `externalEmployeeList` | Stores external stakeholder email and name details. | LIST |  | both |
| `externalNotifications` | Controls external notifications (backend property). | JSON |  | .com only |
| `FDReportColumnsEmployee` | Defines configurable columns for Employee Front Desk report. | JSON |  | .com only |
| `FDReportColumnsVisitor` | Defines configurable columns for Visitor Front Desk report. | JSON |  | .com only |
| `finalScreenCTATextSelfCheckInFlow` | This property controlled what to show as the end button text in different flows | JSON |  | .com only |
| `floorKioskAllowOfficeCheckin` | New property for controlling office check-in via Floor Kiosk. | LIST |  | .com only |
| `floorKioskConfigs` | Defines Floor Kiosk configurations in Settings. | JSON |  | both |
| `forms_configurations` | Controls belongings configuration for VMS self check-in flow. | JSON |  | both |
| `formsMetaDataForHost` | Controls host-side custom fields in invited flow. | JSON |  | both |
| `formsMetaDataForHostPWC` | Handles host-side custom fields and belongings in invited flow (PWC). | JSON |  | both |
| `formsMetaDataForVisitor` | Controls visitor-side custom fields in invited flow. | JSON |  | both |
| `formsMetaDataForVisitorPWC` | Handles visitor-side custom fields and belongings in invited flow (PWC). | JSON |  | both |
| `formsMetaDataForWalkIn` | Handles custom fields and belongings for Walk-in flow. | JSON |  | both |
| `front_desk_configurations` | Defines core functionalities visible on Front Desk. | JSON |  | both |
| `frontDeskColumns` | Controls column dropdown configuration on Front Desk. | LIST |  | .com only |
| `GUEST_BULK_UPLOAD` | Enables bulk upload option for visitors. | BOOLEAN |  | both |
| `GUEST_POLICY_HEADER` | Adds a customizable guest policy header. | STRING |  | .com only |
| `HOST_POLICY_HEADER` | Adds a customizable host policy header. | STRING |  | .com only |
| `hostNotifications` | Controls host notifications (backend property). | JSON |  | both |
| `identification` | Allows enablement of identification on front desk | BOOLEAN |  | both |
| `inviteFormDefaultOfficeSelection` | Defines default office selection in Invite Visitor form. | BOOLEAN |  | both |
| `is2StepCheckInEnabled` | Enables 2-step check-in and check-out process. | BOOLEAN |  | both |
| `isEditEndTimeOnFrontDeskEnabled` | Enables editing of invite end time on Front Desk. | BOOLEAN |  | both |
| `isEmployeeFlowEnabled` | Enables employee check-in flow on kiosk. | BOOLEAN |  | both |
| `IsGuestWifiEnabled` | Enables or disables Guest Wi-Fi. | BOOLEAN |  | both |
| `isTemporaryCheckoutEnabled` | Enables temporary checkout option on Front Desk. | BOOLEAN |  | both |
| `isVisitorCheckinMsTeamsNotificationEnabled` | Enables visitor check-in notifications via email and MS Teams. | BOOLEAN |  | both |
| `isVisitorCheckoutMsTeamsNotificationEnabled` | Controls visitor check-out notifications on MS Teams. | BOOLEAN |  | both |
| `isVisitorPhotoCaptureEnabled` | Controls whether photo capture is required during self check-in. | LIST |  | .com only |
| `kioskEmployeeRegistrationFields` | Controls fields displayed in kiosk employee self-registration form. | JSON |  | .com only |
| `kioskInviteOptions` | Controls QR-based check-in and check-out options on kiosk. | LIST |  | both |
| `kioskRequireOTPBeforeRegister` | Enables OTP validation before kiosk employee registration. | BOOLEAN |  | .com only |
| `KioskSafeReachInterval` | Defines Safe Reach interval (in minutes) for VMS kiosk. | LIST |  | .com only |
| `mandateAcceptNda` | NDA mandatory? |  |  | .in only |
| `NDA` | Not in use. | BOOLEAN |  | .com only |
| `ndaCheckbox` | Controls NDA checkbox visibility. | BOOLEAN |  | both |
| `ndaCheckboxContent` | Defines content displayed below NDA checkbox. | STRING |  | both |
| `ndaPagePosition` | Position of NDA. |  |  | .in only |
| `ndaScreenHeader` | This property controlled nda screen header text | STRING |  | .com only |
| `notesToAdmins` | Enables optional notes to admins via email. | BOOLEAN |  | both |
| `noteToFrontDesk` | Enables optional notes to receptionist/security via email. | BOOLEAN |  | both |
| `notificationConfigs` | Defines notification page configuration values. | JSON |  | both |
| `notificationMetaData` | Defines metadata configuration for notification page. | JSON |  | both |
| `otpApprovalFlow` | Not in use. | BOOLEAN |  | .com only |
| `overStayAlertBuffer` | Defines buffer time (in minutes) after end time to trigger overstay alerts. | INTEGER |  | both |
| `overStayAlertMsTeamsTemplate` | Defines MS Teams template for overstay alerts. | JSON |  | both |
| `overStayAlertRecipients` | Defines recipient list for overstay alerts. | LIST |  | both |
| `overstayTriggerList` | Defines channels (MS Teams/Email) for overstay alerts. | LIST |  | both |
| `preFillVisitorPhotoForExistingVisitor` | Allows pre-filling of visitor photo for existing visitors. | BOOLEAN |  | both |
| `Print_Visitor_Badge` | Enables Print Badge button on Front Desk dashboard. | BOOLEAN |  | both |
| `printerConnectionModes` | Defines available printer connection modes. | LIST |  | .com only |
| `profileFieldsMetaData` | Handles profile fields configuration for invited flow. | LIST |  | both |
| `qrCheckInBufferTime` | Defines buffer time (in minutes) before booking start when QR check-in is allowed. | INTEGER |  | .com only |
| `safeReachConsentContent` | Defines consent statement with checkbox in Safe Reach kiosk form. | STRING |  | .com only |
| `safeReachFailedVerificationTrigger` | Defines trigger conditions for Safe Reach escalation email. | INTEGER |  | .com only |
| `SafeReachInputFields` | Defines customizable fields in Safe Reach form. | LIST |  | both |
| `safeReachManualVerificationTrigger` | Defines timeout for Safe Reach Level 2 escalation. | INTEGER |  | .com only |
| `safeReachSecurityTeamContacts` | Defines security contacts for Safe Reach Level 1 escalation. | LIST |  | .com only |
| `SafeReachVmsTimeInMin` | Defines Safe Reach trigger time in minutes. | INTEGER |  | both |
| `selfCheckinSuccessMessage` | Defines success message displayed after visitor self check-in. | STRING |  | both |
| `sendHostEmailsToDelegate` | Sends all host-triggered emails to the delegate as well. | BOOLEAN |  | both |
| `sendHostMsTeamsNotificationToDelegate` | Controls whether MS Teams notifications are sent to delegate. | BOOLEAN |  | both |
| `sendInviteEmail` | Defines default state of visitor, host, and creator email checkboxes. | JSON |  | both |
| `sendVisitorInviteEmail` | DTO key for sending visitor invite emails. | BOOLEAN |  | .com only |
| `showBelongings` | Not in use. | BOOLEAN |  | .com only |
| `showDefaultInviteTitle` | Enables default invite title on Invite Visitor page. | BOOLEAN |  | both |
| `showDelegateeBookForSomeoneElse` | Displays delegatees in host search for booking on behalf. | LIST |  | .com only |
| `tempEntryTimeLimit` | Defines buffer time for entry after temporary checkout in the 2-step check-in/checkout process. | INTEGER |  | both |
| `triggerExternalEmails` | Triggers emails to designated roles such as Global Admin. | LIST |  | .com only |
| `triggerListForLandlords` | Defines external stakeholder email trigger list. | JSON |  | .com only |
| `triggerSafeReachForFemaleOnly` | Triggers Safe Reach for female visitors only. | BOOLEAN |  | .com only |
| `triggerVisitorEmailsFromRooms` | Controls visitor email triggers in Meeting Rooms workflow. | BOOLEAN |  | .com only |
| `vendorKioskConfigs` | Contains all the configs related for Vendor Kiosk | JSON |  | .com only |
| `visitDurationHours` | Defines dropdown options for visit duration. | INTEGER |  | both |
| `VISITOR_DIGIPASS` | Not in use. | BOOLEAN |  | .com only |
| `Visitor_Document_Storage` | Enables visitor document storage configuration. | BOOLEAN |  | both |
| `Visitor_Document_Storage_Document_Type` | Defines document types applicable for visitor data storage. | LIST |  | both |
| `Visitor_Document_Storage_Duration` | Defines retention period (in days) for visitor data storage. | INTEGER |  | both |
| `VISITOR_PROFILE_ID` | Controls whether visitor identity proof upload is required. | BOOLEAN |  | both |
| `Visitor_Profile_ID_Document_Upload_Field_Inputs` | Defines allowed document types for visitor upload. | LIST |  | both |
| `visitor_wifi_name` | Stores client Wi-Fi name. | STRING |  | both |
| `visitorApprovalMsTeamsNotification` | Controls visitor approval notification on MS Teams. | BOOLEAN |  | both |
| `visitorBulkUploadData` | Defines headers and data rules for visitor bulk upload; must comply with profileFieldsMetaData. | JSON |  | both |
| `visitorBulkUploadFields` | Defines headers and default values for visitor bulk upload. | JSON |  | both |
| `visitorCheckinMsTeamsBodyTemplate` | Defines body template for MS Teams visitor check-in notification. | STRING |  | .com only |
| `visitorCheckinMsTeamsHeaderTemplate` | Defines salutation header for MS Teams visitor check-in notification. | STRING |  | .com only |
| `visitorCheckinMsTeamsTemplate` | Defines visitor check-in email template. | JSON |  | both |
| `visitorCheckoutMsTeamsTemplate` | Defines MS Teams template for visitor check-out notification. | JSON |  | both |
| `visitorFormsMetaData` | Not in use. | LIST |  | .com only |
| `visitorFormsMetaDataPWC` | Handles profile and custom fields in VMS self check-in flow (PWC). | LIST |  | both |
| `visitorKioskConfigs` | Handles UI formatting for VMS self check-in flow. | JSON |  | both |
| `visitorNotifications` | Controls visitor notifications. | JSON |  | .com only |
| `visitorProfileFields` | Controls visitor profile fields for Walk-in flow. | JSON |  | both |
| `visitorProfilePhotoUpload` | Controls whether profile photo is mandatory in invited flow. | BOOLEAN |  | both |
| `visitorSelfCheckOutDigiPass` | Not in use. | BOOLEAN |  | .com only |
| `visitorWidgetEnabled` | Controls visibility of VMS widget on Employee Home. | BOOLEAN |  | both |
| `vmsInviteTrigger` | Triggers visitor invite based on configured list. | LIST |  | both |
| `vmsQrCodeTrigger` | Controls sending DigiPass and checkout QR via SMS or email. | LIST |  | both |
| `walkInEnabled` | Not in use. | BOOLEAN |  | .com only |
