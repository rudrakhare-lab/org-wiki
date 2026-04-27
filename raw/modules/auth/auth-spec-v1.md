# Auth Module — Feature Spec v1
Date: 2026-04-27

## Overview
The Auth module handles all user authentication and session management.
It issues JWT tokens used by the Payments module and Notifications module.

## Key Features
- Email/password login
- OAuth 2.0 (Google, GitHub)
- JWT-based sessions (15-min access token, 30-day refresh token)
- Rate limiting: 5 failed attempts triggers 15-min lockout

## Data Entities
- User (owns this entity): id, email, password_hash, created_at, last_login
- Session: id, user_id, token_hash, expires_at, device_info

## Dependencies
- None (Auth is a foundational module)

## Used By
- Payments module (validates JWT on every payment request)
- Notifications module (uses user_id from JWT to target notifications)

## Open Questions
- Should we support passkeys in v2?
- Who owns rate limiting config — Auth or Platform?
