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
MAX_COMMENTS_CHARS = 8000  # Same cap as MAX_TEXT_CHARS; keeps embed cost predictable
                           # for long comment threads.

SELECT_FULL = """
    SELECT key, summary, description_text, comments_text
    FROM tickets
    ORDER BY updated_at DESC
"""

SELECT_DELTA = """
    SELECT key, summary, description_text, comments_text
    FROM tickets
    WHERE embedded_at IS NULL OR updated_at > embedded_at
    ORDER BY updated_at DESC
"""

# --comments-only backfill queries: filter on comments_embedding IS NULL so a
# re-run after a Gemini quota trip skips rows already backfilled (resumable).
# Accepted tradeoff: rows whose comments_text is permanently empty re-select on
# every run, but they never reach the embedder (empty texts are skipped), so
# they cost no quota.
SELECT_FULL_COMMENTS_ONLY = """
    SELECT key, summary, description_text, comments_text
    FROM tickets
    WHERE comments_embedding IS NULL
    ORDER BY updated_at DESC
"""

SELECT_DELTA_COMMENTS_ONLY = """
    SELECT key, summary, description_text, comments_text
    FROM tickets
    WHERE comments_embedding IS NULL
      AND (embedded_at IS NULL OR updated_at > embedded_at)
    ORDER BY updated_at DESC
"""

UPDATE_ROW = """
    UPDATE tickets
    SET embedding          = COALESCE(%(desc_vec)s::vector, embedding),
        comments_embedding = COALESCE(%(comm_vec)s::vector, comments_embedding),
        embedded_at        = now()
    WHERE key = %(key)s
"""

# --comments-only path: touches ONLY comments_embedding. It must not reference
# the embedding column (never-clobber) and must NOT bump the embedded_at
# watermark — doing so would make a later delta run skip a description edit
# that landed before the backfill (updated_at would no longer be > embedded_at,
# so the edit would silently never be re-embedded).
UPDATE_ROW_COMMENTS_ONLY = """
    UPDATE tickets
    SET comments_embedding = COALESCE(%(comm_vec)s::vector, comments_embedding)
    WHERE key = %(key)s
"""

def compose_text(row: dict) -> str:
    summary = (row.get("summary") or "").strip()
    desc = (row.get("description_text") or "").strip()
    text = f"{summary}\n\n{desc}" if desc else summary
    if len(text) > MAX_TEXT_CHARS:
        text = text[:MAX_TEXT_CHARS]
    return text

def compose_comments_text(row: dict) -> str:
    """Return trimmed comments_text for the second embedding, or '' if empty."""
    text = (row.get("comments_text") or "").strip()
    if len(text) > MAX_COMMENTS_CHARS:
        text = text[:MAX_COMMENTS_CHARS]
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

def _select_sql(mode: str, comments_only: bool = False) -> str:
    """Pick the SELECT query for (mode, comments_only).

    comments_only=True routes to the *_COMMENTS_ONLY variants, which add
    `WHERE comments_embedding IS NULL` so a backfill re-run after a Gemini
    quota trip only processes rows still missing the column (resumable) and
    never re-embeds rows already completed.
    """
    if comments_only:
        return SELECT_FULL_COMMENTS_ONLY if mode == "full" else SELECT_DELTA_COMMENTS_ONLY
    return SELECT_FULL if mode == "full" else SELECT_DELTA

def run(dsn: str, mode: str, comments_only: bool = False) -> int:
    sql = _select_sql(mode, comments_only)
    total = 0
    t0 = time.perf_counter()
    with psycopg.connect(dsn) as conn:
        register_vector(conn)
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql)
            for batch in iter_batches(cur, BATCH):
                # Description embeddings (unless --comments-only).
                desc_vecs: list = [None] * len(batch)
                if not comments_only:
                    desc_texts = [compose_text(r) for r in batch]
                    desc_vecs = embed_documents(desc_texts)

                # Comment embeddings — separate batch; skip rows with empty comments.
                comm_texts_indexed = [(i, compose_comments_text(r))
                                      for i, r in enumerate(batch)]
                non_empty = [(i, t) for i, t in comm_texts_indexed if t]
                comm_vecs: list = [None] * len(batch)
                if non_empty:
                    embedded = embed_documents([t for _, t in non_empty])
                    for (i, _), v in zip(non_empty, embedded):
                        comm_vecs[i] = v

                update_sql = UPDATE_ROW_COMMENTS_ONLY if comments_only else UPDATE_ROW
                with conn.cursor() as upd:
                    for r, dv, cv in zip(batch, desc_vecs, comm_vecs):
                        params = {"key": r["key"], "comm_vec": cv}
                        if not comments_only:
                            params["desc_vec"] = dv
                        upd.execute(update_sql, params)
                conn.commit()
                total += len(batch)
                dt = time.perf_counter() - t0
                print(f"  embedded {total} rows ({total/dt:.1f}/s)", flush=True)
    print(f"done: {total} rows embedded.", flush=True)
    return 0

def _resolve_dsn(cli_dsn: str | None) -> str | None:
    """Resolve the DSN in this order:
      1. --dsn CLI flag
      2. CONWO_DSN env var
      3. DATABASE_URL env var (prod platform convention)
      4. If CONWO_SECRET_ID is set, load AWS Secrets Manager into os.environ
         (via backend.secrets_loader) and retry (2) + (3).
    Also loads GOOGLE_GENAI_API_KEY into os.environ as a side effect of step 4,
    which the embedder (via backend.retrieval.v2.embed) requires at runtime.
    """
    if cli_dsn:
        return cli_dsn
    dsn = os.getenv("CONWO_DSN") or os.getenv("DATABASE_URL")
    if dsn:
        return dsn
    if os.getenv("CONWO_SECRET_ID"):
        try:
            from backend.secrets_loader import load_aws_secrets
            load_aws_secrets()
            return os.getenv("CONWO_DSN") or os.getenv("DATABASE_URL")
        except Exception as exc:  # noqa: BLE001
            print(f"secrets_loader.load_aws_secrets() failed: {exc}", file=sys.stderr)
    return None

def _build_argparser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["full", "delta"], required=True)
    ap.add_argument("--dsn", default=None)
    ap.add_argument("--comments-only", action="store_true",
                    help="Populate only comments_embedding; leave embedding untouched. "
                         "Used for the post-migration-151 backfill of existing tickets.")
    return ap


def main() -> int:
    args = _build_argparser().parse_args()
    dsn = _resolve_dsn(args.dsn)
    if not dsn:
        print(
            "DSN required. Set one of: --dsn, CONWO_DSN, DATABASE_URL, or "
            "CONWO_SECRET_ID (for AWS Secrets Manager auto-load).",
            file=sys.stderr,
        )
        return 2
    return run(dsn, args.mode, comments_only=args.comments_only)

if __name__ == "__main__":
    sys.exit(main())
