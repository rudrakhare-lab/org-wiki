# WorkInSync Feature Wiki — Index
_Last updated: 2026-05-27_
_Total pages: 101 | Modules: 22 | Configs: 11 | Entities: 12 | Concepts: 0 | Answers: 1 | Integrations: 0 | Decisions: 8 | Sources: 35 | Cross-module: 8_

---

## Modules
| Page | Summary | Status | Owner | Depends On |
|------|---------|--------|-------|------------|
| [[modules/meeting-rooms]] | Room booking, catering, kiosk, Outlook sync, dynamic policy, maintenance | active | unknown | tags-desk-parking, floor-kiosk, mobile-app, ms-teams-integration |
| [[modules/parking-management]] | Parking slot booking (WFO add-on), dynamic policy, waitlist, check-in | active | unknown | tags-desk-parking, mobile-app, desk-management |
| [[modules/visitor-management]] | Visitor invite, digipass, 2-step check-in, badge printing, visitor parking | active | unknown | parking-management, guard-app-kiosks |
| [[modules/delegation]] | Delegate resource booking rights to other employees (profile switcher) | active | Aditya Dutta | employee-experience, meeting-rooms, desk-management |
| [[modules/digital-wayfinding]] | Indoor navigation on mobile app — floor plan amenities + path routing | active | Aditya Dutta | mobile-app, parking-management |
| [[modules/employee-experience]] | emp-exp service — hosts delegation, wayfinding, and cross-cutting emp features | active | unknown | — |
| [[modules/floor-kiosk]] | Device hardware spec, DIY Floor Planner tool, floor plan pipeline | active | Aditya Dutta | — |
| [[modules/meal-management]] | Meal booking (WFO add-on + standalone), RFID check-in, vendor dashboard | active | Aditya Dutta | access-management, floor-kiosk, desk-management |
| [[modules/implementation]] | Internal SOPs for client onboarding and ETS migration | internal | unknown | — |
| [[modules/ms-teams-integration]] | WorkInSync app on Microsoft Teams — Azure AD SSO, Graph API permissions, license/install flows | active | unknown | sso |
| [[modules/third-party]] | WorkInSync's Slack integration — workspace install, WFO/WFH booking from Home tab, check-in notifications, Slack status updates | active | unknown | — |
| [[modules/safe-reach]] | Late-departure employee safety workflow — VMS kiosk-initiated, configurable form, gender-trigger, ETA, IVR/mobile/email notification chain, WIS dashboard, reports | active | unknown | visitor-management |
| [[modules/access-management]] | External access-card vendor integration — REST API (.com/.in) + SFTP file-based modes; card swipe → booking check-in/out | active | unknown | desk-management, meeting-rooms, parking-management, meal-management |
| [[modules/employee-provisioning]] | Inbound employee data sync — SCIM 2.0 (Azure AD / Okta / any IdP) + SFTP CSV modes; users-only, 40-min cadence | active | unknown | — |
| [[modules/sso]] | Single Sign-On — SAML 2.0 (workinsync.io SP) + OAuth 2.0/OIDC (mis-auth); IdP-agnostic (Azure AD / Okta / ADFS / Google); TechOps integration process | active | unknown | — |

## Concepts
| Page | Summary | Used By |
|------|---------|---------|

