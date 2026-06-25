"""Tests for OCR wrapper."""
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
