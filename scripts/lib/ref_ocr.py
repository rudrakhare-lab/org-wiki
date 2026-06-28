"""OCR a screenshot to text by reusing the backend's Claude Vision extractor."""
from __future__ import annotations

import pathlib
import sys

# Make the repo root importable so `backend` resolves when run as a script.
_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from backend.document_extractor import extract_image  # noqa: E402

# R4 instructional OCR prompt. NOTE: the crawler's bulk OCR (ocr_image, below) uses
# extract_image's generic built-in prompt — that is the searchable coverage layer.
# This instructional prompt is captured for authoring time: Claude reads key screenshots
# in-context with this intent while writing runbooks (R4 addendum + R7 collector-vs-author).
# It is intentionally NOT wired into extract_image (which accepts no prompt arg); doing so
# would be a separate, out-of-scope backend change.
INSTRUCTIONAL_OCR_PROMPT = (
    "This is a screenshot from an SE configuration runbook. State (1) what tool/screen "
    "is shown (Postman, browser, admin UI), (2) the action being performed "
    "(GET/PUT/click/select), (3) what to look for or do next. Transcribe all visible "
    "text, URLs, and config keys verbatim. CRITICAL: treat example values — BUIDs like "
    "`tata-TCPOC`, office names, GUIDs, phone numbers — as ILLUSTRATIVE PLACEHOLDERS; "
    "label them 'example', never as literal config."
)


def ocr_image(image_path: str) -> str:
    """Extract text from a screenshot using the backend's Vision extractor.

    Never raises; returns a marker string on any error to keep bulk OCR crawls resilient.

    Args:
        image_path: Path to the screenshot file.

    Returns:
        Extracted text, or "[OCR failed: <exception>]" if extraction failed.
    """
    try:
        return (extract_image(image_path) or {}).get("text", "") or ""
    except Exception as exc:  # never let one bad screenshot break the crawl
        return f"[OCR failed: {exc}]"
