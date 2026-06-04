# UI Document Ingestion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a `/ingest` UI route where any authenticated user can upload a document (PDF, DOCX, XLSX, MD, TXT), review an AI-generated ingestion plan, approve it, and watch wiki pages be created/updated via SSE streaming — all via Anthropic API only, no Claude Code subprocess.

**Architecture:** Two-phase agent pattern. Phase 1 runs a read-only agent (extraction + wiki read tools) that returns a structured JSON plan. User reviews and approves. Phase 2 runs a write agent that executes the plan literally and streams per-operation progress via SSE.

**Tech Stack:** Python 3 / FastAPI / Anthropic SDK (`anthropic`) / pdfplumber / python-docx / openpyxl — backend. Angular 21 / TypeScript / RxJS signals — frontend.

**Spec:** `docs/superpowers/specs/2026-06-04-ui-document-ingestion-design.md`

---

## File Map

**New backend files:**
- `backend/document_extractor.py` — PDF/DOCX/XLSX/text extraction utilities
- `backend/ingest_service.py` — mutex, in-memory session state, phase orchestration, tool registries
- `backend/ingest_api.py` — 3 FastAPI endpoints: upload, plan, execute
- `backend/tools/wiki_write_tools.py` — 5 write tools (create, edit, append, update_frontmatter, rebuild_index)
- `backend/tools/wiki_read_tools.py` — 2 new read tools (list_pages, check_duplicate)

**Modified backend files:**
- `backend/api.py` — include ingest router + add `raw/modules/_uploads/` to `.gitignore` note
- `backend/tools/__init__.py` — register `wiki_list_pages` and `wiki_check_duplicate` into main registry

**New test files:**
- `tests/test_document_extractor.py`
- `tests/test_wiki_write_tools.py`
- `tests/test_wiki_read_tools.py`
- `tests/test_ingest_service.py`
- `tests/test_ingest_api.py`

**New frontend files:**
- `frontend/src/app/features/ingest/ingest.ts` — main page, step state machine
- `frontend/src/app/features/ingest/ingest.scss`
- `frontend/src/app/features/ingest/upload-step.ts` — drag-drop + form
- `frontend/src/app/features/ingest/plan-step.ts` — plan review + approve/cancel
- `frontend/src/app/features/ingest/execute-step.ts` — SSE streaming progress + result

**Modified frontend files:**
- `frontend/src/app/app.routes.ts` — add `/ingest` route
- `frontend/src/app/app.html` — add nav link
- `frontend/src/app/core/api.service.ts` — add `uploadFile`, `planIngest`, `executeIngest` methods

---

## Task 1: Document Extractor

**Files:**
- Create: `backend/document_extractor.py`
- Create: `tests/test_document_extractor.py`

First check that extraction libraries are available:

- [ ] **Step 1: Verify dependencies**

```bash
cd /Users/rudrakhare/Desktop/my-wiki/org-wiki
grep -E "pdfplumber|python-docx|openpyxl" requirements.txt
```

Expected: all three present. If any missing, add them to `requirements.txt` and run `pip install -r requirements.txt`.

- [ ] **Step 2: Write failing tests**

Create `tests/test_document_extractor.py`:

```python
"""Tests for document_extractor — uses real tiny fixtures."""
import json
import os
import tempfile
from pathlib import Path

import pytest

# ── helpers to create tiny real files ──────────────────────────────────────


def make_txt(tmp: Path, name: str, content: str) -> Path:
    p = tmp / name
    p.write_text(content, encoding="utf-8")
    return p


def make_docx(tmp: Path, name: str, text: str) -> Path:
    from docx import Document  # python-docx

    doc = Document()
    doc.add_paragraph(text)
    p = tmp / name
    doc.save(str(p))
    return p


def make_xlsx(tmp: Path, name: str) -> Path:
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "Sheet1"
    ws.append(["Name", "Value"])
    ws.append(["foo", "bar"])
    p = tmp / name
    wb.save(str(p))
    return p


# ── tests ───────────────────────────────────────────────────────────────────


@pytest.fixture
def tmp(tmp_path):
    return tmp_path


def test_extract_txt(tmp):
    from backend.document_extractor import extract_text_file

    p = make_txt(tmp, "hello.txt", "Hello world\nLine two")
    result = extract_text_file(str(p))
    assert result["text"] == "Hello world\nLine two"
    assert result["char_count"] == 20


def test_extract_docx(tmp):
    from backend.document_extractor import extract_docx

    p = make_docx(tmp, "doc.docx", "Hello from docx")
    result = extract_docx(str(p))
    assert "Hello from docx" in result["text"]
    assert result["char_count"] > 0
    assert isinstance(result["has_tables"], bool)


def test_extract_xlsx(tmp):
    from backend.document_extractor import extract_xlsx

    p = make_xlsx(tmp, "wb.xlsx")
    result = extract_xlsx(str(p))
    assert len(result["sheets"]) == 1
    assert result["sheets"][0]["name"] == "Sheet1"
    assert result["sheets"][0]["rows"][0] == ["Name", "Value"]


def test_extract_md(tmp):
    from backend.document_extractor import extract_text_file

    p = make_txt(tmp, "notes.md", "# Title\n\nBody text")
    result = extract_text_file(str(p))
    assert "# Title" in result["text"]


def test_truncation(tmp):
    from backend.document_extractor import extract_text_file

    big = "x" * 60_000
    p = make_txt(tmp, "big.txt", big)
    result = extract_text_file(str(p))
    assert len(result["text"]) == 50_000
    assert result.get("truncated") is True


def test_unsupported_extension(tmp):
    from backend.document_extractor import extract_document, UnsupportedFileType

    p = make_txt(tmp, "file.xyz", "data")
    with pytest.raises(UnsupportedFileType):
        extract_document(str(p))


def test_dispatch_by_extension(tmp):
    from backend.document_extractor import extract_document

    p = make_txt(tmp, "readme.txt", "plain text")
    result = extract_document(str(p))
    assert "plain text" in result["text"]
```

- [ ] **Step 3: Run tests to confirm they fail**

```bash
cd /Users/rudrakhare/Desktop/my-wiki/org-wiki
python -m pytest tests/test_document_extractor.py -v 2>&1 | head -30
```

Expected: `ModuleNotFoundError: No module named 'backend.document_extractor'`

- [ ] **Step 4: Implement `backend/document_extractor.py`**

```python
"""Document text extraction for ingestion pipeline.

Supports: PDF (pdfplumber), DOCX (python-docx), XLSX (openpyxl),
          MD / TXT / plain text (built-in).

All extractors truncate output to MAX_CHARS (50 000) to stay within
the LLM context budget.
"""
from __future__ import annotations

import pathlib

MAX_CHARS = 50_000

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".doc", ".xlsx", ".xls", ".md", ".txt", ".rtf"}


class UnsupportedFileType(ValueError):
    pass


def extract_document(file_path: str) -> dict:
    """Dispatch to the right extractor based on file extension."""
    ext = pathlib.Path(file_path).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise UnsupportedFileType(f"Unsupported file type: {ext!r}")
    if ext == ".pdf":
        return extract_pdf(file_path)
    if ext in {".docx", ".doc"}:
        return extract_docx(file_path)
    if ext in {".xlsx", ".xls"}:
        return extract_xlsx(file_path)
    # .md, .txt, .rtf — plain text
    return extract_text_file(file_path)


def extract_pdf(file_path: str) -> dict:
    import pdfplumber

    pages_text: list[str] = []
    with pdfplumber.open(file_path) as pdf:
        page_count = len(pdf.pages)
        for page in pdf.pages:
            t = page.extract_text() or ""
            pages_text.append(t)

    full = "\n".join(pages_text)
    truncated = len(full) > MAX_CHARS
    return {
        "text": full[:MAX_CHARS],
        "page_count": page_count,
        "char_count": len(full),
        "truncated": truncated,
    }


def extract_docx(file_path: str) -> dict:
    from docx import Document  # python-docx

    doc = Document(file_path)
    parts: list[str] = []
    for para in doc.paragraphs:
        if para.text.strip():
            parts.append(para.text)
    has_tables = bool(doc.tables)
    for table in doc.tables:
        for row in table.rows:
            row_text = " | ".join(c.text.strip() for c in row.cells if c.text.strip())
            if row_text:
                parts.append(row_text)

    full = "\n".join(parts)
    truncated = len(full) > MAX_CHARS
    return {
        "text": full[:MAX_CHARS],
        "char_count": len(full),
        "has_tables": has_tables,
        "truncated": truncated,
    }


def extract_xlsx(file_path: str) -> dict:
    from openpyxl import load_workbook

    wb = load_workbook(file_path, read_only=True, data_only=True)
    sheets: list[dict] = []
    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        rows: list[list[str]] = []
        for row in ws.iter_rows(values_only=True):
            str_row = [str(cell) if cell is not None else "" for cell in row]
            if any(c.strip() for c in str_row):
                rows.append(str_row)
        sheets.append({"name": sheet_name, "rows": rows})
    wb.close()
    return {"sheets": sheets}


def extract_text_file(file_path: str) -> dict:
    text = pathlib.Path(file_path).read_text(encoding="utf-8", errors="replace")
    truncated = len(text) > MAX_CHARS
    return {
        "text": text[:MAX_CHARS],
        "char_count": len(text),
        "truncated": truncated,
    }
```

- [ ] **Step 5: Run tests to confirm they pass**

```bash
python -m pytest tests/test_document_extractor.py -v
```

Expected: all 7 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/document_extractor.py tests/test_document_extractor.py
git commit -m "feat(ingest): document extractor — PDF/DOCX/XLSX/text with 50k truncation"
```

---

## Task 2: New Wiki Read Tools

**Files:**
- Create: `backend/tools/wiki_read_tools.py`
- Create: `tests/test_wiki_read_tools.py`
- Modify: `backend/tools/__init__.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_wiki_read_tools.py`:

```python
"""Tests for wiki_list_pages and wiki_check_duplicate tools."""
import pytest
from unittest.mock import patch, MagicMock


def test_list_pages_modules():
    from backend.tools.wiki_read_tools import _wiki_list_pages_handler

    with patch("backend.tools.wiki_read_tools.wiki_retriever") as mock_r:
        mock_page = MagicMock()
        mock_page.path = "wiki/modules/visitor-management.md"
        mock_page.title = "Visitor Management"
        mock_r.all_pages.return_value = [mock_page]

        result = _wiki_list_pages_handler({"category": "modules"})

    assert result["total"] == 1
    assert result["pages"][0]["path"] == "wiki/modules/visitor-management.md"
    assert result["pages"][0]["slug"] == "visitor-management"


