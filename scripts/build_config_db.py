#!/usr/bin/env python3
"""
build_config_db.py — Ingest all PMS configs from raw Excel + CSV sources into
a SQLite FTS5 database, and regenerate wiki/configs/<slug>.md pages.

Outputs:
  raw/configs/configs.sqlite   — SQLite with FTS5 virtual table
  wiki/configs/<slug>.md       — 10 regenerated config wiki pages

Sources:
  .in  raw/modules/pms-configs-in/All WIS CONFIGS.xlsx
  .com raw/modules/pms-configs-com/wis_service_configs/*.csv
  fallback descriptions: raw/modules/pms-configs-in/wis_unique_configs.xlsx

Deduplication rule:
  Same (property_name, service) found in both servers → server='both'
  Description/data_type from .com wins; falls back to .in if .com is empty.

Usage:
  python scripts/build_config_db.py [--reset]
  --reset  Drop and recreate all tables from scratch (idempotent).
           Without --reset, upserts existing data.
"""
from __future__ import annotations

import argparse
import sqlite3
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import NamedTuple

import pandas as pd

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent
RAW_IN_XLSX = ROOT / "raw" / "modules" / "pms-configs-in" / "All WIS CONFIGS.xlsx"
RAW_COM_CSV_DIR = ROOT / "raw" / "modules" / "pms-configs-com" / "wis_service_configs"
RAW_UNIQUE_XLSX = ROOT / "raw" / "modules" / "pms-configs-in" / "wis_unique_configs.xlsx"
DB_PATH = ROOT / "raw" / "configs" / "configs.sqlite"
WIKI_CONFIGS = ROOT / "wiki" / "configs"

TODAY = date.today().isoformat()

# ---------------------------------------------------------------------------
# Service mappings
# ---------------------------------------------------------------------------

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
    "1. PMS":                      ("PROJECT-MANAGEMENT-SERVICE", "pms",                    "PMS"),
    "2. VMS":                      ("VISITOR",                    "visitor-management",      "VMS"),
    "3. Meeting Rooms":            ("MEETING_ROOMS",              "meeting-rooms",           "Meeting Rooms"),
    "4. Booking Rule Engine":      ("BOOKING-RULE-ENGINE",        "booking-rule-engine",     "Booking Rule Engine"),
    "5. WIS Seat Booking":         ("WIS-SEAT-BOOKING",           "wis-seat-booking",        "WIS Seat Booking"),
    "6. Guard App":                ("GUARD-APP",                  "guard-app",               "Guard App"),
    "7. Email Emp Experience":     ("EMAIL-EMP-EXPERIENCE",       "emp-experience-email",    "Email Employee Experience"),
    "8. Emp Exp Internal Config":  ("EMP-EXP-INTERNAL-CONFIG",   "emp-experience-internal", "Emp Exp Internal Config"),
    "9. Emp Exp Common Config":    ("EMP-EXP-COMMON-CONFIG",     "emp-experience-common",   "Emp Exp Common Config"),
    "10. App Server Config":       ("APP_SERVER_CONFIG",          "app-server-config",       "App Server Config"),
    "11. App Server Config (.in)": ("APP_SERVER_CONFIG",          "app-server-config",       "App Server Config"),
}

# All services ordered for consistent output
# Map service_id -> (slug, label)
SERVICE_META: dict[str, tuple[str, str]] = {}
for _svc_id, _slug, _label in SHEET_TO_SERVICE.values():
    SERVICE_META[_svc_id] = (_slug, _label)

# Ordered list of service IDs for wiki generation (preserves logical ordering)
SERVICE_ORDER = [
    "PROJECT-MANAGEMENT-SERVICE",
    "VISITOR",
    "MEETING_ROOMS",
    "BOOKING-RULE-ENGINE",
    "WIS-SEAT-BOOKING",
    "GUARD-APP",
    "EMAIL-EMP-EXPERIENCE",
    "EMP-EXP-INTERNAL-CONFIG",
    "EMP-EXP-COMMON-CONFIG",
    "APP_SERVER_CONFIG",
]

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

