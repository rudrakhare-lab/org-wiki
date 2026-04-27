# Activity Log
Append-only. Format: `## [YYYY-MM-DD HH:MM] <operation> | <title>`

---

## [INIT] Wiki initialized
- Scaffold created. Ready for first ingest.
- CLAUDE.md written with 8 sections.
- Obsidian vault configured.
- Starter pages created: index.md, log.md, overview.md, glossary.md, cross-module/overview.md

---

## [2026-04-27 13:28] ingest | Auth Module — Feature Spec v1

- Created: [[sources/auth-spec-v1]]
- Created: [[modules/auth]]
- Created: [[modules/payments]] (stub — referenced in auth spec, no own spec ingested)
- Created: [[modules/notifications]] (stub — referenced in auth spec, no own spec ingested)
- Created: [[entities/user]]
- Created: [[entities/session]]
- Created: [[cross-module/auth-payments-notifications]]
- Created: [[decisions/2026-04-27-jwt-session-strategy]]
- Updated: [[wiki/glossary]] — 8 terms added (JWT, Access Token, Refresh Token, OAuth 2.0, Rate Limiting, TTL, Session, user_id)
- Updated: [[wiki/index]] — 10 pages registered
- Updated: [[wiki/overview]]
- Updated: [[cross-module/overview]]

Flags:
- ⚠️ Rate limiting ownership is unresolved — Auth spec asks whether Auth or Platform owns the config. No decision made yet.
- ⚠️ Payments and Notifications are stubs. Suggest ingesting their specs to fill in dependencies and entity ownership.
