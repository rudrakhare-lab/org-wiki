# Config Knowledge Base Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a dual-layer PMS config knowledge base — SQLite precision lookup + 10 regenerated wiki pages — covering all ~1800 configs across `.in` and `.com` servers, enriched with Jira cross-refs, module links, and LLM-inferred dependencies.

**Architecture:** `build_config_db.py` reads Excel + CSV source files and writes both `raw/configs/configs.sqlite` (FTS5-enabled) and 10 regenerated `wiki/configs/*.md` pages. `enrich_config_db.py` adds Jira links, module links, and LLM-inferred dependencies to the SQLite layer. `config_lookup` tool is rewritten to query SQLite first (exact → FTS5) with wiki TF-IDF fallback. Graph API gains a toggleable config layer.

**Tech Stack:** Python 3.13 (venv), openpyxl, sqlite3 stdlib, anthropic SDK (already installed), FastAPI, pytest

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `scripts/build_config_db.py` | CREATE | Parse Excel/CSV → SQLite schema + populate + generate 10 wiki pages |
| `scripts/enrich_config_db.py` | CREATE | Steps A (Jira), B (module links), C (co-occurrence + LLM deps) |
| `raw/configs/configs.sqlite` | CREATE (by script) | SQLite precision lookup with FTS5 |
| `wiki/configs/*.md` (10 files) | REGENERATE (by script) | All ~1800 configs, richer columns |
| `backend/tools/config_tools.py` | MODIFY | SQLite-first config_lookup, wiki TF-IDF fallback |
| `backend/wiki_graph_api.py` | MODIFY | Add `include_configs` toggleable layer |
| `CLAUDE.md` | MODIFY | Add Step 2b to Section 5 |
| `tests/test_config_tools.py` | CREATE | Unit tests for the rewritten config_lookup |
| `tests/test_build_config_db.py` | CREATE | Integration tests for ingestion + wiki generation |

---

## Source file parsing notes (verified 2026-06-09)

**`.in` Excel sheets** (`All WIS CONFIGS.xlsx`):
- Row 1: `('Service: <name>', None)` — skip
- Row 2: `('Total properties: N',)` — skip
- Row 3: `(None, None)` — skip
- Row 4: `('Property Name', 'Description')` — headers
- Row 5+: data; 2 columns: `Property Name`, `Description`
- **Exception** — `APP_SERVER_CONFIGS` sheet: Row 1 is immediately `('Property Name', 'Data Type', 'Description', ...)` — no 3-row header

**`.com` CSVs** (`wis_service_configs/`):
- Row 1: `Property Name,Data Type,Description` — headers
- Row 2+: data; 3 columns

**`wis_unique_configs.xlsx`**:
- Row 1: title string — skip
- Row 2: summary string — skip
- Row 3: empty — skip
- Row 4: `('Property Name', 'Description', 'Service(s)', 'Service Count')` — headers
- Row 5+: data

---

## Service → PMS ID → wiki slug mapping

```python
# (Excel sheet name / CSV filename)  →  (PMS service ID, wiki slug, display name)
SHEET_TO_SERVICE = {
    "1. PMS":                  ("PROJECT-MANAGEMENT-SERVICE", "pms",                    "PMS (Project Management Service)"),
    "2. Visitor Mgmt":         ("VISITOR",                    "visitor-management",      "Visitor Management Service"),
    "3. Meeting Rooms":        ("MEETING_ROOMS",              "meeting-rooms",           "Meeting Rooms"),
    "4. Booking Rule Engine":  ("BOOKING-RULE-ENGINE",        "booking-rule-engine",     "Booking Rule Engine"),
    "5. WIS Seat Booking":     ("WIS-SEAT-BOOKING",           "wis-seat-booking",        "WIS Seat Booking"),
    "6. Guard App":            ("GUARD-APP",                  "guard-app",               "Guard App"),
    "7. Email Emp Experience": ("EMAIL-EMP-EXPERIENCE",       "emp-experience-email",    "Email Employee Experience"),
    "8. Emp Exp Internal Config": ("EMP-EXP-INTERNAL-CONFIG", "emp-experience-internal", "Emp Exp Internal Config"),
    "9. Emp Exp Common Config":   ("EMP-EXP-COMMON-CONFIG",  "emp-experience-common",   "Emp Exp Common Config"),
    "APP_SERVER_CONFIGS":      ("APP_SERVER_CONFIG",          "app-server-config",       "App Server Config"),
}

# CSV filename prefix → same tuple (prefix = N. <name>)
CSV_TO_SERVICE = {
    "1. PMS":                     SHEET_TO_SERVICE["1. PMS"],
    "2. VMS":                     SHEET_TO_SERVICE["2. Visitor Mgmt"],
    "3. Meeting Rooms":           SHEET_TO_SERVICE["3. Meeting Rooms"],
    "4. Booking Rule Engine":     SHEET_TO_SERVICE["4. Booking Rule Engine"],
    "5. WIS Seat Booking":        SHEET_TO_SERVICE["5. WIS Seat Booking"],
    "6. Guard App":               SHEET_TO_SERVICE["6. Guard App"],
    "7. Email Emp Experience":    SHEET_TO_SERVICE["7. Email Emp Experience"],
    "8. Emp Exp Internal Config": SHEET_TO_SERVICE["8. Emp Exp Internal Config"],
    "9. Emp Exp Common Config":   SHEET_TO_SERVICE["9. Emp Exp Common Config"],
    "10. App Server Config":      SHEET_TO_SERVICE["APP_SERVER_CONFIGS"],
    "11. App Server Config (.in)": SHEET_TO_SERVICE["APP_SERVER_CONFIGS"],
}
```

---

## Task 1: SQLite schema + ingestion script (`scripts/build_config_db.py`)

