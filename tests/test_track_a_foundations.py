"""Tests for Track A Sub-pass A foundations:
  - typed proposal store (legacy normalization, startup warn)
  - wiki_read_page disk-fallback for unindexed paths
  - file_locks context managers
  - wiki_retriever filter for Obsidian artifacts
"""
from __future__ import annotations

import importlib
import json
import logging
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest


# ── A.1 — wiki_proposals normalization + startup warn ────────────────────────

@pytest.fixture
def isolated_proposals(tmp_path, monkeypatch):
    """Point wiki_proposals at a fresh JSONL under tmp_path."""
    fb = tmp_path / "raw" / "feedback"
    fb.mkdir(parents=True)
    from backend import config
    monkeypatch.setattr(config, "FEEDBACK_DIR", fb, raising=False)
    import backend.wiki_proposals as wp
    importlib.reload(wp)
    monkeypatch.setattr(wp, "PROPOSALS_FILE", fb / "wiki_proposals.jsonl", raising=False)
    monkeypatch.setattr(wp, "FEEDBACK_DIR", fb, raising=False)
    return wp


def test_wiki_proposals_load_assigns_legacy_type(isolated_proposals):
    """Pre-Track-A records (no proposal_type) load with proposal_type='legacy_text'."""
    wp = isolated_proposals
    # Hand-write a pre-Track-A shape (matches the old wiki_proposals.py output)
    legacy = {
        "id": "prop_aaaaaaaaaaaa",
        "page_path": "modules/foo.md",
        "proposed_change": "Fix the OTP description",
        "submitter_email": "agent",
        "answer_id": None,
        "status": "pending",
        "admin_note": None,
        "created_at": "2026-04-01T10:00:00+00:00",
        "resolved_at": None,
    }
    with wp.PROPOSALS_FILE.open("w") as f:
        f.write(json.dumps(legacy) + "\n")

    proposals = wp.list_proposals()
    assert len(proposals) == 1
    p = proposals[0]
    assert p["proposal_type"] == "legacy_text"
    # New base fields also normalized in
    assert p["applied_at"] is None
    assert p["applied_by"] is None
    assert p["validation_log"] == []
    assert p["suggested_companion_edit"] is None


