"""Embed Jira tickets into pgvector. Run as a one-time backfill (--full) or
nightly delta (--delta). Idempotent; resumable; safe to interrupt.
"""
from __future__ import annotations
import argparse
import os
import sys
import time
from typing import Iterable

import psycopg
from psycopg.rows import dict_row
from pgvector.psycopg import register_vector

# Add backend to path so we can import retrieval.v2.embed
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.retrieval.v2.embed import embed_documents  # noqa: E402

BATCH = 100
MAX_TEXT_CHARS = 8000  # Gemini handles more but trimming keeps embed cost predictable.

SELECT_FULL = """
    SELECT key, summary, description_text
    FROM tickets
    ORDER BY updated_at DESC
"""

SELECT_DELTA = """
    SELECT key, summary, description_text
    FROM tickets
    WHERE embedded_at IS NULL OR updated_at > embedded_at
    ORDER BY updated_at DESC
"""

UPDATE_ROW = """
    UPDATE tickets
    SET embedding = %s, embedded_at = now()
    WHERE key = %s
"""

def compose_text(row: dict) -> str:
    summary = (row.get("summary") or "").strip()
    desc = (row.get("description_text") or "").strip()
    text = f"{summary}\n\n{desc}" if desc else summary
    if len(text) > MAX_TEXT_CHARS:
        text = text[:MAX_TEXT_CHARS]
    return text

def iter_batches(rows: Iterable[dict], n: int) -> Iterable[list[dict]]:
    buf: list[dict] = []
    for r in rows:
        buf.append(r)
        if len(buf) >= n:
            yield buf
            buf = []
    if buf:
        yield buf

def run(dsn: str, mode: str) -> int:
    sql = SELECT_FULL if mode == "full" else SELECT_DELTA
    total = 0
    t0 = time.perf_counter()
    with psycopg.connect(dsn) as conn:
        register_vector(conn)
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql)
            for batch in iter_batches(cur, BATCH):
                texts = [compose_text(r) for r in batch]
                vecs = embed_documents(texts)
                with conn.cursor() as upd:
                    for r, v in zip(batch, vecs):
                        upd.execute(UPDATE_ROW, (v, r["key"]))
                conn.commit()
                total += len(batch)
                dt = time.perf_counter() - t0
                print(f"  embedded {total} rows ({total/dt:.1f}/s)", flush=True)
    print(f"done: {total} rows embedded.", flush=True)
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
