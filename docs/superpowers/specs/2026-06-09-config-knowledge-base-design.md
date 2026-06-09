# Config Knowledge Base — Design Spec

**Date:** 2026-06-09
**Status:** Approved
**Feature:** Enriched PMS config knowledge base backed by SQLite for accurate, low-latency config lookup

---

## Goal

Replace the current TF-IDF-based config lookup (11 large wiki pages, 800-char excerpt truncation) with a dedicated SQLite config knowledge base covering all ~1800 PMS configs across `.in` and `.com` servers. Each config entry is enriched with Jira ticket cross-references, wiki module page links, hierarchy metadata (`criteriaPriorityList`), and LLM-inferred dependency relationships between configs.

The chatbot gains complete, untruncated context for any config property in a single tool call — accurate answers, ~1ms lookup latency, no TF-IDF scaling penalty.

---

## What Is Already Implemented (Do Not Change)

- `pms_runtime_values` — live config values at BUID / OFFICEID / ROOMID / ROLE level
- `pms_diagnose_property` — full hierarchy walk for one property at one BUID
- `pms_list_offices`, `pms_list_criteria`, `pms_verify_buid` — BUID/office discovery
- `pms_default_properties` — all default property metadata from live PMS API
- The 11 `wiki/configs/*.md` pages — kept as browsable service overviews
- Intent classifier → CONFIGURATION intent already boosts config pages in preflight

---

## Architecture

```
raw/configs/configs.sqlite          ← new config knowledge base (single source of truth)
scripts/build_config_db.py          ← Phase 1: ingest Excel/CSV → SQLite
scripts/enrich_config_db.py         ← Phase 2: Jira links + module links + LLM dependencies
backend/tools/config_tools.py       ← rewrite config_lookup to query SQLite (not wiki TF-IDF)
backend/wiki_graph_api.py           ← add configs as toggleable graph layer
```

No changes to: `wiki_retriever.py`, TF-IDF index, `pms_tools.py`, `preflight.py`, orchestrator, API, or Angular frontend.

---

## Section 1 — SQLite Schema (`raw/configs/configs.sqlite`)

```sql
CREATE TABLE configs (
    id                     INTEGER PRIMARY KEY AUTOINCREMENT,
    property_name          TEXT NOT NULL,
    service                TEXT NOT NULL,
    server                 TEXT NOT NULL CHECK(server IN ('com', 'in', 'both')),
    description            TEXT,
    data_type              TEXT,
    default_value          TEXT,
    customizable           INTEGER,          -- 0/1 boolean
    criteria_priority_list TEXT,             -- JSON array e.g. ["BUID","OFFICEID","ROOMID"]
    category               TEXT,             -- sheet or CSV filename (source grouping)
    UNIQUE(property_name, service, server)
);

CREATE TABLE jira_links (
    property_name  TEXT    NOT NULL,
    jira_key       TEXT    NOT NULL,
    relevance      REAL    NOT NULL,   -- 1.0=summary, 0.7=description, 0.5=comment
    PRIMARY KEY (property_name, jira_key)
);

CREATE TABLE module_links (
    property_name  TEXT    NOT NULL,
    module_slug    TEXT    NOT NULL,   -- e.g. visitor-management, meeting-rooms
    link_type      TEXT    NOT NULL,   -- service_match | wiki_mention
    PRIMARY KEY (property_name, module_slug)
);

CREATE TABLE dependencies (
    property_a   TEXT    NOT NULL,
    property_b   TEXT    NOT NULL,
    dep_type     TEXT    NOT NULL CHECK(dep_type IN ('functional','co_occurrence','structural')),
    direction    TEXT    NOT NULL CHECK(direction IN ('a_requires_b','b_requires_a','bidirectional','correlated')),
    confidence   REAL    NOT NULL,
    evidence     TEXT,                -- JSON: reasoning from LLM or co-occurrence count
    PRIMARY KEY (property_a, property_b, dep_type)
);

-- Full-text search: exact and fuzzy property name lookup
CREATE VIRTUAL TABLE configs_fts USING fts5(
    property_name,
    description,
    category,
    content=configs,
    content_rowid=id
);

-- Keep FTS in sync
CREATE TRIGGER configs_ai AFTER INSERT ON configs BEGIN
    INSERT INTO configs_fts(rowid, property_name, description, category)
    VALUES (new.id, new.property_name, new.description, new.category);
END;
CREATE TRIGGER configs_ad AFTER DELETE ON configs BEGIN
    INSERT INTO configs_fts(configs_fts, rowid, property_name, description, category)
    VALUES ('delete', old.id, old.property_name, old.description, old.category);
END;
CREATE TRIGGER configs_au AFTER UPDATE ON configs BEGIN
    INSERT INTO configs_fts(configs_fts, rowid, property_name, description, category)
    VALUES ('delete', old.id, old.property_name, old.description, old.category);
    INSERT INTO configs_fts(rowid, property_name, description, category)
    VALUES (new.id, new.property_name, new.description, new.category);
END;
```

