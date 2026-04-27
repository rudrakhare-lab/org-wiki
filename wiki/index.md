# Org Feature Wiki — Index
_Last updated: 2026-04-27_
_Total pages: 10 | Modules: 3 | Entities: 2 | Concepts: 0 | Integrations: 0 | Decisions: 1_

---

## Modules
| Page | Summary | Status | Owner | Depends On |
|------|---------|--------|-------|------------|
| [[modules/auth]] | Authentication & session management; issues JWTs | active | Platform | — |
| [[modules/payments]] | Payment processing; validates JWT before every request | stub | unknown | auth |
| [[modules/notifications]] | User notifications; uses user_id from JWT to route messages | stub | unknown | auth |

## Concepts
| Page | Summary | Used By |
|------|---------|---------|

## Entities
| Page | Summary | Owned By |
|------|---------|----------|
| [[entities/user]] | Core user identity record | auth |
| [[entities/session]] | Active JWT session record | auth |

## Integrations
| Page | Summary | Used By |
|------|---------|---------|

## Cross-Module
| Page | Modules Involved | Topic |
|------|-----------------|-------|
| [[cross-module/auth-payments-notifications]] | auth, payments, notifications | JWT-based identity propagation |

## Decisions
| Page | Date | Status | Modules |
|------|------|--------|---------|
| [[decisions/2026-04-27-jwt-session-strategy]] | 2026-04-27 | accepted | auth, payments, notifications |

## Sources Ingested
| Page | Type | Date | Pages Touched |
|------|------|------|---------------|
| [[sources/auth-spec-v1]] | spec | 2026-04-27 | 10 pages |