def test_list_pages_all():
    from backend.tools.wiki_read_tools import _wiki_list_pages_handler

    with patch("backend.tools.wiki_read_tools.wiki_retriever") as mock_r:
        pages = []
        for cat in ["modules", "entities", "sources"]:
            m = MagicMock()
            m.path = f"wiki/{cat}/foo.md"
            m.title = "Foo"
            pages.append(m)
        mock_r.all_pages.return_value = pages

        result = _wiki_list_pages_handler({})

    assert result["total"] == 3


def test_list_pages_filters_by_category():
    from backend.tools.wiki_read_tools import _wiki_list_pages_handler

    with patch("backend.tools.wiki_read_tools.wiki_retriever") as mock_r:
        module_page = MagicMock()
        module_page.path = "wiki/modules/sso.md"
        module_page.title = "SSO"
        entity_page = MagicMock()
        entity_page.path = "wiki/entities/user.md"
        entity_page.title = "User"
        mock_r.all_pages.return_value = [module_page, entity_page]

        result = _wiki_list_pages_handler({"category": "modules"})

    assert result["total"] == 1
    assert result["pages"][0]["slug"] == "sso"


def test_check_duplicate_exists():
    from backend.tools.wiki_read_tools import _wiki_check_duplicate_handler
    import tempfile, os

    with tempfile.TemporaryDirectory() as tmp:
        wiki_dir = os.path.join(tmp, "wiki", "modules")
        os.makedirs(wiki_dir)
        open(os.path.join(wiki_dir, "visitor-management.md"), "w").close()

        with patch("backend.tools.wiki_read_tools.WIKI_ROOT", tmp):
            result = _wiki_check_duplicate_handler(
                {"slug": "visitor-management", "category": "modules"}
            )

    assert result["exists"] is True
    assert "visitor-management.md" in result["path"]


def test_check_duplicate_not_exists():
    from backend.tools.wiki_read_tools import _wiki_check_duplicate_handler
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        with patch("backend.tools.wiki_read_tools.WIKI_ROOT", tmp):
            result = _wiki_check_duplicate_handler(
                {"slug": "brand-new-module", "category": "modules"}
            )

    assert result["exists"] is False
    assert result["path"] is None
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
python -m pytest tests/test_wiki_read_tools.py -v 2>&1 | head -20
```

Expected: `ModuleNotFoundError: No module named 'backend.tools.wiki_read_tools'`

- [ ] **Step 3: Implement `backend/tools/wiki_read_tools.py`**

```python
"""New wiki read tools for the ingestion phase-1 agent.

wiki_list_pages   — list all pages in a category (modules, entities, etc.)
wiki_check_duplicate — check whether a slug already exists on disk
"""
from __future__ import annotations

import os
import pathlib

from backend import wiki_retriever

# Resolved at import time so tests can patch it
WIKI_ROOT = str(pathlib.Path(__file__).resolve().parents[2])

CATEGORY_DIRS = {
    "modules": "wiki/modules",
    "entities": "wiki/entities",
    "sources": "wiki/sources",
    "concepts": "wiki/concepts",
    "decisions": "wiki/decisions",
    "cross-module": "wiki/cross-module",
    "configs": "wiki/configs",
    "integrations": "wiki/integrations",
    "persons": "wiki/persons",
    "patterns": "wiki/patterns",
}

# ── wiki_list_pages ──────────────────────────────────────────────────────────

WIKI_LIST_PAGES_SCHEMA: dict = {
    "name": "wiki_list_pages",
    "description": (
        "List all existing wiki pages, optionally filtered by category "
        "(modules, entities, sources, concepts, decisions, cross-module, configs). "
        "Use this at the start of ingestion to know what already exists."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "category": {
                "type": "string",
                "description": (
                    "Filter to one category folder. "
                    "One of: modules, entities, sources, concepts, decisions, "
                    "cross-module, configs, integrations, persons. "
                    "Omit to list all pages."
                ),
            }
        },
        "required": [],
    },
}


def _wiki_list_pages_handler(inp: dict) -> dict:
    category = inp.get("category", "").strip().lower()
    all_pages = wiki_retriever.all_pages()

    if category and category in CATEGORY_DIRS:
        prefix = f"wiki/{category}/"
        filtered = [p for p in all_pages if p.path.startswith(prefix)]
    else:
        filtered = all_pages

    pages = []
    for p in filtered:
        slug = pathlib.Path(p.path).stem
        pages.append({"path": p.path, "title": p.title, "slug": slug})

    return {"pages": pages, "total": len(pages)}


# ── wiki_check_duplicate ─────────────────────────────────────────────────────

WIKI_CHECK_DUPLICATE_SCHEMA: dict = {
    "name": "wiki_check_duplicate",
    "description": (
        "Check whether a wiki page already exists for a given slug and category. "
        "Always call this before proposing to create a new page."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "slug": {
                "type": "string",
                "description": "The page slug, e.g. 'visitor-management'",
            },
            "category": {
                "type": "string",
                "description": (
                    "The category folder to check. "
                    "One of: modules, entities, sources, concepts, decisions, "
                    "cross-module, configs."
                ),
            },
        },
        "required": ["slug", "category"],
    },
}


def _wiki_check_duplicate_handler(inp: dict) -> dict:
    slug = str(inp.get("slug", "")).strip()
    category = str(inp.get("category", "")).strip().lower()

    if not slug:
        return {"error": "slug is required", "code": "missing_input"}
    if category not in CATEGORY_DIRS:
        return {"error": f"Unknown category: {category!r}", "code": "unknown_category"}

    rel_dir = CATEGORY_DIRS[category]
    candidate = pathlib.Path(WIKI_ROOT) / rel_dir / f"{slug}.md"
    exists = candidate.exists()
    return {
        "exists": exists,
        "path": str(candidate.relative_to(WIKI_ROOT)) if exists else None,
    }
```

- [ ] **Step 4: Register in `backend/tools/__init__.py`**

Open `backend/tools/__init__.py`. Find where existing tools are registered in `build_registry()`. Add the two new tools:

```python
# At the top with other imports:
from backend.tools.wiki_read_tools import (
    WIKI_LIST_PAGES_SCHEMA, _wiki_list_pages_handler,
    WIKI_CHECK_DUPLICATE_SCHEMA, _wiki_check_duplicate_handler,
)

# Inside build_registry(), after existing wiki tool registrations:
r.register(WIKI_LIST_PAGES_SCHEMA, _wiki_list_pages_handler)
r.register(WIKI_CHECK_DUPLICATE_SCHEMA, _wiki_check_duplicate_handler)
```

- [ ] **Step 5: Run tests to confirm they pass**

```bash
python -m pytest tests/test_wiki_read_tools.py -v
```

Expected: all 5 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/tools/wiki_read_tools.py tests/test_wiki_read_tools.py backend/tools/__init__.py
git commit -m "feat(ingest): add wiki_list_pages and wiki_check_duplicate tools"
```

---

## Task 3: Wiki Write Tools

**Files:**
- Create: `backend/tools/wiki_write_tools.py`
- Create: `tests/test_wiki_write_tools.py`

These tools are ONLY registered in the Phase 2 ingest registry — never in the main query registry.

- [ ] **Step 1: Write failing tests**

Create `tests/test_wiki_write_tools.py`:

```python
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
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
python -m pytest tests/test_wiki_write_tools.py -v 2>&1 | head -20
```

Expected: `ModuleNotFoundError: No module named 'backend.tools.wiki_write_tools'`

- [ ] **Step 3: Implement `backend/tools/wiki_write_tools.py`**

