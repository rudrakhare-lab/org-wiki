# Cross-Module Dependency Map
_Auto-maintained. Updated when new dependencies are discovered._

---

## Module Dependency Table
| Module | Depends On | Used By |
|--------|-----------|---------|
| [[modules/meeting-rooms]] | tags-desk-parking (tag engine), floor-kiosk (kiosk infra), mobile-app (app container), ms-teams-integration (Outlook sync) | meal-management (cafeteria entity) |
| [[modules/tags-desk-parking]] | _(none known yet)_ | meeting-rooms (Dynamic Policy) |
| [[modules/floor-kiosk]] | _(none known yet)_ | meeting-rooms (kiosk surface) |
| [[modules/mobile-app]] | _(none known yet)_ | meeting-rooms (booking surface) |
| [[modules/ms-teams-integration]] | _(none known yet)_ | meeting-rooms (Outlook/Google sync) |

---

## Shared Entities
| Entity | Owner Module | Also Used By |
|--------|-------------|-------------|
| [[entities/cafeteria]] | meeting-rooms ⚠️ | meal-management |
| [[entities/room-tag]] | tags-desk-parking | meeting-rooms |

---

## Shared Concepts
| Concept | Implemented By |
|---------|---------------|
| Tag Engine (Dynamic Policy) | tags-desk-parking — consumed by meeting-rooms for room access control. See [[cross-module/meeting-rooms-tags-desk-parking]] |
| Kiosk Device Infrastructure | floor-kiosk — consumed by meeting-rooms for room kiosks. See [[cross-module/meeting-rooms-floor-kiosk]] |
| Mobile App Container | mobile-app — meeting-rooms booking surface runs inside the app. See [[cross-module/meeting-rooms-mobile-app]] |

---

## Cross-Module Pages
| Page | Modules | Topic |
|------|---------|-------|
| [[cross-module/meeting-rooms-tags-desk-parking]] | meeting-rooms, tags-desk-parking | Dynamic Policy — tag-based room access control |
| [[cross-module/meeting-rooms-floor-kiosk]] | meeting-rooms, floor-kiosk | Room kiosk hardware, MDM, status display, PIN auth |
| [[cross-module/meeting-rooms-mobile-app]] | meeting-rooms, mobile-app | Mobile booking flow, QR check-in, maintenance banners |
