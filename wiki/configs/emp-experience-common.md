---
type: config
module: employee-experience
servers:
  - in
  - com
last_updated: 2026-05-26
sources:
  in: "[[sources/pms-configs-in-all-wis-configs]]"
  com: "[[sources/pms-configs-com-wis-service-configs]]"
---

# Employee Experience — Common Config — Config Properties

## Service
Employee Experience — Common Config. Linked module: [[modules/employee-experience]].

_Source: [[sources/pms-configs-in-all-wis-configs]] | [[sources/pms-configs-com-wis-service-configs]]_

## Config Comparison

> **Server key:** ✅ = property present in that server's config list | — = absent
> **Description source:** `.com` description preferred; falls back to `.in`, PMS Description Cleaned, then `wis_unique_configs`.
> ⚠️ `undocumented` = no description found in any source — contact the owning team.

| Property Name | .in | .com | Data Type | Description |
|---------------|-----|------|-----------|-------------|
| `ACCESS_MATRIX_ENABLED_BUIDS` | ✅ | ✅ | LIST | Defines BUs with access matrix enabled. |
| `ADDRESS_CHANGE_HOME_TO_OFFICE_DISTANCE_VALIDATION` | ✅ | ✅ | STRING | ⚠️ undocumented |
| `ADDRESS_CHANGE_RADIAL_DISTANCE_VALIDATION` | ✅ | ✅ | STRING | ⚠️ undocumented |
| `ADDRESS_CHANGE_RESTRICTED_AREA_VALIDATION` | ✅ | ✅ | STRING | ⚠️ undocumented |
| `ADDRESS_CHANGE_TRANSPORT_BOUNDARY_VALIDATION` | ✅ | ✅ | STRING | ⚠️ undocumented |
| `adminAssignmentFloorPlanUrl` | ✅ | ✅ | STRING | Defines Admin Seat Allocation Floor Plan URL. |
| `adminexpUI` | ✅ | ✅ | STRING | Defines Admin Experience UI URL. |
| `adminexpUi` | ✅ | ✅ | STRING | Defines alternate Admin UI URL. |
| `adminFloorPlanUrl` | ✅ | ✅ | STRING | Defines Admin Floor Plan URL. |
| `airtelBuid` | ✅ | ✅ | STRING | ⚠️ undocumented |
| `allowBookingConversionFromWfhToWfo` | ✅ | ✅ | BOOLEAN | Enables direct WFH to WFO booking conversion. |
| `allowBookingConversionFromWfoToWfh` | ✅ | ✅ | BOOLEAN | Enables direct WFO to WFH booking conversion. |
| `allowBookingForOthers` | ✅ | ✅ | LIST | Defines booking types allowed for others. |
| `allowCheckInAtIncorrectSlot` | ✅ | ✅ | BOOLEAN | Allows check-in outside booked slot. |
| `allowedEmployeeNameRegex` | ✅ | ✅ | STRING | Defines the allowed employee name format using regex validation. |
| `allowEmployeeToBooKAnySeatInBL` | ✅ | ✅ | BOOLEAN | Allows employees to book seats within permitted hierarchy levels in BL. |
| `allowPastAllocationTimesForCurrentDayFor` | ✅ | ✅ | LIST | Allows admins to allocate desks/slots/rooms for past shift times on the same day. |
| `allowPeerOrMarshalReporting` | ✅ | ✅ | BOOLEAN | ⚠️ undocumented |
| `allowQrCheckInWithoutSeat` | ✅ | ✅ | BOOLEAN | Allows QR check-in without seat. |
| `allowRoomBookingWithOfficeBooking` | ✅ | ✅ | BOOLEAN | Controls visibility of Room booking option on Employee Home. |
| `APPROVAL_POST_NO_SHOW_CHECK_BUFFER` | ✅ | ✅ | DOUBLE | ⚠️ undocumented |
| `approvalFlowEnabled` | ✅ | ✅ | BOOLEAN | Enables Team Manager approval dashboard. |
| `approvalWebViewUrl` | ✅ | ✅ | STRING | Defines approval web view URL. |
| `autoAllocate` | ✅ | ✅ | BOOLEAN | Enables automatic desk allocation during bulk booking upload. |
| `autoClockOutRemainder` | ✅ | ✅ | BOOLEAN | Sends reminder notification before auto-checkout triggers. |
| `autoClockOutRemainderMinutes` | ✅ | ✅ | DOUBLE | Defines minutes before logout when reminder notification is triggered. |
| `autoLogoutEnabled` | ✅ | ✅ | BOOLEAN | Enables automatic sign-out after configured duration. |
| `autoLogoutMinutes` | ✅ | ✅ | DOUBLE | Defines minutes after planned checkout for auto-checkout trigger. |
| `autoPopulateBookingForm` | ✅ | ✅ | BOOLEAN | Auto-populates booking form using preferences or past data. |
| `autoProvisionEnabled` | ✅ | ✅ | BOOLEAN | Automatically marks all employees as onboarded during bulk onboarding. |
| `autoSeatCheckOutEnabled` | ✅ | ✅ | BOOLEAN | Enables auto seat checkout. |
| `autoSeatCheckOutMinutes` | ✅ | ✅ | DOUBLE | Defines auto seat checkout duration. |
| `autoSlotAllocate` | ✅ | ✅ | BOOLEAN | Automatically allocates parking slots without manual slot selection. |
| `autoTagAssignmentMapping` | ✅ | ✅ | JSON | Automatically assigns tags based on employee designation. |
| `averageOverallTripFeedbackCalculation` | ✅ | ✅ | BOOLEAN | ⚠️ undocumented |
| `bannerEndTime` | ✅ | ✅ | STRING | ⚠️ undocumented |
| `bannerNativeRoomEmail` | ✅ | ✅ | BOOLEAN | Controls native banner visibility in room emails. |
| `bannerNewRoomBookingEmpHome` | ✅ | ✅ | STRING | Defines banner text for New Room booking page. |
| `bannerStartTime` | ✅ | ✅ | STRING | ⚠️ undocumented |
| `blockDelegationEmail` | ✅ | ✅ | BOOLEAN | Blocks delegation email notifications. |
| `blockGenerateDigiPassOnSeatMandatory` | ✅ | ✅ | BOOLEAN | Blocks DigiPass generation when seat is mandatory. |
| `blockNumber` | ✅ | ✅ | STRING | Controls Block number field visibility. |
| `blockOfficeCheckingIfNoBooking` | ✅ | ✅ | BOOLEAN | Blocks office check-in without booking. |
| `blockUserIfNotVaccinated` | ✅ | ✅ | BOOLEAN | Blocks non-vaccinated users from making bookings when enabled. |
| `BOOKING_HISTORY` | ✅ | ✅ | BOOLEAN | Enables booking history option on web. |
| `bookingCancellationReasons` | ✅ | ✅ | LIST | Defines cancellation reason list. |
| `bookingConversionCutOff` | ✅ | ✅ | DOUBLE | Defines cutoff time for WFH to WFO and vice versa conversion. |
| `bookingEnabledOnTag` | ✅ | ✅ | BOOLEAN | Enables booking based on tags. |
| `bookingRequestApprovalFlowEnabled` | ✅ | ✅ | BOOLEAN | Enables booking approval workflow. |
| `bookingRuleEngine` | ✅ | ✅ | STRING | Defines Booking Rule Engine URL. |
| `bookingsTypesForCheckinReminder` | ✅ | ✅ | LIST | Defines booking types eligible for check-in reminder. |
| `bufferTimeInSecondsOfAarogyaSetuUser` | ✅ | ✅ | DOUBLE | This property controls the buffer time in seconds applied to Aarogya Setu user validation (covid feature). |
| `bulkScheduleAllowedDaysForRoom` | ✅ | ✅ | DOUBLE | Defines bulk room scheduling window. |
| `cacheTimeInHoursOfAarogyaSetuUserStatus` | ✅ | ✅ | DOUBLE | Defines Aarogya Setu status cache duration. |
| `CANCELLATION_REMINDER_NOTIFICATION` | ✅ | ✅ | BOOLEAN | Enables cancellation reminder notifications. |
| `cancelTransportBooking` | ✅ | ✅ | BOOLEAN | Allows transport booking cancellation. |
| `captureEmployeeBookingStats` | ✅ | ✅ | BOOLEAN | Enables booking statistics capture. |
| `checkinReminderCutoffInMinute` | ✅ | ✅ | DOUBLE | Defines when check-in reminder notification is sent. |
| `checkInWithoutAarogyasetuValidation` | ✅ | ✅ | BOOLEAN | Allows check-in without Aarogya Setu validation. |
| `CITY_DISTRICT_MAPPINGS` | ✅ | ✅ | JSON | ⚠️ undocumented |
| `commentsMandatoryOnRating` | ✅ | ✅ | DOUBLE | ⚠️ undocumented |
| `commuteMandatory` | ✅ | ✅ | BOOLEAN | Requires users to select either parking or transport while creating an office booking to prevent resource-less bookings. |
| `confirmationMessageForLogoutTracking` | ✅ | ✅ | STRING | ⚠️ undocumented |
| `consentPopupData` | ✅ | ✅ | LIST | Defines consent popup configuration. |
| `contactTHDReasons` | ✅ | ✅ | LIST | ⚠️ undocumented |
| `CutOffTimeBetweenBookingsOnSeatInMinute` | ✅ | ✅ | DOUBLE | Defines minimum gap between consecutive bookings on the same seat. |
| `cutoffTimeBetweenWISAppFeedback` | ✅ | ✅ | JSON | Defines minimum time gap between feedback prompts. |
| `cutoffTimeForSkipWISAppFeedback` | ✅ | ✅ | DOUBLE | Defines interval in hours for app feedback display frequency. |
| `DATE_FORMAT` | ✅ | ✅ | STRING | Defines date format for UI. |
| `DATE_FORMAT_SERVICES` | ✅ | ✅ | STRING | Defines date format for backend services. |
| `defaultLogoutShiftMinutes` | ✅ | ✅ | DOUBLE | Auto-populates checkout time based on configured duration after check-in selection. |
| `delegatorDelegateeEmailsEnabled` | ✅ | ✅ | BOOLEAN | Sends email notification to delegator. |
| `directCheckinEndCutOffInMinute` | ✅ | ✅ | DOUBLE | Defines end cutoff for direct check-in. |
| `directCheckinExpiryInMinute` | ✅ | ✅ | DOUBLE | Defines expiry time for direct check-in. |
| `directCheckinStartCutOffInMinute` | ✅ | ✅ | DOUBLE | Defines start cutoff for direct check-in. |
| `DIRECTION` | ✅ | ✅ | STRING | ⚠️ undocumented |
| `email` | ✅ | ✅ | STRING | Controls whether the Email field is shown or hidden during employee profile validation. |
| `empExp` | ✅ | ✅ | STRING | Defines primary Employee Experience URL. |
| `empExpUi` | ✅ | ✅ | STRING | Defines Employee Experience UI URL. |
| `empexpUI` | ✅ | ✅ | STRING | Defines Employee Experience interface URL. |
| `empID` | ✅ | ✅ | STRING | Controls whether the Employee ID field is shown or hidden during employee profile validation. |
| `employeeFloorPlanUrl` | ✅ | ✅ | STRING | Defines Employee Floor Plan URL. |
| `employeePIIMasking` | ✅ | ✅ | LIST | Configures selective masking of PII fields and visual security settings. |
| `employeeStatusModuleEnabled` | ✅ | ✅ | BOOLEAN | If this property is set true, it starts using configuration under employeeStatusList. |
| `ENABLE_CHECKIN_NOTIFICATION` | ✅ | ✅ | BOOLEAN | Master switch to enable check-in notifications. |
| `enableAutoAbsentNotification` | ✅ | ✅ | BOOLEAN | Sends notification when a booking results in no-show. |
| `enableBookingCancellationReasonsFor` | ✅ | ✅ | LIST | Requires cancellation reason for specified booking types. |
| `enableBookingEmail` | ✅ | ✅ | BOOLEAN | Enables booking details email notification. |
| `enableCarbonFootprintTrackingInParking` | ✅ | ✅ | BOOLEAN | Tracks and displays carbon footprint for employee commutes. |
| `enableColorInParkingVehicleCreation` | ✅ | ✅ | BOOLEAN | Adds vehicle color input field in parking vehicle creation. |
| `enabledCheckInEmailBodyParam` | ✅ | ✅ | LIST | Defines enabled parameters in check-in email body. |
| `enabledCheckInEmailBodyParamNames` | ✅ | ✅ | LIST | Defines parameter names in check-in email body. |
| `enableDelegationForAdmins` | ✅ | ✅ | BOOLEAN | Allows admins to manage delegation. |
| `enableDynamicFields` | ✅ | ✅ | BOOLEAN | Enables configurable dynamic fields per BU. |
| `enableEmployeePreferences` | ✅ | ✅ | BOOLEAN | Enables employee preference settings on web. |
| `enableEmployeeRFIDColumn` | ✅ | ✅ | BOOLEAN | Enables RFID number field and prevents duplicates. |
| `enableFloorPlanAccessibility` | ✅ | ✅ | BOOLEAN | Enables accessibility features for visually impaired users. |
| `enableGeofenceCheckFor` | ✅ | ✅ | LIST | Enables GPS/geofence validation for specified workflows. |
| `enableGeofenceCheckForCheckin` | ✅ | ✅ | BOOLEAN | Enforces check-in validation within defined geofence limits. |
| `enableGridFloorPlan` | ✅ | ✅ | BOOLEAN | Enables grid-based parking floor plan. |
| `enableJoinAllWaitlist` | ✅ | ✅ | BOOLEAN | Allows joining waitlists across all parking levels. |
| `enableMealCartView` | ✅ | ✅ | BOOLEAN | Activates meal cart and payment flow when enabled with showMealPaymentCTA. |
| `enableMealImageIn` | ✅ | ✅ | LIST | To show meal image in meal item. |
| `enableMultiAllocation` | ✅ | ✅ | LIST | Controls desk multi-allocation functionality and displays the Multi-allocated Desk legend entry on floor plans when value includes 'DESK'. |
| `enableNewAdminDashboard` | ✅ | ✅ | BOOLEAN | Enables Admin Dashboard 2.0. |
| `enableNewAllocationFlow` | ✅ | ✅ | BOOLEAN | Enables new allocation flow required for time-based allocation. |
| `EnableNewEmailTemplate` | ✅ | ✅ | BOOLEAN | Enables new email template format. |
| `enablePerpetualDigipassForAllUsers` | ✅ | ✅ | BOOLEAN | Allows DigiPass generation without office booking. |
| `enableProjectCodeFor` | ✅ | ✅ | LIST | Enables Project Code field for specified booking types. |
| `enableProjectColor` | ✅ | ✅ | BOOLEAN | Enables enhanced seat and team color legends on floor plan. |
| `enableQRBasedRemoteSignin` | ✅ | ✅ | BOOLEAN | Enables QR-based remote sign-in. |
| `enableSafeReachForBookingTypes` | ✅ | ✅ | LIST | Defines booking types eligible for Safe Reach. |
| `enableSafeReachWisList` | ✅ | ✅ | LIST | Defines environments where Safe Reach is enabled. |
| `enableTimeBasedDeskAllocation` | ✅ | ✅ | BOOLEAN | Enables time-based desk allocation and disables List View. |
| `enableTimezoneWithOfficeName` | ✅ | ✅ | BOOLEAN | Displays timezone with office name. |
| `enableTransportBookingBulkUpload` | ✅ | ✅ | BOOLEAN | ⚠️ undocumented |
| `enableVisitorManagementOnApp` | ✅ | ✅ | BOOLEAN | Enables visitor management in app. |
| `enableWaitlistBooking` | ✅ | ✅ | BOOLEAN | Enables waitlist functionality in parking bookings. |
| `enforceReAuthentication` | ✅ | ✅ | BOOLEAN | Enables enforcement of re-authentication. |
| `enforceReAuthenticationDurationInMinutes` | ✅ | ✅ | DOUBLE | Defines re-authentication validity duration in minutes. |
| `externalStaffUi` | ✅ | ✅ | STRING | Defines External Staff UI URL. |
| `fabDisplayNames` | ✅ | ✅ | LIST | Defines FAB display names. |
| `filterNoAvailableSeatInFloor` | ✅ | ✅ | BOOLEAN | Filters floors without available seats. |
| `floorManagement` | ✅ | ✅ | STRING | Defines Floor Management URL. |
| `floorPlan` | ✅ | ✅ | STRING | Defines primary Floor Plan URL. |
| `floorPlanUI` | ✅ | ✅ | STRING | Defines Floor Plan UI URL. |
| `forecastingEfficiancy` | ✅ | ✅ | DOUBLE | ⚠️ undocumented |
| `gender` | ✅ | ✅ | STRING | Controls whether the Gender field is shown or hidden during employee profile validation. |
| `generateGatepassDelayCutOff` | ✅ | ✅ | DOUBLE | Defines minutes after booking start when DigiPass generation is allowed. |
| `hideBookingTimeMealOnly` | ✅ | ✅ | BOOLEAN | ⚠️ undocumented |
| `hierarchy` | ✅ | ✅ | LIST | Defines organizational hierarchy levels. |
| `homeGeocode` | ✅ | ✅ | STRING | Controls whether the Home Geocode field is shown or hidden during employee profile validation. |
| `igonreErrorOfArrogyaSetu` | ✅ | ✅ | BOOLEAN | Ignores Aarogya Setu app status check errors. |
| `includeChildHierarchy` | ✅ | ✅ | BOOLEAN | Controls inclusion of child hierarchy levels. |
| `INDEMNIFICATION_REASONS` | ✅ | ✅ | STRING | Defines available indemnification reasons. |
| `industryStandard` | ✅ | ✅ | JSON | Controls industry standard values on Admin Dashboard metric cards. |
| `isAmenitiesFilter` | ✅ | ✅ | BOOLEAN | Enables amenities filter in desk booking. |
| `isAppFeedbackEnabled` | ✅ | ✅ | BOOLEAN | Enables app feedback feature. |
| `isAutoAbsentEnabled` | ✅ | ✅ | BOOLEAN | Enables auto-absent feature and automatic seat release if check-in does not occur within cutoff. |
| `isAutoProvision` | ✅ | ✅ | BOOLEAN | ⚠️ undocumented |
| `isBlSubblBuid` | ✅ | ✅ | BOOLEAN | Enables N-level hierarchy/Business Line feature for BU. |
| `isBuNudgeNotifEnabled` | ✅ | ✅ | BOOLEAN | Enables weekly nudge notifications for users without bookings. |
| `isCalendarInviteEnabled` | ✅ | ✅ | BOOLEAN | Enables calendar invite option. |
| `isCheckinNotificationEnabled` | ✅ | ✅ | BOOLEAN | Enables notification after successful check-in. |
| `isDelegationEnabled` | ✅ | ✅ | BOOLEAN | Master switch enabling Delegation feature. |
| `isDynamicFieldsMandatory` | ✅ | ✅ | BOOLEAN | Makes dynamic fields mandatory. |
| `isGDPRCookiePolicyEnabled` | ✅ | ✅ | BOOLEAN | Displays GDPR compliance pop-up in mobile app. |
| `isMasterNudgeNotifEnabled` | ✅ | ✅ | BOOLEAN | Controls master nudge notifications. |
| `isPhoneValidationOptional` | ✅ | ✅ | BOOLEAN | Controls whether phone number is optional or mandatory during employee registration. |
| `isReportingAndAnalyticEnable` | ✅ | ✅ | BOOLEAN | ⚠️ undocumented |
| `isSeatBookingAssignment` | ✅ | ✅ | BOOLEAN | Controls seat assignment feature. |
| `isShuttleRequired` | ✅ | ✅ | BOOLEAN | Replaces cab labels and icons with shuttle terminology across modules. |
| `isZedaReleaseNoteEnabled` | ✅ | ✅ | BOOLEAN | Displays Zeda widget showcasing new features and feedback. |
| `jobTitleWiseCalenderInDays` | ✅ | ✅ | JSON | ⚠️ undocumented |
| `landmark` | ✅ | ✅ | STRING | Controls visibility of Landmark field during registration. |
| `lastSwipeAsCheckoutTimeForBUID` | ✅ | ✅ | LIST | Uses the last swipe checkout time as final checkout instead of auto-checkout for access card integration clients. |
| `listOfEligibleBuidsForAutoClockout` | ✅ | ✅ | LIST | Defines BUs eligible for auto clock-out. |
| `listOfEligibleBuidsForBusNotification` | ✅ | ✅ | LIST | ⚠️ undocumented |
| `madatoryFieldforScheduling` | ✅ | ✅ | LIST | (Inferred) Defines the list of mandatory fields (e.g., ADDRESS, GENDER, OFFICE, MOBILE) required when an employee is scheduling a trip/booking. |
| `mapSchedulesToBooking` | ✅ | ✅ | BOOLEAN | Automatically maps schedules to matching bookings. |
| `maximumCharacterLimit` | ✅ | ✅ | DOUBLE | ⚠️ undocumented |
| `maxTripLevelNonComplianceEventsAllowed` | ✅ | ✅ | INTEGER | maxTripLevelNonComplianceEventsAllowed |
| `mealCutoffInMinutes` | ✅ | ✅ | DOUBLE | Defines meal booking cutoff calculated from 00:00 of booked date. |
| `mealFeedbackEnabled` | ✅ | ✅ | BOOLEAN | Enables meal feedback feature and reporting. |
| `mealPlanningEnabled` | ✅ | ✅ | BOOLEAN | Enables meal booking via Work Planner. |
| `mealPlanningMandatory` | ✅ | ✅ | BOOLEAN | Makes meal selection mandatory in office booking form. |
| `medicalEmergencyRequest` | ✅ | ✅ | JSON | ⚠️ undocumented |
| `meetingDetailsForDateUrl` | ✅ | ✅ | STRING | Defines Meeting Details by date URL. |
| `meetingOptionWebViewUrl` | ✅ | ✅ | STRING | Defines Meeting Room web view URL. |
| `meetingRoomKioskUrl` | ✅ | ✅ | STRING | Defines Meeting Room Kiosk URL. |
| `meetingRoomUrl` | ✅ | ✅ | STRING | Defines Meeting Room module URL. |
| `microBookingEnabled` | ✅ | ✅ | BOOLEAN | ⚠️ undocumented |
| `mobile` | ✅ | ✅ | STRING | Controls whether the Mobile field is shown or hidden during employee profile validation. |
| `MOBILE_APP_BANNERS` | ✅ | ✅ | LIST | ⚠️ undocumented |
| `mobileNumberLength` | ✅ | ✅ | DOUBLE | Defines required mobile number length. |
| `mobileSSOMandatory` | ✅ | ✅ | BOOLEAN | Removes the 'Continue with OTP' option on the mobile SSO login screen. |
| `mobilityHealthStatus` | ✅ | ✅ | STRING | Displays driver vaccination details on the Tracking page. |
| `multipleBookingsOnASeatInADayAllowed` | ✅ | ✅ | BOOLEAN | Allows multiple bookings on the same seat within a single day. |
| `multipleScanErrorMessage` | ✅ | ✅ | STRING | Defines error message for multiple scans. |
| `name` | ✅ | ✅ | STRING | Controls whether the Name field is shown or hidden during employee profile validation. |
| `nativeRoomEmail` | ✅ | ✅ | BOOLEAN | Displays room email ID input in new room workflow. |
| `NO_SHOW_COUNT_BANNER_ENABLED` | ✅ | ✅ | BOOLEAN | Controls no-show banner visibility. |
| `nodal` | ✅ | ✅ | STRING | Controls whether the Nodal Point field is shown or hidden during employee profile validation. |
| `noOfDaysAllowedInPlanner` | ✅ | ✅ | DOUBLE | Defines allowed planning window. |
| `numberOfAllowedTrips` | ✅ | ✅ | DOUBLE | Defines maximum trips per user. |
| `office` | ✅ | ✅ | STRING | Controls whether the Office field is shown or hidden during employee profile validation. |
| `officeCheckInMode` | ✅ | ✅ | STRING | Configures office check-in mode for mobile. |
| `officeCheckInModeApp` | ✅ | ✅ | STRING | Configures office check-in mode for mobile app. |
| `officeCheckInModeWeb` | ✅ | ✅ | STRING | Configures office check-in mode for web. |
| `officeCheckInReminderEmailEnabled` | ✅ | ✅ | BOOLEAN | Controls office check-in reminder emails. |
| `onBehalfBookingEmailToCreatorEnabled` | ✅ | ✅ | BOOLEAN | Controls on-behalf booking email notification to creator. |
| `onlyParkingBookingEnabled` | ✅ | ✅ | BOOLEAN | Displays only the Parking booking option on Employee Home and FAB for clients using MoveInSync exclusively for parking. |
| `parkingAllocationUrl` | ✅ | ✅ | STRING | Defines Parking Allocation URL. |
| `parkingBookingMandatory` | ✅ | ✅ | BOOLEAN | Makes parking booking mandatory for office booking. |
| `parkingEnabled` | ✅ | ✅ | BOOLEAN | Enables parking option in the booking form. |
| `parkingEndCutOffInMinute` | ✅ | ✅ | DOUBLE | Defines minutes after booking start when parking QR can be generated. |
| `parkingExpiry` | ✅ | ✅ | DOUBLE | Defines expiry time of generated parking QR. |
| `parkingMailNotificationMinutes` | ✅ | ✅ | DOUBLE | Defines parking email trigger minutes. |
| `parkingReminderEmailEnabled` | ✅ | ✅ | BOOLEAN | Controls parking reminder emails. |
| `parkingScheduleCutoff` | ✅ | ✅ | DOUBLE | Defines advance booking window for parking. |
| `parkingStartCutOffInMinute` | ✅ | ✅ | DOUBLE | Defines minutes before booking start when parking QR can be generated. |
| `pendingRequestsNotificationEnabled` | ✅ | ✅ | BOOLEAN | Controls pending request notifications. |
| `PRE_TRIP_CANCELLATION_NOTIFICATION_MINUTES_BEFORE_LOGIN_CANCELLATION_CUTOFF` | ✅ | ✅ | INTEGER | ⚠️ undocumented |
| `PRE_TRIP_CANCELLATION_NOTIFICATION_MINUTES_BEFORE_LOGOUT_CANCELLATION_CUTOFF` | ✅ | ✅ | INTEGER | ⚠️ undocumented |
| `preferencesFloorPlanUrl` | ✅ | ✅ | STRING | Defines Preferences floor plan URL. |
| `premiseUI` | ✅ | ✅ | STRING | Defines Premises management UI URL. |
| `profileRegistrationEmailSubject` | ✅ | ✅ | STRING | ⚠️ undocumented |
| `projectCodeEnabledOnBooking` | ✅ | ✅ | BOOLEAN | Controls Project Code field visibility. |
| `projectCodeEnabledOnBookingMandatory` | ✅ | ✅ | BOOLEAN | Controls mandatory Project Code field. |
| `projectCodeMandatoryFor` | ✅ | ✅ | LIST | Makes Project Code field mandatory for specified booking types. |
| `promotionBannerUrl` | ✅ | ✅ | STRING | ⚠️ undocumented |
| `promotionDisplayText` | ✅ | ✅ | STRING | ⚠️ undocumented |
| `qRScannerEndCutOffInMinute` | ✅ | ✅ | DOUBLE | Defines minutes after booking start when Scan QR becomes inactive. |
| `qRScannerExpiry` | ✅ | ✅ | DOUBLE | Defines expiry time of QR scanner after booking start. |
| `qRScannerStartCutOffInMinute` | ✅ | ✅ | DOUBLE | Defines minutes before booking start when Scan QR becomes active. |
| `reAuthenticationModeEmail` | ✅ | ✅ | BOOLEAN | Defines email-based two-step authentication mode. |
| `reAuthenticationModePhone` | ✅ | ✅ | BOOLEAN | Defines phone-based two-step authentication mode. |
| `recurrenceBookingEnabled` | ✅ | ✅ | BOOLEAN | Enables recurring booking feature. |
| `remoteSignCutoffInMinute` | ✅ | ✅ | DOUBLE | Defines cutoff time for contactless bus solution sign-in. |
| `remoteSignInAllowed` | ✅ | ✅ | BOOLEAN | Enables remote sign-in using Scan QR. |
| `remoteSignOutCutoffInMinute` | ✅ | ✅ | INTEGER | Defines cutoff time for remote sign-out. |
| `removeFloorsMappedToRooms` | — | — | — | ⚠️ undocumented |
| `reportingAndAnalyticUrl` | ✅ | ✅ | STRING | Defines Reporting and Analytics dashboard URL. |
| `reportingService` | ✅ | ✅ | STRING | Defines Reporting service URL. |
| `restrictMealScanToOne` | ✅ | ✅ | BOOLEAN | Restricts meal QR scanning to once per meal window. |
| `restrictMultipleVisitorBookingCheckIn` | ✅ | ✅ | BOOLEAN | Restricts multiple visitor booking check-ins. |
| `roomAllocationEnabled` | ✅ | ✅ | BOOLEAN | Enables automatic room allocation. |
| `sanitisationFloorPlanUrl` | ✅ | ✅ | STRING | ⚠️ undocumented |
| `scheduled_reminder_notification_enabled_buids` | ✅ | ✅ | STRING | ⚠️ undocumented |
| `scheduledTimeForVisitorGatePassEmailInMin` | ✅ | ✅ | DOUBLE | ⚠️ undocumented |
| `SEAT_BELT_NON_COMPLIANCE_REPORT_EMAIL_ENABLED` | ✅ | ✅ | BOOLEAN | ⚠️ undocumented |
| `seatBeltNonFunctioningIssues` | ✅ | ✅ | LIST | ⚠️ undocumented |
| `seatBeltUndoTimeoutMinutes` | ✅ | ✅ | INTEGER | ⚠️ undocumented |
| `seatBooking` | ✅ | ✅ | STRING | Defines primary Seat Booking application URL. |
| `seatBookingUrl` | ✅ | ✅ | STRING | Defines Seat Booking service URL. |
| `seatBookingV2` | ✅ | ✅ | BOOLEAN | Enables Seat Booking version 2. |
| `seatSanitizationCheck` | ✅ | ✅ | BOOLEAN | Controls seat sanitization validation before booking. |
| `seatScanEnable` | ✅ | ✅ | BOOLEAN | Enables seat QR scanning on booking page. |
| `securityGuard` | ✅ | ✅ | STRING | Defines Security Guard service URL. |
| `sendEmailIneligibility` | ✅ | ✅ | BOOLEAN | ⚠️ undocumented |
| `shareRideCallDriver` | ✅ | ✅ | BOOLEAN | (Inferred) Enables the ability for employees in shared rides to call the driver directly from the app. |
| `showBookingFilter` | ✅ | ✅ | BOOLEAN | Enables toggle to show/hide cancelled bookings. |
| `showBookingHistory` | ✅ | ✅ | BOOLEAN | Enables booking history on app. |
| `showBookingsOfSomeoneElseOnWeb` | ✅ | ✅ | BOOLEAN | ⚠️ undocumented |
| `showConfirmationForLogoutTracking` | ✅ | ✅ | BOOLEAN | ⚠️ undocumented |
| `showEmployeeSearchOnSeatBooking` | ✅ | ✅ | BOOLEAN | Enables colleague search by name. |
| `showFabQRScanner` | ✅ | ✅ | BOOLEAN | Controls QR scanner visibility on FAB. |
| `showMealCountOnBookingForm` | ✅ | ✅ | BOOLEAN | Displays real-time meal availability count on booking form. |
| `showMealPaymentCTA` | ✅ | ✅ | BOOLEAN | Enables meal payment CTA integrated with payment gateways. |
| `showMeetingRoomOnApp` | ✅ | ✅ | BOOLEAN | Enables Meeting Room booking option on mobile app. |
| `showOfficeInfoOnBookingForm` | ✅ | ✅ | BOOLEAN | Displays searchable office address list during booking. |
| `showOrderOfChallengesAfterQRScan` | ✅ | ✅ | BOOLEAN | Displays declaration after QR scan. |
| `showOtherEmployeeDetailsOnSeat` | ✅ | ✅ | BOOLEAN | Controls visibility of other employee booking details on seat view. |
| `showOtpWithoutDigipassGeneration` | ✅ | ✅ | BOOLEAN | Displays cab login/logout OTPs directly on the booking card. |
| `showParking` | ✅ | ✅ | BOOLEAN | Controls parking field visibility in Teams chatbot. |
| `showQRScanner` | ✅ | ✅ | BOOLEAN | Enables Scan QR option in the app. |
| `showQRScannerMeetingCheckIn` | ✅ | ✅ | BOOLEAN | Enables QR-based meeting room check-in. |
| `showRegistrationNumberInputFieldForParking` | ✅ | ✅ | BOOLEAN | Displays vehicle registration number input field during parking booking. |
| `showSanitizationDetails` | ✅ | ✅ | BOOLEAN | Displays sanitization details in the app. |
| `showSeatSearchOnAdminPages` | ✅ | ✅ | BOOLEAN | Enables desk search on admin floor plan pages. |
| `showSeatSearchOnSeatBooking` | ✅ | ✅ | BOOLEAN | Enables desk search by desk number. |
| `showSeparateDigipassFor` | ✅ | ✅ | LIST | Controls resource-level DigiPass generation. |
| `showSeparateDigipassForParking` | ✅ | ✅ | BOOLEAN | Displays separate digipass for parking resources in the mobile app. |
| `showSignedinStateOnEmployeeFloorPlan` | ✅ | ✅ | BOOLEAN | Displays signed-in desk state (green indicator) on Employee Floor Plan. |
| `showTeamCalendarOption` | ✅ | ✅ | BOOLEAN | Displays Team Calendar option in the app. |
| `showVaccinationOptionInSideMenu` | ✅ | ✅ | BOOLEAN | Enables Vaccination status option in the app side menu. |
| `showWomenSafetyInSideMenu` | ✅ | ✅ | BOOLEAN | Displays Women Safety Handbook in mobile side menu. |
| `showWorkinsyncLogoOnSideNav` | ✅ | ✅ | BOOLEAN | Controls WorkInSync logo visibility on sidenav. |
| `shuttleBookingConfirmationNotificationEnabled` | ✅ | ✅ | BOOLEAN | ⚠️ undocumented |
| `shuttleSigninRemainderBufferMins` | ✅ | ✅ | DOUBLE | ⚠️ undocumented |
| `shuttleSigninRemainderNotificationEnabled` | ✅ | ✅ | BOOLEAN | ⚠️ undocumented |
| `singleShiftOperations` | ✅ | ✅ | BOOLEAN | Hides time components in Team Calendar and Preferences for single-shift environments. |
| `smsTrackingEnabled` | ✅ | ✅ | BOOLEAN | ⚠️ undocumented |
| `ssoMandatory` | ✅ | ✅ | BOOLEAN | Removes OTP login option and enforces SSO-only login on mobile. |
| `stopNoShowEmailForShuttle` | ✅ | ✅ | BOOLEAN | ⚠️ undocumented |
| `tagsEnabled` | ✅ | ✅ | LIST | Defines enabled booking tags. |
| `teamCalendarEnabled` | ✅ | ✅ | BOOLEAN | Enables Team Calendar feature. |
| `teamManager` | ✅ | ✅ | STRING | Defines Team Manager service URL. |
| `TIME_FORMAT` | ✅ | ✅ | STRING | Defines time format for UI. |
| `TIME_FORMAT_SERVICES` | ✅ | ✅ | STRING | Defines time format for backend services. |
| `trackAnyShuttleEnabled` | ✅ | ✅ | BOOLEAN | ⚠️ undocumented |
| `transferBookingEnabled` | ✅ | ✅ | BOOLEAN | Adds a 'Transfer Booking Details' column in seat and meeting room reports. |
| `transferBookingTypes` | ✅ | ✅ | LIST | ⚠️ undocumented |
| `transportFieldsMandatory` | ✅ | ✅ | BOOLEAN | Controls whether transport fields are mandatory. |
| `tripRatingMandatoryThreshold` | ✅ | ✅ | JSON | ⚠️ undocumented |
| `upcomingMeetingsEmployeeHome` | ✅ | ✅ | BOOLEAN | Controls display of upcoming meetings on Employee Home. |
| `vaccinationBookingEnabled` | ✅ | ✅ | BOOLEAN | Enables vaccination slot booking feature in the app. |
| `vaccinationBookingUrl` | ✅ | ✅ | STRING | URL for the vaccination booking feature in the app. |
| `vaccinationMaxApprovalDays` | ✅ | ✅ | DOUBLE | Defines maximum days allowed for vaccination request approval. |
| `VAX_STATUS_CHECK_SEEK_RTPCR_EMP` | ✅ | ✅ | BOOLEAN | Allows or restricts RTPCR upload for non-fully vaccinated employees. |
| `vaxEmailEnabled` | ✅ | ✅ | BOOLEAN | ⚠️ undocumented |
| `vehicleCreationDuringParkingEnabled` | ✅ | ✅ | BOOLEAN | Controls vehicle creation during parking booking. |
| `vehicleCreationDuringParkingFor` | ✅ | ✅ | LIST | Controls vehicle creation by type (CAR etc.). |
| `vehicleFuelTypes` | ✅ | ✅ | LIST | ⚠️ undocumented |
| `visitorWidgetEnabled` | ✅ | ✅ | BOOLEAN | Displays visitor management widget on Employee Home. |
| `waitListBookingBufferTimeInMin` | ✅ | ✅ | INTEGER | Defines buffer time in minutes for waitlist bookings. |
| `welcomeEmailEnabled` | ✅ | ✅ | BOOLEAN | Controls sending of welcome emails. |
| `wfhBookingAllowed` | ✅ | ✅ | BOOLEAN | Controls WFH booking visibility in WorkInSync Teams chatbot. |
| `wfhClockinCutOffInMinute` | ✅ | ✅ | DOUBLE | Defines cutoff time for WFH clock-in. |
| `wfhDisabled` | ✅ | ✅ | BOOLEAN | Controls whether WFH booking is enabled or disabled. |
| `wfhReasonList` | ✅ | ✅ | STRING | Work From Home/Remote booking reasons. |
| `wfhType` | ✅ | ✅ | STRING | Controls default Work From Home booking type. |
| `womenSafetyDocUrl` | ✅ | ✅ | STRING | Controls URL of Women Safety Handbook document. |
| `adminExpUi` | ✅ | — | — | ⚠️ undocumented |
| `cardSyncDefaultMinutes` | ✅ | — | — | ⚠️ undocumented |
| `isCheckInReminderOnMsTeamEnabled` | ✅ | — | — | true |
| `allowBookingWithDedicatedSeat` | — | ✅ | LIST | Controls whether dedicated seat holders can book other desks. |
| `approvalFlowInInWfhEnabled` | — | ✅ | BOOLEAN | Enables approval workflow for WFH. |
| `approvalFlowInWfoEnabled` | — | ✅ | BOOLEAN | Enables approval workflow for WFO. |
| `autoPopulateSchedulingForm` | — | ✅ | BOOLEAN | autoPopulateSchedulingForm |
| `autoRejectionForOptIn` | — | ✅ | BOOLEAN | ⚠️ undocumented |
| `blockChecinOutsideGeofence` | — | ✅ | BOOLEAN | ⚠️ undocumented |
| `BOOKING_AGGREGATES_MIGRATION_BUIDS` | — | ✅ | LIST | List of buids that requires migration of booking aggregates. |
| `BOOKING_AGGREGATES_MIGRATION_DELAY_SECONDS` | — | ✅ | INTEGER | Time delay between migration of buids in booking aggregates. |
| `BOOKING_AGGREGATES_MIGRATION_ENABLED` | — | ✅ | BOOLEAN | Checks if migration is enabled for booking aggregates. |
| `BOOKING_AGGREGATES_MIGRATION_TIMEZONES` | — | ✅ | LIST | ⚠️ undocumented |
| `bookingCreationMessage` | — | ✅ | STRING | Defines booking success message. |
| `bookingDisclaimers` | — | ✅ | JSON | Configures booking disclaimer messages. |
| `checkInBookingsType` | — | ✅ | LIST | Defines booking types eligible for check-in. |
| `checkInByTimeChip` | — | ✅ | BOOLEAN | True - Show the check-in-by chip and chevron to provide users with detailed check-in times. False - Do not show the check-in-by chip or the chevron on booking cards. |
| `createSeatBookingWithOfficeBooking` | — | ✅ | BOOLEAN | Auto-creates seat booking with office booking. |
| `crossHierarchyAllocationEnabled` | — | ✅ | BOOLEAN | Defines if cross hierarchy allocation is allowed for RBAC enabled sites. |
| `crossTeamAllocationEnabled` | — | ✅ | BOOLEAN | Allows cross-team desk and employee allocation. |
| `editProfileEnabled` | — | ✅ | BOOLEAN | Controls profile editing. |
| `empHomepageTodaysAvailabilityCard` | — | ✅ | BOOLEAN | Displays full availability card on Employee Home based on enabled modules. |
| `empHomeWidgetMeetingRoomCheckInCutOff` | — | ✅ | INTEGER | Defines check-in cutoff for meeting room check-in from Employee Home widget. |
| `ENABLE_INDOOR_NAVIGATION` | — | ✅ | BOOLEAN | Enables wayfinding/navigation to desks. |
| `enableCheckInForMeetingRoomEmpHome` | — | ✅ | BOOLEAN | Displays the check-in button on the 'Today's Meeting' widget for old room types and allows check-in from Employee Home. |
| `enableMealDayWiseAvailability` | — | ✅ | BOOLEAN | Allows admin to configure meal availability per day. |
| `enableMultiMealSelect` | — | ✅ | BOOLEAN | Enables multi selection on meal booking. |
| `enableOfficeCheckInWithParkingCheckIn` | — | ✅ | BOOLEAN | Links office check-in with parking check-in. |
| `enableParkingCheckOutWithOfficeCheckOut` | — | ✅ | BOOLEAN | Links parking checkout with office checkout. |
| `enablePriorityWiseAutoSlotAllocate` | — | ✅ | BOOLEAN | Assigns slots based on priority order defined by display order value. |
| `enableQRBasedSignOutButton` | — | ✅ | BOOLEAN | Enables QR-based sign-out. |
| `enableStandardMealSelectionFlow` | — | ✅ | BOOLEAN | Enables standard meal booking flow and overrides both normal chip and cart view. |
| `enableSuppportRequest` | — | ✅ | BOOLEAN | ⚠️ undocumented |
| `enableTeamAsResource` | — | ✅ | BOOLEAN | Creates resource entry for newly created teams. |
| `enableTeamCalendarRMView` | — | ✅ | BOOLEAN | Enables hierarchy filter on Team Calendar. |
| `enableWisThemeColors` | — | ✅ | BOOLEAN | Enables dynamic theming using wisThemeColors property. |
| `excludeMealOnlyBookingsFromActiveBookingCount` | — | ✅ | BOOLEAN | Decides whether to exclude meal booking from web/app/bulk from active booking count for any user. |
| `FEATURE_MEDICAL_EMERGENCY_EMAIL_RM` | — | ✅ | BOOLEAN | ⚠️ undocumented |
| `FEATURE_MEDICAL_EMERGENCY_EMAIL_TM` | — | ✅ | BOOLEAN | ⚠️ undocumented |
| `floorKioskCheckinInfo` | — | ✅ | BOOLEAN | Enables real-time desk check-in display on Floor Kiosk. |
| `floorKioskUrl` | — | ✅ | STRING | Floor Kiosk URL. |
| `Floorplan_Legend_Employee_Web_Expanded` | — | ✅ | BOOLEAN | Controls expanded or collapsed legend state on employee web floor plan. |
| `floorPlanViewMeetingRoomsWeb` | — | ✅ | BOOLEAN | Enables floor plan view for meeting rooms on web. |
| `gatepassExpiryMinutes` | — | ✅ | INTEGER | Defines DigiPass expiry duration after booking start. |
| `generateGatepassAdvanceCutOff` | — | ✅ | DOUBLE | Defines minutes before booking start when DigiPass generation becomes active. |
| `genericLabelForDesk` | — | ✅ | STRING | ⚠️ undocumented |
| `hideScheduleButtonFromFab` | — | ✅ | BOOLEAN | ⚠️ undocumented |
| `IPBasedCheckinEnabled` | — | ✅ | BOOLEAN | Restricts web check-in based on IP address. |
| `IS_WIS_CALENDAR` | — | ✅ | BOOLEAN | Enables the Native Rooms view on the Outlook Add-In and allows use of WIS Meeting Rooms with tags and allocations. |
| `isEmloyeeCreationForMsuEnabled` | — | ✅ | BOOLEAN | Controls MSU employee creation. |
| `isEmployeeCreationEnabledForMSu` | — | ✅ | BOOLEAN | Controls MSU employee creation feature. |
| `isTripRatingMandatory` | — | ✅ | BOOLEAN | Controls trip rating requirement. |
| `isWelcomeEmailEnabled` | — | ✅ | BOOLEAN | ⚠️ undocumented |
| `listOfExcludedBuidsForCheckin` | — | ✅ | LIST | Defines BUs excluded from check-in. |
| `liveSupportChatFeatureEnabled` | — | ✅ | BOOLEAN | ⚠️ undocumented |
| `mappedShuttleRouteBufferInMinutes` | — | ✅ | DOUBLE | ⚠️ undocumented |
| `maxEmployeeSelectionWorkplanner` | — | ✅ | INTEGER | Defines maximum number of employees allowed for recurring bookings. |
| `mealFeedbackOptions` | — | ✅ | JSON | Configures meal feedback options. |
| `mealNotifications` | — | ✅ | BOOLEAN | Enable e-mails related to meal bookings for QR. |
| `mealOnlyBulkBookingOptionalHeaders` | — | ✅ | LIST | Optional headers. |
| `meetingRoomsWidgetEnabled` | — | ✅ | BOOLEAN | Controls Meeting Rooms widget visibility. |
| `nearByShuttleStopDistanceInMetre` | — | ✅ | DOUBLE | ⚠️ undocumented |
| `nextDayLogoutEnabled` | — | ✅ | BOOLEAN | Controls visibility of next-day logout shifts in booking form. |
| `NO_SHOW_APPROVAL_ENABLED` | — | ✅ | BOOLEAN | ⚠️ undocumented |
| `notificationOnDeskRelease` | — | ✅ | BOOLEAN | Controls desk release notifications. |
| `officeCheckInReminderEmailCtaEnabled` | — | ✅ | BOOLEAN | Adds Check-in and Cancel CTAs in reminder emails. |
| `OPT_IN_APPROVAL_FLOW_ENABLED` | — | ✅ | BOOLEAN | OPT_IN_APPROVAL_FLOW_ENABLED |
| `optInDeclarationConfig` | — | ✅ | JSON | Declaration configurations for optin. |
| `optInDisplayText` | — | ✅ | JSON | Defines commute opt-in/opt-out display text. |
| `optInOptionsEnabled` | — | ✅ | LIST | ⚠️ undocumented |
| `optInOutV3Declaration` | — | ✅ | JSON | ⚠️ undocumented |
| `optOutPendingEmailSubject` | — | ✅ | STRING | ⚠️ undocumented |
| `parkingReminderNotificationEnabled` | — | ✅ | BOOLEAN | Controls parking reminder notifications. |
| `parkingReminderNotificationMinutes` | — | ✅ | LIST | Defines parking reminder trigger minutes. |
| `parkingSlotBufferTimeInMin` | — | ✅ | STRING | Defines parking allocation buffer time. |
| `pinDisanceThresholdForShuttleStopApi` | — | ✅ | DOUBLE | ⚠️ undocumented |
| `Premise_Floorplan_Legend_Collapsed` | — | ✅ | BOOLEAN | Collapses the legend by default on the Premises floor plan view. |
| `rbacDeskAllocationEnabled` | — | ✅ | BOOLEAN | Enables RBAC-based desk allocation. |
| `REQUIRE_APPROVAL_FOR_OPT_OUT` | — | ✅ | LIST | ⚠️ undocumented |
| `roomEmailIdEmailMessage` | — | ✅ | JSON | Defines meeting room email message templates. |
| `runTransportOptOutJob` | — | ✅ | BOOLEAN | Auto rejection/approval + schedule deletion for opted out users. |
| `safereach` | — | ✅ | STRING | ⚠️ undocumented |
| `safeReachSuccessMessage` | — | ✅ | STRING | Defines success message for Safe Reach. |
| `searchCriteriaVendorKiosk` | — | ✅ | JSON | Used to control search section and placeholder for vendor kiosk and dashboard search. |
| `SEAT_BELT_NON_COMPLIANCE_EMAIL_CONFIGS` | — | ✅ | JSON | ⚠️ undocumented |
| `selfCommuteSubmissionEmailSubject` | — | ✅ | STRING | Defines subject for opt-in/opt-out submission email. |
| `selfCommuteWithdrawalEmailSubject` | — | ✅ | STRING | Defines subject for opt-in/opt-out withdrawal email. |
| `showCanceledCountinAttendanceChart` | — | ✅ | BOOLEAN | Controls visibility of cancelled count in attendance charts. |
| `showConfigureDeskAmenities` | — | ✅ | BOOLEAN | Controls visibility of desk amenities configuration button. |
| `showEmployeeCreation` | — | ✅ | BOOLEAN | ⚠️ undocumented |
| `showMealCost` | — | ✅ | BOOLEAN | Shows meal cost on items for standard meal booking. |
| `showMealTimings` | — | ✅ | BOOLEAN | Shows meal time on items for standard meal booking. |
| `showTeamOnKioskForEmployee` | — | ✅ | BOOLEAN | Displays team name instead of employee ID in kiosk organizer dropdown. |
| `skipOptInTimeWindowValidation` | — | ✅ | BOOLEAN | ⚠️ undocumented |
| `standardTeamColor` | — | ✅ | STRING | Defines default team legend color in floor plan. |
| `tripFeedbackExpressionsMap` | — | ✅ | LIST | ⚠️ undocumented |
| `tripRatingMandatory` | — | ✅ | BOOLEAN | Controls whether trip rating is mandatory. |
| `USER_CLOCK_OUT_REMAINDER_MINUTES` | — | ✅ | INTEGER | ⚠️ undocumented |
| `USERCLOCKOUTREMAINDERMINUTES` | — | ✅ | INTEGER | ⚠️ undocumented |
| `userResourceGroupMappingEnabled` | — | ✅ | BOOLEAN | Indicates whether resource group mapping is enabled for office visibility. |
| `wayfindingPathColor` | — | ✅ | JSON | Controls arrow color customization in wayfinding path. |
| `wfhMinBetweenClockInClockOut` | — | ✅ | DOUBLE | Defines minimum duration between WFH clock-in and clock-out. |
| `WisThemeColors` | — | ✅ | JSON | Defines theme colors for WorkInSync modules. |
| `workplannerCheckInAdvanceCutOffInMinute` | — | ✅ | INTEGER | Defines early check-in limit for Workplanner bookings. |
| `workplannerCheckInDelayCutOffInMinute` | — | ✅ | INTEGER | Defines late check-in limit for Workplanner bookings. |
| `workplannerRecurrenceMaxDays` | — | ✅ | INTEGER | Defines maximum recurrence window in Workplanner. |

