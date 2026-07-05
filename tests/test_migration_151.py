"""Verifies migration 151 (comments_embedding) creates expected schema.

File-content assertions run unconditionally (no DB required). The live-schema
introspection tests are skipped if no Postgres is available, matching the
pattern in tests/test_migration_150.py.
"""
import os
from pathlib import Path

import pytest
import psycopg

MIGRATION_PATH = (
    Path(__file__).resolve().parent.parent
    / "migrations" / "postgres" / "151_comments_embedding.sql"
)

PG_DSN = os.getenv("CONWO_TEST_DSN")


# ── Unconditional file-content assertions (no DB required) ────────────────

def test_migration_151_file_exists():
    assert MIGRATION_PATH.exists(), f"missing {MIGRATION_PATH}"


def test_migration_151_adds_comments_embedding_column_idempotently():
    sql = MIGRATION_PATH.read_text(encoding="utf-8")
    assert "ADD COLUMN IF NOT EXISTS comments_embedding" in sql
    assert "vector(768)" in sql


def test_migration_151_creates_hnsw_index_idempotently():
    sql = MIGRATION_PATH.read_text(encoding="utf-8")
    assert "CREATE INDEX IF NOT EXISTS idx_tickets_comments_embedding" in sql
    assert "USING hnsw" in sql
    assert "vector_cosine_ops" in sql


# ── Live-schema introspection (requires CONWO_TEST_DSN) ────────────────────

@pytest.mark.skipif(not PG_DSN, reason="requires CONWO_TEST_DSN")
def test_migration_151_creates_comments_embedding_column():
    with psycopg.connect(PG_DSN) as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT udt_name FROM information_schema.columns
            WHERE table_name='tickets' AND column_name='comments_embedding'
        """)
        row = cur.fetchone()
        assert row and row[0] == 'vector'


@pytest.mark.skipif(not PG_DSN, reason="requires CONWO_TEST_DSN")
def test_migration_151_creates_comments_embedding_hnsw_index():
    with psycopg.connect(PG_DSN) as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT indexdef FROM pg_indexes
            WHERE tablename='tickets' AND indexname='idx_tickets_comments_embedding'
        """)
        row = cur.fetchone()
        assert row and 'hnsw' in row[0].lower()
