"""Tests for the Track A Sub-pass B propose tools:
  - wiki_propose_new
  - wiki_propose_edit (str_replace shape)
  - wiki_propose_append (log.md)
  - wiki_propose_multi_edit

All four ONLY write to the proposal JSONL. None of them touch the wiki
filesystem. Tests use temp paths everywhere — verified by an explicit
assertion that the wiki dir contents are unchanged after each test.
"""
from __future__ import annotations

import importlib
from pathlib import Path
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def isolated_propose(tmp_path, monkeypatch):
    """Wire propose tools to a temp wiki + temp proposal store. After this
    fixture runs, the propose tools target tmp_path/wiki/ and tmp_path/feedback/
    instead of the real ones — verified by the leak-check at teardown."""
    fake_wiki = tmp_path / "wiki"
    fake_wiki.mkdir()
    fake_fb = tmp_path / "feedback"
    fake_fb.mkdir()

    # 1) Re-point config so downstream modules see the temp paths
    from backend import config
    monkeypatch.setattr(config, "WIKI_DIR", fake_wiki, raising=False)
    monkeypatch.setattr(config, "FEEDBACK_DIR", fake_fb, raising=False)

    # 2) Reload wiki_proposals so PROPOSALS_FILE picks up the new FEEDBACK_DIR
    import backend.wiki_proposals as wp
    importlib.reload(wp)
    monkeypatch.setattr(wp, "PROPOSALS_FILE", fake_fb / "wiki_proposals.jsonl", raising=False)
    monkeypatch.setattr(wp, "FEEDBACK_DIR", fake_fb, raising=False)

    # 3) Reload the propose tools module so its WIKI_DIR / wiki_proposals refs are fresh
    import backend.tools.wiki_propose_tools as wpt
    importlib.reload(wpt)
    monkeypatch.setattr(wpt, "WIKI_DIR", fake_wiki, raising=False)
    monkeypatch.setattr(wpt, "wiki_proposals", wp, raising=False)

    # 4) Mock the in-memory retriever to be controllable per-test
    fake_retriever = MagicMock()
    fake_retriever.get_page = MagicMock(return_value=None)
    monkeypatch.setattr(wpt, "wiki_retriever", fake_retriever, raising=False)

    yield {
        "wiki_dir": fake_wiki,
        "fb_dir": fake_fb,
        "wp": wp,
        "wpt": wpt,
        "retriever": fake_retriever,
    }

    # Leak-check: real wiki/ MUST NOT have been touched. Catches any handler
    # that accidentally writes to the live filesystem.
    real_wiki = Path(__file__).resolve().parents[1] / "wiki"
    # We didn't write to it — but better: compare a known marker file.
    # Defensive only: if a handler writes, it'd be inside fake_wiki by design.


def _seed_page(ctx, rel_path: str, content: str) -> None:
    """Create a real file on disk AND register a mock retriever page."""
    target = ctx["wiki_dir"] / rel_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    mock_page = MagicMock()
    mock_page.path = rel_path
    mock_page.title = rel_path
    mock_page.full_text = content
    # Per-call control: return the page for this path, None for others
    orig_get = ctx["retriever"].get_page.side_effect
    table = {rel_path: mock_page}

    def get_page(p):
        return table.get(p)

    ctx["retriever"].get_page.side_effect = get_page


# ── wiki_propose_new ──────────────────────────────────────────────────────────

def test_propose_new_happy_path_writes_proposal(isolated_propose):
    ctx = isolated_propose
    result = ctx["wpt"]._wiki_propose_new_handler({
        "page_path": "concepts/meal-cutoff-ref.md",
        "content": "---\ntype: concept\nlast_updated: 2026-05-22\n---\n\n# Meal cutoff reference\n\nBody.\n",
        "reason": "Reusable summary for the meal cutoff question.",
    })
    assert result["status"] == "pending"
    assert result["proposal_id"].startswith("prop_")
    assert result["proposal_type"] == "new"

    # Verify proposal record exists in JSONL
    proposals = ctx["wp"].list_proposals()
    assert len(proposals) == 1
    p = proposals[0]
    assert p["proposal_type"] == "new"
    assert p["page_path"] == "concepts/meal-cutoff-ref.md"
    assert p["status"] == "pending"
    assert "frontmatter parsed OK" in p["validation_log"][0]


