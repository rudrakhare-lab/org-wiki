#!/usr/bin/env python3
"""
enrich_config_db.py — Enrich configs.sqlite with Jira cross-references and module links.

Steps:
  A  Jira cross-references — for each property_name (len >= 8), LIKE-search Jira tickets
     and insert top-10 relevance-ranked matches into jira_links.
  B  Module links — service-to-module slug mapping (service_match) plus wiki mention scan
     (wiki_mention), inserted into module_links.
  C  (reserved — not yet implemented, added in Task 3)

Usage:
  python scripts/enrich_config_db.py --step a
  python scripts/enrich_config_db.py --step b
  python scripts/enrich_config_db.py --all       # runs a then b

Idempotency:
  Step A: DELETE + INSERT per property (stable top-10); safe to re-run.
  Step B: INSERT OR REPLACE (service_match) / INSERT OR IGNORE (wiki_mention); safe to re-run.
"""
from __future__ import annotations

import argparse
import sqlite3
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths — no hardcoded paths
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent
CONFIGS_DB = ROOT / "raw" / "configs" / "configs.sqlite"
JIRA_DB = ROOT / "raw" / "jira" / "tickets.sqlite"
WIKI_DIR = ROOT / "wiki"

# ---------------------------------------------------------------------------
# Service → module slug mapping (Step B Part 1)
# ---------------------------------------------------------------------------

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

BATCH_SIZE = 50  # properties per transaction in Step A


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _escape_like(s: str) -> str:
    """Escape backslash, then %, then _ for SQLite LIKE with ESCAPE '\\'."""
    return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


# ---------------------------------------------------------------------------
# Step A — Jira cross-references
# ---------------------------------------------------------------------------

def step_a(configs_conn: sqlite3.Connection) -> None:
    """Cross-reference each property (len>=8) against Jira tickets."""
    print("=== Step A: Jira cross-references ===")
    t0 = time.time()

    # Attach Jira DB as read-only via URI
    jira_uri = JIRA_DB.as_uri() + "?mode=ro"
    configs_conn.execute(f"ATTACH DATABASE '{jira_uri}' AS jira")

    # Fetch qualifying properties (distinct names only — service doesn't affect search)
    rows = configs_conn.execute(
        "SELECT DISTINCT property_name FROM configs WHERE length(property_name) >= 8"
    ).fetchall()
    properties = [r[0] for r in rows]
    total = len(properties)
    print(f"  {total} distinct properties with len>=8")

    # Single combined query: one scan per property, highest relevance wins via CASE ORDER
    # key is PK in tickets so each row is unique — ORDER BY relevance DESC, key is deterministic
    jira_sql = """
        SELECT key,
            CASE
                WHEN summary LIKE :p ESCAPE '\\'          THEN 1.0
                WHEN description_text LIKE :p ESCAPE '\\' THEN 0.7
                ELSE 0.5
            END AS relevance
        FROM jira.tickets
        WHERE summary        LIKE :p ESCAPE '\\'
           OR description_text LIKE :p ESCAPE '\\'
           OR comments_text    LIKE :p ESCAPE '\\'
        ORDER BY relevance DESC, key
        LIMIT 10
    """

    inserted_total = 0
    batch_start = time.time()

    for idx, prop in enumerate(properties, 1):
        pattern = f"%{_escape_like(prop)}%"

        if idx % BATCH_SIZE == 1:
            configs_conn.execute("BEGIN")

        # Delete existing links for this property (ensures clean top-10 on re-run)
        configs_conn.execute(
            "DELETE FROM jira_links WHERE property_name = ?", (prop,)
        )

        matches = configs_conn.execute(jira_sql, {"p": pattern}).fetchall()
        if matches:
            configs_conn.executemany(
                "INSERT OR REPLACE INTO jira_links (property_name, jira_key, relevance) "
                "VALUES (?, ?, ?)",
                [(prop, key, rel) for key, rel in matches],
            )
            inserted_total += len(matches)

        if idx % BATCH_SIZE == 0 or idx == total:
            configs_conn.execute("COMMIT")
            elapsed = time.time() - batch_start
            print(
                f"  [{idx}/{total}] batch committed — "
                f"{elapsed:.1f}s so far — {inserted_total} links"
            )
            batch_start = time.time()

    configs_conn.execute("DETACH DATABASE jira")
    total_time = time.time() - t0
    print(f"  Step A done: {inserted_total} jira_links in {total_time:.1f}s")


