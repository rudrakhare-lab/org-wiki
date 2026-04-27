#!/usr/bin/env python3
"""
sync_drive.py — Mirror the WorkInSync Google Drive folder into raw/modules/.

The script is **source-agnostic**: point it at any local path that contains the
Drive folder structure (rclone mount, Google Drive Desktop folder, or a manually
unzipped download). It will:

  1. Walk every top-level subfolder ("feature folder") in the source.
  2. Resolve the canonical slug (via SLUG_OVERRIDES first, then slugify()).
  3. Mirror its contents into raw/modules/<slug>/.
  4. Skip files that already exist with identical content (SHA-256 dedup).
  5. Optionally skip "Copy of ..." duplicates (--skip-copies).
  6. Create raw/modules/<slug>/ automatically if the feature is genuinely new.
  7. Print a per-feature report of new / updated / unchanged files.
  8. Suggest the next `ingest` commands for files that changed.

The script is **idempotent** — safe to re-run any time. It only copies what is
actually new or changed.

Examples
--------
  # Drive Desktop (typical macOS path)
  python scripts/sync_drive.py \\
      --source "$HOME/Library/CloudStorage/GoogleDrive-<email>/My Drive/Conwo WorkInSync Docs"

  # rclone staging folder
  python scripts/sync_drive.py --source ./raw/_drive_staging

  # Preview without copying
  python scripts/sync_drive.py --source <path> --dry-run

  # Skip "Copy of ..." duplicates (recommended for clean ingest)
  python scripts/sync_drive.py --source <path> --skip-copies

  # Sync just one feature
  python scripts/sync_drive.py --source <path> --only meeting-rooms
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent
RAW_MODULES = ROOT / "raw" / "modules"
MANIFEST_PATH = ROOT / "raw" / ".sync_manifest.json"

# ---------------------------------------------------------------------------
# Slug overrides
#
# Drive folder names that would slugify to a long/wrong slug are mapped here
# to the canonical slug we want. Keys are matched against the slugified Drive
# folder name (not the raw name), so you only need the simplified version.
#
# Add a new line whenever Drive has a folder with a long/variant name that
# should map to an existing canonical slug.
# ---------------------------------------------------------------------------

SLUG_OVERRIDES: dict[str, str] = {
    # Drive folder name (slugified)          → canonical slug
    "digital-wayfinding-kavya":                "digital-wayfinding",
    "employee-provisioning-via-external-integrations": "employee-provisioning",
    "third-party-integrations-slack":          "third-party",
    "access-management-integration":           "access-management",
    "desk-management-admin-employee-experience": "desk-management",
    "guard-app-kiosks-for-guard-app":          "guard-app-kiosks",
    "tags-desk-parking-dynamic-policy-engine": "tags-desk-parking",
    # Add more as Drive folder names evolve:
    # "some-verbose-drive-name":             "canonical-slug",
}

# ---------------------------------------------------------------------------
# Filters
# ---------------------------------------------------------------------------

# Google native docs cannot be copied as raw files — they must be exported first.
GOOGLE_NATIVE_EXT = {".gdoc", ".gsheet", ".gslides", ".gform", ".gdraw", ".gsite", ".gmap"}

# Filenames to always ignore (system / lock files).
IGNORE_NAMES = {".DS_Store", ".gitkeep", "Thumbs.db", "desktop.ini"}
IGNORE_PREFIXES = ("~$", ".~lock.")

# File extensions we actively want to bring in.
ACCEPT_EXT = {".pdf", ".md", ".txt", ".docx", ".doc", ".rtf", ".csv", ".xlsx",
              ".png", ".jpg", ".jpeg", ".svg", ".yaml", ".yml", ".json"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def slugify(name: str) -> str:
    """Convert a Drive folder name to a kebab-case slug.

    Strips parenthetical owner annotations (e.g. ``(Kavya)``, ``(KAVYA)``,
    ``(Mohit)``) and normalizes punctuation/whitespace to single hyphens.

    Examples
    --------
    >>> slugify("Floor Kiosk (Kavya)")
    'floor-kiosk'
    >>> slugify("MS Teams Integration")
    'ms-teams-integration'
    >>> slugify("Tags - desk + parking")
    'tags-desk-parking'
    >>> slugify("Third-party")
    'third-party'
    """
    cleaned = re.sub(r"\s*\([^)]*\)\s*", " ", name)
    cleaned = cleaned.lower().strip()
    cleaned = re.sub(r"[^a-z0-9]+", "-", cleaned)
    return cleaned.strip("-")


def resolve_slug(raw_folder_name: str) -> tuple[str, bool]:
    """Return (canonical_slug, was_overridden).

    First checks SLUG_OVERRIDES (keyed on the pre-override slugified name),
    then falls back to the plain slugify result.
    """
    auto = slugify(raw_folder_name)
    if auto in SLUG_OVERRIDES:
        return SLUG_OVERRIDES[auto], True
    return auto, False


def is_copy(filename: str) -> bool:
    """Return True if the filename looks like a Drive 'Copy of ...' duplicate."""
    return re.match(r"^(Copy of\s+)+", filename, re.IGNORECASE) is not None


def file_sha256(path: Path, chunk_size: int = 65536) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()


def classify_skip(name: str, skip_copies: bool) -> str | None:
    """Return a skip reason string, or None if the file should be processed."""
    if name in IGNORE_NAMES:
        return "ignored"
    for prefix in IGNORE_PREFIXES:
        if name.startswith(prefix):
            return "lock"
    ext = Path(name).suffix.lower()
    if ext in GOOGLE_NATIVE_EXT:
        return "google-native"
    if ACCEPT_EXT and ext and ext not in ACCEPT_EXT:
        return f"unsupported-ext({ext})"
    if skip_copies and is_copy(name):
        return "copy-duplicate"
    return None


# ---------------------------------------------------------------------------
# Sync
# ---------------------------------------------------------------------------

def sync_feature(
    src_root: Path,
    dst_root: Path,
    feature_slug: str,
    dry_run: bool,
    verbose: bool,
    skip_copies: bool,
) -> tuple[dict, list[str]]:
    """Sync one feature folder. Returns (counts, skipped_messages)."""
    counts = {"new": 0, "updated": 0, "unchanged": 0, "skipped": 0}
    skipped: list[str] = []

    for src in sorted(src_root.rglob("*")):
        if src.is_dir():
            continue
        rel = src.relative_to(src_root)

        reason = classify_skip(src.name, skip_copies)
        if reason:
            counts["skipped"] += 1
            if reason == "google-native":
                skipped.append(f"{feature_slug}/{rel}  (Google native — export to PDF first)")
            elif reason == "copy-duplicate":
                skipped.append(f"{feature_slug}/{rel}  (Drive 'Copy of' duplicate — skipped)")
            elif reason.startswith("unsupported"):
                skipped.append(f"{feature_slug}/{rel}  ({reason})")
            continue

        dst = dst_root / rel

        verb: str
        if dst.exists():
            same_size = dst.stat().st_size == src.stat().st_size
            if same_size and file_sha256(src) == file_sha256(dst):
                counts["unchanged"] += 1
                if verbose:
                    print(f"  [SAME  ] {feature_slug}/{rel}")
                continue
            counts["updated"] += 1
            verb = "UPDATE"
        else:
            counts["new"] += 1
            verb = "NEW   "

        if not dry_run:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        print(f"  [{verb}] {feature_slug}/{rel}")

    return counts, skipped


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument(
        "--source", required=True,
        help="Local path to the Drive root (folder containing all feature subfolders)",
    )
    ap.add_argument("--dry-run", action="store_true", help="Report changes but do not copy files")
    ap.add_argument("--only", help="Sync only this canonical feature slug (e.g. meeting-rooms)")
    ap.add_argument("--skip-copies", action="store_true",
                    help="Skip files whose names start with 'Copy of ...' (Drive duplicates)")
    ap.add_argument("-v", "--verbose", action="store_true", help="Also print files that were unchanged")
    args = ap.parse_args()

    src_root = Path(args.source).expanduser().resolve()
    if not src_root.is_dir():
        print(f"ERROR: source is not a directory: {src_root}", file=sys.stderr)
        return 2

    print(f"Source      : {src_root}")
    print(f"Target      : {RAW_MODULES.relative_to(ROOT)}/")
    print(f"Skip copies : {'yes' if args.skip_copies else 'no'}")
    if args.dry_run:
        print("Mode        : DRY RUN (no files will be copied)")
    print()

    if not args.dry_run:
        RAW_MODULES.mkdir(parents=True, exist_ok=True)

    totals = {"new": 0, "updated": 0, "unchanged": 0, "skipped": 0}
    new_features: list[str] = []
    overridden_slugs: list[tuple[str, str, str]] = []  # (drive_name, raw_slug, canonical_slug)
    feature_reports: list[tuple[str, dict, bool]] = []
    all_skipped: list[str] = []

    for src_feature_dir in sorted(p for p in src_root.iterdir() if p.is_dir() and not p.name.startswith(".")):
        slug, was_overridden = resolve_slug(src_feature_dir.name)
        if not slug:
            continue
        if args.only and slug != args.only:
            continue
        if was_overridden:
            raw_auto = slugify(src_feature_dir.name)
            overridden_slugs.append((src_feature_dir.name, raw_auto, slug))

        dst_dir = RAW_MODULES / slug
        is_new_feature = not dst_dir.exists()
        if is_new_feature:
            new_features.append(slug)
            if not args.dry_run:
                dst_dir.mkdir(parents=True, exist_ok=True)
                (dst_dir / ".gitkeep").touch()

        counts, skipped = sync_feature(
            src_feature_dir, dst_dir, slug,
            args.dry_run, args.verbose, args.skip_copies,
        )
        all_skipped.extend(skipped)
        for k in totals:
            totals[k] += counts[k]
        feature_reports.append((slug, counts, is_new_feature))

    # ---------------- Report ----------------
    print()
    print("=" * 64)
    print("Drive Sync Report")
    print("=" * 64)

    if overridden_slugs:
        print(f"\nSlug overrides applied ({len(overridden_slugs)}):")
        for drive_name, raw_slug, canonical in overridden_slugs:
            print(f"  '{drive_name}'")
            print(f"    auto-slug : {raw_slug}")
            print(f"    canonical : {canonical}  ← used")

    if new_features:
        print(f"\nGenuinely new feature folders ({len(new_features)}):")
        for f in new_features:
            print(f"  + raw/modules/{f}/")

    print("\nPer-feature counts:")
    print(f"  {'feature':<38}  {'new':>4} {'upd':>4} {'unch':>5} {'skip':>4}")
    print(f"  {'-'*38}  {'----':>4} {'----':>4} {'-----':>5} {'----':>4}")
    for slug, counts, is_new in feature_reports:
        marker = "*" if is_new else " "
        print(f"  {marker} {slug:<36}  {counts['new']:>4} {counts['updated']:>4} "
              f"{counts['unchanged']:>5} {counts['skipped']:>4}")

    if all_skipped:
        print(f"\nSkipped ({len(all_skipped)} — first 15):")
        for s in all_skipped[:15]:
            print(f"  - {s}")
        if len(all_skipped) > 15:
            print(f"  ... and {len(all_skipped) - 15} more")

    print(f"\nTotal: {totals['new']} new | {totals['updated']} updated | "
          f"{totals['unchanged']} unchanged | {totals['skipped']} skipped")

    # Suggest ingest commands for changed features
    changed = [r[0] for r in feature_reports if r[1]["new"] + r[1]["updated"] > 0]
    if changed and not args.dry_run:
        print("\nNext: in Cursor chat, ingest each feature with new content:")
        for f in changed:
            print(f"  ingest all new docs in raw/modules/{f}/")

    # ---------------- Manifest ----------------
    if not args.dry_run:
        MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
        manifest = {
            "last_sync": datetime.now(timezone.utc).isoformat(),
            "source": str(src_root),
            "skip_copies": args.skip_copies,
            "totals": totals,
            "new_features": new_features,
            "slug_overrides_applied": [
                {"drive_folder": d, "auto_slug": a, "canonical": c}
                for d, a, c in overridden_slugs
            ],
            "features_with_changes": changed,
            "feature_counts": {slug: c for slug, c, _ in feature_reports},
        }
        MANIFEST_PATH.write_text(json.dumps(manifest, indent=2))
        print(f"\nManifest: {MANIFEST_PATH.relative_to(ROOT)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
