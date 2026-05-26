"""Pagination tests for jira_get_ticket and wiki_read_page (G09 + G20).

Backwards-compatibility note:
  Both handlers add `total_length` / `has_more` / `next_offset` fields but
  keep the original `description_text` / `comments_text` / `content` field
  names. Callers that read those fields keep working; the new fields are
  additive. Verified by the `_backwards_compat` tests below.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch


# ── jira_get_ticket pagination ────────────────────────────────────────────────

def _mock_sqlite_row(description: str, comments: str):
    """Return a row tuple matching the SELECT column order in
    _jira_get_ticket_handler. Lets us bypass the real SQLite DB."""
    return (
        "TS-12345", "Test summary", "done", "P1",
        "2026-04-12", "2026-04-13",
        description, comments, 5,
        '{"links": []}', "WP-admin", "EPIC-1",
    )


def _patch_jira_db(monkeypatch, row):
    """Replace JIRA_DB with a mock Path whose .exists() returns True, and
    swap _open_ro() to return a mock cursor that yields `row`."""
    from backend.tools import jira_tools
    fake_db = MagicMock()
    fake_db.exists.return_value = True
    monkeypatch.setattr(jira_tools, "JIRA_DB", fake_db)
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = row
    mock_conn = MagicMock()
    mock_conn.execute.return_value = mock_cursor
    monkeypatch.setattr(jira_tools, "_open_ro", lambda: mock_conn)


def test_jira_get_ticket_full_read_when_under_default_chunk(monkeypatch):
    """Backwards-compat: short description (<2000 chars) returns fully, with
    has_more=False. The 'content' fields keep their pre-G09 names."""
    from backend.tools.jira_tools import _jira_get_ticket_handler
    _patch_jira_db(monkeypatch, _mock_sqlite_row("short desc", "short comments"))
    result = _jira_get_ticket_handler({"key": "TS-12345"})

    assert result["description_text"] == "short desc"
    assert result["description_total_length"] == len("short desc")
    assert result["description_has_more"] is False
    assert result["description_next_offset"] is None
    assert result["comments_text"] == "short comments"
    assert result["comments_has_more"] is False


def test_jira_get_ticket_first_chunk_when_over_default(monkeypatch):
    """Long description: first 2000 chars returned, has_more=True, next_offset=2000."""
    from backend.tools.jira_tools import _jira_get_ticket_handler
    long_desc = "x" * 3500  # 1500 chars past the default chunk
    _patch_jira_db(monkeypatch, _mock_sqlite_row(long_desc, ""))
    result = _jira_get_ticket_handler({"key": "TS-12345"})

    assert len(result["description_text"]) == 2000
    assert result["description_total_length"] == 3500
    assert result["description_has_more"] is True
    assert result["description_next_offset"] == 2000


def test_jira_get_ticket_offset_midway(monkeypatch):
    """Offset = 2000 retrieves chars 2000..4000; remaining 1500 chars is < chunk, so has_more=False."""
    from backend.tools.jira_tools import _jira_get_ticket_handler
    long_desc = "x" * 1500 + "Y" * 2000  # 3500 chars total, Y starts at index 1500
    _patch_jira_db(monkeypatch, _mock_sqlite_row(long_desc, ""))
    result = _jira_get_ticket_handler({"key": "TS-12345", "description_offset": 2000})

    assert result["description_text"] == "Y" * 1500  # chars 2000..3500
    assert result["description_total_length"] == 3500
    assert result["description_has_more"] is False
    assert result["description_next_offset"] is None


def test_jira_get_ticket_offset_past_end_returns_empty(monkeypatch):
    """An offset past the total length returns an empty chunk with has_more=False."""
    from backend.tools.jira_tools import _jira_get_ticket_handler
    _patch_jira_db(monkeypatch, _mock_sqlite_row("only 10 ch", ""))
    result = _jira_get_ticket_handler({"key": "TS-12345", "description_offset": 100})

    assert result["description_text"] == ""
    assert result["description_total_length"] == 10
    assert result["description_has_more"] is False


def test_jira_get_ticket_backwards_compat_callers_reading_legacy_fields(monkeypatch):
    """Pre-G09 callers that only read description_text/comments_text/comment_count
    must keep working without the new fields breaking them."""
    from backend.tools.jira_tools import _jira_get_ticket_handler
    _patch_jira_db(monkeypatch, _mock_sqlite_row("desc here", "comments here"))
    result = _jira_get_ticket_handler({"key": "TS-12345"})

    # All legacy fields still present and populated
    assert result["description_text"] == "desc here"
    assert result["comments_text"] == "comments here"
    assert result["comment_count"] == 5
    assert result["summary"] == "Test summary"
    assert result["status_category"] == "done"
    assert result["priority"] == "P1"


# ── wiki_read_page pagination ─────────────────────────────────────────────────

def _patch_wiki_page(monkeypatch, content: str):
    """Patch wiki_retriever.get_page to return a Page with the given full_text."""
    from backend.tools import wiki_tools
    mock_page = MagicMock()
    mock_page.path = "test/page.md"
    mock_page.title = "Test Page"
    mock_page.full_text = content
    monkeypatch.setattr(wiki_tools.wiki_retriever, "get_page", lambda path: mock_page)


def test_wiki_read_page_returns_full_content_by_default(monkeypatch):
    """Backwards-compat: no limit specified → return the full page exactly
    like pre-G20. New fields are additive."""
    from backend.tools.wiki_tools import _wiki_read_page_handler
    _patch_wiki_page(monkeypatch, "Full page content " * 100)
    result = _wiki_read_page_handler({"path": "test/page.md"})

    assert result["content"] == "Full page content " * 100
    assert result["total_length"] == len("Full page content " * 100)
    assert result["has_more"] is False
    assert result["next_offset"] is None
    assert result["offset"] == 0


def test_wiki_read_page_with_limit_first_chunk(monkeypatch):
    """limit=100 returns first 100 chars, has_more=True, next_offset=100."""
    from backend.tools.wiki_tools import _wiki_read_page_handler
    _patch_wiki_page(monkeypatch, "x" * 500)
    result = _wiki_read_page_handler({"path": "test/page.md", "limit": 100})

    assert len(result["content"]) == 100
    assert result["total_length"] == 500
    assert result["has_more"] is True
    assert result["next_offset"] == 100


def test_wiki_read_page_with_offset_midway(monkeypatch):
    """offset=200, limit=100 returns chars 200..300."""
    from backend.tools.wiki_tools import _wiki_read_page_handler
    content = "".join(str(i % 10) for i in range(500))
    _patch_wiki_page(monkeypatch, content)
    result = _wiki_read_page_handler({"path": "test/page.md", "offset": 200, "limit": 100})

    assert result["content"] == content[200:300]
    assert result["has_more"] is True
    assert result["next_offset"] == 300


def test_wiki_read_page_with_offset_past_end_returns_empty(monkeypatch):
    """Offset past end → empty content, has_more=False."""
    from backend.tools.wiki_tools import _wiki_read_page_handler
    _patch_wiki_page(monkeypatch, "short content")
    result = _wiki_read_page_handler({"path": "test/page.md", "offset": 1000, "limit": 100})

    assert result["content"] == ""
    assert result["total_length"] == len("short content")
    assert result["has_more"] is False


def test_wiki_read_page_backwards_compat_caller_reading_only_content(monkeypatch):
    """Callers that read only `content` (e.g. existing UI code) keep working
    — `content` is still the full page text when no limit is set."""
    from backend.tools.wiki_tools import _wiki_read_page_handler
    expected = "**Page Title**\n\nFull body here with some markdown."
    _patch_wiki_page(monkeypatch, expected)
    result = _wiki_read_page_handler({"path": "test/page.md"})
    assert result["content"] == expected
