#!/usr/bin/env python3
"""
sync_drive.py — Mirror the WorkInSync Google Drive folder into raw/modules/.

The script is **source-agnostic**: point it at any local path that contains the
Drive folder structure (rclone mount, Google Drive Desktop folder, or a manually
unzipped download). It will:

  1. Walk every top-level subfolder ("feature folder") in the source.
  2. Slugify the folder name → kebab-case (e.g. "Floor Kiosk (Kavya)" → "floor-kiosk").
  3. Mirror its contents into raw/modules/<slug>/.
  4. Skip files that already exist with identical content (SHA-256 dedup).
  5. Create raw/modules/<slug>/ automatically if the feature is new.
  6. Print a per-feature report of new / updated / unchanged files.
  7. Suggest the next `ingest` commands for files that changed.

The script is **idempotent** — safe to re-run any time. It only copies what is
actually new or changed.

Examples
--------
  # Drive Desktop (typical macOS path)
  python scripts/sync_drive.py \
      --source "$HOME/Library/CloudStorage/GoogleDrive-<email>/My Drive/Conwo WorkInSync Docs"

  # rclone mount
  python scripts/sync_drive.py --source ~/mnt/gdrive/Conwo\\ WorkInSync\\ Docs

  # Manually downloaded + unzipped folder
  python scripts/sync_drive.py --source ~/Downloads/Conwo\\ WorkInSync\\ Docs

  # Preview without copying
  python scripts/sync_drive.py --source <path> --dry-run

  # Sync just one feature
  python scripts/sync_drive.py --source <path> --only sso
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
    # Remove (annotations) — typical owner tags
    cleaned = re.sub(r"\s*\([^)]*\)\s*", " ", name)
    cleaned = cleaned.lower().strip()
    cleaned = re.sub(r"[^a-z0-9]+", "-", cleaned)
    return cleaned.strip("-")


def file_sha256(path: Path, chunk_size: int = 65536) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()


def classify_skip(name: str) -> str | None:
    """Return a skip reason, or None if the file should be processed."""
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
) -> tuple[dict, list[str]]:
    """Sync one feature folder. Returns (counts, skipped_messages)."""
    counts = {"new": 0, "updated": 0, "unchanged": 0, "skipped": 0}
    skipped: list[str] = []

    for src in sorted(src_root.rglob("*")):
        if src.is_dir():
            continue
        rel = src.relative_to(src_root)

        reason = classify_skip(src.name)
        if reason:
            counts["skipped"] += 1
            if reason == "google-native":
                skipped.append(f"{feature_slug}/{rel}  (Google native — export to PDF first)")
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
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", required=True, help="Local path to the Drive root (folder containing all feature subfolders)")
    ap.add_argument("--dry-run", action="store_true", help="Report changes but do not copy files")
    ap.add_argument("--only", help="Sync only this feature slug (e.g. sso)")
    ap.add_argument("-v", "--verbose", action="store_true", help="Also print files that were unchanged")
    args = ap.parse_args()

    src_root = Path(args.source).expanduser().resolve()
    if not src_root.is_dir():
        print(f"ERROR: source is not a directory: {src_root}", file=sys.stderr)
        return 2

    print(f"Source : {src_root}")
    print(f"Target : {RAW_MODULES.relative_to(ROOT)}/")
    if args.dry_run:
        print("Mode   : DRY RUN (no files will be copied)")
    print()

    if not args.dry_run:
        RAW_MODULES.mkdir(parents=True, exist_ok=True)

    totals = {"new": 0, "updated": 0, "unchanged": 0, "skipped": 0}
    new_features: list[str] = []
    feature_reports: list[tuple[str, dict, bool]] = []
    all_skipped: list[str] = []

    for src_feature_dir in sorted(p for p in src_root.iterdir() if p.is_dir() and not p.name.startswith(".")):
        slug = slugify(src_feature_dir.name)
        if not slug:
            continue
        if args.only and slug != args.only:
            continue

        dst_dir = RAW_MODULES / slug
        is_new_feature = not dst_dir.exists()
        if is_new_feature:
            new_features.append(slug)
            if not args.dry_run:
                dst_dir.mkdir(parents=True, exist_ok=True)
                (dst_dir / ".gitkeep").touch()

        counts, skipped = sync_feature(src_feature_dir, dst_dir, slug, args.dry_run, args.verbose)
        all_skipped.extend(skipped)
        for k in totals:
            totals[k] += counts[k]
        feature_reports.append((slug, counts, is_new_feature))

    # ---------------- Report ----------------
    print()
    print("=" * 64)
    print("Drive Sync Report")
    print("=" * 64)

    if new_features:
        print(f"\nNew feature folders ({len(new_features)}):")
        for f in new_features:
            print(f"  + raw/modules/{f}/")

    print("\nPer-feature counts:")
    print(f"  {'feature':<32}  {'new':>4} {'upd':>4} {'unch':>5} {'skip':>4}")
    print(f"  {'-'*32}  {'----':>4} {'----':>4} {'-----':>5} {'----':>4}")
    for slug, counts, is_new in feature_reports:
        marker = "*" if is_new else " "
        print(f"  {marker} {slug:<30}  {counts['new']:>4} {counts['updated']:>4} "
              f"{counts['unchanged']:>5} {counts['skipped']:>4}")

    if all_skipped:
        print(f"\nSkipped ({len(all_skipped)} — show first 10):")
        for s in all_skipped[:10]:
            print(f"  - {s}")
        if len(all_skipped) > 10:
            print(f"  ... and {len(all_skipped) - 10} more")

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
            "totals": totals,
            "new_features": new_features,
            "features_with_changes": changed,
            "feature_counts": {slug: c for slug, c, _ in feature_reports},
        }
        MANIFEST_PATH.write_text(json.dumps(manifest, indent=2))
        print(f"\nManifest: {MANIFEST_PATH.relative_to(ROOT)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
