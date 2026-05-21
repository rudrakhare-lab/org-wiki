# tests/test_wiki_proposals.py
import importlib
import json
import pytest
from pathlib import Path


@pytest.fixture
def isolated_proposals(tmp_path, monkeypatch):
    """Point wiki_proposals at a fresh JSONL under tmp_path."""
    feedback_dir = tmp_path / "raw" / "feedback"
    feedback_dir.mkdir(parents=True)
    proposals_file = feedback_dir / "wiki_proposals.jsonl"

    import backend.wiki_proposals as wp_module
    importlib.reload(wp_module)
    monkeypatch.setattr(wp_module, "PROPOSALS_FILE", proposals_file, raising=False)
    monkeypatch.setattr(wp_module, "FEEDBACK_DIR", feedback_dir, raising=False)
    yield wp_module


def test_create_and_list_proposals(isolated_proposals):
    wp = isolated_proposals
    pid = wp.create_proposal(
        page_path="modules/visitor-management.md",
        proposed_change="OTP is required, not optional",
        submitter_email="alice@example.com",
        answer_id="abc123",
    )
    assert pid is not None
    proposals = wp.list_proposals()
    assert len(proposals) == 1
    assert proposals[0]["page_path"] == "modules/visitor-management.md"
    assert proposals[0]["status"] == "pending"


def test_get_proposal(isolated_proposals):
    wp = isolated_proposals
    pid = wp.create_proposal(
        page_path="modules/meeting-rooms.md",
        proposed_change="Booking slots are 30 min, not 15 min",
        submitter_email="bob@example.com",
    )
    p = wp.get_proposal(pid)
    assert p is not None
    assert p["id"] == pid


def test_apply_proposal(isolated_proposals):
    wp = isolated_proposals
    pid = wp.create_proposal(
        page_path="modules/visitor-management.md",
        proposed_change="Fix description",
        submitter_email="carol@example.com",
    )
    wp.update_status(pid, "applied", admin_note="Looks correct")
    p = wp.get_proposal(pid)
    assert p["status"] == "applied"
    assert p["admin_note"] == "Looks correct"


def test_reject_proposal(isolated_proposals):
    wp = isolated_proposals
    pid = wp.create_proposal(
        page_path="modules/desk-management.md",
        proposed_change="Wrong info",
        submitter_email="dave@example.com",
    )
    wp.update_status(pid, "rejected", admin_note="Not accurate")
    p = wp.get_proposal(pid)
    assert p["status"] == "rejected"


def test_list_proposals_filtered_by_status(isolated_proposals):
    wp = isolated_proposals
    p1 = wp.create_proposal("a.md", "fix a", "alice@example.com")
    p2 = wp.create_proposal("b.md", "fix b", "bob@example.com")
    wp.update_status(p1, "applied")

    pending = wp.list_proposals(status="pending")
    assert len(pending) == 1
    assert pending[0]["id"] == p2


def test_proposal_never_writes_to_wiki_dir(isolated_proposals, tmp_path):
    """Proposals JSONL must stay inside raw/feedback, not wiki/."""
    wp = isolated_proposals
    import os
    wiki_path = tmp_path / "wiki"
    wiki_path.mkdir()
    # create_proposal does NOT write inside wiki_path
    wp.create_proposal("modules/foo.md", "change", "eve@example.com")
    wiki_files = list(wiki_path.rglob("*"))
    assert wiki_files == [], "wiki/ must not be written by create_proposal"