# ---------------------------------------------------------------------------
# Step B — Module links
# ---------------------------------------------------------------------------

def step_b(configs_conn: sqlite3.Connection) -> None:
    """Populate module_links via service mapping and wiki mention scan."""
    print("=== Step B: Module links ===")

    _step_b_service_match(configs_conn)
    _step_b_wiki_mentions(configs_conn)

    service_count = configs_conn.execute(
        "SELECT COUNT(*) FROM module_links WHERE link_type='service_match'"
    ).fetchone()[0]
    wiki_count = configs_conn.execute(
        "SELECT COUNT(*) FROM module_links WHERE link_type='wiki_mention'"
    ).fetchone()[0]
    print(f"  Step B done: {service_count} service_match, {wiki_count} wiki_mention rows")


def _step_b_service_match(configs_conn: sqlite3.Connection) -> None:
    """Part 1 — map (property_name, service) → module_slug via SERVICE_TO_MODULE_SLUG."""
    print("  Part 1: service_match ...")
    rows = configs_conn.execute(
        "SELECT DISTINCT property_name, service FROM configs"
    ).fetchall()

    inserted = 0
    configs_conn.execute("BEGIN")
    for prop, service in rows:
        slug = SERVICE_TO_MODULE_SLUG.get(service)
        if slug:
            configs_conn.execute(
                "INSERT OR REPLACE INTO module_links (property_name, module_slug, link_type) "
                "VALUES (?, ?, 'service_match')",
                (prop, slug),
            )
            inserted += 1
    configs_conn.execute("COMMIT")
    print(f"    {inserted} service_match rows inserted/replaced")


def _step_b_wiki_mentions(configs_conn: sqlite3.Connection) -> None:
    """Part 2 — scan wiki/**/*.md for exact property_name occurrences."""
    print("  Part 2: wiki_mention ...")

    # Fetch qualifying property names (len >= 6)
    rows = configs_conn.execute(
        "SELECT DISTINCT property_name FROM configs WHERE length(property_name) >= 6"
    ).fetchall()
    properties = [r[0] for r in rows]

    # Collect all wiki .md files (recursive)
    md_files = list(WIKI_DIR.rglob("*.md"))
    print(f"    Scanning {len(md_files)} wiki files for {len(properties)} properties ...")

    # Build a map: property_name → set of module_slugs found
    # We scan each file once and check all properties against its content
    mentions: dict[str, set[str]] = {}

    prop_set = set(properties)  # for O(1) lookup after str.find

    for md_path in md_files:
        try:
            content = md_path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        # slug = relative path from wiki/ dir, no extension
        slug = md_path.relative_to(WIKI_DIR).with_suffix("").as_posix()

        for prop in prop_set:
            if prop in content:
                mentions.setdefault(prop, set()).add(slug)

    # Insert findings
    inserted = 0
    configs_conn.execute("BEGIN")
    for prop, slugs in mentions.items():
        for slug in slugs:
            configs_conn.execute(
                "INSERT OR IGNORE INTO module_links (property_name, module_slug, link_type) "
                "VALUES (?, ?, 'wiki_mention')",
                (prop, slug, ),
            )
            inserted += 1
    configs_conn.execute("COMMIT")
    print(f"    {inserted} wiki_mention rows inserted")


# ---------------------------------------------------------------------------
# Step C placeholder (Task 3)
# ---------------------------------------------------------------------------

def step_c(configs_conn: sqlite3.Connection) -> None:
    """Step C — co-occurrence + LLM dependency inference. Not yet implemented."""
    print("Step C not yet implemented — will be added in Task 3.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Enrich configs.sqlite with Jira links and module links."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--step", choices=["a", "b", "c"], help="Run a single step")
    group.add_argument("--all", action="store_true", help="Run steps a then b")
    args = parser.parse_args()

    conn = sqlite3.connect(CONFIGS_DB)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")

    try:
        if args.all:
            step_a(conn)
            step_b(conn)
        elif args.step == "a":
            step_a(conn)
        elif args.step == "b":
            step_b(conn)
        elif args.step == "c":
            step_c(conn)
    finally:
        conn.close()

    print("Done.")


if __name__ == "__main__":
    main()
