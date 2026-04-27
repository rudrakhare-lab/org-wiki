# WorkInSync Feature Wiki — Index
_Last updated: 2026-04-27_
_Total pages: 22 | Modules: 1 | Entities: 6 | Concepts: 0 | Integrations: 0 | Decisions: 3 | Sources: 8 | Cross-module: 3_

---

## Modules
| Page | Summary | Status | Owner | Depends On |
|------|---------|--------|-------|------------|
| [[modules/meeting-rooms]] | Room booking, catering, kiosk, Outlook sync, dynamic policy, maintenance | active | unknown | tags-desk-parking, floor-kiosk, mobile-app, ms-teams-integration |

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
| [[entities/room-tag]] | Tag assigned to rooms and employees for Dynamic Policy access control | tags-desk-parking |
| [[entities/maintenance-period]] | Scheduled room downtime window (create/delete; optional booking block) | meeting-rooms |

## Integrations
| Page | Summary | Used By |
|------|---------|---------|

## Cross-Module
| Page | Modules Involved | Topic |
|------|-----------------|-------|
| [[cross-module/meeting-rooms-tags-desk-parking]] | meeting-rooms, tags-desk-parking | Tag engine reused for Dynamic Policy (room access control) |
| [[cross-module/meeting-rooms-floor-kiosk]] | meeting-rooms, floor-kiosk | Kiosk tablet hardware + MDM shared; room status/booking data from meeting-rooms |
| [[cross-module/meeting-rooms-mobile-app]] | meeting-rooms, mobile-app | Mobile booking surface; QR check-in via app camera; maintenance banners |

## Decisions
| Page | Date | Status | Modules |
|------|------|--------|---------|
| [[decisions/2026-04-27-meeting-room-auto-release]] | 2026-04-27 | active | meeting-rooms |
| [[decisions/2026-04-27-kiosk-pin-auth-over-login]] | 2026-04-27 | active | meeting-rooms, floor-kiosk |
| [[decisions/2026-04-27-catering-order-id-model]] | 2026-04-27 | active | meeting-rooms |

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