## Entities
| Page | Summary | Owned By |
|------|---------|----------|
| [[entities/employee]] | Foundational identity record — subject of bookings, visitor-hosting, delegation, RFID access; loaded via provisioning | employee-provisioning |
| [[entities/room]] | Physical meeting room resource (capacity, amenities, calendar type) | meeting-rooms |
| [[entities/booking]] | Meeting room reservation (organizer, time slot, check-in state, catering) | meeting-rooms |
| [[entities/catering-order]] | Food/beverage order attached to a meeting booking (per cafeteria × slot) | meeting-rooms |
| [[entities/cafeteria]] | Food-service premise with menu categories and items | meeting-rooms (consumed by meal-management) |
| [[entities/room-tag]] | Tag assigned to rooms/employees for Dynamic Policy access control | tags-desk-parking |
| [[entities/maintenance-period]] | Scheduled room downtime window (create/delete; optional booking block) | meeting-rooms |
| [[entities/parking-slot]] | Bookable parking space (assignment type, vehicle type, dynamic policy tags) | parking-management |
| [[entities/parking-booking]] | Parking reservation created as WFO add-on (slot, vehicle, check-in, waitlist) | parking-management |
| [[entities/visitor-invite]] | Visitor visit booking with full check-in lifecycle, approval, parking | visitor-management |
| [[entities/visitor-profile]] | Persistent visitor profile (name, photo, ID, NDA) reused across visits | visitor-management |
| [[entities/meal-booking]] | Meal reservation (WFO-integrated or standalone; RFID or QR check-in) | meal-management |

## Integrations
| Page | Summary | Used By |
|------|---------|---------|

## Cross-Module
| Page | Modules Involved | Topic |
|------|-----------------|-------|
| [[cross-module/meeting-rooms-tags-desk-parking]] | meeting-rooms, tags-desk-parking | Tag engine reused for Dynamic Policy (room access control) |
| [[cross-module/meeting-rooms-floor-kiosk]] | meeting-rooms, floor-kiosk | Kiosk tablet hardware + MDM shared; room status/booking data from meeting-rooms |
| [[cross-module/meeting-rooms-mobile-app]] | meeting-rooms, mobile-app | Mobile booking surface; QR check-in via app camera; maintenance banners |
| [[cross-module/parking-tags-desk-parking]] | parking-management, tags-desk-parking | Tag engine reused for vehicle-type slot access + BLOCK_HOTSEAT policy |
| [[cross-module/vms-parking-management]] | visitor-management, parking-management | Visitor-tagged parking slots auto-allocated at invite creation |
| [[cross-module/vms-guard-app]] | visitor-management, guard-app-kiosks | Guard App scans visitor digipass at security gate (step 1 of 2-step check-in) |
| [[cross-module/meal-access-management]] | meal-management, access-management | RFID/HID card swipe at cafeteria triggers meal check-in |

## Decisions
| Page | Date | Status | Modules |
|------|------|--------|---------|
| [[decisions/2026-04-27-meeting-room-auto-release]] | 2026-04-27 | active | meeting-rooms |
| [[decisions/2026-04-27-kiosk-pin-auth-over-login]] | 2026-04-27 | active | meeting-rooms, floor-kiosk |
| [[decisions/2026-04-27-catering-order-id-model]] | 2026-04-27 | active | meeting-rooms |
| [[decisions/2026-04-28-parking-slot-allocation-priority]] | 2026-04-28 | active | parking-management |
| [[decisions/2026-04-28-vms-2step-checkin]] | 2026-04-28 | active | visitor-management, guard-app-kiosks |
| [[decisions/2026-04-28-vms-digipass-as-primary-auth]] | 2026-04-28 | active | visitor-management |
| [[decisions/2026-04-28-delegation-stateless-session]] | 2026-04-28 | active | delegation |
| [[decisions/2026-04-28-standalone-meal-booking-constraint]] | 2026-04-28 | active | meal-management |

## Configs
| Page | Service | Servers | Module |
|------|---------|---------|--------|
| [[configs/pms]] | Project Management Service (PMS) | .in + .com | — |
| [[configs/visitor-management]] | Visitor Management Service (VMS) | .in + .com | [[modules/visitor-management]] |
| [[configs/meeting-rooms]] | Meeting Rooms Service | .in + .com | [[modules/meeting-rooms]] |
| [[configs/booking-rule-engine]] | Booking Rule Engine | .in + .com | — |
| [[configs/wis-seat-booking]] | WIS Seat Booking Service | .in + .com | [[modules/desk-management]] |
| [[configs/guard-app]] | Guard App Service | .in + .com | [[modules/guard-app-kiosks]] |
| [[configs/emp-experience-email]] | Employee Experience — Email Service | .in + .com | [[modules/employee-experience]] |
| [[configs/emp-experience-internal]] | Employee Experience — Internal Config | .in + .com | [[modules/employee-experience]] |
| [[configs/emp-experience-common]] | Employee Experience — Common Config | .in + .com | [[modules/employee-experience]] |
| [[configs/mobile-app-server]] | Mobile App Server Config |  | [[modules/mobile-app]] |
| [[configs/app-server-config]] | App Server Config | .com | — |