```python
"""Wiki write tools — only registered in the Phase-2 ingest agent registry.

NEVER register these in the main query tool registry.
Safety properties:
- All paths validated to be inside wiki/ (no traversal)
- wiki_create_page refuses to overwrite existing files
- wiki_edit_page requires unique old_str (no silent multi-replace)
- wiki_rebuild_index calls wiki_retriever.build_index() in-process
  (does NOT touch backend/api.py — avoids the reload/wiki-destruction risk)
"""
from __future__ import annotations

import pathlib
import re

from backend import wiki_retriever

WIKI_ROOT = str(pathlib.Path(__file__).resolve().parents[2])
_WIKI_SUBDIR = str(pathlib.Path(WIKI_ROOT) / "wiki")

LIST_FIELDS = {"depends_on", "used_by", "modules", "servers"}


def _safe_path(rel_path: str) -> pathlib.Path | None:
    """Return resolved Path if rel_path is inside wiki/, else None."""
    candidate = (pathlib.Path(WIKI_ROOT) / rel_path).resolve()
    try:
        candidate.relative_to(pathlib.Path(_WIKI_SUBDIR).resolve())
        return candidate
    except ValueError:
        return None


# ── wiki_create_page ─────────────────────────────────────────────────────────

WIKI_CREATE_PAGE_SCHEMA: dict = {
    "name": "wiki_create_page",
    "description": (
        "Create a new wiki markdown page. Refuses to overwrite an existing file. "
        "Path must be inside wiki/ (e.g. 'wiki/modules/visitor-management.md')."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Relative path, e.g. wiki/modules/foo.md"},
            "frontmatter": {"type": "object", "description": "YAML frontmatter as a dict"},
            "body": {"type": "string", "description": "Markdown body below the frontmatter"},
        },
        "required": ["path", "frontmatter", "body"],
    },
}


def _wiki_create_page_handler(inp: dict) -> dict:
    rel = str(inp.get("path", "")).strip()
    target = _safe_path(rel)
    if target is None:
        return {"error": f"Path {rel!r} is outside wiki/", "code": "invalid_path"}
    if target.exists():
        return {"error": f"{rel} already exists", "code": "already_exists"}

    import yaml  # pyyaml, already in requirements

    fm = inp.get("frontmatter") or {}
    body = str(inp.get("body", ""))
    fm_str = yaml.dump(fm, default_flow_style=False, allow_unicode=True).strip()
    content = f"---\n{fm_str}\n---\n\n{body}\n"

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return {"created": True, "path": rel}


# ── wiki_edit_page ───────────────────────────────────────────────────────────

WIKI_EDIT_PAGE_SCHEMA: dict = {
    "name": "wiki_edit_page",
    "description": (
        "Targeted string replacement in an existing wiki page. "
        "old_str must appear exactly once — errors if not found or ambiguous."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "old_str": {"type": "string", "description": "Exact string to replace (must be unique in file)"},
            "new_str": {"type": "string", "description": "Replacement string"},
        },
        "required": ["path", "old_str", "new_str"],
    },
}


def _wiki_edit_page_handler(inp: dict) -> dict:
    rel = str(inp.get("path", "")).strip()
    target = _safe_path(rel)
    if target is None:
        return {"error": f"Path {rel!r} is outside wiki/", "code": "invalid_path"}
    if not target.exists():
        return {"error": f"{rel} does not exist", "code": "not_found"}

    old_str = str(inp.get("old_str", ""))
    new_str = str(inp.get("new_str", ""))
    text = target.read_text(encoding="utf-8")

    count = text.count(old_str)
    if count == 0:
        return {"error": f"old_str not found in {rel}", "code": "not_found"}
    if count > 1:
        return {"error": f"old_str appears {count} times in {rel} — provide more context", "code": "ambiguous"}

    target.write_text(text.replace(old_str, new_str, 1), encoding="utf-8")
    return {"edited": True, "path": rel}


# ── wiki_append_section ──────────────────────────────────────────────────────

WIKI_APPEND_SECTION_SCHEMA: dict = {
    "name": "wiki_append_section",
    "description": (
        "Append a new ## section to an existing wiki page. "
        "Errors if the heading already exists."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "heading": {"type": "string", "description": "Section heading text (without ##)"},
            "content": {"type": "string", "description": "Section body in markdown"},
        },
        "required": ["path", "heading", "content"],
    },
}


def _wiki_append_section_handler(inp: dict) -> dict:
    rel = str(inp.get("path", "")).strip()
    target = _safe_path(rel)
    if target is None:
        return {"error": f"Path {rel!r} is outside wiki/", "code": "invalid_path"}
    if not target.exists():
        return {"error": f"{rel} does not exist", "code": "not_found"}

    heading = str(inp.get("heading", "")).strip()
    content = str(inp.get("content", "")).strip()
    text = target.read_text(encoding="utf-8")

    if f"## {heading}" in text:
        return {"error": f"Heading '## {heading}' already exists in {rel}", "code": "heading_exists"}

    new_text = text.rstrip() + f"\n\n## {heading}\n{content}\n"
    target.write_text(new_text, encoding="utf-8")
    return {"appended": True, "path": rel, "heading": heading}


# ── wiki_update_frontmatter ──────────────────────────────────────────────────

WIKI_UPDATE_FRONTMATTER_SCHEMA: dict = {
    "name": "wiki_update_frontmatter",
    "description": (
        "Append a value to a list field (depends_on, used_by, modules) "
        "in an existing wiki page's frontmatter. No-ops if the value is already present."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "field": {"type": "string", "description": "List field name, e.g. 'used_by'"},
            "value": {"type": "string", "description": "Value to append, e.g. 'visitor-management'"},
        },
        "required": ["path", "field", "value"],
    },
}


def _wiki_update_frontmatter_handler(inp: dict) -> dict:
    rel = str(inp.get("path", "")).strip()
    target = _safe_path(rel)
    if target is None:
        return {"error": f"Path {rel!r} is outside wiki/", "code": "invalid_path"}
    if not target.exists():
        return {"error": f"{rel} does not exist", "code": "not_found"}

    field = str(inp.get("field", "")).strip()
    value = str(inp.get("value", "")).strip()

    if field not in LIST_FIELDS:
        return {"error": f"Field {field!r} is not a known list field", "code": "unknown_field"}

    text = target.read_text(encoding="utf-8")

    # Check already present
    if value in text:
        return {"updated": True, "path": rel, "note": "already present — no change"}

    # Find the field line and append value
    pattern = re.compile(r"^(" + re.escape(field) + r":\s*\[)([^\]]*)\]", re.MULTILINE)
    match = pattern.search(text)
    if match:
        existing = match.group(2).strip()
        new_val = f"{existing}, {value}" if existing else value
        new_text = pattern.sub(f"{match.group(1)}{new_val}]", text, count=1)
        target.write_text(new_text, encoding="utf-8")
        return {"updated": True, "path": rel}

    # Field not on one line — append as a new list item after the field
    line_pattern = re.compile(r"^" + re.escape(field) + r":", re.MULTILINE)
    lm = line_pattern.search(text)
    if lm:
        insert_pos = text.index("\n", lm.start()) + 1
        new_text = text[:insert_pos] + f"  - {value}\n" + text[insert_pos:]
        target.write_text(new_text, encoding="utf-8")
        return {"updated": True, "path": rel}

    return {"error": f"Field {field!r} not found in frontmatter of {rel}", "code": "field_not_found"}


# ── wiki_rebuild_index ───────────────────────────────────────────────────────

WIKI_REBUILD_INDEX_SCHEMA: dict = {
    "name": "wiki_rebuild_index",
    "description": (
        "Rebuild the in-memory wiki search index after all pages have been written. "
        "Call this as the final step after all wiki_create_page / wiki_edit_page calls."
    ),
    "input_schema": {"type": "object", "properties": {}, "required": []},
}


def _wiki_rebuild_index_handler(_inp: dict) -> dict:
    try:
        wiki_retriever.build_index()
        count = len(wiki_retriever.all_pages())
        return {"rebuilt": True, "pages_indexed": count}
    except Exception as exc:
        return {"error": str(exc), "code": "rebuild_failed"}
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
python -m pytest tests/test_wiki_write_tools.py -v
```

Expected: all 10 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/tools/wiki_write_tools.py tests/test_wiki_write_tools.py
git commit -m "feat(ingest): wiki write tools — create/edit/append/frontmatter/rebuild"
```

---

## Task 4: Ingest Service — Mutex and Session State

**Files:**
- Create: `backend/ingest_service.py`
- Create: `tests/test_ingest_service.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_ingest_service.py`:

```python
"""Tests for ingest_service — mutex, session state, tool registry builders."""
import time
import pytest
from unittest.mock import patch


def test_acquire_and_release_lock():
    from backend.ingest_service import acquire_lock, release_lock, is_locked

    assert not is_locked()
    assert acquire_lock() is True
    assert is_locked()
    release_lock()
    assert not is_locked()


def test_acquire_lock_fails_when_held():
    from backend.ingest_service import acquire_lock, release_lock

    acquire_lock()
    try:
        assert acquire_lock() is False
    finally:
        release_lock()


def test_store_and_get_session():
    from backend.ingest_service import store_session, get_session, IngestSession

    s = IngestSession(
        session_id="abc123",
        upload_id="up-1",
        plan={"operations": []},
        created_at=time.time(),
        slug="visitor-management",
        filename="test.pdf",
        original_path="raw/modules/_uploads/up-1/test.pdf",
    )
    store_session(s)
    retrieved = get_session("abc123")
    assert retrieved is not None
    assert retrieved.slug == "visitor-management"


def test_session_expires():
    from backend.ingest_service import store_session, get_session, IngestSession

    old_time = time.time() - 700  # 700 seconds ago > 600s TTL
    s = IngestSession(
        session_id="expired-session",
        upload_id="up-2",
        plan={},
        created_at=old_time,
        slug="test",
        filename="test.pdf",
        original_path="raw/modules/_uploads/up-2/test.pdf",
    )
    store_session(s)
    assert get_session("expired-session") is None


def test_get_nonexistent_session():
    from backend.ingest_service import get_session

    assert get_session("does-not-exist") is None


def test_build_plan_registry_has_no_write_tools():
    from backend.ingest_service import build_plan_registry

    registry = build_plan_registry()
    tool_names = {s["name"] for s in registry.schemas}
    assert "wiki_create_page" not in tool_names
    assert "wiki_edit_page" not in tool_names
    assert "wiki_search" in tool_names
    assert "extract_pdf" in tool_names
    assert "wiki_list_pages" in tool_names


def test_build_execute_registry_has_write_tools():
    from backend.ingest_service import build_execute_registry

    registry = build_execute_registry()
    tool_names = {s["name"] for s in registry.schemas}
    assert "wiki_create_page" in tool_names
    assert "wiki_edit_page" in tool_names
    assert "wiki_rebuild_index" in tool_names
    # Execute registry should NOT have extraction tools (not needed)
    assert "extract_pdf" not in tool_names
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
python -m pytest tests/test_ingest_service.py -v 2>&1 | head -20
```

Expected: `ModuleNotFoundError: No module named 'backend.ingest_service'`

- [ ] **Step 3: Implement `backend/ingest_service.py`**

```python
"""Ingest service — mutex, session state, and per-phase tool registry builders.

Single global mutex: only one ingestion may run at a time.
Session TTL: 600 seconds (10 minutes) between plan and execute.
"""
from __future__ import annotations

import secrets
import threading
import time
from dataclasses import dataclass, field

SESSION_TTL = 600  # seconds

# ── mutex ────────────────────────────────────────────────────────────────────

_lock = threading.Lock()


def acquire_lock() -> bool:
    """Try to acquire the ingest mutex. Returns True if acquired, False if already held."""
    return _lock.acquire(blocking=False)


def release_lock() -> None:
    try:
        _lock.release()
    except RuntimeError:
        pass  # already released


def is_locked() -> bool:
    acquired = _lock.acquire(blocking=False)
    if acquired:
        _lock.release()
        return False
    return True


# ── session state ─────────────────────────────────────────────────────────────

@dataclass
class IngestSession:
    session_id: str
    upload_id: str
    plan: dict
    created_at: float
    slug: str
    filename: str
    original_path: str

    @property
    def expired(self) -> bool:
        return (time.time() - self.created_at) > SESSION_TTL


_sessions: dict[str, IngestSession] = {}


def store_session(session: IngestSession) -> None:
    _sessions[session.session_id] = session


def get_session(session_id: str) -> IngestSession | None:
    s = _sessions.get(session_id)
    if s is None:
        return None
    if s.expired:
        del _sessions[session_id]
        return None
    return s


def new_session_id() -> str:
    return secrets.token_hex(12)


# ── tool registries ───────────────────────────────────────────────────────────