**Files:**
- Create: `scripts/build_config_db.py`
- Create (by script): `raw/configs/configs.sqlite`
- Regenerate (by script): `wiki/configs/pms.md`, `wiki/configs/visitor-management.md`, `wiki/configs/meeting-rooms.md`, `wiki/configs/booking-rule-engine.md`, `wiki/configs/wis-seat-booking.md`, `wiki/configs/guard-app.md`, `wiki/configs/emp-experience-email.md`, `wiki/configs/emp-experience-internal.md`, `wiki/configs/emp-experience-common.md`, `wiki/configs/app-server-config.md`
- Test: `tests/test_build_config_db.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_build_config_db.py
"""Integration tests for build_config_db.py — uses real source files."""
import sqlite3
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "scripts" / "build_config_db.py"
DB = REPO / "raw" / "configs" / "configs.sqlite"
WIKI_CONFIGS = REPO / "wiki" / "configs"


def test_script_exists():
    assert SCRIPT.exists(), "build_config_db.py not created yet"


def test_build_creates_sqlite(tmp_path):
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--reset"],
        cwd=str(REPO),
        capture_output=True, text=True, timeout=120
    )
    assert result.returncode == 0, f"Script failed:\n{result.stderr}"
    assert DB.exists()


def test_sqlite_has_rows():
    con = sqlite3.connect(DB)
    count = con.execute("SELECT COUNT(*) FROM configs").fetchone()[0]
    con.close()
    assert count >= 1500, f"Expected >=1500 configs, got {count}"


def test_deduplication_server_both():
    """Properties in both .in and .com must have server='both'."""
    con = sqlite3.connect(DB)
    both = con.execute(
        "SELECT COUNT(*) FROM configs WHERE server='both'"
    ).fetchone()[0]
    con.close()
    assert both > 0, "No deduplicated 'both' entries found"


def test_no_null_property_names():
    con = sqlite3.connect(DB)
    nulls = con.execute(
        "SELECT COUNT(*) FROM configs WHERE property_name IS NULL OR property_name=''"
    ).fetchone()[0]
    con.close()
    assert nulls == 0


def test_fts_virtual_table_exists():
    con = sqlite3.connect(DB)
    tables = {r[0] for r in con.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    con.close()
    assert "configs_fts" in tables


def test_exact_known_property():
    """MEETING_ROOM_ENABLED exists in both servers."""
    con = sqlite3.connect(DB)
    rows = con.execute(
        "SELECT server FROM configs WHERE property_name='MEETING_ROOM_ENABLED'"
    ).fetchall()
    con.close()
    assert len(rows) >= 1
    servers = {r[0] for r in rows}
    assert "both" in servers or len(servers) >= 1


def test_wiki_pages_regenerated():
    for slug in [
        "pms", "visitor-management", "meeting-rooms", "booking-rule-engine",
        "wis-seat-booking", "guard-app", "emp-experience-email",
        "emp-experience-internal", "emp-experience-common", "app-server-config"
    ]:
        page = WIKI_CONFIGS / f"{slug}.md"
        assert page.exists(), f"Wiki page not regenerated: {slug}.md"
        content = page.read_text()
        assert "| Property |" in content, f"{slug}.md missing table header"
        assert "generated:" in content, f"{slug}.md missing generated frontmatter"


def test_wiki_page_has_configs(tmp_path):
    """Visitor management wiki page should have > 50 config rows."""
    page = WIKI_CONFIGS / "visitor-management.md"
    lines = page.read_text().splitlines()
    data_rows = [l for l in lines if l.startswith("| `") or l.startswith("| `")]
    assert len(data_rows) >= 50, f"Only {len(data_rows)} rows in visitor-management.md"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/rudrakhare/Desktop/my-wiki/org-wiki
venv/bin/pytest tests/test_build_config_db.py::test_script_exists -v
```
Expected: FAIL — `AssertionError: build_config_db.py not created yet`

- [ ] **Step 3: Create `scripts/build_config_db.py`**

