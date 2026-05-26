"""Tests for backend.wiki_apply — the only path that mutates wiki/ on disk.

ALL tests use tmp_path. The real wiki/ is never touched. Coverage:
  - happy path per writer (new, edit, append, multi_edit)
  - stale-proposal detection per writer
  - lock-contention serialization (verifies flock holds under concurrency)
  - reindex called after apply
  - idempotency (already-applied → no rewrite)
  - multi_edit atomicity (validation failure stops everything)
  - multi_edit rollback (mid-write IO error restores pre-edit state)
  - multi_edit deadlock prevention (sorted path acquisition)
  - legacy_text refusal at /apply, success at /mark-applied
  - integration: propose → apply → file on disk → retriever sees it
"""
from __future__ import annotations

import importlib
import json
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def isolated_wiki(tmp_path, monkeypatch):
    """Redirect WIKI_DIR, FEEDBACK_DIR, and reload the relevant modules so
    the apply path operates on tmp_path, not the real wiki/."""
    fake_wiki = tmp_path / "wiki"
    fake_wiki.mkdir()
    fake_fb = tmp_path / "feedback"
    fake_fb.mkdir()

    from backend import config
    monkeypatch.setattr(config, "WIKI_DIR", fake_wiki, raising=False)
    monkeypatch.setattr(config, "FEEDBACK_DIR", fake_fb, raising=False)

    # Reload wiki_proposals and wiki_apply so their module-level path
    # references pick up the patched config.
    import backend.wiki_proposals as wp
    importlib.reload(wp)
    monkeypatch.setattr(wp, "PROPOSALS_FILE", fake_fb / "wiki_proposals.jsonl", raising=False)
    monkeypatch.setattr(wp, "FEEDBACK_DIR", fake_fb, raising=False)

    import backend.wiki_apply as wa
    importlib.reload(wa)
    monkeypatch.setattr(wa, "WIKI_DIR", fake_wiki, raising=False)

    import backend.admin_api as adm
    importlib.reload(adm)

    return {"wiki_dir": fake_wiki, "fb_dir": fake_fb, "wp": wp, "wa": wa, "adm": adm}


def _new_proposal_dict(**overrides) -> dict:
    """Build a minimal valid proposal record for direct writer testing."""
    base = {
        "id": "prop_test1",
        "proposal_type": "new",
        "page_path": "concepts/test.md",
        "content": "---\ntype: concept\n---\n\n# Test\n",
        "submitter_email": "agent",
        "answer_id": None,
        "reason": "test",
        "status": "pending",
        "validation_log": [],
        "suggested_companion_edit": None,
        "admin_note": None,
        "created_at": "2026-05-22T10:00:00+00:00",
        "resolved_at": None,
        "applied_at": None,
        "applied_by": None,
    }
    base.update(overrides)
    return base


# ──────────────────────────────────────────────────────────────────────────────
# Writer 1: apply_new
# ──────────────────────────────────────────────────────────────────────────────

def test_apply_new_happy_path(isolated_wiki):
    ctx = isolated_wiki
    prop = _new_proposal_dict(
        proposal_type="new",
        page_path="concepts/test.md",
        content="---\ntype: concept\n---\n\n# Test page\n",
    )
    result = ctx["wa"].apply_new(prop)
    assert result["success"] is True
    assert result["files_written"] == ["concepts/test.md"]
    target = ctx["wiki_dir"] / "concepts" / "test.md"
    assert target.is_file()
    assert target.read_text() == "---\ntype: concept\n---\n\n# Test page\n"


def test_apply_new_stale_proposal_when_file_exists(isolated_wiki):
    """If the file was created between propose and apply, refuse."""
    ctx = isolated_wiki
    (ctx["wiki_dir"] / "concepts").mkdir()
    target = ctx["wiki_dir"] / "concepts" / "existing.md"
    target.write_text("---\ntype: concept\n---\n\nalready here\n")

    prop = _new_proposal_dict(
        proposal_type="new",
        page_path="concepts/existing.md",
        content="---\ntype: concept\n---\n\n# New\n",
    )
    result = ctx["wa"].apply_new(prop)
    assert result["success"] is False
    assert result["code"] == "stale_proposal"


