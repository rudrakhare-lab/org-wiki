---
type: module
status: active
owner: Platform
depends_on: []
used_by: [payments, notifications]
last_updated: 2026-04-27
source: "[[sources/auth-spec-v1]]"
---

# Auth Module

## Overview
The Auth module handles all user authentication and session management.
It is a **foundational module** — it has no dependencies on other modules,
but is consumed by both Payments and Notifications.

## Purpose & Scope
Owns user identity verification, credential management, and session lifecycle.
Responsible for issuing and validating JWTs that downstream modules use for
authorization. Does **not** own authorization/permissions logic — that would
belong to a future Permissions module.

## Key Features
- Email/password login
- OAuth 2.0 (Google, GitHub)
- JWT-based sessions: 15-minute access tokens, 30-day refresh tokens
- Rate limiting: 5 consecutive failed attempts triggers a 15-minute lockout

## Data Entities Used
- [[entities/user]] — owns this entity
- [[entities/session]] — owns this entity

## Dependencies on Other Modules
None — Auth is a foundational module with no upstream dependencies.

## Used By
- [[modules/payments]] — validates JWT on every payment request
- [[modules/notifications]] — extracts `user_id` from JWT to target notifications

## API Endpoints
| Method | Path | Description | Auth Required |
|--------|------|-------------|---------------|
| POST | /auth/login | Email/password login | No |
| POST | /auth/oauth/callback | OAuth 2.0 callback handler | No |
| POST | /auth/refresh | Exchange refresh token for new access token | Refresh token |
| POST | /auth/logout | Invalidate the current session | Yes |

## Open Questions
- Should we support passkeys in v2?
- Who owns rate limiting config — Auth or Platform team?

## Last Updated
2026-04-27 — _Source: [[sources/auth-spec-v1]]_
