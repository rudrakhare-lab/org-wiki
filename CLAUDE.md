# CLAUDE.md — WorkInSync Feature Wiki Schema

---

## Section 1 — Identity & Purpose

## Product Context
This wiki documents **WorkInSync** — a workplace management product with ~22 features
(modules) covering desk booking, meeting rooms, parking, visitor management, meal management,
employee onboarding (provisioning, SSO, access management), kiosks (floor + guard),
mobile app, integrations (MS Teams, third-party), and admin/employee experience surfaces.

Each feature in `raw/modules/` corresponds to a folder in the team's
"Conwo WorkInSync Docs" Google Drive (one-to-one mapping).

## Purpose
You are the AI maintainer of this organization's feature knowledge wiki.
Your job is to read source documents from `raw/` and maintain structured,
interlinked markdown wiki pages in `wiki/`.

You **NEVER** modify files in `raw/`. Raw files are the immutable source of truth.
You **OWN** everything in `wiki/` — create, update, and maintain all pages there.

At the start of every session, read this file completely before doing anything else.
Then read `wiki/index.md` to understand the current state of the wiki.

## Module Naming Convention
Module pages use kebab-case slugs matching `raw/modules/<slug>/`. The known
WorkInSync modules are:

`access-management`, `admin-experience`, `create-employee-form`, `delegation`,
`desk-management`, `digital-wayfinding`, `employee-experience`, `employee-provisioning`,
`esg-dashboard`, `floor-kiosk`, `guard-app-kiosks`, `implementation`,
`meal-management`, `meeting-rooms`, `mobile-app`, `ms-teams-integration`,
`parking-management`, `safe-reach`, `sso`, `tags-desk-parking`, `third-party`,
`visitor-management`

**PMS Config sources** (not product modules — these are server configuration stores):

`pms-configs-in` — configs live on the `.in` server (e.g. `wis.moveinsync.com` India region)
`pms-configs-com` — configs live on the `.com` server (global/international customers)
`_root` — Drive root-level docs not belonging to a single feature folder

When a doc references a module not in this list, treat it as a new module and
create a slug in the same kebab-case style.

---

## Server Architecture — `.in` vs `.com`

WorkInSync runs two production server environments that serve different customer
sets. PMS (Property Management Service) configs differ between them:

| Dimension | `.in` server | `.com` server |
|-----------|-------------|---------------|
| Source slug | `pms-configs-in` | `pms-configs-com` |
| Config file | `All WIS CONFIGS.xlsx` + `wis_unique_configs.xlsx` | `wis_service_configs.xlsx` |
| Schema | `Property Name \| Description` | `Property Name \| Data Type \| Description` |
| Coverage | Subset — fewer configs per service | More complete — superset in most services |
| Visitor service name | "Visitor Mgmt" sheet | "VMS" sheet (same service) |

**When answering config queries:**
1. Always ask (or state) which server the user is asking about if not specified.
2. If a config exists on one server but not the other, call that out explicitly:
   `⚠️ This config exists on .com only — not present in .in server config list.`
3. If the config has no description in either source, say:
   `Description not documented in PMS config files. Check Jira or ping the owning team.`
4. Configs are case-sensitive — preserve exact casing from source files.

**Ingestion rule for config CSVs:**
- Each sheet in the PMS Config xlsx maps to one WorkInSync service/module.
- Sheet name → module mapping:
  - `1. PMS` → `pms` (general/cross-cutting properties)
  - `2. Visitor Mgmt` / `2. VMS` → `visitor-management`
  - `3. Meeting Rooms` → `meeting-rooms`
  - `4. Booking Rule Engine` → `booking-rule-engine` (cross-cutting, not a standalone module)
  - `5. WIS Seat Booking` → `desk-management`
  - `6. Guard App` → `guard-app-kiosks`
  - `7. Email Emp Experience` → `employee-experience`
  - `8. Emp Exp Internal Config` → `employee-experience`
  - `9. Emp Exp Common Config` → `employee-experience`

**Known missing services (NOT yet ingested — confirmed 2026-05-08):**

These services exist in production but their config sheets are NOT in the ingested
PMS config xlsx files. When a query returns no result, check whether it might belong
to one of these before answering "undocumented":

| # | Service | Known properties | Notes |
|---|---------|-----------------|-------|
| 11 | `ETS` (Employee Transport Service) | `indemnifyOfficeBookingTransport` (BOOLEAN, default=false), `commuteMandatory` (BOOLEAN), `showCabs` | Confirmed missing — ETS properties sourced from Jira only (PB-52960, SE-51628, SE-47565) |

