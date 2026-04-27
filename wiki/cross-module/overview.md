# Cross-Module Dependency Map
_Auto-maintained. Updated when new dependencies are discovered._

---

## Module Dependency Table
| Module | Depends On | Used By |
|--------|-----------|---------|
| [[modules/auth]] | — | payments, notifications |
| [[modules/payments]] | auth | — |
| [[modules/notifications]] | auth | — |

---

## Shared Entities
| Entity | Owner Module | Also Used By |
|--------|-------------|-------------|
| [[entities/user]] | auth | payments, notifications |
| [[entities/session]] | auth | — |

---

## Shared Concepts
| Concept | Implemented By |
|---------|---------------|
| JWT-based authentication | auth (issues) → payments, notifications (consume) |
| Rate limiting | auth (login attempts) — ownership TBD ⚠️ |
