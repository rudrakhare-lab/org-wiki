"""Tests for document_extractor — uses real tiny fixtures."""
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

    content = "Hello world\nLine two"
    p = make_txt(tmp, "hello.txt", content)
    result = extract_text_file(str(p))
    assert result["text"] == content
    assert result["char_count"] == len(content)


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


def test_xlsx_truncation(tmp):
    from backend.document_extractor import extract_xlsx
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "Big"
    # Each row ~ 100 chars; 600 rows = ~60k chars > MAX_CHARS
    for i in range(600):
        ws.append([f"property_{i}", "x" * 90])
    p = tmp / "big.xlsx"
    wb.save(str(p))

    result = extract_xlsx(str(p))
    assert result["truncated"] is True
    assert len(result["text_repr"]) == 50_000
    assert result["char_count"] > 50_000
    assert "sheets" in result


# ── image extraction tests ───────────────────────────────────────────────────

# Minimal valid 1x1 PNG
_TINY_PNG = bytes([
    0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,  # PNG signature
    0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,  # IHDR chunk length + type
    0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,  # width=1, height=1
    0x08, 0x02, 0x00, 0x00, 0x00, 0x90, 0x77, 0x53,  # bit depth, colour type, ...
    0xDE, 0x00, 0x00, 0x00, 0x0C, 0x49, 0x44, 0x41,  # IDAT chunk
    0x54, 0x08, 0xD7, 0x63, 0xF8, 0xCF, 0xC0, 0x00,
    0x00, 0x00, 0x02, 0x00, 0x01, 0xE2, 0x21, 0xBC,
    0x33, 0x00, 0x00, 0x00, 0x00, 0x49, 0x45, 0x4E,  # IEND chunk
    0x44, 0xAE, 0x42, 0x60, 0x82,
])


def test_extract_image_returns_text_and_title(tmp):
    from unittest.mock import MagicMock, patch
    from backend.document_extractor import extract_image

    img_path = tmp / "diagram.png"
    img_path.write_bytes(_TINY_PNG)

    mock_client = MagicMock()
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text="## Architecture\nService A calls Service B.")]
    )

    with patch("backend.document_extractor._get_anthropic_client", return_value=mock_client):
        result = extract_image(str(img_path))

    assert "text" in result
    assert "title" in result
    assert "Architecture" in result["text"]
    assert result["char_count"] > 0
    assert result["truncated"] is False


def test_extract_image_title_fallback(tmp):
    """When response has no heading, title falls back to filename stem."""
    from unittest.mock import MagicMock, patch
    from backend.document_extractor import extract_image

    img_path = tmp / "mydiagram.png"
    img_path.write_bytes(_TINY_PNG)

    mock_client = MagicMock()
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text="This is a plain description with no heading.")]
    )

    with patch("backend.document_extractor._get_anthropic_client", return_value=mock_client):
        result = extract_image(str(img_path))

    # First non-empty line is used as title (no # prefix)
    assert result["title"] == "This is a plain description with no heading."


def test_extract_image_unsupported_extension(tmp):
    from backend.document_extractor import extract_image, UnsupportedFileType

    p = tmp / "file.bmp"
    p.write_bytes(b"fake")
    with pytest.raises(UnsupportedFileType):
        extract_image(str(p))


def test_extract_image_dispatched_by_extract_document(tmp):
    """extract_document() should dispatch .png to extract_image()."""
    from unittest.mock import MagicMock, patch
    from backend.document_extractor import extract_document

    img_path = tmp / "arch.png"
    img_path.write_bytes(_TINY_PNG)

    mock_client = MagicMock()
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text="## Flow\nStep 1 → Step 2")]
    )

    with patch("backend.document_extractor._get_anthropic_client", return_value=mock_client):
        result = extract_document(str(img_path))

    assert "text" in result
    assert "Flow" in result["text"]


def test_image_extensions_exported():
    """IMAGE_EXTENSIONS must be importable from document_extractor for ingest_api.py."""
    from backend.document_extractor import IMAGE_EXTENSIONS
    assert ".png" in IMAGE_EXTENSIONS
    assert ".jpg" in IMAGE_EXTENSIONS
    assert ".jpeg" in IMAGE_EXTENSIONS
    assert ".webp" in IMAGE_EXTENSIONS
    assert ".gif" in IMAGE_EXTENSIONS