class ConfigRow(NamedTuple):
    property_name: str
    service: str
    server: str          # 'in', 'com', 'both'
    description: str
    data_type: str
    default_value: str
    customizable: int | None
    criteria_priority_list: str
    category: str


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

DDL_CONFIGS = """
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
"""

DDL_JIRA_LINKS = """
CREATE TABLE IF NOT EXISTS jira_links (
    property_name TEXT NOT NULL,
    jira_key      TEXT NOT NULL,
    relevance     REAL NOT NULL,
    PRIMARY KEY (property_name, jira_key)
);
"""

DDL_MODULE_LINKS = """
CREATE TABLE IF NOT EXISTS module_links (
    property_name TEXT NOT NULL,
    module_slug   TEXT NOT NULL,
    link_type     TEXT NOT NULL,
    PRIMARY KEY (property_name, module_slug)
);
"""

DDL_DEPENDENCIES = """
CREATE TABLE IF NOT EXISTS dependencies (
    property_a TEXT NOT NULL,
    property_b TEXT NOT NULL,
    dep_type   TEXT NOT NULL CHECK(dep_type IN ('functional','co_occurrence','structural')),
    direction  TEXT NOT NULL CHECK(direction IN ('a_requires_b','b_requires_a','bidirectional','correlated')),
    confidence REAL NOT NULL,
    evidence   TEXT,
    PRIMARY KEY (property_a, property_b, dep_type)
);
"""

DDL_FTS = """
CREATE VIRTUAL TABLE IF NOT EXISTS configs_fts
    USING fts5(property_name, description, category,
               content=configs, content_rowid=id);
"""

TRIGGER_INSERT = """
CREATE TRIGGER IF NOT EXISTS configs_ai
AFTER INSERT ON configs BEGIN
    INSERT INTO configs_fts(rowid, property_name, description, category)
    VALUES (new.id, new.property_name, new.description, new.category);
END;
"""

TRIGGER_DELETE = """
CREATE TRIGGER IF NOT EXISTS configs_ad
AFTER DELETE ON configs BEGIN
    INSERT INTO configs_fts(configs_fts, rowid, property_name, description, category)
    VALUES ('delete', old.id, old.property_name, old.description, old.category);
END;
"""

TRIGGER_UPDATE = """
CREATE TRIGGER IF NOT EXISTS configs_au
AFTER UPDATE ON configs BEGIN
    INSERT INTO configs_fts(configs_fts, rowid, property_name, description, category)
    VALUES ('delete', old.id, old.property_name, old.description, old.category);
    INSERT INTO configs_fts(rowid, property_name, description, category)
    VALUES (new.id, new.property_name, new.description, new.category);
END;
"""

