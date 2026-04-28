---
type: decision
module: delegation
date: 2026-04-28
status: active
---

# Decision: Delegation sessions are stateless — re-login always returns delegatee to own profile

## Context
When a Delegatee is acting on behalf of a Delegator and logs out (or their session expires),
the system must decide what happens on the next login: return to the delegator's context
(potentially exposing sensitive data to whoever picks up the device) or return to the delegatee's
own profile.

## Decision
Delegation sessions are **stateless**: on re-login, the page always opens in the delegatee's
own profile. The delegatee must explicitly switch to the delegator's profile again each session.
The delegator's profile state is never persisted across sessions for the delegatee.

## Alternatives Considered
- **Persist delegator context across sessions** (rejected — security risk if device is shared; delegatee could inadvertently continue acting as delegator)
- **Prompt on login to choose profile** (not built in v1)

## Trade-offs
- Delegatees who act daily on behalf of executives must switch profile every session — adds minor friction.
- Provides a clear security boundary: the delegatee must consciously choose to enter the delegator's context each time.

## Source
[[sources/delegation-prd]]