**APP_SERVER_CONFIG — ingested 2026-05-14.** 49 properties (42 on both servers, 1 .in-only, 6 .com-only).
See [[configs/app-server-config]]. Source: sheets 10–11 of `wis_service_configs.xlsx` (.com xlsx).

Until these are ingested, do NOT answer "not in config sources" for transport-related
properties — they likely live in ETS. Jira is the only source available for ETS.

- Create a `wiki/configs/<service-slug>.md` page for each service with a
  dual-server comparison table. Link it from the module page.

**wis_unique_configs.xlsx (`.in` only):**
- A deduplicated master list of all 642 unique configs across all `.in` services.
- Columns: `Property Name | Description | Service(s) | Service Count`
- Use this as a quick lookup reference — if a property appears in >1 service,
  `Service Count > 1` flags it.
- When a config's description is blank in a service sheet but populated here,
  prefer this description.

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

### 2i. Config Page — `wiki/configs/<service-slug>.md`

Stores the PMS property-level configuration reference for one WorkInSync service.
One page per service (not per server). The page contains a dual-server comparison table.

**Frontmatter:**
```yaml
---
type: config
module: <linked module slug>
servers: [in, com]          # which servers have this service's config
last_updated: YYYY-MM-DD
sources:
  in: "[[sources/pms-configs-in-<file>]]"
  com: "[[sources/pms-configs-com-<file>]]"
---
```

**Required Sections:**
1. `## Service` — one-line description of what this service does, link to module page
2. `## Config Comparison` — table with columns:
   `Property Name | .in present | .com present | Data Type (.com) | Description`
   - ✅ = present, — = not in that server's config list
   - Mark with `⚠️ undocumented` if description is blank in both sources
3. `## .in-only Configs` — list of properties in `.in` but not `.com` (if any)
4. `## .com-only Configs` — list of properties in `.com` but not `.in` (if any)
5. `## Missing Descriptions` — properties with no description in either source

**Query behaviour:**
When a user asks about a specific config property and it is missing from the config
page description, fall back in this order:
1. `wis_unique_configs` CSV (`.in` master list — often has descriptions)
2. `Copy of Workplace_PMS Description (Cleaned).xlsx` sheets in `_root`
3. Jira tickets (SQLite query)
4. If still not found: respond with `"Description not documented — contact owning team."`

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

**CRITICAL — raw_path accuracy:** The `raw_path` frontmatter field MUST be the exact
relative path to the file as it actually exists in `raw/modules/`, including any leading
spaces or "Copy of" prefixes in the filename. Run `ls raw/modules/<slug>/` to confirm
the exact filename before writing. An incorrect `raw_path` causes false "broken reference"
alerts in the ingest audit.

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

When the user asks a question about the product, modules, architecture, or any config property,
execute **all steps** below in order. Steps 1–4 MUST all run before answering. A complete-looking
result from any single step does NOT let you skip the rest.

### Step 1 — Read the wiki
Read `wiki/index.md` to identify relevant pages. Then read those specific wiki pages
(NOT raw/ source files — the wiki is the authoritative documented view).

### Step 2 — Search Jira SQLite with time-aware ranking

**MANDATORY — no exceptions.** Every query runs a Jira SQLite search alongside the wiki lookup,
not as a fallback. The search MUST rank tickets by recency, status, and content quality —
not just count matches.

**Jira evidence is a timeline, not a flat list.** Historical tickets describe behavior that
may no longer be true. A 2023 ticket and a 2026 ticket about the same property can disagree
because the product changed in between. Treating them as equal weight produces wrong answers.

**Default ranked-search query** (substitute `<KEYWORD>`; optionally add `functional_area` filter):

```sql
SELECT key, status_category, priority,
       date(updated_at) AS updated, date(resolved_at) AS resolved,
       comment_count,
       substr(summary, 1, 100) AS summary
FROM tickets
WHERE (summary LIKE '%<KEYWORD>%' COLLATE NOCASE
    OR description_text LIKE '%<KEYWORD>%' COLLATE NOCASE
    OR comments_text LIKE '%<KEYWORD>%' COLLATE NOCASE)
ORDER BY
  -- Resolved tickets with substantive content rank highest
  CASE WHEN status_category = 'done' AND resolved_at IS NOT NULL THEN 0 ELSE 1 END,
  -- Then by recency of update (newest first)
  updated_at DESC,
  -- Comment count breaks ties (richer context = stronger evidence)
  comment_count DESC
LIMIT 20;
```

**Faster alternative — use the helper:**
```bash
python scripts/query_jira_ranked.py "<keyword>"          # returns bucketed markdown
python scripts/query_jira_ranked.py "<keyword>" --area WF-empexp
python scripts/query_jira_ranked.py "<keyword>" --include-stale
```