def test_apply_new_path_traversal_refused(isolated_wiki):
    ctx = isolated_wiki
    prop = _new_proposal_dict(
        proposal_type="new",
        page_path="../etc/passwd",
        content="---\nx: y\n---\n",
    )
    result = ctx["wa"].apply_new(prop)
    assert result["success"] is False
    assert result["code"] == "path_traversal"


# ──────────────────────────────────────────────────────────────────────────────
# Writer 2: apply_edit
# ──────────────────────────────────────────────────────────────────────────────

def _seed_file(ctx, rel: str, content: str) -> Path:
    target = ctx["wiki_dir"] / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content)
    return target


def test_apply_edit_happy_path(isolated_wiki):
    ctx = isolated_wiki
    target = _seed_file(ctx, "concepts/foo.md", "---\ntype: concept\n---\n\nDefault is **false**.\n")
    prop = _new_proposal_dict(
        proposal_type="edit",
        page_path="concepts/foo.md",
        old_string="Default is **false**.",
        new_string="Default is **true**.",
    )
    result = ctx["wa"].apply_edit(prop)
    assert result["success"] is True
    assert target.read_text() == "---\ntype: concept\n---\n\nDefault is **true**.\n"


def test_apply_edit_stale_when_old_string_missing(isolated_wiki):
    """File changed between propose and apply — old_string no longer present."""
    ctx = isolated_wiki
    _seed_file(ctx, "concepts/foo.md", "---\ntype: concept\n---\n\nDefault is **true**.\n")
    prop = _new_proposal_dict(
        proposal_type="edit",
        page_path="concepts/foo.md",
        old_string="Default is **false**.",  # no longer in file
        new_string="Default is **true**.",
    )
    result = ctx["wa"].apply_edit(prop)
    assert result["success"] is False
    assert result["code"] == "stale_proposal"
    assert "no longer found" in result["message"]


def test_apply_edit_stale_when_old_string_non_unique(isolated_wiki):
    """File changed and old_string now matches multiple places."""
    ctx = isolated_wiki
    _seed_file(ctx, "concepts/foo.md", "foo\nfoo\nfoo\n")
    prop = _new_proposal_dict(
        proposal_type="edit",
        page_path="concepts/foo.md",
        old_string="foo",
        new_string="bar",
    )
    result = ctx["wa"].apply_edit(prop)
    assert result["success"] is False
    assert result["code"] == "stale_proposal"
    assert "3 times" in result["message"]


def test_apply_edit_file_missing(isolated_wiki):
    ctx = isolated_wiki
    prop = _new_proposal_dict(
        proposal_type="edit",
        page_path="concepts/never_existed.md",
        old_string="x",
        new_string="y",
    )
    result = ctx["wa"].apply_edit(prop)
    assert result["success"] is False
    assert result["code"] == "stale_proposal"
    assert "no longer exists" in result["message"]


# ──────────────────────────────────────────────────────────────────────────────
# Writer 3: apply_append
# ──────────────────────────────────────────────────────────────────────────────

def test_apply_append_happy_path_log(isolated_wiki):
    ctx = isolated_wiki
    target = _seed_file(ctx, "log.md", "# Activity Log\n\nExisting entry.\n")
    prop = _new_proposal_dict(
        proposal_type="append",
        page_path="log.md",
        content="## [2026-05-22 14:00] feedback-apply | x\n\n- patched foo.md\n",
    )
    result = ctx["wa"].apply_append(prop)
    assert result["success"] is True
    final = target.read_text()
    assert final.startswith("# Activity Log\n\nExisting entry.\n")
    assert "## [2026-05-22 14:00] feedback-apply | x" in final


def test_apply_append_file_missing(isolated_wiki):
    ctx = isolated_wiki
    prop = _new_proposal_dict(
        proposal_type="append",
        page_path="log.md",
        content="## [2026-05-22 14:00] x | y\n",
    )
    result = ctx["wa"].apply_append(prop)
    assert result["success"] is False
    assert result["code"] == "stale_proposal"


# ──────────────────────────────────────────────────────────────────────────────
# Writer 4: apply_multi_edit
# ──────────────────────────────────────────────────────────────────────────────

