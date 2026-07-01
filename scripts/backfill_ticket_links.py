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
    # Note: uses a plain client-side cursor (fetchall) rather than a server-side
    # named cursor. Prod connections may go through PgBouncer in transaction
    # mode, which does not preserve named cursors between statements. The full
    # ticket set at ~40k rows × two small columns is comfortably in-memory.
    with psycopg.connect(dsn) as conn:
        with conn.cursor() as rcur:
            rcur.execute(sql)
            rows = rcur.fetchall()
        with conn.cursor() as wcur:
            for i, (src_key, links_json) in enumerate(rows):
                pairs = parse_links(src_key, links_json or "")
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

def _resolve_dsn(cli_dsn: str | None) -> str | None:
    """Resolve the DSN in this order:
      1. --dsn CLI flag
      2. CONWO_DSN env var
      3. DATABASE_URL env var (prod platform convention)
      4. If CONWO_SECRET_ID is set, load AWS Secrets Manager into os.environ
         (via backend.secrets_loader) and retry (2) + (3).
    """
    if cli_dsn:
        return cli_dsn
    dsn = os.getenv("CONWO_DSN") or os.getenv("DATABASE_URL")
    if dsn:
        return dsn
    if os.getenv("CONWO_SECRET_ID"):
        try:
            # Add repo root to sys.path so backend.* is importable when this
            # script is run standalone from anywhere.
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from backend.secrets_loader import load_aws_secrets
            load_aws_secrets()
            return os.getenv("CONWO_DSN") or os.getenv("DATABASE_URL")
        except Exception as exc:  # noqa: BLE001
            print(f"secrets_loader.load_aws_secrets() failed: {exc}", file=sys.stderr)
    return None

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["full", "delta"], required=True)
    ap.add_argument("--dsn", default=None)
    args = ap.parse_args()
    dsn = _resolve_dsn(args.dsn)
    if not dsn:
        print(
            "DSN required. Set one of: --dsn, CONWO_DSN, DATABASE_URL, or "
            "CONWO_SECRET_ID (for AWS Secrets Manager auto-load).",
            file=sys.stderr,
        )
        return 2
    return run(dsn, args.mode)

if __name__ == "__main__":
    sys.exit(main())
