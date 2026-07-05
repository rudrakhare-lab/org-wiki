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


# ---------------------------------------------------------------------------
# Behavioral tests for run() — mocked connection, no live DB.
# These exercise the actual execute() calls so a silent revert of the
# COALESCE / embedded_at-watermark semantics fails a test instead of only
# changing an unasserted SQL string.
# ---------------------------------------------------------------------------

from unittest.mock import MagicMock


def _mock_connect_with_rows(rows):
    """Build a psycopg.connect(...) stand-in yielding `rows` from the select
    cursor. The same cursor mock serves the update cursor, so all execute()
    calls (SELECT first, then UPDATEs) land in cur.execute.call_args_list."""
    cur = MagicMock()
    cur.__iter__.return_value = iter(rows)
    conn = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur
    connect_cm = MagicMock()
    connect_cm.__enter__.return_value = conn
    return connect_cm, cur


def _update_calls(cur):
    return [c for c in cur.execute.call_args_list if "UPDATE" in c.args[0]]


def test_run_comments_only_never_touches_embedding_or_embedded_at():
    """--comments-only must not clobber embedding AND must not bump the
    embedded_at watermark: bumping it would make a later delta run skip a
    description edit that landed before the backfill (updated_at would no
    longer be > embedded_at — the edit would silently never be re-embedded)."""
    from scripts import embed_tickets
    rows = [
        {"key": "TS-1", "summary": "Login fails", "description_text": "500 on login",
         "comments_text": "Fixed by resetting the SSO cert"},
        {"key": "TS-2", "summary": "Kiosk blank", "description_text": "Screen blank",
         "comments_text": ""},
    ]
    connect_cm, cur = _mock_connect_with_rows(rows)
    fake_vec = [0.1] * 768
    with patch.object(embed_tickets.psycopg, "connect", return_value=connect_cm), \
         patch.object(embed_tickets, "register_vector"), \
         patch.object(embed_tickets, "embed_documents", return_value=[fake_vec]) as emb:
        rc = embed_tickets.run("postgresql://unused", "full", comments_only=True)
    assert rc == 0

    # Only the single non-empty comments text was embedded; the description
    # embedder path never ran.
    emb.assert_called_once_with(["Fixed by resetting the SSO cert"])

    updates = _update_calls(cur)
    assert len(updates) == 2
    for call in updates:
        sql = call.args[0]
        assert "embedded_at" not in sql, \
            "--comments-only must not bump the embedded_at watermark"
        # Only comments_embedding may be written — after removing that token,
        # no other reference to the embedding column may remain.
        assert "embedding" not in sql.replace("comments_embedding", ""), \
            "--comments-only must not touch the description embedding column"
        assert "COALESCE" in sql

    params_by_key = {c.args[1]["key"]: c.args[1] for c in updates}
    assert params_by_key["TS-1"]["comm_vec"] == fake_vec
    assert params_by_key["TS-2"]["comm_vec"] is None  # empty comments stay NULL


def test_run_normal_mode_coalesces_comments_and_sets_embedded_at():
    """Normal (dual-embed) runs set the embedded_at watermark and use COALESCE
    so a row with empty comments keeps comments_embedding NULL rather than
    having it overwritten."""
    from scripts import embed_tickets
    rows = [
        {"key": "TS-1", "summary": "Login fails", "description_text": "500 on login",
         "comments_text": "Fixed by resetting the SSO cert"},
        {"key": "TS-2", "summary": "Kiosk blank", "description_text": "Screen blank",
         "comments_text": None},
    ]
    connect_cm, cur = _mock_connect_with_rows(rows)
    desc_vec_1, desc_vec_2, comm_vec_1 = [0.1] * 768, [0.2] * 768, [0.3] * 768
    with patch.object(embed_tickets.psycopg, "connect", return_value=connect_cm), \
         patch.object(embed_tickets, "register_vector"), \
         patch.object(embed_tickets, "embed_documents",
                      side_effect=[[desc_vec_1, desc_vec_2], [comm_vec_1]]) as emb:
        rc = embed_tickets.run("postgresql://unused", "full", comments_only=False)
    assert rc == 0
    # One description batch + one comments batch — embedded SEPARATELY,
    # never concatenated into a single text.
    assert emb.call_count == 2

    updates = _update_calls(cur)
    assert len(updates) == 2
    for call in updates:
        sql = call.args[0]
        assert "COALESCE" in sql
        assert "embedded_at" in sql

    params_by_key = {c.args[1]["key"]: c.args[1] for c in updates}
    assert params_by_key["TS-1"]["desc_vec"] == desc_vec_1
    assert params_by_key["TS-1"]["comm_vec"] == comm_vec_1
    assert params_by_key["TS-2"]["desc_vec"] == desc_vec_2
    assert params_by_key["TS-2"]["comm_vec"] is None
