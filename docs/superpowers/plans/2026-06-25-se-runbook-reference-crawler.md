# SE Runbook Reference Crawler — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a recursive, idempotent crawler that starts from the 132-page `WIS-Configurations` DOCX, follows every Google Drive reference (Docs/Sheets/Slides) to full depth — including every sheet tab, cell hyperlink, slide, and embedded screenshot — fetches each file into `raw/se-runbook/`, OCRs screenshots, and records the entire reference graph in a SQLite manifest whose emptiness of unresolved rows is the provable "nothing was missed" guarantee.

**Architecture:** A SQLite **manifest** (`raw/se-runbook/manifest.sqlite`) is the source of truth for coverage — one row per discovered reference with a status lifecycle. A **frontier loop** drains `discovered` rows to a fixpoint: fetch by file-ID via `rclone backend copyid --drive-export-formats`, extract that file's own outbound links + embedded images, OCR the images, enqueue newly-found links, mark done. Non-Drive references (Jira, API URLs, external) are recorded as `terminal` — never fetched. Inaccessible files fail cleanly (`rclone` returns 404) and are recorded as `access_denied` — explicit, auditable coverage holes. The fetch mechanism is isolated behind one module so it can be swapped without touching the coverage logic.

**Tech Stack:** Python 3.13 (repo `venv/`), `sqlite3` (stdlib), `rclone` v1.73.5 (already configured with a `gdrive:` remote), `python-docx`, `openpyxl`, `python-pptx`, and Claude Vision via the existing `backend/document_extractor.py:extract_image()`.

## Global Constraints

- **Backend reload safety (CLAUDE.md §1):** NEVER create or edit a `.py` file in the project tree while the backend runs with `--reload` — it triggers a wiki-index rebuild that can destroy in-memory state. Verified NOT running at plan time; re-verify with `ps aux | grep uvicorn` before each task that writes `.py`.
- **`raw/` is append-only source-of-truth (CLAUDE.md §1):** the crawler may CREATE new files under `raw/se-runbook/` (same as `sync_drive.py` does for `raw/modules/`), but must NEVER modify or delete existing `raw/` files.
- **All Python runs via the repo venv:** `venv/bin/python`, `venv/bin/pytest`. Never system Python.
- **rclone remote name is exactly `gdrive:`** (verified via `rclone listremotes`). Export formats: `gdoc→docx`, `gsheet→xlsx`, `gslide→pptx`.
- **Secrets:** never hardcode tokens. `extract_image()` reads `ANTHROPIC_API_KEY` from the existing env — do not duplicate it.
- **Commit cadence:** one commit per completed task, on a feature branch (NOT `main`). Branch: `feat/se-runbook-crawler`.
- **TDD is mandatory:** every code task is red → green → commit. Tests build their own fixtures (no network, no real Drive) except the final live smoke step.

---

## File Structure

| File | Responsibility |
|------|----------------|
| `scripts/lib/ref_manifest.py` | SQLite manifest: schema, `add_if_new`, `next_discovered`, `update_status`, coverage queries. The coverage guarantee lives here. |
| `scripts/lib/ref_classify.py` | Pure function: URL → `(ref_type, file_id)`. No I/O. |
| `scripts/lib/ref_extract.py` | Per-format link + embedded-image extraction (docx / xlsx / pptx). The depth guarantee lives here (xlsx walks every tab + cell). |
| `scripts/lib/ref_ocr.py` | Thin wrapper reusing `backend.document_extractor.extract_image` to turn a screenshot into text. |
| `scripts/lib/ref_fetch.py` | rclone `copyid` + export wrapper; classifies success / `access_denied` / `error`. The only network module. |
| `scripts/crawl_references.py` | CLI + seed + frontier loop orchestrator + coverage report. |
| `tests/test_ref_manifest.py` | Manifest CRUD + coverage logic (temp sqlite). |
| `tests/test_ref_classify.py` | URL classification table. |
| `tests/test_ref_extract.py` | Extraction against fixtures built in-test with python-docx/openpyxl/python-pptx. |
| `tests/test_ref_ocr.py` | OCR wrapper with `extract_image` mocked. |
| `tests/test_ref_fetch.py` | Fetch command-building + 404/403 classification with `subprocess` mocked. |
| `tests/test_crawl_references.py` | Integration: a small fake reference graph (fetch + extract monkeypatched) reaches fixpoint, with one access-hole. |

Output (created at runtime, gitignored): `raw/se-runbook/manifest.sqlite`, `raw/se-runbook/files/<file_id>.<ext>`, `raw/se-runbook/images/<file_id>__<n>.png` + `.txt` OCR sidecars.

---

## Task 1: Reference manifest (the coverage ledger)

**Files:**
- Create: `scripts/lib/ref_manifest.py`
- Test: `tests/test_ref_manifest.py`

**Interfaces:**
- Produces:
  - `Manifest(db_path: str)` — opens/creates the SQLite db with the schema.
  - `Manifest.add_if_new(url: str, ref_type: str, depth: int, referenced_from: str, file_id: str | None = None) -> bool` — inserts a `discovered` row; returns `False` if `url` already present (dedupe).
  - `Manifest.next_discovered() -> sqlite3.Row | None` — lowest-depth `discovered` row, or `None`.
  - `Manifest.update_status(url: str, status: str, **fields) -> None` — sets `status` plus any of `local_path, sha256, error, fetched_at`.
  - `Manifest.coverage_complete() -> bool` — `True` when no rows in `('discovered','fetched','error')`.
  - `Manifest.report() -> dict[str,int]` — count by status.
  - `Manifest.access_holes() -> list[sqlite3.Row]` — rows with status `access_denied`.
  - `Manifest.requeue_denied() -> int` — flips every `access_denied` row back to `discovered` so a re-run (after access is granted) actually retries them; returns the count requeued.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_ref_manifest.py
import sqlite3
from scripts.lib.ref_manifest import Manifest


def _mk(tmp_path):
    return Manifest(str(tmp_path / "m.sqlite"))


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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `venv/bin/pytest tests/test_ref_manifest.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.lib.ref_manifest'`

- [ ] **Step 3: Write minimal implementation**

