---
title: "Emp Exp Common Config — Config Properties"
service: EMP-EXP-COMMON-CONFIG
total_configs: 408
servers: [in, com]
generated: 2026-06-09
type: config
module: employee-experience
---

# Emp Exp Common Config — Config Properties

Auto-generated on 2026-06-09. Total configs: **408**.

| Property | Description | Type | Default | Server |
|----------|-------------|------|---------|--------|
| `ACCESS_MATRIX_ENABLED_BUIDS` | Defines BUs with access matrix enabled. | LIST |  | both |
| `ADDRESS_CHANGE_HOME_TO_OFFICE_DISTANCE_VALIDATION` | - | STRING |  | both |
| `ADDRESS_CHANGE_RADIAL_DISTANCE_VALIDATION` | - | STRING |  | both |
| `ADDRESS_CHANGE_RESTRICTED_AREA_VALIDATION` | - | STRING |  | both |
| `ADDRESS_CHANGE_TRANSPORT_BOUNDARY_VALIDATION` | - | STRING |  | both |
| `adminAssignmentFloorPlanUrl` | Defines Admin Seat Allocation Floor Plan URL. | STRING |  | both |
| `adminexpUi` | Defines alternate Admin UI URL. | STRING |  | both |
| `adminExpUi` |  |  |  | .in only |
| `adminexpUI` | Defines Admin Experience UI URL. | STRING |  | both |
| `adminFloorPlanUrl` | Defines Admin Floor Plan URL. | STRING |  | both |
| `airtelBuid` | - | STRING |  | both |
| `allowBookingConversionFromWfhToWfo` | Enables direct WFH to WFO booking conversion. | BOOLEAN |  | both |
| `allowBookingConversionFromWfoToWfh` | Enables direct WFO to WFH booking conversion. | BOOLEAN |  | both |
| `allowBookingForOthers` | Defines booking types allowed for others. | LIST |  | both |
| `allowBookingWithDedicatedSeat` | Controls whether dedicated seat holders can book other desks. | LIST |  | .com only |
| `allowCheckInAtIncorrectSlot` | Allows check-in outside booked slot. | BOOLEAN |  | both |
| `allowedEmployeeNameRegex` | Defines the allowed employee name format using regex validation. | STRING |  | both |
| `allowEmployeeToBooKAnySeatInBL` | Allows employees to book seats within permitted hierarchy levels in BL. | BOOLEAN |  | both |
| `allowPastAllocationTimesForCurrentDayFor` | Allows admins to allocate desks/slots/rooms for past shift times on the same day. | LIST |  | both |
| `allowPeerOrMarshalReporting` | - | BOOLEAN |  | both |
| `allowQrCheckInWithoutSeat` | Allows QR check-in without seat. | BOOLEAN |  | both |
| `allowRoomBookingWithOfficeBooking` | Controls visibility of Room booking option on Employee Home. | BOOLEAN |  | both |
| `APPROVAL_POST_NO_SHOW_CHECK_BUFFER` | - | DOUBLE |  | both |
| `approvalFlowEnabled` | Enables Team Manager approval dashboard. | BOOLEAN |  | both |
| `approvalFlowInInWfhEnabled` | Enables approval workflow for WFH. | BOOLEAN |  | .com only |
| `approvalFlowInWfoEnabled` | Enables approval workflow for WFO. | BOOLEAN |  | .com only |
| `approvalWebViewUrl` | Defines approval web view URL. | STRING |  | both |
| `autoAllocate` | Enables automatic desk allocation during bulk booking upload. | BOOLEAN |  | both |
| `autoClockOutRemainder` | Sends reminder notification before auto-checkout triggers. | BOOLEAN |  | both |
| `autoClockOutRemainderMinutes` | Defines minutes before logout when reminder notification is triggered. | DOUBLE |  | both |
| `autoLogoutEnabled` | Enables automatic sign-out after configured duration. | BOOLEAN |  | both |
| `autoLogoutMinutes` | Defines minutes after planned checkout for auto-checkout trigger. | DOUBLE |  | both |
| `autoPopulateBookingForm` | Auto-populates booking form using preferences or past data. | BOOLEAN |  | both |
| `autoPopulateSchedulingForm` | autoPopulateSchedulingForm | BOOLEAN |  | .com only |
| `autoProvisionEnabled` | Automatically marks all employees as onboarded during bulk onboarding. | BOOLEAN |  | both |
| `autoRejectionForOptIn` | - | BOOLEAN |  | .com only |
| `autoSeatCheckOutEnabled` | Enables auto seat checkout. | BOOLEAN |  | both |
| `autoSeatCheckOutMinutes` | Defines auto seat checkout duration. | DOUBLE |  | both |
| `autoSlotAllocate` | Automatically allocates parking slots without manual slot selection. | BOOLEAN |  | both |
| `autoTagAssignmentMapping` | Automatically assigns tags based on employee designation. | JSON |  | both |
| `averageOverallTripFeedbackCalculation` | - | BOOLEAN |  | both |
| `bannerEndTime` | - | STRING |  | both |
| `bannerNativeRoomEmail` | Controls native banner visibility in room emails. | BOOLEAN |  | both |
| `bannerNewRoomBookingEmpHome` | Defines banner text for New Room booking page. | STRING |  | both |
| `bannerStartTime` | - | STRING |  | both |
| `blockChecinOutsideGeofence` | - | BOOLEAN |  | .com only |
| `blockDelegationEmail` | Blocks delegation email notifications. | BOOLEAN |  | both |
| `blockGenerateDigiPassOnSeatMandatory` | Blocks DigiPass generation when seat is mandatory. | BOOLEAN |  | both |
| `blockNumber` | Controls Block number field visibility. | STRING |  | both |
| `blockOfficeCheckingIfNoBooking` | Blocks office check-in without booking. | BOOLEAN |  | both |
| `blockUserIfNotVaccinated` | Blocks non-vaccinated users from making bookings when enabled. | BOOLEAN |  | both |
| `BOOKING_AGGREGATES_MIGRATION_BUIDS` | List of buids that requires migration of booking aggregates. | LIST |  | .com only |
| `BOOKING_AGGREGATES_MIGRATION_DELAY_SECONDS` | Time delay between migration of buids in booking aggregates. | INTEGER |  | .com only |
| `BOOKING_AGGREGATES_MIGRATION_ENABLED` | Checks if migration is enabled for booking aggregates. | BOOLEAN |  | .com only |
| `BOOKING_AGGREGATES_MIGRATION_TIMEZONES` | - | LIST |  | .com only |
| `BOOKING_HISTORY` | Enables booking history option on web. | BOOLEAN |  | both |
| `bookingCancellationReasons` | Defines cancellation reason list. | LIST |  | both |
| `bookingConversionCutOff` | Defines cutoff time for WFH to WFO and vice versa conversion. | DOUBLE |  | both |
| `bookingCreationMessage` | Defines booking success message. | STRING |  | .com only |
| `bookingDisclaimers` | Configures booking disclaimer messages. | JSON |  | .com only |
| `bookingEnabledOnTag` | Enables booking based on tags. | BOOLEAN |  | both |
| `bookingRequestApprovalFlowEnabled` | Enables booking approval workflow. | BOOLEAN |  | both |
| `bookingRuleEngine` | Defines Booking Rule Engine URL. | STRING |  | both |
| `bookingsTypesForCheckinReminder` | Defines booking types eligible for check-in reminder. | LIST |  | both |
| `bufferTimeInSecondsOfAarogyaSetuUser` | - | DOUBLE |  | both |
| `bulkScheduleAllowedDaysForRoom` | Defines bulk room scheduling window. | DOUBLE |  | both |
| `cacheTimeInHoursOfAarogyaSetuUserStatus` | Defines Aarogya Setu status cache duration. | DOUBLE |  | both |
| `CANCELLATION_REMINDER_NOTIFICATION` | Enables cancellation reminder notifications. | BOOLEAN |  | both |
| `cancelTransportBooking` | Allows transport booking cancellation. | BOOLEAN |  | both |
| `captureEmployeeBookingStats` | Enables booking statistics capture. | BOOLEAN |  | both |
| `cardSyncDefaultMinutes` |  |  |  | .in only |
| `checkInBookingsType` | Defines booking types eligible for check-in. | LIST |  | .com only |
| `checkInByTimeChip` | True - Show the check-in-by chip and chevron to provide users with detailed check-in times. False - Do not show the check-in-by chip or the chevron on booking cards. | BOOLEAN |  | .com only |
| `checkinReminderCutoffInMinute` | Defines when check-in reminder notification is sent. | DOUBLE |  | both |
| `checkInWithoutAarogyasetuValidation` | Allows check-in without Aarogya Setu validation. | BOOLEAN |  | both |
| `CITY_DISTRICT_MAPPINGS` | - | JSON |  | both |
| `commentsMandatoryOnRating` | - | DOUBLE |  | both |
| `commuteMandatory` | Requires users to select either parking or transport while creating an office booking to prevent resource-less bookings. | BOOLEAN |  | both |
| `confirmationMessageForLogoutTracking` | - | STRING |  | both |
| `consentPopupData` | Defines consent popup configuration. | LIST |  | both |
| `contactTHDReasons` | - | LIST |  | both |
| `createSeatBookingWithOfficeBooking` | Auto-creates seat booking with office booking. | BOOLEAN |  | .com only |
| `crossHierarchyAllocationEnabled` | Defines if cross hierarchy allocation is allowed for RBAC enabled sites. | BOOLEAN |  | .com only |
| `crossTeamAllocationEnabled` | Allows cross-team desk and employee allocation. | BOOLEAN |  | .com only |
| `CutOffTimeBetweenBookingsOnSeatInMinute` | Defines minimum gap between consecutive bookings on the same seat. | DOUBLE |  | both |
| `cutoffTimeBetweenWISAppFeedback` | Defines minimum time gap between feedback prompts. | JSON |  | both |
| `cutoffTimeForSkipWISAppFeedback` | Defines interval in hours for app feedback display frequency. | DOUBLE |  | both |
| `DATE_FORMAT` | Defines date format for UI. | STRING |  | both |
| `DATE_FORMAT_SERVICES` | Defines date format for backend services. | STRING |  | both |
| `defaultLogoutShiftMinutes` | Auto-populates checkout time based on configured duration after check-in selection. | DOUBLE |  | both |
| `delegatorDelegateeEmailsEnabled` | Sends email notification to delegator. | BOOLEAN |  | both |
| `directCheckinEndCutOffInMinute` | Defines end cutoff for direct check-in. | DOUBLE |  | both |
| `directCheckinExpiryInMinute` | Defines expiry time for direct check-in. | DOUBLE |  | both |
| `directCheckinStartCutOffInMinute` | Defines start cutoff for direct check-in. | DOUBLE |  | both |
| `DIRECTION` | - | STRING |  | both |
| `editProfileEnabled` | Controls profile editing. | BOOLEAN |  | .com only |
| `email` | Controls whether the Email field is shown or hidden during employee profile validation. | STRING |  | both |
| `empExp` | Defines primary Employee Experience URL. | STRING |  | both |
| `empExpUi` | Defines Employee Experience UI URL. | STRING |  | both |
| `empexpUI` | Defines Employee Experience interface URL. | STRING |  | both |
| `empHomepageTodaysAvailabilityCard` | Displays full availability card on Employee Home based on enabled modules. | BOOLEAN |  | .com only |
| `empHomeWidgetMeetingRoomCheckInCutOff` | Defines check-in cutoff for meeting room check-in from Employee Home widget. | INTEGER |  | .com only |
| `empID` | Controls whether the Employee ID field is shown or hidden during employee profile validation. | STRING |  | both |
| `employeeFloorPlanUrl` | Defines Employee Floor Plan URL. | STRING |  | both |
| `employeePIIMasking` | Configures selective masking of PII fields and visual security settings. | LIST |  | both |
| `employeeStatusModuleEnabled` | - | BOOLEAN |  | both |
| `ENABLE_CHECKIN_NOTIFICATION` | Master switch to enable check-in notifications. | BOOLEAN |  | both |
| `ENABLE_INDOOR_NAVIGATION` | Enables wayfinding/navigation to desks. | BOOLEAN |  | .com only |
| `enableAutoAbsentNotification` | Sends notification when a booking results in no-show. | BOOLEAN |  | both |
| `enableBookingCancellationReasonsFor` | Requires cancellation reason for specified booking types. | LIST |  | both |
| `enableBookingEmail` | Enables booking details email notification. | BOOLEAN |  | both |
| `enableCarbonFootprintTrackingInParking` | Tracks and displays carbon footprint for employee commutes. | BOOLEAN |  | both |
| `enableCheckInForMeetingRoomEmpHome` | Displays the check-in button on the 'Today's Meeting' widget for old room types and allows check-in from Employee Home. | BOOLEAN |  | .com only |
| `enableColorInParkingVehicleCreation` | Adds vehicle color input field in parking vehicle creation. | BOOLEAN |  | both |
| `enabledCheckInEmailBodyParam` | Defines enabled parameters in check-in email body. | LIST |  | both |
| `enabledCheckInEmailBodyParamNames` | Defines parameter names in check-in email body. | LIST |  | both |
| `enableDelegationForAdmins` | Allows admins to manage delegation. | BOOLEAN |  | both |
| `enableDynamicFields` | Enables configurable dynamic fields per BU. | BOOLEAN |  | both |
| `enableEmployeePreferences` | Enables employee preference settings on web. | BOOLEAN |  | both |
| `enableEmployeeRFIDColumn` | Enables RFID number field and prevents duplicates. | BOOLEAN |  | both |
| `enableFloorPlanAccessibility` | Enables accessibility features for visually impaired users. | BOOLEAN |  | both |
| `enableGeofenceCheckFor` | Enables GPS/geofence validation for specified workflows. | LIST |  | both |
| `enableGeofenceCheckForCheckin` | Enforces check-in validation within defined geofence limits. | BOOLEAN |  | both |
| `enableGridFloorPlan` | Enables grid-based parking floor plan. | BOOLEAN |  | both |
| `enableJoinAllWaitlist` | Allows joining waitlists across all parking levels. | BOOLEAN |  | both |
| `enableMealCartView` | Activates meal cart and payment flow when enabled with showMealPaymentCTA. | BOOLEAN |  | both |
| `enableMealDayWiseAvailability` | Allows admin to configure meal availability per day. | BOOLEAN |  | .com only |
| `enableMealImageIn` | To show meal image in meal item. | LIST |  | both |
| `enableMultiAllocation` | Controls desk multi-allocation functionality and displays the Multi-allocated Desk legend entry on floor plans when value includes 'DESK'. | LIST |  | both |
| `enableMultiMealSelect` | Enables multi selection on meal booking. | BOOLEAN |  | .com only |
| `enableNewAdminDashboard` | Enables Admin Dashboard 2.0. | BOOLEAN |  | both |
| `enableNewAllocationFlow` | Enables new allocation flow required for time-based allocation. | BOOLEAN |  | both |
| `EnableNewEmailTemplate` | Enables new email template format. | BOOLEAN |  | both |
| `enableOfficeCheckInWithParkingCheckIn` | Links office check-in with parking check-in. | BOOLEAN |  | .com only |
| `enableParkingCheckOutWithOfficeCheckOut` | Links parking checkout with office checkout. | BOOLEAN |  | .com only |
| `enablePerpetualDigipassForAllUsers` | Allows DigiPass generation without office booking. | BOOLEAN |  | both |
| `enablePriorityWiseAutoSlotAllocate` | Assigns slots based on priority order defined by display order value. | BOOLEAN |  | .com only |
| `enableProjectCodeFor` | Enables Project Code field for specified booking types. | LIST |  | both |
| `enableProjectColor` | Enables enhanced seat and team color legends on floor plan. | BOOLEAN |  | both |
| `enableQRBasedRemoteSignin` | Enables QR-based remote sign-in. | BOOLEAN |  | both |
| `enableQRBasedSignOutButton` | Enables QR-based sign-out. | BOOLEAN |  | .com only |
| `enableSafeReachForBookingTypes` | Defines booking types eligible for Safe Reach. | LIST |  | both |
| `enableSafeReachWisList` | Defines environments where Safe Reach is enabled. | LIST |  | both |
| `enableStandardMealSelectionFlow` | Enables standard meal booking flow and overrides both normal chip and cart view. | BOOLEAN |  | .com only |
| `enableSuppportRequest` | - | BOOLEAN |  | .com only |
| `enableTeamAsResource` | Creates resource entry for newly created teams. | BOOLEAN |  | .com only |
| `enableTeamCalendarRMView` | Enables hierarchy filter on Team Calendar. | BOOLEAN |  | .com only |
| `enableTimeBasedDeskAllocation` | Enables time-based desk allocation and disables List View. | BOOLEAN |  | both |
| `enableTimezoneWithOfficeName` | Displays timezone with office name. | BOOLEAN |  | both |
| `enableTransportBookingBulkUpload` | - | BOOLEAN |  | both |
| `enableVisitorManagementOnApp` | Enables visitor management in app. | BOOLEAN |  | both |
| `enableWaitlistBooking` | Enables waitlist functionality in parking bookings. | BOOLEAN |  | both |
| `enableWisThemeColors` | Enables dynamic theming using wisThemeColors property. | BOOLEAN |  | .com only |
| `enforceReAuthentication` | Enables enforcement of re-authentication. | BOOLEAN |  | both |
| `enforceReAuthenticationDurationInMinutes` | Defines re-authentication validity duration in minutes. | DOUBLE |  | both |
| `excludeMealOnlyBookingsFromActiveBookingCount` | Decides whether to exclude meal booking from web/app/bulk from active booking count for any user. | BOOLEAN | false | .com only |
| `externalStaffUi` | Defines External Staff UI URL. | STRING |  | both |
| `fabDisplayNames` | Defines FAB display names. | LIST |  | both |
| `FEATURE_MEDICAL_EMERGENCY_EMAIL_RM` | - | BOOLEAN |  | .com only |
| `FEATURE_MEDICAL_EMERGENCY_EMAIL_TM` | - | BOOLEAN |  | .com only |
| `filterNoAvailableSeatInFloor` | Filters floors without available seats. | BOOLEAN |  | both |
| `floorKioskCheckinInfo` | Enables real-time desk check-in display on Floor Kiosk. | BOOLEAN |  | .com only |
| `floorKioskUrl` | Floor Kiosk URL. | STRING |  | .com only |
| `floorManagement` | Defines Floor Management URL. | STRING |  | both |
| `floorPlan` | Defines primary Floor Plan URL. | STRING |  | both |
| `Floorplan_Legend_Employee_Web_Expanded` | Controls expanded or collapsed legend state on employee web floor plan. | BOOLEAN |  | .com only |
| `floorPlanUI` | Defines Floor Plan UI URL. | STRING |  | both |
| `floorPlanViewMeetingRoomsWeb` | Enables floor plan view for meeting rooms on web. | BOOLEAN |  | .com only |
| `forecastingEfficiancy` | - | DOUBLE |  | both |
| `gatepassExpiryMinutes` | Defines DigiPass expiry duration after booking start. | INTEGER |  | .com only |
| `gender` | Controls whether the Gender field is shown or hidden during employee profile validation. | STRING |  | both |
| `generateGatepassAdvanceCutOff` | Defines minutes before booking start when DigiPass generation becomes active. | DOUBLE |  | .com only |
| `generateGatepassDelayCutOff` | Defines minutes after booking start when DigiPass generation is allowed. | DOUBLE |  | both |
| `genericLabelForDesk` | - | STRING |  | .com only |
| `hideBookingTimeMealOnly` | - | BOOLEAN |  | both |
| `hideScheduleButtonFromFab` | - | BOOLEAN |  | .com only |
| `hierarchy` | Defines organizational hierarchy levels. | LIST |  | both |
| `homeGeocode` | Controls whether the Home Geocode field is shown or hidden during employee profile validation. | STRING |  | both |
| `igonreErrorOfArrogyaSetu` | Ignores Aarogya Setu app status check errors. | BOOLEAN |  | both |
| `includeChildHierarchy` | Controls inclusion of child hierarchy levels. | BOOLEAN |  | both |
| `INDEMNIFICATION_REASONS` | Defines available indemnification reasons. | STRING |  | both |
| `industryStandard` | Controls industry standard values on Admin Dashboard metric cards. | JSON |  | both |
| `IPBasedCheckinEnabled` | Restricts web check-in based on IP address. | BOOLEAN |  | .com only |
| `IS_WIS_CALENDAR` | Enables the Native Rooms view on the Outlook Add-In and allows use of WIS Meeting Rooms with tags and allocations. | BOOLEAN |  | .com only |
| `isAmenitiesFilter` | Enables amenities filter in desk booking. | BOOLEAN |  | both |
| `isAppFeedbackEnabled` | Enables app feedback feature. | BOOLEAN |  | both |
| `isAutoAbsentEnabled` | Enables auto-absent feature and automatic seat release if check-in does not occur within cutoff. | BOOLEAN |  | both |
| `isAutoProvision` | - | BOOLEAN |  | both |
| `isBlSubblBuid` | Enables N-level hierarchy/Business Line feature for BU. | BOOLEAN |  | both |
| `isBuNudgeNotifEnabled` | Enables weekly nudge notifications for users without bookings. | BOOLEAN |  | both |
| `isCalendarInviteEnabled` | Enables calendar invite option. | BOOLEAN |  | both |
| `isCheckinNotificationEnabled` | Enables notification after successful check-in. | BOOLEAN |  | both |
| `isCheckInReminderOnMsTeamEnabled` | true |  |  | .in only |
| `isDelegationEnabled` | Master switch enabling Delegation feature. | BOOLEAN |  | both |
| `isDynamicFieldsMandatory` | Makes dynamic fields mandatory. | BOOLEAN |  | both |
| `isEmloyeeCreationForMsuEnabled` | Controls MSU employee creation. | BOOLEAN |  | .com only |
| `isEmployeeCreationEnabledForMSu` | Controls MSU employee creation feature. | BOOLEAN |  | .com only |
| `isGDPRCookiePolicyEnabled` | Displays GDPR compliance pop-up in mobile app. | BOOLEAN |  | both |
| `isMasterNudgeNotifEnabled` | Controls master nudge notifications. | BOOLEAN |  | both |
| `isPhoneValidationOptional` | Controls whether phone number is optional or mandatory during employee registration. | BOOLEAN |  | both |
| `isReportingAndAnalyticEnable` | - | BOOLEAN |  | both |
| `isSeatBookingAssignment` | Controls seat assignment feature. | BOOLEAN |  | both |
| `isShuttleRequired` | Replaces cab labels and icons with shuttle terminology across modules. | BOOLEAN |  | both |
| `isTripRatingMandatory` | Controls trip rating requirement. | BOOLEAN |  | .com only |
| `isWelcomeEmailEnabled` | - | BOOLEAN |  | .com only |
| `isZedaReleaseNoteEnabled` | Displays Zeda widget showcasing new features and feedback. | BOOLEAN |  | both |
| `jobTitleWiseCalenderInDays` | - | JSON |  | both |
| `landmark` | Controls visibility of Landmark field during registration. | STRING |  | both |
| `lastSwipeAsCheckoutTimeForBUID` | Uses the last swipe checkout time as final checkout instead of auto-checkout for access card integration clients. LIST of BUIDs for which this behavior is enabled. | LIST | not documented | both |
| `listOfEligibleBuidsForAutoClockout` | Defines BUs eligible for auto clock-out. | LIST |  | both |
| `listOfEligibleBuidsForBusNotification` | - | LIST |  | both |
| `listOfExcludedBuidsForCheckin` | Defines BUs excluded from check-in. | LIST |  | .com only |
| `liveSupportChatFeatureEnabled` | - | BOOLEAN |  | .com only |
| `madatoryFieldforScheduling` | - | LIST |  | both |
| `mappedShuttleRouteBufferInMinutes` | - | DOUBLE |  | .com only |
| `mapSchedulesToBooking` | Automatically maps schedules to matching bookings. | BOOLEAN |  | both |
| `maxEmployeeSelectionWorkplanner` | Defines maximum number of employees allowed for recurring bookings. | INTEGER |  | .com only |
| `maximumCharacterLimit` | - | DOUBLE |  | both |
| `maxTripLevelNonComplianceEventsAllowed` | - | INTEGER |  | both |
| `mealCutoffInMinutes` | Defines meal booking cutoff calculated from 00:00 of booked date. | DOUBLE | default not documented | both |
| `mealFeedbackEnabled` | Enables meal feedback feature and reporting. | BOOLEAN |  | both |
| `mealFeedbackOptions` | Configures meal feedback options. | JSON |  | .com only |
| `mealNotifications` | Enable e-mails related to meal bookings for QR. | BOOLEAN |  | .com only |
| `mealOnlyBulkBookingOptionalHeaders` | Optional headers. | LIST |  | .com only |
| `mealPlanningEnabled` | Enables meal booking via Work Planner. | BOOLEAN |  | both |
| `mealPlanningMandatory` | Makes meal selection mandatory in office booking form. | BOOLEAN |  | both |
| `medicalEmergencyRequest` | - | JSON |  | both |
| `meetingDetailsForDateUrl` | Defines Meeting Details by date URL. | STRING |  | both |
| `meetingOptionWebViewUrl` | Defines Meeting Room web view URL. | STRING |  | both |
| `meetingRoomKioskUrl` | Defines Meeting Room Kiosk URL. | STRING |  | both |
| `meetingRoomsWidgetEnabled` | Controls Meeting Rooms widget visibility. | BOOLEAN |  | .com only |
| `meetingRoomUrl` | Defines Meeting Room module URL. | STRING |  | both |
| `microBookingEnabled` | - | BOOLEAN |  | both |
| `mobile` | Controls whether the Mobile field is shown or hidden during employee profile validation. | STRING |  | both |
| `MOBILE_APP_BANNERS` | - | LIST |  | both |
| `mobileNumberLength` | Defines required mobile number length. | DOUBLE |  | both |
| `mobileSSOMandatory` | Removes the 'Continue with OTP' option on the mobile SSO login screen. | BOOLEAN |  | both |
| `mobilityHealthStatus` | Displays driver vaccination details on the Tracking page. | STRING |  | both |
| `multipleBookingsOnASeatInADayAllowed` | Allows multiple bookings on the same seat within a single day. | BOOLEAN |  | both |
| `multipleScanErrorMessage` | Defines error message for multiple scans. | STRING |  | both |
| `name` | Controls whether the Name field is shown or hidden during employee profile validation. | STRING |  | both |
| `nativeRoomEmail` | Displays room email ID input in new room workflow. | BOOLEAN |  | both |
| `nearByShuttleStopDistanceInMetre` | - | DOUBLE |  | .com only |
| `nextDayLogoutEnabled` | Controls visibility of next-day logout shifts in booking form. | BOOLEAN |  | .com only |
| `NO_SHOW_APPROVAL_ENABLED` | - | BOOLEAN |  | .com only |
| `NO_SHOW_COUNT_BANNER_ENABLED` | Controls no-show banner visibility. | BOOLEAN |  | both |
| `nodal` | Controls whether the Nodal Point field is shown or hidden during employee profile validation. | STRING |  | both |
| `noOfDaysAllowedInPlanner` | Defines allowed planning window. | DOUBLE |  | both |
| `notificationOnDeskRelease` | Controls desk release notifications. | BOOLEAN |  | .com only |
| `numberOfAllowedTrips` | Defines maximum trips per user. | DOUBLE |  | both |
| `office` | Controls whether the Office field is shown or hidden during employee profile validation. | STRING |  | both |
| `officeCheckInMode` | Configures office check-in mode for mobile. | STRING |  | both |
| `officeCheckInModeApp` | Configures office check-in mode for mobile app. | STRING |  | both |
| `officeCheckInModeWeb` | Configures office check-in mode for web. | STRING |  | both |
| `officeCheckInReminderEmailCtaEnabled` | Adds Check-in and Cancel CTAs in reminder emails. | BOOLEAN |  | .com only |
| `officeCheckInReminderEmailEnabled` | Controls office check-in reminder emails. | BOOLEAN |  | both |
| `onBehalfBookingEmailToCreatorEnabled` | Controls on-behalf booking email notification to creator. | BOOLEAN |  | both |
| `onlyParkingBookingEnabled` | Displays only the Parking booking option on Employee Home and FAB for clients using MoveInSync exclusively for parking. | BOOLEAN |  | both |
| `OPT_IN_APPROVAL_FLOW_ENABLED` | OPT_IN_APPROVAL_FLOW_ENABLED | BOOLEAN |  | .com only |
| `optInDeclarationConfig` | Declaration configurations for optin. | JSON |  | .com only |
| `optInDisplayText` | Defines commute opt-in/opt-out display text. | JSON |  | .com only |
| `optInOptionsEnabled` | - | LIST |  | .com only |
| `optInOutV3Declaration` | - | JSON |  | .com only |
| `optOutPendingEmailSubject` | - | STRING |  | .com only |
| `parkingAllocationUrl` | Defines Parking Allocation URL. | STRING |  | both |
| `parkingBookingMandatory` | Makes parking booking mandatory for office booking. | BOOLEAN |  | both |
| `parkingEnabled` | Enables parking option in the booking form. | BOOLEAN |  | both |
| `parkingEndCutOffInMinute` | Defines minutes after booking start when parking QR can be generated. | DOUBLE |  | both |
| `parkingExpiry` | Defines expiry time of generated parking QR. | DOUBLE |  | both |
| `parkingMailNotificationMinutes` | Defines parking email trigger minutes. | DOUBLE |  | both |
| `parkingReminderEmailEnabled` | Controls parking reminder emails. | BOOLEAN |  | both |
| `parkingReminderNotificationEnabled` | Controls parking reminder notifications. | BOOLEAN |  | .com only |
| `parkingReminderNotificationMinutes` | Defines parking reminder trigger minutes. | LIST |  | .com only |
| `parkingScheduleCutoff` | Defines advance booking window for parking. | DOUBLE |  | both |
| `parkingSlotBufferTimeInMin` | Defines parking allocation buffer time. | STRING |  | .com only |
| `parkingStartCutOffInMinute` | Defines minutes before booking start when parking QR can be generated. | DOUBLE |  | both |
| `pendingRequestsNotificationEnabled` | Controls pending request notifications. | BOOLEAN |  | both |
| `pinDisanceThresholdForShuttleStopApi` | - | DOUBLE |  | .com only |
| `PRE_TRIP_CANCELLATION_NOTIFICATION_MINUTES_BEFORE_LOGIN_CANCELLATION_CUTOFF` | - | INTEGER |  | both |
| `PRE_TRIP_CANCELLATION_NOTIFICATION_MINUTES_BEFORE_LOGOUT_CANCELLATION_CUTOFF` | - | INTEGER |  | both |
| `preferencesFloorPlanUrl` | Defines Preferences floor plan URL. | STRING |  | both |
| `Premise_Floorplan_Legend_Collapsed` | Collapses the legend by default on the Premises floor plan view. | BOOLEAN |  | .com only |
| `premiseUI` | Defines Premises management UI URL. | STRING |  | both |
| `profileRegistrationEmailSubject` | - | STRING |  | both |
| `projectCodeEnabledOnBooking` | Controls Project Code field visibility. | BOOLEAN |  | both |
| `projectCodeEnabledOnBookingMandatory` | Controls mandatory Project Code field. | BOOLEAN |  | both |
| `projectCodeMandatoryFor` | Makes Project Code field mandatory for specified booking types. | LIST |  | both |
| `promotionBannerUrl` | - | STRING |  | both |
| `promotionDisplayText` | - | STRING |  | both |
| `qRScannerEndCutOffInMinute` | Defines minutes after booking start when Scan QR becomes inactive. | DOUBLE |  | both |
| `qRScannerExpiry` | Defines expiry time of QR scanner after booking start. | DOUBLE |  | both |
| `qRScannerStartCutOffInMinute` | Defines minutes before booking start when Scan QR becomes active. | DOUBLE |  | both |
| `rbacDeskAllocationEnabled` | Enables RBAC-based desk allocation. | BOOLEAN |  | .com only |
| `reAuthenticationModeEmail` | Defines email-based two-step authentication mode. | BOOLEAN |  | both |
| `reAuthenticationModePhone` | Defines phone-based two-step authentication mode. | BOOLEAN |  | both |
| `recurrenceBookingEnabled` | Enables recurring booking feature. | BOOLEAN |  | both |
| `remoteSignCutoffInMinute` | Defines cutoff time for contactless bus solution sign-in. | DOUBLE |  | both |
| `remoteSignInAllowed` | Enables remote sign-in using Scan QR. | BOOLEAN |  | both |
| `remoteSignOutCutoffInMinute` | Defines cutoff time for remote sign-out. | INTEGER |  | both |
| `reportingAndAnalyticUrl` | Defines Reporting and Analytics dashboard URL. | STRING |  | both |
| `reportingService` | Defines Reporting service URL. | STRING |  | both |
| `REQUIRE_APPROVAL_FOR_OPT_OUT` | - | LIST |  | .com only |
| `restrictMealScanToOne` | Restricts meal QR scanning to once per meal window. | BOOLEAN |  | both |
| `restrictMultipleVisitorBookingCheckIn` | Restricts multiple visitor booking check-ins. | BOOLEAN |  | both |
| `roomAllocationEnabled` | Enables automatic room allocation. | BOOLEAN |  | both |
| `roomEmailIdEmailMessage` | Defines meeting room email message templates. | JSON |  | .com only |
| `runTransportOptOutJob` | Auto rejection/approval + schedule deletion for opted out users. | BOOLEAN |  | .com only |
| `safereach` | - | STRING |  | .com only |
| `safeReachSuccessMessage` | Defines success message for Safe Reach. | STRING |  | .com only |
| `sanitisationFloorPlanUrl` | - | STRING |  | both |
| `scheduled_reminder_notification_enabled_buids` | - | STRING |  | both |
| `scheduledTimeForVisitorGatePassEmailInMin` | - | DOUBLE |  | both |
| `searchCriteriaVendorKiosk` | Used to control search section and placeholder for vendor kiosk and dashboard search. | JSON |  | .com only |
| `SEAT_BELT_NON_COMPLIANCE_EMAIL_CONFIGS` | - | JSON |  | .com only |
| `SEAT_BELT_NON_COMPLIANCE_REPORT_EMAIL_ENABLED` | - | BOOLEAN |  | both |
| `seatBeltNonFunctioningIssues` | - | LIST |  | both |
| `seatBeltUndoTimeoutMinutes` | - | INTEGER |  | both |
| `seatBooking` | Defines primary Seat Booking application URL. | STRING |  | both |
| `seatBookingUrl` | Defines Seat Booking service URL. | STRING |  | both |
| `seatBookingV2` | Enables Seat Booking version 2. | BOOLEAN |  | both |
| `seatSanitizationCheck` | Controls seat sanitization validation before booking. | BOOLEAN |  | both |
| `seatScanEnable` | Enables seat QR scanning on booking page. | BOOLEAN |  | both |
| `securityGuard` | Defines Security Guard service URL. | STRING |  | both |
| `selfCommuteSubmissionEmailSubject` | Defines subject for opt-in/opt-out submission email. | STRING |  | .com only |
| `selfCommuteWithdrawalEmailSubject` | Defines subject for opt-in/opt-out withdrawal email. | STRING |  | .com only |
| `sendEmailIneligibility` | - | BOOLEAN |  | both |
| `shareRideCallDriver` | - | BOOLEAN |  | both |
| `showBookingFilter` | Enables toggle to show/hide cancelled bookings. | BOOLEAN |  | both |
| `showBookingHistory` | Enables booking history on app. | BOOLEAN |  | both |
| `showBookingsOfSomeoneElseOnWeb` | - | BOOLEAN |  | both |
| `showCanceledCountinAttendanceChart` | Controls visibility of cancelled count in attendance charts. | BOOLEAN |  | .com only |
| `showConfigureDeskAmenities` | Controls visibility of desk amenities configuration button. | BOOLEAN |  | .com only |
| `showConfirmationForLogoutTracking` | - | BOOLEAN |  | both |
| `showEmployeeCreation` | - | BOOLEAN |  | .com only |
| `showEmployeeSearchOnSeatBooking` | Enables colleague search by name. | BOOLEAN |  | both |
| `showFabQRScanner` | Controls QR scanner visibility on FAB. | BOOLEAN |  | both |
| `showMealCost` | Shows meal cost on items for standard meal booking. | BOOLEAN |  | .com only |
| `showMealCountOnBookingForm` | Displays real-time meal availability count on booking form. | BOOLEAN |  | both |
| `showMealPaymentCTA` | Enables meal payment CTA integrated with payment gateways. | BOOLEAN |  | both |
| `showMealTimings` | Shows meal time on items for standard meal booking. | BOOLEAN |  | .com only |
| `showMeetingRoomOnApp` | Enables Meeting Room booking option on mobile app. | BOOLEAN |  | both |
| `showOfficeInfoOnBookingForm` | Displays searchable office address list during booking. | BOOLEAN |  | both |
| `showOrderOfChallengesAfterQRScan` | Displays declaration after QR scan. | BOOLEAN |  | both |
| `showOtherEmployeeDetailsOnSeat` | Controls visibility of other employee booking details on seat view. | BOOLEAN |  | both |
| `showOtpWithoutDigipassGeneration` | Displays cab login/logout OTPs directly on the booking card. | BOOLEAN |  | both |
| `showParking` | Controls parking field visibility in Teams chatbot. | BOOLEAN |  | both |
| `showQRScanner` | Enables Scan QR option in the app. | BOOLEAN |  | both |
| `showQRScannerMeetingCheckIn` | Enables QR-based meeting room check-in. | BOOLEAN |  | both |
| `showRegistrationNumberInputFieldForParking` | Displays vehicle registration number input field during parking booking. | BOOLEAN |  | both |
| `showSanitizationDetails` | Displays sanitization details in the app. | BOOLEAN |  | both |
| `showSeatSearchOnAdminPages` | Enables desk search on admin floor plan pages. | BOOLEAN |  | both |
| `showSeatSearchOnSeatBooking` | Enables desk search by desk number. | BOOLEAN |  | both |
| `showSeparateDigipassFor` | Controls resource-level DigiPass generation. | LIST |  | both |
| `showSeparateDigipassForParking` | Displays separate digipass for parking resources in the mobile app. | BOOLEAN |  | both |
| `showSignedinStateOnEmployeeFloorPlan` | Displays signed-in desk state (green indicator) on Employee Floor Plan. | BOOLEAN |  | both |
| `showTeamCalendarOption` | Displays Team Calendar option in the app. | BOOLEAN |  | both |
| `showTeamOnKioskForEmployee` | Displays team name instead of employee ID in kiosk organizer dropdown. | BOOLEAN |  | .com only |
| `showVaccinationOptionInSideMenu` | Enables Vaccination status option in the app side menu. | BOOLEAN |  | both |
| `showWomenSafetyInSideMenu` | Displays Women Safety Handbook in mobile side menu. | BOOLEAN |  | both |
| `showWorkinsyncLogoOnSideNav` | Controls WorkInSync logo visibility on sidenav. | BOOLEAN |  | both |
| `shuttleBookingConfirmationNotificationEnabled` | - | BOOLEAN |  | both |
| `shuttleSigninRemainderBufferMins` | - | DOUBLE |  | both |
| `shuttleSigninRemainderNotificationEnabled` | - | BOOLEAN |  | both |
| `singleShiftOperations` | Hides time components in Team Calendar and Preferences for single-shift environments. | BOOLEAN |  | both |
| `skipOptInTimeWindowValidation` | - | BOOLEAN |  | .com only |
| `smsTrackingEnabled` | - | BOOLEAN |  | both |
| `ssoMandatory` | Removes OTP login option and enforces SSO-only login on mobile. | BOOLEAN |  | both |
| `standardTeamColor` | Defines default team legend color in floor plan. | STRING |  | .com only |
| `stopNoShowEmailForShuttle` | - | BOOLEAN |  | both |
| `tagsEnabled` | Defines enabled booking tags. | LIST |  | both |
| `teamCalendarEnabled` | Enables Team Calendar feature. | BOOLEAN |  | both |
| `teamManager` | Defines Team Manager service URL. | STRING |  | both |
| `TIME_FORMAT` | Defines time format for UI. | STRING |  | both |
| `TIME_FORMAT_SERVICES` | Defines time format for backend services. | STRING |  | both |
| `trackAnyShuttleEnabled` | - | BOOLEAN |  | both |
| `transferBookingEnabled` | Adds a 'Transfer Booking Details' column in seat and meeting room reports. | BOOLEAN |  | both |
| `transferBookingTypes` | - | LIST |  | both |
| `transportFieldsMandatory` | Controls whether transport fields are mandatory. | BOOLEAN |  | both |
| `tripFeedbackExpressionsMap` | - | LIST |  | .com only |
| `tripRatingMandatory` | Controls whether trip rating is mandatory. | BOOLEAN |  | .com only |
| `tripRatingMandatoryThreshold` | - | JSON |  | both |
| `upcomingMeetingsEmployeeHome` | Controls display of upcoming meetings on Employee Home. | BOOLEAN |  | both |
| `USER_CLOCK_OUT_REMAINDER_MINUTES` | - | INTEGER |  | .com only |
| `USERCLOCKOUTREMAINDERMINUTES` | - | INTEGER |  | .com only |
| `userResourceGroupMappingEnabled` | Indicates whether resource group mapping is enabled for office visibility. | BOOLEAN |  | .com only |
| `vaccinationBookingEnabled` | Enables vaccination slot booking feature in the app. | BOOLEAN |  | both |
| `vaccinationBookingUrl` | URL for the vaccination booking feature in the app. | STRING |  | both |
| `vaccinationMaxApprovalDays` | Defines maximum days allowed for vaccination request approval. | DOUBLE |  | both |
| `VAX_STATUS_CHECK_SEEK_RTPCR_EMP` | Allows or restricts RTPCR upload for non-fully vaccinated employees. | BOOLEAN |  | both |
| `vaxEmailEnabled` | - | BOOLEAN |  | both |
| `vehicleCreationDuringParkingEnabled` | Controls vehicle creation during parking booking. | BOOLEAN |  | both |
| `vehicleCreationDuringParkingFor` | Controls which vehicle types are offered during parking booking. Valid values: `["CAR","BIKE"]` (both), `["CAR"]` (cars only), `["BIKE"]` (bikes only), `[]` (none). Works together with `vehicleCreationDuringParkingEnabled`. | LIST |  | both |
| `vehicleFuelTypes` | - | LIST |  | both |
| `visitorWidgetEnabled` | Displays visitor management widget on Employee Home. | BOOLEAN |  | both |
| `waitListBookingBufferTimeInMin` | Defines buffer time in minutes for waitlist bookings. | INTEGER |  | both |
| `wayfindingPathColor` | Controls arrow color customization in wayfinding path. | JSON |  | .com only |
| `welcomeEmailEnabled` | Controls sending of welcome emails. | BOOLEAN |  | both |
| `wfhBookingAllowed` | Controls WFH booking visibility in WorkInSync Teams chatbot. | BOOLEAN |  | both |
| `wfhClockinCutOffInMinute` | Defines cutoff time for WFH clock-in. | DOUBLE |  | both |
| `wfhDisabled` | Controls whether WFH booking is enabled or disabled. | BOOLEAN |  | both |
| `wfhMinBetweenClockInClockOut` | Defines minimum duration between WFH clock-in and clock-out. | DOUBLE |  | .com only |
| `wfhReasonList` | Work From Home/Remote booking reasons. | STRING |  | both |
| `wfhType` | Controls default Work From Home booking type. | STRING |  | both |
| `WisThemeColors` | Defines theme colors for WorkInSync modules. | JSON |  | .com only |
| `womenSafetyDocUrl` | Controls URL of Women Safety Handbook document. | STRING |  | both |
| `workplannerCheckInAdvanceCutOffInMinute` | Defines early check-in limit for Workplanner bookings. | INTEGER |  | .com only |
| `workplannerCheckInDelayCutOffInMinute` | Defines late check-in limit for Workplanner bookings. | INTEGER |  | .com only |
| `workplannerRecurrenceMaxDays` | Defines maximum recurrence window in Workplanner. | INTEGER |  | .com only |