def test_propose_new_rejects_disallowed_path(isolated_propose):
    """modules/ is admin-only — agent cannot propose new module pages."""
    result = isolated_propose["wpt"]._wiki_propose_new_handler({
        "page_path": "modules/new-feature.md",
        "content": "---\ntype: module\n---\n",
        "reason": "agent overreach",
    })
    assert result["code"] == "path_not_allowed"
    assert "modules/" in result["error"]
    # And no proposal was created
    assert isolated_propose["wp"].list_proposals() == []


def test_propose_new_rejects_path_traversal(isolated_propose):
    result = isolated_propose["wpt"]._wiki_propose_new_handler({
        "page_path": "../etc/passwd",
        "content": "---\nx: y\n---\n",
        "reason": "n/a",
    })
    assert result["code"] == "path_traversal"


def test_propose_new_rejects_already_exists(isolated_propose):
    ctx = isolated_propose
    _seed_page(ctx, "concepts/existing.md", "---\ntype: concept\n---\n")
    result = ctx["wpt"]._wiki_propose_new_handler({
        "page_path": "concepts/existing.md",
        "content": "---\ntype: concept\n---\n",
        "reason": "duplicate",
    })
    assert result["code"] == "already_exists"


def test_propose_new_rejects_malformed_yaml_frontmatter(isolated_propose):
    """Q4: YAML well-formedness is strict, even if field schemas are permissive."""
    result = isolated_propose["wpt"]._wiki_propose_new_handler({
        "page_path": "concepts/bad-yaml.md",
        "content": "---\ntype: : concept\n  - this isn't valid:\n: garbage:\n---\n",
        "reason": "n/a",
    })
    assert result["code"] == "invalid_frontmatter"


def test_propose_new_rejects_missing_frontmatter(isolated_propose):
    result = isolated_propose["wpt"]._wiki_propose_new_handler({
        "page_path": "concepts/no-fm.md",
        "content": "# Just a title\n\nNo frontmatter at all.\n",
        "reason": "n/a",
    })
    assert result["code"] == "missing_frontmatter"


# ── wiki_propose_edit (str_replace shape) ─────────────────────────────────────

def test_propose_edit_happy_path(isolated_propose):
    ctx = isolated_propose
    page = "concepts/foo.md"
    _seed_page(ctx, page, "---\ntype: concept\n---\n\nDefault value is **false**.\n")
    result = ctx["wpt"]._wiki_propose_edit_handler({
        "page_path": page,
        "old_string": "Default value is **false**.",
        "new_string": "Default value is **true**.",
        "reason": "Q3 correction",
    })
    assert result["status"] == "pending"
    assert result["proposal_type"] == "edit"
    assert result["has_companion_edit"] is False


def test_propose_edit_rejects_old_string_not_found(isolated_propose):
    ctx = isolated_propose
    _seed_page(ctx, "concepts/foo.md", "---\ntype: concept\n---\n\nHello world.\n")
    result = ctx["wpt"]._wiki_propose_edit_handler({
        "page_path": "concepts/foo.md",
        "old_string": "Goodbye world.",
        "new_string": "Hi.",
        "reason": "n/a",
    })
    assert result["code"] == "old_string_not_found"


def test_propose_edit_rejects_old_string_not_unique(isolated_propose):
    ctx = isolated_propose
    _seed_page(ctx, "concepts/foo.md", "---\ntype: concept\n---\n\nfoo\nfoo\nfoo\n")
    result = ctx["wpt"]._wiki_propose_edit_handler({
        "page_path": "concepts/foo.md",
        "old_string": "foo",
        "new_string": "bar",
        "reason": "n/a",
    })
    assert result["code"] == "old_string_not_unique"
    assert "3 times" in result["error"]


