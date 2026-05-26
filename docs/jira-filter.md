# Jira Filters — JQL Queries with Rationale

Two named filters drive the sync. Both run every cycle; results are deduped on `key`.
Stored canonical source: `config/jira.toml`. This doc explains the *why*.

---

## Filter A — Tech Support + Tech Ops + Solution Enabler + Support

```jql
project IN (TS, SUP, "TO", SE)
AND "Functional Area" IN (
  WP-admin, WP-workflows, WF-empexp,
  WF-wis-admin, WF-wis-booking, WF-wis-meeting-vms
)
ORDER BY created DESC
```

**Project scope** (verified against `moveinsync.atlassian.net` on 2026-04-29):
- `TS` — Tech Support
- `SUP` — Support (was `WSP` in the original brief; corrected after enumerating visible projects)
- `"TO"` — Tech Ops; quoted because `TO` is a JQL reserved word
- `SE` — Solution Enabler

**Why these projects**: tickets in these projects that touch our six functional areas
are operational evidence — bug reports, support escalations, customer-driven config
changes. They reflect the lived behavior of WorkInSync features.

---

## Filter B — Tableau + Platform Backend

```jql
"Functional Area" IN (
  WP-admin, WP-workflows, WF-empexp,
  WF-wis-admin, WF-wis-booking, WF-wis-meeting-vms
)
AND project IN (TB, PB)
ORDER BY created DESC
```

**Project scope**:
- `TB` — Tech Backlog (engineering work tracker)
- `PB` — Product Backlog (product requirements + tickets)

**Why these projects**: tickets here surface platform-level concerns (data pipeline,
analytics, infrastructure) that touch the same functional areas as customer-facing
work. They're more architectural in nature and are likely to contribute to pattern
synthesis later.

---

## The custom field — `"Functional Area"`

This is the primary axis for module mapping later. It's a custom Jira field whose
values are constrained to a fixed list:

- `WP-admin`
- `WP-workflows`
- `WF-empexp`
- `WF-wis-admin`
- `WF-wis-booking`
- `WF-wis-meeting-vms`

In JQL, custom fields are addressable by display name (`"Functional Area"`,
quoted because of the space) OR by their internal ID (`customfield_11516`).

**Discovery semantics**: `jira_sync.py` calls `/rest/api/3/field` at startup
to populate `tickets.sqlite::custom_field_map`. On this instance the API token
has limited scope and only returns 28 system fields (no custom fields), so
the script falls back to the verified `customfield_11516` from `config/jira.toml`.
The fallback was confirmed via `createmeta` on 2026-04-29 against `PB` project,
issue type `Story`, and resolved on real ticket `TO-25418` (functional area
`WP-admin`).

**Mapping to wiki modules**: the raw `functional_area` value goes into a SQLite
column unchanged. Translation to wiki module slugs happens at synthesis time only,
via `config/functional_area_to_module.toml`. This keeps Tier 0 immutable and
reversible — the mapping is a configuration concern, not a data concern.

---

## Dedupe semantics

When a ticket appears in both filters (rare but possible at functional-area
intersection), it's stored once with `source_filter = 'A,B'`. If only Filter A
matches, `source_filter = 'A'`. Etc.

The dedupe is by `key` (e.g. `TS-1234`), not by content. We never insert two rows
for the same key.

---

## Volume estimates

(Pending — populate from Checkpoint 2 sample report.)

| Filter | Total tickets | Functional area distribution |
|--------|---------------|------------------------------|
| A      | TBD           | TBD                          |
| B      | TBD           | TBD                          |
| Union  | TBD           | TBD                          |