## Sources Ingested
| Page | Type | Date | Pages Touched |
|------|------|------|---------------|
| [[sources/meeting-rooms-app-prd]] | PRD | 2026-04-27 | modules/meeting-rooms, entities/room, entities/booking |
| [[sources/kiosk-meeting-rooms-prd]] | PRD | 2026-04-27 | modules/meeting-rooms, cross-module/meeting-rooms-floor-kiosk |
| [[sources/dynamic-policy-meeting-rooms]] | spec | 2026-04-27 | modules/meeting-rooms, entities/room-tag, cross-module/meeting-rooms-tags-desk-parking |
| [[sources/meeting-rooms-catering-prd]] | PRD | 2026-04-27 | modules/meeting-rooms, entities/catering-order, entities/cafeteria |
| [[sources/meeting-rooms-room-maintenance]] | spec | 2026-04-27 | modules/meeting-rooms, entities/maintenance-period |
| [[sources/outlook-integration-permissions]] | spec | 2026-04-27 | modules/meeting-rooms, glossary |
| [[sources/outlook-addin-setup]] | spec | 2026-04-27 | modules/meeting-rooms |
| [[sources/meeting-rooms-resources]] | misc | 2026-04-27 | modules/meeting-rooms (configs) |
| [[sources/parking-prd]] | PRD | 2026-04-28 | modules/parking-management, entities/parking-slot, entities/parking-booking |
| [[sources/dynamic-policy-parking]] | spec | 2026-04-28 | modules/parking-management, cross-module/parking-tags-desk-parking |
| [[sources/parking-waitlist]] | spec | 2026-04-28 | modules/parking-management |
| [[sources/vms-prd]] | PRD | 2026-04-28 | modules/visitor-management, entities/visitor-invite, entities/visitor-profile |
| [[sources/vms-implementation]] | spec | 2026-04-28 | modules/visitor-management (configs) |
| [[sources/delegation-prd]] | PRD | 2026-04-28 | modules/delegation, modules/employee-experience |
| [[sources/digital-wayfinding-sop]] | spec | 2026-04-28 | modules/digital-wayfinding, modules/employee-experience |
| [[sources/diy-floor-planner-prd]] | PRD | 2026-04-28 | modules/floor-kiosk |
| [[sources/floor-kiosk-device-spec]] | spec | 2026-04-28 | modules/floor-kiosk (hardware) |
| [[sources/floor-plan-sop]] | spec | 2026-04-28 | modules/floor-kiosk, modules/digital-wayfinding |
| [[sources/meal-checkin-prd]] | PRD | 2026-04-28 | modules/meal-management, entities/meal-booking, cross-module/meal-access-management |
| [[sources/pms-configs-in-all-wis-configs]] | config | 2026-05-26 | configs/pms, configs/visitor-management, configs/meeting-rooms, configs/booking-rule-engine, configs/wis-seat-booking, configs/guard-app, configs/emp-experience-email, configs/emp-experience-internal, configs/emp-experience-common |
| [[sources/pms-configs-com-wis-service-configs]] | config | 2026-05-26 | configs/pms, configs/visitor-management, configs/meeting-rooms, configs/booking-rule-engine, configs/wis-seat-booking, configs/guard-app, configs/emp-experience-email, configs/emp-experience-internal, configs/emp-experience-common, configs/app-server-config |

| [[sources/launch-ets-sop]] | spec | 2026-04-28 | modules/implementation |
