#!/usr/bin/env python3
"""
audit_ingest.py — Find raw/modules/ files that have not been ingested into wiki/sources/.

Compares every primary document in raw/modules/ against the raw_path frontmatter
recorded in wiki/sources/*.md files. Reports:
  - Files NOT ingested (no matching wiki/sources/ page)
  - Files already ingested (with their source page)
  - Broken references (source page points to a file that no longer exists)

A file is considered ingested if any wiki/sources/*.md page has a raw_path field
that resolves to the same file (after normalizing path prefix differences).

Primary documents = .pdf, .xlsx, .docx, .doc, .rtf (not .txt extracts, not CSV
sub-expansions, not Google-native formats, not system files).

Usage:
  python scripts/audit_ingest.py
  python scripts/audit_ingest.py --module visitor-management
  python scripts/audit_ingest.py --show-ingested
  python scripts/audit_ingest.py --json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_MODULES = ROOT / "raw" / "modules"
WIKI_SOURCES = ROOT / "wiki" / "sources"

# File extensions treated as primary source documents worth tracking
PRIMARY_EXT = {".pdf", ".xlsx", ".docx", ".doc", ".rtf"}

# Extensions and names to always skip
GOOGLE_NATIVE_EXT = {".gdoc", ".gsheet", ".gslides", ".gform", ".gdraw", ".gsite", ".gmap"}
IGNORE_NAMES = {".DS_Store", ".gitkeep", "Thumbs.db", "desktop.ini"}
IGNORE_PREFIXES = ("~$", ".~lock.")


def _is_csv_subexpansion(path: Path) -> bool:
    """True if this CSV lives inside a folder that is an xlsx expansion."""
    if path.suffix.lower() != ".csv":
        return False
    parent = path.parent
    return (parent.parent / (parent.name + ".xlsx")).exists()


def is_primary_doc(path: Path) -> bool:
    """Return True if this file counts as an ingestable primary document."""
    name = path.name
    if name in IGNORE_NAMES:
        return False
    for prefix in IGNORE_PREFIXES:
        if name.startswith(prefix):
            return False
    ext = path.suffix.lower()
    if ext in GOOGLE_NATIVE_EXT:
        return False
    if ext not in PRIMARY_EXT:
        return False
    if _is_csv_subexpansion(path):
        return False
    return True


def _normalize_raw_path(raw_path: str) -> str:
    """Normalize raw_path to always start with 'raw/modules/' for comparison."""
    rp = raw_path.strip()
    # Some entries are stored as "modules/..." instead of "raw/modules/..."
    if rp.startswith("modules/"):
        rp = "raw/" + rp
    return rp


def collect_ingested_paths() -> dict[str, str]:
    """Return {normalized_raw_path: wiki_source_filename} for all ingested sources.

    Walks wiki/sources/ (including jira/ subdirectory) and reads raw_path frontmatter.
    """
    ingested: dict[str, str] = {}
    if not WIKI_SOURCES.is_dir():
        return ingested

    for md in WIKI_SOURCES.rglob("*.md"):
        raw_path = _extract_frontmatter_field(md, "raw_path")
        if raw_path:
            normalized = _normalize_raw_path(raw_path)
            ingested[normalized] = md.name

    return ingested


def _extract_frontmatter_field(md_path: Path, field: str) -> str | None:
    """Extract a single field value from YAML frontmatter of a markdown file."""
    try:
        text = md_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None

    in_frontmatter = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped == "---":
            if not in_frontmatter:
                in_frontmatter = True
                continue
            else:
                break  # End of frontmatter block
        if in_frontmatter and stripped.startswith(field + ":"):
            val = stripped[len(field) + 1:].strip().strip('"').strip("'")
            return val if val else None

    return None


def collect_raw_files(module_filter: str | None = None) -> list[Path]:
    """Return all primary-doc files under raw/modules/, optionally filtered by module slug."""
    files: list[Path] = []
    if not RAW_MODULES.is_dir():
        return files

    for path in sorted(RAW_MODULES.rglob("*")):
        if not path.is_file():
            continue
        if module_filter:
            try:
                top = path.relative_to(RAW_MODULES).parts[0]
            except (ValueError, IndexError):
                continue
            if top != module_filter:
                continue
        if is_primary_doc(path):
            files.append(path)

    return files


def _rel(path: Path) -> str:
    """Return path relative to ROOT as a forward-slash string."""
    return path.relative_to(ROOT).as_posix()


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--module", help="Audit only this module slug (e.g. visitor-management)")
    ap.add_argument("--skip-copies", action="store_true",
                    help="Suppress files whose names start with 'Copy of' "
                         "(these are Drive duplicates of already-ingested docs)")
    ap.add_argument("--show-ingested", action="store_true",
                    help="Also list files that are already ingested")
    ap.add_argument("--json", dest="as_json", action="store_true",
                    help="Output machine-readable JSON")
    args = ap.parse_args()

    ingested = collect_ingested_paths()  # normalized_raw_path → source_page_name
    raw_files = collect_raw_files(args.module)

    not_ingested: list[str] = []
    already_ingested: list[tuple[str, str]] = []
    skipped_copies: list[str] = []

    for raw_file in raw_files:
        rel = _rel(raw_file)
        # Skip "Copy of ..." files if requested — they're Drive duplicates
        if args.skip_copies and re.match(r"^(Copy of\s+)+", raw_file.name, re.IGNORECASE):
            skipped_copies.append(rel)
            continue
        if rel in ingested:
            already_ingested.append((rel, ingested[rel]))
        else:
            not_ingested.append(rel)

    # Detect broken references: source page references a file that no longer exists
    broken_refs: list[tuple[str, str]] = []
    for norm_path, source_page in ingested.items():
        if args.module and not norm_path.startswith(f"raw/modules/{args.module}/"):
            continue
        if not (ROOT / norm_path).exists():
            broken_refs.append((norm_path, source_page))

    # ---- JSON output ----
    if args.as_json:
        print(json.dumps({
            "not_ingested": not_ingested,
            "ingested": [{"raw_path": r, "source_page": s} for r, s in already_ingested],
            "broken_refs": [{"raw_path": r, "source_page": s} for r, s in broken_refs],
            "summary": {
                "not_ingested": len(not_ingested),
                "ingested": len(already_ingested),
                "broken_refs": len(broken_refs),
            },
        }, indent=2))
        return 1 if not_ingested else 0

    # ---- Text report ----
    print("=" * 64)
    print("Ingest Audit Report")
    print("=" * 64)
    if args.module:
        print(f"Module filter : {args.module}")
    if args.skip_copies:
        print(f"(Skipping {len(skipped_copies)} 'Copy of ...' duplicate files)")
    print()

    if not_ingested:
        # Group by module slug
        by_module: dict[str, list[str]] = {}
        for rel in not_ingested:
            try:
                module_slug = Path(rel).relative_to("raw/modules").parts[0]
            except (ValueError, IndexError):
                module_slug = "_unknown"
            by_module.setdefault(module_slug, []).append(rel)

        print(f"NOT INGESTED — {len(not_ingested)} file(s) across {len(by_module)} module(s):")
        for module_slug, files in sorted(by_module.items()):
            print(f"\n  [{module_slug}]")
            for f in files:
                filename = Path(f).name
                print(f"    - {filename}")
                print(f"      ({f})")
    else:
        print("All primary docs in raw/modules/ have a wiki/sources/ page. ✓")

    if broken_refs:
        print(f"\nBROKEN REFERENCES — {len(broken_refs)} source page(s) reference missing files:")
        for raw_path, source_page in broken_refs:
            print(f"  - wiki/sources/{source_page}  →  {raw_path}  (file missing)")

    if args.show_ingested and already_ingested:
        print(f"\nALREADY INGESTED — {len(already_ingested)} file(s):")
        for raw_path, source_page in already_ingested:
            print(f"  ✓ {raw_path}  →  wiki/sources/{source_page}")

    print()
    print(f"Summary: {len(not_ingested)} not ingested | "
          f"{len(already_ingested)} ingested | "
          f"{len(broken_refs)} broken refs")

    return 1 if not_ingested else 0


if __name__ == "__main__":
    sys.exit(main())