```python
# scripts/lib/ref_manifest.py
"""SQLite manifest for the SE-runbook reference crawl — the coverage ledger.

Each row is one discovered reference. The crawl is provably complete when
coverage_complete() returns True (no rows still in flight).
"""
from __future__ import annotations

import sqlite3

_SCHEMA = """
CREATE TABLE IF NOT EXISTS refs (
    url             TEXT PRIMARY KEY,
    file_id         TEXT,
    ref_type        TEXT NOT NULL,
    referenced_from TEXT,
    depth           INTEGER NOT NULL,
    status          TEXT NOT NULL DEFAULT 'discovered',
    local_path      TEXT,
    sha256          TEXT,
    error           TEXT,
    fetched_at      TEXT
);
"""

# Statuses that mean "still needs work" — coverage is complete when none remain.
_IN_FLIGHT = ("discovered", "fetched", "error")
_ALLOWED_FIELDS = {"local_path", "sha256", "error", "fetched_at"}


class Manifest:
    def __init__(self, db_path: str):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(_SCHEMA)
        self.conn.commit()

    def add_if_new(self, url, ref_type, depth, referenced_from, file_id=None) -> bool:
        if self.conn.execute("SELECT 1 FROM refs WHERE url=?", (url,)).fetchone():
            return False
        self.conn.execute(
            "INSERT INTO refs(url, file_id, ref_type, referenced_from, depth, status) "
            "VALUES(?,?,?,?,?,'discovered')",
            (url, file_id, ref_type, referenced_from, depth),
        )
        self.conn.commit()
        return True

    def next_discovered(self):
        return self.conn.execute(
            "SELECT * FROM refs WHERE status='discovered' ORDER BY depth, url LIMIT 1"
        ).fetchone()

    def update_status(self, url, status, **fields) -> None:
        bad = set(fields) - _ALLOWED_FIELDS
        if bad:
            raise ValueError(f"unknown manifest fields: {bad}")
        fields["status"] = status
        cols = ", ".join(f"{k}=?" for k in fields)
        self.conn.execute(
            f"UPDATE refs SET {cols} WHERE url=?", [*fields.values(), url]
        )
        self.conn.commit()

    def coverage_complete(self) -> bool:
        placeholders = ",".join("?" * len(_IN_FLIGHT))
        n = self.conn.execute(
            f"SELECT COUNT(*) AS n FROM refs WHERE status IN ({placeholders})",
            _IN_FLIGHT,
        ).fetchone()["n"]
        return n == 0

    def report(self) -> dict:
        rows = self.conn.execute(
            "SELECT status, COUNT(*) AS n FROM refs GROUP BY status"
        ).fetchall()
        return {r["status"]: r["n"] for r in rows}

    def access_holes(self):
        return self.conn.execute(
            "SELECT url, referenced_from, error FROM refs WHERE status='access_denied'"
        ).fetchall()

    def requeue_denied(self) -> int:
        cur = self.conn.execute(
            "UPDATE refs SET status='discovered', error=NULL WHERE status='access_denied'"
        )
        self.conn.commit()
        return cur.rowcount
```

- [ ] **Step 4: Ensure `scripts/` and `scripts/lib/` are importable as packages**

`scripts/lib/__init__.py` already exists. Confirm `scripts/__init__.py` exists; if not, create an empty one so `from scripts.lib...` imports resolve under pytest.

Run: `ls scripts/__init__.py || touch scripts/__init__.py`

- [ ] **Step 5: Run tests to verify they pass**

Run: `venv/bin/pytest tests/test_ref_manifest.py -v`
Expected: 6 passed

- [ ] **Step 6: Commit**

```bash
git add scripts/lib/ref_manifest.py tests/test_ref_manifest.py scripts/__init__.py
git commit -m "feat(crawler): reference manifest with coverage ledger"
```

---

## Task 2: URL classifier

**Files:**
- Create: `scripts/lib/ref_classify.py`
- Test: `tests/test_ref_classify.py`

**Interfaces:**
- Produces: `classify_url(url: str) -> tuple[str, str | None]` returning `(ref_type, file_id)` where `ref_type ∈ {"gdoc","gsheet","gslide","jira","api","external"}` and `file_id` is the Drive ID for the three Google types, else `None`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_ref_classify.py
import pytest
from scripts.lib.ref_classify import classify_url


@pytest.mark.parametrize("url,expected_type,expected_id", [
    ("https://docs.google.com/document/d/11Meiq_ABC/edit", "gdoc", "11Meiq_ABC"),
    ("https://docs.google.com/spreadsheets/d/1FyWu-DnS/edit#gid=0", "gsheet", "1FyWu-DnS"),
    ("https://docs.google.com/presentation/d/1CcHEQ_x/edit#slide=id.g1", "gslide", "1CcHEQ_x"),
    ("https://moveinsync.atlassian.net/browse/PB-49903", "jira", None),
    ("https://moveinsync.atlassian.net/issues/PB-46642", "jira", None),
    ("https://mis-security.moveinsync.com/mis-security-guard/premise", "api", None),
    ("https://signup.eu.workinsync.io/", "api", None),
    ("http://ec2-54-255-90-58.ap-southeast-1.compute.amazonaws.com:9045/x", "api", None),
    ("https://jsonformatter.org/", "external", None),
    ("mailto:abc@xyz.com", "external", None),
])
def test_classify(url, expected_type, expected_id):
    t, fid = classify_url(url)
    assert (t, fid) == (expected_type, expected_id)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `venv/bin/pytest tests/test_ref_classify.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.lib.ref_classify'`

- [ ] **Step 3: Write minimal implementation**

```python
# scripts/lib/ref_classify.py
"""Classify a URL into a crawl ref_type and extract a Drive file-ID."""
from __future__ import annotations

import re

_DRIVE_ID = re.compile(r"/d/([a-zA-Z0-9_-]+)")
_API_HOST = re.compile(r"(moveinsync\.com|moveinsync\.in|workinsync\.io|amazonaws\.com)", re.I)


def _file_id(url: str) -> str | None:
    m = _DRIVE_ID.search(url)
    return m.group(1) if m else None


def classify_url(url: str) -> tuple[str, str | None]:
    u = url.lower()
    if "docs.google.com/document/" in u:
        return "gdoc", _file_id(url)
    if "docs.google.com/spreadsheets/" in u:
        return "gsheet", _file_id(url)
    if "docs.google.com/presentation/" in u:
        return "gslide", _file_id(url)
    if "atlassian.net/browse/" in u or "atlassian.net/issues/" in u:
        return "jira", None
    if u.startswith("mailto:"):
        return "external", None
    if _API_HOST.search(u):
        return "api", None
    return "external", None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `venv/bin/pytest tests/test_ref_classify.py -v`
Expected: 10 passed

- [ ] **Step 5: Commit**

```bash
git add scripts/lib/ref_classify.py tests/test_ref_classify.py
git commit -m "feat(crawler): URL classifier (gdoc/gsheet/gslide/jira/api/external)"
```

---

## Task 3: DOCX link + image extraction

**Files:**
- Create: `scripts/lib/ref_extract.py`
- Test: `tests/test_ref_extract.py`
- Modify: `requirements.txt` (add `python-docx`, `python-pptx`)

**Interfaces:**
- Produces:
  - `extract_links_and_images(local_path: str, image_dir: str) -> tuple[list[str], list[str]]` — dispatches on file extension; returns `(urls, image_paths)`. Image blobs are written into `image_dir` as `<stem>__<n>.<ext>` and their paths returned.
  - This task implements the `.docx` branch; later tasks add `.xlsx` and `.pptx`.

- [ ] **Step 1: Add parsing deps to requirements and install**

```bash
printf '\n# SE-runbook reference crawler\npython-docx==1.1.2\npython-pptx==1.0.2\n' >> requirements.txt
venv/bin/pip install python-docx==1.1.2 python-pptx==1.0.2 -q
```
(`openpyxl` and `pdfplumber` are already present.)

- [ ] **Step 2: Write the failing test (builds its own .docx fixture)**

```python
# tests/test_ref_extract.py
from docx import Document
from scripts.lib.ref_extract import extract_links_and_images


def test_docx_links_extracted(tmp_path):
    doc = Document()
    p = doc.add_paragraph()
    run = p.add_run("see this")
    # add a hyperlink relationship the way python-docx exposes it
    part = doc.part
    r_id = part.relate_to(
        "https://docs.google.com/spreadsheets/d/SHEET1/edit",
        "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink",
        is_external=True,
    )
    # minimal: the relationship alone is what extract reads
    path = tmp_path / "doc.docx"
    doc.save(str(path))

    urls, images = extract_links_and_images(str(path), str(tmp_path / "img"))
    assert "https://docs.google.com/spreadsheets/d/SHEET1/edit" in urls