def build_plan_registry():
    """Phase 1: read-only tools for extraction and wiki lookup. NO write tools."""
    from backend.tools.registry import ToolRegistry
    from backend.tools.wiki_tools import (
        WIKI_SEARCH_SCHEMA, _wiki_search_handler,
        WIKI_READ_PAGE_SCHEMA, _wiki_read_page_handler,
    )
    from backend.tools.wiki_read_tools import (
        WIKI_LIST_PAGES_SCHEMA, _wiki_list_pages_handler,
        WIKI_CHECK_DUPLICATE_SCHEMA, _wiki_check_duplicate_handler,
    )
    from backend.tools.wiki_write_tools import (
        _wiki_create_page_handler,  # imported only to build extraction tool schemas
    )
    from backend.document_extractor import (
        extract_document, extract_pdf, extract_docx, extract_xlsx, extract_text_file,
    )

    r = ToolRegistry(user_role="contributor")

    # Extraction tools
    r.register(
        {
            "name": "extract_pdf",
            "description": "Extract text from a PDF file at the given path. Returns {text, page_count, char_count, truncated}.",
            "input_schema": {
                "type": "object",
                "properties": {"file_path": {"type": "string"}},
                "required": ["file_path"],
            },
        },
        lambda inp: extract_pdf(inp["file_path"]),
    )
    r.register(
        {
            "name": "extract_docx",
            "description": "Extract text from a DOCX file. Returns {text, char_count, has_tables, truncated}.",
            "input_schema": {
                "type": "object",
                "properties": {"file_path": {"type": "string"}},
                "required": ["file_path"],
            },
        },
        lambda inp: extract_docx(inp["file_path"]),
    )
    r.register(
        {
            "name": "extract_xlsx",
            "description": "Extract sheets from an XLSX file. Returns {sheets: [{name, rows}]}.",
            "input_schema": {
                "type": "object",
                "properties": {"file_path": {"type": "string"}},
                "required": ["file_path"],
            },
        },
        lambda inp: extract_xlsx(inp["file_path"]),
    )
    r.register(
        {
            "name": "extract_text_file",
            "description": "Extract text from a plain-text file (MD, TXT, RTF). Returns {text, char_count, truncated}.",
            "input_schema": {
                "type": "object",
                "properties": {"file_path": {"type": "string"}},
                "required": ["file_path"],
            },
        },
        lambda inp: extract_text_file(inp["file_path"]),
    )

    # Wiki read tools
    r.register(WIKI_SEARCH_SCHEMA, _wiki_search_handler)
    r.register(WIKI_READ_PAGE_SCHEMA, _wiki_read_page_handler)
    r.register(WIKI_LIST_PAGES_SCHEMA, _wiki_list_pages_handler)
    r.register(WIKI_CHECK_DUPLICATE_SCHEMA, _wiki_check_duplicate_handler)

    return r


def build_execute_registry():
    """Phase 2: write-only tools. No extraction tools needed here."""
    from backend.tools.registry import ToolRegistry
    from backend.tools.wiki_write_tools import (
        WIKI_CREATE_PAGE_SCHEMA, _wiki_create_page_handler,
        WIKI_EDIT_PAGE_SCHEMA, _wiki_edit_page_handler,
        WIKI_APPEND_SECTION_SCHEMA, _wiki_append_section_handler,
        WIKI_UPDATE_FRONTMATTER_SCHEMA, _wiki_update_frontmatter_handler,
        WIKI_REBUILD_INDEX_SCHEMA, _wiki_rebuild_index_handler,
    )
    from backend.tools.wiki_tools import (
        WIKI_READ_PAGE_SCHEMA, _wiki_read_page_handler,
    )

    r = ToolRegistry(user_role="contributor")
    r.register(WIKI_CREATE_PAGE_SCHEMA, _wiki_create_page_handler)
    r.register(WIKI_EDIT_PAGE_SCHEMA, _wiki_edit_page_handler)
    r.register(WIKI_APPEND_SECTION_SCHEMA, _wiki_append_section_handler)
    r.register(WIKI_UPDATE_FRONTMATTER_SCHEMA, _wiki_update_frontmatter_handler)
    r.register(WIKI_REBUILD_INDEX_SCHEMA, _wiki_rebuild_index_handler)
    # Allow reading pages so the agent can verify its own writes
    r.register(WIKI_READ_PAGE_SCHEMA, _wiki_read_page_handler)
    return r
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
python -m pytest tests/test_ingest_service.py -v
```

Expected: all 7 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/ingest_service.py tests/test_ingest_service.py
git commit -m "feat(ingest): ingest_service — mutex, session TTL, phase tool registries"
```

---

## Task 5: Ingest API — Upload + Plan Endpoints

**Files:**
- Create: `backend/ingest_api.py`
- Create: `tests/test_ingest_api.py` (partial — upload + plan)
- Modify: `backend/api.py` (include router)

- [ ] **Step 1: Write failing tests for upload and plan endpoints**

Create `tests/test_ingest_api.py`:

```python
"""Integration tests for ingest API endpoints."""
import io
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from backend.api import app
    return TestClient(app)


@pytest.fixture
def auth_headers():
    # Matches a token from config/allowed_users.toml test fixtures (or mock _require_user)
    return {"Authorization": "Bearer test-token"}


def _patch_require_user():
    return patch(
        "backend.ingest_api._require_user",
        return_value={"email": "test@example.com", "role": "viewer"},
    )


def test_upload_returns_upload_id(client, tmp_path):
    with _patch_require_user():
        with patch("backend.ingest_api.UPLOAD_DIR", str(tmp_path)):
            response = client.post(
                "/api/ingest/upload",
                files={"file": ("test.txt", b"hello world", "text/plain")},
                data={"notes": "test upload"},
            )
    assert response.status_code == 200
    data = response.json()
    assert "upload_id" in data
    assert data["filename"] == "test.txt"


def test_upload_rejects_unsupported_type(client, tmp_path):
    with _patch_require_user():
        with patch("backend.ingest_api.UPLOAD_DIR", str(tmp_path)):
            response = client.post(
                "/api/ingest/upload",
                files={"file": ("file.exe", b"binary", "application/octet-stream")},
            )
    assert response.status_code == 400
    assert "unsupported" in response.json()["detail"].lower()


def test_upload_rejects_large_file(client, tmp_path):
    big = b"x" * (101 * 1024 * 1024)  # 101 MB
    with _patch_require_user():
        with patch("backend.ingest_api.UPLOAD_DIR", str(tmp_path)):
            response = client.post(
                "/api/ingest/upload",
                files={"file": ("big.pdf", big, "application/pdf")},
            )
    assert response.status_code == 413


def test_plan_returns_409_when_locked(client):
    from backend import ingest_service

    ingest_service.acquire_lock()
    try:
        with _patch_require_user():
            response = client.post(
                "/api/ingest/plan",
                json={"upload_id": "fake-id"},
            )
        assert response.status_code == 409
    finally:
        ingest_service.release_lock()
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
python -m pytest tests/test_ingest_api.py::test_upload_returns_upload_id tests/test_ingest_api.py::test_upload_rejects_unsupported_type tests/test_ingest_api.py::test_upload_rejects_large_file tests/test_ingest_api.py::test_plan_returns_409_when_locked -v 2>&1 | head -30
```

Expected: errors due to missing `backend/ingest_api.py` or missing routes.

- [ ] **Step 3: Implement upload + plan in `backend/ingest_api.py`**

