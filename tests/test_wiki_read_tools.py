"""Tests for wiki_list_pages and wiki_check_duplicate tools."""
import pytest
from unittest.mock import patch, MagicMock


def test_list_pages_modules():
    from backend.tools.wiki_read_tools import _wiki_list_pages_handler

    with patch("backend.tools.wiki_read_tools.wiki_retriever") as mock_r:
        mock_page = MagicMock()
        mock_page.path = "wiki/modules/visitor-management.md"
        mock_page.title = "Visitor Management"
        mock_r.all_pages.return_value = [mock_page]

        result = _wiki_list_pages_handler({"category": "modules"})

    assert result["total"] == 1
    assert result["pages"][0]["path"] == "wiki/modules/visitor-management.md"
    assert result["pages"][0]["slug"] == "visitor-management"


def test_list_pages_all():
    from backend.tools.wiki_read_tools import _wiki_list_pages_handler

    with patch("backend.tools.wiki_read_tools.wiki_retriever") as mock_r:
        pages = []
        for cat in ["modules", "entities", "sources"]:
            m = MagicMock()
            m.path = f"wiki/{cat}/foo.md"
            m.title = "Foo"
            pages.append(m)
        mock_r.all_pages.return_value = pages

        result = _wiki_list_pages_handler({})

    assert result["total"] == 3


def test_list_pages_filters_by_category():
    from backend.tools.wiki_read_tools import _wiki_list_pages_handler

    with patch("backend.tools.wiki_read_tools.wiki_retriever") as mock_r:
        module_page = MagicMock()
        module_page.path = "wiki/modules/sso.md"
        module_page.title = "SSO"
        entity_page = MagicMock()
        entity_page.path = "wiki/entities/user.md"
        entity_page.title = "User"
        mock_r.all_pages.return_value = [module_page, entity_page]

        result = _wiki_list_pages_handler({"category": "modules"})

    assert result["total"] == 1
    assert result["pages"][0]["slug"] == "sso"


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