```

- [ ] **Step 3: Run test to verify it fails**

Run: `venv/bin/pytest tests/test_ref_extract.py -v`
Expected: FAIL — `ImportError`/`AttributeError` (`extract_links_and_images` not defined)

- [ ] **Step 4: Write minimal implementation (docx branch + dispatcher)**

```python
# scripts/lib/ref_extract.py
"""Extract outbound links and embedded images from fetched Office files.

The depth guarantee of the crawl lives here: every link a file contains must
be surfaced so the frontier loop can enqueue it. For spreadsheets that means
every tab and every cell hyperlink; for decks, every slide and shape.
"""
from __future__ import annotations

import pathlib

_HYPERLINK_REL = "hyperlink"
_IMAGE_REL = "image"


def _write_blob(blob: bytes, image_dir: str, stem: str, idx: int, ext: str) -> str:
    d = pathlib.Path(image_dir)
    d.mkdir(parents=True, exist_ok=True)
    out = d / f"{stem}__{idx}{ext}"
    out.write_bytes(blob)
    return str(out)


def _extract_docx(path: str, image_dir: str):
    from docx import Document

    doc = Document(path)
    stem = pathlib.Path(path).stem
    urls, images = [], []
    idx = 0
    for rel in doc.part.rels.values():
        if _HYPERLINK_REL in rel.reltype and rel.is_external:
            urls.append(rel.target_ref)
        elif _IMAGE_REL in rel.reltype:
            try:
                blob = rel.target_part.blob
                ext = pathlib.Path(rel.target_part.partname).suffix or ".png"
                images.append(_write_blob(blob, image_dir, stem, idx, ext))
                idx += 1
            except Exception:
                pass
    return urls, images


def extract_links_and_images(local_path: str, image_dir: str):
    ext = pathlib.Path(local_path).suffix.lower()
    if ext == ".docx":
        return _extract_docx(local_path, image_dir)
    raise ValueError(f"no extractor for {ext!r}")
```

- [ ] **Step 5: Run test to verify it passes**

Run: `venv/bin/pytest tests/test_ref_extract.py -v`
Expected: 1 passed

- [ ] **Step 6: Commit**

```bash
git add scripts/lib/ref_extract.py tests/test_ref_extract.py requirements.txt
git commit -m "feat(crawler): docx link+image extraction + parsing deps"
```

---

## Task 4: XLSX extraction — every tab, every cell hyperlink (depth-critical)

**Files:**
- Modify: `scripts/lib/ref_extract.py`
- Modify: `tests/test_ref_extract.py`

**Interfaces:**
- Consumes: `extract_links_and_images` dispatcher from Task 3.
- Produces: `.xlsx` branch — walks **every worksheet**, collects `cell.hyperlink.target` for every cell, parses `=HYPERLINK("url",...)` formula strings, AND scans every string cell value for bare `https?://` URLs (pasted-as-text links — the most common real-world case). Embedded images via `ws._images`.

> **Why bare-URL scanning matters (verified 2026-06-25):** Google's Sheets/Slides → Office export is lossy on UI-created links — a link can survive only as visible text. Empirical check on real exports (`gdrive:1FyWuDnS...` sheet, `gdrive:11Meiq...` doc) confirmed `.docx` export preserves hyperlink rels (the 132-page root doc carries all 250), but a single structured rendering is not trusted alone. Recall is guaranteed by **unioning** structured links + bare-text URLs (this task) with a throwaway **PDF render** scrape (Task 7b). If a link is visible to a human in any form, one path catches it.

- [ ] **Step 0: Reproduce the export-fidelity check (proves the union approach is needed, not academic)**

```bash
rclone backend copyid --drive-export-formats xlsx gdrive: 1FyWuDnS-L6wB9ZBqTvLwsk6qwQEBWIyTtMaHJ9PojlU /tmp/probe.xlsx
venv/bin/python -c "import openpyxl; wb=openpyxl.load_workbook('/tmp/probe.xlsx'); print('tabs', wb.sheetnames)"
```
Expected: the file exports and lists its tabs. (On this sample the sheet has no outbound links — that is fine; the test below proves the extractor finds links *when present*, in all three forms.)

- [ ] **Step 1: Write the failing test (builds a multi-tab .xlsx fixture)**

```python
# append to tests/test_ref_extract.py
import openpyxl


def test_xlsx_walks_all_tabs_and_formula_links(tmp_path):
    wb = openpyxl.Workbook()
    ws1 = wb.active
    ws1.title = "Tab1"
    ws1["A1"].value = "linked"
    ws1["A1"].hyperlink = "https://docs.google.com/document/d/DOC_IN_TAB1/edit"
    ws2 = wb.create_sheet("Tab2")
    ws2["B2"].value = '=HYPERLINK("https://docs.google.com/presentation/d/DECK_IN_TAB2/edit","go")'
    ws2["B3"].value = "see https://docs.google.com/document/d/PASTED_AS_TEXT/edit for details"
    path = tmp_path / "book.xlsx"
    wb.save(str(path))

    urls, _ = extract_links_and_images(str(path), str(tmp_path / "img"))
    assert "https://docs.google.com/document/d/DOC_IN_TAB1/edit" in urls          # cell hyperlink, tab 1
    assert "https://docs.google.com/presentation/d/DECK_IN_TAB2/edit" in urls     # =HYPERLINK formula, tab 2
    assert "https://docs.google.com/document/d/PASTED_AS_TEXT/edit" in urls       # bare URL in text, tab 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv/bin/pytest tests/test_ref_extract.py::test_xlsx_walks_all_tabs_and_formula_links -v`
Expected: FAIL with `ValueError: no extractor for '.xlsx'`

- [ ] **Step 3: Add the xlsx branch**

```python
# add to scripts/lib/ref_extract.py
import re as _re

_HYPERLINK_FORMULA = _re.compile(r'HYPERLINK\(\s*"([^"]+)"', _re.IGNORECASE)
# Bare URL anywhere in text (footnotes, pasted cells, slide captions).
_BARE_URL = _re.compile(r'https?://[^\s"\'<>)\]]+')


def _extract_xlsx(path: str, image_dir: str):
    import openpyxl

    wb = openpyxl.load_workbook(path)  # keep formulas (data_only=False default)
    stem = pathlib.Path(path).stem
    urls, images = [], []
    idx = 0
    for ws in wb.worksheets:                      # EVERY tab
        for row in ws.iter_rows():
            for cell in row:
                if cell.hyperlink and cell.hyperlink.target:
                    urls.append(cell.hyperlink.target)
                if isinstance(cell.value, str):
                    if "HYPERLINK(" in cell.value.upper():
                        urls.extend(_HYPERLINK_FORMULA.findall(cell.value))
                    urls.extend(_BARE_URL.findall(cell.value))   # pasted-as-text links
        for img in getattr(ws, "_images", []):
            try:
                blob = img._data() if callable(getattr(img, "_data", None)) else img.ref
                if isinstance(blob, bytes):
                    images.append(_write_blob(blob, image_dir, stem, idx, ".png"))
                    idx += 1
            except Exception:
                pass
    return urls, images
```

Then add the dispatch line in `extract_links_and_images`, before the final `raise`:

```python
    if ext == ".xlsx":
        return _extract_xlsx(local_path, image_dir)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `venv/bin/pytest tests/test_ref_extract.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add scripts/lib/ref_extract.py tests/test_ref_extract.py