The helper does the bucketing for you and outputs the three groups ready to drop into the
response template (see Step 4).

**Bucket the matched tickets into three groups based on dates and status:**

| Bucket | Definition | Weight |
|--------|------------|--------|
| **Latest evidence** | Updated within last 180 days, OR resolved within last 180 days, OR resolved any time with substantive resolution (≥2 comments + ≥500 chars body+comments) | Strong — represents current behavior |
| **Historical evidence** | Resolved or last updated >180 days ago, with substantive content | Weak — describes past behavior; may be stale |
| **Stale-open** | Open (`status_category IN ('new','indeterminate')`) and not updated in >180 days | Discount — likely abandoned; mention only if directly relevant |

For each candidate ticket, also score (and weight in the ranking):
- **Direct hit** — exact config/property/module name appears in summary or description (strong boost)
- **Linked-issue evolution** — `links_json` shows "replaces" / "supersedes" / "blocks" to a newer ticket → trust the newer one
- **Resolution clarity** — has resolution + substantive comments → trust over open tickets of any age

**If the first keyword returns nothing**, try synonyms, related property names, or partial
matches. Do not stop after one failed query.

**If Jira returns no relevant results after multiple attempts:** explicitly state
"No relevant Jira tickets found for this query" — do NOT silently omit the Jira step.

**"Not documented" is NEVER a final answer** until both wiki AND Jira return nothing.

### Step 3 — Detect conflict and evolution

After bucketing, explicitly ask:

1. **Do Latest and Historical buckets describe the same behavior?**
   → No conflict; use Latest.
2. **Do they disagree on value, default, owner, or behavior of the same property/feature?**
   → **Conflict detected.** Surface both with the timeline in your answer.
3. **Does a Latest ticket reference an older one as superseded** ("we replaced X with Y",
   "old config is deprecated", "this fixes <OLD-KEY>")?
   → **Evolution.** Note the change explicitly; trust the newer one.
4. **Does the Latest ticket itself describe "current behavior" or fix a previously-broken state?**
   → Strong signal Historical evidence is now stale.

**Never silently choose one bucket.** If conflict exists, surface it in the answer with ⚠️.

### Step 4 — Synthesize using the structured answer format

Combine wiki + ranked Jira evidence into the structured response below. **Every query response
must use this format.** Do not skip sections; write `—` if a section has no content.

For config-property questions specifically: also combine with PMS runtime evidence
(live values from `pms_debug.py` if a customer/BUID is specified) and the config catalog page
(`wiki/configs/<service>.md`).

### Step 5 — Save or log

After answering, ask: "Should I save this as a wiki page?"
- If yes: create it at `wiki/concepts/<topic>.md` or `wiki/cross-module/<topic>.md`
  as appropriate, and update `wiki/index.md` and `wiki/log.md`.
- If no: log the query in `wiki/log.md` under `## [timestamp] query | <question>` as "not saved".

### Step 6 — Log answer and request feedback (MANDATORY for product/config/architecture queries)

This step closes the learning loop. Every product/config/architecture answer MUST be logged
so user feedback can be linked back to the exact answer and turned into wiki improvements.
Skip Step 6 only for trivial meta-queries ("how do I run X?", greetings, etc.).

**Before answering** — quickly check `wiki/known-answer-patterns.md` for failure patterns
that match the incoming question shape. If a known pattern applies, name it explicitly in
your reasoning and apply the correct behavior. (At session start the checklist already
surfaces this; the in-query check catches questions that arrive mid-session.)

**After answering**:

1. **Log the answer** with `scripts/log_answer.py`. Capture: question (verbatim), full
   answer text, confidence (High/Medium/Low — same value used in the answer template),
   and all cited sources. The script returns a stable `answer_id` (12-char sha1 prefix).

   ```bash
   venv/bin/python scripts/log_answer.py log \
     --question "<verbatim user question>" \
     --answer-text "<full answer text>" \
     --confidence Medium \
     --wiki "wiki/modules/X.md,wiki/configs/Y.md" \
     --jira "TS-36471,PB-66727" \
     --pms "VISITOR:kioskRequireOTPBeforeRegister" \
     --retrieval-notes "ranked query bucketed 2 Latest / 0 Historical" \
     --quiet
   ```

2. **End the response with the feedback prompt**:

   ```
   ---
   **Review this answer:** Score 1–5 (5 = fully correct).
   **Answer ID:** `<answer_id>`
   If score ≤3, tell me what was wrong or what the answer should have said.
   ```

