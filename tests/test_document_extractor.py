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