## .in-only Configs
_3 properties present on the `.in` server but absent from the `.com` config list._

- `adminExpUi` — ⚠️ undocumented
- `cardSyncDefaultMinutes` — ⚠️ undocumented
- `isCheckInReminderOnMsTeamEnabled` — true

## .com-only Configs
_103 properties present on the `.com` server but absent from the `.in` config list._

- `allowBookingWithDedicatedSeat` — Controls whether dedicated seat holders can book other desks.
- `approvalFlowInInWfhEnabled` — Enables approval workflow for WFH.
- `approvalFlowInWfoEnabled` — Enables approval workflow for WFO.
- `autoPopulateSchedulingForm` — autoPopulateSchedulingForm
- `autoRejectionForOptIn` — ⚠️ undocumented
- `blockChecinOutsideGeofence` — ⚠️ undocumented
- `BOOKING_AGGREGATES_MIGRATION_BUIDS` — List of buids that requires migration of booking aggregates.
- `BOOKING_AGGREGATES_MIGRATION_DELAY_SECONDS` — Time delay between migration of buids in booking aggregates.
- `BOOKING_AGGREGATES_MIGRATION_ENABLED` — Checks if migration is enabled for booking aggregates.
- `BOOKING_AGGREGATES_MIGRATION_TIMEZONES` — ⚠️ undocumented
- `bookingCreationMessage` — Defines booking success message.
- `bookingDisclaimers` — Configures booking disclaimer messages.
- `checkInBookingsType` — Defines booking types eligible for check-in.
- `checkInByTimeChip` — True - Show the check-in-by chip and chevron to provide users with detailed check-in times. False - Do not show the check-in-by chip or the chevron on booking cards.
- `createSeatBookingWithOfficeBooking` — Auto-creates seat booking with office booking.
- `crossHierarchyAllocationEnabled` — Defines if cross hierarchy allocation is allowed for RBAC enabled sites.
- `crossTeamAllocationEnabled` — Allows cross-team desk and employee allocation.
- `editProfileEnabled` — Controls profile editing.
- `empHomepageTodaysAvailabilityCard` — Displays full availability card on Employee Home based on enabled modules.
- `empHomeWidgetMeetingRoomCheckInCutOff` — Defines check-in cutoff for meeting room check-in from Employee Home widget.
- `ENABLE_INDOOR_NAVIGATION` — Enables wayfinding/navigation to desks.
- `enableCheckInForMeetingRoomEmpHome` — Displays the check-in button on the 'Today's Meeting' widget for old room types and allows check-in from Employee Home.
- `enableMealDayWiseAvailability` — Allows admin to configure meal availability per day.
- `enableMultiMealSelect` — Enables multi selection on meal booking.
- `enableOfficeCheckInWithParkingCheckIn` — Links office check-in with parking check-in.
- `enableParkingCheckOutWithOfficeCheckOut` — Links parking checkout with office checkout.
- `enablePriorityWiseAutoSlotAllocate` — Assigns slots based on priority order defined by display order value.
- `enableQRBasedSignOutButton` — Enables QR-based sign-out.
- `enableStandardMealSelectionFlow` — Enables standard meal booking flow and overrides both normal chip and cart view.
- `enableSuppportRequest` — ⚠️ undocumented
- `enableTeamAsResource` — Creates resource entry for newly created teams.
- `enableTeamCalendarRMView` — Enables hierarchy filter on Team Calendar.
- `enableWisThemeColors` — Enables dynamic theming using wisThemeColors property.
- `excludeMealOnlyBookingsFromActiveBookingCount` — Decides whether to exclude meal booking from web/app/bulk from active booking count for any user.
- `FEATURE_MEDICAL_EMERGENCY_EMAIL_RM` — ⚠️ undocumented
- `FEATURE_MEDICAL_EMERGENCY_EMAIL_TM` — ⚠️ undocumented
- `floorKioskCheckinInfo` — Enables real-time desk check-in display on Floor Kiosk.
- `floorKioskUrl` — Floor Kiosk URL.
- `Floorplan_Legend_Employee_Web_Expanded` — Controls expanded or collapsed legend state on employee web floor plan.
- `floorPlanViewMeetingRoomsWeb` — Enables floor plan view for meeting rooms on web.
- `gatepassExpiryMinutes` — Defines DigiPass expiry duration after booking start.
- `generateGatepassAdvanceCutOff` — Defines minutes before booking start when DigiPass generation becomes active.
- `genericLabelForDesk` — ⚠️ undocumented
- `hideScheduleButtonFromFab` — ⚠️ undocumented
- `IPBasedCheckinEnabled` — Restricts web check-in based on IP address.
- `IS_WIS_CALENDAR` — Enables the Native Rooms view on the Outlook Add-In and allows use of WIS Meeting Rooms with tags and allocations.
- `isEmloyeeCreationForMsuEnabled` — Controls MSU employee creation.
- `isEmployeeCreationEnabledForMSu` — Controls MSU employee creation feature.
- `isTripRatingMandatory` — Controls trip rating requirement.
- `isWelcomeEmailEnabled` — ⚠️ undocumented
- `listOfExcludedBuidsForCheckin` — Defines BUs excluded from check-in.
- `liveSupportChatFeatureEnabled` — ⚠️ undocumented
- `mappedShuttleRouteBufferInMinutes` — ⚠️ undocumented
- `maxEmployeeSelectionWorkplanner` — Defines maximum number of employees allowed for recurring bookings.
- `mealFeedbackOptions` — Configures meal feedback options.
- `mealNotifications` — Enable e-mails related to meal bookings for QR.
- `mealOnlyBulkBookingOptionalHeaders` — Optional headers.
- `meetingRoomsWidgetEnabled` — Controls Meeting Rooms widget visibility.
- `nearByShuttleStopDistanceInMetre` — ⚠️ undocumented
- `nextDayLogoutEnabled` — Controls visibility of next-day logout shifts in booking form.
- `NO_SHOW_APPROVAL_ENABLED` — ⚠️ undocumented
- `notificationOnDeskRelease` — Controls desk release notifications.
- `officeCheckInReminderEmailCtaEnabled` — Adds Check-in and Cancel CTAs in reminder emails.
- `OPT_IN_APPROVAL_FLOW_ENABLED` — OPT_IN_APPROVAL_FLOW_ENABLED
- `optInDeclarationConfig` — Declaration configurations for optin.
- `optInDisplayText` — Defines commute opt-in/opt-out display text.
- `optInOptionsEnabled` — ⚠️ undocumented
- `optInOutV3Declaration` — ⚠️ undocumented
- `optOutPendingEmailSubject` — ⚠️ undocumented
- `parkingReminderNotificationEnabled` — Controls parking reminder notifications.
- `parkingReminderNotificationMinutes` — Defines parking reminder trigger minutes.
- `parkingSlotBufferTimeInMin` — Defines parking allocation buffer time.
- `pinDisanceThresholdForShuttleStopApi` — ⚠️ undocumented
- `Premise_Floorplan_Legend_Collapsed` — Collapses the legend by default on the Premises floor plan view.
- `rbacDeskAllocationEnabled` — Enables RBAC-based desk allocation.
- `REQUIRE_APPROVAL_FOR_OPT_OUT` — ⚠️ undocumented
- `roomEmailIdEmailMessage` — Defines meeting room email message templates.
- `runTransportOptOutJob` — Auto rejection/approval + schedule deletion for opted out users.
- `safereach` — ⚠️ undocumented
- `safeReachSuccessMessage` — Defines success message for Safe Reach.
- `searchCriteriaVendorKiosk` — Used to control search section and placeholder for vendor kiosk and dashboard search.
- `SEAT_BELT_NON_COMPLIANCE_EMAIL_CONFIGS` — ⚠️ undocumented
- `selfCommuteSubmissionEmailSubject` — Defines subject for opt-in/opt-out submission email.
- `selfCommuteWithdrawalEmailSubject` — Defines subject for opt-in/opt-out withdrawal email.
- `showCanceledCountinAttendanceChart` — Controls visibility of cancelled count in attendance charts.
- `showConfigureDeskAmenities` — Controls visibility of desk amenities configuration button.
- `showEmployeeCreation` — ⚠️ undocumented
- `showMealCost` — Shows meal cost on items for standard meal booking.
- `showMealTimings` — Shows meal time on items for standard meal booking.
- `showTeamOnKioskForEmployee` — Displays team name instead of employee ID in kiosk organizer dropdown.
- `skipOptInTimeWindowValidation` — ⚠️ undocumented
- `standardTeamColor` — Defines default team legend color in floor plan.
- `tripFeedbackExpressionsMap` — ⚠️ undocumented
- `tripRatingMandatory` — Controls whether trip rating is mandatory.
- `USER_CLOCK_OUT_REMAINDER_MINUTES` — ⚠️ undocumented
- `USERCLOCKOUTREMAINDERMINUTES` — ⚠️ undocumented
- `userResourceGroupMappingEnabled` — Indicates whether resource group mapping is enabled for office visibility.
- `wayfindingPathColor` — Controls arrow color customization in wayfinding path.
- `wfhMinBetweenClockInClockOut` — Defines minimum duration between WFH clock-in and clock-out.
- `WisThemeColors` — Defines theme colors for WorkInSync modules.
- `workplannerCheckInAdvanceCutOffInMinute` — Defines early check-in limit for Workplanner bookings.
- `workplannerCheckInDelayCutOffInMinute` — Defines late check-in limit for Workplanner bookings.
- `workplannerRecurrenceMaxDays` — Defines maximum recurrence window in Workplanner.