3. **If the user replies with score ≤3 and a correction**, record it:

   ```bash
   venv/bin/python scripts/record_feedback.py record \
     --question "<verbatim>" --answer-id "<answer_id>" \
     --score 2 --label missing_pms_runtime \
     --correction "<user's correction>" \
     --sources "<sources from the original answer>" \
     --affected "<wiki paths or service:property tokens>"
   ```

   Then ask: **"Should I apply this correction to the wiki now?"**

4. **If yes, run apply in dry-run first, show the plan, then apply on confirmation**:

   ```bash
   venv/bin/python scripts/apply_feedback.py --feedback-id <fid>            # plan
   venv/bin/python scripts/apply_feedback.py --feedback-id <fid> --apply    # write
   ```

   `apply_feedback.py` writes a "Feedback Notes" block (marked with an HTML comment for
   idempotency) into the affected wiki page(s), appends `wiki/log.md`, and marks the
   feedback record resolved. If the label has appeared 3+ times across all feedback, the
   script prints a CLAUDE.md guardrail recommendation — review and add manually.

5. **For score 4–5**: no patch needed by default. For score 5, optionally append a
   sanitized entry to `wiki/known-answer-patterns.md` under "Good examples" if the
   answer demonstrates a reusable pattern.

See `docs/feedback-loop-workflow.md` for the full design, label→patch routing table,
and worked examples.

---

### Query response format — MANDATORY STRUCTURE

Every product/config/architecture query must use this format. Sections with no content get
a single dash `—`, not removed.

```
**Answer:**
<best current answer in 1–3 sentences, written as a definitive statement>

**Latest evidence** (current behavior, last ~6 months):
- <KEY> — updated YYYY-MM-DD (resolved YYYY-MM-DD if applicable) — <what it tells us>
- <KEY> — <date> — <what it tells us>

**Historical evidence** (older context, may be stale):
- <KEY> — <date> — <what it said at the time>

**Conflict / evolution:**
<Explain if behavior changed over time, what was superseded, or "—" if Latest and Historical agree>

**Confidence:** High | Medium | Low
<One-line reason: recency + agreement + wiki backing>

**Sources:**
- Wiki/docs: [[wikilinks]] or "—"
- Jira: KEY-1, KEY-2 (max 5 inline; offer SQL for more)
- PMS configs/runtime: [[configs/X]] or live values, or "—"
```

**Confidence calibration:**
- **High** — Wiki agrees with 2+ Latest tickets; no conflicts; resolved tickets with clear resolutions
- **Medium** — Single Latest ticket OR mild conflict OR wiki silent but Latest tickets agree
- **Low** — Strong Latest-vs-Historical conflict, OR only Historical evidence available, OR wiki claims X but no Jira evidence either way

**Rules that MUST NOT be violated:**

1. **Never answer from a single old Jira ticket if newer relevant tickets exist.** Recency wins by default; only an old ticket with explicit "current behavior" framing and no contradicting newer ticket overrides this.
2. **Never collapse Historical evidence into the headline Answer** without flagging it. Old behavior may be wrong now.
3. **Confidence must reflect evidence strength**, not your assertiveness. "Low" is a legitimate, expected answer.
4. **Extract facts from ticket content** (summary, description, comments, resolution text, linked tickets) — do not just cite ticket keys without saying what they say.
5. **If buckets conflict**, state it explicitly with ⚠️. Never silently prefer one without saying why.
6. **Jira evidence is a timeline.** Treat tickets as dated observations, never as a flat list of equally-weighted facts.

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
- [ ] Note current Jira layer state — `sqlite3 raw/jira/tickets.sqlite "SELECT COUNT(*) FROM tickets;"` (Section 9)
- [ ] **Run the ingest audit** — `python scripts/audit_ingest.py --skip-copies` — and note the output
- [ ] **Check pending feedback** — `python scripts/record_feedback.py summary` — note any pending count
- [ ] Read `wiki/known-answer-patterns.md` (skim, not full) — so failure patterns are in working memory
- [ ] Report to the user:
  - How many modules, entities, concepts, integrations, and decisions exist
  - The most recent ingest (what doc, what date)
  - Number of Jira tickets in SQLite + last sync timestamp
  - Any open flags or stubs noted in recent log entries
  - **How many raw files are not yet ingested** (from the audit above) — list them by module
  - **Pending feedback count** — if >0: "N feedback items pending — run `apply_feedback.py --all-pending --dry-run` to see patch plans"
- [ ] If uningeseted files exist, offer: "There are N uningeseted files in raw/. Want me to ingest them before we continue?"
- [ ] Ask the user: "What would you like to do — ingest pending docs, ask a question, lint the wiki, or apply pending feedback?"

Do not start any task until the checklist is complete.

---

## Section 9 — Jira Layer Awareness

The repo contains a Jira integration with three access patterns. Choose correctly.

