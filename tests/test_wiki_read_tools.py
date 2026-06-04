"""Tests for wiki_list_pages and wiki_check_duplicate tools."""
import pytest
from unittest.mock import patch, MagicMock


def _make_page(path: str, title: str) -> MagicMock:
    """Create a mock WikiPage with path and title set."""
    p = MagicMock()
    p.path = path
    p.title = title
    return p


def test_list_pages_modules():
    from backend.tools.wiki_read_tools import _wiki_list_pages_handler

    with patch("backend.tools.wiki_read_tools.wiki_retriever") as mock_r:
        page = _make_page("modules/visitor-management.md", "Visitor Management")
        mock_r.all_paths.return_value = ["modules/visitor-management.md"]
        mock_r.get_page.return_value = page

        result = _wiki_list_pages_handler({"category": "modules"})

    assert result["total"] == 1
    assert result["pages"][0]["path"] == "modules/visitor-management.md"
    assert result["pages"][0]["slug"] == "visitor-management"


def test_list_pages_all():
    from backend.tools.wiki_read_tools import _wiki_list_pages_handler

    paths = [f"{cat}/foo.md" for cat in ["modules", "entities", "sources"]]
    pages = {p: _make_page(p, "Foo") for p in paths}

    with patch("backend.tools.wiki_read_tools.wiki_retriever") as mock_r:
        mock_r.all_paths.return_value = paths
        mock_r.get_page.side_effect = lambda p: pages.get(p)

        result = _wiki_list_pages_handler({})

    assert result["total"] == 3


def test_list_pages_filters_by_category():
    from backend.tools.wiki_read_tools import _wiki_list_pages_handler

    all_paths = ["modules/sso.md", "entities/user.md"]
    pages = {
        "modules/sso.md": _make_page("modules/sso.md", "SSO"),
        "entities/user.md": _make_page("entities/user.md", "User"),
    }

    with patch("backend.tools.wiki_read_tools.wiki_retriever") as mock_r:
        mock_r.all_paths.return_value = all_paths
        mock_r.get_page.side_effect = lambda p: pages.get(p)

        result = _wiki_list_pages_handler({"category": "modules"})

    assert result["total"] == 1
    assert result["pages"][0]["slug"] == "sso"


def test_list_pages_unknown_category():
    from backend.tools.wiki_read_tools import _wiki_list_pages_handler

    with patch("backend.tools.wiki_read_tools.wiki_retriever") as mock_r:
        mock_r.all_paths.return_value = []

        result = _wiki_list_pages_handler({"category": "nonexistent"})

    assert "error" in result
    assert result["code"] == "unknown_category"


def test_check_duplicate_exists():
    from backend.tools.wiki_read_tools import _wiki_check_duplicate_handler
    import tempfile, os

    with tempfile.TemporaryDirectory() as tmp:
        wiki_dir = os.path.join(tmp, "wiki", "modules")
        os.makedirs(wiki_dir)
        open(os.path.join(wiki_dir, "visitor-management.md"), "w").close()

        with patch("backend.tools.wiki_read_tools.WIKI_ROOT", tmp):
            result = _wiki_check_duplicate_handler(
                {"slug": "visitor-management", "category": "modules"}
            )

    assert result["exists"] is True
    assert "visitor-management.md" in result["path"]


def test_check_duplicate_not_exists():
    from backend.tools.wiki_read_tools import _wiki_check_duplicate_handler
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        with patch("backend.tools.wiki_read_tools.WIKI_ROOT", tmp):
            result = _wiki_check_duplicate_handler(
                {"slug": "brand-new-module", "category": "modules"}
            )

    assert result["exists"] is False
    assert result["path"] is None
