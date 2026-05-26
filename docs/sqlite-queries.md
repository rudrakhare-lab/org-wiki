# SQLite Query Playbook — `raw/jira/tickets.sqlite`

This is the agent's go-to reference for ticket aggregates. Pattern-match against
the user's question, pick the closest query, adapt the WHERE clause.

**Always read [`CLAUDE.md` Section 9](../CLAUDE.md#section-9--jira-layer-awareness) first** — it tells you *when* to use SQLite vs MCP vs wiki.

## Conventions

- All queries run from the repo root: `cd /Users/rudrakhare/Desktop/my-wiki/org-wiki`
- Wrap multi-line SQL in heredoc:
  ```bash
  sqlite3 raw/jira/tickets.sqlite <<'SQL'
  SELECT ...
  SQL
  ```
- Use `-header -column` for human-readable output, `-csv` for piping
- `priority` column is **canonical P0-P4** (already normalized) — don't filter on raw "Highest"
- `functional_area` holds raw Jira values (e.g. `WP-admin`) — **do not translate to module slugs in SQL**; that mapping lives in `config/functional_area_to_module.toml`
- **Open vs closed → use `status_category`, NEVER `status`.** `status_category` has 4 stable values: `new`, `indeterminate`, `done`, `undefined`. `status` is freeform per Jira project (you'll see "Open", "Waiting on Tech", "In Review", "Backlog", etc.) — filtering on it will silently miss tickets.
  - Open tickets → `status_category IN ('new', 'indeterminate')`
  - Closed/resolved → `status_category = 'done'`
  - Limbo (unset/cancelled-without-resolution) → `status_category = 'undefined'`
- Date columns are ISO 8601 strings — string comparison works correctly (`>= '2026-01-01'`)
- Cite at most 5 ticket keys per response; for more, offer to print the SQL

## Column cheat-sheet (don't guess — copy from here)

| Group | Columns |
|-------|---------|
| Identity | `key`, `project`, `type` |
| State | `status`, `status_category`, `priority`, `resolution` |
| Text | `summary`, `description_text`, `description_raw_json`, `resolution_text`, `comments_text`, `comments_raw_json`, `comment_count` |
| Classification | `functional_area`, `components_json`, `labels_json`, `triage_tier`, `triage_reason`, `last_triaged_at` |
| People | `reporter_account_id`, `reporter_display_name`, `assignee_account_id`, `assignee_display_name` |
| Structure | `parent_key`, `epic_key`, `links_json`, `external_urls_json`, `attachments_json` |
| **Dates** (all end with `_at`) | `created_at`, `updated_at`, `resolved_at`, `fetched_at`, `normalized_at` |
| Pipeline | `source_filter`, `embedding_id` |

All date columns end with `_at`. There is no `created`, `updated`, or `resolved` column.

## Sync CLI cheat-sheet (don't invent flags)

`scripts/jira_sync.py` accepts exactly these mode flags (mutually exclusive):

| Flag | Purpose |
|------|---------|
| `--backfill` | Full historical pull, resumable |
| `--incremental` | Only tickets updated since last successful run |
| `--ticket KEY` | Refresh one ticket by key |
| `--report` | Print distribution report from existing SQLite (no API call) |

And these modifiers:

| Flag | Purpose |
|------|---------|
| `--filter A` / `--filter B` / `--filter all` | Pick which JQL filter from `config/jira.toml` |
| `--limit N` | Stop after N issues per filter (testing) |
| `--dry-run` | Fetch + normalize, do not write |
| `-v` | Verbose logging |

There is no `--functional-area` flag. To get tickets for a specific functional area, the JQL in `config/jira.toml` must be edited (filters A and B already constrain to the six target functional areas). If the user wants a different area, edit the config — never invent CLI flags.

---

## 1. Schema reminder

```bash
sqlite3 raw/jira/tickets.sqlite ".schema tickets"
```

Key columns: `key`, `project`, `type`, `status_category`, `priority`,
`functional_area`, `summary`, `description_text`, `comments_text`,
`created_at`, `updated_at`, `resolved_at`, `triage_tier`, `triage_reason`,
`external_urls_json`, `links_json`, `parent_key`, `epic_key`.

---

## 2. Total mirror size + last sync

```sql
sqlite3 -header -column raw/jira/tickets.sqlite <<'SQL'
SELECT
  COUNT(*) AS total,
  MIN(created_at) AS oldest_ticket,
  MAX(created_at) AS newest_ticket,
  (SELECT MAX(ended_at) FROM sync_runs WHERE status='success') AS last_successful_sync
FROM tickets;
SQL
```

When opening a session, run this to ground your answers in the current
mirror state.

---

## 3. Open P0/P1 by functional_area

> *"How many open P0s are there in WP-admin?"*

```sql
sqlite3 -header -column raw/jira/tickets.sqlite <<'SQL'
SELECT functional_area, priority, COUNT(*) AS n
FROM tickets
WHERE status_category IN ('new', 'indeterminate')
  AND priority IN ('P0', 'P1')
GROUP BY functional_area, priority
ORDER BY functional_area, priority;
SQL
```

Substitute `functional_area = 'WP-admin'` to focus on one area.

---

## 4. Recently resolved tickets with substantive content

> *"Show me recently resolved WF-wis-booking tickets with substantial resolution text."*

```sql
sqlite3 -header -column raw/jira/tickets.sqlite <<'SQL'
SELECT key, priority, resolved_at, length(description_text) + length(coalesce(comments_text, '')) AS content_size, summary
FROM tickets
WHERE status_category = 'done'
  AND resolved_at >= date('now', '-90 days')
  AND functional_area = 'WF-wis-booking'
  AND comment_count >= 2
ORDER BY content_size DESC
LIMIT 10;
SQL
```

Use `content_size` as a proxy for "substantial" — there's no built-in
`resolution_text` field in this Jira instance, so resolution context lives
in description + comments.

---

## 5. Cross-project tickets touching multiple functional areas

> *"Are there tickets that span both TS and WSP related to workflows?"*

Single tickets only have one `functional_area`. Cross-area signals come from
**linked issues** instead. Look at issuelinks JSON:

```sql
sqlite3 -header -column raw/jira/tickets.sqlite <<'SQL'
SELECT t1.key AS ticket, t1.project, t1.functional_area AS area_a,
       json_extract(j.value, '$.outward') AS linked_to,
       t2.functional_area AS area_b,
       t1.summary
FROM tickets t1, json_each(t1.links_json) j
LEFT JOIN tickets t2 ON t2.key = json_extract(j.value, '$.outward')
WHERE t2.key IS NOT NULL
  AND t1.functional_area != t2.functional_area
ORDER BY t1.created_at DESC
LIMIT 20;
SQL
```

Pairs of tickets with different functional areas linked to each other are
strong signals for cross-module concerns — candidates for `cross-module/`
synthesis.

---

## 6. Tickets with linked external docs (likely wiki-worthy)

> *"Which tickets reference Confluence or Figma — they're often the architecturally interesting ones."*

```sql
sqlite3 -header -column raw/jira/tickets.sqlite <<'SQL'
SELECT key, functional_area, priority, status_category,
       json_array_length(external_urls_json) AS url_count, summary
FROM tickets
WHERE json_array_length(external_urls_json) >= 2
ORDER BY url_count DESC, priority
LIMIT 15;
SQL
```

Tickets with 2+ external links to design/spec docs are prime candidates for
Tier 3 promotion (Phase 3).

---

## 7. Stale tickets — open but no activity

> *"What's been ignored for too long?"*

```sql
sqlite3 -header -column raw/jira/tickets.sqlite <<'SQL'
SELECT key, project, priority, functional_area, updated_at, summary
FROM tickets
WHERE status_category IN ('new', 'indeterminate')
  AND updated_at < date('now', '-90 days')
ORDER BY priority, updated_at
LIMIT 20;
SQL
```

For a strict definition of "no activity", also require `comment_count = 0`
(tickets that nobody has even commented on).

---

## 8. Top reporters by functional_area

> *"Who's filing tickets in WF-empexp?"*

```sql
sqlite3 -header -column raw/jira/tickets.sqlite <<'SQL'
SELECT functional_area, reporter_display_name, COUNT(*) AS n
FROM tickets
WHERE functional_area IS NOT NULL
GROUP BY functional_area, reporter_display_name
HAVING n >= 3
ORDER BY functional_area, n DESC;
SQL
```

Useful for: "who is the SME on X area?" and "is one customer dominating
this area's tickets?"

---

## 9. Top assignees (who's bearing the load)

```sql
sqlite3 -header -column raw/jira/tickets.sqlite <<'SQL'
SELECT assignee_display_name, COUNT(*) AS open,
       SUM(CASE WHEN priority='P0' THEN 1 ELSE 0 END) AS p0,
       SUM(CASE WHEN priority='P1' THEN 1 ELSE 0 END) AS p1
FROM tickets
WHERE status_category IN ('new', 'indeterminate')
  AND assignee_display_name IS NOT NULL
GROUP BY assignee_display_name
HAVING open >= 5
ORDER BY p0 DESC, p1 DESC, open DESC
LIMIT 15;
SQL
```

---

## 10. Resolution time distribution

> *"How long do P0s take to resolve?"*

```sql
sqlite3 -header -column raw/jira/tickets.sqlite <<'SQL'
SELECT priority,
       COUNT(*) AS resolved,
       ROUND(AVG(julianday(resolved_at) - julianday(created_at)), 1) AS avg_days,
       ROUND(MIN(julianday(resolved_at) - julianday(created_at)), 1) AS min_days,
       ROUND(MAX(julianday(resolved_at) - julianday(created_at)), 1) AS max_days
FROM tickets
WHERE resolved_at IS NOT NULL
  AND resolved_at >= date('now', '-180 days')
GROUP BY priority
ORDER BY priority;
SQL
```

For a per-area breakdown, add `functional_area` to GROUP BY.

---

## 11. Tickets needing classification (Phase 3 work)

```sql
sqlite3 -header -column raw/jira/tickets.sqlite <<'SQL'
SELECT COUNT(*) AS unprocessed
FROM tickets
WHERE triage_tier IS NULL
  AND triage_reason IS NULL;            -- exclude empty-shells, already auto-flagged

SELECT COUNT(*) AS empty_shells
FROM tickets WHERE triage_reason = 'empty-shell';

SELECT triage_tier, COUNT(*) AS n
FROM tickets WHERE triage_tier IS NOT NULL
GROUP BY triage_tier;
SQL
```

These three queries together are the classifier dashboard — run before and
after each `triage.py` batch.

---

## 12. Empty-shell tickets (auto-flagged in Tier 0)

> *"How many tickets carry no information at all?"*

```sql
sqlite3 -header -column raw/jira/tickets.sqlite <<'SQL'
SELECT functional_area, status_category, COUNT(*) AS n
FROM tickets
WHERE triage_reason = 'empty-shell'
GROUP BY functional_area, status_category
ORDER BY functional_area, n DESC;
SQL
```

Empty-shells are tickets with no description, no comments, and no resolution
text. They're noise — the Phase 3 classifier will short-circuit them to
`triage_tier = 'ignore'`.

---

## 13. Tickets in an epic

> *"What's in epic PB-1234?"*

```sql
sqlite3 -header -column raw/jira/tickets.sqlite <<'SQL'
SELECT key, type, status_category, priority, summary
FROM tickets
WHERE epic_key = 'PB-1234' OR parent_key = 'PB-1234'
ORDER BY created_at;
SQL
```

In modern Jira Cloud, epic membership is via `parent_key` when the parent's
type is `Epic`. We capture both forms.

---

## 14. Recent activity in one functional_area (Phase 4 enrichment preview)

> *"Show me the top 5 recent tickets in WF-wis-meeting-vms."*

```sql
sqlite3 -header -column raw/jira/tickets.sqlite <<'SQL'
SELECT key, status_category, priority, comment_count,
       date(updated_at) AS updated, summary
FROM tickets
WHERE functional_area = 'WF-wis-meeting-vms'
  AND updated_at >= date('now', '-30 days')
ORDER BY
  CASE priority WHEN 'P0' THEN 0 WHEN 'P1' THEN 1 WHEN 'P2' THEN 2
                WHEN 'P3' THEN 3 ELSE 4 END,
  comment_count DESC,
  updated_at DESC
LIMIT 5;
SQL
```

This is the same shape `enrich_modules.py` will produce in Phase 4.

---

## 15. High-discussion tickets (often architecturally interesting)

```sql
sqlite3 -header -column raw/jira/tickets.sqlite <<'SQL'
SELECT key, comment_count, priority, status_category, functional_area, summary
FROM tickets
WHERE comment_count >= 5
ORDER BY comment_count DESC
LIMIT 20;
SQL
```

Long comment threads usually contain debate, decisions, or postmortem
context — strong candidates for Tier 3 promotion.

---

## 16. Distribution by source filter (which JQL caught what)

```sql
sqlite3 -header -column raw/jira/tickets.sqlite <<'SQL'
SELECT source_filter, COUNT(*) AS n
FROM tickets
GROUP BY source_filter
ORDER BY n DESC;
SQL
```

`A` = Filter A (TS+SUP+TO+SE), `B` = Filter B (TB+PB), `A,B` = ticket caught
by both (rare, but it happens at functional-area intersections).

---

## 17. Tickets containing a keyword (full-text-ish over normalized text)

> *"Find tickets mentioning 'Outlook'."*

```sql
sqlite3 -header -column raw/jira/tickets.sqlite <<'SQL'
SELECT key, functional_area, priority, status_category, summary
FROM tickets
WHERE summary LIKE '%Outlook%' COLLATE NOCASE
   OR description_text LIKE '%Outlook%' COLLATE NOCASE
   OR comments_text LIKE '%Outlook%' COLLATE NOCASE
ORDER BY updated_at DESC
LIMIT 20;
SQL
```

This is a substring scan — fine for Phase 1 sample sizes. For 35K tickets
the embedding index (Phase 5) will be the better tool. Avoid `LIKE` queries
that don't anchor on a column-significant prefix when the mirror is large.

---

## 18. Recent sync run history (operational health)

```sql
sqlite3 -header -column raw/jira/tickets.sqlite <<'SQL'
SELECT id, started_at, ended_at, mode, filter_name,
       tickets_fetched, tickets_new, tickets_updated, status
FROM sync_runs
ORDER BY id DESC
LIMIT 10;
SQL
```

If the most recent run isn't `status = 'success'`, surface that to the user
before answering anything else — stale or partial data leads to wrong
answers.

---

## Translating ticket areas to wiki modules

Whenever an answer references a `functional_area`, also add the wiki module
name from `config/functional_area_to_module.toml`:

```bash
# Read the mapping inline
python3 -c "
import tomllib
with open('config/functional_area_to_module.toml', 'rb') as f:
    print(tomllib.load(f))
"
```

If the area has no mapping (e.g. `WP-admin`), state that explicitly:

> "23 open P0s in `WP-admin`. This functional area is not yet mapped to a
> wiki module — it's likely admin-experience but unconfirmed."

This is the linkage between Tier 0 (raw tickets) and the wiki layer. Don't
silently assume.

---

## Anti-patterns — don't do these

1. **Don't dump 50-row result sets into chat.** If you find more than 5
   relevant tickets, summarize the count + a couple of representative keys
   and offer to print the SQL.
2. **Don't translate raw priority strings to canonical in the WHERE clause.**
   The DB already holds canonical P0-P4; filtering by `'Highest'` returns
   nothing.
3. **Don't try to JOIN module pages from SQLite.** Wiki pages aren't in the
   DB. Use the TOML mapping or read the wiki page directly.
4. **Don't claim a `functional_area = 'X'` ticket "belongs to module Y"
   without checking the TOML.** Some areas don't map yet.
5. **Don't write to `tickets.sqlite` directly.** All writes go through
   `scripts/jira_sync.py` (idempotent UPSERT). Manual edits will be
   clobbered on the next sync.
6. **Don't treat Jira matches as a flat list.** A 2023 ticket and a 2026
   ticket about the same property can disagree because the product changed.
   Always rank by recency + status; see §19 below for the canonical
   ranked-search pattern. Count-only matching produces wrong answers when
   product behavior evolves over time.

---

## Time-aware ranking patterns (§19–22)

These patterns are the canonical Jira retrieval shape used by the QUERY
workflow ([`CLAUDE.md` Section 5](../CLAUDE.md#section-5--query-workflow)).
Use them when answering user questions, not when doing offline analysis.

The rule: **Jira evidence is a timeline.** Tickets are dated observations of
how the product behaved at a moment in time. Older tickets may describe
behavior that has since changed. Recency + status + content richness ranks
evidence; raw match count does not.

---

## 19. Ranked keyword search — the canonical query

> *"What does Jira say about `<config or feature>`?"*

```sql
sqlite3 -header -column raw/jira/tickets.sqlite <<'SQL'
SELECT key, status_category, priority,
       date(updated_at)  AS updated,
       date(resolved_at) AS resolved,
       comment_count,
       substr(summary, 1, 100) AS summary
FROM tickets
WHERE (summary          LIKE '%<KEYWORD>%' COLLATE NOCASE
    OR description_text LIKE '%<KEYWORD>%' COLLATE NOCASE
    OR comments_text    LIKE '%<KEYWORD>%' COLLATE NOCASE)
ORDER BY
  -- Resolved tickets with substantive content rank highest
  CASE WHEN status_category = 'done' AND resolved_at IS NOT NULL THEN 0 ELSE 1 END,
  -- Then by recency of update (newest first)
  updated_at DESC,
  -- Comment count breaks ties (richer context = stronger evidence)
  comment_count DESC
LIMIT 20;
SQL
```

Optional filter to scope by area:
```
AND functional_area = 'WF-empexp'
```

This single query produces the input for bucketing into Latest / Historical /
Stale-open per the QUERY workflow. Always start here, not with a `LIMIT 10`
unranked search.

---

## 20. Bucketed evidence — Latest vs Historical

> *"Split the matches into current vs historical evidence."*

```sql
sqlite3 -header -column raw/jira/tickets.sqlite <<'SQL'
WITH matches AS (
  SELECT key, status_category, priority, summary,
         updated_at, resolved_at, comment_count,
         length(description_text) + length(coalesce(comments_text, '')) AS content_size
  FROM tickets
  WHERE summary          LIKE '%<KEYWORD>%' COLLATE NOCASE
     OR description_text LIKE '%<KEYWORD>%' COLLATE NOCASE
     OR comments_text    LIKE '%<KEYWORD>%' COLLATE NOCASE
)
SELECT
  CASE
    WHEN status_category = 'done' AND (
           resolved_at >= date('now', '-180 days')
           OR (comment_count >= 2 AND content_size >= 500)
         ) THEN 'LATEST'
    WHEN updated_at >= date('now', '-180 days')
         THEN 'LATEST'
    WHEN status_category IN ('new', 'indeterminate')
         AND updated_at < date('now', '-180 days')
         THEN 'STALE-OPEN'
    ELSE 'HISTORICAL'
  END AS bucket,
  key, status_category, priority,
  date(updated_at)  AS updated,
  date(resolved_at) AS resolved,
  comment_count,
  substr(summary, 1, 90) AS summary
FROM matches
ORDER BY
  -- Latest first, then Historical, then Stale-open
  CASE bucket WHEN 'LATEST' THEN 0 WHEN 'HISTORICAL' THEN 1 ELSE 2 END,
  updated_at DESC
LIMIT 25;
SQL
```

Use the bucket column to populate the **Latest evidence** and
**Historical evidence** sections of the answer template. Stale-open tickets
are usually noise; mention only if directly relevant to the question.

---

## 21. Detecting evolution — has this ticket been superseded?

> *"Has the behavior described in `<OLD-KEY>` been replaced by something newer?"*

Linked issues carry evolution signal (`supersedes`, `is replaced by`,
`blocks`, `duplicates`). Trust the newer side of a link.

```sql
sqlite3 -header -column raw/jira/tickets.sqlite <<'SQL'
SELECT t1.key AS source, date(t1.updated_at) AS src_updated,
       json_extract(j.value, '$.type') AS link_type,
       json_extract(j.value, '$.outward') AS linked_key,
       date(t2.updated_at) AS linked_updated,
       t2.status_category AS linked_status,
       substr(t2.summary, 1, 80) AS linked_summary
FROM tickets t1, json_each(t1.links_json) j
LEFT JOIN tickets t2 ON t2.key = json_extract(j.value, '$.outward')
WHERE t1.key = '<OLD-KEY>'
  AND t2.key IS NOT NULL
ORDER BY t2.updated_at DESC;
SQL
```

For an inverse lookup ("what links INTO this ticket?"), replace `$.outward`
with `$.inward` or do a JSON scan over all tickets. If any linked ticket is
newer AND resolved, treat the older ticket as historical/superseded.

---

## 22. Confidence indicators — what makes a ticket strong evidence

Use this scoring shape when deciding which tickets to cite. It encodes the
ranking dimensions from
[`CLAUDE.md` Section 9 — Ranking Jira evidence](../CLAUDE.md#section-9--jira-layer-awareness).

```sql
sqlite3 -header -column raw/jira/tickets.sqlite <<'SQL'
SELECT key,
       status_category,
       date(updated_at)  AS updated,
       date(resolved_at) AS resolved,
       comment_count,
       length(description_text) + length(coalesce(comments_text, '')) AS content_size,

       -- Direct hit on a config/property name in summary (highest signal)
       CASE WHEN summary LIKE '%<KEYWORD>%' COLLATE NOCASE THEN 1 ELSE 0 END AS hits_summary,

       -- Linked-issue evolution (newer replacement exists)
       CASE WHEN json_array_length(links_json) > 0 THEN 1 ELSE 0 END AS has_links,

       -- Composite recency score (180-day half-life)
       CAST((julianday('now') - julianday(updated_at)) AS INTEGER) AS age_days,

       substr(summary, 1, 80) AS summary
FROM tickets
WHERE summary          LIKE '%<KEYWORD>%' COLLATE NOCASE
   OR description_text LIKE '%<KEYWORD>%' COLLATE NOCASE
   OR comments_text    LIKE '%<KEYWORD>%' COLLATE NOCASE
ORDER BY
  hits_summary DESC,
  CASE WHEN status_category = 'done' THEN 0 ELSE 1 END,
  age_days ASC,
  content_size DESC
LIMIT 15;
SQL
```

Read the rows in order — top rows are highest-confidence evidence.
- `hits_summary=1` + `done` + low `age_days` + high `content_size` → cite first
- `hits_summary=0` + only-in-comments match + old → mention only if no better evidence exists