### When to use the Atlassian MCP connector
- Live status of a specific ticket the user named ("is TS-1234 still open?")
- Recently created tickets that may not be in the SQLite mirror yet (the
  mirror is updated nightly via `--incremental` after the initial backfill)
- Single-ticket detail not present in the local mirror

### When to query SQLite via bash
- Aggregate questions ("how many open P0s in WP-admin?")
- Cross-ticket pattern questions ("what auth-related tickets resolved last quarter?")
- Filtering by `functional_area`, project, status, date ranges
- Anything where the answer involves more than 2-3 tickets

Use:
```bash
sqlite3 raw/jira/tickets.sqlite "SELECT ..."
```

Schema and example queries are in `docs/sqlite-queries.md`. Read it before
formulating SQL — it's the canonical playbook.

### When to read wiki pages
- Architectural questions ("how does Auth connect to Payments?")
- Module behavior, design rationale, decisions
- Anything covered by existing `modules/`, `concepts/`, `entities/`, `cross-module/`,
  `decisions/` pages

### THE QUERY PRINCIPLE — wiki + Jira always, both sources mandatory

**CHANGED from "wiki first, Jira as fallback" — that model failed in practice.**

The old model caused "undocumented" to become a terminal state. Jira was never
consulted unless the user explicitly asked, causing incorrect "unknown" answers
for properties that had clear Jira evidence (e.g., `showEmployeeProfileOfficeOnly`,
`hideBookingTimeMealOnly`, `mealCutoffInMinutes` reference point).

**New rule:** Every user query runs both wiki lookup AND Jira SQLite search.
The wiki provides documented structure; Jira provides operational reality and history.
Neither is sufficient alone.

Answer structure:
1. Wiki fact (if exists) — cited with `[[wikilink]]`
2. Jira confirmation or enrichment — cited with ticket keys
3. If wiki and Jira conflict — flag with ⚠️ explicitly
4. If Jira returns nothing — state "No relevant Jira tickets found"
5. "Not documented" is only a valid answer AFTER both sources return nothing

DO NOT enumerate ticket lists. Cite at most 5 ticket keys inline.
For more, offer a SQL query the user can run, or propose a pattern page.

### Functional area to module mapping

The `functional_area` column in `tickets.sqlite` holds raw Jira values like
`WP-admin`, `WF-empexp`, etc. Translation to wiki module slugs is curated in
`config/functional_area_to_module.toml`. Always consult that file before
claiming "tickets about X module" — the mapping is intentional and may
differ from naive name matching.

Current state of the mapping (verified 2026-04-29):

| `functional_area` | Maps to wiki modules | Notes |
|-------------------|----------------------|-------|
| `WF-empexp` | `employee-experience` | Direct match |
| `WF-wis-booking` | `desk-management`, `parking-management` | desk-management not yet ingested |
| `WF-wis-meeting-vms` | `meeting-rooms`, `visitor-management` | Combined area |
| `WP-admin` | _(unmapped)_ | Likely admin-experience + admin tooling — pending |
| `WP-workflows` | _(unmapped)_ | May indicate missing `workflow-engine` module |
| `WF-wis-admin` | _(unmapped)_ | Likely admin-experience — pending |

If a `functional_area` with significant ticket volume has no module mapping,
flag it as a gap in the wiki. Do NOT auto-create a module from tickets
(see Section 10, Rule 6).

### Search order for every query (both must run)

1. **Wiki pages** — read relevant `wiki/modules/`, `wiki/configs/`, `wiki/concepts/` pages.
2. **Jira SQLite** — always, on every query. Extract keywords from the question and search
   `description_text` (and `summary`, `comments_text` if needed). **Always rank by recency +
   status, not just match count.** See "Ranking Jira evidence" below.
3. `config/functional_area_to_module.toml` — when bridging ticket areas to module slugs.
4. **MCP connector** — only for live single-ticket lookups or tickets too recent for the mirror.

Steps 1 and 2 are parallel, not sequential. Do not wait for wiki to "fail" before searching Jira.

### Ranking Jira evidence — recency and status awareness

Jira tickets are not equal weight. A 2026 resolved ticket about a property is stronger evidence
than 5 unresolved 2023 tickets about the same property. Rank evidence on these dimensions, in
priority order:

1. **Direct match precision** — exact config/property/module name in summary or description
   beats partial/keyword match in comments. Boost direct hits.
2. **Status_category + resolution clarity** — `done` with substantive resolution > `done` with
   no resolution text > `indeterminate` > `new` > stale `new`/`indeterminate` (>180 days no
   update). A resolved ticket with substantial comments is the gold standard.
