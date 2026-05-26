---
type: config
module: none
servers:
  - in
  - com
last_updated: 2026-05-26
sources:
  in: "[[sources/pms-configs-in-all-wis-configs]]"
  com: "[[sources/pms-configs-com-wis-service-configs]]"
---

# Booking Rule Engine — Config Properties

## Service
Booking Rule Engine. Linked module: `booking-rule-engine` (no module page yet — needs stub).

_Source: [[sources/pms-configs-in-all-wis-configs]] | [[sources/pms-configs-com-wis-service-configs]]_

## Config Comparison

> **Server key:** ✅ = property present in that server's config list | — = absent
> **Description source:** `.com` description preferred; falls back to `.in`, PMS Description Cleaned, then `wis_unique_configs`.
> ⚠️ `undocumented` = no description found in any source — contact the owning team.

| Property Name | .in | .com | Data Type | Description |
|---------------|-----|------|-----------|-------------|
| `advanceBooking` | ✅ | ✅ | BOOLEAN | Enables users to book seats days or weeks in advance, rather than just same-day. |
| `approvalFlowEnabled` | ✅ | ✅ | BOOLEAN | Seat or WFH bookings go into a "Pending" status and require manager/admin approval. |
| `autoAbsentHours` | ✅ | ✅ | INTEGER | Marks an employee as a "No Show" if they fail to check in within this many hours of their shift start. |
| `autoAllocate` | ✅ | ✅ | BOOLEAN | The system automatically assigns a desk to an employee based on their team zone if they don't pick one manually. |
| `autoApproveEnabled` | ✅ | ✅ | BOOLEAN | Bypasses the manual approval flow, instantly confirming user requests. |
| `autoLogoutMinutes` | ✅ | ✅ | INTEGER | Automatically checks the employee out of their desk X minutes after their scheduled shift ends. |
| `blockUserIfNotVaccinated` | ✅ | ✅ | BOOLEAN | A health-safety compliance rule that prevents booking if the user's profile lacks vaccination approval. |
| `countBookingBySomeOneElseAsEmployeeBooking` | ✅ | ✅ | BOOLEAN | If a manager or SPOC books a seat on behalf of an employee, it counts towards that employee's daily/weekly quota limits. |
| `disableWfhWfoOverlapping` | ✅ | ✅ | BOOLEAN | Prevents an employee from booking both a Work From Home day and a Work From Office desk on the exact same date. |
| `employeeCancelCutOff` | ✅ | ✅ | INTEGER | The deadline (in hours/mins) before a shift starts where an employee can no longer cancel their booking. |
| `enableBookingsOnHolidays` | ✅ | ✅ | BOOLEAN | Allows employees to book desks on dates designated as official company holidays. |
| `enableMealBookingNudge` | ✅ | ✅ | BOOLEAN | (Official Tooltip) To enable meal nudge flow for meal booking. |
| `expiryCutOffInMinutes` | ✅ | ✅ | INTEGER | Automatically cancels a booking and frees the desk if the user hasn't checked in within X minutes of their start time. |
| `extCheckinToBookingBuffer` | ✅ | ✅ | DOUBLE | Buffer time allowed between an external check-in (like badging at the turnstile) and the system confirming the desk booking. |
| `isCalendarInviteEnabled` | ✅ | ✅ | BOOLEAN | Triggers an automated calendar invite (.ics) to the user's email upon booking a seat. |
| `maxShiftDuration` | ✅ | ✅ | DOUBLE | The maximum duration of a single booking (e.g., 1440 minutes = 24 hours). |
| `multipleBookingsOnASeatInADayAllowed` | ✅ | ✅ | BOOLEAN | Allows different employees to book the same physical seat at different times of the day (e.g., morning shift vs. evening shift). |
| `nextDayLogoutEnabled` | ✅ | ✅ | BOOLEAN | Allows users working overnight shifts to have their check-out time roll over into the next calendar day. |
| `qRScannerEndCutOffInMinute` | ✅ | ✅ | INTEGER | How many minutes after a shift starts the QR code remains valid for check-in before the desk is forfeited. |
| `qRScannerStartCutOffInMinute` | ✅ | ✅ | INTEGER | How many minutes before a shift starts that an employee is allowed to scan the desk QR code to check in. |
| `rejectBookingIfNoDesk` | ✅ | ✅ | BOOLEAN | Blocks a user from declaring "Work From Office" if the floor plan is at 100% capacity. |
| `seatAllocationAction` | ✅ | ✅ | STRING | Dictates what happens if a user doesn't check in (e.g., REMOVE_SEAT frees it up for someone else). |
| `seatBookingEnabled` | ✅ | ✅ | BOOLEAN | Allow employees to create desk bookings. |
| `seatMandatory` | ✅ | ✅ | BOOLEAN | Forces a user to select a specific physical desk in order to complete a "Work From Office" request. |
| `seatSanitizationCheck` | ✅ | ✅ | BOOLEAN | Blocks a recently used seat from being booked back-to-back until cleaning staff marks it as sanitized. |
| `seatValidation` | ✅ | ✅ | BOOLEAN | Requires a physical check-in mechanism to confirm the user actually arrived at their desk. |
| `tagsEnabled` | ✅ | ✅ | LIST | Controls which global attendance tags (e.g., WFO, WFH) are active and selectable by users. |
| `wfhBookingAllowed` | ✅ | ✅ | BOOLEAN | Master switch to enable "Work From Home" logging and requests. |
| `wfoReasonList` | ✅ | ✅ | STRING | Populates the dropdown options users see when asked "Why are you coming to the office?" (e.g., Meeting, Demo, Support). |
| `wfhMonthlyLimit / wfhWeeklyLimit` | ✅ | — | — | Caps the maximum number of WFH days an employee is allowed to request per week or month. |
| `allocationChangeCommunicationEnabled` | — | ✅ | BOOLEAN | Sends notification when desk allocation changes. |
| `allowBookingAfterSignOut` | — | ✅ | BOOLEAN | Allows creation of a new booking after signing out of a previous booking. |
| `allowedBookingForContainmentZone` | — | ✅ | BOOLEAN | Allows booking even if employee is in containment zone. |
| `allowedMealBookingPerEmployee` | — | ✅ | INTEGER | Decides how many separate meal bookings the system should allow per user per day. |
| `allowOfficeCheckInWithoutDesk` | — | ✅ | BOOLEAN | Controls the separate checkin for office and desk checkin. |
| `approvalFlowInInWfhEnabled` | — | ✅ | BOOLEAN | Enabling booking approval flow for remote bookings |
| `approvalFlowInWfoEnabled` | — | ✅ | BOOLEAN | Enables WFO booking approval workflow. |
| `approvedRequestNotificationEnabled` | — | ✅ | BOOLEAN | Enables notification to users when booking requests are approved. |
| `approverPersonaEmails` | — | ✅ | JSON | Email notification list for sending approval requests for meeting room bookings |
| `attendanceManagementDisabled` | — | ✅ | BOOLEAN | Enables Attendance Dashboard on Admin Home. |
| `autoApprovalConfig` | — | ✅ | JSON | Config for auto approval. |
| `autoApprovalTime` | — | ✅ | INTEGER | Auto approval of resource. |
| `autoCheckinEnableFloorKiosk` | — | ✅ | LIST | Allow auto-checkin to the booking created from floor kiosk if the following logic stands true. |
| `autoExpireBeforeNoOfdays` | — | ✅ | STRING | configuration to autoexpire booking requests when approval not provided for bookings |
| `autoExpireHour` | — | ✅ | STRING | Action for Notifying users a booking is going to expire(office bookings) |
| `autoRequestApprovalEnabled` | — | ✅ | BOOLEAN | Automatically sends booking requests for approval. |
| `autoSlotAllocate` | — | ✅ | BOOLEAN | Enables auto-allocation of parking slots. |
| `blockGenerateDigiPassOnSeatMandatory` | — | ✅ | BOOLEAN | Blocks DigiPass check-in if seat is not selected in booking. |
| `booker` | — | ✅ | STRING | - |
| `bookingApprovalEmailsEnabled` | — | ✅ | BOOLEAN | Enables email notifications to approvers for booking approvals. |
| `bookingEditCutOff` | — | ✅ | DOUBLE | Defines advance hours required to edit a booking. |
| `bookingLogoutEditCutOff` | — | ✅ | DOUBLE | Defines logout edit cutoff restriction on web. |
| `bookingPerDayEmp` | — | ✅ | DOUBLE | Defines maximum bookings allowed per employee per day. |
| `bookingRequestApprovalFlowEnabled` | — | ✅ | BOOLEAN | Enables the booking approval workflow. |
| `buidsEnabledForPMS` | — | ✅ | LIST | Default list containing all BUIDS present on PMS |
| `cancelSchedulesEnabled` | — | ✅ | BOOLEAN | Allow cancellation of transport schedules from bookings |
| `checkInFirstPremise` | — | ✅ | BOOLEAN | Consider checkin from the first premise of checkin - Office/Desk/Parking |
| `checkInWithoutAarogyasetuValidation` | — | ✅ | BOOLEAN | Allows check-in without Aarogya Setu validation (deprecated). |
| `checkTransportCutoffForBookingEdit` | — | ✅ | BOOLEAN | Applies transport cutoff rules during booking edits. |
| `createBookingAfterSignedOut` | — | ✅ | BOOLEAN | Allows users to create bookings after signing out. |
| `createBookingWhenCheckinReceived` | — | ✅ | BOOLEAN | Controls booking creation via access card check-in. |
| `customPlannerViewEnabled` | — | ✅ | BOOLEAN | Enabling updated Workplanner view(True by default) |
| `CutOffTimeBetweenBookingsOnSeatInMinute` | — | ✅ | INTEGER | Defines minimum time gap between bookings on same seat. |
| `defaulBookingHoursIfExtCheckin` | — | ✅ | DOUBLE | Defines default booking duration when check-in is performed through an external channel. |
| `defaultLogoutShiftMinutes` | — | ✅ | INTEGER | Auto-populates checkout time based on configured duration. |
| `defLogoutDuration` | — | ✅ | DOUBLE | Defines default logout duration from login. |
| `defOnCallLogoutDurationInMinute` | — | ✅ | INTEGER | - |
| `defWfhLogoutDurationInMinute` | — | ✅ | INTEGER | Defines default logout duration for WFH bookings. |
| `deleteFutureSchedulesOnDeactivation` | — | ✅ | BOOLEAN | Automatically cancels future bookings when profile is deactivated. |
| `dynamicDataForDesk` | — | ✅ | JSON | - |
| `dynamicFieldNameOnBookingForm` | — | ✅ | STRING | Dynamic fields name description. |
| `emailBookingMessage` | — | ✅ | STRING | - |
| `emailsForApprovalFlowRequest` | — | ✅ | LIST | Sends approval request email to approvers. |
| `empHomepageTodaysAvailabilityCard` | — | ✅ | BOOLEAN | Once enabled, the user must see the complete availability card; modules inside the card will be visible based on whether the respective module is enabled for the user's office. |
| `employeeEndTimeBookingCutoff` | — | ✅ | INTEGER | Defines cutoff for booking after end time. |
| `employeeEndTimeScheduleCutoff` | — | ✅ | INTEGER | Defines logout edit cutoff restriction on mobile. |
| `employeeScheduleCutoff` | — | ✅ | INTEGER | Defines advance hours required to create a booking. |
| `enableBookingEmail` | — | ✅ | BOOLEAN | Enables booking email notifications. |
| `enableDynamicFields` | — | ✅ | BOOLEAN | Defines if dynamic field is enabled. |
| `enableIndoorNavigation` | — | ✅ | BOOLEAN | Enables indoor navigation (wayfinding) feature. |
| `enableMealConfigureKiosk` | — | ✅ | BOOLEAN | To enable 'Configure Kiosk' button on meal dashboard. |
| `enableMealOnlyBulkUpload` | — | ✅ | BOOLEAN | ⚠️ undocumented |
| `enableOfficeCheckInWithParkingCheckIn` | — | ✅ | BOOLEAN | Clubs office and parking check-in together. |
| `enableParkingAvailabilityWidgetWithoutBooking` | — | ✅ | BOOLEAN | When the parking booking module is not enabled for the client, but they only want to consume the available slot numbers. |
| `enablePriorityWiseAutoSlotAllocate` | — | ✅ | BOOLEAN | When enabled, slot is assigned in priority order based on display order value. |
| `enablePrivilegeOnApp` | — | ✅ | BOOLEAN | To show resources while booking based on privilege. |
| `enableRecurrenceOnTeamPlanner` | — | ✅ | BOOLEAN | Enables repeat booking on Work Planner. |
| `enableSeparateMealOption` | — | ✅ | BOOLEAN | Enable meal-only booking (coupled with existing property to enable meals). |
| `enableWeeklyOffBookings` | — | ✅ | BOOLEAN | Allows bookings on weekly off days. |
| `expiredRequestNotificationEnabled` | — | ✅ | BOOLEAN | Enables notification when booking approval requests expire. |
| `expiryNotificationCutOffInMinutes` | — | ✅ | INTEGER | Notifying users a booking is going to expire(office bookings) |
| `externalChannelCheckIn` | — | ✅ | BOOLEAN | Configures external check-in modes such as Face ID or Access Card. |
| `filterNoAvailableSeatInFloor` | — | ✅ | BOOLEAN | Not in use. |
| `floorKioskCheckInOutEmails` | — | ✅ | LIST | Conditions to send check-in/checkout mail on, values should be of type [CHECKIN, CHECKOUT]. |
| `gatepassDelaycutoff` | — | ✅ | DOUBLE | Defines end time for DigiPass check-in button. |
| `genericLabelForDesk` | — | ✅ | STRING | Resource name label to replace Desk keyword on all employee and admin pages. |
| `hideParkingSlotInfo` | — | ✅ | BOOLEAN | Hides parking slot details after booking confirmation in auto-allocation mode. |
| `isAmenitiesFilter` | — | ✅ | BOOLEAN | Enables amenities feature. |
| `isAppFeedbackEnabled` | — | ✅ | BOOLEAN | Enables app feedback feature. |
| `isAutoAbsentEnabled` | — | ✅ | BOOLEAN | Enables auto-absent functionality. |
| `isAutoEntryAllowed` | — | ✅ | BOOLEAN | Automatically switches to next DigiPass scan mode after first scan. |
| `isAutoLogoutEnabled` | — | ✅ | BOOLEAN | This is a dummy property and should not be updated |
| `isCheckinNotificationEnabled` | — | ✅ | BOOLEAN | Enables notification after successful check-in. |
| `isCustomShiftsRestricted` | — | ✅ | BOOLEAN | TO BE STRICTLY UPDATED ONLY FROM CONFIGURATION PAGE. Defines if the selection of custom shift would be allowed or not. |
| `isDynamicFieldsMandatory` | — | ✅ | BOOLEAN | Defines if dynamic fields is mandatory. |
| `isPhoneValidationOptional` | — | ✅ | BOOLEAN | Controls whether phone number is optional or mandatory during first-time employee registration. |
| `isSeatValidationEnabled` | — | ✅ | BOOLEAN | Prevents overlapping bookings on the same seat and enables floor view. |
| `isSeatValidationEnabledOnQrScan` | — | ✅ | BOOLEAN | Not in use. |
| `isShiftPairingEnabled` | — | ✅ | BOOLEAN | Defines the enablement of shift pairs. |
| `limitEmployeeBookingDays` | — | ✅ | BOOLEAN | Enables active booking limit for users. |
| `limitEmployeeBookingDaysType` | — | ✅ | STRING | Defines booking limit type (weekly/monthly). |
| `limitEmployeeBookingDaysUnit` | — | ✅ | DOUBLE | Defines maximum active bookings per user. |
| `limitMealDuringBookingCreation` | — | ✅ | BOOLEAN | Restricts meal booking to one per day across desk and room bookings. |
| `lockerBookingEnabled` | — | ✅ | BOOLEAN | Update Desk/Office labels to Locker based on this configuration. |
| `mandatoryBookingRequiredForCounterScan` | — | ✅ | BOOLEAN | Ensures only users with an active meal booking can scan the counter QR code to consume a meal, preventing scans without bookings. |
| `maxBufferForCheckin` | — | ✅ | DOUBLE | Not in use. |
| `maxHoursAllowedForCheckin` | — | ✅ | DOUBLE | Not in use. |
| `maxTimeAfterClockin` | — | ✅ | BOOLEAN | Not in use. |
| `maxTimeBeforeClockin` | — | ✅ | BOOLEAN | Not in use. |
| `mealCancelCutoffInMinutes` | — | ✅ | INTEGER | Property to enable/disable booking cancellation option if created with meal and 'enableSeparateMealOption' is enabled. |
| `mealFinalStage` | — | ✅ | LIST | Defines the final status of a meal booking. |
| `mealPlanningEnabled` | — | ✅ | BOOLEAN | Enables meal booking across all the flows |
| `minHoursAllowedForCheckin` | — | ✅ | DOUBLE | Not in use. |
| `minShiftDuration` | — | ✅ | DOUBLE | Defines minimum allowed shift duration in hours. |
| `mobileNumberLength` | — | ✅ | INTEGER | Defines required mobile number length. |
| `newRoomParticipantWorkflow` | — | ✅ | BOOLEAN | Determines whether participant addition should be allowed in the new room booking flow. |
| `noResourceBookingConfirmation` | — | ✅ | BOOLEAN | Defines if there is no resource then the popup to confirm booking without resource should be displayed or not. |
| `numOfDays` | — | ✅ | INTEGER | Defines maximum days in advance for desk booking. |
| `officeCheckInModeApp` | — | ✅ | STRING | Configures office check-in mechanism on app. |
| `officeCheckInModeWeb` | — | ✅ | STRING | Configures office check-in mechanism on web. |
| `onCallMaxShiftDurationInMinute` | — | ✅ | INTEGER | - |
| `onCallMinShiftDurationInMinute` | — | ✅ | INTEGER | - |
| `otpOverIvrForVisitor` | — | ✅ | BOOLEAN | Triggers OTP delivery to visitors via IVR call. |
| `overlappingTimeInMinutes` | — | ✅ | INTEGER | Defines allowed overlap duration for desk bookings. |
| `overrideMinMaxShiftDurations` | — | ✅ | JSON | Overrides minShiftDuration and maxShiftDuration configurations for bookings created from Workplanner and Booking Bulk Upload. |
| `parkingSlotBufferTimeInMin` | — | ✅ | INTEGER | Defines parking booking buffer time. |
| `pendingRequestsNotificationEnabled` | — | ✅ | BOOLEAN | Allow notification to users regarding pending booking requests that need action |
| `recordCheckInOutViaAccessCardAPI` | — | ✅ | BOOLEAN | Records multiple daily check-ins/check-outs via access card API. |
| `rejectedRequestNotificationEnabled` | — | ✅ | BOOLEAN | Enables notification when booking requests are rejected. |
| `remoteSignInAllowed` | — | ✅ | BOOLEAN | Enables remote sign-in via Scan QR. |
| `removeMealSelectionOnHolidayAndWeeklyOff` | — | ✅ | BOOLEAN | Removes meal selection on holidays and weekly offs. |
| `requestorPersonaEmails` | — | ✅ | JSON | For approval flow email. |
| `resourceApprovalsPage` | — | ✅ | BOOLEAN | Resource approval page. |
| `resourceApprovalsPageApp` | — | ✅ | BOOLEAN | Enables resource approval page. |
| `resourceRequestsPage` | — | ✅ | BOOLEAN | Resource request page for approval. |
| `resourceRequestsPageApp` | — | ✅ | BOOLEAN | Enabling meeting room approval module on mobile |
| `restrictMealSelectionTo` | — | ✅ | INTEGER | Specifies the maximum number of meal items a user is allowed to select. Users can choose up to restrictMealSelectionTo items; they cannot select more. If 0, user can select unlimited items. |
| `restrictScanQROnFabButton` | — | ✅ | BOOLEAN | When enabled (default false), restricts that the check-in mode on an office level also needs to be ScanQR. If disabled, any QR code can be scanned regardless of the office check-in mode. |
| `roomMaintenanceMessage` | — | ✅ | STRING | Controls the message displayed after the maintenance message, to allow admins to give further instructions for maintenance related messages. |
| `roomMaintenanceWorkflow` | — | ✅ | BOOLEAN | Property for enabling and disabling the room maintenance flow. |
| `seatScanEnable` | — | ✅ | BOOLEAN | Enables seat QR scanning on booking page. |
| `selectShiftsAfterSpecificTime` | — | ✅ | DOUBLE | Defines time threshold after which shift bookings can be created. |
| `setFavoriteRooms` | — | ✅ | BOOLEAN | Allows user to set any meeting room as their favourite for easy access. |
| `shouldAllowCustomTimingWhileEdit` | — | ✅ | BOOLEAN | STRICTLY TO BE UPDATED ONLY FROM CONFIG PAGE IN THE UI. Defines if employee will be allowed to select custom timing while editing a booking. |
| `showCabs` | — | ✅ | BOOLEAN | Enables transport toggle on booking form. |
| `showDigipassOptionForDedicatedSeat` | — | ✅ | BOOLEAN | Enables DigiPass option in the mobile app side navigation. |
| `showFirstCheckInRecord` | — | ✅ | BOOLEAN | Honors only the first check-in record across the system for SFTP Access Card integrations. |
| `showMealOrderStatus` | — | ✅ | BOOLEAN | Displays vendor-set meal order status on booking card. |
| `showParking` | — | ✅ | BOOLEAN | Controls parking field visibility in Teams chatbot. |
| `showQRScanner` | — | ✅ | BOOLEAN | Enables Scan QR option in the app. |
| `showSanitizationDetails` | — | ✅ | BOOLEAN | Displays sanitization details in the app. |
| `showVaccinationOptionInSideMenu` | — | ✅ | BOOLEAN | Enables Vaccination Status option in the app side menu. |
| `spocCancelCutOff` | — | ✅ | INTEGER | Defines advance hours required for SPOC to cancel bookings. |
| `spocScheduleCutOff` | — | ✅ | INTEGER | Defines advance hours required for SPOC to create bookings. |
| `teamCalendarEnabled` | — | ✅ | BOOLEAN | Enables Team Calendar feature. |
| `TestPropertyOnPMS` | — | ✅ | BOOLEAN | Test property to verify the PMS movement |
| `timeDiffShiftsMin` | — | ✅ | DOUBLE | Defines minimum time difference between paired shifts. |
| `vaccinationMaxApprovalDays` | — | ✅ | INTEGER | Defines maximum days allowed for vaccination request approval. |
| `vendorColumnMappings` | — | ✅ | JSON | To customize the column header labels in the Meal Dashboard. |
| `vendorMealDisplayColumn` | — | ✅ | LIST | Tells which columns need to be shown on vendor-dashboard (only related to meal columns). |
| `vendorMealStatus` | — | ✅ | LIST | Types of meal statuses defined per office. |
| `waitlistExpiryEnabled` | — | ✅ | BOOLEAN | Expire waitlist bookings once the start time has passed and no confirmed slot has been assigned to the parking booking. |
| `wfhCancelCutOff` | — | ✅ | INTEGER | Defines cancellation cutoff time for remote bookings. |
| `wfhClockinBuffer` | — | ✅ | DOUBLE | Buffer duration to checkin to remote bookings |
| `wfhClockInBuffer` | — | ✅ | INTEGER | ⚠️ undocumented |
| `wfhDisabled` | — | ✅ | BOOLEAN | Enables or disables WFH/remote booking feature. |
| `wfhEditCutOff` | — | ✅ | INTEGER | Defines cutoff for editing WFH bookings. |
| `wfhMaxDurationForBooking` | — | ✅ | DOUBLE | Defines maximum duration for WFH booking. |
| `wfhMaxShiftDurationInMinute` | — | ✅ | INTEGER | Defines maximum shift duration for remote bookings. |
| `wfhMinBetweenClockinClockout` | — | ✅ | DOUBLE | Enabling buffer duration between checkin and checkout in remote bookings |
| `wfhMinDurationForBooking` | — | ✅ | DOUBLE | Defines minimum duration for WFH booking. |
| `wfhMinShiftDurationInMinute` | — | ✅ | INTEGER | Defines minimum shift duration for remote bookings. |
| `wfhMonthlyLimit` | — | ✅ | INTEGER | Defines monthly limit for remote/WFH bookings per user. |
| `wfhScheduleCutOff` | — | ✅ | INTEGER | Defines cutoff for scheduling WFH bookings. |
| `wfhSpocEditCutOff` | — | ✅ | INTEGER | Defines cutoff for SPOC to edit WFH bookings. |
| `wfhSpocSchecduleCutOff` | — | ✅ | INTEGER | Defines cutoff for SPOC to schedule WFH bookings. |
| `wfhWeeklyLimit` | — | ✅ | INTEGER | Defines weekly booking limit for remote bookings. |
| `workplannerNotificationControl` | — | ✅ | JSON | Controls the email flow of the workplanner. |

