---
type: entity
owned_by: auth
used_by: [auth, payments, notifications]
last_updated: 2026-04-27
source: "[[sources/auth-spec-v1]]"
---

# User

## Description
Represents an authenticated person in the system. The canonical identity record.
Owned and managed by the Auth module; consumed by Payments and Notifications via JWT claims.

## Fields
| Field | Type | Description | Required |
|-------|------|-------------|----------|
| id | UUID | Unique user identifier | Yes |
| email | string | User's email address (unique) | Yes |
| password_hash | string | Bcrypt/argon2 hash of the user's password | Yes |
| created_at | timestamp | Account creation time (UTC) | Yes |
| last_login | timestamp | Most recent successful login (UTC) | No |

## Used By
- [[modules/auth]] — owns and manages this entity
- [[modules/payments]] — receives `user_id` via validated JWT to associate payments
- [[modules/notifications]] — receives `user_id` via JWT to target notifications

## Relationships to Other Entities
- [[entities/session]] — a User can have multiple active Sessions

## Source of Truth
[[modules/auth]] is the canonical owner of the User entity.
No other module may write to or alter User records.

_Source: [[sources/auth-spec-v1]]_
