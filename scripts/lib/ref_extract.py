"""Extract outbound links and embedded images from fetched Office files.

The depth guarantee of the crawl lives here: every link a file contains must
be surfaced so the frontier loop can enqueue it. For spreadsheets that means
every tab and every cell hyperlink; for decks, every slide and shape.

Return contract (R3):
    extract_links_and_images(local_path, image_dir)
        -> tuple[list[str], list[dict]]

    urls:   list of external URL strings.
    images: list of dicts, one per embedded image written, in document order:
            {"path": <str>, "section": <str|None>, "nearby_text": <str|None>}

    - section    : text of the nearest *preceding* heading paragraph
                   (style name starts with "Heading"); None if not found.
    - nearby_text: text of the nearest *preceding* non-empty non-heading
                   paragraph; None if not found.

Tasks 4/5 append .xlsx/.pptx branches and map their own context onto the
same three keys — do NOT rename them.
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


def _extract_docx(path: str, image_dir: str) -> tuple[list[str], list[dict]]:
    """Extract URLs and context-tagged images from a .docx file.

    URL extraction: walks doc.part.rels for external hyperlink relationships
    (these have no document position but are exhaustive for all hyperlinks).

    Image extraction: walks the document body in element order, tracking the
    current heading and last non-empty paragraph as context.  Inline images
    are found via a:blip/@r:embed → the image part's blob.  This body-walk
    technique is adapted from raw/se-runbook/_extract/extract_maindoc.py.txt.
    """
    from docx import Document
    from docx.oxml.ns import qn
    from docx.text.paragraph import Paragraph

    doc = Document(path)
    stem = pathlib.Path(path).stem

    # ── 1. Collect URLs from all relationships ────────────────────────────
    urls: list[str] = []
    for rel in doc.part.rels.values():
        if _HYPERLINK_REL in rel.reltype and rel.is_external:
            urls.append(rel.target_ref)

    # ── 2. Body-walk for images with section/nearby_text context ─────────
    images: list[dict] = []
    idx = 0
    current_section: str | None = None
    last_nearby: str | None = None

    for child in doc.element.body.iterchildren():
        if child.tag == qn("w:p"):
            p = Paragraph(child, doc)
            style_name: str = p.style.name if p.style is not None else ""
            text = p.text.strip()

            if style_name.startswith("Heading"):
                current_section = text or None
                # A heading also resets nearby_text — the heading IS the new
                # context boundary; paragraph text after the heading is what
                # we want for nearby_text, not the heading itself.
                last_nearby = None
            elif text:
                last_nearby = text

            # Find all inline image references in this paragraph
            for blip in p._p.findall(".//" + qn("a:blip")):
                embed = blip.get(qn("r:embed"))
                if embed and embed in doc.part.rels:
                    rel = doc.part.rels[embed]
                    try:
                        blob = rel.target_part.blob
                        ext = pathlib.Path(rel.target_part.partname).suffix or ".png"
                        img_path = _write_blob(blob, image_dir, stem, idx, ext)
                        images.append(
                            {
                                "path": img_path,
                                "section": current_section,
                                "nearby_text": last_nearby,
                            }
                        )
                        idx += 1
                    except Exception:
                        pass

    return urls, images


def extract_links_and_images(
    local_path: str, image_dir: str
) -> tuple[list[str], list[dict]]:
    """Dispatch to the correct extractor based on file extension.

    Supported: .docx (Task 3).  .xlsx and .pptx added in Tasks 4/5.

    Raises:
        ValueError: if the file extension has no registered extractor.
    """
    ext = pathlib.Path(local_path).suffix.lower()
    if ext == ".docx":
        return _extract_docx(local_path, image_dir)
    raise ValueError(f"no extractor for {ext!r}")