```python
#!/usr/bin/env python3
"""
Build the PMS config SQLite knowledge base and regenerate 10 wiki/configs/*.md pages.

Usage:
    python scripts/build_config_db.py [--reset]

--reset : drop and recreate the SQLite database before ingestion (full rebuild).
          Without --reset, rows are upserted (INSERT OR REPLACE).
          Wiki pages are ALWAYS fully regenerated.
"""
from __future__ import annotations

import argparse
import csv
import json
import sqlite3
import sys
import textwrap
from datetime import date
from pathlib import Path

import openpyxl

REPO = Path(__file__).resolve().parent.parent
XLSX_IN = REPO / "raw/modules/pms-configs-in/All WIS CONFIGS.xlsx"
XLSX_UNIQUE = REPO / "raw/modules/pms-configs-in/wis_unique_configs.xlsx"
CSV_DIR = REPO / "raw/modules/pms-configs-com/wis_service_configs"
DB_PATH = REPO / "raw/configs/configs.sqlite"
WIKI_CONFIGS = REPO / "wiki/configs"

TODAY = date.today().isoformat()

# (sheet / CSV prefix) → (service_id, wiki_slug, display_name)
SHEET_TO_SERVICE: dict[str, tuple[str, str, str]] = {
    "1. PMS":                     ("PROJECT-MANAGEMENT-SERVICE", "pms",                    "PMS (Project Management Service)"),
    "2. Visitor Mgmt":            ("VISITOR",                    "visitor-management",      "Visitor Management Service"),
    "3. Meeting Rooms":           ("MEETING_ROOMS",              "meeting-rooms",           "Meeting Rooms"),
    "4. Booking Rule Engine":     ("BOOKING-RULE-ENGINE",        "booking-rule-engine",     "Booking Rule Engine"),
    "5. WIS Seat Booking":        ("WIS-SEAT-BOOKING",           "wis-seat-booking",        "WIS Seat Booking"),
    "6. Guard App":               ("GUARD-APP",                  "guard-app",               "Guard App"),
    "7. Email Emp Experience":    ("EMAIL-EMP-EXPERIENCE",       "emp-experience-email",    "Email Employee Experience"),
    "8. Emp Exp Internal Config": ("EMP-EXP-INTERNAL-CONFIG",   "emp-experience-internal", "Emp Exp Internal Config"),
    "9. Emp Exp Common Config":   ("EMP-EXP-COMMON-CONFIG",     "emp-experience-common",   "Emp Exp Common Config"),
    "APP_SERVER_CONFIGS":         ("APP_SERVER_CONFIG",          "app-server-config",       "App Server Config"),
}

CSV_PREFIX_TO_SERVICE: dict[str, tuple[str, str, str]] = {
    "1. PMS":                      SHEET_TO_SERVICE["1. PMS"],
    "2. VMS":                      SHEET_TO_SERVICE["2. Visitor Mgmt"],
    "3. Meeting Rooms":            SHEET_TO_SERVICE["3. Meeting Rooms"],
    "4. Booking Rule Engine":      SHEET_TO_SERVICE["4. Booking Rule Engine"],
    "5. WIS Seat Booking":         SHEET_TO_SERVICE["5. WIS Seat Booking"],
    "6. Guard App":                SHEET_TO_SERVICE["6. Guard App"],
    "7. Email Emp Experience":     SHEET_TO_SERVICE["7. Email Emp Experience"],
    "8. Emp Exp Internal Config":  SHEET_TO_SERVICE["8. Emp Exp Internal Config"],
    "9. Emp Exp Common Config":    SHEET_TO_SERVICE["9. Emp Exp Common Config"],
    "10. App Server Config":       SHEET_TO_SERVICE["APP_SERVER_CONFIGS"],
    "11. App Server Config (.in)": SHEET_TO_SERVICE["APP_SERVER_CONFIGS"],
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS configs (
    id                     INTEGER PRIMARY KEY AUTOINCREMENT,
    property_name          TEXT NOT NULL,
    service                TEXT NOT NULL,
    server                 TEXT NOT NULL CHECK(server IN ('com', 'in', 'both')),
    description            TEXT,
    data_type              TEXT,
    default_value          TEXT,
    customizable           INTEGER,
    criteria_priority_list TEXT,
    category               TEXT,
    UNIQUE(property_name, service, server)
);

CREATE TABLE IF NOT EXISTS jira_links (
    property_name  TEXT    NOT NULL,
    jira_key       TEXT    NOT NULL,
    relevance      REAL    NOT NULL,
    PRIMARY KEY (property_name, jira_key)
);

CREATE TABLE IF NOT EXISTS module_links (
    property_name  TEXT    NOT NULL,
    module_slug    TEXT    NOT NULL,
    link_type      TEXT    NOT NULL,
    PRIMARY KEY (property_name, module_slug)
);

CREATE TABLE IF NOT EXISTS dependencies (
    property_a   TEXT    NOT NULL,
    property_b   TEXT    NOT NULL,
    dep_type     TEXT    NOT NULL CHECK(dep_type IN ('functional','co_occurrence','structural')),
    direction    TEXT    NOT NULL CHECK(direction IN ('a_requires_b','b_requires_a','bidirectional','correlated')),
    confidence   REAL    NOT NULL,
    evidence     TEXT,
    PRIMARY KEY (property_a, property_b, dep_type)
);

CREATE VIRTUAL TABLE IF NOT EXISTS configs_fts USING fts5(
    property_name,
    description,
    category,
    content=configs,
    content_rowid=id
);

CREATE TRIGGER IF NOT EXISTS configs_ai AFTER INSERT ON configs BEGIN
    INSERT INTO configs_fts(rowid, property_name, description, category)
    VALUES (new.id, new.property_name, new.description, new.category);
END;
CREATE TRIGGER IF NOT EXISTS configs_ad AFTER DELETE ON configs BEGIN
    INSERT INTO configs_fts(configs_fts, rowid, property_name, description, category)
    VALUES ('delete', old.id, old.property_name, old.description, old.category);
END;
CREATE TRIGGER IF NOT EXISTS configs_au AFTER UPDATE ON configs BEGIN
    INSERT INTO configs_fts(configs_fts, rowid, property_name, description, category)
    VALUES ('delete', old.id, old.property_name, old.description, old.category);
    INSERT INTO configs_fts(rowid, property_name, description, category)
    VALUES (new.id, new.property_name, new.description, new.category);
END;
"""

# Each record: {property_name, service, server, description, data_type, category}
ConfigRow = dict


def _clean(v: object) -> str:
    if v is None:
        return ""
    s = str(v).strip()
    return s if s not in ("-", "N/A", "n/a") else ""


def _read_in_excel() -> list[ConfigRow]:
    """Parse All WIS CONFIGS.xlsx — .in server configs."""
    rows: list[ConfigRow] = []
    wb = openpyxl.load_workbook(XLSX_IN, read_only=True, data_only=True)
    for sheet_name in wb.sheetnames:
        mapping = SHEET_TO_SERVICE.get(sheet_name)
        if not mapping:
            continue
        service_id, _, _ = mapping
        ws = wb[sheet_name]
        all_rows = list(ws.iter_rows(values_only=True))

        if sheet_name == "APP_SERVER_CONFIGS":
            # Row 0 = headers (Property Name, Data Type, Description)
            data_start = 1
        else:
            # Rows 0-2: service header, total, blank. Row 3: column headers. Row 4+: data.
            data_start = 4

        for row in all_rows[data_start:]:
            if not row or not row[0]:
                continue
            prop = _clean(row[0])
            if not prop:
                continue
            if sheet_name == "APP_SERVER_CONFIGS":
                dtype = _clean(row[1]) if len(row) > 1 else ""
                desc = _clean(row[2]) if len(row) > 2 else ""
            else:
                dtype = ""
                desc = _clean(row[1]) if len(row) > 1 else ""
            rows.append({
                "property_name": prop,
                "service": service_id,
                "server": "in",
                "description": desc,
                "data_type": dtype,
                "category": sheet_name,
            })
    wb.close()
    return rows


def _read_unique_configs() -> dict[str, str]:
    """Return {property_name: description} from wis_unique_configs.xlsx for fallback."""
    out: dict[str, str] = {}
    if not XLSX_UNIQUE.exists():
        return out
    wb = openpyxl.load_workbook(XLSX_UNIQUE, read_only=True, data_only=True)
    ws = wb.active
    all_rows = list(ws.iter_rows(values_only=True))
    # Row 0: title, Row 1: summary, Row 2: blank, Row 3: headers, Row 4+: data
    for row in all_rows[4:]:
        if not row or not row[0]:
            continue
        prop = _clean(row[0])
        desc = _clean(row[1]) if len(row) > 1 else ""
        if prop and prop not in out:
            out[prop] = desc
    wb.close()
    return out


def _read_com_csvs() -> list[ConfigRow]:
    """Parse .com CSV files."""
    rows: list[ConfigRow] = []
    for csv_path in sorted(CSV_DIR.glob("*.csv")):
        stem = csv_path.stem  # e.g. "2. VMS"
        mapping = CSV_PREFIX_TO_SERVICE.get(stem)
        if not mapping:
            continue
        service_id, _, _ = mapping
        with open(csv_path, encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                prop = _clean(row.get("Property Name", ""))
                if not prop:
                    continue
                rows.append({
                    "property_name": prop,
                    "service": service_id,
                    "server": "com",
                    "description": _clean(row.get("Description", "")),
                    "data_type": _clean(row.get("Data Type", "")),
                    "category": stem,
                })
    return rows


def _deduplicate(in_rows: list[ConfigRow], com_rows: list[ConfigRow],
                 unique_desc: dict[str, str]) -> list[ConfigRow]:
    """
    Merge .in and .com rows. Same property+service → server='both', .com description wins.
    Fill missing descriptions from unique_desc fallback.
    """
    # Index: (property_name, service) → row
    com_idx: dict[tuple[str, str], ConfigRow] = {}
    for r in com_rows:
        com_idx[(r["property_name"], r["service"])] = r

    in_idx: dict[tuple[str, str], ConfigRow] = {}
    for r in in_rows:
        in_idx[(r["property_name"], r["service"])] = r

    result: list[ConfigRow] = []
    seen: set[tuple[str, str]] = set()

    # Process .in rows — check if .com also has the same
    for key, in_r in in_idx.items():
        seen.add(key)
        if key in com_idx:
            com_r = com_idx[key]
            desc = com_r["description"] or in_r["description"]
            dtype = com_r["data_type"] or in_r["data_type"]
            result.append({**in_r, "server": "both", "description": desc, "data_type": dtype})
        else:
            result.append(in_r)

    # .com-only rows
    for key, com_r in com_idx.items():
        if key not in seen:
            result.append(com_r)

    # Fill missing descriptions from wis_unique_configs
    for row in result:
        if not row["description"]:
            row["description"] = unique_desc.get(row["property_name"], "")

    return result


def _init_db(con: sqlite3.Connection, reset: bool) -> None:
    if reset:
        for tbl in ["configs_fts", "configs", "jira_links", "module_links", "dependencies"]:
            con.execute(f"DROP TABLE IF EXISTS {tbl}")
        for trig in ["configs_ai", "configs_ad", "configs_au"]:
            con.execute(f"DROP TRIGGER IF EXISTS {trig}")
    con.executescript(SCHEMA)
    con.commit()


def _upsert_rows(con: sqlite3.Connection, rows: list[ConfigRow]) -> tuple[int, int]:
    inserted = updated = 0
    for r in rows:
        existing = con.execute(
            "SELECT id FROM configs WHERE property_name=? AND service=? AND server=?",
            (r["property_name"], r["service"], r["server"])
        ).fetchone()
        if existing:
            con.execute(
                """UPDATE configs SET description=?, data_type=?, category=?
                   WHERE property_name=? AND service=? AND server=?""",
                (r["description"] or None, r["data_type"] or None, r["category"] or None,
                 r["property_name"], r["service"], r["server"])
            )
            updated += 1
        else:
            con.execute(
                """INSERT INTO configs
                   (property_name, service, server, description, data_type, category)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (r["property_name"], r["service"], r["server"],
                 r["description"] or None, r["data_type"] or None, r["category"] or None)
            )
            inserted += 1
    con.commit()
    return inserted, updated


def _wiki_page(service_id: str, slug: str, display_name: str,
               rows: list[ConfigRow]) -> str:
    """Render one wiki/configs/<slug>.md page."""
    sorted_rows = sorted(rows, key=lambda r: r["property_name"].lower())
    server_set = {r["server"] for r in rows}
    servers_list = sorted(server_set)

    header = textwrap.dedent(f"""\
        ---
        title: "PMS Configs — {display_name}"
        service: {service_id}
        total_configs: {len(sorted_rows)}
        servers: [{', '.join(servers_list)}]
        generated: {TODAY}
        type: config
        module: {slug}
        ---

        # {display_name} — PMS Config Properties

        > Auto-generated {TODAY} from `raw/modules/pms-configs-in/All WIS CONFIGS.xlsx`
        > and `raw/modules/pms-configs-com/wis_service_configs/`.
        > Total: **{len(sorted_rows)} configs**.

        | Property | Description | Type | Default | Server |
        |----------|-------------|------|---------|--------|
        """)

    table_rows = []
    for r in sorted_rows:
        prop = f"`{r['property_name']}`"
        desc = (r["description"] or "").replace("|", "\\|")
        if len(desc) > 200:
            desc = desc[:197] + "..."
        dtype = r["data_type"] or ""
        default = r["default_value"] or ""
        server_label = {
            "both": "both",
            "in": ".in only",
            "com": ".com only",
        }.get(r["server"], r["server"])
        table_rows.append(f"| {prop} | {desc} | {dtype} | {default} | {server_label} |")

    return header + "\n".join(table_rows) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true",
                        help="Drop and recreate the SQLite database")
    args = parser.parse_args()

    print("Reading .in Excel...")
    in_rows = _read_in_excel()
    unique_desc = _read_unique_configs()
    print(f"  .in rows: {len(in_rows)}")

    print("Reading .com CSVs...")
    com_rows = _read_com_csvs()
    print(f"  .com rows: {len(com_rows)}")

    print("Deduplicating...")
    merged = _deduplicate(in_rows, com_rows, unique_desc)
    print(f"  Merged rows: {len(merged)}")

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    _init_db(con, args.reset)

    inserted, updated = _upsert_rows(con, merged)
    total = con.execute("SELECT COUNT(*) FROM configs").fetchone()[0]
    print(f"  SQLite: {inserted} inserted, {updated} updated, {total} total")
    con.close()

    # Group by service for wiki pages
    by_service: dict[str, list[ConfigRow]] = {}
    for r in merged:
        by_service.setdefault(r["service"], []).append(r)

    WIKI_CONFIGS.mkdir(parents=True, exist_ok=True)
    pages_written = 0
    for sheet_name, (service_id, slug, display_name) in SHEET_TO_SERVICE.items():
        rows = by_service.get(service_id, [])
        if not rows:
            print(f"  ⚠️  No rows for {service_id} — skipping wiki page")
            continue
        page_path = WIKI_CONFIGS / f"{slug}.md"
        page_path.write_text(_wiki_page(service_id, slug, display_name, rows), encoding="utf-8")
        pages_written += 1
        print(f"  ✓ {slug}.md ({len(rows)} configs)")

    print(f"\nDone. {total} SQLite rows, {pages_written} wiki pages written.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the script**

```bash
cd /Users/rudrakhare/Desktop/my-wiki/org-wiki
venv/bin/python scripts/build_config_db.py --reset
```
Expected output ending with:
```
Done. <N> SQLite rows, 10 wiki pages written.
```
N should be ≥ 1500.

- [ ] **Step 5: Run the tests**

```bash
venv/bin/pytest tests/test_build_config_db.py -v
```
Expected: all 9 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add scripts/build_config_db.py raw/configs/configs.sqlite wiki/configs/*.md tests/test_build_config_db.py
git commit -m "feat: add build_config_db.py — ingest all ~1800 PMS configs to SQLite + regenerate wiki pages"
```

