---
type: config
module: meeting-rooms
servers:
  - in
  - com
last_updated: 2026-05-26
sources:
  in: "[[sources/pms-configs-in-all-wis-configs]]"
  com: "[[sources/pms-configs-com-wis-service-configs]]"
---

# Meeting Rooms Service — Config Properties

## Service
Meeting Rooms Service. Linked module: [[modules/meeting-rooms]].

_Source: [[sources/pms-configs-in-all-wis-configs]] | [[sources/pms-configs-com-wis-service-configs]]_

## Config Comparison

> **Server key:** ✅ = property present in that server's config list | — = absent
> **Description source:** `.com` description preferred; falls back to `.in`, PMS Description Cleaned, then `wis_unique_configs`.
> ⚠️ `undocumented` = no description found in any source — contact the owning team.

| Property Name | .in | .com | Data Type | Description |
|---------------|-----|------|-----------|-------------|
| `AD_HOC_MEETING` | ✅ | ✅ | INTEGER | Enables auto check-in for room bookings within this defined window - this value is set in minutes. |
| `advanceBookingLimitInMinutes` | ✅ | ✅ | INTEGER | Controls the window of advance booking for users to make room bookings |
| `beginHour` | ✅ | ✅ | INTEGER | This configuration defines the begin time of the bookable time in the meeting rooms timeline - room level configuration. Integer value, 0-24. |
| `BLOCK_CALENDAR_FOR_X_MINS` | ✅ | ✅ | INTEGER | Controls how long the room's calendar is blocked around a meeting, in minutes. |
| `BUILDING_PREMISE_NAME` | ✅ | ✅ | STRING | On stratus sites, it controls the name of the entity on outlook |
| `BULK_UPLOAD_ENABLED` | ✅ | ✅ | BOOLEAN | Enables the room bulk upload option in the Meeting Rooms Settings page |
| `BULK_UPLOAD_HEADERS` | ✅ | ✅ | LIST | Defines the column headers for meeting room bulk upload, this cannot be changed. Do not alter this. |
| `CANCEL_EVENT_PIN_VERIFICATION_ENABLE` | ✅ | ✅ | BOOLEAN | Enables secure cancellation or ending of meetings via meeting room kiosk using OTP verification. |
| `CATERING_ORDER_STATUS_LIST` | ✅ | ✅ | JSON | This property pertains to the catering feature within the Meeting Rooms module. It allows administrators to define the various statuses that can be assigned to catering orders on the catering dashboard. Recognizing that terminology may differ across organizations, this list is configurable to accommodate specific needs. The sequence of statuses specified here will directly reflect the order in which they appear on the catering dashboard. |
| `CONSENT_TYPE` | ✅ | ✅ | STRING | Defines consent type configuration at admin or user level. |
| `Cost_Center_Catering` | ✅ | ✅ | BOOLEAN | Catering workflow - Controls cost center field availability for catering requests workflow |
| `Cost_Center_Max_Len` | ✅ | ✅ | INTEGER | Catering workflow - Defines maximum character limit for cost center input. |
| `Cost_Center_Min_Len` | ✅ | ✅ | INTEGER | Catering workflow - Defines minimum character limit for cost center input. |
| `Create_Meeting_Room` | ✅ | ✅ | BOOLEAN | Controls visibility of the Create Room button in the Meeting Rooms settings page. |
| `CREATE_PREMISE_IF_IT_DOESNT_EXIST` | ✅ | ✅ | BOOLEAN | Allows the system in creation of premise, if premise does not exist |
| `DEACTIVATION_TYPE` | ✅ | ✅ | STRING | Control the action of deactivation of meeting room |
| `dynamicFieldLabel` | ✅ | ✅ | JSON | Customizes the label text for the meeting request section on meeting booking form. |
| `dynamicFieldOnRooms` | ✅ | ✅ | BOOLEAN | Displays dynamic fields during meeting room creation - i.e Meeting Rooms request section |
| `dynamicFieldsConfigForRooms` | ✅ | ✅ | LIST | This controls the dynamic fields aka custom fields for the catering workflow where we can define different types of fields - their header and the type of input values. You can find the output of this dynamic field configuration under Delivery instructions of the catering workflow on both the web and Outlook Add-In |
| `dynamicFieldUserEmails` | ✅ | ✅ | LIST | Defines email recipients for dynamic field notifications. |
| `ENABLE_AUTO_MEETING_ROOM_SYNC` | ✅ | ✅ | BOOLEAN | Automatically runs meeting room sync when enabled. |
| `ENABLE_MEETING_CATERING` | ✅ | ✅ | BOOLEAN | Catering workflow - Enables catering functionality in meeting rooms, to see the Catering Request option in room booking form. |
| `ENABLE_WITH_PRINCIPAL_NAME` | ✅ | ✅ | BOOLEAN | Uses email prefix as visitor name when name is unavailable. |
| `enableCheckInReminderEmailForRoom` | ✅ | ✅ | BOOLEAN | Enables check-in reminder emails for meeting rooms. |
| `enableCheckInReminderNotificationForRoom` | ✅ | ✅ | BOOLEAN | Sends app notification reminder for meeting room check-in. |
| `EnableMRMailCancel` | ✅ | ✅ | BOOLEAN | Sends mail over email when meeting room cancellation is triggered via kiosk to the organiser |
| `EnableMROTPCancel` | ✅ | ✅ | BOOLEAN | Controls OTP verification over email when meeting room cancellation is triggered via kiosk to the organiser |
| `endHour` | ✅ | ✅ | INTEGER | This configuration defines the end time of the bookable time in the meeting rooms timeline - room level configuration. Integer value, 0-24. |
| `HideCancelButton` | ✅ | ✅ | BOOLEAN | Controls visibility of the Cancel button on the Meeting Room Kiosk at room level. |
| `HideCheckInButton` | ✅ | ✅ | BOOLEAN | Controls visibility of the check-in button on the Meeting Rooms Kiosk screen |
| `HideEndButton` | ✅ | ✅ | BOOLEAN | Controls visibility of the End Now button on the Meeting Rooms Kiosk screen |
| `HideExtendButton` | ✅ | ✅ | BOOLEAN | Controls visibility of the Extend on the Meeting Rooms Kiosk screen |
| `HideMeetingTitle` | ✅ | ✅ | BOOLEAN | Controls visibility of the meeting title sendRoomBookingEmailToAllParticipants |
| `HideOrganizerName` | ✅ | ✅ | BOOLEAN | Controls visibility of the organizer name on the Meeting Rooms Kiosk screen |
| `HideStartMeetingButton` | ✅ | ✅ | BOOLEAN | Controls visibility of the Start Meeting button on the Meeting Room Kiosk. |
| `iadeaLightsBrightness` | ✅ | ✅ | JSON | This property controls colour and brightness of led lights of IADEA Device for Meeting Rooms Kiosk |
| `INVITE_VISITOR_FROM_ROOMS` | ✅ | ✅ | BOOLEAN | Enabled the Meeting and Visitor booking workflow from meeting booking from on web and mobile. |
| `INVITE_VISITOR_ROOMS` | ✅ | ✅ | BOOLEAN | Enables Invite Visitor tab within the Meeting Rooms Outlook Add-in. |
| `IS_RICHEMONT` | ✅ | ✅ | BOOLEAN | Enables Richemont-specific workflow configurations. |
| `IS_WIS_CALENDAR` | ✅ | ✅ | BOOLEAN | Indicates whether the BUID has Native Meeting Room setup enabled. |
| `KIOSK_IMAGE_FOR_OFFICE` | ✅ | ✅ | STRING | Controls whether a kiosk image is applied at the office level (instead of per-room / per-kiosk only). |
| `kioskDefaultImage` | ✅ | ✅ | STRING | Defines the default image displayed on kiosks across the BUID. |
| `maxDurationInMinutes` | ✅ | ✅ | INTEGER | Defines maximum duration for meeting room bookings. |
| `mealMailList` | ✅ | ✅ | STRING | Defines email recipients for catering-related communications. |
| `MEETING_EMAIL_OTP_TO_AUTHENTICATE` | ✅ | ✅ | BOOLEAN | Controls the OTP notifcation send via email to verify end or cancellation of meeting bookings via meeting room kiosk |
| `MEETING_END_NOTIFICATION` | ✅ | ✅ | INTEGER | Controls the notification sent when the meeting has ended via meeting room kiosk |
| `MEETING_ROOM_RELEASE_IF_NO_CHECKIN` | ✅ | ✅ | INTEGER | Releases room if check-in does not occur within configured minutes. |
| `MEETING_ROOM_SYNC_JOB_EMAIL_LIST` | ✅ | ✅ | LIST | Defines email recipients for meeting room sync job notifications. |
| `MEETING_START_NOTIFICATION` | ✅ | ✅ | INTEGER | Controls the notification sent when the meeting has started via meeting room kiosk |
| `Meeting_Title_Catering_Order` | ✅ | ✅ | BOOLEAN | Controls display of meeting title in the Catering Dashboard detailed view |
| `meetingRoomCheckInCutOff` | ✅ | ✅ | INTEGER | Defines the cutoff for the visibility of the checkin button on the meeting rooms web and mobile view. |
| `meetingRoomCost` | ✅ | ✅ | BOOLEAN | Controls display of meeting room cost in the UI for web and mobile view. |
| `meetingStartTimeCuttoffInMinutes` | ✅ | ✅ | INTEGER | Defines the cutoff for how much prior to that start time the booking can be created. Its a booking creation cutoff time. Value is in minutes. |
| `MULTI_DOMAIN` | ✅ | ✅ | BOOLEAN | Controls multiple domains in a single BUID (for clients like MAF) |
| `office_name` | ✅ | ✅ | STRING | The office label used to scope rooms and MR configs to that office. If it doesn't match the server office name, rooms/configs for that office will show as expected. |
| `OFFICE_PREMISE_NAME` | ✅ | ✅ | STRING | Defines the office mapping for meeting room via meeting room sync. |
| `organiserBookingEmailsMeetingRooms` | ✅ | ✅ | BOOLEAN | Controls whether the organizer receives booking emails. |
| `OUTLOOK_WO_ADMIN_CONSENT` | ✅ | ✅ | BOOLEAN | This controls the room email id field in the room details section of Meeting Rooms Settings page. This is needed for an integrated setup. |
| `RELEASE_MEETING_ROOM` | ✅ | ✅ | BOOLEAN | Controls the auto-release logic for rooms, based on the other MR configs (especially MEETING_ROOM_RELEASE_IF_NO_CHECKIN). |
| `RELEASE_ROOM_CANCEL_MEETING` | ✅ | ✅ | BOOLEAN | Controls whether releasing a room also cancels the meeting from users calendars. |
| `ReleaseRoom` | ✅ | ✅ | BOOLEAN | Controls if release room functionality is enabled |
| `releaseRoomEmailList` | ✅ | ✅ | LIST | Additional email recipients for release room notifications, other than organiser of the meeting which was released |
| `rommEnabled` | ✅ | ✅ | BOOLEAN | Controls the enablement of the room for booking |
| `Room_As_Organizer` | ✅ | ✅ | BOOLEAN | Controls the enablement of the room as organiser workflow for the meeting room kiosk |
| `room_cancel_cutoff` | ✅ | ✅ | INTEGER | Defines cancellation cut-off time in minutes for meeting room bookings. |
| `Room_Kiosk_With_Cisco` | ✅ | ✅ | BOOLEAN | Meeting Rooms Kiosk workflow - Enables Cisco-related fields in the Meeting Rooms settings page under the Kiosk column |
| `room_name` | ✅ | ✅ | STRING | Mapping of meeting room name via outlook sync |
| `Room_Special_Request_Enable` | ✅ | ✅ | BOOLEAN | Controls visibility of the Meeting Request section in the meeting booking form - on web view. |
| `RoomBookingEmailEnabled` | ✅ | ✅ | BOOLEAN | Controls the emails sent to additional recipients |
| `roomBookingsEmailList` | ✅ | ✅ | LIST | Defines additional recipients for meeting room booking emails. |
| `SEND_INVITE_TO_ALL_EMPLOYEES` | ✅ | ✅ | BOOLEAN | Controls recipients of native meeting room booking emails. |
| `sendRoomBookingEmailToAllParticipants` | ✅ | ✅ | BOOLEAN | Controls whether booking emails are sent to all participants. |
| `Show_Room_If_Not_Eligible` | ✅ | ✅ | BOOLEAN | Controls visibility of ineligible rooms. |
| `SHOW_UPCOMING_BOOKINGS_TIME` | ✅ | ✅ | INTEGER | Meeting Rooms Kiosk - Defines how prior to the meeting start time the kiosk screen will turn yellow to let users checkin to their booking. Value set in minutes |
| `showWisLogo` | ✅ | ✅ | BOOLEAN | Toggles display of the MoveInSync logo on meeting room kiosk and calendar integration UIs |
| `SyncMeetingRooms` | ✅ | ✅ | BOOLEAN | Enables the Sync Rooms button for integrated setups in the Meeting Room Settings page |
| `timezone` | ✅ | ✅ | STRING | Defines the timezone of that office |
| `weekdays` | ✅ | ✅ | LIST | Defines the set of days considered working days for that office's rooms |
| `cateringLimits` | — | ✅ | LIST | Defines cut-off times for modifying or cancelling catering orders based on participant count. |
| `CheckOutCTARooms` | — | ✅ | BOOLEAN | Controls the visibility of the checkout button against room bookings. Not dependent on checkin button. |
| `colorVCStatsIconsKiosk` | — | ✅ | STRING | Meeting Rooms Kiosk - Defines the color for the VC stats displayed on the kiosk screen. |
| `defaultAdvanceBookingLimitForBypass` | — | ✅ | INTEGER | Defines the threshold for the Advance Booking Limit bypass privilege. |
| `defaultMaxDurationForBypass` | — | ✅ | INTEGER | Defines the threshold for the maximum duration bypass privilege. |
| `enableCheckInForMeetingRoom` | — | ✅ | BOOLEAN | Enables meeting room check-in button on the web and app. |
| `endTimeBufferRoomBookingBuidLevel` | — | ✅ | BOOLEAN | Defines end time buffer for meeting room bookings at BUID level for the Buffer Time workflow in catering/IT request. |
| `endTimeBufferRoomBookingRoomLevel` | — | ✅ | INTEGER | Defines end time buffer for meeting room bookings at room level for the Buffer Time workflow in catering/IT request. |
| `facilityMailList` | — | ✅ | STRING | For IT request workflow to control who receives the IT request emails. |
| `FLOOR_PREMISE_NAME` | — | ✅ | STRING | - |
| `IT_REQUEST_OUTLOOK_ADDIN` | — | ✅ | BOOLEAN | Enables IT request functionality within the WorkInSync Outlook Add-in. |
| `itemsDynamicFields` | — | ✅ | LIST | dynamic fields for IT Request |
| `maxApprovalRequest` | — | ✅ | INTEGER | For resource approval workflow - defines maximum overlapping approval requests per user. |
| `MEETING_ROOM_SUBSCRIPTION_JOB_EMAIL_LIST` | — | ✅ | LIST | Defines email recipients for room subscription status. |
| `minDurationInMinutes` | — | ✅ | INTEGER | Defines minimum duration need for a meeting room booking. |
| `noAutoCheckinKiosk` | — | ✅ | BOOLEAN | When Checkin is hidden, the kiosk auto-checks into the booking. This controls that auto check-in behavior on Meeting Rooms Kiosk. |
| `organiserPersonaMeetingRooms` | — | ✅ | JSON | Controls email notifications for organizer persona in Meeting Rooms module. |
| `otherUsersPersonaMeetingRooms` | — | ✅ | JSON | Controls email notifications for other participant personas in Meeting Rooms module. |
| `OutlookNativeRoomSetup` | — | ✅ | BOOLEAN | Hybrid setup for outlook integration |
| `participantPersonaMeetingRooms` | — | ✅ | JSON | Controls email notifications for participant personas in the Meeting Rooms module. |
| `recurringBookings` | — | ✅ | BOOLEAN | Enables recurring booking flow for meeting rooms for both integrated and native. |
| `releaseRoom` | — | ✅ | BOOLEAN | Not used |
| `roomCheckinQrOnKiosk` | — | ✅ | BOOLEAN | Controls display of meeting room QR code on kiosk at room level. |
| `roomStatsKiosk` | — | ✅ | BOOLEAN | Controls the visibility of the checkout button against room bookings. Not dependent on checkin button. |
| `roomWithApproval` | — | ✅ | BOOLEAN | Enables approval workflow for meeting rooms on web and mobile. |
| `roomWithApprovalBuidLevel` | — | ✅ | BOOLEAN | Enables meeting room approval workflow at BUID level. |
| `showOrganiserNameAddInTimeline` | — | ✅ | BOOLEAN | Show organizer name on booking timeline on outlook addin |
| `smartRoomRecommendation` | — | ✅ | BOOLEAN | Enables AI-based smart room recommendation. |
| `startTimeBufferRoomBookingBuidLevel` | — | ✅ | BOOLEAN | Defines start time buffer for meeting room bookings at BUID level for the Buffer Time workflow in catering/IT request. |
| `startTimeBufferRoomBookingRoomLevel` | — | ✅ | INTEGER | Defines start time buffer at individual room level. |
| `textMessageForKiosk` | — | ✅ | JSON | Defines text displayed on the kiosk. |
| `textOnKiosk` | — | ✅ | BOOLEAN | Controls additional text visibility on the Meeting Rooms Kiosk screen |
| `WEIGHT_CAPACITY` | — | ✅ | DOUBLE | Defines weight configuration for AI room recommendation based on capacity. |
| `WEIGHT_HISTORICAL` | — | ✅ | DOUBLE | Defines weight configuration for AI room recommendation based on historical usage. |