git commit -m "feat(crawler): xlsx extraction across all tabs + HYPERLINK formulas"
```

---

## Task 5: PPTX extraction — every slide, shape, run hyperlink + pictures

**Files:**
- Modify: `scripts/lib/ref_extract.py`
- Modify: `tests/test_ref_extract.py`

**Interfaces:**
- Consumes: dispatcher from Task 3.
- Produces: `.pptx` branch — iterates every slide, **recursing into GROUP shapes** (SE decks group screenshots with callout boxes); collects shape click-action hyperlinks, text-run hyperlinks, and bare URLs in text; writes every picture shape's blob to `image_dir` for OCR. (Verified 2026-06-25 on `gdrive:1CcHEQ...`: 21 slides → 40 pictures extract cleanly.)

- [ ] **Step 1: Write the failing test (builds a .pptx fixture with a run hyperlink)**

```python
# append to tests/test_ref_extract.py
from pptx import Presentation
from pptx.util import Inches


def test_pptx_extracts_run_hyperlink(tmp_path):
    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[5])
    tb = slide.shapes.add_textbox(Inches(1), Inches(1), Inches(4), Inches(1))
    run = tb.text_frame.paragraphs[0].add_run()
    run.text = "open sheet"
    run.hyperlink.address = "https://docs.google.com/spreadsheets/d/SHEET_IN_DECK/edit"
    path = tmp_path / "deck.pptx"
    prs.save(str(path))

    urls, _ = extract_links_and_images(str(path), str(tmp_path / "img"))
    assert "https://docs.google.com/spreadsheets/d/SHEET_IN_DECK/edit" in urls
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv/bin/pytest tests/test_ref_extract.py::test_pptx_extracts_run_hyperlink -v`
Expected: FAIL with `ValueError: no extractor for '.pptx'`

- [ ] **Step 3: Add the pptx branch**

```python
# add to scripts/lib/ref_extract.py
def _extract_pptx(path: str, image_dir: str):
    from pptx import Presentation
    from pptx.enum.shapes import MSO_SHAPE_TYPE

    prs = Presentation(path)
    stem = pathlib.Path(path).stem
    urls, images = [], []
    counter = [0]  # mutable so the nested walker can bump it

    def walk(shapes):
        for shape in shapes:
            try:
                addr = shape.click_action.hyperlink.address
                if addr:
                    urls.append(addr)
            except Exception:
                pass
            if shape.shape_type == MSO_SHAPE_TYPE.GROUP:   # recurse into grouped shapes
                walk(shape.shapes)
                continue
            if shape.has_text_frame:
                for para in shape.text_frame.paragraphs:
                    for run in para.runs:
                        addr = run.hyperlink.address
                        if addr:
                            urls.append(addr)
                urls.extend(_BARE_URL.findall(shape.text_frame.text or ""))
            if shape.shape_type == MSO_SHAPE_TYPE.PICTURE:
                try:
                    image = shape.image
                    ext = "." + (image.ext or "png")
                    images.append(_write_blob(image.blob, image_dir, stem, counter[0], ext))
                    counter[0] += 1
                except Exception:
                    pass

    for slide in prs.slides:
        walk(slide.shapes)
    return urls, images
```

Add dispatch before the final `raise`:

```python
    if ext == ".pptx":
        return _extract_pptx(local_path, image_dir)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `venv/bin/pytest tests/test_ref_extract.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add scripts/lib/ref_extract.py tests/test_ref_extract.py
git commit -m "feat(crawler): pptx extraction (slide/shape/run links + pictures)"
```

---

## Task 6: OCR wrapper (screenshots → text)

**Files:**
- Create: `scripts/lib/ref_ocr.py`
- Test: `tests/test_ref_ocr.py`

**Interfaces:**
- Produces: `ocr_image(image_path: str) -> str` — returns extracted text; never raises (returns a `[OCR failed: ...]` marker on error). Reuses `backend.document_extractor.extract_image`.

- [ ] **Step 1: Write the failing test (mocks extract_image — no API call)**

```python
# tests/test_ref_ocr.py
from unittest.mock import patch
from scripts.lib import ref_ocr


def test_ocr_returns_text(tmp_path):
    img = tmp_path / "shot.png"
    img.write_bytes(b"\x89PNG\r\n")  # content irrelevant — extract_image is mocked
    with patch("scripts.lib.ref_ocr.extract_image", return_value={"text": "Step 1: click Save"}):
        assert ref_ocr.ocr_image(str(img)) == "Step 1: click Save"


def test_ocr_never_raises(tmp_path):
    img = tmp_path / "shot.png"
    img.write_bytes(b"x")
    with patch("scripts.lib.ref_ocr.extract_image", side_effect=RuntimeError("boom")):
        out = ref_ocr.ocr_image(str(img))
    assert out.startswith("[OCR failed:")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `venv/bin/pytest tests/test_ref_ocr.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.lib.ref_ocr'`

- [ ] **Step 3: Write minimal implementation**

```python
# scripts/lib/ref_ocr.py
"""OCR a screenshot to text by reusing the backend's Claude Vision extractor."""
from __future__ import annotations

import pathlib
import sys

# Make the repo root importable so `backend` resolves when run as a script.
_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from backend.document_extractor import extract_image  # noqa: E402


def ocr_image(image_path: str) -> str:
    try:
        return (extract_image(image_path) or {}).get("text", "") or ""
    except Exception as exc:  # never let one bad screenshot break the crawl
        return f"[OCR failed: {exc}]"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `venv/bin/pytest tests/test_ref_ocr.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add scripts/lib/ref_ocr.py tests/test_ref_ocr.py
git commit -m "feat(crawler): OCR wrapper reusing backend Vision extractor"
```

---

## Task 7: rclone fetcher (the only network module)

**Files:**
- Create: `scripts/lib/ref_fetch.py`
- Test: `tests/test_ref_fetch.py`

**Interfaces:**
- Produces:
  - `FetchResult` dataclass: `status: str` (`"fetched" | "access_denied" | "error"`), `local_path: str | None`, `sha256: str | None`, `error: str | None`.
  - `fetch_drive_file(file_id: str, ref_type: str, dest_dir: str, remote: str = "gdrive:", runner=subprocess.run) -> FetchResult` — builds and runs the rclone export command. `runner` is injectable for testing.

- [ ] **Step 1: Write the failing tests (mock the runner — no real rclone)**

```python
# tests/test_ref_fetch.py
import subprocess
from scripts.lib.ref_fetch import fetch_drive_file


class _Proc:
    def __init__(self, rc, out="", err=""):
        self.returncode, self.stdout, self.stderr = rc, out, err


def test_command_shape_and_success(tmp_path):
    captured = {}

    def runner(cmd, **kw):
        captured["cmd"] = cmd
        (tmp_path / "FID.docx").write_bytes(b"hello")   # simulate rclone writing the file
        return _Proc(0)

    res = fetch_drive_file("FID", "gdoc", str(tmp_path), runner=runner)
    assert res.status == "fetched"
    assert res.sha256 == __import__("hashlib").sha256(b"hello").hexdigest()
    assert "--drive-export-formats" in captured["cmd"]
    assert "docx" in captured["cmd"]
    assert "gdrive:" in captured["cmd"] and "FID" in captured["cmd"]


def test_404_is_access_denied(tmp_path):
    def runner(cmd, **kw):
        return _Proc(1, err='Error 404: File not found: FID., notFound')
    res = fetch_drive_file("FID", "gsheet", str(tmp_path), runner=runner)
    assert res.status == "access_denied"