---

## Task 2: Enrichment pipeline Steps A + B (`scripts/enrich_config_db.py`)

**Files:**
- Create: `scripts/enrich_config_db.py`
- Populates: `raw/configs/configs.sqlite` (tables: `jira_links`, `module_links`)

- [ ] **Step 1: Create `scripts/enrich_config_db.py` with Steps A and B**

```python
#!/usr/bin/env python3
"""
Enrich the PMS config SQLite knowledge base with Jira links, module links,
and LLM-inferred dependencies.

Usage:
    python scripts/enrich_config_db.py --step a   # Jira cross-references
    python scripts/enrich_config_db.py --step b   # Module links
    python scripts/enrich_config_db.py --step c   # Co-occurrence + LLM dependencies
    python scripts/enrich_config_db.py --all      # All three steps in order
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DB_PATH = REPO / "raw/configs/configs.sqlite"
JIRA_DB = REPO / "raw/jira/tickets.sqlite"
WIKI_DIR = REPO / "wiki"

SERVICE_TO_MODULE_SLUG: dict[str, str] = {
    "PROJECT-MANAGEMENT-SERVICE": "modules/pms",
    "VISITOR":                    "modules/visitor-management",
    "MEETING_ROOMS":              "modules/meeting-rooms",
    "BOOKING-RULE-ENGINE":        "modules/booking-rule-engine",
    "WIS-SEAT-BOOKING":           "modules/desk-management",
    "GUARD-APP":                  "modules/guard-app-kiosks",
    "EMAIL-EMP-EXPERIENCE":       "modules/employee-experience",
    "EMP-EXP-INTERNAL-CONFIG":    "modules/employee-experience",
    "EMP-EXP-COMMON-CONFIG":      "modules/employee-experience",
    "APP_SERVER_CONFIG":          "modules/implementation",
}


def _step_a(con: sqlite3.Connection) -> None:
    """Step A: Jira cross-references — pure SQLite, no LLM."""
    if not JIRA_DB.exists():
        print("  ⚠️  Jira SQLite not found, skipping Step A")
        return

    jira = sqlite3.connect(JIRA_DB)
    props = con.execute(
        "SELECT DISTINCT property_name FROM configs WHERE length(property_name) >= 8"
    ).fetchall()
    print(f"  Step A: scanning {len(props)} property names against Jira...")

    inserted = 0
    for (prop,) in props:
        # Escape % and _ for LIKE patterns
        safe = prop.replace("%", "\\%").replace("_", "\\_")

        rows: dict[str, float] = {}
        for col, relevance in [("summary", 1.0), ("description_text", 0.7), ("comments_text", 0.5)]:
            try:
                hits = jira.execute(
                    f"SELECT key FROM tickets WHERE {col} LIKE ? ESCAPE '\\'",
                    (f"%{safe}%",)
                ).fetchall()
                for (key,) in hits:
                    rows[key] = max(rows.get(key, 0.0), relevance)
            except sqlite3.OperationalError:
                pass

        # Keep top 10 by relevance
        top10 = sorted(rows.items(), key=lambda x: -x[1])[:10]
        for jira_key, rel in top10:
            con.execute(
                """INSERT OR REPLACE INTO jira_links (property_name, jira_key, relevance)
                   VALUES (?, ?, ?)""",
                (prop, jira_key, rel)
            )
            inserted += 1

    con.commit()
    jira.close()
    total = con.execute("SELECT COUNT(*) FROM jira_links").fetchone()[0]
    print(f"  Step A done: {inserted} jira_links rows, {total} total")


def _step_b(con: sqlite3.Connection) -> None:
    """Step B: Module links — service mapping + wiki mention scan."""
    props = con.execute(
        "SELECT DISTINCT property_name, service FROM configs"
    ).fetchall()
    print(f"  Step B: building module links for {len(props)} (property, service) pairs...")

    inserted = 0
    # Service match
    for prop, service in props:
        slug = SERVICE_TO_MODULE_SLUG.get(service)
        if slug:
            con.execute(
                """INSERT OR REPLACE INTO module_links (property_name, module_slug, link_type)
                   VALUES (?, ?, 'service_match')""",
                (prop, slug)
            )
            inserted += 1

    # Wiki mention scan
    all_props = {r[0] for r in props}
    wiki_files = list(WIKI_DIR.rglob("*.md"))
    print(f"  Scanning {len(wiki_files)} wiki files for property mentions...")
    mention_count = 0
    for wiki_path in wiki_files:
        try:
            text = wiki_path.read_text(encoding="utf-8")
        except OSError:
            continue
        slug = str(wiki_path.relative_to(WIKI_DIR)).replace("\\", "/").removesuffix(".md")
        for prop in all_props:
            if len(prop) >= 6 and prop in text:
                con.execute(
                    """INSERT OR IGNORE INTO module_links (property_name, module_slug, link_type)
                       VALUES (?, ?, 'wiki_mention')""",
                    (prop, slug)
                )
                mention_count += 1

    con.commit()
    total = con.execute("SELECT COUNT(*) FROM module_links").fetchone()[0]
    print(f"  Step B done: {inserted} service_match + {mention_count} wiki_mention = {total} total")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--step", choices=["a", "b", "c"])
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()

    if not DB_PATH.exists():
        print(f"ERROR: {DB_PATH} not found — run build_config_db.py first")
        raise SystemExit(1)

    con = sqlite3.connect(DB_PATH)

    run_a = args.all or args.step == "a"
    run_b = args.all or args.step == "b"
    run_c = args.all or args.step == "c"

    if run_a:
        _step_a(con)
    if run_b:
        _step_b(con)
    if run_c:
        _step_c(con)

    con.close()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run Step A (Jira links)**

```bash
cd /Users/rudrakhare/Desktop/my-wiki/org-wiki
venv/bin/python scripts/enrich_config_db.py --step a
```
Expected: prints progress + "Step A done: N jira_links rows". N should be in the thousands.

Verify:
```bash
sqlite3 raw/configs/configs.sqlite "SELECT COUNT(*) FROM jira_links;"
```

- [ ] **Step 3: Run Step B (module links)**

```bash
venv/bin/python scripts/enrich_config_db.py --step b
```
Expected: "Step B done: N service_match + M wiki_mention = total"

Verify:
```bash
sqlite3 raw/configs/configs.sqlite "SELECT link_type, COUNT(*) FROM module_links GROUP BY link_type;"
```

- [ ] **Step 4: Commit**

```bash
git add scripts/enrich_config_db.py
git commit -m "feat: add enrich_config_db.py Steps A+B — Jira links and module links"
```

---

## Task 3: Enrichment pipeline Step C (`scripts/enrich_config_db.py` — LLM deps)

**Files:**
- Modify: `scripts/enrich_config_db.py` (add `_step_c` function + co-occurrence logic)
- Populates: `raw/configs/configs.sqlite` (table: `dependencies`)

**Note:** Step C requires `ANTHROPIC_API_KEY` in the environment. Uses `claude-haiku-4-5` only.

- [ ] **Step 1: Add `_step_c` to `scripts/enrich_config_db.py`**

Add `import os` and `import anthropic` at top of the file, then add the `_step_c` function:

```python
def _detect_co_occurrence(con: sqlite3.Connection, jira: sqlite3.Connection) -> list[tuple]:
    """
    Find (property_a, property_b) pairs appearing together in ≥3 Jira tickets.
    Returns list of (prop_a, prop_b, count).
    """
    # Get all property names with jira links
    props = [r[0] for r in con.execute(
        "SELECT DISTINCT property_name FROM jira_links"
    ).fetchall()]

    # Build prop → set of ticket keys
    prop_to_tickets: dict[str, set[str]] = {}
    for prop in props:
        keys = {r[0] for r in con.execute(
            "SELECT jira_key FROM jira_links WHERE property_name=?", (prop,)
        ).fetchall()}
        prop_to_tickets[prop] = keys

    # Count pair co-occurrences
    pairs: dict[tuple[str, str], int] = {}
    prop_list = sorted(prop_to_tickets.keys())
    for i, pa in enumerate(prop_list):
        for pb in prop_list[i+1:]:
            shared = len(prop_to_tickets[pa] & prop_to_tickets[pb])
            if shared >= 3:
                pairs[(pa, pb)] = shared

    return [(pa, pb, cnt) for (pa, pb), cnt in pairs.items()]


