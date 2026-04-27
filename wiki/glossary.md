# Glossary
_All terms, abbreviations, and naming conventions. Updated on every ingest._

| Term | Definition | Module Context | Notes |
|------|-----------|----------------|-------|
| JWT | JSON Web Token — a self-contained, signed token encoding claims (e.g. user_id, expiry) | [[modules/auth]] | Used as access token (15-min TTL) |
| Access Token | Short-lived JWT (15 min) used to authenticate requests to downstream services | [[modules/auth]] | Stateless — validated without calling Auth |
| Refresh Token | Long-lived token (30 days) used to obtain a new access token after expiry | [[modules/auth]] | Stored as a hash in the Session entity, not plaintext |
| OAuth 2.0 | Authorization framework for third-party login (Google, GitHub) | [[modules/auth]] | |
| Rate Limiting | Restricting the number of requests/attempts in a time window | [[modules/auth]] | 5 failed logins → 15-min lockout. Ownership TBD: Auth vs Platform |
| TTL | Time-to-live — the duration before a token or record expires | [[modules/auth]] | |
| Session | A server-side record linking a User to an active refresh token | [[modules/auth]] | See [[entities/session]] |
| user_id | Unique identifier for a User; embedded in JWT claims | [[modules/auth]], [[modules/notifications]] | Extracted by Notifications to target messages |