def test_apply_multi_edit_happy_path(isolated_wiki):
    ctx = isolated_wiki
    _seed_file(ctx, "modules/a.md", "---\ntype: module\nused_by: []\n---\n")
    _seed_file(ctx, "modules/b.md", "---\ntype: module\nused_by: []\n---\n")
    prop = _new_proposal_dict(
        proposal_type="multi_edit",
        edits=[
            {"page_path": "modules/a.md", "old_string": "used_by: []", "new_string": "used_by: [b]"},
            {"page_path": "modules/b.md", "old_string": "used_by: []", "new_string": "used_by: [a]"},
        ],
    )
    result = ctx["wa"].apply_multi_edit(prop)
    assert result["success"] is True
    assert result["rollback_status"] == "clean"
    assert set(result["files_written"]) == {"modules/a.md", "modules/b.md"}
    assert "used_by: [b]" in (ctx["wiki_dir"] / "modules" / "a.md").read_text()
    assert "used_by: [a]" in (ctx["wiki_dir"] / "modules" / "b.md").read_text()


def test_apply_multi_edit_all_or_none_validation(isolated_wiki):
    """If ANY edit fails Pass 1 validation, no file is touched. The first edit
    is fine, but the second one's old_string is stale."""
    ctx = isolated_wiki
    a_initial = "---\ntype: module\n---\n\nfoo\n"
    b_initial = "---\ntype: module\n---\n\nbaz\n"  # 'bar' is NOT in this file
    _seed_file(ctx, "modules/a.md", a_initial)
    _seed_file(ctx, "modules/b.md", b_initial)
    prop = _new_proposal_dict(
        proposal_type="multi_edit",
        edits=[
            {"page_path": "modules/a.md", "old_string": "foo", "new_string": "FOO"},
            {"page_path": "modules/b.md", "old_string": "bar", "new_string": "BAR"},  # stale
        ],
    )
    result = ctx["wa"].apply_multi_edit(prop)
    assert result["success"] is False
    assert result["code"] == "stale_proposal"
    assert result["edit_index"] == 1
    # Critical: NEITHER file is touched
    assert (ctx["wiki_dir"] / "modules" / "a.md").read_text() == a_initial
    assert (ctx["wiki_dir"] / "modules" / "b.md").read_text() == b_initial


