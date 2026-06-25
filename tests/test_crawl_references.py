"""Integration tests for the SE-runbook crawl orchestrator.

TDD order: RED first (scripts.crawl_references does not exist yet), then GREEN.

Three tests:
  1. test_crawl_reaches_fixpoint_with_access_hole  — frontier loop, done/denied
  2. test_seed_from_docx_classifies               — seed classifies jira vs gdoc
  3. test_crawl_records_and_ocrs_images           — R2 image coverage wired
"""
import pathlib
import pytest

from scripts.lib.ref_manifest import Manifest
from scripts import crawl_references as C


# ── Test 1 — frontier loop reaches fixpoint ─────────────────────────────────

def test_crawl_reaches_fixpoint_with_access_hole(tmp_path):
    """Graph: root → A (good, links to B) ; root → SECRET (denied).
    Fixpoint means: A and B done, SECRET access_denied, nothing left in flight.
    """
    m = Manifest(str(tmp_path / "m.sqlite"))
    m.add_if_new("https://docs.google.com/document/d/A/edit", "gdoc", 0, "root", file_id="A")
    m.add_if_new("https://docs.google.com/document/d/SECRET/edit", "gdoc", 0, "root", file_id="SECRET")

    from scripts.lib.ref_fetch import FetchResult

    def fake_fetch(file_id, ref_type, dest_dir, **kw):
        if file_id == "SECRET":
            return FetchResult("access_denied", error="404")
        p = tmp_path / f"{file_id}.docx"
        p.write_bytes(b"x")
        return FetchResult("fetched", str(p), "hash")

    def fake_extract(local_path, image_dir):
        if local_path.endswith("A.docx"):
            return (["https://docs.google.com/document/d/B/edit"], [])  # A links to B
        return ([], [])

    report = C.crawl(m, str(tmp_path), str(tmp_path / "img"),
                     fetcher=fake_fetch, extractor=fake_extract, ocr=lambda p: "",
                     pdf_fetcher=lambda *a, **k: None,  # no-op PDF safety net offline
                     pdf_linker=lambda p: [])

    assert m.coverage_complete() is True
    assert report.get("done") == 2          # A and B
    assert report.get("access_denied") == 1  # SECRET
    assert len(m.access_holes()) == 1


# ── Test 2 — seed_from_docx classifies links correctly ──────────────────────

def test_seed_from_docx_classifies(tmp_path):
    from docx import Document
    doc = Document()
    part = doc.part
    part.relate_to("https://moveinsync.atlassian.net/browse/PB-1",
                   "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink",
                   is_external=True)
    part.relate_to("https://docs.google.com/document/d/SEED1/edit",
                   "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink",
                   is_external=True)
    path = tmp_path / "root.docx"
    doc.save(str(path))

    m = Manifest(str(tmp_path / "m.sqlite"))
    n = C.seed_from_docx(m, str(path), str(tmp_path / "img"))
    assert n == 2
    # the jira link is terminal, the gdoc is discovered
    assert m.next_discovered()["file_id"] == "SEED1"


# ── Test 3 — R2: images are recorded in manifest and OCR'd ──────────────────

def test_crawl_records_and_ocrs_images(tmp_path):
    m = Manifest(str(tmp_path / "m.sqlite"))
    m.add_if_new("https://docs.google.com/document/d/A/edit", "gdoc", 0, "root", file_id="A")

    from scripts.lib.ref_fetch import FetchResult

    def fake_fetch(fid, rt, dd, **kw):
        p = tmp_path / f"{fid}.docx"
        p.write_bytes(b"x")
        return FetchResult("fetched", str(p), "h")

    img_path = str(tmp_path / "img" / "A__0.png")

    def fake_extract(local_path, image_dir):
        return ([], [{"path": img_path, "section": "Setup", "nearby_text": "click save"}])

    C.crawl(m, str(tmp_path), str(tmp_path / "img"),
            fetcher=fake_fetch, extractor=fake_extract,
            ocr=lambda p: "OCR TEXT",
            pdf_fetcher=lambda *a, **k: None,
            pdf_linker=lambda p: [])

    assert m.coverage_complete() is True                        # image recorded AND marked done
    assert pathlib.Path(img_path + ".txt").read_text() == "OCR TEXT"  # sidecar written
    assert m.next_pending_image() is None                       # no pending images
