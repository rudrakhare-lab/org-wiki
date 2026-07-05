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

def test_compose_comments_text_returns_empty_when_no_comments():
    from scripts.embed_tickets import compose_comments_text
    assert compose_comments_text({"comments_text": None}) == ""
    assert compose_comments_text({"comments_text": ""}) == ""
    assert compose_comments_text({}) == ""

def test_compose_comments_text_returns_stripped_text():
    from scripts.embed_tickets import compose_comments_text
    assert compose_comments_text({"comments_text": "  hello  "}) == "hello"

def test_compose_comments_text_truncates_at_max():
    from scripts.embed_tickets import compose_comments_text, MAX_COMMENTS_CHARS
    long = "x" * (MAX_COMMENTS_CHARS + 100)
    out = compose_comments_text({"comments_text": long})
    assert len(out) == MAX_COMMENTS_CHARS

def test_argparse_accepts_comments_only_flag():
    """CLI flag --comments-only must parse successfully."""
    from scripts.embed_tickets import _build_argparser
    ap = _build_argparser()
    args = ap.parse_args(["--mode", "full", "--comments-only"])
    assert args.comments_only is True

    args = ap.parse_args(["--mode", "full"])
    assert args.comments_only is False

def test_select_sql_comments_only_filters_null_comments_embedding():
    """--comments-only must be resumable: only rows still missing
    comments_embedding should be re-selected after a quota-trip restart.
    Neither SELECT_FULL nor SELECT_DELTA filter on comments_embedding, so
    comments_only=True must route to a query that does.
    """
    from scripts.embed_tickets import _select_sql
    sql_full = _select_sql("full", comments_only=True)
    sql_delta = _select_sql("delta", comments_only=True)
    assert "comments_embedding IS NULL" in sql_full
    assert "comments_embedding IS NULL" in sql_delta

def test_select_sql_normal_mode_ignores_comments_embedding():
    from scripts.embed_tickets import _select_sql, SELECT_FULL, SELECT_DELTA
    assert _select_sql("full", comments_only=False) is SELECT_FULL
    assert _select_sql("delta", comments_only=False) is SELECT_DELTA
