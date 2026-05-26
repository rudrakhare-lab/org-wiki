#!/usr/bin/env python3
"""Track A stress harness — Sub-pass D Part B.2 + B.3.

Two stress scenarios:
  1. Lock contention: N threads race to apply edits to the same page.
     Expected outcome: exactly 1 succeeds, N-1 get stale_proposal.
     Tested at N = 2, 5, 10, 20.

  2. Rollback robustness: a 5-file multi_edit where one write is
     force-failed. Verify all 5 files end up at pre-apply content.
     Run 100 iterations to catch flakiness.

Both scenarios use a temp wiki — the real wiki/ is never touched.
Not part of the regular test suite. Run on demand:

    venv/bin/python tests/manual/track_a_stress.py
"""
from __future__ import annotations

import importlib
import sys
import tempfile
import threading
import time
import traceback
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))


def setup_temp_wiki() -> dict:
    """Build an isolated wiki under tmpfs and re-point all relevant modules
    at it. Returns a dict with the modules and paths so callers can use them."""
    tmp = Path(tempfile.mkdtemp(prefix="track_a_stress_"))
    fake_wiki = tmp / "wiki"
    fake_wiki.mkdir()
    fake_fb = tmp / "feedback"
    fake_fb.mkdir()
    from backend import config
    config.WIKI_DIR = fake_wiki
    config.FEEDBACK_DIR = fake_fb

    import backend.wiki_proposals as wp
    importlib.reload(wp)
    wp.PROPOSALS_FILE = fake_fb / "wiki_proposals.jsonl"
    wp.FEEDBACK_DIR = fake_fb

    import backend.wiki_apply as wa
    importlib.reload(wa)
    wa.WIKI_DIR = fake_wiki

    import backend.admin_api as adm
    importlib.reload(adm)

    # Silence index rebuild
    import backend.wiki_retriever as wr
    wr.rebuild_index = lambda: None

    return {"tmp": tmp, "wiki": fake_wiki, "fb": fake_fb, "wp": wp, "wa": wa, "adm": adm}


def banner(s: str) -> None:
    print("\n" + "═" * 72)
    print(s)
    print("═" * 72)


# ──────────────────────────────────────────────────────────────────────────────
# B.2 — Lock contention at varying concurrency
# ──────────────────────────────────────────────────────────────────────────────

def run_lock_contention(n_threads: int, ctx: dict) -> dict:
    """N threads each try to apply edits that target the SAME old_string
    on the same page. Only one can win — once the winner writes, the
    old_string is no longer in the file, so the apply layer's re-validation
    under flock returns stale_proposal for the losers.

    This is what stresses the lock + re-validation correctness path. (An
    earlier version of this test used per-thread unique old_strings, which
    proved nothing — all writes succeeded because they targeted different
    content. Real contention requires shared target content.)
    """
    page = ctx["wiki"] / "concepts" / "contended.md"
    page.parent.mkdir(parents=True, exist_ok=True)
    # All threads compete to replace the same unique marker line
    page.write_text("---\ntype: concept\n---\n\nCONTENDED_LINE_v1\n")

    # Each proposal does the same replacement (CONTENDED_LINE_v1 → THREAD_i_WON).
    proposal_ids: list[str] = []
    for i in range(n_threads):
        pid = ctx["wp"].create_edit_proposal(
            page_path="concepts/contended.md",
            old_string="CONTENDED_LINE_v1",
            new_string=f"THREAD_{i}_WON",
            submitter_email=f"agent{i}",
        )
        proposal_ids.append(pid)

    barrier = threading.Barrier(n_threads)
    results: dict[int, dict] = {}
    latencies: dict[int, float] = {}
    exceptions: list[str] = []

    def worker(idx: int, pid: str):
        try:
            barrier.wait()  # synchronize start
            t0 = time.monotonic()
            r = ctx["adm"].apply_wiki_proposal(pid)
            latencies[idx] = time.monotonic() - t0
            results[idx] = r
        except Exception:
            exceptions.append(f"thread {idx}: {traceback.format_exc()}")

    threads = [threading.Thread(target=worker, args=(i, pid)) for i, pid in enumerate(proposal_ids)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=15)

    # Tally
    success_count = sum(1 for r in results.values() if r.get("success") and r.get("code") != "already_applied")
    stale_count = sum(1 for r in results.values() if r.get("code") == "stale_proposal")
    other_codes: dict[str, int] = {}
    for r in results.values():
        code = r.get("code", "ok") or "ok"
        if code not in ("stale_proposal",) and not r.get("success"):
            other_codes[code] = other_codes.get(code, 0) + 1

    return {
        "n_threads": n_threads,
        "success_count": success_count,
        "stale_count": stale_count,
        "other_codes": other_codes,
        "exceptions": exceptions,
        "max_latency_s": max(latencies.values()) if latencies else 0.0,
        "min_latency_s": min(latencies.values()) if latencies else 0.0,
    }