def test_apply_multi_edit_rollback_on_write_failure(isolated_wiki, monkeypatch):
    """If a write succeeds for edit 1 but fails for edit 2, rollback restores
    edit 1's original content.

    FRAGILE-TEST WARNING: This test patches `Path.write_text` to inject a
    failure on the second file's write. Inside `apply_multi_edit`, both the
    happy-path write AND the rollback use `target.write_text(...)` via the
    Path object, so the patched function intercepts BOTH. The rollback path
    deliberately doesn't go through `locked_write`'s `fh.write` for restore
    today — IF SOMEONE REFACTORS the rollback path to use `fh.write` via a
    file handle (which would NOT be intercepted by a Path.write_text patch),
    this test will SILENTLY pass even though rollback no longer fires
    correctly. Defensive: if you touch _rollback() in wiki_apply.py, audit
    this test and verify the failure-injection still reaches the rollback
    write path."""
    ctx = isolated_wiki
    a_initial = "foo content here for edit 1"
    b_initial = "bar content here for edit 2"
    _seed_file(ctx, "modules/a.md", a_initial)
    _seed_file(ctx, "modules/b.md", b_initial)
    prop = _new_proposal_dict(
        proposal_type="multi_edit",
        edits=[
            {"page_path": "modules/a.md", "old_string": "foo content", "new_string": "FOO CONTENT"},
            {"page_path": "modules/b.md", "old_string": "bar content", "new_string": "BAR CONTENT"},
        ],
    )

    # Inject a write failure on the SECOND file by patching write_text on
    # that specific path. We let the first write succeed normally so rollback
    # has something to restore.
    original_write = Path.write_text
    a_path = ctx["wiki_dir"] / "modules" / "a.md"
    b_path = ctx["wiki_dir"] / "modules" / "b.md"
    state = {"first_a_write": True}

    def patched_write(self, *args, **kwargs):
        # Allow the very first write to A (the actual edit) to succeed
        # but fail any write to B that isn't the rollback restore.
        if self == b_path and state["first_a_write"]:
            # First write attempt to B → fail
            state["first_a_write"] = False
            raise OSError("disk full (simulated)")
        return original_write(self, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", patched_write)

    result = ctx["wa"].apply_multi_edit(prop)
    assert result["success"] is False
    assert result["code"] == "write_io_error"
    assert result["rollback_status"] == "clean"
    # Rollback restored A's pre-edit content
    assert a_path.read_text() == a_initial
    # B was never successfully written
    assert b_path.read_text() == b_initial


def test_apply_multi_edit_deadlock_prevention_sorted_paths(isolated_wiki):
    """Two threads multi-editing files A and B in different declared orders
    must not deadlock — internal sort by path ensures consistent lock order."""
    ctx = isolated_wiki
    _seed_file(ctx, "modules/a.md", "foo a\n")
    _seed_file(ctx, "modules/b.md", "foo b\n")

    prop1 = _new_proposal_dict(
        id="prop_thread1",
        proposal_type="multi_edit",
        edits=[
            {"page_path": "modules/a.md", "old_string": "foo a", "new_string": "T1 A"},
            {"page_path": "modules/b.md", "old_string": "foo b", "new_string": "T1 B"},
        ],
    )
    prop2 = _new_proposal_dict(
        id="prop_thread2",
        proposal_type="multi_edit",
        edits=[
            # Same two files, OPPOSITE declared order
            {"page_path": "modules/b.md", "old_string": "T1 B", "new_string": "T2 B"},
            {"page_path": "modules/a.md", "old_string": "T1 A", "new_string": "T2 A"},
        ],
    )

    results: dict[str, dict] = {}

    def runner(prop, key, delay):
        time.sleep(delay)
        results[key] = ctx["wa"].apply_multi_edit(prop)

    # T1 runs first and lands; T2 runs after with old_string matching T1's
    # output (so it has a valid Pass 1). They must not deadlock.
    t1 = threading.Thread(target=runner, args=(prop1, "t1", 0))
    t2 = threading.Thread(target=runner, args=(prop2, "t2", 0.02))
    t1.start()
    t2.start()
    t1.join(timeout=10)
    t2.join(timeout=10)
    assert not t1.is_alive() and not t2.is_alive(), "deadlock — threads still running"
    # Final state should be T2's writes (T1 ran first, T2 saw T1's output and edited it)
    assert ctx["wiki_dir"].joinpath("modules", "a.md").read_text() == "T2 A\n"
    assert ctx["wiki_dir"].joinpath("modules", "b.md").read_text() == "T2 B\n"


# ──────────────────────────────────────────────────────────────────────────────
# Lock contention (per-file)
# ──────────────────────────────────────────────────────────────────────────────

def test_apply_edit_lock_contention_serializes(isolated_wiki):
    """Two threads each holding a proposal to edit the same file. Both can't
    succeed — the second one will see a changed file inside the lock and
    refuse with stale_proposal. The flock serializes; what changes is the
    re-validation under lock.

    Test platform dependency: this verifies fcntl.flock semantics on POSIX
    (macOS + Linux). On Windows, `backend.file_locks` falls back to a no-op
    lock and the test would have a race window — the assertions could fail
    intermittently. CI/test runs are POSIX-only today; if Windows support is
    ever added, this test should be marked skip on win32."""
    ctx = isolated_wiki
    _seed_file(ctx, "concepts/race.md", "AAAA\n")
    prop1 = _new_proposal_dict(
        id="r1",
        proposal_type="edit",
        page_path="concepts/race.md",
        old_string="AAAA",
        new_string="BBBB",
    )
    prop2 = _new_proposal_dict(
        id="r2",
        proposal_type="edit",
        page_path="concepts/race.md",
        old_string="AAAA",
        new_string="CCCC",
    )

    results: dict[str, dict] = {}

    def runner(prop, key):
        results[key] = ctx["wa"].apply_edit(prop)

    t1 = threading.Thread(target=runner, args=(prop1, "t1"))
    t2 = threading.Thread(target=runner, args=(prop2, "t2"))
    t1.start()
    t2.start()
    t1.join(timeout=5)
    t2.join(timeout=5)

    success_count = sum(1 for r in results.values() if r["success"])
    stale_count = sum(1 for r in results.values() if r.get("code") == "stale_proposal")
    assert success_count == 1, f"exactly one writer should succeed, got {results}"
    assert stale_count == 1, f"the loser should see stale_proposal, got {results}"


# ──────────────────────────────────────────────────────────────────────────────
# refuse_legacy_text
# ──────────────────────────────────────────────────────────────────────────────

def test_refuse_legacy_text_returns_refused(isolated_wiki):
    ctx = isolated_wiki
    prop = _new_proposal_dict(
        id="prop_legacy",
        proposal_type="legacy_text",
        page_path="modules/foo.md",
        proposed_change="Fix the OTP description.",
    )
    result = ctx["wa"].refuse_legacy_text(prop)
    assert result["success"] is False
    assert result["code"] == "legacy_text_refused"
    assert "mark-applied" in result["message"]
    assert result["proposed_change"] == "Fix the OTP description."


# ──────────────────────────────────────────────────────────────────────────────
# Endpoint-level: apply_wiki_proposal dispatcher + mark_wiki_proposal_applied
# ──────────────────────────────────────────────────────────────────────────────

def test_dispatcher_idempotency_already_applied(isolated_wiki):
    ctx = isolated_wiki
    pid = ctx["wp"].create_new_proposal(
        page_path="concepts/idem.md",
        content="---\ntype: concept\n---\n",
        submitter_email="agent",
    )
    # First apply
    r1 = ctx["adm"].apply_wiki_proposal(pid)
    assert r1["success"] is True
    assert r1.get("files_written") == ["concepts/idem.md"]
    # Second apply — must NOT re-write; returns already_applied
    file_mtime_before = (ctx["wiki_dir"] / "concepts" / "idem.md").stat().st_mtime
    time.sleep(0.01)  # ensure mtime would change if rewritten
    r2 = ctx["adm"].apply_wiki_proposal(pid)
    assert r2["success"] is True
    assert r2["code"] == "already_applied"
    assert r2.get("files_written") == []
    file_mtime_after = (ctx["wiki_dir"] / "concepts" / "idem.md").stat().st_mtime
    assert file_mtime_after == file_mtime_before, "file was rewritten despite already_applied"


def test_dispatcher_reindex_called_after_apply(isolated_wiki, monkeypatch):
    ctx = isolated_wiki
    pid = ctx["wp"].create_new_proposal(
        page_path="concepts/reidx.md",
        content="---\ntype: concept\n---\n\n# Reidx\n",
        submitter_email="agent",
    )
    rebuild_called = []
    from backend import wiki_retriever
    monkeypatch.setattr(wiki_retriever, "rebuild_index", lambda: rebuild_called.append(1))
    result = ctx["adm"].apply_wiki_proposal(pid)
    assert result["success"] is True
    assert result.get("index_rebuilt") is True
    assert rebuild_called == [1]


def test_dispatcher_legacy_text_returns_refused_with_pointer_to_mark_applied(isolated_wiki):
    """A legacy_text proposal at /apply returns success=False with code legacy_text_refused."""
    ctx = isolated_wiki
    pid = ctx["wp"].create_proposal(
        page_path="modules/foo.md",
        proposed_change="text proposal",
        submitter_email="agent",
    )
    result = ctx["adm"].apply_wiki_proposal(pid)
    assert result["success"] is False
    assert result["code"] == "legacy_text_refused"
    assert "mark-applied" in result["message"]


def test_mark_applied_succeeds_on_legacy_text(isolated_wiki):
    ctx = isolated_wiki
    pid = ctx["wp"].create_proposal(
        page_path="modules/foo.md",
        proposed_change="manual fix done",
        submitter_email="agent",
    )
    result = ctx["adm"].mark_wiki_proposal_applied(pid, applied_by="admin@example.com")
    assert result["success"] is True
    assert result["proposal"]["status"] == "applied"
    assert result["proposal"]["applied_by"] == "admin@example.com"
    assert result["proposal"]["applied_at"] is not None


def test_mark_applied_refuses_on_structured_proposal(isolated_wiki):
    """Structured proposals must use /apply, not /mark-applied."""
    ctx = isolated_wiki
    pid = ctx["wp"].create_new_proposal(
        page_path="concepts/x.md",
        content="---\ntype: concept\n---\n",
        submitter_email="agent",
    )
    result = ctx["adm"].mark_wiki_proposal_applied(pid)
    assert result["success"] is False
    assert result["code"] == "not_legacy_text"
    assert "/apply" in result["message"]


def test_dispatcher_unknown_proposal_id_returns_not_found(isolated_wiki):
    ctx = isolated_wiki
    result = ctx["adm"].apply_wiki_proposal("prop_nonexistent")
    assert result["success"] is False
    assert result["code"] == "not_found"


# ──────────────────────────────────────────────────────────────────────────────
# Integration: propose → apply → file on disk → retriever sees it
# ──────────────────────────────────────────────────────────────────────────────

def test_integration_propose_new_apply_indexed(isolated_wiki, monkeypatch):
    """End-to-end: propose a new page via the propose tool, apply via the
    admin endpoint, then verify the file exists AND the retriever's
    rebuild_index would pick it up on a fresh build."""
    ctx = isolated_wiki

    # Set the propose-tool module's WIKI_DIR too — it caches the import
    import backend.tools.wiki_propose_tools as wpt
    importlib.reload(wpt)
    monkeypatch.setattr(wpt, "WIKI_DIR", ctx["wiki_dir"], raising=False)
    monkeypatch.setattr(wpt, "wiki_proposals", ctx["wp"], raising=False)
    fake_retriever = MagicMock()
    fake_retriever.get_page = MagicMock(return_value=None)
    monkeypatch.setattr(wpt, "wiki_retriever", fake_retriever, raising=False)

    # 1) Propose
    propose_result = wpt._wiki_propose_new_handler({
        "page_path": "answers/test-flow.md",
        "content": "---\ntype: answer\nlast_updated: 2026-05-22\n---\n\n# Integration test answer\n\nBody.\n",
        "reason": "integration test",
    })
    assert propose_result["status"] == "pending"
    pid = propose_result["proposal_id"]
    # File NOT yet written
    assert not (ctx["wiki_dir"] / "answers" / "test-flow.md").exists()

    # 2) Apply
    apply_result = ctx["adm"].apply_wiki_proposal(pid, applied_by="admin@example.com")
    assert apply_result["success"] is True
    assert apply_result["files_written"] == ["answers/test-flow.md"]
    target = ctx["wiki_dir"] / "answers" / "test-flow.md"
    assert target.is_file()
    assert "# Integration test answer" in target.read_text()

    # 3) Proposal record updated
    final = ctx["wp"].get_proposal(pid)
    assert final["status"] == "applied"
    assert final["applied_by"] == "admin@example.com"
    assert final["applied_at"] is not None

    # 4) Retriever sees it on a fresh build
    from backend.wiki_retriever import WikiIndex
    idx = WikiIndex()
    idx.build(wiki_dir=ctx["wiki_dir"])
    assert "answers/test-flow.md" in idx.all_paths()


def test_integration_propose_edit_apply_file_updated(isolated_wiki, monkeypatch):
    ctx = isolated_wiki
    _seed_file(ctx, "concepts/edit-flow.md", "---\ntype: concept\n---\n\nold body\n")

    import backend.tools.wiki_propose_tools as wpt
    importlib.reload(wpt)
    monkeypatch.setattr(wpt, "WIKI_DIR", ctx["wiki_dir"], raising=False)
    monkeypatch.setattr(wpt, "wiki_proposals", ctx["wp"], raising=False)
    # Real retriever-like behavior for this test: get_page returns content
    mock_page = MagicMock()
    mock_page.full_text = "---\ntype: concept\n---\n\nold body\n"
    fake_retriever = MagicMock()
    fake_retriever.get_page = MagicMock(return_value=mock_page)
    monkeypatch.setattr(wpt, "wiki_retriever", fake_retriever, raising=False)

    propose_result = wpt._wiki_propose_edit_handler({
        "page_path": "concepts/edit-flow.md",
        "old_string": "old body",
        "new_string": "new body",
        "reason": "integration test",
    })
    assert propose_result["status"] == "pending"
    pid = propose_result["proposal_id"]

    apply_result = ctx["adm"].apply_wiki_proposal(pid)
    assert apply_result["success"] is True
    assert (ctx["wiki_dir"] / "concepts" / "edit-flow.md").read_text().endswith("new body\n")