```python
"""Ingest API — three endpoints for document ingestion.

POST /api/ingest/upload  — save uploaded file
POST /api/ingest/plan    — Phase 1 agent: read-only, returns JSON plan
POST /api/ingest/execute — Phase 2 agent: write tools, SSE streaming
"""
from __future__ import annotations

import json
import os
import pathlib
import secrets
import time
from typing import AsyncGenerator

import anthropic
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend import ingest_service, wiki_retriever
from backend.api import _require_user  # reuse existing auth dependency

router = APIRouter(prefix="/api/ingest")

MAX_UPLOAD_BYTES = 100 * 1024 * 1024  # 100 MB
SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".doc", ".xlsx", ".xls", ".md", ".txt", ".rtf"}

# Where uploads land before being moved to raw/modules/{slug}/
UPLOAD_DIR = str(pathlib.Path(__file__).resolve().parent.parent / "raw" / "modules" / "_uploads")

# ── System prompts ────────────────────────────────────────────────────────────

PLAN_SYSTEM_PROMPT = """\
You are an ingestion planner for the WorkInSync org wiki.
A document has been uploaded. Your job: read it, classify it,
identify cross-references with the existing wiki, and produce
a structured JSON plan. You MUST NOT write anything — you have
no write tools.

WIKI STRUCTURE:
- wiki/sources/<slug>.md       — every ingested doc gets one
- wiki/modules/<slug>.md       — product modules
- wiki/entities/<slug>.md      — data models / domain objects
- wiki/cross-module/<a>-<b>.md — when two modules connect
- wiki/decisions/<date>-<title>.md — architecture decisions
- wiki/configs/<slug>.md       — PMS config tables

SLUG RULES: lowercase-hyphenated, match the module folder name.
Always call wiki_check_duplicate before proposing a new slug.

BIDIRECTIONALITY: if module A depends_on B, then B must have
used_by A. Flag any asymmetry as a warning in your plan.

CLASSIFICATION ORDER:
1. Folder context — raw/modules/<slug>/ tells you the module
2. Doc type from content (PRD, SOP, spec, config sheet)
3. Entity definitions (fields + types → entity pages)
4. Dependency language ("calls X API") → cross-module pages
5. Decision language ("we chose X because") → decision pages
6. Config tables (property + description columns) → config pages

MANDATORY STEPS:
1. Extract the document using extract_pdf / extract_docx / extract_xlsx / extract_text_file
2. Call wiki_list_pages to see what already exists
3. Read 3-5 most relevant existing wiki pages for context
4. Output your final answer as JSON only — no prose outside the JSON

OUTPUT: a single JSON object matching this schema exactly:
{
  "summary_bullets": ["string", ...],
  "classification": "module|entity|config|source|concept|decision|cross-module",
  "target_slug": "visitor-management",
  "operations": [
    {
      "type": "create|edit|append|update_frontmatter",
      "path": "wiki/...",
      "frontmatter": {},
      "preview": "first 200 chars of planned body",
      "change_description": "what this change does"
    }
  ],
  "cross_references": ["wiki/cross-module/..."],
  "warnings": ["string", ...],
  "agent_reasoning": "one paragraph explaining classification"
}
"""

EXECUTE_SYSTEM_PROMPT = """\
You are an ingestion executor. Execute the approved plan EXACTLY
as specified. Do not re-classify. Do not add or remove operations.

For each operation in the plan:
- "create"             → call wiki_create_page
- "edit"               → call wiki_edit_page
- "append"             → call wiki_append_section
- "update_frontmatter" → call wiki_update_frontmatter

After ALL operations complete successfully, call wiki_rebuild_index.

If any tool call returns an error, stop immediately and do not
continue. Report the error clearly.
"""

MODEL = "claude-sonnet-4-6"


# ── Upload endpoint ───────────────────────────────────────────────────────────

@router.post("/upload")
async def upload_file(
    file: UploadFile,
    notes: str = "",
    target_slug: str = "",
    user: dict = Depends(_require_user),
):
    ext = pathlib.Path(file.filename or "").suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type {ext!r}. Allowed: {', '.join(sorted(SUPPORTED_EXTENSIONS))}",
        )

    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File exceeds 100 MB limit")

    upload_id = secrets.token_hex(8)
    dest_dir = pathlib.Path(UPLOAD_DIR) / upload_id
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_file = dest_dir / (file.filename or "upload" + ext)
    dest_file.write_bytes(content)

    return {
        "upload_id": upload_id,
        "filename": file.filename,
        "size": len(content),
        "file_path": str(dest_file),
        "notes": notes,
        "target_slug": target_slug or None,
    }


# ── Plan endpoint ─────────────────────────────────────────────────────────────

class PlanRequest(BaseModel):
    upload_id: str
    notes: str = ""
    target_slug: str = ""


@router.post("/plan")
def plan_ingest(req: PlanRequest, user: dict = Depends(_require_user)):
    if not ingest_service.acquire_lock():
        raise HTTPException(
            status_code=409,
            detail="Another ingestion is in progress. Try again in a moment.",
        )

    try:
        # Locate the uploaded file
        upload_dir = pathlib.Path(UPLOAD_DIR) / req.upload_id
        if not upload_dir.exists():
            raise HTTPException(status_code=404, detail=f"Upload {req.upload_id!r} not found")

        files = list(upload_dir.iterdir())
        if not files:
            raise HTTPException(status_code=404, detail="Upload directory is empty")
        file_path = str(files[0])
        filename = files[0].name

        # Compose the user message
        hint = f"\nUser hint — target module: {req.target_slug}" if req.target_slug else ""
        context = f"\nUser context: {req.notes}" if req.notes else ""
        user_message = (
            f"Ingest the document at: {file_path}{hint}{context}\n\n"
            "Produce the JSON plan as your final response."
        )

        registry = ingest_service.build_plan_registry()
        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))

        messages = [{"role": "user", "content": user_message}]
        plan_json: dict = {}

        # Run tool-use loop until agent returns end_turn
        for _ in range(20):  # max 20 rounds
            response = client.messages.create(
                model=MODEL,
                max_tokens=4096,
                system=PLAN_SYSTEM_PROMPT,
                tools=registry.schemas,
                messages=messages,
            )

            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result_str, _ = registry.execute(block.name, block.input, round_num=0)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result_str,
                    })

            if response.stop_reason == "end_turn":
                # Extract JSON from the final text block
                for block in response.content:
                    if hasattr(block, "text"):
                        text = block.text.strip()
                        # Strip markdown code fences if present
                        if text.startswith("```"):
                            text = text.split("```")[1]
                            if text.startswith("json"):
                                text = text[4:]
                        plan_json = json.loads(text.strip())
                break

            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})

        # Detect slug from plan
        slug = plan_json.get("target_slug") or req.target_slug or "unknown"

        session_id = ingest_service.new_session_id()
        session = ingest_service.IngestSession(
            session_id=session_id,
            upload_id=req.upload_id,
            plan=plan_json,
            created_at=time.time(),
            slug=slug,
            filename=filename,
            original_path=file_path,
        )
        ingest_service.store_session(session)

        return {"session_id": session_id, "plan": plan_json}

    finally:
        ingest_service.release_lock()
```

- [ ] **Step 4: Register router in `backend/api.py`**

Open `backend/api.py`. Find the line `from backend import trace_api` near the bottom of the file. Add immediately after it:

```python
from backend import ingest_api  # noqa: E402
app.include_router(ingest_api.router)
```

- [ ] **Step 5: Run tests**

```bash
python -m pytest tests/test_ingest_api.py::test_upload_returns_upload_id tests/test_ingest_api.py::test_upload_rejects_unsupported_type tests/test_ingest_api.py::test_upload_rejects_large_file tests/test_ingest_api.py::test_plan_returns_409_when_locked -v
```

Expected: all 4 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/ingest_api.py backend/api.py tests/test_ingest_api.py
git commit -m "feat(ingest): upload + plan endpoints — Phase 1 agent with read-only tools"
```

---

## Task 6: Ingest API — Execute Endpoint (SSE Streaming)

**Files:**
- Modify: `backend/ingest_api.py` (add execute endpoint)
- Add tests: `tests/test_ingest_api.py`

- [ ] **Step 1: Add failing test for execute endpoint**

Append to `tests/test_ingest_api.py`:

```python
def test_execute_returns_410_for_expired_session(client):
    with _patch_require_user():
        response = client.post(
            "/api/ingest/execute",
            json={"session_id": "no-such-session"},
        )
    assert response.status_code == 410


def test_execute_returns_409_when_locked(client):
    from backend import ingest_service

    ingest_service.acquire_lock()
    try:
        with _patch_require_user():
            response = client.post(
                "/api/ingest/execute",
                json={"session_id": "fake-session"},
            )
        assert response.status_code == 409
    finally:
        ingest_service.release_lock()
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
python -m pytest tests/test_ingest_api.py::test_execute_returns_410_for_expired_session tests/test_ingest_api.py::test_execute_returns_409_when_locked -v 2>&1 | head -20
```

