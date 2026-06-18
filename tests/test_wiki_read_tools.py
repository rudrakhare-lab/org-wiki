"""Tests for wiki_list_pages and wiki_check_duplicate tools.

Both handlers resolve the ACTIVE agent's wiki_dir (via agent_context) and validate
categories against backend.wiki_schema.ALL_CATEGORIES, so these tests point the
active agent at a temp dir rather than patching a module-level WIKI_ROOT.
"""
import types

from backend import agent_context


def _point_agent_at(monkeypatch, wiki_dir, schema_kind="workinsync"):
    fake = types.SimpleNamespace(id="t", schema_kind=schema_kind, wiki_dir=wiki_dir)
    monkeypatch.setattr(
        agent_context, "get_current_agent", lambda: fake, raising=False
    )


def _write_page(wiki_dir, rel_path, title="Foo"):
    p = wiki_dir / rel_path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(f"# {title}\n", encoding="utf-8")
    return p


def test_list_pages_modules(tmp_path, monkeypatch):
    from backend.tools.wiki_read_tools import _wiki_list_pages_handler

    wiki = tmp_path / "wiki"
    _write_page(wiki, "modules/visitor-management.md", "Visitor Management")
    _point_agent_at(monkeypatch, wiki)

    result = _wiki_list_pages_handler({"category": "modules"})

    assert result["total"] == 1
    assert result["pages"][0]["path"] == "modules/visitor-management.md"
    assert result["pages"][0]["slug"] == "visitor-management"
    assert result["pages"][0]["title"] == "Visitor Management"


def test_list_pages_all(tmp_path, monkeypatch):
    from backend.tools.wiki_read_tools import _wiki_list_pages_handler

    wiki = tmp_path / "wiki"
    for cat in ["modules", "entities", "sources"]:
        _write_page(wiki, f"{cat}/foo.md", "Foo")
    _point_agent_at(monkeypatch, wiki)

    result = _wiki_list_pages_handler({})

    assert result["total"] == 3


def test_list_pages_filters_by_category(tmp_path, monkeypatch):
    from backend.tools.wiki_read_tools import _wiki_list_pages_handler

    wiki = tmp_path / "wiki"
    _write_page(wiki, "modules/sso.md", "SSO")
    _write_page(wiki, "entities/user.md", "User")
    _point_agent_at(monkeypatch, wiki)

    result = _wiki_list_pages_handler({"category": "modules"})

    assert result["total"] == 1
    assert result["pages"][0]["slug"] == "sso"


def test_list_pages_unknown_category(tmp_path, monkeypatch):
    from backend.tools.wiki_read_tools import _wiki_list_pages_handler

    wiki = tmp_path / "wiki"
    wiki.mkdir(parents=True)
    _point_agent_at(monkeypatch, wiki)

    result = _wiki_list_pages_handler({"category": "nonexistent"})

    assert "error" in result
    assert result["code"] == "unknown_category"


def test_check_duplicate_exists(tmp_path, monkeypatch):
    from backend.tools.wiki_read_tools import _wiki_check_duplicate_handler

    wiki = tmp_path / "wiki"
    _write_page(wiki, "modules/visitor-management.md", "Visitor Management")
    _point_agent_at(monkeypatch, wiki)

    result = _wiki_check_duplicate_handler(
        {"slug": "visitor-management", "category": "modules"}
    )

    assert result["exists"] is True
    assert "visitor-management.md" in result["path"]


def test_check_duplicate_not_exists(tmp_path, monkeypatch):
    from backend.tools.wiki_read_tools import _wiki_check_duplicate_handler

    wiki = tmp_path / "wiki"
    wiki.mkdir(parents=True)
    _point_agent_at(monkeypatch, wiki)

    result = _wiki_check_duplicate_handler(
        {"slug": "brand-new-module", "category": "modules"}
    )

    assert result["exists"] is False
    assert result["path"] is None