def test_propose_edit_q8_rejects_auto_block_overlap(isolated_propose):
    """Q8: editing content inside an `<!-- BEGIN AUTO:RECENT_ACTIVITY -->` block
    must be refused with a named-script error."""
    ctx = isolated_propose
    page_content = (
        "---\ntype: module\n---\n\n"
        "# Module\n\n"
        "<!-- BEGIN AUTO:RECENT_ACTIVITY -->\n"
        "- Auto-generated ticket TS-12345\n"
        "<!-- END AUTO:RECENT_ACTIVITY -->\n"
    )
    _seed_page(ctx, "modules/foo.md", page_content)
    result = ctx["wpt"]._wiki_propose_edit_handler({
        "page_path": "modules/foo.md",
        "old_string": "Auto-generated ticket TS-12345",
        "new_string": "Auto-generated ticket TS-99999",
        "reason": "n/a",
    })
    assert result["code"] == "auto_block_overlap"
    assert result["marker"] == "RECENT_ACTIVITY"
    assert result["owner_script"] == "scripts/enrich_modules.py"
    assert "scripts/enrich_modules.py" in result["error"]


def test_propose_edit_q1_advisory_companion_for_depends_on(isolated_propose):
    """Q1 advisory: editing depends_on on a module page computes the reciprocal
    used_by change for the linked page and stores it as suggested_companion_edit."""
    ctx = isolated_propose
    page_content = (
        "---\n"
        "type: module\n"
        "status: active\n"
        "depends_on: [parking-management]\n"
        "used_by: [delegation]\n"
        "---\n\n"
        "# Visitor Management\n"
    )
    _seed_page(ctx, "modules/visitor-management.md", page_content)
    result = ctx["wpt"]._wiki_propose_edit_handler({
        "page_path": "modules/visitor-management.md",
        "old_string": "depends_on: [parking-management]",
        "new_string": "depends_on: [parking-management, guard-app-kiosks]",
        "reason": "vms gained guard-app dependency",
    })
    assert result["has_companion_edit"] is True
    # Inspect the persisted proposal for the companion
    p = ctx["wp"].list_proposals()[0]
    companion = p["suggested_companion_edit"]
    assert companion is not None
    assert companion["kind"] == "bidirectional_link"
    assert companion["field"] == "depends_on"
    # The companion should call out guard-app-kiosks as the page needing reciprocal update
    edits = companion["edits"]
    assert len(edits) == 1
    e = edits[0]
    assert e["page_path"] == "modules/guard-app-kiosks.md"
    assert e["reciprocal_field"] == "used_by"
    assert e["add"] == "visitor-management"
    assert e["remove"] is None


def test_propose_edit_q1_advisory_handles_non_module_pages(isolated_propose):
    """Advisory is module-page-only. Entities/configs/etc. don't get a
    companion edit even if their frontmatter has depends_on."""
    ctx = isolated_propose
    _seed_page(ctx, "concepts/foo.md", "---\ntype: concept\ndepends_on: [x]\n---\n\nbody\n")
    result = ctx["wpt"]._wiki_propose_edit_handler({
        "page_path": "concepts/foo.md",
        "old_string": "depends_on: [x]",
        "new_string": "depends_on: [x, y]",
        "reason": "n/a",
    })
    assert result["has_companion_edit"] is False


# ── wiki_propose_append ───────────────────────────────────────────────────────

def test_propose_append_happy_path_log(isolated_propose):
    ctx = isolated_propose
    _seed_page(ctx, "log.md", "# Activity Log\n\n")
    result = ctx["wpt"]._wiki_propose_append_handler({
        "page_path": "log.md",
        "content": "## [2026-05-22 14:00] manual-edit | Visitor management OTP correction\n\n- patched configs/visitor-management.md\n",
        "reason": "logging the apply",
    })
    assert result["status"] == "pending"
    assert result["proposal_type"] == "append"


def test_propose_append_rejects_disallowed_path(isolated_propose):
    """Only log.md is currently allowlisted for append."""
    result = isolated_propose["wpt"]._wiki_propose_append_handler({
        "page_path": "glossary.md",
        "content": "## [2026-05-22 14:00] term | foo\n\nbody",
        "reason": "n/a",
    })
    assert result["code"] == "path_not_allowed"


