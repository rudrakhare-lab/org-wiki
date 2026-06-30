"""Verifies migration 150 creates expected schema. Skipped if no Postgres available."""
import os
import pytest
import psycopg

PG_DSN = os.getenv("CONWO_TEST_DSN")
pytestmark = pytest.mark.skipif(not PG_DSN, reason="requires CONWO_TEST_DSN")

def test_migration_150_creates_tsvector_column():
    with psycopg.connect(PG_DSN) as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT data_type FROM information_schema.columns
            WHERE table_name='tickets' AND column_name='search_tsv'
        """)
        row = cur.fetchone()
        assert row and row[0] == 'tsvector'

def test_migration_150_creates_embedding_column():
    with psycopg.connect(PG_DSN) as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT udt_name FROM information_schema.columns
            WHERE table_name='tickets' AND column_name='embedding'
        """)
        row = cur.fetchone()
        assert row and row[0] == 'vector'

def test_migration_150_creates_ticket_links_table():
    with psycopg.connect(PG_DSN) as conn, conn.cursor() as cur:
        cur.execute("SELECT to_regclass('ticket_links')")
        assert cur.fetchone()[0] == 'ticket_links'

def test_migration_150_creates_shadow_log_table():
    with psycopg.connect(PG_DSN) as conn, conn.cursor() as cur:
        cur.execute("SELECT to_regclass('retrieval_shadow_log')")
        assert cur.fetchone()[0] == 'retrieval_shadow_log'

def test_migration_150_creates_hnsw_index():
    with psycopg.connect(PG_DSN) as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT indexdef FROM pg_indexes
            WHERE tablename='tickets' AND indexname='idx_tickets_embedding'
        """)
        row = cur.fetchone()
        assert row and 'hnsw' in row[0].lower()
