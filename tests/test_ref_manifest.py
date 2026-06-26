# tests/test_ref_manifest.py
"""Tests for the SE-runbook reference manifest (coverage ledger).

Brief's 6 refs tests + R2 image surface tests.
TDD order: write all tests first (RED), then implement (GREEN).
"""
import pytest
import sqlite3
from scripts.lib.ref_manifest import Manifest


def _mk(tmp_path):
    return Manifest(str(tmp_path / "m.sqlite"))


# ── Brief's 6 refs tests (verbatim) ─────────────────────────────────────────

def test_add_if_new_dedupes(tmp_path):
    m = _mk(tmp_path)
    assert m.add_if_new("https://x/doc/1", "gdoc", 0, "root", file_id="1") is True
    # same url again → not added
    assert m.add_if_new("https://x/doc/1", "gdoc", 1, "other", file_id="1") is False


def test_next_discovered_is_lowest_depth(tmp_path):
    m = _mk(tmp_path)
    m.add_if_new("https://x/a", "gdoc", 2, "root", file_id="a")
    m.add_if_new("https://x/b", "gdoc", 0, "root", file_id="b")
    assert m.next_discovered()["url"] == "https://x/b"


def test_update_status_sets_fields(tmp_path):
    m = _mk(tmp_path)
    m.add_if_new("https://x/a", "gdoc", 0, "root", file_id="a")
    m.update_status("https://x/a", "fetched", local_path="/p/a.docx", sha256="deadbeef")
    row = m.next_discovered()
    assert row is None  # no longer 'discovered'


def test_update_status_rejects_unknown_fields(tmp_path):
    m = _mk(tmp_path)
    m.add_if_new("https://x/a", "gdoc", 0, "root", file_id="a")
    with pytest.raises(ValueError, match="unknown manifest fields"):
        m.update_status("https://x/a", "done", bogus_field="x")


def test_coverage_complete_and_report(tmp_path):
    m = _mk(tmp_path)
    m.add_if_new("https://x/a", "gdoc", 0, "root", file_id="a")
    assert m.coverage_complete() is False
    m.update_status("https://x/a", "done")
    assert m.coverage_complete() is True
    assert m.report() == {"done": 1}


def test_access_holes_listed(tmp_path):
    m = _mk(tmp_path)
    m.add_if_new("https://x/secret", "gsheet", 1, "root", file_id="s")
    m.update_status("https://x/secret", "access_denied", error="404")
    holes = m.access_holes()
    assert len(holes) == 1 and holes[0]["url"] == "https://x/secret"


def test_requeue_denied_reopens_for_retry(tmp_path):
    m = _mk(tmp_path)
    m.add_if_new("https://x/secret", "gsheet", 1, "root", file_id="s")
    m.update_status("https://x/secret", "access_denied", error="404")
    assert m.coverage_complete() is True          # denied is terminal for THIS run
    assert m.requeue_denied() == 1
    assert m.coverage_complete() is False         # back in flight
    assert m.next_discovered()["url"] == "https://x/secret"


# ── R2 image surface tests ───────────────────────────────────────────────────

def test_add_image_if_new_dedupes(tmp_path):
    """add_image_if_new returns True on first insert, False on duplicate."""
    m = _mk(tmp_path)
    assert m.add_image_if_new("img/screenshot_01.png", "source.docx",
                               section="Overview", nearby_text="See figure 1") is True
    # Same image_path again → not added
    assert m.add_image_if_new("img/screenshot_01.png", "source.docx") is False


def test_add_image_if_new_default_status(tmp_path):
    """Newly added image starts with ocr_status='pending'."""
    m = _mk(tmp_path)
    m.add_image_if_new("img/screenshot_02.png", "doc.docx")
    row = m.next_pending_image()
    assert row is not None
    assert row["ocr_status"] == "pending"
    assert row["image_path"] == "img/screenshot_02.png"