def test_other_failure_is_error(tmp_path):
    def runner(cmd, **kw):
        return _Proc(1, err="some transient network blip")
    res = fetch_drive_file("FID", "gslide", str(tmp_path), runner=runner)
    assert res.status == "error"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `venv/bin/pytest tests/test_ref_fetch.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.lib.ref_fetch'`

- [ ] **Step 3: Write minimal implementation**

```python
# scripts/lib/ref_fetch.py
"""Fetch a Google-native Drive file by ID via rclone, exporting to Office format.

This is the ONLY module that touches the network. Swapping the fetch mechanism
(e.g. to the Drive API later) means replacing only this file.
"""
from __future__ import annotations

import hashlib
import pathlib
import subprocess
from dataclasses import dataclass

_EXPORT_FMT = {"gdoc": "docx", "gsheet": "xlsx", "gslide": "pptx"}
_EXT = {"gdoc": ".docx", "gsheet": ".xlsx", "gslide": ".pptx"}
_DENIED_MARKERS = ("404", "notfound", "403", "forbidden", "permission")


@dataclass
class FetchResult:
    status: str
    local_path: str | None = None
    sha256: str | None = None
    error: str | None = None


def fetch_drive_file(file_id, ref_type, dest_dir, remote="gdrive:", runner=subprocess.run):
    fmt = _EXPORT_FMT[ref_type]
    dest = pathlib.Path(dest_dir) / f"{file_id}{_EXT[ref_type]}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "rclone", "backend", "copyid",
        "--drive-export-formats", fmt,
        remote, file_id, str(dest),
    ]
    proc = runner(cmd, capture_output=True, text=True)
    blob = (getattr(proc, "stdout", "") or "") + (getattr(proc, "stderr", "") or "")
    if proc.returncode == 0 and dest.exists():
        data = dest.read_bytes()
        return FetchResult("fetched", str(dest), hashlib.sha256(data).hexdigest())
    low = blob.lower()
    if any(m in low for m in _DENIED_MARKERS):
        return FetchResult("access_denied", error=blob.strip()[:300])
    return FetchResult("error", error=blob.strip()[:300])
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `venv/bin/pytest tests/test_ref_fetch.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add scripts/lib/ref_fetch.py tests/test_ref_fetch.py
git commit -m "feat(crawler): rclone by-id export fetcher with access-hole detection"
```

---

## Task 7b: PDF-render link safety net (guarantees link recall)

**Files:**
- Modify: `scripts/lib/ref_fetch.py` (add PDF fetch)
- Modify: `scripts/lib/ref_extract.py` (add PDF link scrape)
- Modify: `tests/test_ref_fetch.py`, `tests/test_ref_extract.py`

**Why:** Google's Office export can silently drop UI-created links (verified concern). To guarantee recall, every fetched Google file is ALSO rendered to a throwaway PDF and scraped for both annotation URIs and visible-text URLs. The orchestrator (Task 8) unions these with the structured-format links. Two independent renderings → a link must be invisible in *both* to be missed.

**Interfaces:**
- Produces:
  - `ref_fetch.fetch_pdf(file_id: str, dest_dir: str, remote="gdrive:", runner=subprocess.run) -> str | None` — exports the file to PDF; returns the path or `None` on any failure (never raises; the PDF is a best-effort safety net, not load-bearing for content).
  - `ref_extract.extract_pdf_links(pdf_path: str) -> list[str]` — returns annotation URIs + bare-text URLs found in the PDF.

- [ ] **Step 1: Write the failing test for `extract_pdf_links` (uses the real probe PDF from Task 4 Step 0, or skips if absent)**

```python
# append to tests/test_ref_extract.py
import os
import pytest
from scripts.lib.ref_extract import extract_pdf_links


def test_extract_pdf_links_returns_list(tmp_path):
    # Build a tiny PDF with a visible URL using pdfplumber's dependency (pdfminer can't write);
    # instead assert the function handles a missing/empty file gracefully and returns a list.
    missing = str(tmp_path / "nope.pdf")
    assert extract_pdf_links(missing) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv/bin/pytest tests/test_ref_extract.py::test_extract_pdf_links_returns_list -v`
Expected: FAIL — `ImportError` (`extract_pdf_links` not defined)

- [ ] **Step 3: Implement `extract_pdf_links` (in `scripts/lib/ref_extract.py`)**

```python
# add to scripts/lib/ref_extract.py
def extract_pdf_links(pdf_path: str) -> list:
    """Scrape annotation URIs + visible-text URLs from a PDF render. Never raises."""
    if not pathlib.Path(pdf_path).exists():
        return []
    urls = []
    try:
        import pdfplumber

        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                for annot in (page.annots or []):
                    uri = annot.get("uri") or (annot.get("data") or {}).get("A", {}).get("URI")
                    if uri:
                        urls.append(uri)
                urls.extend(_BARE_URL.findall(page.extract_text() or ""))
    except Exception:
        return urls
    return urls
```

- [ ] **Step 4: Run test to verify it passes**

Run: `venv/bin/pytest tests/test_ref_extract.py::test_extract_pdf_links_returns_list -v`
Expected: 1 passed

- [ ] **Step 5: Add `fetch_pdf` to `scripts/lib/ref_fetch.py` with a mocked test**

```python
# append to tests/test_ref_fetch.py
from scripts.lib.ref_fetch import fetch_pdf


def test_fetch_pdf_success_and_failure(tmp_path):
    def ok(cmd, **kw):
        (tmp_path / "FID.pdf").write_bytes(b"%PDF-1.4")
        return _Proc(0)
    assert fetch_pdf("FID", str(tmp_path), runner=ok).endswith("FID.pdf")

    def fail(cmd, **kw):
        return _Proc(1, err="404 notFound")
    assert fetch_pdf("FID2", str(tmp_path), runner=fail) is None
```

```python
# add to scripts/lib/ref_fetch.py
def fetch_pdf(file_id, dest_dir, remote="gdrive:", runner=subprocess.run):
    """Best-effort PDF render for link scraping. Returns path or None; never raises."""
    dest = pathlib.Path(dest_dir) / f"{file_id}.pdf"
    dest.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["rclone", "backend", "copyid", "--drive-export-formats", "pdf",
           remote, file_id, str(dest)]
    try:
        proc = runner(cmd, capture_output=True, text=True)
    except Exception:
        return None
    return str(dest) if proc.returncode == 0 and dest.exists() else None