DROP_TABLES = [
    "DROP TABLE IF EXISTS dependencies;",
    "DROP TABLE IF EXISTS module_links;",
    "DROP TABLE IF EXISTS jira_links;",
    "DROP TRIGGER IF EXISTS configs_au;",
    "DROP TRIGGER IF EXISTS configs_ad;",
    "DROP TRIGGER IF EXISTS configs_ai;",
    "DROP TABLE IF EXISTS configs_fts;",
    "DROP TABLE IF EXISTS configs;",
]


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def _clean(val) -> str:
    """Convert a pandas value to a clean string (empty string for NaN/None)."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return ""
    return str(val).strip()


def load_in_configs() -> dict[str, dict[str, dict]]:
    """
    Parse All WIS CONFIGS.xlsx (.in server).
    Returns: {service_id: {property_name: {"description": str, "data_type": str}}}
    """
    xl = pd.ExcelFile(RAW_IN_XLSX)
    result: dict[str, dict[str, dict]] = defaultdict(dict)

    for sheet_name, (service_id, _slug, _label) in SHEET_TO_SERVICE.items():
        df = xl.parse(sheet_name, header=None)

        if sheet_name == "APP_SERVER_CONFIGS":
            # Row 0 = header (Property Name, Data Type, Description), row 1+ = data
            data = df.iloc[1:].copy()
            data.columns = range(data.shape[1])
            prop_col, dtype_col, desc_col = 0, 1, 2
        else:
            # Rows 0-2 = service header/total/blank, row 3 = column headers, row 4+ = data
            data = df.iloc[4:].copy()
            data.columns = range(data.shape[1])
            prop_col, dtype_col, desc_col = 0, None, 1

        for _, row in data.iterrows():
            prop = _clean(row[prop_col])
            if not prop:
                continue
            desc = _clean(row[desc_col])
            dtype = _clean(row[dtype_col]) if dtype_col is not None else ""
            result[service_id][prop] = {"description": desc, "data_type": dtype}

    return result


def load_com_configs() -> dict[str, dict[str, dict]]:
    """
    Parse .csv files from wis_service_configs/ (.com server).
    Returns: {service_id: {property_name: {"description": str, "data_type": str}}}
    """
    result: dict[str, dict[str, dict]] = defaultdict(dict)

    for csv_prefix, (service_id, _slug, _label) in CSV_PREFIX_TO_SERVICE.items():
        csv_path = RAW_COM_CSV_DIR / f"{csv_prefix}.csv"
        if not csv_path.exists():
            print(f"  WARNING: CSV not found: {csv_path}")
            continue
        df = pd.read_csv(csv_path)
        for _, row in df.iterrows():
            prop = _clean(row.get("Property Name", ""))
            if not prop:
                continue
            desc = _clean(row.get("Description", ""))
            dtype = _clean(row.get("Data Type", ""))
            # For a given service, last value wins if a property appears in multiple
            # CSVs that map to the same service (e.g. CSV 10 + CSV 11 -> APP_SERVER_CONFIG)
            # Non-empty values take priority over empty
            existing = result[service_id].get(prop)
            if existing is None:
                result[service_id][prop] = {"description": desc, "data_type": dtype}
            else:
                if not existing["description"] and desc:
                    existing["description"] = desc
                if not existing["data_type"] and dtype:
                    existing["data_type"] = dtype

    return result


def load_unique_config_descriptions() -> dict[str, str]:
    """
    Parse wis_unique_configs.xlsx for description fallback.
    Returns: {property_name: description}
    Rows 0-2 = title/summary/blank, row 3 = header, row 4+ = data.
    """
    df = pd.read_excel(RAW_UNIQUE_XLSX, header=None)
    data = df.iloc[4:].copy()
    data.columns = range(data.shape[1])
    # Columns: 0=Property Name, 1=Description, 2=Service(s), 3=Service Count
    result: dict[str, str] = {}
    for _, row in data.iterrows():
        prop = _clean(row[0])
        desc = _clean(row[1]) if data.shape[1] > 1 else ""
        if prop:
            result[prop] = desc
    return result


# ---------------------------------------------------------------------------
# Merge / deduplication
# ---------------------------------------------------------------------------

def merge_configs(
    in_data: dict[str, dict[str, dict]],
    com_data: dict[str, dict[str, dict]],
    unique_descs: dict[str, str],
) -> list[ConfigRow]:
    """
    Merge .in and .com data per service into a deduplicated list.
    Dedup rule:
      - (property_name, service) in both → server='both', .com description wins
      - Only in .in → server='in'
      - Only in .com → server='com'
    """
    rows: list[ConfigRow] = []
    all_services = set(in_data.keys()) | set(com_data.keys())

    for service_id in all_services:
        in_props = in_data.get(service_id, {})
        com_props = com_data.get(service_id, {})
        all_props = set(in_props.keys()) | set(com_props.keys())

        for prop in all_props:
            in_entry = in_props.get(prop)
            com_entry = com_props.get(prop)

            if in_entry and com_entry:
                server = "both"
                # .com description wins; fall back to .in if .com is empty
                desc = com_entry["description"] or in_entry["description"]
                dtype = com_entry["data_type"] or in_entry["data_type"]
            elif com_entry:
                server = "com"
                desc = com_entry["description"]
                dtype = com_entry["data_type"]
            else:
                server = "in"
                desc = in_entry["description"]  # type: ignore[index]
                dtype = in_entry["data_type"]  # type: ignore[index]

            # If description still empty, fall back to wis_unique_configs
            if not desc:
                desc = unique_descs.get(prop, "")

            rows.append(ConfigRow(
                property_name=prop,
                service=service_id,
                server=server,
                description=desc,
                data_type=dtype,
                default_value="",
                customizable=None,
                criteria_priority_list="",
                category="",
            ))

    return rows


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

def create_schema(con: sqlite3.Connection) -> None:
    """Create all tables, FTS virtual table, and triggers."""
    con.execute(DDL_CONFIGS)
    con.execute(DDL_JIRA_LINKS)
    con.execute(DDL_MODULE_LINKS)
    con.execute(DDL_DEPENDENCIES)
    con.execute(DDL_FTS)
    con.execute(TRIGGER_INSERT)
    con.execute(TRIGGER_DELETE)
    con.execute(TRIGGER_UPDATE)
    con.commit()


def drop_schema(con: sqlite3.Connection) -> None:
    """Drop all tables (for --reset mode)."""
    for stmt in DROP_TABLES:
        con.execute(stmt)
    con.commit()


def upsert_rows(con: sqlite3.Connection, rows: list[ConfigRow]) -> int:
    """Insert or replace config rows. Returns count of rows written."""
    sql = """
    INSERT OR REPLACE INTO configs
        (property_name, service, server, description, data_type,
         default_value, customizable, criteria_priority_list, category)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    params = [
        (
            r.property_name, r.service, r.server,
            r.description or None,
            r.data_type or None,
            r.default_value or None,
            r.customizable,
            r.criteria_priority_list or None,
            r.category or None,
        )
        for r in rows
    ]
    con.executemany(sql, params)
    con.commit()
    return len(params)


