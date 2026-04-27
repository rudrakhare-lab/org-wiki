---
type: source
raw_path: raw/modules/auth/auth-spec-v1.md
ingested: 2026-04-27
doc_type: spec
---

# Auth Module — Feature Spec v1

## Source Title
Auth Module — Feature Spec v1

## Date
2026-04-27

## Type
spec

## Key Takeaways
- The Auth module is a **foundational module** with no dependencies on other modules.
- It owns **two entities**: `User` (primary owner) and `Session`.
- It issues **JWT access tokens** (15-min TTL) and **refresh tokens** (30-day TTL).
- Downstream consumers are **Payments** (validates JWT on every request) and **Notifications** (extracts `user_id` from JWT).
- Supports **email/password login** and **OAuth 2.0** via Google and GitHub.
- **Rate limiting**: 5 consecutive failed logins triggers a 15-minute lockout.
- Two open questions flagged: passkey support in v2, and ownership of rate limiting config.

## Entities Mentioned
- [[entities/user]]
- [[entities/session]]

## Modules Mentioned
- [[modules/auth]] (primary subject)
- [[modules/payments]] (consumer — stub created)
- [[modules/notifications]] (consumer — stub created)

## Decisions Extracted
- [[decisions/2026-04-27-jwt-session-strategy]]

## Wiki Pages Created/Updated
- Created: [[modules/auth]]
- Created: [[modules/payments]] (stub)
- Created: [[modules/notifications]] (stub)
- Created: [[entities/user]]
- Created: [[entities/session]]
- Created: [[cross-module/auth-payments-notifications]]
- Created: [[decisions/2026-04-27-jwt-session-strategy]]
- Updated: [[wiki/glossary]]
- Updated: [[wiki/index]]
- Updated: [[wiki/log]]
- Updated: [[wiki/overview]]
- Updated: [[cross-module/overview]]