def test_next_pending_image_ordering(tmp_path):
    """next_pending_image returns rows ordered by image_path; returns None when none pending."""
    m = _mk(tmp_path)
    m.add_image_if_new("img/b.png", "doc.docx")
    m.add_image_if_new("img/a.png", "doc.docx")
    # ORDER BY image_path → 'img/a.png' comes first
    row = m.next_pending_image()
    assert row["image_path"] == "img/a.png"


def test_set_image_ocr_marks_done(tmp_path):
    """set_image_ocr updates ocr_status and ocr_text_path."""
    m = _mk(tmp_path)
    m.add_image_if_new("img/screenshot_03.png", "source.docx")
    m.set_image_ocr("img/screenshot_03.png", "done", ocr_text_path="/tmp/screenshot_03.txt")
    # No more pending images
    assert m.next_pending_image() is None


def test_next_pending_image_returns_none_when_all_done(tmp_path):
    """next_pending_image returns None when no images have ocr_status='pending'."""
    m = _mk(tmp_path)
    m.add_image_if_new("img/only.png", "doc.docx")
    m.set_image_ocr("img/only.png", "done")
    assert m.next_pending_image() is None


def test_coverage_complete_requires_images_done(tmp_path):
    """coverage_complete is False when a ref is done but an image is still pending."""
    m = _mk(tmp_path)
    # One done ref
    m.add_if_new("https://x/a", "gdoc", 0, "root", file_id="a")
    m.update_status("https://x/a", "done")
    # One pending image
    m.add_image_if_new("img/diag.png", "source.docx")

    # Ref is done but image is pending → coverage NOT complete
    assert m.coverage_complete() is False

    # Mark image done → coverage complete
    m.set_image_ocr("img/diag.png", "done")
    assert m.coverage_complete() is True


def test_coverage_complete_no_images_is_vacuously_true(tmp_path):
    """With no image rows at all, coverage_complete respects only refs state."""
    m = _mk(tmp_path)
    m.add_if_new("https://x/a", "gdoc", 0, "root", file_id="a")
    assert m.coverage_complete() is False  # ref in flight
    m.update_status("https://x/a", "done")
    assert m.coverage_complete() is True   # no images → vacuously true for image condition


def test_report_does_not_include_image_counts(tmp_path):
    """report() returns only refs status counts (brief contract — image counts not included)."""
    m = _mk(tmp_path)
    m.add_if_new("https://x/a", "gdoc", 0, "root", file_id="a")
    m.update_status("https://x/a", "done")
    m.add_image_if_new("img/screenshot.png", "doc.docx")
    # report() must return {"done": 1} only — no image keys
    assert m.report() == {"done": 1}


# ── Task R: Resilience — new tests ──────────────────────────────────────────

def test_is_image_done(tmp_path):
    """is_image_done: pending→False, done→True, absent path→False."""
    m = _mk(tmp_path)
    m.add_image_if_new("img/shot.png", "doc.docx")
    # pending → False
    assert m.is_image_done("img/shot.png") is False
    # set to done → True
    m.set_image_ocr("img/shot.png", "done")
    assert m.is_image_done("img/shot.png") is True
    # absent path → False
    assert m.is_image_done("img/nonexistent.png") is False


def test_requeue_incomplete_fetches(tmp_path):
    """requeue_incomplete_fetches flips fetched→discovered, returns count,
    and next_discovered returns the requeued url."""
    m = _mk(tmp_path)
    m.add_if_new("https://x/a", "gdoc", 1, "root", file_id="a")
    m.update_status("https://x/a", "fetched")
    # Before requeue: not in discovered frontier
    assert m.next_discovered() is None
    # Requeue returns count of rows flipped
    count = m.requeue_incomplete_fetches()
    assert count == 1
    # Now it's back in the frontier
    row = m.next_discovered()
    assert row is not None
    assert row["url"] == "https://x/a"