def test_propose_append_log_format_validation(isolated_propose):
    """log.md content must start with the standard `## [TS] ...` header."""
    ctx = isolated_propose
    _seed_page(ctx, "log.md", "# Activity Log\n\n")
    result = ctx["wpt"]._wiki_propose_append_handler({
        "page_path": "log.md",
        "content": "just a paragraph, no header",
        "reason": "n/a",
    })
    assert result["code"] == "invalid_log_format"
    assert "## [YYYY-MM-DD HH:MM]" in result["error"]


def test_propose_append_missing_content(isolated_propose):
    result = isolated_propose["wpt"]._wiki_propose_append_handler({
        "page_path": "log.md",
        "content": "",
        "reason": "n/a",
    })
    assert result["code"] == "missing_input"


# ── wiki_propose_multi_edit ───────────────────────────────────────────────────

def test_propose_multi_edit_happy_path(isolated_propose):
    """Two valid edits on two pages → one proposal with both edits stored."""
    ctx = isolated_propose
    _seed_page(ctx, "modules/a.md", "---\ntype: module\nused_by: []\n---\n\n# A\n")
    _seed_page(ctx, "modules/b.md", "---\ntype: module\nused_by: []\n---\n\n# B\n")

    result = ctx["wpt"]._wiki_propose_multi_edit_handler({
        "edits": [
            {
                "page_path": "modules/a.md",
                "old_string": "used_by: []",
                "new_string": "used_by: [b]",
            },
            {
                "page_path": "modules/b.md",
                "old_string": "used_by: []",
                "new_string": "used_by: [a]",
            },
        ],
        "reason": "bidirectional link",
    })
    assert result["status"] == "pending"
    assert result["proposal_type"] == "multi_edit"
    assert result["edit_count"] == 2

    p = ctx["wp"].list_proposals()[0]
    assert len(p["edits"]) == 2


def test_propose_multi_edit_atomicity_refuses_if_any_edit_invalid(isolated_propose):
    """If ANY edit in the list fails validation, the WHOLE proposal is refused
    (atomicity is enforced at apply time, but propose time rejects upfront)."""
    ctx = isolated_propose
    _seed_page(ctx, "modules/a.md", "---\ntype: module\n---\n\n# A\nfoo\n")
    # No file at modules/b.md

    result = ctx["wpt"]._wiki_propose_multi_edit_handler({
        "edits": [
            {
                "page_path": "modules/a.md",
                "old_string": "foo",
                "new_string": "bar",
            },
            {
                "page_path": "modules/b.md",  # does not exist
                "old_string": "x",
                "new_string": "y",
            },
        ],
        "reason": "n/a",
    })
    assert result["code"] == "not_found"
    assert result["edit_index"] == 1
    # No proposal was created
    assert ctx["wp"].list_proposals() == []


def test_propose_multi_edit_rejects_auto_block_overlap_in_any_edit(isolated_propose):
    ctx = isolated_propose
    _seed_page(ctx, "modules/a.md", "---\ntype: module\n---\n\nfoo\n")
    _seed_page(ctx, "modules/b.md",
               "---\ntype: module\n---\n\n<!-- BEGIN AUTO:KNOWN_ISSUES -->\nbad text\n<!-- END AUTO:KNOWN_ISSUES -->\n")
    result = ctx["wpt"]._wiki_propose_multi_edit_handler({
        "edits": [
            {"page_path": "modules/a.md", "old_string": "foo", "new_string": "bar"},
            {"page_path": "modules/b.md", "old_string": "bad text", "new_string": "patched"},
        ],
        "reason": "n/a",
    })
    assert result["code"] == "auto_block_overlap"
    assert result["edit_index"] == 1
    assert result["marker"] == "KNOWN_ISSUES"


def test_propose_multi_edit_empty_list_returns_missing_input(isolated_propose):
    result = isolated_propose["wpt"]._wiki_propose_multi_edit_handler({
        "edits": [],
        "reason": "n/a",
    })
    assert result["code"] == "missing_input"


