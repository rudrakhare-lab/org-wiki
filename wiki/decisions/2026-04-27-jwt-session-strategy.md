---
type: decision
date: 2026-04-27
status: accepted
modules: [auth, payments, notifications]
source: "[[sources/auth-spec-v1]]"
---

# JWT Session Strategy

## Context
The Auth module needs a session management approach that supports multiple
downstream consumers (Payments, Notifications) without requiring them to call
Auth on every request or maintain their own session state.

## Decision
Use **JWT-based sessions** with a dual-token approach:
- **Access token**: short-lived (15 minutes), stateless, self-contained
- **Refresh token**: long-lived (30 days), stored server-side as a hash in the Session entity

## Rationale
- Short access token TTL limits damage from token theft without requiring constant re-auth.
- Downstream modules (Payments, Notifications) can validate JWTs locally without a round-trip to Auth — reducing latency and coupling.
- Refresh tokens are stored as hashes (not plaintext) so a DB compromise doesn't expose live tokens.

## Consequences
- Downstream modules must implement JWT validation logic (or share a library).
- Access token revocation is not instant — a stolen access token is valid for up to 15 minutes even after logout. Logout invalidates the refresh token only.
- All downstream modules that consume Auth tokens must handle token expiry and refresh gracefully.

## Alternatives Rejected
- **Server-side sessions with session IDs**: Would require Auth to be called on every downstream request — too much coupling and latency.
- **Single long-lived tokens**: Unacceptable risk if a token is stolen.
- **No session strategy (per-request credentials)**: Not suitable for user-facing flows.

## Related Modules
- [[modules/auth]]
- [[modules/payments]]
- [[modules/notifications]]

_Source: [[sources/auth-spec-v1]]_
