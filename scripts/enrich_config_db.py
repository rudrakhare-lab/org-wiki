#!/usr/bin/env python3
"""
enrich_config_db.py — Enrich configs.sqlite with Jira cross-references and module links.

Steps:
  A  Jira cross-references — for each property_name (len >= 8), LIKE-search Jira tickets
     and insert top-10 relevance-ranked matches into jira_links.
  B  Module links — service-to-module slug mapping (service_match) plus wiki mention scan
     (wiki_mention), inserted into module_links.
  C  Co-occurrence detection (no LLM) + LLM dependency inference (requires ANTHROPIC_API_KEY).
     Inserts into dependencies table.

Usage:
  python scripts/enrich_config_db.py --step a
  python scripts/enrich_config_db.py --step b
  python scripts/enrich_config_db.py --step c
  python scripts/enrich_config_db.py --all       # runs a then b then c

Idempotency:
  Step A: DELETE + INSERT per property (stable top-10); safe to re-run.
  Step B: INSERT OR REPLACE (service_match) / INSERT OR IGNORE (wiki_mention); safe to re-run.
  Step C: INSERT OR REPLACE (co_occurrence) / INSERT OR IGNORE (functional/structural); safe to re-run.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from itertools import combinations
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths — no hardcoded paths
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent
# Repo root on path so we can import backend.db (DSN + Row factory + migrations).
# Importing backend also loads .env (CONWO_DB_*).
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
import psycopg  # noqa: E402
from backend import db as _appdb  # noqa: E402

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

def step_a(configs_conn) -> None:
    """Cross-reference each property (len>=8) against Jira tickets.

    Under Postgres, configs and tickets live in the SAME database, so the old
    SQLite ATTACH is gone — `jira.tickets` is just `tickets`."""
    print("=== Step A: Jira cross-references ===")
    t0 = time.time()

    # Fetch qualifying properties (distinct names only — service doesn't affect search)
    rows = configs_conn.execute(
        "SELECT DISTINCT property_name FROM configs WHERE length(property_name) >= 8"
    ).fetchall()
    properties = [r[0] for r in rows]
    total = len(properties)
    print(f"  {total} distinct properties with len>=8")

    # Single combined query: one scan per property, highest relevance wins via CASE ORDER.
    # ILIKE = case-insensitive (matches SQLite LIKE default). ESCAPE '\' for the
    # %/_ wildcards escaped by _escape_like().
    jira_sql = """
        SELECT key,
            CASE
                WHEN summary ILIKE %(p)s ESCAPE '\\'          THEN 1.0
                WHEN description_text ILIKE %(p)s ESCAPE '\\' THEN 0.7
                ELSE 0.5
            END AS relevance
        FROM tickets
        WHERE summary        ILIKE %(p)s ESCAPE '\\'
           OR description_text ILIKE %(p)s ESCAPE '\\'
           OR comments_text    ILIKE %(p)s ESCAPE '\\'
        ORDER BY relevance DESC, key
        LIMIT 10
    """

    inserted_total = 0
    batch_start = time.time()

    for idx, prop in enumerate(properties, 1):
        pattern = f"%{_escape_like(prop)}%"

        # Delete existing links for this property (ensures clean top-10 on re-run)
        configs_conn.execute(
            "DELETE FROM jira_links WHERE property_name = %s", (prop,)
        )

        matches = configs_conn.execute(jira_sql, {"p": pattern}).fetchall()
        if matches:
            with configs_conn.cursor() as cur:
                cur.executemany(
                    "INSERT INTO jira_links (property_name, jira_key, relevance) "
                    "VALUES (%s, %s, %s) "
                    "ON CONFLICT (property_name, jira_key) DO UPDATE SET "
                    "relevance = excluded.relevance",
                    [(prop, key, rel) for key, rel in matches],
                )
            inserted_total += len(matches)

        # Commit every BATCH_SIZE properties (autocommit=False auto-starts the
        # next transaction on the following statement).
        if idx % BATCH_SIZE == 0 or idx == total:
            configs_conn.commit()
            elapsed = time.time() - batch_start
            print(
                f"  [{idx}/{total}] batch committed — "
                f"{elapsed:.1f}s so far — {inserted_total} links"
            )
            batch_start = time.time()

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


def _step_b_service_match(configs_conn) -> None:
    """Part 1 — map (property_name, service) → module_slug via SERVICE_TO_MODULE_SLUG."""
    print("  Part 1: service_match ...")
    rows = configs_conn.execute(
        "SELECT DISTINCT property_name, service FROM configs"
    ).fetchall()

    inserted = 0
    for prop, service in rows:
        slug = SERVICE_TO_MODULE_SLUG.get(service)
        if slug:
            configs_conn.execute(
                "INSERT INTO module_links (property_name, module_slug, link_type) "
                "VALUES (%s, %s, 'service_match') "
                "ON CONFLICT (property_name, module_slug) DO UPDATE SET "
                "link_type = excluded.link_type",
                (prop, slug),
            )
            inserted += 1
    configs_conn.commit()
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
    for prop, slugs in mentions.items():
        for slug in slugs:
            configs_conn.execute(
                "INSERT INTO module_links (property_name, module_slug, link_type) "
                "VALUES (%s, %s, 'wiki_mention') "
                "ON CONFLICT (property_name, module_slug) DO NOTHING",
                (prop, slug, ),
            )
            inserted += 1
    configs_conn.commit()
    print(f"    {inserted} wiki_mention rows inserted")


# ---------------------------------------------------------------------------
# Step C — co-occurrence detection + LLM dependency inference
# ---------------------------------------------------------------------------

LLM_BATCH_SIZE = 80  # max properties per LLM batch
LLM_MODEL = "claude-haiku-4-5-20251001"


def step_c(configs_conn: sqlite3.Connection) -> None:
    """Step C — co-occurrence detection (no LLM) + LLM dependency inference."""
    print("=== Step C: Co-occurrence + LLM dependency inference ===")
    t0 = time.time()

    _step_c_cooccurrence(configs_conn)
    _step_c_llm(configs_conn)

    total = configs_conn.execute("SELECT COUNT(*) FROM dependencies").fetchone()[0]
    elapsed = time.time() - t0
    print(f"  Step C done: {total} total rows in dependencies ({elapsed:.1f}s)")


def _step_c_cooccurrence(configs_conn: sqlite3.Connection) -> None:
    """Part 1 — co-occurrence detection based on shared Jira tickets."""
    print("  Part 1: Co-occurrence detection ...")
    t0 = time.time()

    # Fetch all jira_links for properties with len >= 8
    rows = configs_conn.execute(
        "SELECT property_name, jira_key FROM jira_links "
        "WHERE length(property_name) >= 8"
    ).fetchall()

    # Build {property_name: set(jira_keys)}
    prop_to_tickets: dict[str, set[str]] = {}
    for prop, key in rows:
        prop_to_tickets.setdefault(prop, set()).add(key)

    properties = list(prop_to_tickets.keys())
    print(f"    {len(properties)} properties with jira links (len>=8)")

    # Find pairs with shared tickets >= 3
    pairs: list[tuple[str, str, int]] = []
    for prop_a, prop_b in combinations(properties, 2):
        shared = prop_to_tickets[prop_a] & prop_to_tickets[prop_b]
        count = len(shared)
        if count >= 3:
            pairs.append((prop_a, prop_b, count))

    print(f"    {len(pairs)} co-occurrence pairs (shared tickets >= 3)")

    if not pairs:
        print("    No co-occurrence pairs found.")
        return

    # Insert pairs into dependencies
    inserted = 0
    for prop_a, prop_b, count in pairs:
        confidence = min(0.5 + count * 0.05, 0.95)
        evidence = json.dumps({"co_occurrence_count": count})
        configs_conn.execute(
            "INSERT INTO dependencies "
            "(property_a, property_b, dep_type, direction, confidence, evidence) "
            "VALUES (%s, %s, 'co_occurrence', 'correlated', %s, %s) "
            "ON CONFLICT (property_a, property_b, dep_type) DO UPDATE SET "
            "direction = excluded.direction, confidence = excluded.confidence, "
            "evidence = excluded.evidence",
            (prop_a, prop_b, confidence, evidence),
        )
        inserted += 1
    configs_conn.commit()

    elapsed = time.time() - t0
    print(f"    {inserted} co_occurrence rows inserted/replaced ({elapsed:.1f}s)")


def _step_c_llm(configs_conn: sqlite3.Connection) -> None:
    """Part 2 — LLM-based dependency inference, grouped by service."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        print("  Part 2: ANTHROPIC_API_KEY not set — skipping LLM dependency inference.")
        return

    print("  Part 2: LLM dependency inference ...")
    t0 = time.time()

    try:
        import anthropic
    except ImportError:
        print("  WARNING: anthropic SDK not installed — skipping LLM step.")
        return

    client = anthropic.Anthropic(api_key=api_key)

    # Fetch all services
    services = [
        r[0] for r in configs_conn.execute(
            "SELECT DISTINCT service FROM configs ORDER BY service"
        ).fetchall()
    ]
    print(f"    Processing {len(services)} services ...")

    total_inserted = 0

    for service in services:
        # Fetch all (property_name, description, data_type) for this service
        props = configs_conn.execute(
            "SELECT DISTINCT property_name, description, data_type FROM configs "
            "WHERE service = %s ORDER BY property_name",
            (service,),
        ).fetchall()

        if len(props) < 2:
            # Can't have dependencies with fewer than 2 properties
            continue

        # Split into sub-batches if needed
        batches = [props[i:i + LLM_BATCH_SIZE] for i in range(0, len(props), LLM_BATCH_SIZE)]

        for batch_idx, batch in enumerate(batches, 1):
            batch_label = (
                f"service={service}"
                if len(batches) == 1
                else f"service={service} batch {batch_idx}/{len(batches)}"
            )
            try:
                inserted = _run_llm_batch(configs_conn, client, service, batch, batch_label)
                total_inserted += inserted
            except Exception as exc:
                print(f"    ERROR [{batch_label}]: {exc} — continuing to next service")

    elapsed = time.time() - t0
    print(f"    {total_inserted} LLM dependency rows inserted ({elapsed:.1f}s)")