3. **Recency** — `updated_at` and `resolved_at` are the timeline. Recent (≤180 days) >
   moderately old (180d–1yr) > old (>1yr). The default `ORDER BY` should be `updated_at DESC`
   within each status tier.
4. **Content richness** — `comment_count` ≥ 2 AND `length(description_text) + length(comments_text)`
   ≥ 500 chars indicates actual discussion. Empty-shells and one-liners are weak evidence.
5. **Linked-issue evolution** — if `links_json` shows a "supersedes" / "blocks" / "duplicate of"
   relationship to a newer ticket, the newer ticket carries authority. Always check links on
   the top-ranked older tickets.
6. **Bucket into Latest / Historical / Stale-open** per Section 5 Step 2 thresholds.

**Conflict detection** — if Latest and Historical buckets describe the same property with
different values, defaults, or behaviors, you have a conflict. Surface it explicitly in the
answer; do not silently choose one.

**Never** count matching tickets and treat the highest count as winning. **Always** check
timestamps and status before forming an answer.

See `docs/sqlite-queries.md` §19–22 for ranked-query SQL templates, and
`scripts/query_jira_ranked.py` for a pre-bucketed helper.

---

## Section 10 — Linking Rules (Mandatory)

These rules govern how Jira-derived content connects to existing wiki structure.
Violating them produces an unreadable Obsidian graph. Non-negotiable.

### Rule 1: Tickets don't link out
Individual ticket pages in `wiki/sources/jira/` link sparingly — at most one
module page and one decision page if directly relevant. They do NOT enumerate
concept links, entity links, or other ticket links.

### Rule 2: Pattern pages are the bridge
Pattern pages in `wiki/patterns/` are where Jira-derived content connects to
modules. Each pattern page links to: 1-3 module pages, 0-2 concept pages, and
lists its contributing ticket keys (which resolve to SQLite, not wiki pages).
Pattern pages NEVER link to individual `wiki/sources/jira/<KEY>.md` files —
those are evidence, the pattern is the synthesis.

### Rule 3: Module pages reference patterns, never individual tickets
Module pages get a "Related Patterns" section linking to pattern pages.
Module pages NEVER enumerate individual ticket links — even for major
incidents. Major incidents get a Tier 3 page in `wiki/sources/jira/<KEY>.md`
and are linked from a relevant decision page or pattern page, not directly
from the module.

### Rule 4: Auto-generated sections live between markers
Auto-appended content in module pages goes between:

```
<!-- BEGIN AUTO:RECENT_ACTIVITY -->
<!-- END AUTO:RECENT_ACTIVITY -->

<!-- BEGIN AUTO:KNOWN_ISSUES -->
<!-- END AUTO:KNOWN_ISSUES -->

<!-- BEGIN AUTO:RELATED_PATTERNS -->
<!-- END AUTO:RELATED_PATTERNS -->
```

Anything outside markers is human-owned. Never modify it during synthesis.
The `enrich_modules.py` and `synthesize_patterns.py` scripts (Phase 4 and 5)
operate strictly between markers.

### Rule 5: Existing connections are preserved
Pre-existing module-to-module, module-to-entity, and cross-module links
derived from PRDs and design docs are NEVER modified by ticket synthesis.
If tickets contradict existing wiki claims, flag with `⚠️ Conflict` in the
relevant page and ask the user. Do not silently rewrite.

### Rule 6: No new modules from tickets
Modules are defined by PRDs and specs only. Cluster synthesis MAY identify a
recurring pattern that suggests a missing module — when this happens, flag
it as an "unrepresented area" in the lint report. NEVER auto-create a module
page from ticket clusters.

This applies to functional areas without a wiki mapping (see Section 9):
flag, don't invent.

### Rule 7: Bidirectional links remain mandatory
Existing rule still applies: if A depends on B, B's page says "used by A".
Pattern pages and module enrichment must respect this. If a pattern page
lists `related_modules: [A, B]`, both A and B's `<!-- AUTO:RELATED_PATTERNS -->`
sections must back-link to the pattern.

### Rule 8: Evidence citations vs. synthesis citations
- **Evidence** (Tier 3 ticket sources, frontmatter `type: source`) cite their
  Jira key and URL in frontmatter only. Body never re-pastes ticket lists.
- **Synthesis** (patterns, enriched modules) cite contributing ticket keys
  in frontmatter `contributing_tickets`, NOT inline in prose.

Inline prose may quote a single ticket if it captures the canonical example
of a pattern — keep it to one, not five.

---

## Section 11 — Frontmatter Standards for Synthesized Pages

All Jira-derived pages must include provenance frontmatter.

### Pattern pages — `wiki/patterns/*.md`

