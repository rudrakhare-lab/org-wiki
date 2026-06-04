"""Tests for wiki write tools — create, edit, append, update_frontmatter, rebuild_index."""
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


@pytest.fixture
def wiki_tmp(tmp_path):
    """Return a tmp dir that acts as WIKI_ROOT, with wiki/ subdirs pre-created."""
    (tmp_path / "wiki" / "modules").mkdir(parents=True)
    (tmp_path / "wiki" / "entities").mkdir(parents=True)
    (tmp_path / "wiki" / "sources").mkdir(parents=True)
    return tmp_path


# ── wiki_create_page ─────────────────────────────────────────────────────────

def test_create_page_creates_file(wiki_tmp):
    from backend.tools.wiki_write_tools import _wiki_create_page_handler

    with patch("backend.tools.wiki_write_tools.WIKI_ROOT", str(wiki_tmp)):
        result = _wiki_create_page_handler({
            "path": "wiki/modules/test-module.md",
            "frontmatter": {"type": "module", "status": "active"},
            "body": "## Overview\nThis is a test module.",
        })

    assert result.get("created") is True
    written = (wiki_tmp / "wiki" / "modules" / "test-module.md").read_text()
    assert "type: module" in written
    assert "## Overview" in written


def test_create_page_refuses_overwrite(wiki_tmp):
    from backend.tools.wiki_write_tools import _wiki_create_page_handler

    existing = wiki_tmp / "wiki" / "modules" / "existing.md"
    existing.write_text("existing content")

    with patch("backend.tools.wiki_write_tools.WIKI_ROOT", str(wiki_tmp)):
        result = _wiki_create_page_handler({
            "path": "wiki/modules/existing.md",
            "frontmatter": {},
            "body": "new content",
        })

    assert "error" in result
    assert result.get("code") == "already_exists"
    assert existing.read_text() == "existing content"


def test_create_page_rejects_path_outside_wiki(wiki_tmp):
    from backend.tools.wiki_write_tools import _wiki_create_page_handler

    with patch("backend.tools.wiki_write_tools.WIKI_ROOT", str(wiki_tmp)):
        result = _wiki_create_page_handler({
            "path": "../../etc/passwd",
            "frontmatter": {},
            "body": "evil",
        })

    assert "error" in result
    assert result.get("code") == "invalid_path"


# ── wiki_edit_page ───────────────────────────────────────────────────────────

def test_edit_page_replaces_unique_string(wiki_tmp):
    from backend.tools.wiki_write_tools import _wiki_edit_page_handler

    target = wiki_tmp / "wiki" / "modules" / "sso.md"
    target.write_text("---\ntype: module\n---\n## Overview\nOld content here.\n")

    with patch("backend.tools.wiki_write_tools.WIKI_ROOT", str(wiki_tmp)):
        result = _wiki_edit_page_handler({
            "path": "wiki/modules/sso.md",
            "old_str": "Old content here.",
            "new_str": "New content here.",
        })

    assert result.get("edited") is True
    assert "New content here." in target.read_text()
    assert "Old content here." not in target.read_text()


def test_edit_page_errors_if_old_str_not_found(wiki_tmp):
    from backend.tools.wiki_write_tools import _wiki_edit_page_handler

    target = wiki_tmp / "wiki" / "modules" / "sso.md"
    target.write_text("some content")

    with patch("backend.tools.wiki_write_tools.WIKI_ROOT", str(wiki_tmp)):
        result = _wiki_edit_page_handler({
            "path": "wiki/modules/sso.md",
            "old_str": "text that does not exist",
            "new_str": "replacement",
        })

    assert "error" in result
    assert result.get("code") == "not_found"


def test_edit_page_errors_if_old_str_not_unique(wiki_tmp):
    from backend.tools.wiki_write_tools import _wiki_edit_page_handler

    target = wiki_tmp / "wiki" / "modules" / "sso.md"
    target.write_text("repeat repeat")

    with patch("backend.tools.wiki_write_tools.WIKI_ROOT", str(wiki_tmp)):
        result = _wiki_edit_page_handler({
            "path": "wiki/modules/sso.md",
            "old_str": "repeat",
            "new_str": "once",
        })

    assert "error" in result
    assert result.get("code") == "ambiguous"


# ── wiki_append_section ──────────────────────────────────────────────────────

def test_append_section(wiki_tmp):
    from backend.tools.wiki_write_tools import _wiki_append_section_handler

    target = wiki_tmp / "wiki" / "modules" / "mod.md"
    target.write_text("## Overview\nExisting content.\n")

    with patch("backend.tools.wiki_write_tools.WIKI_ROOT", str(wiki_tmp)):
        result = _wiki_append_section_handler({
            "path": "wiki/modules/mod.md",
            "heading": "New Section",
            "content": "Some new content.",
        })

    assert result.get("appended") is True
    text = target.read_text()
    assert "## New Section" in text
    assert "Some new content." in text


def test_append_section_errors_if_heading_exists(wiki_tmp):
    from backend.tools.wiki_write_tools import _wiki_append_section_handler

    target = wiki_tmp / "wiki" / "modules" / "mod.md"
    target.write_text("## Overview\nExisting.\n\n## Existing Section\nContent.\n")

    with patch("backend.tools.wiki_write_tools.WIKI_ROOT", str(wiki_tmp)):
        result = _wiki_append_section_handler({
            "path": "wiki/modules/mod.md",
            "heading": "Existing Section",
            "content": "duplicate",
        })

    assert "error" in result
    assert result.get("code") == "heading_exists"


# ── wiki_update_frontmatter ──────────────────────────────────────────────────

def test_update_frontmatter_appends_to_list(wiki_tmp):
    from backend.tools.wiki_write_tools import _wiki_update_frontmatter_handler

    target = wiki_tmp / "wiki" / "modules" / "mod.md"
    target.write_text("---\ntype: module\nused_by: []\n---\n## Body\n")

    with patch("backend.tools.wiki_write_tools.WIKI_ROOT", str(wiki_tmp)):
        result = _wiki_update_frontmatter_handler({
            "path": "wiki/modules/mod.md",
            "field": "used_by",
            "value": "visitor-management",
        })

    assert result.get("updated") is True
    assert "visitor-management" in target.read_text()


def test_update_frontmatter_no_duplicate(wiki_tmp):
    from backend.tools.wiki_write_tools import _wiki_update_frontmatter_handler

    target = wiki_tmp / "wiki" / "modules" / "mod.md"
    target.write_text("---\ntype: module\nused_by: [visitor-management]\n---\n")

    with patch("backend.tools.wiki_write_tools.WIKI_ROOT", str(wiki_tmp)):
        _wiki_update_frontmatter_handler({
            "path": "wiki/modules/mod.md",
            "field": "used_by",
            "value": "visitor-management",
        })

    text = target.read_text()
    assert text.count("visitor-management") == 1
