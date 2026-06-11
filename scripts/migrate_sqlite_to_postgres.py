#!/usr/bin/env python3
"""
One-time ETL: copy rows from the legacy SQLite files into PostgreSQL.

Reads each source SQLite DB, introspects its columns, and bulk-inserts into the
same-named Postgres table (schema must already exist via migrations). Idempotent:
uses INSERT ... ON CONFLICT DO NOTHING so re-running won't duplicate.

Tables are migrated in FK-dependency order (parents before children). Virtual /
shadow tables (configs_fts*, sqlite_sequence) are skipped.

Usage (run with the venv, after `docker compose up -d postgres` and migrations):
    venv/bin/python scripts/migrate_sqlite_to_postgres.py --only auth,conversations,traces
    venv/bin/python scripts/migrate_sqlite_to_postgres.py --only tickets,configs
    venv/bin/python scripts/migrate_sqlite_to_postgres.py --all
    venv/bin/python scripts/migrate_sqlite_to_postgres.py --all --verify-only
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=str(ROOT / ".env"))
sys.path.insert(0, str(ROOT))

from backend import db  # noqa: E402

RAW = ROOT / "raw"

# Source DB → ordered list of tables (FK parents first). IDENTITY-PK tables get
# their sequence reset after load.
PLAN: dict[str, dict] = {
    "auth": {
        "sqlite": RAW / "auth" / "auth.sqlite",
        "tables": ["users", "tokens"],
        "identity": {},
    },
    "conversations": {
        "sqlite": RAW / "conversations" / "conversations.sqlite",
        "tables": ["conversations", "messages"],
        "identity": {},
    },
    "traces": {
        "sqlite": RAW / "traces" / "traces.sqlite",
        "tables": ["trace_sessions", "trace_events", "trace_metrics"],
        "identity": {},
    },
    "tickets": {
        "sqlite": RAW / "jira" / "tickets.sqlite",
        "tables": ["tickets", "custom_field_map", "sync_runs",
                   "ticket_classifications", "ticket_module_tags"],
        "identity": {"sync_runs": "id"},
    },
    "configs": {
        "sqlite": RAW / "configs" / "configs.sqlite",
        "tables": ["configs", "jira_links", "module_links", "dependencies"],
        "identity": {"configs": "id"},
    },
}

BATCH = 500


def _sqlite_columns(scon: sqlite3.Connection, table: str) -> list[str]:
    return [r[1] for r in scon.execute(f"PRAGMA table_info({table})").fetchall()]


def migrate_table(scon: sqlite3.Connection, table: str, identity_col: str | None) -> tuple[int, int]:
    cols = _sqlite_columns(scon, table)
    if not cols:
        print(f"    !! {table}: no columns found in SQLite — skipped")
        return (0, 0)
    collist = ", ".join(cols)
    placeholders = ", ".join(["%s"] * len(cols))
    insert = (f"INSERT INTO {table} ({collist}) VALUES ({placeholders}) "
              f"ON CONFLICT DO NOTHING")

    src_rows = scon.execute(f"SELECT {collist} FROM {table}").fetchall()
    total = len(src_rows)
    inserted = 0
    with db.connection() as conn:
        with conn.cursor() as cur:
            for i in range(0, total, BATCH):
                batch = [tuple(r) for r in src_rows[i:i + BATCH]]
                cur.executemany(insert, batch)
            # row count after load (PG side)
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            inserted = cur.fetchone()[0]
            # Reset IDENTITY sequence so future inserts don't collide with copied ids.
            if identity_col:
                cur.execute(
                    f"SELECT setval(pg_get_serial_sequence('{table}', '{identity_col}'), "
                    f"COALESCE((SELECT MAX({identity_col}) FROM {table}), 1))"
                )
    return (total, inserted)


def verify(scon: sqlite3.Connection, table: str) -> tuple[int, int]:
    src = scon.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    with db.connection() as conn:
        dst = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    return src, dst


def main() -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--only", help="comma-separated subset of: " + ",".join(PLAN))
    g.add_argument("--all", action="store_true")
    ap.add_argument("--verify-only", action="store_true",
                    help="only compare row counts, don't write")
    args = ap.parse_args()

    groups = list(PLAN) if args.all else [s.strip() for s in args.only.split(",")]
    db.init_pool()
    db.init_db()  # ensure schema exists

    overall_ok = True
    for grp in groups:
        spec = PLAN.get(grp)
        if not spec:
            print(f"!! unknown group {grp!r} — skipping"); overall_ok = False; continue
        sqlite_path: Path = spec["sqlite"]
        if not sqlite_path.exists():
            print(f"!! {grp}: source {sqlite_path} not found — skipping"); overall_ok = False; continue
        print(f"\n=== {grp}  ({sqlite_path.name}) ===")
        scon = sqlite3.connect(str(sqlite_path))
        try:
            for table in spec["tables"]:
                if args.verify_only:
                    src, dst = verify(scon, table)
                    flag = "OK" if src == dst else "MISMATCH"
                    if src != dst:
                        overall_ok = False
                    print(f"    {table:<24} sqlite={src:<8} postgres={dst:<8} {flag}")
                else:
                    total, after = migrate_table(scon, table, spec["identity"].get(table))
                    print(f"    {table:<24} sqlite={total:<8} -> postgres now has {after}")
        finally:
            scon.close()

    db.close_pool()
    print("\n" + ("ALL OK" if overall_ok else "COMPLETED WITH WARNINGS"))
    return 0 if overall_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
