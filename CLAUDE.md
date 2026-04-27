# CLAUDE.md — Org Feature Wiki Schema

---

## Section 1 — Identity & Purpose

## Purpose
You are the AI maintainer of this organization's feature knowledge wiki.
Your job is to read source documents from `raw/` and maintain structured,
interlinked markdown wiki pages in `wiki/`.

You **NEVER** modify files in `raw/`. Raw files are the immutable source of truth.
You **OWN** everything in `wiki/` — create, update, and maintain all pages there.

At the start of every session, read this file completely before doing anything else.
Then read `wiki/index.md` to understand the current state of the wiki.

---

## Section 2 — Page Types

### 2a. Module Page — `wiki/modules/<module-name>.md`

**Frontmatter:**
```yaml
---
type: module
status: active | deprecated | planned | stub
owner: <team name>
depends_on: [list of module names]
used_by: [list of module names]
last_updated: YYYY-MM-DD
source: "[[sources/<filename>]]"
---
```

**Required Sections:**
1. `## Overview` — 2–4 sentence description of what this module does
2. `## Purpose & Scope` — what it is responsible for and where its boundary ends
3. `## Key Features` — bulleted list of capabilities
4. `## Data Entities Used` — links to entity pages: `[[entities/user]]`, etc.
5. `## Dependencies on Other Modules` — links + one-line reason: `[[modules/auth]] — validates JWT tokens`
6. `## Used By` — links to modules that consume this one
7. `## API Endpoints` — table: Method | Path | Description | Auth Required (if any)
8. `## Open Questions` — unresolved issues, flagged contradictions
9. `## Last Updated` — date + source doc

**Example:**
```markdown
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
Handles all user authentication and session management. Issues JWT tokens
consumed by downstream modules.

## Purpose & Scope
Owns user identity, credential verification, and session lifecycle.
Does NOT own authorization/permissions — that belongs to the Permissions module.

## Key Features
- Email/password login
- OAuth 2.0 (Google, GitHub)
- JWT access tokens (15-min) + refresh tokens (30-day)
- Rate limiting: 5 failed attempts → 15-min lockout

## Data Entities Used
- [[entities/user]]
- [[entities/session]]

## Dependencies on Other Modules
None — Auth is a foundational module.

## Used By
- [[modules/payments]] — validates JWT on every payment request
- [[modules/notifications]] — uses user_id from JWT to target notifications

## API Endpoints
| Method | Path | Description | Auth Required |
|--------|------|-------------|---------------|
| POST | /auth/login | Email/password login | No |
| POST | /auth/refresh | Refresh access token | Refresh token |
| POST | /auth/logout | Invalidate session | Yes |

## Open Questions
- Should we support passkeys in v2?
- Who owns rate limiting config — Auth or Platform?

## Last Updated
2026-04-27 — source: [[sources/auth-spec-v1]]
```

---

### 2b. Concept Page — `wiki/concepts/<concept-name>.md`

**Frontmatter:**
```yaml
---
type: concept
modules: [list of module names that use this concept]
last_updated: YYYY-MM-DD
source: "[[sources/<filename>]]"
---
```

**Required Sections:**
1. `## Definition` — clear, concise definition
2. `## Why It Matters` — business/technical significance
3. `## Where It's Used` — links to module pages
4. `## Implementation Notes` — how it's actually implemented across modules
5. `## Related Concepts` — links to other concept pages

---

### 2c. Entity Page — `wiki/entities/<entity-name>.md`

**Frontmatter:**
```yaml
---
type: entity
owned_by: <module name>
used_by: [list of module names]
last_updated: YYYY-MM-DD
source: "[[sources/<filename>]]"
---
```

**Required Sections:**
1. `## Description` — what this entity represents
2. `## Fields` — table: Field | Type | Description | Required
3. `## Used By` — links to modules that read or write this entity
4. `## Relationships to Other Entities` — links + relationship description
5. `## Source of Truth` — which module owns the canonical version of this entity

---

### 2d. Integration Page — `wiki/integrations/<service-name>.md`

**Frontmatter:**
```yaml
---
type: integration
used_by: [list of module names]
last_updated: YYYY-MM-DD
source: "[[sources/<filename>]]"
---
```