```

- [ ] **Step 6: Run the fetch + extract suites**

Run: `venv/bin/pytest tests/test_ref_fetch.py tests/test_ref_extract.py -v`
Expected: all green

- [ ] **Step 7: Commit**

```bash
git add scripts/lib/ref_fetch.py scripts/lib/ref_extract.py tests/test_ref_fetch.py tests/test_ref_extract.py
git commit -m "feat(crawler): PDF-render link safety net for guaranteed recall"
```

---

## Task 8: Orchestrator + CLI + coverage report

**Files:**
- Create: `scripts/crawl_references.py`
- Test: `tests/test_crawl_references.py`

**Interfaces:**
- Consumes: `Manifest`, `classify_url`, `extract_links_and_images`, `extract_pdf_links`, `ocr_image`, `fetch_drive_file`, `fetch_pdf`.
- Produces:
  - `seed_from_docx(manifest, docx_path, image_dir, ocr=ocr_image) -> int` — extracts links AND embedded images from the root DOCX, classifies each link into `discovered`/`terminal` rows, and OCRs every embedded screenshot to a `.txt` sidecar (the root doc is the highest-value file — its screenshots must not be lost); returns count of links seeded.
  - `crawl(manifest, files_dir, image_dir, fetcher=fetch_drive_file, extractor=extract_links_and_images, ocr=ocr_image, pdf_fetcher=fetch_pdf, pdf_linker=extract_pdf_links) -> dict` — runs the frontier loop to fixpoint; for each fetched Google file it unions structured links with PDF-render links; returns the status report. Dependencies are injected so the integration test runs offline.
  - `main(argv=None)` — CLI: `--root <docx> --out raw/se-runbook [--retry-denied]`.

- [ ] **Step 1: Write the failing integration test (fully offline via injected fakes)**

```python
# tests/test_crawl_references.py
from scripts.lib.ref_manifest import Manifest
from scripts import crawl_references as C


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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `venv/bin/pytest tests/test_crawl_references.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.crawl_references'`

- [ ] **Step 3: Write minimal implementation**

```python
# scripts/crawl_references.py
"""Recursive reference crawler for the SE-runbook DOCX and everything it links to.

Drains the manifest frontier to a fixpoint. Coverage is provably complete when
manifest.coverage_complete() is True; access_denied rows are the explicit holes.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import pathlib

from scripts.lib.ref_manifest import Manifest
from scripts.lib.ref_classify import classify_url
from scripts.lib.ref_extract import extract_links_and_images, extract_pdf_links
from scripts.lib.ref_ocr import ocr_image
from scripts.lib.ref_fetch import fetch_drive_file, fetch_pdf

_TERMINAL = {"jira", "api", "external"}
_FETCHABLE = {"gdoc", "gsheet", "gslide"}


def _ocr_images(images, ocr) -> None:
    for img in images:
        pathlib.Path(img + ".txt").write_text(ocr(img), encoding="utf-8")


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")


def _seed_links(manifest, links, depth, referenced_from) -> int:
    n = 0
    for url in links:
        ref_type, file_id = classify_url(url)
        if manifest.add_if_new(url, ref_type, depth, referenced_from, file_id=file_id):
            if ref_type in _TERMINAL:
                manifest.update_status(url, "terminal")
            n += 1
    return n


def seed_from_docx(manifest, docx_path, image_dir, ocr=ocr_image) -> int:
    links, images = extract_links_and_images(docx_path, image_dir)
    _ocr_images(images, ocr)  # the root doc's own screenshots are highest-value — don't lose them
    return _seed_links(manifest, links, depth=1, referenced_from="ROOT")


def crawl(manifest, files_dir, image_dir,
          fetcher=fetch_drive_file, extractor=extract_links_and_images, ocr=ocr_image,
          pdf_fetcher=fetch_pdf, pdf_linker=extract_pdf_links) -> dict:
    while True:
        ref = manifest.next_discovered()
        if ref is None:
            break
        url, rtype, depth = ref["url"], ref["ref_type"], ref["depth"]

        if rtype not in _FETCHABLE:        # jira / api / external → recorded, never fetched
            manifest.update_status(url, "terminal")
            continue

        result = fetcher(ref["file_id"], rtype, files_dir)
        if result.status != "fetched":
            manifest.update_status(url, result.status, error=result.error)
            continue
        manifest.update_status(url, "fetched", local_path=result.local_path,
                               sha256=result.sha256, fetched_at=_now())

        links, images = extractor(result.local_path, image_dir)
        _ocr_images(images, ocr)

        # Link-recall safety net: union with a throwaway PDF render (Task 7b).
        pdf_path = pdf_fetcher(ref["file_id"], files_dir)
        if pdf_path:
            links = list(links) + pdf_linker(pdf_path)
            try:
                pathlib.Path(pdf_path).unlink()   # PDF is for links only — not archived
            except OSError:
                pass

        _seed_links(manifest, links, depth + 1, referenced_from=url)
        manifest.update_status(url, "done")
    return manifest.report()


def main(argv=None):
    ap = argparse.ArgumentParser(description="Crawl the SE-runbook reference graph.")
    ap.add_argument("--root", required=True, help="Path to the root WIS-Configurations .docx")
    ap.add_argument("--out", default="raw/se-runbook", help="Output dir (manifest + files + images)")
    ap.add_argument("--retry-denied", action="store_true",
                    help="Reopen previously access_denied files (run after access is granted)")
    args = ap.parse_args(argv)

    out = pathlib.Path(args.out)
    files_dir = out / "files"
    image_dir = out / "images"
    manifest = Manifest(str(out / "manifest.sqlite"))

    if args.retry_denied:
        n = manifest.requeue_denied()
        print(f"requeued {n} previously access-denied files for retry")

    seeded = seed_from_docx(manifest, args.root, str(image_dir))
    print(f"seeded {seeded} new references from root")
    report = crawl(manifest, str(files_dir), str(image_dir))

    print("\n=== COVERAGE REPORT ===")
    for status, n in sorted(report.items()):
        print(f"  {status:14} {n}")
    print(f"  complete: {manifest.coverage_complete()}")
    holes = manifest.access_holes()
    if holes:
        print(f"\n⚠️  {len(holes)} ACCESS HOLES (request access, then re-run):")
        for h in holes:
            print(f"  - {h['url']}  (from {h['referenced_from']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `venv/bin/pytest tests/test_crawl_references.py -v`
Expected: 2 passed

- [ ] **Step 5: Run the full crawler test suite**

Run: `venv/bin/pytest tests/test_ref_manifest.py tests/test_ref_classify.py tests/test_ref_extract.py tests/test_ref_ocr.py tests/test_ref_fetch.py tests/test_crawl_references.py -v`
Expected: all green (28 tests)

- [ ] **Step 6: Commit**

```bash
git add scripts/crawl_references.py tests/test_crawl_references.py
git commit -m "feat(crawler): orchestrator, seed-from-docx, CLI + coverage report"
```

---

## Task 9: Live smoke run + gitignore output

**Files:**
- Modify: `.gitignore`
- (Runtime output only — no source change)

**Interfaces:** none — this validates the assembled system against the real document and Drive.

- [ ] **Step 1: Gitignore the crawl output (verbatim raw archive is large + may hold sensitive screenshots)**

```bash
printf '\n# SE-runbook crawl output (verbatim archive; regenerate via scripts/crawl_references.py)\nraw/se-runbook/\n' >> .gitignore
```

- [ ] **Step 2: Copy the root DOCX into the repo's raw archive (verbatim, never edited)**

```bash
mkdir -p raw/se-runbook
cp "$HOME/Downloads/WIS-Configurations(ETS,Employee App, Guard app,Sanitisation App).docx" \
   "raw/se-runbook/WIS-Configurations-ETS-EmployeeApp-GuardApp-SanitisationApp.docx"
```

- [ ] **Step 3: Verify backend is not running (reload safety), then run the crawler for real**

```bash
ps aux | grep -i uvicorn | grep -v grep || echo "backend not running — safe"
venv/bin/python -m scripts.crawl_references \
  --root "raw/se-runbook/WIS-Configurations-ETS-EmployeeApp-GuardApp-SanitisationApp.docx" \
  --out raw/se-runbook