```yaml
---
type: pattern
auto_generated: true
human_edited: false
last_synthesized: YYYY-MM-DD
evidence_window: YYYY-MM to YYYY-MM
ticket_count: N
contributing_tickets: [KEY-1, KEY-2, ...]
related_modules: [module1, module2]
related_concepts: []
cluster_id: <hdbscan-cluster-id-from-phase-5>
---
```

### Tier 3 ticket source pages — `wiki/sources/jira/*.md`

```yaml
---
type: source
source_kind: jira
jira_key: PROJ-1234
jira_url: https://moveinsync.atlassian.net/browse/PROJ-1234
ingested: YYYY-MM-DD
related_modules: [module1]
related_decisions: [decision-page-1]
---
```

### Synthesized epic pages — `wiki/epics/*.md`

```yaml
---
type: epic
auto_generated: true
last_synthesized: YYYY-MM-DD
epic_key: PROJ-EPIC-1
epic_url: https://moveinsync.atlassian.net/browse/PROJ-EPIC-1
status: active|done|abandoned
modules: [module1, module2]
child_count: N
---
```

### Protection flag

The `human_edited: true` flag, when manually set on a pattern or epic page,
protects the page body from prose rewrites during re-synthesis. Only
frontmatter and `contributing_tickets` get updated; body is preserved.

If you ever set `human_edited: true`, also bump `last_synthesized` and add
a body footer:

```
> Note: human-edited from synthesized output on YYYY-MM-DD by <name>.
> Subsequent runs will not overwrite the body.
```

### Lint expectations

The linter (Phase 4+) checks:
- Pattern pages with `last_synthesized` >60 days old → stale flag
- `contributing_tickets` referencing keys not in `tickets.sqlite` → broken evidence flag
- Pages under `wiki/patterns/` or `wiki/sources/jira/` missing `type:` frontmatter → schema flag
- Module pages whose `<!-- AUTO:RECENT_ACTIVITY -->` section hasn't been refreshed in >14 days → stale enrichment flag

---

## Section 12 — Live Config Debug Workflow

Use this when a user reports a bug that might be caused by a PMS config value.
The static wiki and config pages document **default** values only. This workflow
fetches the **actual live values** for a specific customer at each level of the
config hierarchy. Full documentation in `docs/live-config-debug.md`.

### Trigger conditions

Start this workflow when the user says any of:
- "This config isn't working for client X / BUID Y"
- "I set this config but it didn't take effect"
- "Why does this office behave differently?"
- Any question about the *actual* value of a config for a specific customer

### Config hierarchy model

Every PMS property resolves through a priority chain. Most specific wins:

```
DEFAULT  ←  system default (what the wiki documents)
  BUID override       ←  applies to all offices under this BUID
    OFFICEID override ←  applies to one office; overrides BUID
      ROOMID override ←  meeting-rooms only; overrides OFFICEID
      ROLE override   ←  PROJECT-MANAGEMENT-SERVICE only; overrides OFFICEID
```

**Critical:** A BUID-level change has NO effect on an office that has an
OFFICEID-level override for that property. You must know which level the
customer is setting their config at.

### Disambiguation — MANDATORY before fetching anything

**Never assume the server from the BUID name alone.** BUIDs look similar across both
servers and a wrong server choice returns empty results that look like "no config set"
— a very misleading false negative.

Before calling any API, explicitly confirm with the user:

