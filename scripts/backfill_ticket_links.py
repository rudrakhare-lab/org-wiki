"""Normalize tickets.links_json into the ticket_links table.

Modes:
  --full   rebuild ticket_links from every ticket row.
  --delta  process tickets updated since the last successful run (tracked in sync_runs).
"""
from __future__ import annotations
import argparse
import json
import os
import re
import sys

import psycopg

_NORMALIZE = re.compile(r"[^a-z0-9]+")

def _norm_type(s: str) -> str:
    s = (s or "").strip().lower()
    s = _NORMALIZE.sub("_", s).strip("_")
    return s

def parse_links(src_key: str, links_json: str) -> list[tuple[str, str, str]]:
    """Return list of (src, dst, link_type) tuples. Robust to empty/malformed input."""
    if not links_json:
        return []
    try:
        data = json.loads(links_json)
    except Exception:
        return []
    if not isinstance(data, list):
        return []
    pairs: list[tuple[str, str, str]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        ltype = _norm_type(item.get("type") or "")
        if not ltype:
            continue
        for end_key in ("outward", "inward"):
            dst = item.get(end_key)
            if isinstance(dst, str) and dst:
                pairs.append((src_key, dst, ltype))
    return pairs

UPSERT = """
    INSERT INTO ticket_links (src_key, dst_key, link_type)
    VALUES (%s, %s, %s)
    ON CONFLICT (src_key, dst_key, link_type) DO NOTHING
"""

DELETE_FOR_SRC = "DELETE FROM ticket_links WHERE src_key = %s"

SELECT_FULL = "SELECT key, links_json FROM tickets"
SELECT_DELTA = """
    SELECT key, links_json
    FROM tickets
    WHERE updated_at > (
        SELECT COALESCE(MAX(ended_at), 'epoch'::timestamptz)
        FROM sync_runs WHERE status = 'success' AND filter_name = 'ticket_links'
    )
"""

def run(dsn: str, mode: str) -> int:
    sql = SELECT_FULL if mode == "full" else SELECT_DELTA
    n_rows = 0
    n_links = 0
    with psycopg.connect(dsn) as conn:
        with conn.cursor(name="cur") as cur:  # server-side cursor for streaming
            cur.execute(sql)
            for src_key, links_json in cur:
                pairs = parse_links(src_key, links_json or "")
                with conn.cursor() as wcur:
                    wcur.execute(DELETE_FOR_SRC, (src_key,))
                    for p in pairs:
                        wcur.execute(UPSERT, p)
                n_rows += 1
                n_links += len(pairs)
                if n_rows % 1000 == 0:
                    conn.commit()
            conn.commit()
        # mark sync_runs
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO sync_runs (started_at, ended_at, filter_name, mode, status) "
                "VALUES (now(), now(), 'ticket_links', %s, 'success')", (mode,))
        conn.commit()
    print(f"done: {n_rows} tickets processed, {n_links} links written.", flush=True)
    return 0

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["full", "delta"], required=True)
    ap.add_argument("--dsn", default=os.getenv("CONWO_DSN"))
    args = ap.parse_args()
    if not args.dsn:
        print("CONWO_DSN env var or --dsn required", file=sys.stderr)
        return 2
    return run(args.dsn, args.mode)

if __name__ == "__main__":
    sys.exit(main())