```
Expected: a coverage report. `complete: True` once the frontier drains. The ~6 known access-denied files appear under "ACCESS HOLES". (This run makes real Vision/OCR calls and real rclone calls — expect it to take a few minutes and incur some API cost.)

- [ ] **Step 4: Inspect the manifest to confirm depth was reached**

```bash
sqlite3 raw/se-runbook/manifest.sqlite \
  "SELECT ref_type, status, COUNT(*) FROM refs GROUP BY ref_type, status ORDER BY ref_type;"
sqlite3 raw/se-runbook/manifest.sqlite \
  "SELECT MAX(depth) AS max_depth FROM refs;"
```
Expected: `gsheet`/`gdoc`/`gslide` rows in `done`, `jira`/`api`/`external` in `terminal`, the inaccessible files in `access_denied`, and `max_depth >= 2` (proves nested sheet/doc links were followed).

- [ ] **Step 5: Commit the gitignore change**

```bash
git add .gitignore
git commit -m "chore(crawler): gitignore raw/se-runbook crawl output"
```

---

## Self-Review

- **Spec coverage:** completeness ledger (Task 1) ✓; depth into every sheet tab + cell + slide, incl. grouped shapes (Tasks 4, 5) ✓; **link-recall guarantee via dual rendering** — structured links + bare-text URLs + PDF annotation/text scrape, unioned (Tasks 4, 5, 7b, 8) ✓; screenshot OCR incl. the root doc's own images (Tasks 6, 8) ✓; access holes surfaced not silently dropped, and retryable after access granted (Tasks 1, 7, 8, 9) ✓; rclone by-ID fetch, no Drive restructure (Task 7) ✓; idempotent re-run via `add_if_new` dedupe + `coverage_complete` (Tasks 1, 8) ✓; Jira/API recorded-not-fetched (Tasks 2, 8) ✓.
- **Export-fidelity risk (verified 2026-06-25):** Google Office export can drop UI-created links. Mitigated, not assumed away: every Google file is read in two independent renderings (Office + PDF) and their link sets unioned. A link must be invisible in *both* a structured parse AND a PDF render to be missed.
- **Placeholder scan:** no TBD/"handle errors"/"similar to" — every code step is complete and runnable.
- **Type consistency:** `FetchResult.status` strings (`fetched`/`access_denied`/`error`) match the orchestrator's branches; manifest statuses (`discovered`/`fetched`/`done`/`terminal`/`access_denied`/`error`) are consistent across Tasks 1 and 8; `extract_links_and_images(path, image_dir) -> (urls, images)` identical in Tasks 3–5 and 8; `fetch_pdf`/`extract_pdf_links` signatures match between Task 7b and the Task 8 orchestrator injection.

---

## Downstream phases (process, NOT part of this code plan)

These consume the crawler's output and follow the **existing CLAUDE.md workflows** — they are content/curation work, executed interactively, not TDD code. Listed so the whole picture is visible.

**Parallel Track — start NOW, no dependency on the crawler:**
- **Ingest the main DOCX (node #0)** via the CLAUDE.md §4 9-step INGEST. It is 132 pages of standalone SE knowledge. Highest-value content; don't let it wait on access requests.
- **Jira backfill:** the 17 referenced tickets missing from `tickets.sqlite` (PB-20759, PB-44169, PB-47717, PB-49080, PB-49826, PB-49828, PB-52044, SE-47098, TO-10593/10903/11510/14755/6362/6706/8197, TS-22716, PB-46642) — pull via `scripts/jira_daily_sync.py --incremental`.

**Phase B — Run crawl to fixpoint** (Task 9). Review the coverage report; send the access-hole list to the SE team for the ~6 files. After access is granted, re-run with `--retry-denied`, which flips the `access_denied` rows back to `discovered` so they (and any newly-reachable subtree behind them) are fetched. Already-`done` files are skipped — only the newly-reachable work runs.

**Phase C — Schema evolution (CLAUDE.md change):** add a `runbooks/` page type. Define frontmatter (`type: runbook`, `module(s)`, `team: SE`, `source`, `last_updated`) and required sections (Purpose, Prerequisites, Ordered Steps with exact API calls + config values, Validation, Related Jira, Linked raw evidence). Add it to CLAUDE.md §2 and the `wiki/index.md` table layout. Use the `superpowers:improve-codebase-architecture` lens to keep it consistent with existing page types.

**Phase D — Ingest crawled content, per topic:** for each of the ~8 SE topics (ETS setup, premise/capacity creation, parking, floor-plan upload, guard-user creation, seat sanitization, meal booking, vaccination, meeting-room/EU specifics), run the 9-step INGEST against the relevant fetched files + OCR sidecars. Create a `wiki/runbooks/<topic>.md`, enrich the existing `modules/` + `configs/` pages with any new properties/endpoints/defaults (using the §4 diff-and-decide rule — preserve existing curation), cross-link both ways, and cite back to `raw/se-runbook/`. Apply the **Conflict & Recency Resolution Policy** (next section) to every fact that touches an existing page. Pause for review per topic (not per file) — and that review is a light sanity-check of the capture/auto-resolution summary, NOT a domain-truth adjudication. The verbatim `raw/se-runbook/` archive is the zero-loss safety net regardless of curation choices.

**Phase E — (optional) Drive folder mirror:** generate the human-readable `Conwo WorkInSync Docs/se-runbook/` folder structure FROM the manifest (grouped by topic), as an output/presentation mirror — not a prerequisite for any of the above.

---

## Conflict & Recency Resolution Policy

**Governs:** Phase D ingestion **and** query-time answers.
**Principle:** **Evidence is the judge — never the maintainer.** A contradiction between the incoming SE doc and an existing wiki page is NOT settled by assuming either side wins, and is NOT punted to a human who lacks context. It is settled by evidence: dates, Jira tickets, and (for configs) the live system. Ingestion **never blocks** waiting for someone to know domain truth.

### The resolution ladder (top to bottom — most conflicts stop at rung 1–2)

**Rung 1 — Dates & tickets decide (automatic).**
Compare datable evidence on both claims: referenced Jira ticket resolution dates, the SE doc's date, the existing page's `last_updated` + source date. Newer *resolved* evidence wins (a resolved 2026 ticket beats a 2023 screenshot). Direction can go **either way** — an older incoming doc **loses** to a newer wiki claim and is demoted to history; it never overwrites the newer claim. (This is the protection against the "old doc downgrades the wiki" risk.)

**Rung 2 — The live product decides (automatic; configs only).**
For PMS config properties, the running system is ground truth. Run `pms_diagnose_property` / `scripts/pms_debug.py` for a BUID to fetch the **actual live value**. Doc and wiki can both be stale; the live value cannot. Final arbiter for config conflicts. (Not applicable to procedural/runbook steps — those use rungs 1, 3, 4.)

**Rung 3 — Show both (evidence silent, no live check).**
Do NOT force a pick. Record both claims with dates + evidence; Conwo surfaces both at query time with calibrated Confidence. The person asking applies their own situational context — usually better than a maintainer guessing months earlier. "Can't decide yet" is an honest, useful answer, not a failure.

**Rung 4 — Route to the owning team (last resort; never the maintainer; never blocking).**
If it matters and is still ambiguous, flag it into the unresolved-conflicts list, tagged with the likely owning team / doc author. Resolved opportunistically as newer evidence arrives. Never blocks ingestion or queries.

### Ingestion-time behavior (what Phase D does per fact)

| Situation | Action |
|-----------|--------|
| No conflict | Add/augment the existing page (default bias: preserve existing curation, §4 diff-and-decide) |
| Conflict, rung 1 dates it | Write **Current** + keep loser as **Previously** (format below). Automatic. |
| Conflict, config, rung 2 live value available | Record the live value as current truth + keep both documented claims as history |
| Conflict, unresolved | Write a dual-claim block (`status: unresolved`) + append a row to the unresolved-conflicts list |

**Ingestion never blocks on domain judgment.** The only human gate is a per-topic approval where the maintainer reviews a **summary** — e.g. *"14 conflicts: 9 date-resolved, 2 live-config-checked, 3 shown-both"* — and confirms the *capture* looks sane. The maintainer does not adjudicate truth.

### On-page format — resolved-by-date conflict

```markdown
### Guard OTP before registration
- **Current (2026):** Required before registration. _Evidence: PB-49903 (resolved 2026-03) + wiki PRD._
- **Previously (2023):** Optional. _Evidence: SE runbook (2023)._
- _Changed optional → required; both retained for historical awareness._
```

### On-page format — unresolved conflict

```markdown
### <topic>
> ⚠️ Unresolved conflict — both claims shown; evidence cannot date-rank them.
- **Claim A (wiki — source X, undated):** ...
- **Claim B (SE doc — 2023):** ...
- _Status: unresolved · routed to <owning team> · tracked in unresolved-conflicts._
```

### Query-time behavior (maps onto the existing CLAUDE.md §5 answer template)

- **Resolved** → "Latest evidence" = Current, "Historical evidence" = Previously, "Conflict / evolution" explains the change.
- **Unresolved** → both surfaced under their buckets; **Confidence: Low/Medium**; answer states evidence is mixed and shows each claim's date.
- **Config questions** → additionally run the live `pms_diagnose_property` check so the user gets the **actual current value**, not just documented claims.

### Unresolved-conflicts tracking

Maintain `wiki/unresolved-conflicts.md` (or reuse the feedback mechanism): topic, both claims, evidence, owning team, date flagged. Cleared over time as evidence arrives. This is what makes "show both now, resolve later" safe — nothing is lost, nothing blocks, and the maintainer is never the bottleneck.

> **Reframed goal:** not "100% omniscient" (no system knows every current truth), but **100% honest** — never confidently wrong; always shows what's known, how fresh it is, what it used to be, and (for configs) what's live right now.

---

## Revision 2 (2026-06-25) — Main-doc tabs, context-linked screenshots, instructional OCR, exhaustive capture

**These refinements update the tasks/phases above; where they conflict, this section wins.** Driven by review of the real document + four user decisions.

### Verified facts (empirical, this session)
- Main-doc `.docx` is **byte-identical** to a fresh rclone fetch (3,536 paras / 133,768 chars / 65 headings) — the download is a faithful, complete export.
- The **34 Google-Doc tabs survive in the `.docx` as headings** (9× Heading-1 + 56× Heading-4). All 23 sampled sidebar tab-names matched headings **23/23**. → **The Docs API is NOT needed; the `.docx` is the authoritative source for content AND tab structure.** (rclone's Docs-API probe returned 403 — API disabled in rclone's GCP project — confirming we must not depend on it.)
- All **80 inline images get a real section heading** when tracking *all* heading levels (0 orphans). → screenshot→section context is recoverable from the `.docx`.
- ETS spreadsheet (`1WpEu4vW…`) has **11 real tabs**; the crawler walks all of them. Deep nesting confirmed.

### R1 — Main-doc extraction = node #0 (replaces the simple `seed_from_docx`)
Parse the `.docx` into its ~34-tab skeleton using headings (H1 + H4) as section boundaries. Per section capture ordered text, tables, and inline images **in document order**.
- **Tab-coverage proof:** assert every tab name from the doc's tab list appears as a heading; report any missing. This is node #0's completeness guarantee, analogous to the link checklist for the crawl.

### R2 — Manifest also tracks screenshots (extends Task 1)
Add an `images` table: `image_path, source_file, section, nearby_text, ocr_status, ocr_text_path`. `coverage_complete()` additionally requires every image row `ocr_status='done'`. → **screenshot coverage becomes provable, exactly like links.**

### R3 — Extractors return images WITH context (extends Tasks 3/4/5)
`extract_links_and_images` also returns, per image, a `context` dict:
- **docx:** `{section: <nearest heading, ALL levels>, nearby_text: <preceding non-empty paragraph(s)>}`
- **pptx:** `{slide_title, slide_text}`
- **xlsx:** `{tab_name, nearby_cells}`

### R4 — Instructional OCR prompt (replaces Task 6's generic prompt)
Vision prompt becomes: *"This is a screenshot from an SE configuration runbook. State (1) what tool/screen is shown (Postman, browser, admin UI), (2) the action being performed (GET/PUT/click/select), (3) what to look for or do next. Transcribe all visible text, URLs, and config keys verbatim. CRITICAL: treat example values — BUIDs like `tata-TCPOC`, office names, GUIDs, phone numbers — as ILLUSTRATIVE PLACEHOLDERS; label them 'example', never as literal config."*

### R5 — Runbook template (Phase C), now with instructional steps + Notes & Gotchas
`wiki/runbooks/<topic>.md` sections: Purpose · Prerequisites · **Ordered Steps** (each: tool + action + endpoint/URL + example-value-flagged-as-placeholder) · **Screenshots** (transcription + what it shows) · Validation · **Notes & Gotchas** (loose-but-critical details that fit no single step) · Related Jira · Linked raw evidence.
Granularity (your decision): **one runbook per real topic, merging micro-tabs** (e.g. `isWelcomeEmailEnabled=false`) into their parent → ~15–20 runbooks from the 34 tabs.

### R6 — Exhaustive capture, not just topic buckets (Phase D)
Every fact is captured, including orphans: anything that fits no step lands in that topic's **Notes & Gotchas** (your decision). Nothing is dropped for not fitting the structure; the verbatim vault remains the zero-loss backstop.

### R7 — Ingestion is Claude-agentic, NOT the UI code pipeline (decisive)
The wiki (`.md` pages, nodes, relations) is authored by **Claude in the terminal** following the CLAUDE.md §4 9-step process with the full document in context — **NOT** the UI 2-phase pipeline (`backend/ingest_api.py`), which extracts to a truncatable text blob and writes pages from 200-char plan previews. Division of labour:
- **Crawler (code) = collector only** — fetch files → vault, build the coverage checklist, bulk pre-OCR images. Deterministic, re-runnable, provides the completeness proof. **Never writes wiki pages.**
- **Claude (agentic) = author** — reads collected content with full context, views screenshots **in-context** (R4), applies the 9-step + Conflict & Recency ladder + cross-module §7 checks + Notes & Gotchas, and writes every page. You approve per topic. This is where `.md`/node/relation quality comes from.
- **UI pipeline (`ingest_api.py`) = unused** for this doc (remains for fast routine small-doc ingestion).

This beats both alternatives: full-context authoring (quality, no truncation) **and** the crawler's checklist (provable completeness — plain terminal ingestion has no coverage proof). Note: the crawler is a *tool Claude uses* for repetitive fetching; all knowledge synthesis remains Claude's.

### R4 addendum — Claude reads screenshots in-context during authoring
Beyond the bulk pre-OCR (the searchable coverage layer, logged in the manifest), Claude reads key screenshots directly (as a vision model) **while authoring the relevant runbook step**, interpreting them with the surrounding procedure in mind — higher fidelity than blind pre-OCR alone.