1. **Which server?**
   - `.com` = global / international clients (default if unsure — but ASK, don't assume)
   - `.in` = India-region clients
   - If the user doesn't know: "Is this client hosted at cmsapp.moveinsync.com or cmsapp.moveinsync.in?"
   - The `init` command verifies the BUID on that server and will warn if it's not found —
     use that as a sanity check, not as a substitute for asking.

2. **Which service?** (VISITOR / MEETING_ROOMS / BOOKING-RULE-ENGINE / etc.)

3. **Which BUID?** (e.g. `genpactindia-GInd`)

4. **Which level is the bug at?**
   - All offices under this BUID → fetch BUID level only
   - One specific office → fetch BUID + OFFICEID level (ask for the OFFICEID)
   - One specific room (meeting-rooms) → fetch BUID + OFFICEID + ROOM_ID (ask for each)
   - One specific role (PMS) → fetch BUID + ROLE (values: `employee`, `RECEPTIONIST`, or the UUID)

**Do not guess the server or the level.** Wrong server → empty results. Wrong level → misleading answer.

### BUID–server mismatch detection (automatic)

`init` always calls the roles API and checks whether the given BUID appears in the
accessible BUID list for that server. If not found, it prints a ⚠️ warning and suggests
trying the other server. This is a safety net — confirm with the user before switching.

### Session commands (run via bash)

```bash
# Recommended: export server-specific tokens once, switch freely
export PMS_TOKEN_COM="<com_bearer_token>"   # .com server token
export PMS_TOKEN_IN="<in_bearer_token>"     # .in  server token
export PMS_COOKIE_COM="<com_cookie>"        # optional
export PMS_COOKIE_IN="<in_cookie>"          # optional

# Fallback: single token used for both servers if _COM/_IN not set
export PMS_TOKEN="<bearer_token>"
export PMS_COOKIE="<cookie_string>"

# --server com is the default (omit for .com clients)
# --server in must be specified for India-region clients

# Step 1: init + load defaults
python scripts/pms_debug.py --service VISITOR --buid <buid> init
python scripts/pms_debug.py --server in --service VISITOR --buid <buid> init

# Step 2: fetch BUID level (always)
python scripts/pms_debug.py --service VISITOR --buid <buid> fetch

# Step 3a: fetch office name → OFFICEID mapping (run once per BUID; cached in session)
python scripts/pms_debug.py --service VISITOR --buid <buid> list-offices

# Step 3b: list OFFICEIDs that have any config override (separate from name mapping)
python scripts/pms_debug.py --service VISITOR --buid <buid> list-criteria OFFICEID

# Step 3c: fetch office level config
python scripts/pms_debug.py --service VISITOR --buid <buid> \
    fetch --criteria OFFICEID --value <officeid>

# Step 3c: fetch room level (meeting-rooms)
python scripts/pms_debug.py --service MEETING_ROOMS --buid <buid> \
    fetch --criteria ROOM_ID --value <roomid>

# Step 3d: fetch role level (PMS)
python scripts/pms_debug.py --service PROJECT-MANAGEMENT-SERVICE --buid <buid> \
    fetch --criteria ROLE --value employee

# Step 4: full debug report
python scripts/pms_debug.py --service VISITOR --buid <buid> \
    report --property <propertyName>

# See session state
python scripts/pms_debug.py --service VISITOR --buid <buid> show-session
```

Session files are stored in `/tmp/` — never in the repo.
- `.com` sessions: `/tmp/pms_debug_com_{SERVICE}_{BUID}.json`
- `.in` sessions: `/tmp/pms_debug_in_{SERVICE}_{BUID}.json`

### Service ID reference

| Wiki module | Service ID |
|-------------|-----------|
| `visitor-management` | `VISITOR` |
| `meeting-rooms` | `MEETING_ROOMS` |
| `booking-rule-engine` | `BOOKING-RULE-ENGINE` |
| `desk-management` | `WIS-SEAT-BOOKING` |
| `guard-app-kiosks` | `GUARD-APP` |
| `employee-experience` (email) | `EMAIL-EMP-EXPERIENCE` |
| `employee-experience` (internal) | `EMP-EXP-INTERNAL-CONFIG` |
| `employee-experience` (common) | `EMP-EXP-COMMON-CONFIG` |
| `pms` (role-level configs) | `PROJECT-MANAGEMENT-SERVICE` |

### Response format when using live data

Always combine live config data with wiki + Jira:

```
**Live config values for `<propertyName>` — BUID `<buid>` — service `<service>`**

| Level | Value |
|-------|-------|
| DEFAULT | <from defaults> |
| BUID | <from buid fetch> |
| OFFICEID::<id>  (<office name>) | <from office fetch> |

Effective value: `<winning value>` (set at <winning level>)

Wiki: <definition from [[configs/<module>]]>
Fix: <what to change and where>
Jira: <relevant tickets>
```

### Session is scoped to one (server, service, buid) tuple

One session = one server + one service + one BUID. Sessions for `.com` and `.in` are
stored in separate files even for the same service+buid — they never collide.
To debug across two BUIDs, run two separate sessions by changing `--buid`.
To debug across two servers, run two separate sessions by changing `--server`.

### OFFICEID → office name mapping

Run `list-offices` once per BUID at the start of a debug session. For `.com` this calls
`https://mis-security.moveinsync.com/mis-security-guard/premise/offices/{buid}?premiseType=2`;
for `.in` it calls the equivalent endpoint on `mis-security.moveinsync.in`.
Caches a `{OFFICEID → "Name (City, Country)"}` map in the session file.

Once cached, `diagnose`, `compare`, and `report` outputs automatically show
the human-readable office name alongside every OFFICEID:

```
🔴 `OFFICEID::LOpwcind-PWCP-OC$0-0000-000000000001` — WorkInSync Pune Office → `3` ← CULPRIT
```

If `list-offices` returns empty, verify the BUID string is correct. The mapping
is cached for the lifetime of the session — no re-fetch needed.