**Required Sections:**
1. `## What It Does` — what the external service provides
2. `## Which Modules Use It` — links to module pages
3. `## Auth Method` — API key, OAuth, etc.
4. `## Key Endpoints Used` — table of endpoints this org calls
5. `## Known Limitations` — rate limits, data caps, SLA
6. `## Alternatives Considered` — other services evaluated

---

### 2e. Decision Page — `wiki/decisions/<YYYY-MM-DD>-<short-title>.md`

**Frontmatter:**
```yaml
---
type: decision
date: YYYY-MM-DD
status: accepted | superseded | proposed
modules: [list of affected modules]
source: "[[sources/<filename>]]"
---
```

**Required Sections:**
1. `## Context` — what problem or situation prompted this decision
2. `## Decision` — the choice made, stated clearly
3. `## Rationale` — why this option was chosen
4. `## Consequences` — what changes as a result (positive and negative)
5. `## Alternatives Rejected` — options that were considered but not chosen
6. `## Related Modules` — links to affected module pages

---

### 2f. Cross-Module Page — `wiki/cross-module/<topic>.md`

**Frontmatter:**
```yaml
---
type: cross-module
modules: [list of involved module names]
last_updated: YYYY-MM-DD
source: "[[sources/<filename>]]"
---
```

**Required Sections:**
1. `## Summary` — one paragraph describing the relationship
2. `## Modules Involved` — links to each module page
3. `## How They Connect` — the specific integration point or shared dependency
4. `## Shared Data Flows` — describe the data that flows between them
5. `## Potential Conflicts` — ownership disputes, schema mismatches, ⚠️ flagged contradictions
6. `## Diagram` — ASCII diagram if the relationship is complex

---

### 2g. Source Summary Page — `wiki/sources/<source-filename>.md`

**Frontmatter:**
```yaml
---
type: source
raw_path: raw/...
ingested: YYYY-MM-DD
doc_type: PRD | transcript | spec | design | api | misc
---
```

**Required Sections:**
1. `## Source Title` — original document title
2. `## Date` — document date (not ingest date)
3. `## Type` — PRD / transcript / spec / design / api / misc
4. `## Key Takeaways` — 5–8 bullet points of the most important facts
5. `## Entities Mentioned` — list with links
6. `## Modules Mentioned` — list with links
7. `## Decisions Extracted` — list with links to decision pages
8. `## Wiki Pages Created/Updated` — complete list of pages touched during this ingest

---

### 2h. Person Page — `wiki/persons/<name>.md`

**Frontmatter:**
```yaml
---
type: person
team: <team name>
last_updated: YYYY-MM-DD
---
```

**Required Sections:**
1. `## Role` — job title / function
2. `## Team` — which team they belong to
3. `## Module Ownership` — links to modules they own
4. `## Areas of Expertise` — links to modules/concepts they know deeply

---

## Section 3 — Index & Log Conventions

### index.md Format

```markdown
# Wiki Index
_Last updated: YYYY-MM-DD_
_Total pages: N | Modules: N | Entities: N | Concepts: N_

## Modules
| Page | Summary | Status | Owner | Depends On |
|------|---------|--------|-------|------------|
| [[modules/auth]] | Authentication & session management | active | Platform | — |

## Concepts
| Page | Summary | Used By |
|------|---------|---------|

## Entities
| Page | Summary | Owned By |
|------|---------|----------|

## Integrations
| Page | Summary | Used By |
|------|---------|---------|

## Cross-Module
| Page | Modules Involved | Topic |
|------|-----------------|-------|

## Decisions
| Page | Date | Status | Modules |
|------|------|--------|---------|

## Sources Ingested
| Page | Type | Date | Pages Touched |
|------|------|------|---------------|
```

**Rules for index.md:**
- Every page in `wiki/` (except `index.md`, `log.md`, `overview.md`, `glossary.md`) MUST have a row in the correct table.
- Update counts in the header on every ingest.
- Use `[[wikilinks]]` for all page references.

### log.md Format

```markdown
## [YYYY-MM-DD HH:MM] ingest | <source title>
- Created: [[page1]], [[page2]]
- Updated: [[page3]], [[page4]]
- Flags: <any contradictions or open questions>

## [YYYY-MM-DD HH:MM] query | <question asked>
- Pages read: [[page1]]
- Answer saved as: [[concepts/caching-strategy]] (or "not saved")

## [YYYY-MM-DD HH:MM] lint | health check
- Issues found: <list>
- Fixed: <list>
- Deferred: <list>
```