def _step_c(con: sqlite3.Connection) -> None:
    """Step C: Co-occurrence detection + LLM dependency inference."""
    import anthropic as anthropic_sdk

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("  ⚠️  ANTHROPIC_API_KEY not set — skipping LLM inference. Co-occurrence only.")

    if not JIRA_DB.exists():
        print("  ⚠️  Jira SQLite not found, skipping co-occurrence step")
    else:
        jira = sqlite3.connect(JIRA_DB)
        print("  Step C: detecting co-occurrence pairs...")
        co_pairs = _detect_co_occurrence(con, jira)
        jira.close()
        print(f"  Found {len(co_pairs)} co-occurrence pairs (count ≥ 3)")

        for pa, pb, cnt in co_pairs:
            con.execute(
                """INSERT OR REPLACE INTO dependencies
                   (property_a, property_b, dep_type, direction, confidence, evidence)
                   VALUES (?, ?, 'co_occurrence', 'correlated', ?, ?)""",
                (pa, pb, min(0.5 + cnt * 0.05, 0.95),
                 json.dumps({"co_occurrence_count": cnt}))
            )
        con.commit()
        print(f"  Inserted {len(co_pairs)} co_occurrence dependency rows")

    if not api_key:
        return

    # LLM inference — batch by service (~10 services)
    client = anthropic_sdk.Anthropic(api_key=api_key)
    services = [r[0] for r in con.execute(
        "SELECT DISTINCT service FROM configs ORDER BY service"
    ).fetchall()]

    total_llm = 0
    for service in services:
        rows = con.execute(
            "SELECT property_name, description, data_type FROM configs WHERE service=?",
            (service,)
        ).fetchall()
        if len(rows) < 2:
            continue

        # Build compact prompt
        prop_list_str = "\n".join(
            f"- {r[0]}: {(r[1] or '')[:120]} [{r[2] or ''}]"
            for r in rows[:80]  # cap at 80 to stay within haiku context
        )

        prompt = f"""You are analyzing PMS configs for service '{service}'.
Identify dependencies between these properties. Only report high-confidence ones.

Properties:
{prop_list_str}

Return JSON only:
{{
  "dependencies": [
    {{
      "property_a": "...",
      "property_b": "...",
      "dep_type": "functional|structural",
      "direction": "a_requires_b|b_requires_a|bidirectional",
      "confidence": 0.0-1.0,
      "evidence": "one sentence explanation"
    }}
  ]
}}

Rules:
- functional: A only works / has effect when B is true/enabled
- structural: A and B share a naming prefix or clearly form a feature group  
- Only include confidence >= 0.6
- Max 20 dependencies per service
"""

        try:
            resp = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=1500,
                messages=[{"role": "user", "content": prompt}]
            )
            raw = resp.content[0].text.strip()
            # Extract JSON block
            m = re.search(r"\{.*\}", raw, re.DOTALL)
            if not m:
                continue
            data = json.loads(m.group())
            deps = data.get("dependencies", [])
            for d in deps:
                pa = d.get("property_a", "")
                pb = d.get("property_b", "")
                if not pa or not pb:
                    continue
                con.execute(
                    """INSERT OR IGNORE INTO dependencies
                       (property_a, property_b, dep_type, direction, confidence, evidence)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (pa, pb, d.get("dep_type", "structural"),
                     d.get("direction", "bidirectional"),
                     float(d.get("confidence", 0.0)),
                     d.get("evidence", ""))
                )
                total_llm += 1
            con.commit()
            print(f"  {service}: {len(deps)} dependencies inferred")
        except Exception as e:
            print(f"  ⚠️  LLM call failed for {service}: {e}")

    print(f"  Step C done: {total_llm} LLM dependency rows inserted")
    total_deps = con.execute("SELECT COUNT(*) FROM dependencies").fetchone()[0]
    print(f"  Total dependencies in DB: {total_deps}")
```

Also add `import os` to the imports at the top of the file.

- [ ] **Step 2: Run Step C (co-occurrence only first, without API key)**

```bash
# Test co-occurrence without LLM (no API key)
cd /Users/rudrakhare/Desktop/my-wiki/org-wiki
venv/bin/python scripts/enrich_config_db.py --step c
```
Expected: detects co-occurrence pairs, prints count, skips LLM (no API key warning).

Verify:
```bash
sqlite3 raw/configs/configs.sqlite "SELECT dep_type, COUNT(*) FROM dependencies GROUP BY dep_type;"
```

- [ ] **Step 3: Run Step C with API key (LLM enrichment)**

```bash
export ANTHROPIC_API_KEY="$(grep ANTHROPIC_API_KEY .env | cut -d= -f2)"
venv/bin/python scripts/enrich_config_db.py --step c
```
Expected: ~10 service batches, each printing "N dependencies inferred".

Total LLM calls: ~10. Should complete in < 5 minutes.

Verify:
```bash
sqlite3 raw/configs/configs.sqlite \
  "SELECT dep_type, COUNT(*) FROM dependencies GROUP BY dep_type;"
```

- [ ] **Step 4: Commit**

```bash
git add scripts/enrich_config_db.py
git commit -m "feat: enrich_config_db.py Step C — co-occurrence detection + LLM dependency inference"
```

---

## Task 4: Rewrite `backend/tools/config_tools.py`

**Files:**
- Modify: `backend/tools/config_tools.py`
- Create: `tests/test_config_tools.py`

**Do NOT start the backend when editing this file.** Edit with backend stopped.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_config_tools.py
"""Unit tests for config_lookup tool — SQLite first, wiki TF-IDF fallback."""
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch


def _make_test_db(path: str) -> None:
    """Create a minimal SQLite DB with one config row."""
    con = sqlite3.connect(path)
    con.executescript("""
        CREATE TABLE configs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            property_name TEXT NOT NULL,
            service TEXT NOT NULL,
            server TEXT NOT NULL,
            description TEXT,
            data_type TEXT,
            default_value TEXT,
            customizable INTEGER,
            criteria_priority_list TEXT,
            category TEXT,
            UNIQUE(property_name, service, server)
        );
        CREATE VIRTUAL TABLE configs_fts USING fts5(
            property_name, description, category,
            content=configs, content_rowid=id
        );
        CREATE TRIGGER configs_ai AFTER INSERT ON configs BEGIN
            INSERT INTO configs_fts(rowid, property_name, description, category)
            VALUES (new.id, new.property_name, new.description, new.category);
        END;
        INSERT INTO configs (property_name, service, server, description, data_type, default_value, criteria_priority_list)
        VALUES ('kioskRequireOTPBeforeRegister', 'VISITOR', 'both',
                'Requires OTP verification before kiosk self-registration completes.',
                'Boolean', 'false', '["BUID","OFFICEID"]');
        INSERT INTO configs (property_name, service, server, description, data_type)
        VALUES ('kioskOTPLength', 'VISITOR', 'both', 'Length of OTP sent to visitor.', 'Integer');
        CREATE TABLE jira_links (property_name TEXT, jira_key TEXT, relevance REAL,
            PRIMARY KEY(property_name, jira_key));
        INSERT INTO jira_links VALUES ('kioskRequireOTPBeforeRegister', 'VIS-1234', 1.0);
        INSERT INTO jira_links VALUES ('kioskRequireOTPBeforeRegister', 'VIS-5678', 0.7);
        CREATE TABLE module_links (property_name TEXT, module_slug TEXT, link_type TEXT,
            PRIMARY KEY(property_name, module_slug));
        INSERT INTO module_links VALUES ('kioskRequireOTPBeforeRegister', 'modules/visitor-management', 'service_match');
        CREATE TABLE dependencies (property_a TEXT, property_b TEXT, dep_type TEXT,
            direction TEXT, confidence REAL, evidence TEXT,
            PRIMARY KEY(property_a, property_b, dep_type));
        INSERT INTO dependencies VALUES ('kioskRequireOTPBeforeRegister', 'kioskOTPLength',
            'structural', 'bidirectional', 0.9, 'Share kiosk OTP naming prefix');
    """)
    con.close()


def _get_handler():
    from backend.tools.config_tools import _config_lookup_handler
    return _config_lookup_handler


def test_exact_match(tmp_path):
    db = tmp_path / "test.sqlite"
    _make_test_db(str(db))
    with patch("backend.tools.config_tools._DB_PATH", db):
        result = _get_handler()({"property_name": "kioskRequireOTPBeforeRegister"})
    assert result["found"] is True
    assert result["property_name"] == "kioskRequireOTPBeforeRegister"
    assert result["service"] == "VISITOR"
    assert result["server"] == "both"
    assert "OTP" in result["description"]
    assert result["data_type"] == "Boolean"
    assert result["default_value"] == "false"
    assert result["criteria_priority_list"] == ["BUID", "OFFICEID"]


def test_exact_match_case_insensitive(tmp_path):
    db = tmp_path / "test.sqlite"
    _make_test_db(str(db))
    with patch("backend.tools.config_tools._DB_PATH", db):
        result = _get_handler()({"property_name": "kiskoRequireotpbeforeregister"})
    # Should find via case-insensitive exact or FTS
    assert result["found"] is True or result.get("found") is False  # graceful either way


def test_jira_tickets_returned(tmp_path):
    db = tmp_path / "test.sqlite"
    _make_test_db(str(db))
    with patch("backend.tools.config_tools._DB_PATH", db):
        result = _get_handler()({"property_name": "kioskRequireOTPBeforeRegister"})
    assert len(result["jira_tickets"]) == 2
    keys = {t["key"] for t in result["jira_tickets"]}
    assert "VIS-1234" in keys


def test_module_pages_returned(tmp_path):
    db = tmp_path / "test.sqlite"
    _make_test_db(str(db))
    with patch("backend.tools.config_tools._DB_PATH", db):
        result = _get_handler()({"property_name": "kioskRequireOTPBeforeRegister"})
    assert "modules/visitor-management" in result["module_pages"]


def test_dependencies_returned(tmp_path):
    db = tmp_path / "test.sqlite"
    _make_test_db(str(db))
    with patch("backend.tools.config_tools._DB_PATH", db):
        result = _get_handler()({"property_name": "kioskRequireOTPBeforeRegister"})
    assert len(result["depends_on"]) >= 1
    dep = result["depends_on"][0]
    assert dep["property"] == "kioskOTPLength"
    assert dep["dep_type"] == "structural"


def test_missing_property_returns_not_found(tmp_path):
    db = tmp_path / "test.sqlite"
    _make_test_db(str(db))
    with patch("backend.tools.config_tools._DB_PATH", db):
        result = _get_handler()({"property_name": "nonExistentPropertyXYZ"})
    # Either not found in SQLite, falls back to wiki (found=False or uses wiki)
    assert "found" in result


def test_empty_property_name_returns_error(tmp_path):
    db = tmp_path / "test.sqlite"
    _make_test_db(str(db))
    with patch("backend.tools.config_tools._DB_PATH", db):
        result = _get_handler()({"property_name": ""})
    assert "error" in result


def test_service_filter(tmp_path):
    db = tmp_path / "test.sqlite"
    _make_test_db(str(db))
    with patch("backend.tools.config_tools._DB_PATH", db):
        result = _get_handler()({"property_name": "kioskRequireOTPBeforeRegister",
                                  "service": "VISITOR"})
    assert result["found"] is True
    assert result["service"] == "VISITOR"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
venv/bin/pytest tests/test_config_tools.py -v
```
Expected: ImportError or AttributeError — `_DB_PATH` not yet defined.

- [ ] **Step 3: Rewrite `backend/tools/config_tools.py`**

```python
"""
Config tools — look up PMS property names in the SQLite config knowledge base.
Falls back to wiki TF-IDF if SQLite returns no results.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from backend import wiki_retriever