banner("B.2 — Lock contention stress")
print("  N threads → expected: 1 success, N-1 stale_proposal, 0 exceptions")
for n in (2, 5, 10, 20):
    ctx = setup_temp_wiki()
    summary = run_lock_contention(n, ctx)
    status = "✅" if (
        summary["success_count"] == 1
        and summary["stale_count"] == n - 1
        and not summary["exceptions"]
        and not summary["other_codes"]
    ) else "❌"
    print(
        f"  N={n:3d} {status}: success={summary['success_count']} "
        f"stale={summary['stale_count']} other={summary['other_codes']} "
        f"exceptions={len(summary['exceptions'])} "
        f"latency=[{summary['min_latency_s']*1000:.1f}ms..{summary['max_latency_s']*1000:.1f}ms]"
    )
    if summary["exceptions"]:
        for exc in summary["exceptions"][:2]:
            print(f"    EXC: {exc[:200]}")


# ──────────────────────────────────────────────────────────────────────────────
# B.3 — Rollback robustness: 5-file multi_edit, mid-stream IO error
# ──────────────────────────────────────────────────────────────────────────────

def run_rollback_iteration(ctx: dict, fail_at_idx: int = 2) -> tuple[bool, str]:
    """One iteration: build a 5-file multi_edit, mock write_text to fail
    on the (fail_at_idx)th write. Verify all 5 files end at pre-apply content.

    Returns (clean: bool, detail: str).
    """
    # Seed 5 files with known content
    files: list[tuple[str, Path, str]] = []
    for i in range(5):
        rel = f"modules/stress_{i}.md"
        target = ctx["wiki"] / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        content = f"---\ntype: module\n---\n\nseed_{i}\n"
        target.write_text(content)
        files.append((rel, target, content))

    edits = [
        {"page_path": rel, "old_string": f"seed_{i}", "new_string": f"NEW_{i}"}
        for i, (rel, _, _) in enumerate(files)
    ]
    pid = ctx["wp"].create_multi_edit_proposal(
        edits=edits,
        submitter_email="agent",
        reason="rollback stress",
    )

    # Patch write_text to fail at the chosen file. Track which write is failing.
    # CRITICAL: must compare RESOLVED paths. `files[fail_at_idx][1]` is
    # `ctx["wiki"] / rel` (e.g. /var/folders/...) while apply_multi_edit
    # internally uses `(WIKI_DIR / rel).resolve()` (e.g. /private/var/folders/...
    # on macOS). Without .resolve() the equality check silently never matches
    # and the patch never fires — caught by the first run of this harness.
    original_write = Path.write_text
    state = {"writes_seen": 0, "failed_yet": False}
    fail_target = files[fail_at_idx][1].resolve()

    def patched_write(self, *args, **kwargs):
        if self.resolve() == fail_target and not state["failed_yet"]:
            state["failed_yet"] = True
            raise OSError(f"simulated disk full on {self.name}")
        return original_write(self, *args, **kwargs)

    with patch.object(Path, "write_text", patched_write):
        result = ctx["adm"].apply_wiki_proposal(pid)

    if result.get("success"):
        return False, "apply unexpectedly succeeded"
    if result.get("rollback_status") != "clean":
        return False, f"rollback_status={result.get('rollback_status')}"

    # Verify every file is at pre-apply content
    for rel, target, expected in files:
        actual = target.read_text()
        if actual != expected:
            return False, f"{rel}: content differs from pre-apply\n  expected: {expected!r}\n  actual: {actual!r}"

    return True, "all 5 files restored to pre-apply content"


banner("B.3 — Multi-edit rollback robustness (100 iterations)")
clean_count = 0
failed_count = 0
failure_samples: list[str] = []
for i in range(100):
    ctx = setup_temp_wiki()
    ok, detail = run_rollback_iteration(ctx, fail_at_idx=2)
    if ok:
        clean_count += 1
    else:
        failed_count += 1
        if len(failure_samples) < 3:
            failure_samples.append(f"iter {i}: {detail}")

print(f"  100 iterations of 5-file multi_edit with forced IO fail on file [2]:")
print(f"    clean rollbacks : {clean_count} / 100")
print(f"    failed rollbacks: {failed_count} / 100")
if failure_samples:
    print(f"    sample failures:")
    for s in failure_samples:
        print(f"      {s}")
status_b3 = "✅" if failed_count == 0 else "❌"
print(f"  {status_b3} rollback {'is robust' if failed_count == 0 else 'has flakiness'}")


print("\n" + "═" * 72)
print("Track A stress harness complete.")
print("═" * 72)
