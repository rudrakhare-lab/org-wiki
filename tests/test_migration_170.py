"""Migration 170 — wiki_chunks table for wiki retrieval v2."""
import os
import pathlib
import pytest

PG_DSN = os.getenv("CONWO_TEST_DSN")
MIGRATION = pathlib.Path("migrations/postgres/170_wiki_chunks.sql")


def test_migration_170_file_exists():
    assert MIGRATION.is_file()


def test_migration_170_is_idempotent_sql():
    sql = MIGRATION.read_text()
    assert "CREATE TABLE IF NOT EXISTS wiki_chunks" in sql
    assert sql.count("IF NOT EXISTS") >= 4  # table + 3 indexes


def test_migration_170_has_required_columns_and_indexes():
    sql = MIGRATION.read_text()
    for col in ("agent_id", "page_path", "section_anchor", "section_title",
                "page_type", "chunk_index", "chunk_text", "last_updated",
                "content_hash", "embedding", "search_tsv"):
        assert col in sql, f"missing column {col}"
    assert "vector(768)" in sql
    assert "hnsw" in sql and "vector_cosine_ops" in sql
    assert "GENERATED ALWAYS" in sql  # search_tsv is generated (repo convention)


@pytest.mark.skipif(not PG_DSN, reason="requires CONWO_TEST_DSN")
def test_migration_170_applies_idempotently():
    import psycopg
    sql = MIGRATION.read_text()
    with psycopg.connect(PG_DSN, autocommit=True) as conn:
        conn.execute(sql)
        conn.execute(sql)  # second run must be a no-op
        cur = conn.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'wiki_chunks'")
        cols = {r[0] for r in cur.fetchall()}
        assert {"agent_id", "page_path", "section_anchor", "embedding",
                "content_hash", "search_tsv"} <= cols