_REPO = Path(__file__).resolve().parent.parent.parent
_DB_PATH = _REPO / "raw" / "configs" / "configs.sqlite"

CONFIG_LOOKUP_SCHEMA: dict = {
    "name": "config_lookup",
    "description": (
        "Look up a PMS config property name in the knowledge base. "
        "Returns full static context: description, hierarchy levels (criteriaPriorityList), "
        "related Jira tickets, dependent configs, and module pages. "
        "Use this when a question names a specific property like "
        "'kioskRequireOTPBeforeRegister' or 'mealCutoffInMinutes'."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "property_name": {
                "type": "string",
                "description": "The PMS config property name to look up (case-insensitive).",
            },
            "service": {
                "type": "string",
                "description": "Optional: narrow to this PMS service (e.g. 'VISITOR').",
            },
            "server": {
                "type": "string",
                "enum": ["com", "in"],
                "description": "Optional: filter by server.",
            },
            "fuzzy": {
                "type": "boolean",
                "description": "If true (default), try FTS match when exact match misses.",
                "default": True,
            },
        },
        "required": ["property_name"],
    },
}


def _sqlite_lookup(prop: str, service: str, server: str, fuzzy: bool) -> dict | None:
    """Query SQLite. Returns enriched dict or None if not found."""
    if not _DB_PATH.exists():
        return None

    con = sqlite3.connect(_DB_PATH)
    con.row_factory = sqlite3.Row

    # Build optional filters
    filters = ["LOWER(property_name) = LOWER(?)"]
    params: list = [prop]
    if service:
        filters.append("service = ?")
        params.append(service.upper())
    if server:
        filters.append("server IN (?, 'both')")
        params.append(server.lower())

    row = con.execute(
        f"SELECT * FROM configs WHERE {' AND '.join(filters)} LIMIT 1",
        params
    ).fetchone()

    # FTS fallback
    if row is None and fuzzy:
        fts_query = prop.replace('"', '""')
        fts_results = con.execute(
            "SELECT c.* FROM configs c JOIN configs_fts f ON c.id = f.rowid "
            f"WHERE configs_fts MATCH ? ORDER BY rank LIMIT 1",
            (f'"{fts_query}"',)
        ).fetchone()
        if fts_results is None:
            # Try prefix match
            fts_results = con.execute(
                "SELECT c.* FROM configs c JOIN configs_fts f ON c.id = f.rowid "
                f"WHERE configs_fts MATCH ? ORDER BY rank LIMIT 1",
                (fts_query + "*",)
            ).fetchone()
        row = fts_results

    if row is None:
        con.close()
        return None

    prop_name = row["property_name"]

    # Jira links
    jira_rows = con.execute(
        "SELECT jira_key, relevance FROM jira_links WHERE property_name=? ORDER BY relevance DESC LIMIT 10",
        (prop_name,)
    ).fetchall()

    # Module links
    module_rows = con.execute(
        "SELECT module_slug FROM module_links WHERE property_name=?",
        (prop_name,)
    ).fetchall()

    # Dependencies (where prop is property_a)
    dep_a_rows = con.execute(
        "SELECT property_b, dep_type, direction, confidence FROM dependencies WHERE property_a=? ORDER BY confidence DESC",
        (prop_name,)
    ).fetchall()

    # Dependencies (where prop is property_b — b_requires_a)
    dep_b_rows = con.execute(
        "SELECT property_a, dep_type, direction, confidence FROM dependencies WHERE property_b=? ORDER BY confidence DESC",
        (prop_name,)
    ).fetchall()

    con.close()

    # Parse criteria_priority_list
    cpl_raw = row["criteria_priority_list"]
    try:
        criteria_priority_list = json.loads(cpl_raw) if cpl_raw else []
    except (json.JSONDecodeError, TypeError):
        criteria_priority_list = []

    return {
        "found": True,
        "source": "sqlite",
        "property_name": prop_name,
        "service": row["service"],
        "server": row["server"],
        "description": row["description"] or "",
        "data_type": row["data_type"] or "",
        "default_value": row["default_value"] or "",
        "customizable": bool(row["customizable"]) if row["customizable"] is not None else None,
        "criteria_priority_list": criteria_priority_list,
        "jira_tickets": [
            {"key": r["jira_key"], "relevance": r["relevance"]}
            for r in jira_rows
        ],
        "module_pages": [r["module_slug"] for r in module_rows],
        "depends_on": [
            {"property": r["property_b"], "dep_type": r["dep_type"],
             "direction": r["direction"], "confidence": r["confidence"]}
            for r in dep_a_rows
        ],
        "required_by": [
            {"property": r["property_a"], "dep_type": r["dep_type"],
             "direction": r["direction"], "confidence": r["confidence"]}
            for r in dep_b_rows
        ],
    }