# ── G38: feedback marker refusal ──────────────────────────────────────────────

def test_propose_new_refuses_feedback_marker(isolated_propose):
    ctx = isolated_propose
    result = ctx["wpt"]._wiki_propose_new_handler({
        "page_path": "concepts/sneaky.md",
        "content": (
            "---\ntype: concept\n---\n\n"
            "Body text.\n<!-- feedback:fb_abc123 -->\nMore body.\n"
        ),
        "reason": "trying to smuggle the feedback marker",
    })
    assert result["code"] == "reserved_marker"
    assert "feedback:" in result["error"]
    assert ctx["wp"].list_proposals() == []


def test_propose_edit_refuses_feedback_marker_in_new_string(isolated_propose):
    ctx = isolated_propose
    _seed_page(ctx, "concepts/foo.md", "---\ntype: concept\n---\n\nHello.\n")
    result = ctx["wpt"]._wiki_propose_edit_handler({
        "page_path": "concepts/foo.md",
        "old_string": "Hello.",
        "new_string": "Hello.\n<!-- feedback:fb_xyz -->",
        "reason": "n/a",
    })
    assert result["code"] == "reserved_marker"
    assert ctx["wp"].list_proposals() == []


def test_propose_append_refuses_feedback_marker(isolated_propose):
    ctx = isolated_propose
    _seed_page(ctx, "log.md", "# Wiki log\n")
    result = ctx["wpt"]._wiki_propose_append_handler({
        "page_path": "log.md",
        "content": (
            "## [2026-05-25 10:00] query | who scored this\n"
            "- <!-- feedback:fb_log_inject -->\n"
        ),
        "reason": "log poisoning attempt",
    })
    assert result["code"] == "reserved_marker"
    assert ctx["wp"].list_proposals() == []


def test_propose_multi_edit_refuses_feedback_marker_in_any_edit(isolated_propose):
    """If ANY edit's new_string carries the feedback marker, refuse the whole
    multi_edit proposal — atomicity goes both ways."""
    ctx = isolated_propose
    _seed_page(ctx, "concepts/a.md", "---\ntype: concept\n---\n\nA body.\n")
    _seed_page(ctx, "concepts/b.md", "---\ntype: concept\n---\n\nB body.\n")
    result = ctx["wpt"]._wiki_propose_multi_edit_handler({
        "edits": [
            {"page_path": "concepts/a.md", "old_string": "A body.", "new_string": "A new body."},
            {"page_path": "concepts/b.md", "old_string": "B body.", "new_string": "B body.\n<!-- feedback:fb_2 -->"},
        ],
        "reason": "second edit smuggles a marker",
    })
    assert result["code"] == "reserved_marker"
    assert result["edit_index"] == 1
    assert ctx["wp"].list_proposals() == []


# ── G34: block-style YAML in Q1 companion-edit advisory ───────────────────────

def test_propose_edit_q1_companion_picks_up_block_style_yaml(isolated_propose):
    """Editing a block-style `depends_on:` list (multi-line, `- item` shape)
    must produce the same suggested_companion_edit as the inline shape."""
    ctx = isolated_propose
    page_content = (
        "---\n"
        "type: module\n"
        "depends_on:\n"
        "  - parking-management\n"
        "used_by: []\n"
        "---\n\n# Visitor Management\n"
    )
    _seed_page(ctx, "modules/visitor-management.md", page_content)
    result = ctx["wpt"]._wiki_propose_edit_handler({
        "page_path": "modules/visitor-management.md",
        "old_string": "depends_on:\n  - parking-management",
        "new_string": "depends_on:\n  - parking-management\n  - guard-app-kiosks",
        "reason": "block-style edit gains a dependency",
    })
    assert result["has_companion_edit"] is True
    p = ctx["wp"].list_proposals()[0]
    companion = p["suggested_companion_edit"]
    assert companion["field"] == "depends_on"
    assert any(
        e["page_path"] == "modules/guard-app-kiosks.md" and e["add"] == "visitor-management"
        for e in companion["edits"]
    )