---

## Section 2 — Ingestion Pipeline (`scripts/build_config_db.py`)

### Source files

| Server | File | Format | Sheets / contents |
|--------|------|--------|-------------------|
| `.in` | `raw/modules/pms-configs-in/All WIS CONFIGS.xlsx` | Excel | 10 sheets (PMS, Visitor Mgmt, Meeting Rooms, Booking Rule Engine, WIS Seat Booking, Guard App, Email Emp Experience, Emp Exp Internal Config, Emp Exp Common Config, APP_SERVER_CONFIGS) |
| `.in` | `raw/modules/pms-configs-in/wis_unique_configs.xlsx` | Excel | Unique configs not in main file |
| `.com` | `raw/modules/pms-configs-com/wis_service_configs/*.csv` | CSV | One file per service |

### Service → PMS service ID mapping

| Sheet / CSV name | PMS service ID |
|-----------------|----------------|
| PMS / 1. PMS.csv | PROJECT-MANAGEMENT-SERVICE |
| Visitor Mgmt / 2. VMS.csv | VISITOR |
| Meeting Rooms / 3. Meeting Rooms.csv | MEETING_ROOMS |
| Booking Rule Engine / 4. Booking Rule Engine.csv | BOOKING-RULE-ENGINE |
| WIS Seat Booking / 5. WIS Seat Booking.csv | WIS-SEAT-BOOKING |
| Guard App / 6. Guard App.csv | GUARD-APP |
| Email Emp Experience / 7. Email Emp Experience.csv | EMAIL-EMP-EXPERIENCE |
| Emp Exp Internal Config / 8. Emp Exp Internal Config.csv | EMP-EXP-INTERNAL-CONFIG |
| Emp Exp Common Config / 9. Emp Exp Common Config.csv | EMP-EXP-COMMON-CONFIG |
| APP_SERVER_CONFIGS / 10+11 App Server Config.csv | APP_SERVER_CONFIG |

### Deduplication rule

- Same `property_name` + `service` in both `.in` and `.com` sources → single row with `server='both'`, description from `.com` (more complete), note `.in` presence
- Only in `.in` → `server='in'`
- Only in `.com` → `server='com'`

### Script behavior

```
python scripts/build_config_db.py [--reset]
```

- `--reset`: drop and recreate the database (full rebuild)
- Without `--reset`: upsert only (update existing rows, insert new ones)
- Prints summary: total inserted, updated, skipped (duplicates), errors

---

## Section 3 — Enrichment Pipeline (`scripts/enrich_config_db.py`)

Run after `build_config_db.py`. Adds Jira links, module links, and dependencies.

### Step A — Jira cross-references (pure SQLite, no LLM)

For each `property_name` in `configs`:
1. Search `raw/jira/tickets.sqlite` for tickets where `summary LIKE '%{property_name}%'` → relevance 1.0
2. Search `description_text LIKE '%{property_name}%'` → relevance 0.7
3. Search `comments_text LIKE '%{property_name}%'` → relevance 0.5
4. Deduplicate (take highest relevance per ticket), keep top 10 per property
5. Write to `jira_links`

Only property names ≥ 8 characters are searched (avoids false positives for short names like "otp", "id").

### Step B — Module links (rule-based)

1. **Service match**: map each `service` → `module_slug` using the table above → `link_type='service_match'`
2. **Wiki mention**: scan all `wiki/*.md` files for exact `property_name` occurrences → `link_type='wiki_mention'`

Write to `module_links`.

### Step C — LLM dependency inference (Claude API, batched)

Uses `claude-haiku-4-5` (cheap, fast) via the Anthropic SDK already installed in `venv/`.

**Batch strategy**: group configs by service (10 groups). For each group:
- Send all property names + descriptions for that service
- Include top Jira co-occurrence pairs (configs mentioned together in same ticket)
- Ask Claude to identify:
  - **Functional deps**: "Property A only has effect if Property B is true/enabled"
  - **Structural deps**: Configs sharing a naming prefix or clearly forming a feature group
  - **Co-occurrence**: Already detected from Jira — Claude confirms or rejects

Output format (structured JSON):
```json
{
  "dependencies": [
    {
      "property_a": "kioskRequireOTPBeforeRegister",
      "property_b": "otpEnabled",
      "dep_type": "functional",
      "direction": "a_requires_b",
      "confidence": 0.92,
      "evidence": "OTP requirement is meaningless if OTP is globally disabled"
    }
  ]
}
```

Write to `dependencies` table. Flag low-confidence entries (< 0.6) for human review.

**Co-occurrence detection (pre-LLM step)**: Count how many Jira tickets mention both property A and property B. Pairs with count ≥ 3 become `dep_type='co_occurrence'` entries directly (no LLM needed).

