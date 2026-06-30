from unittest.mock import patch
import pytest

def test_select_delta_query_excludes_already_embedded_unchanged_rows():
    from scripts import embed_tickets
    sql = embed_tickets.SELECT_DELTA
    assert "embedded_at IS NULL" in sql
    assert "updated_at > embedded_at" in sql

def test_select_full_query_returns_all_rows():
    from scripts import embed_tickets
    assert "embedded_at" not in embed_tickets.SELECT_FULL
    assert "FROM tickets" in embed_tickets.SELECT_FULL

def test_compose_text_concatenates_summary_and_description():
    from scripts import embed_tickets
    row = {"summary": "Login fails", "description_text": "Users see 500"}
    t = embed_tickets.compose_text(row)
    assert "Login fails" in t
    assert "Users see 500" in t

def test_compose_text_truncates_to_max_chars():
    from scripts import embed_tickets
    row = {"summary": "x", "description_text": "y" * 100000}
    t = embed_tickets.compose_text(row)
    assert len(t) <= embed_tickets.MAX_TEXT_CHARS
