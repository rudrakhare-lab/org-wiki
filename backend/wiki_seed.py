"""Wiki baseline sync — keep the runtime wiki volume in step with the image's
baked baseline, exactly once per deploy.

Prod serves the wiki off a mounted PVC (CONWO_DATA_DIR=/app/data → WIKI_DIR=
/app/data/wiki) that persists across deploys. The image bakes the current wiki/
at SEED_WIKI_DIR. The old rule — "seed only if the volume is empty" — meant a new
image's wiki never reached an already-populated volume, so ingested pages baked
into a new image never showed up in prod.

This module instead MERGES the baked baseline onto the volume whenever the baked
content changes, detected via a content hash stamped on the volume. Effect:
  - first boot (empty volume)            → full seed
  - new image with changed wiki content  → merge once, then restamp
  - ordinary restart (same content)      → no-op

Merge semantics (shutil.copytree dirs_exist_ok=True): ADDS new files, OVERWRITES
changed files with the baked (git) version, and NEVER deletes volume-only files
(e.g. runtime-authored content). Fail-open is the caller's responsibility.
"""
from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

# Dotfile (not *.md), so wiki_retriever / graph *.md scans ignore it.
STAMP_NAME = ".wiki_seed_version"


def seed_digest(seed_dir: Path) -> str:
    """Stable content hash of the baked wiki: sorted (relpath, sha256(bytes))."""
    h = hashlib.sha256()
    for p in sorted(seed_dir.rglob("*")):
        if p.is_file():
            h.update(p.relative_to(seed_dir).as_posix().encode("utf-8"))
            h.update(b"\0")
            h.update(hashlib.sha256(p.read_bytes()).digest())
    return h.hexdigest()


def sync_wiki_baseline(seed_dir: Path, volume_dir: Path) -> dict:
    """Merge the baked wiki baseline onto the runtime volume, once per content change.

    Returns a small status dict for logging. Actions:
      noop-local : seed_dir == volume_dir (local dev) — nothing to do
      no-seed    : no baked baseline present
      seeded     : volume had no pages — full copy (first boot)
      merged     : baked content changed since last sync — overlay + restamp
      skip       : volume already in sync with this baked content
    """
    if seed_dir.resolve() == volume_dir.resolve():
        return {"action": "noop-local"}
    if not seed_dir.is_dir():
        return {"action": "no-seed", "seed_dir": str(seed_dir)}

    digest = seed_digest(seed_dir)
    stamp = volume_dir / STAMP_NAME
    has_pages = volume_dir.exists() and any(volume_dir.rglob("*.md"))

    if has_pages:
        prev = stamp.read_text(encoding="utf-8").strip() if stamp.exists() else ""
        if prev == digest:
            return {"action": "skip", "reason": "up-to-date"}
        action = "merged"
    else:
        action = "seeded"

    volume_dir.mkdir(parents=True, exist_ok=True)
    # Overlay: adds new + overwrites changed; never deletes volume-only files.
    shutil.copytree(seed_dir, volume_dir, dirs_exist_ok=True)
    stamp.write_text(digest, encoding="utf-8")
    pages = sum(1 for _ in volume_dir.rglob("*.md"))
    return {"action": action, "pages": pages}


def sync_file(src: Path, dst: Path) -> dict:
    """Copy a single git-owned file from the image baseline onto the runtime volume
    when it is missing or differs. No-op when src == dst (local dev) or src absent.

    Used for CLAUDE.md: the answering agent reads it from the PVC (_BASE/CLAUDE.md),
    but the wiki sync only covers wiki/ — so prompt/schema edits to CLAUDE.md never
    reached prod. CLAUDE.md is git-owned (no runtime writes), so overwrite-from-image
    is correct. Actions: noop-local | no-source | skip | created | updated.
    """
    if src.resolve() == dst.resolve():
        return {"action": "noop-local"}
    if not src.is_file():
        return {"action": "no-source", "src": str(src)}
    new = src.read_bytes()
    if dst.exists() and dst.read_bytes() == new:
        return {"action": "skip"}
    action = "updated" if dst.exists() else "created"
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(new)
    return {"action": action}