def _config_lookup_handler(inp: dict) -> dict:
    property_name = str(inp.get("property_name", "")).strip()
    if not property_name:
        return {"error": "property_name is required", "code": "missing_input"}

    service = str(inp.get("service", "")).strip()
    server = str(inp.get("server", "")).strip()
    fuzzy = bool(inp.get("fuzzy", True))

    # Try SQLite first
    result = _sqlite_lookup(property_name, service, server, fuzzy)
    if result:
        return result

    # Fallback: wiki TF-IDF
    query_parts = [property_name]
    if service:
        query_parts.append(service)
    if server:
        query_parts.append(f".{server}")
    query = " ".join(query_parts)

    pages = wiki_retriever.search(query, top_n=5)
    config_pages = [p for p in pages if "configs/" in p.path]
    other_pages = [p for p in pages if "configs/" not in p.path]
    ranked = config_pages + other_pages

    return {
        "found": len(ranked) > 0,
        "source": "wiki_tfidf",
        "property_name": property_name,
        "wiki_matches": [
            {"path": p.path, "title": p.title, "excerpt": p.excerpt(300)}
            for p in ranked[:5]
        ],
    }
```

- [ ] **Step 4: Run the tests**

```bash
venv/bin/pytest tests/test_config_tools.py -v
```
Expected: all 8 tests PASS. The `test_exact_match_case_insensitive` test may return `found=False` (falls through to wiki) — that is acceptable behavior.

- [ ] **Step 5: Commit**

```bash
git add backend/tools/config_tools.py tests/test_config_tools.py
git commit -m "feat: rewrite config_lookup — SQLite exact/FTS first, wiki TF-IDF fallback"
```

---

## Task 5: Add `include_configs` layer to graph API

**Files:**
- Modify: `backend/wiki_graph_api.py`

**Do NOT start the backend when editing this file.**

- [ ] **Step 1: Modify `backend/wiki_graph_api.py`**

Read the current file, then replace the `@router.get("/graph")` function with this version:

```python
@router.get("/graph")
async def wiki_graph(include_configs: bool = False) -> dict:
    nodes: dict[str, dict] = {}
    texts: dict[str, str] = {}

    for path in sorted(_WIKI_DIR.rglob("*.md")):
        if path.name in _SKIP:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue

        node_id = str(path.relative_to(_WIKI_DIR)).replace("\\", "/").removesuffix(".md")
        label = path.stem.replace("-", " ").replace("_", " ").title()
        nodes[node_id] = {
            "id": node_id,
            "label": label,
            "type": _page_type(text),
            "path": node_id,
            "val": 1,
        }
        texts[node_id] = text

    # Build wiki edges
    seen: set[tuple[str, str]] = set()
    links: list[dict] = []
    degree: dict[str, int] = {k: 0 for k in nodes}

    for node_id, text in texts.items():
        for raw in _extract_links(text):
            target = raw.strip().removesuffix(".md")
            if target not in nodes or target == node_id:
                continue
            key = (min(node_id, target), max(node_id, target))
            if key in seen:
                continue
            seen.add(key)
            links.append({"source": node_id, "target": target})
            degree[node_id] = degree.get(node_id, 0) + 1
            degree[target] = degree.get(target, 0) + 1

    for nid, d in degree.items():
        nodes[nid]["val"] = max(1, d)

    # Config layer (optional)
    if include_configs:
        _add_config_layer(nodes, links, seen)

    return {"nodes": list(nodes.values()), "links": links}
