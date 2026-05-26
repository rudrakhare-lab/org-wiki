"""Tests for the wiki_grep tool (G13).

Mocks wiki_retriever.all_paths + get_page so tests run without the real
wiki index. Covers literal substring, regex, path glob filtering, and the
max_matches truncation.
"""
from __future__ import annotations

from unittest.mock import MagicMock


def _patch_wiki_index(monkeypatch, pages: dict[str, str]) -> None:
    """Install a fake wiki_retriever with the given {path: full_text} map."""
    from backend.tools import wiki_tools

    def fake_all_paths():
        return list(pages.keys())

    def fake_get_page(path):
        if path not in pages:
            return None
        p = MagicMock()
        p.path = path
        p.full_text = pages[path]
        return p

    monkeypatch.setattr(wiki_tools.wiki_retriever, "all_paths", fake_all_paths)
    monkeypatch.setattr(wiki_tools.wiki_retriever, "get_page", fake_get_page)


def test_wiki_grep_literal_match_returns_hits_with_context(monkeypatch):
    """Default literal (case-insensitive substring) match returns hits with
    line numbers and ±2 lines of context."""
    from backend.tools.wiki_tools import _wiki_grep_handler
    _patch_wiki_index(monkeypatch, {
        "modules/visitor-management.md": (
            "# Visitor Management\n\n"
            "Used for kiosks.\n"
            "Property: kioskRequireOTPBeforeRegister controls OTP flow.\n"
            "Default value: false.\n"
            "## Open questions\n"
        ),
        "configs/visitor.md": "(no relevant content here)\n",
    })
    result = _wiki_grep_handler({"pattern": "kioskRequireOTP"})

    assert result["total_matches"] == 1
    match = result["matches"][0]
    assert match["path"] == "modules/visitor-management.md"
    assert match["line_number"] == 4  # 1-indexed
    assert "kioskRequireOTPBeforeRegister" in match["line_text"]
    # Surrounding context includes ±2 lines
    assert "Used for kiosks." in match["surrounding_context"]
    assert "Default value: false." in match["surrounding_context"]


def test_wiki_grep_regex_matches_with_case_insensitive(monkeypatch):
    """regex=True compiles the pattern with re.IGNORECASE. Verify with a
    pattern that depends on case-insensitivity."""
    from backend.tools.wiki_tools import _wiki_grep_handler
    _patch_wiki_index(monkeypatch, {
        "a.md": "Says HELLO world\n",
        "b.md": "Says hello again\n",
        "c.md": "no greeting\n",
    })
    result = _wiki_grep_handler({"pattern": r"^says\s+hello", "regex": True})

    assert result["total_matches"] == 2
    paths = {m["path"] for m in result["matches"]}
    assert paths == {"a.md", "b.md"}


def test_wiki_grep_path_glob_filters(monkeypatch):
    """`path_glob` restricts the search to matching paths only."""
    from backend.tools.wiki_tools import _wiki_grep_handler
    _patch_wiki_index(monkeypatch, {
        "modules/auth.md": "secret token reference\n",
        "modules/billing.md": "secret token reference\n",
        "configs/auth.md": "secret token reference\n",
    })
    result = _wiki_grep_handler({"pattern": "secret token", "path_glob": "modules/*"})

    assert result["total_matches"] == 2
    paths = {m["path"] for m in result["matches"]}
    assert paths == {"modules/auth.md", "modules/billing.md"}


def test_wiki_grep_max_matches_truncates_with_has_more(monkeypatch):
    """When matches exceed `max_matches`, return up to the cap and set has_more=True."""
    from backend.tools.wiki_tools import _wiki_grep_handler
    pages = {f"p{i}.md": "needle\nneedle\nneedle\n" for i in range(20)}
    _patch_wiki_index(monkeypatch, pages)
    result = _wiki_grep_handler({"pattern": "needle", "max_matches": 5})

    assert result["total_matches"] == 5
    assert result["has_more"] is True


def test_wiki_grep_invalid_regex_returns_error_code(monkeypatch):
    """A malformed regex returns the structured error envelope, no crash."""
    from backend.tools.wiki_tools import _wiki_grep_handler
    _patch_wiki_index(monkeypatch, {"x.md": "anything\n"})
    result = _wiki_grep_handler({"pattern": "[unclosed", "regex": True})

    assert result["code"] == "invalid_pattern"
    assert "Invalid regex" in result["error"]


def test_wiki_grep_missing_pattern_returns_missing_input():
    from backend.tools.wiki_tools import _wiki_grep_handler
    assert _wiki_grep_handler({})["code"] == "missing_input"
    assert _wiki_grep_handler({"pattern": ""})["code"] == "missing_input"
    assert _wiki_grep_handler({"pattern": "   "})["code"] == "missing_input"