**Rules for log.md:**
- NEVER edit existing entries. Only append.
- Always include a timestamp.
- Always list every page created or updated, not just a summary.
- Flag any contradictions discovered with ⚠️.

---

## Section 4 — INGEST Workflow (9 Steps)

When told **"ingest raw/\<path\>"**, execute ALL 9 steps in order without skipping:

### Step 1 — Read the Source
Read the entire source document. Do not skim or summarize prematurely.
If it is a PDF, read all pages. Note the document date, author (if mentioned), and document type.

### Step 2 — Discuss Before Proceeding
Summarize the document in **5–8 bullet points** covering:
- What module(s) it describes
- Key features or capabilities introduced
- Entities mentioned
- Dependencies revealed
- Decisions or trade-offs made
- Anything surprising or potentially conflicting with existing pages

Present this to the user and confirm before writing any wiki pages.

### Step 3 — Create a Source Summary Page
Write `wiki/sources/<filename>.md` (strip file extension from path for the page name).
Fill in all required sections from the Section 2g template above.

### Step 4 — Process Entities
Identify every data model, domain object, or system entity mentioned.

For each entity:
- **If an entity page exists** at `wiki/entities/<name>.md` → open it, add new fields or notes, append the source reference to the relevant sections.
- **If no entity page exists** → create a new one using the 2c template.

### Step 5 — Process Modules
Identify every module mentioned or clearly implied.

For each module:
- **If a module page exists** → open it, update relevant sections (Key Features, Dependencies, Used By, API Endpoints, Open Questions). Add the new source citation.
- **If no module page exists** → create a new one. If there isn't enough information to fill all sections, create it with `status: stub` and leave a `## Open Questions` section noting what's missing.

### Step 6 — Identify Cross-Module Connections
After processing all modules, explicitly check:
- Does any entity appear in more than one module? → Update both modules' `Data Entities Used` sections. Create or update `wiki/cross-module/<moduleA>-<moduleB>.md`.
- Does Module A call Module B's API? → Update `Dependencies on Other Modules` on Module A and `Used By` on Module B. Document in the cross-module page.
- Do two modules share a concept (e.g., rate limiting, event bus, idempotency)? → Create or update `wiki/concepts/<concept>.md` and link both modules to it.

### Step 7 — Extract Decisions
Identify any architecture or technology decisions, explicit trade-offs, or choices documented in the source.

For each decision:
- Create `wiki/decisions/YYYY-MM-DD-<short-title>.md` using the 2e template.
- The date should be the document date, not the ingest date.

### Step 8 — Update Glossary
Scan the source for:
- New terms or abbreviations not already in `wiki/glossary.md`
- Deprecated names or aliases
- Terms used differently than in existing pages (flag as ⚠️ Conflict if so)

Add all new terms to the glossary table.

### Step 9 — Update Index and Log
1. Open `wiki/index.md`. Add a row for every **new** page created. Update the page count header.
2. Open `wiki/log.md`. Append a new entry with:
   - Timestamp
   - Operation: `ingest`
   - Source title
   - All pages created (listed individually)
   - All pages updated (listed individually)
   - Any flags or contradictions

### Critical Rules During Ingest

- **If a new fact contradicts an existing wiki page:** Do NOT silently overwrite. Add a `⚠️ Conflict` block to the affected page AND the source summary page. Ask the user for resolution.
- **If a module is mentioned but under-documented:** Create a stub with `status: stub` and an `## Open Questions` section.
- **Always cite sources:** Every section you write or update must end with `_Source: [[sources/<filename>]]_`.
- **Bidirectional links are mandatory:** If Module A's page says `depends_on: [B]`, Module B's page MUST have `used_by: [A]` in its frontmatter and `Used By` section.

---

## Section 5 — QUERY Workflow

When the user asks a question about the product, modules, or architecture:

1. Read `wiki/index.md` first to identify which pages are relevant.
2. Read those specific wiki pages (NOT the raw/ source files — the wiki is the authoritative view).
3. Synthesize an answer with inline citations using wikilinks: `(see [[modules/auth]])`.
4. After answering, ask: "Should I save this as a wiki page?" 
   - If yes: create it at `wiki/concepts/<topic>.md` or `wiki/cross-module/<topic>.md` as appropriate, and update `wiki/index.md` and `wiki/log.md`.
   - If no: log the query in `wiki/log.md` under `## [timestamp] query | <question>` as "not saved".

---

## Section 6 — LINT Workflow

When told **"lint the wiki"**, perform all checks below and report everything before making any fixes:

### Check 1 — Broken Dependency Links
Scan all `wiki/modules/*.md` frontmatter. For every module name in `depends_on`, verify a corresponding page exists at `wiki/modules/<name>.md`. List all missing pages.

### Check 2 — Orphan Pages
Find every page in `wiki/` (excluding index, log, overview, glossary) that has no inbound wikilinks from any other page. List all orphans.

### Check 3 — Missing Cross-Module Pages
Scan all module pages. Find any two modules that share an entity (same entity listed in both `Data Entities Used` sections) but have no corresponding `wiki/cross-module/` page. Flag these pairs.

### Check 4 — Contradictions
Scan for the same entity or concept described with different field names, types, or ownership in different pages. Flag all discrepancies with ⚠️.

### Check 5 — Stubs
List all pages where frontmatter contains `status: stub`, and suggest which `raw/` documents might have information to fill them in (based on module names and topics).

### Check 6 — Stale Pages
Read `wiki/log.md`. Find any source that was ingested more than 30 days ago whose corresponding module pages have not had a log entry since. Flag these as potentially stale.

### Reporting & Resolution
After listing all findings, present them grouped by severity:
- 🔴 Critical: broken links, ownership conflicts
- 🟡 Warning: missing cross-module pages, stubs
- 🟢 Info: orphans, potentially stale pages

Ask the user which fixes to apply before changing anything.

---

## Section 7 — Cross-Module Connection Rules

This is the most important section for maintaining the integrity of the wiki.

### Mandatory Checks on Every Ingest

After processing a document, you MUST explicitly ask yourself each of these questions:

**Entity Overlap:**
Does any entity in this doc already appear in any existing module page?
→ Update both modules' `Data Entities Used` sections.
→ Create or update `wiki/cross-module/<moduleA>-<moduleB>.md`.
→ Confirm entity ownership in `wiki/entities/<entity>.md` under `Source of Truth`.

**API Dependencies:**
Does any module in this doc call APIs or consume output from another module?
→ Update `Dependencies on Other Modules` on the calling module.
→ Update `Used By` on the providing module.
→ Document the specific API contract (endpoint, data passed, auth method) in the cross-module page.

**Shared Concepts:**
Do two or more modules implement the same concept (rate limiting, idempotency, event-driven communication, caching)?
→ Create or update `wiki/concepts/<concept>.md`.
→ Link both modules to the concept page.
→ Note any differences in implementation between the modules.

**Ownership Conflicts:**
Does this doc claim ownership of an entity already owned by another module?
→ FLAG immediately. Add a `⚠️ Conflict: Ownership Disputed` block to:
  - The entity page
  - Both module pages
  - The cross-module page
→ Do NOT resolve silently. Ask the user.

### Bidirectionality Rule
If `wiki/modules/A.md` has `depends_on: [B]`, then `wiki/modules/B.md` MUST have `used_by: [A]`.
This applies to frontmatter AND to the body text sections.
Enforce this on every ingest — check both directions before marking a step complete.

---

## Section 8 — Session Start Checklist

At the start of every new session (before taking any action):

- [ ] Read `CLAUDE.md` (this file) completely
- [ ] Read `wiki/index.md` to know the current state of the wiki
- [ ] Read `wiki/log.md` (last 10 entries) to know what was recently done
- [ ] Read `wiki/overview.md` to have the big-picture context
- [ ] Report to the user:
  - How many modules, entities, concepts, integrations, and decisions exist
  - The most recent ingest (what doc, what date)
  - Any open flags or stubs noted in recent log entries
- [ ] Ask the user: "What would you like to do — ingest a document, ask a question, or lint the wiki?"

Do not start any task until the checklist is complete.