**Total LLM calls**: ~10 batches × services + ~20 co-occurrence confirmation calls = ~30 API calls total.

---

## Section 4 — Rewritten `config_lookup` Tool

### New behavior

Queries `raw/configs/configs.sqlite` instead of `wiki_retriever.search()`.

**Input**: `property_name` (required), `service` (optional), `server` (optional)

**Query strategy**:
1. Exact match: `WHERE property_name = ?` (case-insensitive)
2. FTS match: `configs_fts MATCH ?` (handles partial names, camelCase fragments)
3. Fallback: original wiki TF-IDF search if SQLite returns nothing

**Output** (full context, no truncation):
```python
{
    "property_name": "kioskRequireOTPBeforeRegister",
    "service": "VISITOR",
    "server": "both",
    "description": "Requires OTP verification before kiosk self-registration completes.",
    "data_type": "Boolean",
    "default_value": "false",
    "customizable": True,
    "criteria_priority_list": ["BUID", "OFFICEID"],   # hierarchy levels supported
    "jira_tickets": [
        {"key": "WF-empexp-4521", "relevance": 1.0, "summary": "Kiosk OTP not triggering..."},
        ...
    ],
    "module_pages": ["visitor-management", "floor-kiosk"],
    "depends_on": [
        {"property": "otpEnabled", "dep_type": "functional",
         "direction": "a_requires_b", "confidence": 0.92}
    ],
    "related_configs": [
        {"property": "kioskOTPLength", "dep_type": "structural"},
        {"property": "kioskOTPExpiry", "dep_type": "structural"}
    ]
}
```

The `criteria_priority_list` field tells the model exactly which hierarchy levels this config supports — so it knows whether to call `pms_diagnose_property` with `officeid` or `roomid` for live diagnosis.

### Tool schema update

Add `fuzzy` boolean parameter (default true): when true, FTS match is tried if exact match returns nothing. When false, exact only (for when the model already knows the precise name).

---

## Section 5 — Graph Integration (`backend/wiki_graph_api.py`)

Add `include_configs` query parameter to `GET /api/wiki/graph` (default: `false`).

When `include_configs=true`:
- Add config nodes: `{id: property_name, label: property_name, type: "config", service: ..., val: jira_link_count}`
- Node size (`val`) = number of Jira links (historically significant configs are bigger)
- Edges: config → module_slug (from `module_links`)
- Config-to-config dependency edges: from `dependencies` table, coloured by `dep_type`
- Config nodes are a distinct colour (e.g. amber) separate from module (blue) and cross-module (green) nodes

Frontend graph page already supports the `type` field for node colouring — no Angular changes needed.

---

## Section 6 — CLAUDE.md Update

Add to Section 5 (QUERY Workflow), after Step 2 (Jira search):

```
### Step 2b — Config lookup (for config property questions)

When the question names or describes a specific PMS config property, call
`config_lookup` BEFORE calling `pms_runtime_values` or `pms_diagnose_property`.
`config_lookup` returns the full static context for that property: description,
which hierarchy levels it supports (criteriaPriorityList), related Jira tickets,
dependent configs, and which module pages document it.

Use `criteria_priority_list` from `config_lookup` to decide which levels to
diagnose: if the list includes "OFFICEID", pass `officeid` to `pms_diagnose_property`.
If it includes "ROOMID", use `criteria='ROOM_ID'` in `pms_list_criteria` first.
```

---

## Files Changed

| File | Action |
|------|--------|
| `raw/configs/configs.sqlite` | CREATE — config knowledge base |
| `scripts/build_config_db.py` | CREATE — ingestion pipeline |
| `scripts/enrich_config_db.py` | CREATE — Jira + module + LLM enrichment |
| `backend/tools/config_tools.py` | MODIFY — rewrite `config_lookup` to query SQLite |
| `backend/wiki_graph_api.py` | MODIFY — add `include_configs` parameter |
| `CLAUDE.md` | MODIFY — add Step 2b to Section 5 |

---

## Constraints

- Do NOT modify `wiki_retriever.py` or the TF-IDF index
- Do NOT modify `pms_tools.py` (live fetch tools unchanged)
- Do NOT modify `wiki/configs/*.md` pages (kept as human-readable overviews)
- Do NOT modify `raw/modules/` source files
- LLM enrichment uses `claude-haiku-4-5` only (cost control)
- `enrich_config_db.py` must be idempotent (safe to re-run; upserts not inserts)
- Jira cross-ref search only for property names ≥ 8 characters
- `build_config_db.py` must complete in < 60 seconds (no network calls)
- `enrich_config_db.py` Jira step must complete in < 5 minutes (pure SQLite)
- `enrich_config_db.py` LLM step: ~30 API calls, estimated < 10 minutes