def test_wiki_proposals_startup_warn_logs_legacy_count(isolated_proposals, caplog):
    """warn_if_legacy_pending logs a WARN with the count when legacy records exist."""
    wp = isolated_proposals
    # Two legacy + one new + one resolved-legacy
    records = [
        {"id": "p1", "page_path": "a.md", "proposed_change": "x", "submitter_email": "u",
         "status": "pending", "created_at": "2026-04-01T10:00:00+00:00"},
        {"id": "p2", "page_path": "b.md", "proposed_change": "y", "submitter_email": "u",
         "status": "pending", "created_at": "2026-04-02T10:00:00+00:00"},
        {"id": "p3", "page_path": "c.md", "proposed_change": "z", "submitter_email": "u",
         "status": "resolved", "created_at": "2026-04-03T10:00:00+00:00"},
    ]
    with wp.PROPOSALS_FILE.open("w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
    wp.create_new_proposal("concepts/test.md", "---\ntype: concept\n---\n", "agent")

    caplog.set_level(logging.WARNING, logger="backend.wiki_proposals")
    count = wp.warn_if_legacy_pending()
    assert count == 2  # only pending legacy_text counted
    assert any("2 legacy_text wiki proposals are pending" in rec.message for rec in caplog.records)


def test_wiki_proposals_warn_is_silent_when_zero(isolated_proposals, caplog):
    wp = isolated_proposals
    wp.create_new_proposal("concepts/x.md", "---\ntype: concept\n---\n", "agent")

    caplog.set_level(logging.WARNING, logger="backend.wiki_proposals")
    assert wp.warn_if_legacy_pending() == 0
    assert not any("legacy_text" in rec.message for rec in caplog.records)


# ── A.2 — wiki_read_page disk-fallback for unindexed files ────────────────────

def test_wiki_read_page_reads_unindexed_files(monkeypatch, tmp_path):
    """A real .md file under wiki/ but NOT in the index (e.g. log.md, or a
    freshly-created file) is readable via disk fallback."""
    fake_wiki = tmp_path / "wiki"
    fake_wiki.mkdir()
    target = fake_wiki / "freshly_created.md"
    target.write_text("# Fresh Page\n\nNot indexed yet.\n", encoding="utf-8")

    from backend.tools import wiki_tools
    monkeypatch.setattr(wiki_tools, "WIKI_DIR", fake_wiki)
    monkeypatch.setattr(wiki_tools.wiki_retriever, "get_page", lambda path: None)

    result = wiki_tools._wiki_read_page_handler({"path": "freshly_created.md"})
    assert "error" not in result
    assert result["content"] == "# Fresh Page\n\nNot indexed yet.\n"
    assert result["title"] == "Fresh Page"
    assert result["path"] == "freshly_created.md"


def test_wiki_read_page_disk_fallback_pagination(monkeypatch, tmp_path):
    """Pagination works on disk-fallback reads too."""
    fake_wiki = tmp_path / "wiki"
    fake_wiki.mkdir()
    (fake_wiki / "big.md").write_text("x" * 5000, encoding="utf-8")

    from backend.tools import wiki_tools
    monkeypatch.setattr(wiki_tools, "WIKI_DIR", fake_wiki)
    monkeypatch.setattr(wiki_tools.wiki_retriever, "get_page", lambda path: None)

    result = wiki_tools._wiki_read_page_handler({"path": "big.md", "limit": 1000})
    assert len(result["content"]) == 1000
    assert result["has_more"] is True
    assert result["next_offset"] == 1000
    assert result["total_length"] == 5000


def test_wiki_read_page_path_traversal_still_blocked(monkeypatch, tmp_path):
    """The disk-fallback branch must not weaken path traversal protection."""
    fake_wiki = tmp_path / "wiki"
    fake_wiki.mkdir()

    from backend.tools import wiki_tools
    monkeypatch.setattr(wiki_tools, "WIKI_DIR", fake_wiki)
    monkeypatch.setattr(wiki_tools.wiki_retriever, "get_page", lambda path: None)

    for bad in ("../etc/passwd", "/etc/passwd", "../../something.md"):
        result = wiki_tools._wiki_read_page_handler({"path": bad})
        assert result["code"] == "path_traversal", f"path {bad!r} not blocked: {result}"


def test_wiki_read_page_not_found_for_truly_missing(monkeypatch, tmp_path):
    """Disk-fallback returns not_found when the file really doesn't exist."""
    fake_wiki = tmp_path / "wiki"
    fake_wiki.mkdir()

    from backend.tools import wiki_tools
    monkeypatch.setattr(wiki_tools, "WIKI_DIR", fake_wiki)
    monkeypatch.setattr(wiki_tools.wiki_retriever, "get_page", lambda path: None)

    result = wiki_tools._wiki_read_page_handler({"path": "does-not-exist.md"})
    assert result["code"] == "not_found"


# ── A.3 — file_locks context managers ────────────────────────────────────────

def test_file_lock_basic_acquire_release(tmp_path):
    """locked_write writes content and releases the lock cleanly."""
    from backend.file_locks import locked_write
    target = tmp_path / "x.txt"
    with locked_write(target) as fh:
        fh.write("hello")
    assert target.read_text() == "hello"


def test_file_lock_concurrent_threads_serialize(tmp_path):
    """Two threads writing the same file via locked_write produce a final
    state equal to the LAST writer's content (locks serialize them; no
    interleaving / corruption)."""
    from backend.file_locks import locked_write
    target = tmp_path / "concurrent.txt"
    barrier = threading.Barrier(2)

    def writer(content: str, delay: float):
        barrier.wait()
        time.sleep(delay)
        with locked_write(target) as fh:
            fh.write(content)
            time.sleep(0.05)  # hold the lock briefly

    t1 = threading.Thread(target=writer, args=("AAAA", 0))
    t2 = threading.Thread(target=writer, args=("BBBB", 0.01))
    t1.start(); t2.start()
    t1.join(); t2.join()
    final = target.read_text()
    # Must be exactly one of the two writes — no interleaved bytes
    assert final in ("AAAA", "BBBB"), f"corruption suspected, got {final!r}"


def test_locked_read_write_holds_lock(tmp_path):
    """locked_read_write yields the target path and creates a sidecar .lock."""
    from backend.file_locks import locked_read_write
    target = tmp_path / "y.txt"
    target.write_text("original")
    with locked_read_write(target) as p:
        assert p == target
        # Inside the lock, we can read + write the target
        text = p.read_text()
        p.write_text(text + " + edit")
    assert target.read_text() == "original + edit"
    # Sidecar lock file is left behind (harmless)
    assert (tmp_path / "y.txt.lock").exists()


# ── A.4 — wiki_retriever filters Obsidian artifacts ───────────────────────────

def test_wiki_retriever_filters_untitled_at_root(tmp_path):
    """build() skips Untitled* files at wiki root."""
    fake_wiki = tmp_path / "wiki"
    fake_wiki.mkdir()
    (fake_wiki / "Untitled.md").write_text("# Untitled\n")
    (fake_wiki / "Untitled 1.md").write_text("# Untitled 1\n")
    (fake_wiki / "real.md").write_text("# Real\n")

    from backend.wiki_retriever import WikiIndex
    idx = WikiIndex()
    idx.build(wiki_dir=fake_wiki)
    paths = idx.all_paths()
    assert "real.md" in paths
    assert not any(p.startswith("Untitled") for p in paths), f"got {paths}"


def test_wiki_retriever_filters_dated_files_at_root(tmp_path):
    """build() skips YYYY-MM-DD.md at wiki root."""
    fake_wiki = tmp_path / "wiki"
    fake_wiki.mkdir()
    (fake_wiki / "2026-05-13.md").write_text("# Daily note\n")
    (fake_wiki / "2026-12-31.md").write_text("# Daily note\n")
    (fake_wiki / "real.md").write_text("# Real\n")

    from backend.wiki_retriever import WikiIndex
    idx = WikiIndex()
    idx.build(wiki_dir=fake_wiki)
    paths = idx.all_paths()
    assert "real.md" in paths
    assert "2026-05-13.md" not in paths
    assert "2026-12-31.md" not in paths


def test_wiki_retriever_keeps_dated_files_in_subdirs(tmp_path):
    """Dated files in subdirectories (decisions/) ARE legitimate and must
    NOT be filtered."""
    fake_wiki = tmp_path / "wiki"
    (fake_wiki / "decisions").mkdir(parents=True)
    (fake_wiki / "decisions" / "2026-05-13-mealcutoff.md").write_text(
        "---\ntype: decision\n---\n# Mealcutoff decision\n"
    )
    (fake_wiki / "real.md").write_text("# Real\n")

    from backend.wiki_retriever import WikiIndex
    idx = WikiIndex()
    idx.build(wiki_dir=fake_wiki)
    paths = idx.all_paths()
    assert "decisions/2026-05-13-mealcutoff.md" in paths
    assert "real.md" in paths
