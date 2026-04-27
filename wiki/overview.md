# Product Overview
_Maintained by AI. Last updated: 2026-04-27_

---

## What We're Building
A multi-module product platform. Currently the Auth module is the only fully
documented module — Payments and Notifications are referenced as consumers of Auth
but their own specs have not yet been ingested.

---

## Core Modules
| Module | Purpose | Status |
|--------|---------|--------|
| [[modules/auth]] | User authentication, session management, JWT issuance | active |
| [[modules/payments]] | Payment processing (depends on Auth for JWT validation) | stub |
| [[modules/notifications]] | User notifications (depends on Auth for user_id) | stub |

---

## Key Architecture Decisions
- **JWT dual-token strategy** — 15-min access tokens + 30-day refresh tokens.
  Downstream modules validate JWTs locally, no round-trip to Auth.
  See [[decisions/2026-04-27-jwt-session-strategy]].

---

## Entity Ownership Map
| Entity | Owner Module |
|--------|-------------|
| [[entities/user]] | [[modules/auth]] |
| [[entities/session]] | [[modules/auth]] |

---

## Cross-Module Dependency Summary
Auth is the foundational identity provider. Both Payments and Notifications
depend on it via JWT. See [[cross-module/auth-payments-notifications]] and
[[cross-module/overview]] for the full dependency graph.

---

## Open Questions
- Who owns rate limiting config — Auth team or Platform team?
- Should Auth support passkeys in v2?
- Full specs for Payments and Notifications modules are not yet ingested.
