# WorkInSync Feature Wiki — Index
_Last updated: 2026-04-28_
_Total pages: 36 | Modules: 2 | Entities: 8 | Concepts: 0 | Integrations: 0 | Decisions: 4 | Sources: 11 | Cross-module: 4_

---

## Modules
| Page | Summary | Status | Owner | Depends On |
|------|---------|--------|-------|------------|
| [[modules/meeting-rooms]] | Room booking, catering, kiosk, Outlook sync, dynamic policy, maintenance | active | unknown | tags-desk-parking, floor-kiosk, mobile-app, ms-teams-integration |
| [[modules/parking-management]] | Parking slot booking (WFO add-on), dynamic policy, waitlist, check-in | active | unknown | tags-desk-parking, mobile-app, desk-management |

## Concepts
| Page | Summary | Used By |
|------|---------|---------|

## Entities
| Page | Summary | Owned By |
|------|---------|----------|
| [[entities/room]] | Physical meeting room resource (capacity, amenities, calendar type) | meeting-rooms |
| [[entities/booking]] | Meeting room reservation (organizer, time slot, check-in state, catering) | meeting-rooms |
| [[entities/catering-order]] | Food/beverage order attached to a meeting booking (per cafeteria × slot) | meeting-rooms |
| [[entities/cafeteria]] | Food-service premise with menu categories and items | meeting-rooms ⚠️ shared |
| [[entities/room-tag]] | Tag assigned to rooms/employees for Dynamic Policy access control | tags-desk-parking |
| [[entities/maintenance-period]] | Scheduled room downtime window (create/delete; optional booking block) | meeting-rooms |
| [[entities/parking-slot]] | Bookable parking space (assignment type, vehicle type, dynamic policy tags) | parking-management |
| [[entities/parking-booking]] | Parking reservation created as WFO add-on (slot, vehicle, check-in, waitlist) | parking-management |

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

## Decisions
| Page | Date | Status | Modules |
|------|------|--------|---------|
| [[decisions/2026-04-27-meeting-room-auto-release]] | 2026-04-27 | active | meeting-rooms |
| [[decisions/2026-04-27-kiosk-pin-auth-over-login]] | 2026-04-27 | active | meeting-rooms, floor-kiosk |
| [[decisions/2026-04-27-catering-order-id-model]] | 2026-04-27 | active | meeting-rooms |
| [[decisions/2026-04-28-parking-slot-allocation-priority]] | 2026-04-28 | active | parking-management |

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