## .in-only Configs
_1 properties present on the `.in` server but absent from the `.com` config list._

- `wfhMonthlyLimit / wfhWeeklyLimit` — Caps the maximum number of WFH days an employee is allowed to request per week or month.

## .com-only Configs
_158 properties present on the `.com` server but absent from the `.in` config list._

- `allocationChangeCommunicationEnabled` — Sends notification when desk allocation changes.
- `allowBookingAfterSignOut` — Allows creation of a new booking after signing out of a previous booking.
- `allowedBookingForContainmentZone` — Allows booking even if employee is in containment zone.
- `allowedMealBookingPerEmployee` — Decides how many separate meal bookings the system should allow per user per day.
- `allowOfficeCheckInWithoutDesk` — Controls the separate checkin for office and desk checkin.
- `approvalFlowInInWfhEnabled` — Enabling booking approval flow for remote bookings
- `approvalFlowInWfoEnabled` — Enables WFO booking approval workflow.
- `approvedRequestNotificationEnabled` — Enables notification to users when booking requests are approved.
- `approverPersonaEmails` — Email notification list for sending approval requests for meeting room bookings
- `attendanceManagementDisabled` — Enables Attendance Dashboard on Admin Home.
- `autoApprovalConfig` — Config for auto approval.
- `autoApprovalTime` — Auto approval of resource.
- `autoCheckinEnableFloorKiosk` — Allow auto-checkin to the booking created from floor kiosk if the following logic stands true.
- `autoExpireBeforeNoOfdays` — configuration to autoexpire booking requests when approval not provided for bookings
- `autoExpireHour` — Action for Notifying users a booking is going to expire(office bookings)
- `autoRequestApprovalEnabled` — Automatically sends booking requests for approval.
- `autoSlotAllocate` — Enables auto-allocation of parking slots.
- `blockGenerateDigiPassOnSeatMandatory` — Blocks DigiPass check-in if seat is not selected in booking.
- `booker` — -
- `bookingApprovalEmailsEnabled` — Enables email notifications to approvers for booking approvals.
- `bookingEditCutOff` — Defines advance hours required to edit a booking.
- `bookingLogoutEditCutOff` — Defines logout edit cutoff restriction on web.
- `bookingPerDayEmp` — Defines maximum bookings allowed per employee per day.
- `bookingRequestApprovalFlowEnabled` — Enables the booking approval workflow.
- `buidsEnabledForPMS` — Default list containing all BUIDS present on PMS
- `cancelSchedulesEnabled` — Allow cancellation of transport schedules from bookings
- `checkInFirstPremise` — Consider checkin from the first premise of checkin - Office/Desk/Parking
- `checkInWithoutAarogyasetuValidation` — Allows check-in without Aarogya Setu validation (deprecated).
- `checkTransportCutoffForBookingEdit` — Applies transport cutoff rules during booking edits.
- `createBookingAfterSignedOut` — Allows users to create bookings after signing out.
- `createBookingWhenCheckinReceived` — Controls booking creation via access card check-in.
- `customPlannerViewEnabled` — Enabling updated Workplanner view(True by default)
- `CutOffTimeBetweenBookingsOnSeatInMinute` — Defines minimum time gap between bookings on same seat.
- `defaulBookingHoursIfExtCheckin` — Defines default booking duration when check-in is performed through an external channel.
- `defaultLogoutShiftMinutes` — Auto-populates checkout time based on configured duration.
- `defLogoutDuration` — Defines default logout duration from login.
- `defOnCallLogoutDurationInMinute` — -
- `defWfhLogoutDurationInMinute` — Defines default logout duration for WFH bookings.
- `deleteFutureSchedulesOnDeactivation` — Automatically cancels future bookings when profile is deactivated.
- `dynamicDataForDesk` — -
- `dynamicFieldNameOnBookingForm` — Dynamic fields name description.
- `emailBookingMessage` — -
- `emailsForApprovalFlowRequest` — Sends approval request email to approvers.
- `empHomepageTodaysAvailabilityCard` — Once enabled, the user must see the complete availability card; modules inside the card will be visible based on whether the respective module is enabled for the user's office.
- `employeeEndTimeBookingCutoff` — Defines cutoff for booking after end time.
- `employeeEndTimeScheduleCutoff` — Defines logout edit cutoff restriction on mobile.
- `employeeScheduleCutoff` — Defines advance hours required to create a booking.
- `enableBookingEmail` — Enables booking email notifications.
- `enableDynamicFields` — Defines if dynamic field is enabled.
- `enableIndoorNavigation` — Enables indoor navigation (wayfinding) feature.
- `enableMealConfigureKiosk` — To enable 'Configure Kiosk' button on meal dashboard.
- `enableMealOnlyBulkUpload` — ⚠️ undocumented
- `enableOfficeCheckInWithParkingCheckIn` — Clubs office and parking check-in together.
- `enableParkingAvailabilityWidgetWithoutBooking` — When the parking booking module is not enabled for the client, but they only want to consume the available slot numbers.
- `enablePriorityWiseAutoSlotAllocate` — When enabled, slot is assigned in priority order based on display order value.
- `enablePrivilegeOnApp` — To show resources while booking based on privilege.
- `enableRecurrenceOnTeamPlanner` — Enables repeat booking on Work Planner.
- `enableSeparateMealOption` — Enable meal-only booking (coupled with existing property to enable meals).
- `enableWeeklyOffBookings` — Allows bookings on weekly off days.
- `expiredRequestNotificationEnabled` — Enables notification when booking approval requests expire.
- `expiryNotificationCutOffInMinutes` — Notifying users a booking is going to expire(office bookings)
- `externalChannelCheckIn` — Configures external check-in modes such as Face ID or Access Card.
- `filterNoAvailableSeatInFloor` — Not in use.
- `floorKioskCheckInOutEmails` — Conditions to send check-in/checkout mail on, values should be of type [CHECKIN, CHECKOUT].
- `gatepassDelaycutoff` — Defines end time for DigiPass check-in button.
- `genericLabelForDesk` — Resource name label to replace Desk keyword on all employee and admin pages.
- `hideParkingSlotInfo` — Hides parking slot details after booking confirmation in auto-allocation mode.
- `isAmenitiesFilter` — Enables amenities feature.
- `isAppFeedbackEnabled` — Enables app feedback feature.
- `isAutoAbsentEnabled` — Enables auto-absent functionality.
- `isAutoEntryAllowed` — Automatically switches to next DigiPass scan mode after first scan.
- `isAutoLogoutEnabled` — This is a dummy property and should not be updated
- `isCheckinNotificationEnabled` — Enables notification after successful check-in.
- `isCustomShiftsRestricted` — TO BE STRICTLY UPDATED ONLY FROM CONFIGURATION PAGE. Defines if the selection of custom shift would be allowed or not.
- `isDynamicFieldsMandatory` — Defines if dynamic fields is mandatory.
- `isPhoneValidationOptional` — Controls whether phone number is optional or mandatory during first-time employee registration.
- `isSeatValidationEnabled` — Prevents overlapping bookings on the same seat and enables floor view.
- `isSeatValidationEnabledOnQrScan` — Not in use.
- `isShiftPairingEnabled` — Defines the enablement of shift pairs.
- `limitEmployeeBookingDays` — Enables active booking limit for users.
- `limitEmployeeBookingDaysType` — Defines booking limit type (weekly/monthly).
- `limitEmployeeBookingDaysUnit` — Defines maximum active bookings per user.
- `limitMealDuringBookingCreation` — Restricts meal booking to one per day across desk and room bookings.
- `lockerBookingEnabled` — Update Desk/Office labels to Locker based on this configuration.
- `mandatoryBookingRequiredForCounterScan` — Ensures only users with an active meal booking can scan the counter QR code to consume a meal, preventing scans without bookings.
- `maxBufferForCheckin` — Not in use.
- `maxHoursAllowedForCheckin` — Not in use.
- `maxTimeAfterClockin` — Not in use.
- `maxTimeBeforeClockin` — Not in use.
- `mealCancelCutoffInMinutes` — Property to enable/disable booking cancellation option if created with meal and 'enableSeparateMealOption' is enabled.
- `mealFinalStage` — Defines the final status of a meal booking.
- `mealPlanningEnabled` — Enables meal booking across all the flows
- `minHoursAllowedForCheckin` — Not in use.
- `minShiftDuration` — Defines minimum allowed shift duration in hours.
- `mobileNumberLength` — Defines required mobile number length.
- `newRoomParticipantWorkflow` — Determines whether participant addition should be allowed in the new room booking flow.
- `noResourceBookingConfirmation` — Defines if there is no resource then the popup to confirm booking without resource should be displayed or not.
- `numOfDays` — Defines maximum days in advance for desk booking.
- `officeCheckInModeApp` — Configures office check-in mechanism on app.
- `officeCheckInModeWeb` — Configures office check-in mechanism on web.
- `onCallMaxShiftDurationInMinute` — -
- `onCallMinShiftDurationInMinute` — -
- `otpOverIvrForVisitor` — Triggers OTP delivery to visitors via IVR call.
- `overlappingTimeInMinutes` — Defines allowed overlap duration for desk bookings.
- `overrideMinMaxShiftDurations` — Overrides minShiftDuration and maxShiftDuration configurations for bookings created from Workplanner and Booking Bulk Upload.
- `parkingSlotBufferTimeInMin` — Defines parking booking buffer time.
- `pendingRequestsNotificationEnabled` — Allow notification to users regarding pending booking requests that need action
- `recordCheckInOutViaAccessCardAPI` — Records multiple daily check-ins/check-outs via access card API.
- `rejectedRequestNotificationEnabled` — Enables notification when booking requests are rejected.
- `remoteSignInAllowed` — Enables remote sign-in via Scan QR.
- `removeMealSelectionOnHolidayAndWeeklyOff` — Removes meal selection on holidays and weekly offs.
- `requestorPersonaEmails` — For approval flow email.
- `resourceApprovalsPage` — Resource approval page.
- `resourceApprovalsPageApp` — Enables resource approval page.
- `resourceRequestsPage` — Resource request page for approval.
- `resourceRequestsPageApp` — Enabling meeting room approval module on mobile
- `restrictMealSelectionTo` — Specifies the maximum number of meal items a user is allowed to select. Users can choose up to restrictMealSelectionTo items; they cannot select more. If 0, user can select unlimited items.
- `restrictScanQROnFabButton` — When enabled (default false), restricts that the check-in mode on an office level also needs to be ScanQR. If disabled, any QR code can be scanned regardless of the office check-in mode.
- `roomMaintenanceMessage` — Controls the message displayed after the maintenance message, to allow admins to give further instructions for maintenance related messages.
- `roomMaintenanceWorkflow` — Property for enabling and disabling the room maintenance flow.
- `seatScanEnable` — Enables seat QR scanning on booking page.
- `selectShiftsAfterSpecificTime` — Defines time threshold after which shift bookings can be created.
- `setFavoriteRooms` — Allows user to set any meeting room as their favourite for easy access.
- `shouldAllowCustomTimingWhileEdit` — STRICTLY TO BE UPDATED ONLY FROM CONFIG PAGE IN THE UI. Defines if employee will be allowed to select custom timing while editing a booking.
- `showCabs` — Enables transport toggle on booking form.
- `showDigipassOptionForDedicatedSeat` — Enables DigiPass option in the mobile app side navigation.
- `showFirstCheckInRecord` — Honors only the first check-in record across the system for SFTP Access Card integrations.
- `showMealOrderStatus` — Displays vendor-set meal order status on booking card.
- `showParking` — Controls parking field visibility in Teams chatbot.
- `showQRScanner` — Enables Scan QR option in the app.
- `showSanitizationDetails` — Displays sanitization details in the app.
- `showVaccinationOptionInSideMenu` — Enables Vaccination Status option in the app side menu.
- `spocCancelCutOff` — Defines advance hours required for SPOC to cancel bookings.
- `spocScheduleCutOff` — Defines advance hours required for SPOC to create bookings.
- `teamCalendarEnabled` — Enables Team Calendar feature.
- `TestPropertyOnPMS` — Test property to verify the PMS movement
- `timeDiffShiftsMin` — Defines minimum time difference between paired shifts.
- `vaccinationMaxApprovalDays` — Defines maximum days allowed for vaccination request approval.
- `vendorColumnMappings` — To customize the column header labels in the Meal Dashboard.
- `vendorMealDisplayColumn` — Tells which columns need to be shown on vendor-dashboard (only related to meal columns).
- `vendorMealStatus` — Types of meal statuses defined per office.
- `waitlistExpiryEnabled` — Expire waitlist bookings once the start time has passed and no confirmed slot has been assigned to the parking booking.
- `wfhCancelCutOff` — Defines cancellation cutoff time for remote bookings.
- `wfhClockinBuffer` — Buffer duration to checkin to remote bookings
- `wfhClockInBuffer` — ⚠️ undocumented
- `wfhDisabled` — Enables or disables WFH/remote booking feature.
- `wfhEditCutOff` — Defines cutoff for editing WFH bookings.
- `wfhMaxDurationForBooking` — Defines maximum duration for WFH booking.
- `wfhMaxShiftDurationInMinute` — Defines maximum shift duration for remote bookings.
- `wfhMinBetweenClockinClockout` — Enabling buffer duration between checkin and checkout in remote bookings
- `wfhMinDurationForBooking` — Defines minimum duration for WFH booking.
- `wfhMinShiftDurationInMinute` — Defines minimum shift duration for remote bookings.
- `wfhMonthlyLimit` — Defines monthly limit for remote/WFH bookings per user.
- `wfhScheduleCutOff` — Defines cutoff for scheduling WFH bookings.
- `wfhSpocEditCutOff` — Defines cutoff for SPOC to edit WFH bookings.
- `wfhSpocSchecduleCutOff` — Defines cutoff for SPOC to schedule WFH bookings.
- `wfhWeeklyLimit` — Defines weekly booking limit for remote bookings.
- `workplannerNotificationControl` — Controls the email flow of the workplanner.

## Missing Descriptions
_2 properties have no description in any source (PMS config files, PMS Description Cleaned, or wis_unique_configs)._
Contact the owning service team for documentation.

- `enableMealOnlyBulkUpload`
- `wfhClockInBuffer`

_Last updated: 2026-05-26_
_Source: [[sources/pms-configs-in-all-wis-configs]] | [[sources/pms-configs-com-wis-service-configs]]_
