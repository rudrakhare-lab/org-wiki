"""SE-runbook reference crawler — orchestrator, seed, and CLI.

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


def _record_and_ocr_images(manifest, images, ocr, source_file) -> None:
    """Record each extracted image in the manifest, OCR it, mark it done.

    Wires R2: screenshot coverage becomes provable via coverage_complete().
    Each image dict has keys: path, section (optional), nearby_text (optional).
    """
    for img in images:
        path = img["path"]
        manifest.add_image_if_new(
            path,
            source_file,
            section=img.get("section"),
            nearby_text=img.get("nearby_text"),
        )
        sidecar = path + ".txt"
        pathlib.Path(sidecar).parent.mkdir(parents=True, exist_ok=True)
        pathlib.Path(sidecar).write_text(ocr(path), encoding="utf-8")
        manifest.set_image_ocr(path, "done", ocr_text_path=sidecar)


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")


def _seed_links(manifest, links, depth, referenced_from) -> int:
    """Classify each URL and insert into manifest; mark terminal types immediately."""
    n = 0
    for url in links:
        ref_type, file_id = classify_url(url)
        if manifest.add_if_new(url, ref_type, depth, referenced_from, file_id=file_id):
            if ref_type in _TERMINAL:
                manifest.update_status(url, "terminal")
            n += 1
    return n


def seed_from_docx(manifest, docx_path, image_dir, ocr=ocr_image) -> int:
    """Extract links and images from the root DOCX; seed links at depth=1.

    Root doc screenshots are highest-value — they are recorded in the manifest
    and OCR'd immediately (R2 wiring). Returns count of links seeded.
    """
    links, images = extract_links_and_images(docx_path, image_dir)
    _record_and_ocr_images(manifest, images, ocr, source_file=docx_path)
    return _seed_links(manifest, links, depth=1, referenced_from="ROOT")


def crawl(
    manifest,
    files_dir,
    image_dir,
    fetcher=fetch_drive_file,
    extractor=extract_links_and_images,
    ocr=ocr_image,
    pdf_fetcher=fetch_pdf,
    pdf_linker=extract_pdf_links,
) -> dict:
    """Drain the manifest frontier to a fixpoint.

    For each fetchable ref:
      - fetch it
      - extract structured links + images (record/OCR images — R2)
      - union with PDF-render safety-net links
      - seed new links at depth+1
      - mark done

    Non-fetchable refs (jira/api/external) are immediately marked terminal.
    Returns manifest.report() dict.
    """
    while True:
        ref = manifest.next_discovered()
        if ref is None:
            break

        url, rtype, depth = ref["url"], ref["ref_type"], ref["depth"]

        if rtype not in _FETCHABLE:
            # jira / api / external — recorded for completeness, never fetched
            manifest.update_status(url, "terminal")
            continue

        result = fetcher(ref["file_id"], rtype, files_dir)
        if result.status != "fetched":
            manifest.update_status(url, result.status, error=result.error)
            continue

        manifest.update_status(
            url,
            "fetched",
            local_path=result.local_path,
            sha256=result.sha256,
            fetched_at=_now(),
        )

        links, images = extractor(result.local_path, image_dir)

        # R2: record and OCR every embedded screenshot found in this file
        _record_and_ocr_images(manifest, images, ocr, source_file=result.local_path)

        # Link-recall safety net: union with a throwaway PDF render
        # (PDF hyperlinks often survive even when the DOCX parser misses them)
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
    ap.add_argument(
        "--out",
        default="raw/se-runbook",
        help="Output dir (manifest + files + images)",
    )
    ap.add_argument(
        "--retry-denied",
        action="store_true",
        help="Reopen previously access_denied files (run after access is granted)",
    )
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
