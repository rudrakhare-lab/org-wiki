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


# ── Task R: Resilience tests ─────────────────────────────────────────────────

def test_resume_skips_already_done_ocr(tmp_path):
    """Resume: an image already marked 'done' in the manifest is NOT re-OCR'd."""
    m = Manifest(str(tmp_path / "m.sqlite"))
    m.add_if_new("https://docs.google.com/document/d/A/edit", "gdoc", 0, "root", file_id="A")

    from scripts.lib.ref_fetch import FetchResult

    def fake_fetch(fid, rt, dd, **kw):
        p = tmp_path / f"{fid}.docx"
        p.write_bytes(b"x")
        return FetchResult("fetched", str(p), "h")

    done_img = str(tmp_path / "img" / "A__already_done.png")
    fresh_img = str(tmp_path / "img" / "A__fresh.png")

    # Pre-mark the "done" image in the manifest as already OCR'd
    m.add_image_if_new(done_img, "prior_run.docx")
    m.set_image_ocr(done_img, "done", ocr_text_path=done_img + ".txt")

    ocr_called_on = []

    def recording_ocr(path):
        ocr_called_on.append(path)
        return "OCR TEXT"

    def fake_extract(local_path, image_dir):
        # Return both images: the done one and a fresh one
        return ([], [
            {"path": done_img, "section": "S1"},
            {"path": fresh_img, "section": "S2"},
        ])

    C.crawl(m, str(tmp_path), str(tmp_path / "img"),
            fetcher=fake_fetch, extractor=fake_extract,
            ocr=recording_ocr,
            pdf_fetcher=lambda *a, **k: None,
            pdf_linker=lambda p: [])

    # The already-done image must NOT have been OCR'd again
    assert done_img not in ocr_called_on
    # The fresh image MUST have been OCR'd
    assert fresh_img in ocr_called_on


def test_requeue_reprocesses_fetched_ref(tmp_path):
    """requeue_incomplete_fetches re-opens a 'fetched' ref so crawl processes it to 'done'."""
    m = Manifest(str(tmp_path / "m.sqlite"))
    url = "https://docs.google.com/document/d/A/edit"
    m.add_if_new(url, "gdoc", 0, "root", file_id="A")
    # Simulate an interrupted run: file was fetched but never extracted/done
    m.update_status(url, "fetched", local_path=str(tmp_path / "A.docx"), sha256="h")
    # Write the file so the fake fetcher finds it
    (tmp_path / "A.docx").write_bytes(b"x")

    from scripts.lib.ref_fetch import FetchResult

    def fake_fetch(fid, rt, dd, **kw):
        p = tmp_path / f"{fid}.docx"
        p.write_bytes(b"x")
        return FetchResult("fetched", str(p), "h")

    # crawl should call requeue_incomplete_fetches internally at the start
    report = C.crawl(m, str(tmp_path), str(tmp_path / "img"),
                     fetcher=fake_fetch,
                     extractor=lambda lp, id: ([], []),
                     ocr=lambda p: "",
                     pdf_fetcher=lambda *a, **k: None,
                     pdf_linker=lambda p: [])

    assert report.get("done") == 1
    assert m.coverage_complete() is True


def test_max_depth_bounds_crawl(tmp_path):
    """max_depth=1: depth-2 refs are recorded as 'terminal', never fetched.
    Graph: root→A(depth1)→B(depth2); with max_depth=1, B is terminal.
    """
    m = Manifest(str(tmp_path / "m.sqlite"))
    # Seed root→A at depth 1 (as if seeded by seed_from_docx with max_depth=1)
    m.add_if_new("https://docs.google.com/document/d/A/edit", "gdoc", 1, "root", file_id="A")

    from scripts.lib.ref_fetch import FetchResult

    fetched_ids = []

    def fake_fetch(fid, rt, dd, **kw):
        fetched_ids.append(fid)
        p = tmp_path / f"{fid}.docx"
        p.write_bytes(b"x")
        return FetchResult("fetched", str(p), "h")

    def fake_extract(local_path, image_dir):
        # A links to B (which would be depth 2 with max_depth=1)
        if local_path.endswith("A.docx"):
            return (["https://docs.google.com/document/d/B/edit"], [])
        return ([], [])

    C.crawl(m, str(tmp_path), str(tmp_path / "img"),
            fetcher=fake_fetch,
            extractor=fake_extract,
            ocr=lambda p: "",
            pdf_fetcher=lambda *a, **k: None,
            pdf_linker=lambda p: [],
            max_depth=1)

    # A should be fetched and done (depth 0, seeded at depth 0 before crawl)
    assert "A" in fetched_ids
    # B must NOT have been fetched
    assert "B" not in fetched_ids
    # B must be recorded as 'terminal' (not silently dropped)
    conn = m.conn
    row = conn.execute(
        "SELECT status FROM refs WHERE file_id='B'"
    ).fetchone()
    assert row is not None, "B must be recorded in manifest"
    assert row["status"] == "terminal"
