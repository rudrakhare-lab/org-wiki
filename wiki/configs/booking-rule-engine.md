---
title: "Booking Rule Engine — Config Properties"
service: BOOKING-RULE-ENGINE
total_configs: 188
servers: [in, com]
generated: 2026-06-09
type: config
module: booking-rule-engine
---

# Booking Rule Engine — Config Properties

Auto-generated on 2026-06-09. Total configs: **188**.

| Property | Description | Type | Default | Server |
|----------|-------------|------|---------|--------|
| `advanceBooking` | - | BOOLEAN |  | both |
| `allocationChangeCommunicationEnabled` | - | BOOLEAN |  | .com only |
| `allowBookingAfterSignOut` | - | BOOLEAN |  | .com only |
| `allowedBookingForContainmentZone` | - | BOOLEAN |  | .com only |
| `allowedMealBookingPerEmployee` | Decides how many separate meal bookings the system should allow per user per day. | INTEGER |  | .com only |
| `allowOfficeCheckInWithoutDesk` | Controls the separate checkin for office and desk checkin. | BOOLEAN |  | .com only |
| `approvalFlowEnabled` | - | BOOLEAN |  | both |
| `approvalFlowInInWfhEnabled` | - | BOOLEAN |  | .com only |
| `approvalFlowInWfoEnabled` | - | BOOLEAN |  | .com only |
| `approvedRequestNotificationEnabled` | - | BOOLEAN |  | .com only |
| `approverPersonaEmails` | - | JSON |  | .com only |
| `attendanceManagementDisabled` | - | BOOLEAN |  | .com only |
| `autoAbsentHours` | - | INTEGER |  | both |
| `autoAllocate` | - | BOOLEAN |  | both |
| `autoApprovalConfig` | Config for auto approval. | JSON |  | .com only |
| `autoApprovalTime` | Auto approval of resource. | INTEGER |  | .com only |
| `autoApproveEnabled` | - | BOOLEAN |  | both |
| `autoCheckinEnableFloorKiosk` | Allow auto-checkin to the booking created from floor kiosk if the following logic stands true. | LIST |  | .com only |
| `autoExpireBeforeNoOfdays` | - | STRING |  | .com only |
| `autoExpireHour` | - | STRING |  | .com only |
| `autoLogoutMinutes` | - | INTEGER |  | both |
| `autoRequestApprovalEnabled` | - | BOOLEAN |  | .com only |
| `autoSlotAllocate` | - | BOOLEAN |  | .com only |
| `blockGenerateDigiPassOnSeatMandatory` | - | BOOLEAN |  | .com only |
| `blockUserIfNotVaccinated` | - | BOOLEAN |  | both |
| `booker` | - | STRING |  | .com only |
| `bookingApprovalEmailsEnabled` | - | BOOLEAN |  | .com only |
| `bookingEditCutOff` | - | DOUBLE |  | .com only |
| `bookingLogoutEditCutOff` | - | DOUBLE |  | .com only |
| `bookingPerDayEmp` | - | DOUBLE |  | .com only |
| `bookingRequestApprovalFlowEnabled` | - | BOOLEAN |  | .com only |
| `buidsEnabledForPMS` | - | LIST |  | .com only |
| `cancelSchedulesEnabled` | - | BOOLEAN |  | .com only |
| `checkInFirstPremise` | - | BOOLEAN |  | .com only |
| `checkInWithoutAarogyasetuValidation` | - | BOOLEAN |  | .com only |
| `checkTransportCutoffForBookingEdit` | - | BOOLEAN |  | .com only |
| `countBookingBySomeOneElseAsEmployeeBooking` | - | BOOLEAN |  | both |
| `createBookingAfterSignedOut` | - | BOOLEAN |  | .com only |
| `createBookingWhenCheckinReceived` | - | BOOLEAN |  | .com only |
| `customPlannerViewEnabled` | - | BOOLEAN |  | .com only |
| `CutOffTimeBetweenBookingsOnSeatInMinute` | - | INTEGER |  | .com only |
| `defaulBookingHoursIfExtCheckin` | - | DOUBLE |  | .com only |
| `defaultLogoutShiftMinutes` | - | INTEGER |  | .com only |
| `defLogoutDuration` | - | DOUBLE |  | .com only |
| `defOnCallLogoutDurationInMinute` | - | INTEGER |  | .com only |
| `defWfhLogoutDurationInMinute` | - | INTEGER |  | .com only |
| `deleteFutureSchedulesOnDeactivation` | - | BOOLEAN |  | .com only |
| `disableWfhWfoOverlapping` | - | BOOLEAN |  | both |
| `dynamicDataForDesk` | - | JSON |  | .com only |
| `dynamicFieldNameOnBookingForm` | Dynamic fields name description. | STRING |  | .com only |
| `emailBookingMessage` | - | STRING |  | .com only |
| `emailsForApprovalFlowRequest` | - | LIST |  | .com only |
| `empHomepageTodaysAvailabilityCard` | Once enabled, the user must see the complete availability card; modules inside the card will be visible based on whether the respective module is enabled for the user's office. | BOOLEAN |  | .com only |
| `employeeCancelCutOff` | - | INTEGER |  | both |
| `employeeEndTimeBookingCutoff` | - | INTEGER |  | .com only |
| `employeeEndTimeScheduleCutoff` | - | INTEGER |  | .com only |
| `employeeScheduleCutoff` | - | INTEGER |  | .com only |
| `enableBookingEmail` | - | BOOLEAN |  | .com only |
| `enableBookingsOnHolidays` | - | BOOLEAN |  | both |
| `enableDynamicFields` | Defines if dynamic field is enabled. | BOOLEAN |  | .com only |
| `enableIndoorNavigation` | - | BOOLEAN |  | .com only |
| `enableMealBookingNudge` | - | BOOLEAN |  | both |
| `enableMealConfigureKiosk` | To enable 'Configure Kiosk' button on meal dashboard. | BOOLEAN |  | .com only |
| `enableMealOnlyBulkUpload` | - | BOOLEAN |  | .com only |
| `enableOfficeCheckInWithParkingCheckIn` | - | BOOLEAN |  | .com only |
| `enableParkingAvailabilityWidgetWithoutBooking` | When the parking booking module is not enabled for the client, but they only want to consume the available slot numbers. | BOOLEAN |  | .com only |
| `enablePriorityWiseAutoSlotAllocate` | When enabled, slot is assigned in priority order based on display order value. | BOOLEAN |  | .com only |
| `enablePrivilegeOnApp` | To show resources while booking based on privilege. | BOOLEAN |  | .com only |
| `enableRecurrenceOnTeamPlanner` | - | BOOLEAN |  | .com only |
| `enableSeparateMealOption` | Enable meal-only booking (coupled with existing property to enable meals). | BOOLEAN |  | .com only |
| `enableWeeklyOffBookings` | - | BOOLEAN |  | .com only |
| `expiredRequestNotificationEnabled` | - | BOOLEAN |  | .com only |
| `expiryCutOffInMinutes` | - | INTEGER |  | both |
| `expiryNotificationCutOffInMinutes` | - | INTEGER |  | .com only |
| `extCheckinToBookingBuffer` | - | DOUBLE |  | both |
| `externalChannelCheckIn` | - | BOOLEAN |  | .com only |
| `filterNoAvailableSeatInFloor` | - | BOOLEAN |  | .com only |
| `floorKioskCheckInOutEmails` | Conditions to send check-in/checkout mail on, values should be of type [CHECKIN, CHECKOUT]. | LIST |  | .com only |
| `gatepassDelaycutoff` | - | DOUBLE |  | .com only |
| `genericLabelForDesk` | Resource name label to replace Desk keyword on all employee and admin pages. | STRING |  | .com only |
| `hideParkingSlotInfo` | - | BOOLEAN |  | .com only |
| `isAmenitiesFilter` | - | BOOLEAN |  | .com only |
| `isAppFeedbackEnabled` | - | BOOLEAN |  | .com only |
| `isAutoAbsentEnabled` | - | BOOLEAN |  | .com only |
| `isAutoEntryAllowed` | - | BOOLEAN |  | .com only |
| `isAutoLogoutEnabled` | - | BOOLEAN |  | .com only |
| `isCalendarInviteEnabled` | - | BOOLEAN |  | both |
| `isCheckinNotificationEnabled` | - | BOOLEAN |  | .com only |
| `isCustomShiftsRestricted` | TO BE STRICTLY UPDATED ONLY FROM CONFIGURATION PAGE. Defines if the selection of custom shift would be allowed or not. | BOOLEAN |  | .com only |
| `isDynamicFieldsMandatory` | Defines if dynamic fields is mandatory. | BOOLEAN |  | .com only |
| `isPhoneValidationOptional` | - | BOOLEAN |  | .com only |
| `isSeatValidationEnabled` | - | BOOLEAN |  | .com only |
| `isSeatValidationEnabledOnQrScan` | - | BOOLEAN |  | .com only |
| `isShiftPairingEnabled` | Defines the enablement of shift pairs. | BOOLEAN |  | .com only |
| `limitEmployeeBookingDays` | - | BOOLEAN |  | .com only |
| `limitEmployeeBookingDaysType` | - | STRING |  | .com only |
| `limitEmployeeBookingDaysUnit` | - | DOUBLE |  | .com only |
| `limitMealDuringBookingCreation` | - | BOOLEAN |  | .com only |
| `lockerBookingEnabled` | Update Desk/Office labels to Locker based on this configuration. | BOOLEAN |  | .com only |
| `mandatoryBookingRequiredForCounterScan` | Ensures only users with an active meal booking can scan the counter QR code to consume a meal, preventing scans without bookings. | BOOLEAN |  | .com only |
| `maxBufferForCheckin` | - | DOUBLE |  | .com only |
| `maxHoursAllowedForCheckin` | - | DOUBLE |  | .com only |
| `maxShiftDuration` | - | DOUBLE |  | both |
| `maxTimeAfterClockin` | - | BOOLEAN |  | .com only |
| `maxTimeBeforeClockin` | - | BOOLEAN |  | .com only |
| `mealCancelCutoffInMinutes` | Property to enable/disable booking cancellation option if created with meal and 'enableSeparateMealOption' is enabled. | INTEGER |  | .com only |
| `mealFinalStage` | Defines the final status of a meal booking. | LIST |  | .com only |
| `mealPlanningEnabled` | - | BOOLEAN |  | .com only |
| `minHoursAllowedForCheckin` | - | DOUBLE |  | .com only |
| `minShiftDuration` | - | DOUBLE |  | .com only |
| `mobileNumberLength` | - | INTEGER |  | .com only |
| `multipleBookingsOnASeatInADayAllowed` | - | BOOLEAN |  | both |
| `newRoomParticipantWorkflow` | Determines whether participant addition should be allowed in the new room booking flow. | BOOLEAN |  | .com only |
| `nextDayLogoutEnabled` | - | BOOLEAN |  | both |
| `noResourceBookingConfirmation` | Defines if there is no resource then the popup to confirm booking without resource should be displayed or not. | BOOLEAN |  | .com only |
| `numOfDays` | - | INTEGER |  | .com only |
| `officeCheckInModeApp` | - | STRING |  | .com only |
| `officeCheckInModeWeb` | - | STRING |  | .com only |
| `onCallMaxShiftDurationInMinute` | - | INTEGER |  | .com only |
| `onCallMinShiftDurationInMinute` | - | INTEGER |  | .com only |
| `otpOverIvrForVisitor` | - | BOOLEAN |  | .com only |
| `overlappingTimeInMinutes` | - | INTEGER |  | .com only |
| `overrideMinMaxShiftDurations` | Overrides minShiftDuration and maxShiftDuration configurations for bookings created from Workplanner and Booking Bulk Upload. | JSON |  | .com only |
| `parkingSlotBufferTimeInMin` | - | INTEGER |  | .com only |
| `pendingRequestsNotificationEnabled` | - | BOOLEAN |  | .com only |
| `qRScannerEndCutOffInMinute` | - | INTEGER |  | both |
| `qRScannerStartCutOffInMinute` | - | INTEGER |  | both |
| `recordCheckInOutViaAccessCardAPI` | - | BOOLEAN |  | .com only |
| `rejectBookingIfNoDesk` | - | BOOLEAN |  | both |
| `rejectedRequestNotificationEnabled` | - | BOOLEAN |  | .com only |
| `remoteSignInAllowed` | - | BOOLEAN |  | .com only |
| `removeMealSelectionOnHolidayAndWeeklyOff` | - | BOOLEAN |  | .com only |
| `requestorPersonaEmails` | For approval flow email. | JSON |  | .com only |
| `resourceApprovalsPage` | Resource approval page. | BOOLEAN |  | .com only |
| `resourceApprovalsPageApp` | Enables resource approval page. | BOOLEAN |  | .com only |
| `resourceRequestsPage` | Resource request page for approval. | BOOLEAN |  | .com only |
| `resourceRequestsPageApp` | - | BOOLEAN |  | .com only |
| `restrictMealSelectionTo` | Specifies the maximum number of meal items a user is allowed to select. Users can choose up to restrictMealSelectionTo items; they cannot select more. If 0, user can select unlimited items. | INTEGER |  | .com only |
| `restrictScanQROnFabButton` | When enabled (default false), restricts that the check-in mode on an office level also needs to be ScanQR. If disabled, any QR code can be scanned regardless of the office check-in mode. | BOOLEAN |  | .com only |
| `roomMaintenanceMessage` | Controls the message displayed after the maintenance message, to allow admins to give further instructions for maintenance related messages. | STRING |  | .com only |
| `roomMaintenanceWorkflow` | Property for enabling and disabling the room maintenance flow. | BOOLEAN |  | .com only |
| `seatAllocationAction` | - | STRING |  | both |
| `seatBookingEnabled` | Allow employees to create desk bookings. | BOOLEAN |  | both |
| `seatMandatory` | - | BOOLEAN |  | both |
| `seatSanitizationCheck` | - | BOOLEAN |  | both |
| `seatScanEnable` | - | BOOLEAN |  | .com only |
| `seatValidation` | - | BOOLEAN |  | both |
| `selectShiftsAfterSpecificTime` | - | DOUBLE |  | .com only |
| `setFavoriteRooms` | Allows user to set any meeting room as their favourite for easy access. | BOOLEAN |  | .com only |
| `shouldAllowCustomTimingWhileEdit` | STRICTLY TO BE UPDATED ONLY FROM CONFIG PAGE IN THE UI. Defines if employee will be allowed to select custom timing while editing a booking. | BOOLEAN |  | .com only |
| `showCabs` | - | BOOLEAN |  | .com only |
| `showDigipassOptionForDedicatedSeat` | - | BOOLEAN |  | .com only |
| `showFirstCheckInRecord` | - | BOOLEAN |  | .com only |
| `showMealOrderStatus` | - | BOOLEAN |  | .com only |
| `showParking` | - | BOOLEAN |  | .com only |
| `showQRScanner` | - | BOOLEAN |  | .com only |
| `showSanitizationDetails` | - | BOOLEAN |  | .com only |
| `showVaccinationOptionInSideMenu` | - | BOOLEAN |  | .com only |
| `spocCancelCutOff` | - | INTEGER |  | .com only |
| `spocScheduleCutOff` | - | INTEGER |  | .com only |
| `tagsEnabled` | - | LIST |  | both |
| `teamCalendarEnabled` | - | BOOLEAN |  | .com only |
| `TestPropertyOnPMS` | - | BOOLEAN |  | .com only |
| `timeDiffShiftsMin` | - | DOUBLE |  | .com only |
| `vaccinationMaxApprovalDays` | - | INTEGER |  | .com only |
| `vendorColumnMappings` | To customize the column header labels in the Meal Dashboard. | JSON |  | .com only |
| `vendorMealDisplayColumn` | Tells which columns need to be shown on vendor-dashboard (only related to meal columns). | LIST |  | .com only |
| `vendorMealStatus` | Types of meal statuses defined per office. | LIST |  | .com only |
| `waitlistExpiryEnabled` | Expire waitlist bookings once the start time has passed and no confirmed slot has been assigned to the parking booking. | BOOLEAN |  | .com only |
| `wfhBookingAllowed` | - | BOOLEAN |  | both |
| `wfhCancelCutOff` | - | INTEGER |  | .com only |
| `wfhClockInBuffer` | - | INTEGER |  | .com only |
| `wfhClockinBuffer` | - | DOUBLE |  | .com only |
| `wfhDisabled` | - | BOOLEAN |  | .com only |
| `wfhEditCutOff` | - | INTEGER |  | .com only |
| `wfhMaxDurationForBooking` | - | DOUBLE |  | .com only |
| `wfhMaxShiftDurationInMinute` | - | INTEGER |  | .com only |
| `wfhMinBetweenClockinClockout` | - | DOUBLE |  | .com only |
| `wfhMinDurationForBooking` | - | DOUBLE |  | .com only |
| `wfhMinShiftDurationInMinute` | - | INTEGER |  | .com only |
| `wfhMonthlyLimit` | - | INTEGER |  | .com only |
| `wfhMonthlyLimit / wfhWeeklyLimit` | Caps the maximum number of WFH days an employee is allowed to request per week or month. |  |  | .in only |
| `wfhScheduleCutOff` | - | INTEGER |  | .com only |
| `wfhSpocEditCutOff` | - | INTEGER |  | .com only |
| `wfhSpocSchecduleCutOff` | - | INTEGER |  | .com only |
| `wfhWeeklyLimit` | - | INTEGER |  | .com only |
| `wfoReasonList` | - | STRING |  | both |
| `workplannerNotificationControl` | Controls the email flow of the workplanner. | JSON |  | .com only |