## .com-only Configs
_34 properties present on the `.com` server but absent from the `.in` config list._

- `cateringLimits` — Defines cut-off times for modifying or cancelling catering orders based on participant count.
- `CheckOutCTARooms` — Controls the visibility of the checkout button against room bookings. Not dependent on checkin button.
- `colorVCStatsIconsKiosk` — Meeting Rooms Kiosk - Defines the color for the VC stats displayed on the kiosk screen.
- `defaultAdvanceBookingLimitForBypass` — Defines the threshold for the Advance Booking Limit bypass privilege.
- `defaultMaxDurationForBypass` — Defines the threshold for the maximum duration bypass privilege.
- `enableCheckInForMeetingRoom` — Enables meeting room check-in button on the web and app.
- `endTimeBufferRoomBookingBuidLevel` — Defines end time buffer for meeting room bookings at BUID level for the Buffer Time workflow in catering/IT request.
- `endTimeBufferRoomBookingRoomLevel` — Defines end time buffer for meeting room bookings at room level for the Buffer Time workflow in catering/IT request.
- `facilityMailList` — For IT request workflow to control who receives the IT request emails.
- `FLOOR_PREMISE_NAME` — -
- `IT_REQUEST_OUTLOOK_ADDIN` — Enables IT request functionality within the WorkInSync Outlook Add-in.
- `itemsDynamicFields` — dynamic fields for IT Request
- `maxApprovalRequest` — For resource approval workflow - defines maximum overlapping approval requests per user.
- `MEETING_ROOM_SUBSCRIPTION_JOB_EMAIL_LIST` — Defines email recipients for room subscription status.
- `minDurationInMinutes` — Defines minimum duration need for a meeting room booking.
- `noAutoCheckinKiosk` — When Checkin is hidden, the kiosk auto-checks into the booking. This controls that auto check-in behavior on Meeting Rooms Kiosk.
- `organiserPersonaMeetingRooms` — Controls email notifications for organizer persona in Meeting Rooms module.
- `otherUsersPersonaMeetingRooms` — Controls email notifications for other participant personas in Meeting Rooms module.
- `OutlookNativeRoomSetup` — Hybrid setup for outlook integration
- `participantPersonaMeetingRooms` — Controls email notifications for participant personas in the Meeting Rooms module.
- `recurringBookings` — Enables recurring booking flow for meeting rooms for both integrated and native.
- `releaseRoom` — Not used
- `roomCheckinQrOnKiosk` — Controls display of meeting room QR code on kiosk at room level.
- `roomStatsKiosk` — Controls the visibility of the checkout button against room bookings. Not dependent on checkin button.
- `roomWithApproval` — Enables approval workflow for meeting rooms on web and mobile.
- `roomWithApprovalBuidLevel` — Enables meeting room approval workflow at BUID level.
- `showOrganiserNameAddInTimeline` — Show organizer name on booking timeline on outlook addin
- `smartRoomRecommendation` — Enables AI-based smart room recommendation.
- `startTimeBufferRoomBookingBuidLevel` — Defines start time buffer for meeting room bookings at BUID level for the Buffer Time workflow in catering/IT request.
- `startTimeBufferRoomBookingRoomLevel` — Defines start time buffer at individual room level.
- `textMessageForKiosk` — Defines text displayed on the kiosk.
- `textOnKiosk` — Controls additional text visibility on the Meeting Rooms Kiosk screen
- `WEIGHT_CAPACITY` — Defines weight configuration for AI room recommendation based on capacity.
- `WEIGHT_HISTORICAL` — Defines weight configuration for AI room recommendation based on historical usage.

_Last updated: 2026-05-26_
_Source: [[sources/pms-configs-in-all-wis-configs]] | [[sources/pms-configs-com-wis-service-configs]]_
