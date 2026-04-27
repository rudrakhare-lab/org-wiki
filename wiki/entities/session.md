---
type: entity
owned_by: auth
used_by: [auth]
last_updated: 2026-04-27
source: "[[sources/auth-spec-v1]]"
---

# Session

## Description
Represents an active authenticated session for a User. Tracks the JWT pair
(access + refresh tokens) and device metadata. Managed entirely by the Auth module.

## Fields
| Field | Type | Description | Required |
|-------|------|-------------|----------|
| id | UUID | Unique session identifier | Yes |
| user_id | UUID | FK → [[entities/user]].id | Yes |
| token_hash | string | Hash of the refresh token (not stored in plaintext) | Yes |
| expires_at | timestamp | Refresh token expiry (UTC, 30-day TTL) | Yes |
| device_info | string | User-agent / device metadata for the session | No |

## Used By
- [[modules/auth]] — creates, validates, and invalidates sessions

## Relationships to Other Entities
- [[entities/user]] — each Session belongs to one User

## Source of Truth
[[modules/auth]] is the sole owner of the Session entity.

_Source: [[sources/auth-spec-v1]]_