## Missing Descriptions
_78 properties have no description in any source (PMS config files, PMS Description Cleaned, or wis_unique_configs)._
Contact the owning service team for documentation.

- `ADDRESS_CHANGE_HOME_TO_OFFICE_DISTANCE_VALIDATION`
- `ADDRESS_CHANGE_RADIAL_DISTANCE_VALIDATION`
- `ADDRESS_CHANGE_RESTRICTED_AREA_VALIDATION`
- `ADDRESS_CHANGE_TRANSPORT_BOUNDARY_VALIDATION`
- `adminExpUi`
- `airtelBuid`
- `allowPeerOrMarshalReporting`
- `APPROVAL_POST_NO_SHOW_CHECK_BUFFER`
- `autoRejectionForOptIn`
- `averageOverallTripFeedbackCalculation`
- `bannerEndTime`
- `bannerStartTime`
- `blockChecinOutsideGeofence`
- `BOOKING_AGGREGATES_MIGRATION_TIMEZONES`
- `cardSyncDefaultMinutes`
- `CITY_DISTRICT_MAPPINGS`
- `commentsMandatoryOnRating`
- `confirmationMessageForLogoutTracking`
- `contactTHDReasons`
- `DIRECTION`
- `enableSuppportRequest`
- `enableTransportBookingBulkUpload`
- `FEATURE_MEDICAL_EMERGENCY_EMAIL_RM`
- `FEATURE_MEDICAL_EMERGENCY_EMAIL_TM`
- `forecastingEfficiancy`
- `genericLabelForDesk`
- `hideBookingTimeMealOnly`
- `hideScheduleButtonFromFab`
- `isAutoProvision`
- `isReportingAndAnalyticEnable`
- `isWelcomeEmailEnabled`
- `jobTitleWiseCalenderInDays`
- `listOfEligibleBuidsForBusNotification`
- `liveSupportChatFeatureEnabled`
- `mappedShuttleRouteBufferInMinutes`
- `maximumCharacterLimit`
- `medicalEmergencyRequest`
- `microBookingEnabled`
- `MOBILE_APP_BANNERS`
- `nearByShuttleStopDistanceInMetre`
- `NO_SHOW_APPROVAL_ENABLED`
- `optInOptionsEnabled`
- `optInOutV3Declaration`
- `optOutPendingEmailSubject`
- `pinDisanceThresholdForShuttleStopApi`
- `PRE_TRIP_CANCELLATION_NOTIFICATION_MINUTES_BEFORE_LOGIN_CANCELLATION_CUTOFF`
- `PRE_TRIP_CANCELLATION_NOTIFICATION_MINUTES_BEFORE_LOGOUT_CANCELLATION_CUTOFF`
- `profileRegistrationEmailSubject`
- `promotionBannerUrl`
- `promotionDisplayText`
- `removeFloorsMappedToRooms`
- `REQUIRE_APPROVAL_FOR_OPT_OUT`
- `safereach`
- `sanitisationFloorPlanUrl`
- `scheduled_reminder_notification_enabled_buids`
- `scheduledTimeForVisitorGatePassEmailInMin`
- `SEAT_BELT_NON_COMPLIANCE_EMAIL_CONFIGS`
- `SEAT_BELT_NON_COMPLIANCE_REPORT_EMAIL_ENABLED`
- `seatBeltNonFunctioningIssues`
- `seatBeltUndoTimeoutMinutes`
- `sendEmailIneligibility`
- `showBookingsOfSomeoneElseOnWeb`
- `showConfirmationForLogoutTracking`
- `showEmployeeCreation`
- `shuttleBookingConfirmationNotificationEnabled`
- `shuttleSigninRemainderBufferMins`
- `shuttleSigninRemainderNotificationEnabled`
- `skipOptInTimeWindowValidation`
- `smsTrackingEnabled`
- `stopNoShowEmailForShuttle`
- `trackAnyShuttleEnabled`
- `transferBookingTypes`
- `tripFeedbackExpressionsMap`
- `tripRatingMandatoryThreshold`
- `USER_CLOCK_OUT_REMAINDER_MINUTES`
- `USERCLOCKOUTREMAINDERMINUTES`
- `vaxEmailEnabled`
- `vehicleFuelTypes`

_Last updated: 2026-05-26_
_Source: [[sources/pms-configs-in-all-wis-configs]] | [[sources/pms-configs-com-wis-service-configs]]_
