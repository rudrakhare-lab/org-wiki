#!/usr/bin/env python3
"""
list_pending.py — List raw files not yet ingested into the wiki.

A raw file is considered "ingested" when there is a matching wiki/sources/<stem>.md
page (the AI creates one source-summary page per ingested file).

Run this any time after a Drive sync to see what's queued up for ingest.

Usage
-----
  python scripts/list_pending.py
  python scripts/list_pending.py --feature desk-management
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "raw"
SOURCES = ROOT / "wiki" / "sources"

# Only flag these as candidates for ingest. Images/CSVs etc. are auxiliary.
INGEST_EXT = {".pdf", ".md", ".txt", ".docx", ".doc", ".rtf", ".yaml", ".yml"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--feature", help="Only show pending files for this feature slug")
    args = ap.parse_args()

    if not SOURCES.exists():
        ingested_stems: set[str] = set()
    else:
        ingested_stems = {p.stem for p in SOURCES.glob("*.md")}

    pending: list[Path] = []
    for raw_file in RAW.rglob("*"):
        if not raw_file.is_file():
            continue
        if raw_file.name in {".gitkeep", ".sync_manifest.json", ".DS_Store"}:
            continue
        if raw_file.suffix.lower() not in INGEST_EXT:
            continue
        if raw_file.stem in ingested_stems:
            continue
        rel = raw_file.relative_to(ROOT)
        if args.feature and args.feature not in str(rel):
            continue
        pending.append(rel)

    if not pending:
        if args.feature:
            print(f"No pending files for feature: {args.feature}")
        else:
            print("All raw files have been ingested. Nothing pending.")
        return 0

    by_folder: dict[str, list[str]] = {}
    for f in pending:
        by_folder.setdefault(str(f.parent), []).append(f.name)

    print(f"{len(pending)} file(s) pending ingest:\n")
    for folder in sorted(by_folder):
        names = sorted(by_folder[folder])
        print(f"  {folder}/  ({len(names)} file{'s' if len(names) != 1 else ''})")
        for name in names:
            print(f"    - {name}")
        print()

    print("To ingest in Cursor chat, run one of these:\n")
    for folder in sorted(by_folder):
        print(f"  ingest all docs in {folder}/")

    return 0


if __name__ == "__main__":
    sys.exit(main())
