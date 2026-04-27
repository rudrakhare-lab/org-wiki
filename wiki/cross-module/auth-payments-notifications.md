---
type: cross-module
modules: [auth, payments, notifications]
last_updated: 2026-04-27
source: "[[sources/auth-spec-v1]]"
---

# Auth → Payments & Notifications

## Summary
The Auth module is the upstream identity provider for both the Payments and
Notifications modules. Both downstream modules rely on JWT tokens issued by Auth
to identify the acting user — Payments validates the token before processing a
payment; Notifications extracts the `user_id` from the token to route messages.

## Modules Involved
- [[modules/auth]] — issues JWT tokens; foundational module
- [[modules/payments]] — validates JWT on every payment request (stub)
- [[modules/notifications]] — reads `user_id` from JWT to target messages (stub)

## How They Connect

### Auth → Payments
Payments calls Auth's `/auth/` token validation mechanism on every inbound
payment request. If the JWT is invalid or expired, the payment request is rejected.

**Data passed:** JWT access token (in Authorization header)
**Direction:** Payments reads from Auth

### Auth → Notifications
Notifications receives `user_id` by parsing the JWT issued by Auth. No direct
API call to Auth appears to be required — the JWT is self-contained.

**Data passed:** `user_id` extracted from JWT payload
**Direction:** Notifications reads JWT (issued by Auth)

## Shared Data Flows

```
User Login
    │
    ▼
[Auth Module]
    │  issues JWT { user_id, exp }
    ├──────────────────────────────────► [Payments Module]
    │          validates JWT before        processes payment
    │          every payment request
    │
    └──────────────────────────────────► [Notifications Module]
               extracts user_id from       routes notification
               JWT to identify target
```

## Shared Entities
- [[entities/user]] — owned by Auth; referenced by Payments and Notifications via `user_id` in JWT

## Potential Conflicts
- **Rate limiting ownership**: Auth spec flags an open question about whether
  rate limiting config is owned by Auth or Platform. If Payments also implements
  its own rate limiting, this could create a conflict. ⚠️ Flag for resolution.
- **Payments and Notifications stubs**: Full details of how these modules consume
  Auth are not yet known. Update this page when their specs are ingested.

_Source: [[sources/auth-spec-v1]]_