def rebuild_fts(con: sqlite3.Connection) -> None:
    """Rebuild FTS index from scratch (safe after bulk insert with triggers)."""
    con.execute("INSERT INTO configs_fts(configs_fts) VALUES('rebuild')")
    con.commit()


# ---------------------------------------------------------------------------
# Wiki page generation
# ---------------------------------------------------------------------------

def _escape_pipe(text: str) -> str:
    """Escape pipe characters for markdown tables."""
    return text.replace("|", "\\|")


def _truncate(text: str, maxlen: int = 200) -> str:
    """Truncate text to maxlen characters, appending '...' if truncated."""
    if len(text) <= maxlen:
        return text
    return text[:maxlen - 3] + "..."


def _server_label(server: str) -> str:
    if server == "both":
        return "both"
    if server == "in":
        return ".in only"
    return ".com only"


def _servers_frontmatter(service_rows: list[ConfigRow]) -> str:
    servers = {r.server for r in service_rows}
    parts = []
    if "in" in servers or "both" in servers:
        parts.append("in")
    if "com" in servers or "both" in servers:
        parts.append("com")
    return "[" + ", ".join(parts) + "]"


def generate_wiki_page(service_id: str, service_rows: list[ConfigRow]) -> str:
    """Generate a wiki markdown page for one service."""
    slug, label = SERVICE_META[service_id]

    # Sort rows alphabetically (case-insensitive) by property name
    sorted_rows = sorted(service_rows, key=lambda r: r.property_name.lower())

    servers_fm = _servers_frontmatter(service_rows)
    total = len(sorted_rows)

    # Determine module field (best-effort mapping)
    module_map = {
        "PROJECT-MANAGEMENT-SERVICE": "none",
        "VISITOR":                    "visitor-management",
        "MEETING_ROOMS":              "meeting-rooms",
        "BOOKING-RULE-ENGINE":        "booking-rule-engine",
        "WIS-SEAT-BOOKING":           "wis-seat-booking",
        "GUARD-APP":                  "guard-app-kiosks",
        "EMAIL-EMP-EXPERIENCE":       "employee-experience",
        "EMP-EXP-INTERNAL-CONFIG":    "employee-experience",
        "EMP-EXP-COMMON-CONFIG":      "employee-experience",
        "APP_SERVER_CONFIG":          "none",
    }
    module = module_map.get(service_id, "none")

    lines: list[str] = []

    # YAML frontmatter
    lines.append("---")
    lines.append(f"title: \"{label} — Config Properties\"")
    lines.append(f"service: {service_id}")
    lines.append(f"total_configs: {total}")
    lines.append(f"servers: {servers_fm}")
    lines.append(f"generated: {TODAY}")
    lines.append("type: config")
    lines.append(f"module: {module}")
    lines.append("---")
    lines.append("")

    # Intro
    lines.append(f"# {label} — Config Properties")
    lines.append("")
    lines.append(
        f"Auto-generated on {TODAY}. Total configs: **{total}**."
    )
    lines.append("")

    # Table header
    lines.append("| Property | Description | Type | Default | Server |")
    lines.append("|----------|-------------|------|---------|--------|")

    # Table rows
    for row in sorted_rows:
        prop = f"`{row.property_name}`"
        desc = _escape_pipe(_truncate(row.description or ""))
        dtype = _escape_pipe(row.data_type or "")
        default = _escape_pipe(row.default_value or "")
        server = _server_label(row.server)
        lines.append(f"| {prop} | {desc} | {dtype} | {default} | {server} |")

    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Build PMS configs SQLite DB and wiki pages")
    parser.add_argument("--reset", action="store_true", help="Drop and recreate all tables")
    args = parser.parse_args()

    # Ensure output directories exist
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    WIKI_CONFIGS.mkdir(parents=True, exist_ok=True)

    print("Loading source data...")
    print("  Parsing .in Excel...")
    in_data = load_in_configs()
    print("  Parsing .com CSVs...")
    com_data = load_com_configs()
    print("  Loading unique config descriptions (fallback)...")
    unique_descs = load_unique_config_descriptions()

    print("Merging and deduplicating...")
    rows = merge_configs(in_data, com_data, unique_descs)
    print(f"  Total merged rows: {len(rows)}")
    both_count = sum(1 for r in rows if r.server == "both")
    in_only_count = sum(1 for r in rows if r.server == "in")
    com_only_count = sum(1 for r in rows if r.server == "com")
    print(f"  server='both': {both_count}  server='in': {in_only_count}  server='com': {com_only_count}")

    print(f"Writing SQLite to {DB_PATH} ...")
    con = sqlite3.connect(DB_PATH)
    try:
        if args.reset:
            print("  --reset: dropping existing tables...")
            drop_schema(con)
        create_schema(con)
        written = upsert_rows(con, rows)
        print(f"  Wrote {written} rows")
        # Rebuild FTS to ensure index is consistent after bulk insert
        rebuild_fts(con)
        print("  FTS index rebuilt")
        final_count = con.execute("SELECT COUNT(*) FROM configs").fetchone()[0]
        print(f"  Final configs table count: {final_count}")
    finally:
        con.close()

    print(f"\nGenerating wiki pages in {WIKI_CONFIGS} ...")
    # Group rows by service
    by_service: dict[str, list[ConfigRow]] = defaultdict(list)
    for r in rows:
        by_service[r.service].append(r)

    for service_id in SERVICE_ORDER:
        slug, label = SERVICE_META[service_id]
        service_rows = by_service.get(service_id, [])
        page_content = generate_wiki_page(service_id, service_rows)
        page_path = WIKI_CONFIGS / f"{slug}.md"
        page_path.write_text(page_content, encoding="utf-8")
        print(f"  Wrote {page_path.name} ({len(service_rows)} configs)")

    print("\nDone.")


if __name__ == "__main__":
    main()
