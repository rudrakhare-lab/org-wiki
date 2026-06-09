---
title: "Meeting Rooms — Config Properties"
service: MEETING_ROOMS
total_configs: 112
servers: [in, com]
generated: 2026-06-09
type: config
module: meeting-rooms
---

# Meeting Rooms — Config Properties

Auto-generated on 2026-06-09. Total configs: **112**.

| Property | Description | Type | Default | Server |
|----------|-------------|------|---------|--------|
| `AD_HOC_MEETING` | Enables auto check-in for room bookings within this defined window - this value is set in minutes. | INTEGER |  | both |
| `advanceBookingLimitInMinutes` | Controls the window of advance booking for users to make room bookings | INTEGER |  | both |
| `beginHour` | This configuration defines the begin time of the bookable time in the meeting rooms timeline - room level configuration. Integer value, 0-24. | INTEGER |  | both |
| `BLOCK_CALENDAR_FOR_X_MINS` | Controls how long the room's calendar is blocked around a meeting, in minutes. | INTEGER |  | both |
| `BUILDING_PREMISE_NAME` | On stratus sites, it controls the name of the entity on outlook | STRING |  | both |
| `BULK_UPLOAD_ENABLED` | Enables the room bulk upload option in the Meeting Rooms Settings page | BOOLEAN |  | both |
| `BULK_UPLOAD_HEADERS` | Defines the column headers for meeting room bulk upload, this cannot be changed. Do not alter this. | LIST |  | both |
| `CANCEL_EVENT_PIN_VERIFICATION_ENABLE` | Enables secure cancellation or ending of meetings via meeting room kiosk using OTP verification. | BOOLEAN |  | both |
| `CATERING_ORDER_STATUS_LIST` | This property pertains to the catering feature within the Meeting Rooms module. It allows administrators to define the various statuses that can be assigned to catering orders on the catering dashb... | JSON |  | both |
| `cateringLimits` | Defines cut-off times for modifying or cancelling catering orders based on participant count. | LIST |  | .com only |
| `CheckOutCTARooms` | Controls the visibility of the checkout button against room bookings. Not dependent on checkin button. | BOOLEAN |  | .com only |
| `colorVCStatsIconsKiosk` | Meeting Rooms Kiosk - Defines the color for the VC stats displayed on the kiosk screen. | STRING |  | .com only |
| `CONSENT_TYPE` | Defines consent type configuration at admin or user level. | STRING |  | both |
| `Cost_Center_Catering` | Catering workflow - Controls cost center field availability for catering requests workflow | BOOLEAN |  | both |
| `Cost_Center_Max_Len` | Catering workflow - Defines maximum character limit for cost center input. | INTEGER |  | both |
| `Cost_Center_Min_Len` | Catering workflow - Defines minimum character limit for cost center input. | INTEGER |  | both |
| `Create_Meeting_Room` | Controls visibility of the Create Room button in the Meeting Rooms settings page. | BOOLEAN |  | both |
| `CREATE_PREMISE_IF_IT_DOESNT_EXIST` | Allows the system in creation of premise, if premise does not exist | BOOLEAN |  | both |
| `DEACTIVATION_TYPE` | Control the action of deactivation of meeting room | STRING |  | both |
| `defaultAdvanceBookingLimitForBypass` | Defines the threshold for the Advance Booking Limit bypass privilege. | INTEGER |  | .com only |
| `defaultMaxDurationForBypass` | Defines the threshold for the maximum duration bypass privilege. | INTEGER |  | .com only |
| `dynamicFieldLabel` | Customizes the label text for the meeting request section on meeting booking form. | JSON |  | both |
| `dynamicFieldOnRooms` | Displays dynamic fields during meeting room creation - i.e Meeting Rooms request section | BOOLEAN |  | both |
| `dynamicFieldsConfigForRooms` | This controls the dynamic fields aka custom fields for the catering workflow where we can define different types of fields - their header and the type of input values. You can find the output of th... | LIST |  | both |
| `dynamicFieldUserEmails` | Defines email recipients for dynamic field notifications. | LIST |  | both |
| `ENABLE_AUTO_MEETING_ROOM_SYNC` | Automatically runs meeting room sync when enabled. | BOOLEAN |  | both |
| `ENABLE_MEETING_CATERING` | Catering workflow - Enables catering functionality in meeting rooms, to see the Catering Request option in room booking form. | BOOLEAN |  | both |
| `ENABLE_WITH_PRINCIPAL_NAME` | Uses email prefix as visitor name when name is unavailable. | BOOLEAN |  | both |
| `enableCheckInForMeetingRoom` | Enables meeting room check-in button on the web and app. | BOOLEAN |  | .com only |
| `enableCheckInReminderEmailForRoom` | Enables check-in reminder emails for meeting rooms. | BOOLEAN |  | both |
| `enableCheckInReminderNotificationForRoom` | Sends app notification reminder for meeting room check-in. | BOOLEAN |  | both |
| `EnableMRMailCancel` | Sends mail over email when meeting room cancellation is triggered via kiosk to the organiser | BOOLEAN |  | both |
| `EnableMROTPCancel` | Controls OTP verification over email when meeting room cancellation is triggered via kiosk to the organiser | BOOLEAN |  | both |
| `endHour` | This configuration defines the end time of the bookable time in the meeting rooms timeline - room level configuration. Integer value, 0-24. | INTEGER |  | both |
| `endTimeBufferRoomBookingBuidLevel` | Defines end time buffer for meeting room bookings at BUID level for the Buffer Time workflow in catering/IT request. | BOOLEAN |  | .com only |
| `endTimeBufferRoomBookingRoomLevel` | Defines end time buffer for meeting room bookings at room level for the Buffer Time workflow in catering/IT request. | INTEGER |  | .com only |
| `facilityMailList` | For IT request workflow to control who receives the IT request emails. | STRING |  | .com only |
| `FLOOR_PREMISE_NAME` | - | STRING |  | .com only |
| `HideCancelButton` | Controls visibility of the Cancel button on the Meeting Room Kiosk at room level. | BOOLEAN |  | both |
| `HideCheckInButton` | Controls visibility of the check-in button on the Meeting Rooms Kiosk screen | BOOLEAN |  | both |
| `HideEndButton` | Controls visibility of the End Now button on the Meeting Rooms Kiosk screen | BOOLEAN |  | both |
| `HideExtendButton` | Controls visibility of the Extend on the Meeting Rooms Kiosk screen | BOOLEAN |  | both |
| `HideMeetingTitle` | Controls visibility of the meeting title sendRoomBookingEmailToAllParticipants | BOOLEAN |  | both |
| `HideOrganizerName` | Controls visibility of the organizer name on the Meeting Rooms Kiosk screen | BOOLEAN |  | both |
| `HideStartMeetingButton` | Controls visibility of the Start Meeting button on the Meeting Room Kiosk. | BOOLEAN |  | both |
| `iadeaLightsBrightness` | This property controls colour and brightness of led lights of IADEA Device for Meeting Rooms Kiosk | JSON |  | both |
| `INVITE_VISITOR_FROM_ROOMS` | Enabled the Meeting and Visitor booking workflow from meeting booking from on web and mobile. | BOOLEAN |  | both |
| `INVITE_VISITOR_ROOMS` | Enables Invite Visitor tab within the Meeting Rooms Outlook Add-in. | BOOLEAN |  | both |
| `IS_RICHEMONT` | Enables Richemont-specific workflow configurations. | BOOLEAN |  | both |
| `IS_WIS_CALENDAR` | Indicates whether the BUID has Native Meeting Room setup enabled. | BOOLEAN |  | both |
| `IT_REQUEST_OUTLOOK_ADDIN` | Enables IT request functionality within the WorkInSync Outlook Add-in. | BOOLEAN |  | .com only |
| `itemsDynamicFields` | dynamic fields for IT Request | LIST |  | .com only |
| `KIOSK_IMAGE_FOR_OFFICE` | Controls whether a kiosk image is applied at the office level (instead of per-room / per-kiosk only). | STRING |  | both |
| `kioskDefaultImage` | Defines the default image displayed on kiosks across the BUID. | STRING |  | both |
| `maxApprovalRequest` | For resource approval workflow - defines maximum overlapping approval requests per user. | INTEGER |  | .com only |
| `maxDurationInMinutes` | Defines maximum duration for meeting room bookings. | INTEGER |  | both |
| `mealMailList` | Defines email recipients for catering-related communications. | STRING |  | both |
| `MEETING_EMAIL_OTP_TO_AUTHENTICATE` | Controls the OTP notifcation send via email to verify end or cancellation of meeting bookings via meeting room kiosk | BOOLEAN |  | both |
| `MEETING_END_NOTIFICATION` | Controls the notification sent when the meeting has ended via meeting room kiosk | INTEGER |  | both |
| `MEETING_ROOM_RELEASE_IF_NO_CHECKIN` | Releases room if check-in does not occur within configured minutes. | INTEGER |  | both |
| `MEETING_ROOM_SUBSCRIPTION_JOB_EMAIL_LIST` | Defines email recipients for room subscription status. | LIST |  | .com only |
| `MEETING_ROOM_SYNC_JOB_EMAIL_LIST` | Defines email recipients for meeting room sync job notifications. | LIST |  | both |
| `MEETING_START_NOTIFICATION` | Controls the notification sent when the meeting has started via meeting room kiosk | INTEGER |  | both |
| `Meeting_Title_Catering_Order` | Controls display of meeting title in the Catering Dashboard detailed view | BOOLEAN |  | both |
| `meetingRoomCheckInCutOff` | Defines the cutoff for the visibility of the checkin button on the meeting rooms web and mobile view. | INTEGER |  | both |
| `meetingRoomCost` | Controls display of meeting room cost in the UI for web and mobile view. | BOOLEAN |  | both |
| `meetingStartTimeCuttoffInMinutes` | Defines the cutoff for how much prior to that start time the booking can be created. Its a booking creation cutoff time. Value is in minutes. | INTEGER |  | both |
| `minDurationInMinutes` | Defines minimum duration need for a meeting room booking. | INTEGER |  | .com only |
| `MULTI_DOMAIN` | Controls multiple domains in a single BUID (for clients like MAF) | BOOLEAN |  | both |
| `noAutoCheckinKiosk` | When Checkin is hidden, the kiosk auto-checks into the booking. This controls that auto check-in behavior on Meeting Rooms Kiosk. | BOOLEAN |  | .com only |
| `office_name` | The office label used to scope rooms and MR configs to that office. If it doesn't match the server office name, rooms/configs for that office will show as expected. | STRING |  | both |
| `OFFICE_PREMISE_NAME` | Defines the office mapping for meeting room via meeting room sync. | STRING |  | both |
| `organiserBookingEmailsMeetingRooms` | Controls whether the organizer receives booking emails. | BOOLEAN |  | both |
| `organiserPersonaMeetingRooms` | Controls email notifications for organizer persona in Meeting Rooms module. | JSON |  | .com only |
| `otherUsersPersonaMeetingRooms` | Controls email notifications for other participant personas in Meeting Rooms module. | JSON |  | .com only |
| `OUTLOOK_WO_ADMIN_CONSENT` | This controls the room email id field in the room details section of Meeting Rooms Settings page. This is needed for an integrated setup. | BOOLEAN |  | both |
| `OutlookNativeRoomSetup` | Hybrid setup for outlook integration | BOOLEAN |  | .com only |
| `participantPersonaMeetingRooms` | Controls email notifications for participant personas in the Meeting Rooms module. | JSON |  | .com only |
| `recurringBookings` | Enables recurring booking flow for meeting rooms for both integrated and native. | BOOLEAN |  | .com only |
| `RELEASE_MEETING_ROOM` | Controls the auto-release logic for rooms, based on the other MR configs (especially MEETING_ROOM_RELEASE_IF_NO_CHECKIN). | BOOLEAN |  | both |
| `RELEASE_ROOM_CANCEL_MEETING` | Controls whether releasing a room also cancels the meeting from users calendars. | BOOLEAN |  | both |
| `ReleaseRoom` | Controls if release room functionality is enabled | BOOLEAN |  | both |
| `releaseRoom` | Not used | BOOLEAN |  | .com only |
| `releaseRoomEmailList` | Additional email recipients for release room notifications, other than organiser of the meeting which was released | LIST |  | both |
| `rommEnabled` | Controls the enablement of the room for booking | BOOLEAN |  | both |
| `Room_As_Organizer` | Controls the enablement of the room as organiser workflow for the meeting room kiosk | BOOLEAN |  | both |
| `room_cancel_cutoff` | Defines cancellation cut-off time in minutes for meeting room bookings. | INTEGER |  | both |
| `Room_Kiosk_With_Cisco` | Meeting Rooms Kiosk workflow - Enables Cisco-related fields in the Meeting Rooms settings page under the Kiosk column | BOOLEAN |  | both |
| `room_name` | Mapping of meeting room name via outlook sync | STRING |  | both |
| `Room_Special_Request_Enable` | Controls visibility of the Meeting Request section in the meeting booking form - on web view. | BOOLEAN |  | both |
| `RoomBookingEmailEnabled` | Controls the emails sent to additional recipients | BOOLEAN |  | both |
| `roomBookingsEmailList` | Defines additional recipients for meeting room booking emails. | LIST |  | both |
| `roomCheckinQrOnKiosk` | Controls display of meeting room QR code on kiosk at room level. | BOOLEAN |  | .com only |
| `roomStatsKiosk` | Controls the visibility of the checkout button against room bookings. Not dependent on checkin button. | BOOLEAN |  | .com only |
| `roomWithApproval` | Enables approval workflow for meeting rooms on web and mobile. | BOOLEAN |  | .com only |
| `roomWithApprovalBuidLevel` | Enables meeting room approval workflow at BUID level. | BOOLEAN |  | .com only |
| `SEND_INVITE_TO_ALL_EMPLOYEES` | Controls recipients of native meeting room booking emails. | BOOLEAN |  | both |
| `sendRoomBookingEmailToAllParticipants` | Controls whether booking emails are sent to all participants. | BOOLEAN |  | both |
| `Show_Room_If_Not_Eligible` | Controls visibility of ineligible rooms. | BOOLEAN |  | both |
| `SHOW_UPCOMING_BOOKINGS_TIME` | Meeting Rooms Kiosk - Defines how prior to the meeting start time the kiosk screen will turn yellow to let users checkin to their booking. Value set in minutes | INTEGER |  | both |
| `showOrganiserNameAddInTimeline` | Show organizer name on booking timeline on outlook addin | BOOLEAN |  | .com only |
| `showWisLogo` | Toggles display of the MoveInSync logo on meeting room kiosk and calendar integration UIs | BOOLEAN |  | both |
| `smartRoomRecommendation` | Enables AI-based smart room recommendation. | BOOLEAN |  | .com only |
| `startTimeBufferRoomBookingBuidLevel` | Defines start time buffer for meeting room bookings at BUID level for the Buffer Time workflow in catering/IT request. | BOOLEAN |  | .com only |
| `startTimeBufferRoomBookingRoomLevel` | Defines start time buffer at individual room level. | INTEGER |  | .com only |
| `SyncMeetingRooms` | Enables the Sync Rooms button for integrated setups in the Meeting Room Settings page | BOOLEAN |  | both |
| `textMessageForKiosk` | Defines text displayed on the kiosk. | JSON |  | .com only |
| `textOnKiosk` | Controls additional text visibility on the Meeting Rooms Kiosk screen | BOOLEAN |  | .com only |
| `timezone` | Defines the timezone of that office | STRING |  | both |
| `weekdays` | Defines the set of days considered working days for that office's rooms | LIST |  | both |
| `WEIGHT_CAPACITY` | Defines weight configuration for AI room recommendation based on capacity. | DOUBLE |  | .com only |
| `WEIGHT_HISTORICAL` | Defines weight configuration for AI room recommendation based on historical usage. | DOUBLE |  | .com only |