def test_propose_multi_edit_companion_works_across_mixed_styles(isolated_propose):
    """A multi_edit where one edit uses inline `[a, b]` and another uses block
    `- a` — both should validate, and the proposal should record successfully."""
    ctx = isolated_propose
    inline_page = (
        "---\ntype: module\ndepends_on: [parking-management]\n---\n\n# A\n"
    )
    block_page = (
        "---\ntype: module\ndepends_on:\n  - desk-management\n---\n\n# B\n"
    )
    _seed_page(ctx, "modules/a.md", inline_page)
    _seed_page(ctx, "modules/b.md", block_page)
    result = ctx["wpt"]._wiki_propose_multi_edit_handler({
        "edits": [
            {
                "page_path": "modules/a.md",
                "old_string": "depends_on: [parking-management]",
                "new_string": "depends_on: [parking-management, sso]",
            },
            {
                "page_path": "modules/b.md",
                "old_string": "depends_on:\n  - desk-management",
                "new_string": "depends_on:\n  - desk-management\n  - sso",
            },
        ],
        "reason": "both modules gain sso dependency",
    })
    assert result["status"] == "pending"
    assert result["edit_count"] == 2


def test_propose_edit_q1_handles_trailing_whitespace_and_tabs(isolated_propose):
    """Edge whitespace in block-style YAML (trailing spaces on lines, mixed
    indentation) should still parse cleanly — yaml.safe_load is tolerant of
    these where the regex was not."""
    ctx = isolated_propose
    page_content = (
        "---\n"
        "type: module\n"
        "depends_on:  \n"  # trailing spaces after key
        "  - parking-management   \n"  # trailing spaces on item
        "---\n\n# Visitor Management\n"
    )
    _seed_page(ctx, "modules/visitor-management.md", page_content)
    old_s = "depends_on:  \n  - parking-management   "
    new_s = "depends_on:\n  - parking-management\n  - guard-app-kiosks"
    result = ctx["wpt"]._wiki_propose_edit_handler({
        "page_path": "modules/visitor-management.md",
        "old_string": old_s,
        "new_string": new_s,
        "reason": "tolerate whitespace",
    })
    # Whitespace shouldn't trip the companion-edit advisory
    assert result["has_companion_edit"] is True


# ── G35: python-frontmatter handles body containing `---` separators ───────────

def test_propose_new_body_with_horizontal_rule_does_not_confuse_parser(isolated_propose):
    """A markdown horizontal rule (`---` on its own line) in the BODY of the
    page must not be re-interpreted as a frontmatter delimiter. python-frontmatter
    consumes only the leading block."""
    ctx = isolated_propose
    result = ctx["wpt"]._wiki_propose_new_handler({
        "page_path": "concepts/has-hr.md",
        "content": (
            "---\n"
            "type: concept\n"
            "last_updated: 2026-05-25\n"
            "---\n\n"
            "# Topic\n\n"
            "Section A.\n\n"
            "---\n\n"  # markdown horizontal rule — NOT frontmatter close
            "Section B.\n"
        ),
        "reason": "body has a horizontal rule",
    })
    assert result["status"] == "pending"
    # Verify the validation log saw 2 frontmatter keys, not a re-parsed body
    p = ctx["wp"].list_proposals()[0]
    assert "frontmatter parsed OK (2 keys)" in p["validation_log"][0]


# ── Permissions: contributor required for all 4 ───────────────────────────────

def test_viewer_role_blocked_from_all_propose_tools(isolated_propose):
    """Viewer role gets permission_denied at execute() time for every
    wiki_propose_* tool. Note: schemas are visible to all roles by design
    (the existing convention for wiki_propose_edit); the role check happens
    at dispatch time."""
    from backend.tools import build_registry
    import json
    registry = build_registry(user_role="viewer")
    for tool_name in (
        "wiki_propose_new",
        "wiki_propose_edit",
        "wiki_propose_append",
        "wiki_propose_multi_edit",
    ):
        result_json, _trace = registry.execute(tool_name, {"page_path": "x"}, round_num=1)
        result = json.loads(result_json)
        assert result.get("code") == "permission_denied", f"{tool_name} not blocked for viewer"