def _run_llm_batch(
    configs_conn: sqlite3.Connection,
    client: "anthropic.Anthropic",
    service: str,
    batch: list[tuple],
    batch_label: str,
) -> int:
    """Run one LLM batch for a service sub-batch. Returns number of rows inserted."""
    # Build property list
    prop_lines = []
    prop_names_in_batch = set()
    for prop_name, description, data_type in batch:
        desc_text = description or "no description"
        dtype_text = data_type or "unknown"
        prop_lines.append(f"- {prop_name}: {desc_text} [{dtype_text}]")
        prop_names_in_batch.add(prop_name)

    properties_block = "\n".join(prop_lines)

    prompt = (
        f"You are analyzing PMS configs for service '{service}'.\n"
        f"Identify dependencies between these properties. Only report high-confidence ones (confidence >= 0.6).\n\n"
        f"Properties:\n{properties_block}\n\n"
        f"Return JSON only, no explanation:\n"
        f'{{\n'
        f'  "dependencies": [\n'
        f'    {{\n'
        f'      "property_a": "...",\n'
        f'      "property_b": "...",\n'
        f'      "dep_type": "functional|structural",\n'
        f'      "direction": "a_requires_b|b_requires_a|bidirectional",\n'
        f'      "confidence": 0.0-1.0,\n'
        f'      "evidence": "one sentence"\n'
        f'    }}\n'
        f'  ]\n'
        f'}}\n\n'
        f"Rules:\n"
        f"- functional: A only works/has effect when B is enabled/true\n"
        f"- structural: A and B share a naming prefix or clearly form a feature group\n"
        f"- Max 20 dependencies per service batch"
    )

    message = client.messages.create(
        model=LLM_MODEL,
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )

    resp_text = message.content[0].text if message.content else ""

    # Extract JSON from response
    match = re.search(r"\{.*\}", resp_text, re.DOTALL)
    if not match:
        print(f"    [{batch_label}] No JSON found in LLM response — skipping")
        return 0

    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        print(f"    [{batch_label}] JSON parse error: {exc} — skipping")
        return 0

    dependencies = data.get("dependencies", [])
    if not isinstance(dependencies, list):
        print(f"    [{batch_label}] 'dependencies' is not a list — skipping")
        return 0

    valid_dep_types = {"functional", "structural"}
    valid_directions = {"a_requires_b", "b_requires_a", "bidirectional", "correlated"}

    inserted = 0
    for dep in dependencies:
        if not isinstance(dep, dict):
            continue

        prop_a = dep.get("property_a", "")
        prop_b = dep.get("property_b", "")
        dep_type = dep.get("dep_type", "")
        direction = dep.get("direction", "")
        confidence_raw = dep.get("confidence", 0.0)
        evidence = dep.get("evidence", "")

        # Validate required fields
        if not prop_a or not prop_b or not dep_type or not direction:
            continue
        if dep_type not in valid_dep_types:
            continue
        if direction not in valid_directions:
            continue

        # Only insert deps for properties that were actually in this batch
        if prop_a not in prop_names_in_batch or prop_b not in prop_names_in_batch:
            continue

        try:
            confidence = float(confidence_raw)
        except (TypeError, ValueError):
            confidence = 0.6

        confidence = max(0.0, min(1.0, confidence))

        evidence_str = str(evidence) if evidence else None

        configs_conn.execute(
            "INSERT INTO dependencies "
            "(property_a, property_b, dep_type, direction, confidence, evidence) "
            "VALUES (%s, %s, %s, %s, %s, %s) "
            "ON CONFLICT (property_a, property_b, dep_type) DO NOTHING",
            (prop_a, prop_b, dep_type, direction, confidence, evidence_str),
        )
        inserted += 1

    configs_conn.commit()

    print(f"    [{batch_label}] {len(batch)} props → {len(dependencies)} deps proposed → {inserted} inserted")
    return inserted


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Enrich configs.sqlite with Jira links, module links, and dependencies."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--step", choices=["a", "b", "c"], help="Run a single step")
    group.add_argument("--all", action="store_true", help="Run steps a then b then c")
    args = parser.parse_args()

    # Ensure schema exists (idempotent), then open a dedicated rw connection.
    _appdb.init_db()
    _appdb.close_pool()
    conn = psycopg.connect(_appdb._dsn(), autocommit=False)
    conn.row_factory = _appdb._row_factory

    try:
        if args.all:
            step_a(conn)
            step_b(conn)
            step_c(conn)
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
