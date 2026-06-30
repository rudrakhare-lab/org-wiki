"""Tests for backend.wiki_seed.sync_wiki_baseline — the deploy-time wiki merge."""
from pathlib import Path

from backend.wiki_seed import sync_wiki_baseline, STAMP_NAME


def _write(d: Path, rel: str, content: str) -> None:
    p = d / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


def test_seeds_empty_volume(tmp_path):
    seed, vol = tmp_path / "seed", tmp_path / "vol"
    _write(seed, "modules/a.md", "A")
    _write(seed, "history/h.md", "H")
    r = sync_wiki_baseline(seed, vol)
    assert r["action"] == "seeded" and r["pages"] == 2
    assert (vol / "modules/a.md").read_text() == "A"
    assert (vol / STAMP_NAME).exists()


def test_merge_adds_updates_and_preserves_volume_only(tmp_path):
    """The current-prod case: populated volume, NO stamp → merge up to the new baseline."""
    seed, vol = tmp_path / "seed", tmp_path / "vol"
    # volume already populated (old), no stamp — exactly today's stale PVC
    _write(vol, "modules/a.md", "OLD-A")          # exists in both → must UPDATE
    _write(vol, "answers/local.md", "PROD-ONLY")  # volume-only → must be PRESERVED
    # new baked baseline: updated a.md + a brand-new page
    _write(seed, "modules/a.md", "NEW-A")
    _write(seed, "history/h.md", "H")
    r = sync_wiki_baseline(seed, vol)
    assert r["action"] == "merged"
    assert (vol / "modules/a.md").read_text() == "NEW-A"          # updated to git version
    assert (vol / "history/h.md").read_text() == "H"             # new page added
    assert (vol / "answers/local.md").read_text() == "PROD-ONLY"  # volume-only NOT deleted


def test_skip_when_unchanged_and_volume_only_survives(tmp_path):
    seed, vol = tmp_path / "seed", tmp_path / "vol"
    _write(seed, "modules/a.md", "A")
    assert sync_wiki_baseline(seed, vol)["action"] == "seeded"
    # an ordinary restart with the SAME baked content → no-op; a later volume edit survives
    _write(vol, "answers/local.md", "PROD")
    r = sync_wiki_baseline(seed, vol)
    assert r["action"] == "skip"
    assert (vol / "answers/local.md").read_text() == "PROD"


def test_remerges_when_seed_content_changes(tmp_path):
    seed, vol = tmp_path / "seed", tmp_path / "vol"
    _write(seed, "modules/a.md", "A")
    sync_wiki_baseline(seed, vol)                         # seeded
    assert sync_wiki_baseline(seed, vol)["action"] == "skip"
    _write(seed, "modules/a.md", "A2")                    # a new deploy changes the baked wiki
    r = sync_wiki_baseline(seed, vol)
    assert r["action"] == "merged"
    assert (vol / "modules/a.md").read_text() == "A2"


def test_noop_local_when_same_path(tmp_path):
    d = tmp_path / "wiki"
    _write(d, "a.md", "A")
    assert sync_wiki_baseline(d, d)["action"] == "noop-local"


def test_no_seed_dir(tmp_path):
    assert sync_wiki_baseline(tmp_path / "missing", tmp_path / "vol")["action"] == "no-seed"