Expected: 404 Not Found (execute endpoint doesn't exist yet).

- [ ] **Step 3: Add execute endpoint to `backend/ingest_api.py`**

Append to `backend/ingest_api.py` after the plan endpoint:

```python
# ── Execute endpoint ──────────────────────────────────────────────────────────

class ExecuteRequest(BaseModel):
    session_id: str


@router.post("/execute")
def execute_ingest(req: ExecuteRequest, user: dict = Depends(_require_user)):
    session = ingest_service.get_session(req.session_id)
    if session is None:
        raise HTTPException(
            status_code=410,
            detail="Plan expired or not found. Please re-upload and re-plan.",
        )

    if not ingest_service.acquire_lock():
        raise HTTPException(
            status_code=409,
            detail="Another ingestion is in progress. Try again in a moment.",
        )

    async def event_stream() -> AsyncGenerator[str, None]:
        try:
            registry = ingest_service.build_execute_registry()
            client_api = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))

            plan = session.plan
            operations = plan.get("operations", [])
            total = len(operations) + 1  # +1 for rebuild_index

            user_msg = (
                f"Execute this approved ingestion plan for file '{session.filename}':\n\n"
                f"{json.dumps(plan, indent=2)}"
            )
            messages = [{"role": "user", "content": user_msg}]

            files_created: list[str] = []
            files_modified: list[str] = []
            completed = 0

            for _ in range(30):  # max 30 rounds
                response = client_api.messages.create(
                    model=MODEL,
                    max_tokens=4096,
                    system=EXECUTE_SYSTEM_PROMPT,
                    tools=registry.schemas,
                    messages=messages,
                )

                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        result_str, _ = registry.execute(block.name, block.input, round_num=0)
                        result = json.loads(result_str)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result_str,
                        })
                        completed += 1

                        # Track created vs modified
                        path = block.input.get("path", "")
                        if block.name == "wiki_create_page" and result.get("created"):
                            files_created.append(path)
                        elif block.name in {"wiki_edit_page", "wiki_append_section", "wiki_update_frontmatter"}:
                            if path not in files_modified:
                                files_modified.append(path)

                        # Determine status label
                        if "error" in result:
                            status_label = "error"
                        elif block.name == "wiki_create_page":
                            status_label = "created"
                        elif block.name == "wiki_rebuild_index":
                            status_label = "rebuilt"
                        else:
                            status_label = "edited"

                        event = {
                            "type": "progress",
                            "tool": block.name,
                            "path": path,
                            "status": status_label,
                            "result": result,
                            "completed": completed,
                            "total": total,
                        }
                        yield f"data: {json.dumps(event)}\n\n"

                        if "error" in result:
                            yield f"event: error\ndata: {json.dumps({'message': result['error'], 'tool': block.name, 'path': path})}\n\n"
                            return

                if response.stop_reason == "end_turn":
                    break

                messages.append({"role": "assistant", "content": response.content})
                messages.append({"role": "user", "content": tool_results})

            # Move uploaded file to proper raw/modules/{slug}/ location
            src = pathlib.Path(session.original_path)
            if src.exists():
                import pathlib as _pl
                dest_dir = _pl.Path(UPLOAD_DIR).parent / session.slug
                dest_dir.mkdir(parents=True, exist_ok=True)
                dest = dest_dir / session.filename
                src.rename(dest)
                # Clean up empty upload dir
                try:
                    src.parent.rmdir()
                except OSError:
                    pass

            # Emit completion event
            links = [p.replace("wiki/", "").replace(".md", "") for p in files_created]
            complete_event = {
                "type": "complete",
                "files_created": files_created,
                "files_modified": files_modified,
                "links": links,
            }
            yield f"event: complete\ndata: {json.dumps(complete_event)}\n\n"

        except Exception as exc:
            yield f"event: error\ndata: {json.dumps({'message': str(exc)})}\n\n"
        finally:
            ingest_service.release_lock()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/test_ingest_api.py -v
```

Expected: all 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/ingest_api.py tests/test_ingest_api.py
git commit -m "feat(ingest): execute endpoint — Phase 2 write agent with SSE streaming"
```

---

## Task 7: Frontend — API Service Methods

**Files:**
- Modify: `frontend/src/app/core/api.service.ts`

- [ ] **Step 1: Add interfaces and methods to `api.service.ts`**

Open `frontend/src/app/core/api.service.ts`. Add interfaces near the top of the file (after existing interfaces):

```typescript
// ── Ingest types ──────────────────────────────────────────────────────────────

export interface IngestUploadResponse {
  upload_id: string;
  filename: string;
  size: number;
  file_path: string;
  notes: string;
  target_slug: string | null;
}

export interface IngestOperation {
  type: 'create' | 'edit' | 'append' | 'update_frontmatter';
  path: string;
  frontmatter?: Record<string, unknown>;
  preview?: string;
  change_description?: string;
}

export interface IngestPlan {
  summary_bullets: string[];
  classification: string;
  target_slug: string;
  operations: IngestOperation[];
  cross_references: string[];
  warnings: string[];
  agent_reasoning: string;
}

export interface IngestPlanResponse {
  session_id: string;
  plan: IngestPlan;
}

export type IngestProgressEvent =
  | { type: 'progress'; tool: string; path: string; status: string; result: Record<string, unknown>; completed: number; total: number }
  | { type: 'complete'; files_created: string[]; files_modified: string[]; links: string[] }
  | { type: 'error'; message: string; tool?: string; path?: string }
  | { type: '__sse_error'; error: string };
```

Then add these three methods to the `ApiService` class:

```typescript
uploadIngestFile(
  file: File,
  notes: string,
  targetSlug: string
): Observable<IngestUploadResponse> {
  const token = this.getAdminToken();
  const headers = token ? new HttpHeaders({ Authorization: `Bearer ${token}` }) : new HttpHeaders();
  const body = new FormData();
  body.append('file', file);
  if (notes) body.append('notes', notes);
  if (targetSlug) body.append('target_slug', targetSlug);
  return this.http.post<IngestUploadResponse>(`${API_BASE}/api/ingest/upload`, body, { headers });
}

planIngest(uploadId: string, notes: string, targetSlug: string): Observable<IngestPlanResponse> {
  const token = this.getAdminToken();
  const headers = token
    ? new HttpHeaders({ Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' })
    : new HttpHeaders({ 'Content-Type': 'application/json' });
  return this.http.post<IngestPlanResponse>(
    `${API_BASE}/api/ingest/plan`,
    { upload_id: uploadId, notes, target_slug: targetSlug },
    { headers }
  );
}

streamExecuteIngest(sessionId: string): Observable<IngestProgressEvent> {
  return new Observable<IngestProgressEvent>(subscriber => {
    const ctrl = new AbortController();
    const token = this.getAdminToken();

    fetch(`${API_BASE}/api/ingest/execute`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: token ? `Bearer ${token}` : '',
        Accept: 'text/event-stream',
      },
      body: JSON.stringify({ session_id: sessionId }),
      signal: ctrl.signal,
    })
      .then(async resp => {
        if (!resp.ok) {
          const err = await resp.json().catch(() => ({ detail: resp.statusText }));
          subscriber.next({ type: '__sse_error', error: err.detail ?? resp.statusText });
          subscriber.complete();
          return;
        }
        const reader = resp.body!.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          let sep: number;
          while ((sep = buffer.indexOf('\n\n')) !== -1) {
            const frame = buffer.slice(0, sep);
            buffer = buffer.slice(sep + 2);
            const parsed = parseIngestSseFrame(frame);
            if (parsed) subscriber.next(parsed);
          }
        }
        subscriber.complete();
      })
      .catch(err => {
        subscriber.next({ type: '__sse_error', error: String(err?.message ?? err) });
        subscriber.complete();
      });

    return () => ctrl.abort();
  });
}
```

Add the SSE parser helper function at the bottom of the file (outside the class):

```typescript
function parseIngestSseFrame(frame: string): IngestProgressEvent | null {
  let eventType = 'data';
  let dataLine = '';

  for (const line of frame.split('\n')) {
    if (line.startsWith('event: ')) eventType = line.slice(7).trim();
    else if (line.startsWith('data: ')) dataLine = line.slice(6).trim();
  }

  if (!dataLine) return null;
  try {
    const parsed = JSON.parse(dataLine);
    if (eventType === 'error') return { type: 'error', ...parsed };
    if (eventType === 'complete') return { type: 'complete', ...parsed };
    return parsed as IngestProgressEvent;
  } catch {
    return null;
  }
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -20
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/app/core/api.service.ts
git commit -m "feat(ingest): add uploadIngestFile, planIngest, streamExecuteIngest to ApiService"
```

---

## Task 8: Frontend — Upload Step Component

**Files:**
- Create: `frontend/src/app/features/ingest/upload-step.ts`

- [ ] **Step 1: Create `upload-step.ts`**

```typescript
import { Component, output, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService, IngestUploadResponse } from '../../core/api.service';
import { inject } from '@angular/core';

export interface UploadResult {
  uploadId: string;
  filename: string;
  notes: string;
  targetSlug: string;
}

@Component({
  selector: 'app-upload-step',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="upload-step">
      <h2>Ingest Document</h2>
      <p class="subtitle">Upload a document to add it to the wiki.</p>

      <div
        class="drop-zone"
        [class.drag-over]="dragOver()"
        [class.has-file]="selectedFile()"
        (dragover)="onDragOver($event)"
        (dragleave)="dragOver.set(false)"
        (drop)="onDrop($event)"
        (click)="fileInput.click()"
      >
        @if (selectedFile(); as f) {
          <div class="file-info">
            <span class="file-icon">📄</span>
            <span class="file-name">{{ f.name }}</span>
            <span class="file-size">{{ formatSize(f.size) }}</span>
          </div>
        } @else {
          <div class="drop-hint">
            <span class="drop-icon">📄</span>
            <span>Drop a file here, or click to browse</span>
            <span class="drop-types">PDF · DOCX · XLSX · MD · TXT</span>
          </div>
        }
        <input
          #fileInput
          type="file"
          style="display:none"
          accept=".pdf,.docx,.doc,.xlsx,.xls,.md,.txt,.rtf"
          (change)="onFileSelected($event)"
        />
      </div>

      @if (typeError()) {
        <div class="error-msg">{{ typeError() }}</div>
      }

      <div class="form-field">
        <label>Context for the AI <span class="optional">(optional)</span></label>
        <textarea
          [(ngModel)]="notes"
          placeholder="e.g. Updated VMS PRD from Q3 planning, supersedes the earlier version"
          rows="3"
        ></textarea>
      </div>

      <div class="form-field">
        <label>Target module <span class="optional">(optional — AI will detect if blank)</span></label>
        <input
          type="text"
          [(ngModel)]="targetSlug"
          placeholder="e.g. visitor-management"
          list="module-slugs"
        />
        <datalist id="module-slugs">
          @for (slug of knownSlugs; track slug) {
            <option [value]="slug" />
          }
        </datalist>
      </div>

      @if (error()) {
        <div class="error-msg">{{ error() }}</div>
      }

      <button
        class="btn-primary"
        [disabled]="!selectedFile() || loading()"
        (click)="submit()"
      >
        @if (loading()) { Uploading… } @else { Upload & Analyse → }
      </button>
    </div>
  `,
})
export class UploadStep {
  private api = inject(ApiService);

  done = output<UploadResult>();

  selectedFile = signal<File | null>(null);
  dragOver = signal(false);
  loading = signal(false);
  error = signal('');
  typeError = signal('');
  notes = '';
  targetSlug = '';

  readonly knownSlugs = [
    'access-management', 'admin-experience', 'create-employee-form', 'delegation',
    'desk-management', 'digital-wayfinding', 'employee-experience', 'employee-provisioning',
    'esg-dashboard', 'floor-kiosk', 'guard-app-kiosks', 'implementation',
    'meal-management', 'meeting-rooms', 'mobile-app', 'ms-teams-integration',
    'parking-management', 'safe-reach', 'sso', 'tags-desk-parking', 'third-party',
    'visitor-management',
  ];

  private readonly supported = new Set(['.pdf', '.docx', '.doc', '.xlsx', '.xls', '.md', '.txt', '.rtf']);

  onDragOver(e: DragEvent) {
    e.preventDefault();
    this.dragOver.set(true);
  }

  onDrop(e: DragEvent) {
    e.preventDefault();
    this.dragOver.set(false);
    const f = e.dataTransfer?.files?.[0];
    if (f) this.setFile(f);
  }

  onFileSelected(e: Event) {
    const f = (e.target as HTMLInputElement).files?.[0];
    if (f) this.setFile(f);
  }

  private setFile(f: File) {
    const ext = '.' + f.name.split('.').pop()!.toLowerCase();
    if (!this.supported.has(ext)) {
      this.typeError.set(`Unsupported file type: ${ext}. Allowed: PDF, DOCX, XLSX, MD, TXT`);
      this.selectedFile.set(null);
      return;
    }
    this.typeError.set('');
    this.selectedFile.set(f);
  }

  formatSize(bytes: number): string {
    return bytes > 1024 * 1024 ? `${(bytes / 1024 / 1024).toFixed(1)} MB` : `${(bytes / 1024).toFixed(0)} KB`;
  }

  submit() {
    const f = this.selectedFile();
    if (!f) return;
    this.loading.set(true);
    this.error.set('');

    this.api.uploadIngestFile(f, this.notes, this.targetSlug).subscribe({
      next: (upload) => {
        this.loading.set(false);
        this.done.emit({
          uploadId: upload.upload_id,
          filename: upload.filename ?? f.name,
          notes: this.notes,
          targetSlug: this.targetSlug,
        });
      },
      error: (err) => {
        this.loading.set(false);
        this.error.set(err?.error?.detail ?? 'Upload failed. Try again.');
      },
    });
  }
}
```

**Note:** The parent `Ingest` component will hold the `planResponse` signal. The upload step triggers upload + plan and emits the `uploadId` when done. The parent fetches the plan result separately (see Task 10).

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit 2>&1 | grep -i "upload-step" | head -10
```

Expected: no errors for this file.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/app/features/ingest/upload-step.ts
git commit -m "feat(ingest): upload-step component — drag-drop, file validation, upload+plan trigger"
```

---

## Task 9: Frontend — Plan Review Step

**Files:**
- Create: `frontend/src/app/features/ingest/plan-step.ts`

- [ ] **Step 1: Create `plan-step.ts`**

```typescript
import { Component, input, output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { IngestPlan, IngestOperation } from '../../core/api.service';

@Component({
  selector: 'app-plan-step',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="plan-step">
      <div class="plan-header">
        <h2>Review Ingestion Plan</h2>
        <span class="filename">{{ filename() }}</span>
      </div>

      <div class="summary-box">
        <div class="section-label">Document Summary</div>
        <ul>
          @for (bullet of plan().summary_bullets; track bullet) {
            <li>{{ bullet }}</li>
          }
        </ul>
      </div>

      <div class="classification-badges">
        <div class="badge">
          <span class="badge-label">Type</span>
          <span class="badge-value">{{ plan().classification }}</span>
        </div>
        <div class="badge">
          <span class="badge-label">Target module</span>
          <span class="badge-value">{{ plan().target_slug }}</span>
        </div>
        <div class="badge">
          <span class="badge-label">Action</span>
          <span class="badge-value">{{ hasExistingModule() ? 'Update existing page' : 'Create new page' }}</span>
        </div>
      </div>

      <div class="ops-grid">
        <div class="ops-col">
          <div class="section-label">Files to create ({{ creates().length }})</div>
          <ul class="ops-list">
            @for (op of creates(); track op.path) {
              <li>
                <span class="op-icon">📄</span>
                <span class="op-path">{{ op.path }}</span>
                @if (op.preview) {
                  <span class="op-preview">{{ op.preview }}</span>
                }
              </li>
            }
            @if (creates().length === 0) {
              <li class="empty">None</li>
            }
          </ul>
        </div>

        <div class="ops-col">
          <div class="section-label">Files to modify ({{ edits().length }})</div>
          <ul class="ops-list">
            @for (op of edits(); track op.path) {
              <li>
                <span class="op-icon">✏️</span>
                <span class="op-path">{{ op.path }}</span>
                <span class="op-desc">{{ op.change_description }}</span>
              </li>
            }
            @if (edits().length === 0) {
              <li class="empty">None</li>
            }
          </ul>
        </div>
      </div>

      @if (plan().cross_references.length) {
        <div class="cross-refs">
          <div class="section-label">Cross-references to create ({{ plan().cross_references.length }})</div>
          <ul class="ops-list">
            @for (ref of plan().cross_references; track ref) {
              <li><span class="op-icon">🔗</span><span class="op-path">{{ ref }}</span></li>
            }
          </ul>
        </div>
      }

      @if (plan().warnings.length) {
        <div class="warnings-box">
          @for (w of plan().warnings; track w) {
            <div class="warning-item">⚠ {{ w }}</div>
          }
        </div>
      }

      <div class="plan-actions">
        <button class="btn-secondary" (click)="cancel.emit()">Cancel</button>
        <button class="btn-approve" (click)="approve.emit()">Approve & Execute →</button>
      </div>
    </div>
  `,
})
export class PlanStep {
  plan = input.required<IngestPlan>();
  filename = input<string>('');
  sessionId = input<string>('');

  approve = output<void>();
  cancel = output<void>();

  creates() {
    return this.plan().operations.filter(o => o.type === 'create');
  }

  edits() {
    return this.plan().operations.filter(o => o.type !== 'create');
  }

  hasExistingModule() {
    return this.plan().operations.some(
      o => o.type !== 'create' && o.path.startsWith('wiki/modules/')
    );
  }
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit 2>&1 | grep -i "plan-step" | head -10
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/app/features/ingest/plan-step.ts
git commit -m "feat(ingest): plan-step component — summary, operations list, approve/cancel"
```

---

## Task 10: Frontend — Execute Step Component

**Files:**
- Create: `frontend/src/app/features/ingest/execute-step.ts`

- [ ] **Step 1: Create `execute-step.ts`**

```typescript
import { Component, input, OnDestroy, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { Subscription } from 'rxjs';
import { ApiService, IngestProgressEvent } from '../../core/api.service';
import { inject } from '@angular/core';

interface ProgressItem {
  path: string;
  status: 'pending' | 'in_progress' | 'done' | 'error';
  label: string;
}

@Component({
  selector: 'app-execute-step',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <div class="execute-step">
      <div class="execute-header">
        <h2>Ingesting: {{ filename() }}</h2>
        <span class="elapsed">⏱ {{ elapsedSeconds() }}s elapsed</span>
      </div>

      <div class="progress-list">
        <div class="section-label">Progress</div>
        @for (item of progressItems(); track item.path) {
          <div class="progress-item" [class]="item.status">
            <span class="item-icon">
              @switch (item.status) {
                @case ('done') { ✅ }
                @case ('error') { ❌ }
                @case ('in_progress') { ⏳ }
                @default { ○ }
              }
            </span>
            <span class="item-path">{{ item.path || item.label }}</span>
          </div>
        }
      </div>

      @if (total() > 0) {
        <div class="progress-bar">
          <div class="progress-fill" [style.width.%]="progressPercent()"></div>
        </div>
      }

      @if (done()) {
        <div class="success-box">
          <div class="success-title">
            ✅ Ingestion complete — {{ createdCount() }} created, {{ modifiedCount() }} modified
          </div>
          <div class="result-links">
            @for (link of resultLinks(); track link) {
              <a [routerLink]="['/ask']" [queryParams]="{q: link}" class="result-link">
                {{ link }}
              </a>
            }
          </div>
        </div>
        <button class="btn-primary" (click)="onIngestAnother()">Ingest another doc</button>
      }

      @if (errorMsg()) {
        <div class="error-box">
          <div class="error-title">❌ Ingestion failed</div>
          <div class="error-detail">{{ errorMsg() }}</div>
        </div>
        <button class="btn-secondary" (click)="onIngestAnother()">Go back</button>
      }

      @if (!done() && !errorMsg()) {
        <div class="warning-note">⚠ Ingestion in progress — please don't close this tab</div>
      }
    </div>
  `,
})
export class ExecuteStep implements OnInit, OnDestroy {
  private api = inject(ApiService);

  sessionId = input.required<string>();
  filename = input<string>('');
  ingestAnother = output<void>();

  progressItems = signal<ProgressItem[]>([]);
  total = signal(0);
  completed = signal(0);
  done = signal(false);
  errorMsg = signal('');
  resultLinks = signal<string[]>([]);
  createdCount = signal(0);
  modifiedCount = signal(0);
  elapsedSeconds = signal(0);

  private sub?: Subscription;
  private timerHandle?: ReturnType<typeof setInterval>;
  private startedAt = Date.now();

  progressPercent() {
    const t = this.total();
    return t > 0 ? Math.round((this.completed() / t) * 100) : 0;
  }

  ngOnInit() {
    this.startedAt = Date.now();
    this.timerHandle = setInterval(() => {
      this.elapsedSeconds.set(Math.round((Date.now() - this.startedAt) / 1000));
    }, 1000);

    this.sub = this.api.streamExecuteIngest(this.sessionId()).subscribe({
      next: (evt: IngestProgressEvent) => this.handleEvent(evt),
      error: (err) => this.errorMsg.set(String(err?.message ?? err)),
    });
  }

  ngOnDestroy() {
    this.sub?.unsubscribe();
    if (this.timerHandle) clearInterval(this.timerHandle);
  }

  private handleEvent(evt: IngestProgressEvent) {
    switch (evt.type) {
      case 'progress': {
        this.total.set(evt.total);
        this.completed.set(evt.completed);
        const items = [...this.progressItems()];
        const existing = items.findIndex(i => i.path === evt.path && i.status === 'pending');
        const newItem: ProgressItem = {
          path: evt.path,
          status: evt.status === 'error' ? 'error' : 'done',
          label: `${evt.tool}: ${evt.path}`,
        };
        if (existing >= 0) items[existing] = newItem;
        else items.push(newItem);
        this.progressItems.set(items);
        break;
      }
      case 'complete': {
        this.done.set(true);
        this.resultLinks.set(evt.links);
        this.createdCount.set(evt.files_created.length);
        this.modifiedCount.set(evt.files_modified.length);
        if (this.timerHandle) clearInterval(this.timerHandle);
        break;
      }
      case 'error':
      case '__sse_error': {
        this.errorMsg.set((evt as any).message ?? (evt as any).error ?? 'Unknown error');
        if (this.timerHandle) clearInterval(this.timerHandle);
        break;
      }
    }
  }

  onIngestAnother() {
    this.ingestAnother.emit();
  }
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit 2>&1 | grep -i "execute-step" | head -10
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/app/features/ingest/execute-step.ts
git commit -m "feat(ingest): execute-step — SSE streaming progress, completion state, error handling"
```

---

## Task 11: Frontend — Main Ingest Page

**Files:**
- Create: `frontend/src/app/features/ingest/ingest.ts`
- Create: `frontend/src/app/features/ingest/ingest.scss`

- [ ] **Step 1: Create `ingest.ts`**

```typescript
import { Component, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService, IngestPlan, IngestPlanResponse } from '../../core/api.service';
import { inject } from '@angular/core';
import { UploadStep, UploadResult } from './upload-step';
import { PlanStep } from './plan-step';
import { ExecuteStep } from './execute-step';

type IngestPhase = 'upload' | 'planning' | 'plan-review' | 'executing' | 'done';

@Component({
  selector: 'app-ingest',
  standalone: true,
  imports: [CommonModule, UploadStep, PlanStep, ExecuteStep],
  templateUrl: './ingest.html',
  styleUrl: './ingest.scss',
})
export class Ingest {
  private api = inject(ApiService);

  phase = signal<IngestPhase>('upload');
  uploadResult = signal<UploadResult | null>(null);
  planResponse = signal<IngestPlanResponse | null>(null);
  planningError = signal('');

  onUploaded(result: UploadResult) {
    this.uploadResult.set(result);
    this.phase.set('planning');
    this.planningError.set('');

    // Upload step already triggered upload; now fetch the plan
    this.api.planIngest(result.uploadId, result.notes, result.targetSlug).subscribe({
      next: (resp) => {
        this.planResponse.set(resp);
        this.phase.set('plan-review');
      },
      error: (err) => {
        this.planningError.set(err?.error?.detail ?? 'Planning failed. Try again.');
        this.phase.set('upload');
      },
    });
  }

  onApprove() {
    this.phase.set('executing');
  }

  onCancel() {
    this.reset();
  }

  onIngestAnother() {
    this.reset();
  }

  private reset() {
    this.phase.set('upload');
    this.uploadResult.set(null);
    this.planResponse.set(null);
    this.planningError.set('');
  }
}
```

Create `frontend/src/app/features/ingest/ingest.html`:

```html
<div class="ingest-page">
  <div class="ingest-container">

    @switch (phase()) {
      @case ('upload') {
        <app-upload-step (done)="onUploaded($event)" />
        @if (planningError()) {
          <div class="error-banner">{{ planningError() }}</div>
        }
      }

      @case ('planning') {
        <div class="planning-spinner">
          <div class="spinner"></div>
          <p>Analysing document…</p>
        </div>
      }

      @case ('plan-review') {
        @if (planResponse(); as pr) {
          <app-plan-step
            [plan]="pr.plan"
            [filename]="uploadResult()?.filename ?? ''"
            [sessionId]="pr.session_id"
            (approve)="onApprove()"
            (cancel)="onCancel()"
          />
        }
      }

      @case ('executing') {
        @if (planResponse(); as pr) {
          <app-execute-step
            [sessionId]="pr.session_id"
            [filename]="uploadResult()?.filename ?? ''"
            (ingestAnother)="onIngestAnother()"
          />
        }
      }
    }

  </div>
</div>
```

- [ ] **Step 2: Create `ingest.scss`**

```scss
.ingest-page {
  display: flex;
  justify-content: center;
  padding: 32px 16px;
  min-height: calc(100vh - 60px);
}

.ingest-container {
  width: 100%;
  max-width: 700px;
}

// ── Upload step ──────────────────────────────────────────────────────────────
.drop-zone {
  border: 2px dashed #90caf9;
  border-radius: 12px;
  padding: 48px 32px;
  text-align: center;
  background: #f8fbff;
  cursor: pointer;
  transition: border-color 0.2s, background 0.2s;

  &:hover, &.drag-over { border-color: #1976d2; background: #e3f2fd; }
  &.has-file { border-style: solid; border-color: #4caf50; background: #f1f8e9; }

  .drop-icon { font-size: 2.5em; display: block; margin-bottom: 12px; }
  .drop-types { display: block; font-size: 0.82em; color: #888; margin-top: 6px; }
  .file-info { display: flex; align-items: center; gap: 12px; justify-content: center; }
  .file-name { font-weight: 600; color: #1976d2; }
  .file-size { color: #888; font-size: 0.85em; }
}

.form-field {
  margin-top: 20px;
  label { display: block; font-size: 0.82em; font-weight: 600; color: #555; margin-bottom: 6px; text-transform: uppercase; letter-spacing: 0.05em; }
  .optional { font-weight: 400; color: #aaa; }
  textarea, input[type="text"] { width: 100%; padding: 10px 12px; border: 1px solid #ddd; border-radius: 6px; font-size: 0.9em; resize: vertical; box-sizing: border-box; }
}

// ── Plan step ─────────────────────────────────────────────────────────────────
.plan-header { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 20px; }
.filename { font-size: 0.85em; color: #888; }
.summary-box { background: #e8f5e9; border-radius: 8px; padding: 16px; margin-bottom: 20px; ul { margin: 0; padding-left: 18px; li { line-height: 1.8; font-size: 0.88em; } } }
.section-label { font-size: 0.75em; font-weight: 700; color: #555; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 8px; }
.classification-badges { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 20px; }
.badge { background: #e3f2fd; padding: 10px 16px; border-radius: 8px; font-size: 0.82em; .badge-label { display: block; color: #888; font-size: 0.85em; } .badge-value { font-weight: 600; } }
.ops-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px; }
.ops-list { list-style: none; padding: 0; margin: 0; background: #f9f9f9; border-radius: 6px; padding: 12px; li { display: flex; flex-direction: column; gap: 2px; margin-bottom: 10px; font-size: 0.83em; } .op-path { font-family: monospace; color: #333; } .op-desc, .op-preview { color: #888; font-size: 0.9em; } .empty { color: #bbb; font-style: italic; } }
.warnings-box { background: #fff8e1; border: 1px solid #ffe082; border-radius: 8px; padding: 12px; margin-bottom: 20px; .warning-item { font-size: 0.85em; } }
.plan-actions { display: flex; gap: 12px; }

// ── Execute step ──────────────────────────────────────────────────────────────
.execute-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.elapsed { font-size: 0.85em; color: #888; }
.progress-list { margin-bottom: 16px; }
.progress-item { display: flex; gap: 10px; align-items: flex-start; font-size: 0.84em; line-height: 2; &.done { color: #2e7d32; } &.error { color: #c62828; } &.in_progress { color: #1976d2; } &.pending { color: #ccc; } }
.progress-bar { background: #e0e0e0; border-radius: 4px; height: 6px; margin-bottom: 24px; .progress-fill { background: #1976d2; height: 6px; border-radius: 4px; transition: width 0.3s; } }
.success-box { background: #e8f5e9; border-radius: 8px; padding: 16px; margin-bottom: 16px; .success-title { font-weight: 600; color: #2e7d32; margin-bottom: 10px; } }
.result-links { display: flex; flex-wrap: wrap; gap: 8px; .result-link { color: #1976d2; font-size: 0.85em; text-decoration: none; &:hover { text-decoration: underline; } } }
.error-box { background: #ffebee; border-radius: 8px; padding: 16px; margin-bottom: 16px; .error-title { font-weight: 600; color: #c62828; } .error-detail { font-size: 0.85em; color: #555; margin-top: 6px; } }
.warning-note { font-size: 0.8em; color: #888; text-align: center; margin-top: 12px; }
.error-banner { background: #ffebee; color: #c62828; padding: 12px; border-radius: 6px; margin-top: 12px; font-size: 0.88em; }
.planning-spinner { display: flex; flex-direction: column; align-items: center; gap: 16px; padding: 80px 0; .spinner { width: 40px; height: 40px; border: 3px solid #e0e0e0; border-top-color: #1976d2; border-radius: 50%; animation: spin 0.8s linear infinite; } }
@keyframes spin { to { transform: rotate(360deg); } }

// ── Shared buttons ────────────────────────────────────────────────────────────
.btn-primary { width: 100%; padding: 14px; background: #1976d2; color: white; border: none; border-radius: 8px; font-size: 1em; font-weight: 600; cursor: pointer; &:hover:not(:disabled) { background: #1565c0; } &:disabled { opacity: 0.5; cursor: not-allowed; } }
.btn-approve { flex: 2; padding: 13px; background: #2e7d32; color: white; border: none; border-radius: 8px; font-weight: 600; font-size: 0.95em; cursor: pointer; &:hover { background: #1b5e20; } }
.btn-secondary { flex: 1; padding: 13px; background: #f5f5f5; color: #555; border: none; border-radius: 8px; font-size: 0.95em; cursor: pointer; &:hover { background: #e0e0e0; } }
```

**Note:** Update `ingest.ts` to use a separate template file by changing `template:` to `templateUrl: './ingest.html'` — this was included in the component definition above.

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit 2>&1 | grep -E "ingest" | head -20
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/app/features/ingest/
git commit -m "feat(ingest): main ingest page — step state machine wiring upload/plan/execute"
```

---

## Task 12: Route, Nav, and `.gitignore`

**Files:**
- Modify: `frontend/src/app/app.routes.ts`
- Modify: `frontend/src/app/app.html`
- Modify: `.gitignore`

- [ ] **Step 1: Add route to `app.routes.ts`**

Open `frontend/src/app/app.routes.ts`. Find the `traces/:traceId` route entry. Add immediately after it (before the wildcard `**` redirect):

```typescript
{
  path: 'ingest',
  canActivate: [authGuard],
  loadComponent: () => import('./features/ingest/ingest').then(m => m.Ingest),
},
```

- [ ] **Step 2: Add nav link to `app.html`**

Open `frontend/src/app/app.html`. Find `<a routerLink="/admin" routerLinkActive="active" class="nav-link">Admin</a>`. Add immediately before it:

```html
<a routerLink="/ingest" routerLinkActive="active" class="nav-link">Ingest</a>
```

- [ ] **Step 3: Add `_uploads/` to `.gitignore`**

Open `.gitignore`. Add:

```
# Ingest uploads (ephemeral — moved to raw/modules/{slug}/ on success)
raw/modules/_uploads/
```

- [ ] **Step 4: Verify app compiles**

```bash
cd frontend && ng build 2>&1 | tail -10
```

Expected: `Application bundle generation complete.` with no errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/app/app.routes.ts frontend/src/app/app.html .gitignore
git commit -m "feat(ingest): add /ingest route and nav link; gitignore _uploads/"
```

---

## Task 13: End-to-End Verification

Run this test manually with a real document before marking the feature done.

- [ ] **Step 1: Start the backend**

```bash
cd /Users/rudrakhare/Desktop/my-wiki/org-wiki
uvicorn backend.api:app --reload --port 8000
```

Verify startup: `curl localhost:8000/health` — confirm `wiki_pages` count is shown.

- [ ] **Step 2: Start the frontend**

```bash
cd frontend && ng serve
```

Open `http://localhost:4200/ingest` — should see the upload step UI.

- [ ] **Step 3: Upload a real document**

Pick any PDF from `raw/modules/visitor-management/` (or any module folder). Drag it onto the drop zone. Add a note: "Test ingest — visitor management doc". Click "Upload & Analyse".

Expected: spinner appears while planning, then plan review screen with:
- 5-8 bullet summary
- `target_slug: visitor-management`
- Operations list with at least one "create" (source page)

- [ ] **Step 4: Approve and watch execute**

Click "Approve & Execute →". Watch SSE stream:
- Each operation should show `✅ Created wiki/sources/...`
- Final `✅ Ingestion complete` with links

- [ ] **Step 5: Verify audit trail**

```bash
python scripts/audit_ingest.py 2>&1 | grep visitor
```

Expected: the uploaded file shows as "ingested" (not "not ingested").

- [ ] **Step 6: Verify index rebuilt**

```bash
curl localhost:8000/health
```

Expected: `wiki_pages` count is higher than before.

- [ ] **Step 7: Verify log entry**

```bash
tail -20 wiki/log.md
```

Expected: new timestamped ingest entry at the bottom.

- [ ] **Step 8: Test mutex**

Open a second browser tab. Navigate to `/ingest`. Try to upload while the first ingest is running.
Expected: `409 Conflict` toast/error: "Another ingestion is in progress."

- [ ] **Step 9: Test session expiry**

Start a plan, wait 11+ minutes without approving, then click Approve.
Expected: `410 Gone` error: "Plan expired, please re-upload."

- [ ] **Step 10: Run full test suite**

```bash
python -m pytest tests/test_document_extractor.py tests/test_wiki_write_tools.py tests/test_wiki_read_tools.py tests/test_ingest_service.py tests/test_ingest_api.py -v
```

Expected: all tests PASS.

- [ ] **Step 11: Final commit**

```bash
git add -A
git commit -m "feat(ingest): end-to-end verification pass — UI document ingestion complete"
```

---

## Summary

13 tasks, approximately 3 weeks of focused work:

| Week | Tasks | Outcome |
|---|---|---|
| 1 | 1–4 | Backend foundations: extractor, tools, service — fully tested |
| 2 | 5–6 | API endpoints with agent loops — plan + execute working |
| 3 | 7–12 | Frontend: API service + 3 components + route/nav |
| End | 13 | E2E verification with a real document |

Each task ends with a commit. The backend can be verified independently before the frontend is built (use `curl` or Postman against the API endpoints).