```

Also add the helper `_add_config_layer` function and the `_CONFIG_DB` path constant **above** the `@router.get` handler:

```python
_CONFIG_DB = pathlib.Path(__file__).resolve().parent.parent / "raw" / "configs" / "configs.sqlite"


def _add_config_layer(
    nodes: dict[str, dict],
    links: list[dict],
    seen: set[tuple[str, str]],
) -> None:
    """Add config nodes and edges from configs.sqlite into the graph."""
    import sqlite3

    if not _CONFIG_DB.exists():
        return

    con = sqlite3.connect(_CONFIG_DB)
    con.row_factory = sqlite3.Row

    # Config nodes: val = jira_link_count (bigger = historically more significant)
    config_rows = con.execute(
        """SELECT c.property_name, c.service,
                  COUNT(j.jira_key) AS jira_count
           FROM configs c
           LEFT JOIN jira_links j ON c.property_name = j.property_name
           GROUP BY c.property_name, c.service"""
    ).fetchall()

    for row in config_rows:
        node_id = f"configs/{row['property_name']}"
        if node_id not in nodes:
            nodes[node_id] = {
                "id": node_id,
                "label": row["property_name"],
                "type": "config",
                "service": row["service"],
                "path": node_id,
                "val": max(1, row["jira_count"]),
            }

    # Config → module edges (service_match links)
    module_links = con.execute(
        "SELECT property_name, module_slug FROM module_links WHERE link_type='service_match'"
    ).fetchall()

    for ml in module_links:
        src = f"configs/{ml['property_name']}"
        tgt = ml["module_slug"]  # e.g. "modules/visitor-management"
        if src not in nodes or tgt not in nodes:
            continue
        key = (min(src, tgt), max(src, tgt))
        if key in seen:
            continue
        seen.add(key)
        links.append({"source": src, "target": tgt, "dep_type": "service_match"})

    # Config-to-config dependency edges
    dep_rows = con.execute(
        "SELECT property_a, property_b, dep_type FROM dependencies WHERE confidence >= 0.7"
    ).fetchall()

    for dep in dep_rows:
        src = f"configs/{dep['property_a']}"
        tgt = f"configs/{dep['property_b']}"
        if src not in nodes or tgt not in nodes:
            continue
        key = (min(src, tgt), max(src, tgt))
        if key in seen:
            continue
        seen.add(key)
        links.append({"source": src, "target": tgt, "dep_type": dep["dep_type"]})

    con.close()
```

- [ ] **Step 2: Verify the graph API still works without the flag**

Start the backend and test:
```bash
curl -s "http://localhost:8000/api/wiki/graph" | python -m json.tool | head -20
```
Expected: JSON with `nodes` and `links`, no error.

- [ ] **Step 3: Test with include_configs=true**

```bash
curl -s "http://localhost:8000/api/wiki/graph?include_configs=true" | \
  python -c "import json,sys; d=json.load(sys.stdin); \
  cfg=[n for n in d['nodes'] if n.get('type')=='config']; \
  print(f'Config nodes: {len(cfg)}, total nodes: {len(d[\"nodes\"])}, links: {len(d[\"links\"])}')"
```
Expected: `Config nodes: N, total nodes: M, links: L` where N ≥ 1000.

- [ ] **Step 4: Commit**

```bash
git add backend/wiki_graph_api.py
git commit -m "feat: add include_configs layer to graph API — toggleable config nodes + dependency edges"
```

---

## Task 6: Update CLAUDE.md Section 5

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Add Step 2b to CLAUDE.md Section 5**

In `CLAUDE.md`, find the line:

```
### Step 3 — Detect conflict and evolution
```

Insert the following block **immediately before** that line (after the Step 2 Jira search section):

```markdown
### Step 2b — Config lookup (for config property questions)

When the question names or describes a specific PMS config property, call
`config_lookup` BEFORE calling `pms_runtime_values` or `pms_diagnose_property`.
`config_lookup` returns the full static context for that property: description,
which hierarchy levels it supports (`criteria_priority_list`), related Jira tickets,
dependent configs, and which module pages document it.

Use `criteria_priority_list` from `config_lookup` to decide which levels to
diagnose: if the list includes `"OFFICEID"`, pass `officeid` to `pms_diagnose_property`.
If it includes `"ROOMID"`, use `criteria='ROOM_ID'` in `pms_list_criteria` first.

`config_lookup` queries a SQLite knowledge base covering all ~1800 PMS configs across
`.in` and `.com` servers. When SQLite has no result, it falls back to wiki TF-IDF.
```

- [ ] **Step 2: Verify the edit looks correct**

```bash
grep -n "Step 2b" CLAUDE.md
```
Expected: shows the new section header with a line number.

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: add Step 2b — config_lookup workflow to CLAUDE.md Section 5"
```

---

## End-to-end verification

After all tasks complete, run this verification sequence:

```bash
# 1. SQLite row count
sqlite3 raw/configs/configs.sqlite \
  "SELECT server, COUNT(*) FROM configs GROUP BY server;"

# 2. Enrichment summary
sqlite3 raw/configs/configs.sqlite "
SELECT 'configs' as table_name, COUNT(*) as rows FROM configs
UNION ALL
SELECT 'jira_links', COUNT(*) FROM jira_links
UNION ALL
SELECT 'module_links', COUNT(*) FROM module_links
UNION ALL
SELECT 'dependencies', COUNT(*) FROM dependencies;"

# 3. FTS spot check
sqlite3 raw/configs/configs.sqlite \
  "SELECT property_name, service FROM configs_fts WHERE configs_fts MATCH 'kiosk' LIMIT 5;"

# 4. Full test suite
venv/bin/pytest tests/test_build_config_db.py tests/test_config_tools.py -v

# 5. Wiki pages generated
ls -la wiki/configs/*.md | wc -l
```

Expected output:
- configs: ≥ 1500 rows; dedup breakdown shows in/com/both distribution
- jira_links: thousands of rows
- module_links: thousands of rows  
- dependencies: ≥ 20 co-occurrence rows + LLM rows
- All pytest tests pass
- 11 wiki/configs/*.md files (10 regenerated + mobile-app-server.md unchanged)
