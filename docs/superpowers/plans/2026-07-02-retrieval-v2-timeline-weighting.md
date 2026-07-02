# Retrieval-V2 Timeline Weighting Implementation Plan (Phase 1 / spec §5)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Retrieval ranks candidates by recency + status, tags each ticket with a `bucket ∈ {latest, historical, stale_open}` label that flows all the way to the LLM context, and the confidence gate factors bucket-mix into its tier.

**Architecture:** A new single-purpose `backend/retrieval/v2/timeline.py` module owns bucket assignment, continuous timeline score (exp-decay × status-tier), and bucket-count aggregation. `hybrid.py` calls it post-fusion (one line). `gate.py` uses `_bucket_penalty` to downgrade confidence when the top 3 candidates are all historical or all stale-open, and surfaces `bucket_counts` in `diagnostics`. `shadow.py` logs bucket counts via `logging.info` so no schema change is needed for Phase 1.

**Tech Stack:** Python 3.11 + FastAPI + psycopg 3 + pgvector. Tests use pytest. No new dependencies.

## Global Constraints

- No schema change in Phase 1 — `retrieval_shadow_log` stays as-is; bucket counts logged via Python logger.
- No new dependencies — pure Python + existing `datetime`, `os`, `math`.
- Bucket string values: `"latest" | "historical" | "stale_open"` (snake_case) — see spec §5.4 note.
- CLAUDE.md §5 Step 2 thresholds (180d) are the source of truth for bucket boundaries. `assign_bucket`'s docstring cites §5 Step 2 verbatim.
- Env knobs prefixed `CONWO_RETRIEVAL_V2_TIMELINE_*`, defaults matching spec §5.1.
- All new callable surfaces have unit tests. Post-fusion scoring behavior verified via existing e2e integration test path.
- CLAUDE.md §1 rule: no `.py` edits while backend runs with `--reload`. Kill any local dev server before starting.

---

### Task 1: Timeline module — bucket assignment + timeline_score (pure functions)

**Files:**
- Create: `backend/retrieval/v2/timeline.py`
- Test: `tests/retrieval/v2/test_timeline.py` (create)

**Interfaces:**
- Consumes: nothing (pure functions over candidate dicts with `updated_at`, `resolved_at`, `status_category`, `comment_count` fields — all already present in `hybrid.py`'s SELECT).
- Produces:
  - `assign_bucket(row: dict) -> str` — returns `"latest" | "historical" | "stale_open"`
  - `timeline_score(row: dict) -> float` — returns value in `[0.05, 1.0]`
  - Module-level constants: `HALFLIFE_DAYS`, `LATEST_DAYS`, `STALE_DAYS`, `STATUS_WEIGHTS`

- [ ] **Step 1: Write the failing test file**

Create `tests/retrieval/v2/test_timeline.py`:

```python
"""Unit tests for the timeline module (pure functions over candidate dicts)."""
from datetime import datetime, timedelta, timezone


def _now():
    return datetime(2026, 7, 2, tzinfo=timezone.utc)


def _row(days_ago_updated=0, days_ago_resolved=None,
         status_category="done", comment_count=0):
    now = _now()
    updated = now - timedelta(days=days_ago_updated)
    resolved = now - timedelta(days=days_ago_resolved) if days_ago_resolved is not None else None
    return {
        "updated_at": updated,
        "resolved_at": resolved,
        "status_category": status_category,
        "comment_count": comment_count,
    }


def test_assign_bucket_within_180d_is_latest(monkeypatch):
    from backend.retrieval.v2 import timeline
    monkeypatch.setattr(timeline, "_utcnow", _now)
    assert timeline.assign_bucket(_row(days_ago_updated=30)) == "latest"


def test_assign_bucket_boundary_179d_is_latest(monkeypatch):
    from backend.retrieval.v2 import timeline
    monkeypatch.setattr(timeline, "_utcnow", _now)
    assert timeline.assign_bucket(_row(days_ago_updated=179)) == "latest"


def test_assign_bucket_boundary_181d_is_historical(monkeypatch):
    from backend.retrieval.v2 import timeline
    monkeypatch.setattr(timeline, "_utcnow", _now)
    r = _row(days_ago_updated=181, status_category="done", days_ago_resolved=181)
    assert timeline.assign_bucket(r) == "historical"


def test_assign_bucket_substantive_resolution_beats_age(monkeypatch):
    from backend.retrieval.v2 import timeline
    monkeypatch.setattr(timeline, "_utcnow", _now)
    r = _row(days_ago_updated=800, days_ago_resolved=800,
             status_category="done", comment_count=3)
    assert timeline.assign_bucket(r) == "latest"


def test_assign_bucket_stale_open(monkeypatch):
    from backend.retrieval.v2 import timeline
    monkeypatch.setattr(timeline, "_utcnow", _now)
    r = _row(days_ago_updated=300, status_category="new")
    assert timeline.assign_bucket(r) == "stale_open"


def test_timeline_score_monotonic_recent_higher(monkeypatch):
    from backend.retrieval.v2 import timeline
    monkeypatch.setattr(timeline, "_utcnow", _now)
    new = _row(days_ago_updated=1, days_ago_resolved=1, status_category="done")
    old = _row(days_ago_updated=365, days_ago_resolved=365, status_category="done")
    assert timeline.timeline_score(new) > timeline.timeline_score(old)


def test_timeline_score_status_tier_ordering(monkeypatch):
    from backend.retrieval.v2 import timeline
    monkeypatch.setattr(timeline, "_utcnow", _now)
    done_res = _row(days_ago_updated=30, days_ago_resolved=30, status_category="done")
    done     = _row(days_ago_updated=30, status_category="done")
    indet    = _row(days_ago_updated=30, status_category="indeterminate")
    new      = _row(days_ago_updated=30, status_category="new")
    assert (timeline.timeline_score(done_res) > timeline.timeline_score(done)
            > timeline.timeline_score(indet) > timeline.timeline_score(new))


def test_timeline_score_has_floor(monkeypatch):
    from backend.retrieval.v2 import timeline
    monkeypatch.setattr(timeline, "_utcnow", _now)
    ancient = _row(days_ago_updated=5000, status_category="new")
    assert timeline.timeline_score(ancient) >= 0.05
```

- [ ] **Step 2: Run tests, verify they all fail with import error**

Run: `venv/bin/pytest tests/retrieval/v2/test_timeline.py -v`
Expected: `ModuleNotFoundError: No module named 'backend.retrieval.v2.timeline'` (all 8 tests fail).

- [ ] **Step 3: Implement `backend/retrieval/v2/timeline.py`**

Create `backend/retrieval/v2/timeline.py`:

```python
"""Timeline weighting for retrieval-v2 candidates.

Encodes the CLAUDE.md §5 Step 2 rules ("Jira evidence is a timeline") that were
previously enforced only in the prompt layer. Retrieval now emits candidates
tagged with a categorical bucket AND ranked by a continuous timeline_score, so
`deep_system_prompt.py`'s Latest/Historical rendering has structured input
instead of raw dates it must re-derive from.

Env knobs (defaults per spec §5.1):
  CONWO_RETRIEVAL_V2_TIMELINE_HALFLIFE_DAYS   default 180.0
  CONWO_RETRIEVAL_V2_TIMELINE_LATEST_DAYS     default 180
  CONWO_RETRIEVAL_V2_TIMELINE_STALE_DAYS      default 180
"""
from __future__ import annotations
import math
import os
from datetime import datetime, timezone
from typing import Iterable

HALFLIFE_DAYS = float(os.getenv("CONWO_RETRIEVAL_V2_TIMELINE_HALFLIFE_DAYS", "180"))
LATEST_DAYS   = int(os.getenv("CONWO_RETRIEVAL_V2_TIMELINE_LATEST_DAYS",   "180"))
STALE_DAYS    = int(os.getenv("CONWO_RETRIEVAL_V2_TIMELINE_STALE_DAYS",    "180"))

STATUS_WEIGHTS = {
    "done_resolved": 1.00,   # status_category='done' AND resolved_at IS NOT NULL
    "done":          0.90,   # status_category='done' AND resolved_at IS NULL
    "indeterminate": 0.75,
    "new":           0.65,
}
_FLOOR = 0.05


def _utcnow() -> datetime:
    """Indirection so tests can freeze time via monkeypatch."""
    return datetime.now(timezone.utc)


def _days_since(dt) -> float | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return max((_utcnow() - dt).total_seconds() / 86400.0, 0.0)


def _status_tier(row: dict) -> str:
    sc = (row.get("status_category") or "").lower()
    if sc == "done" and row.get("resolved_at") is not None:
        return "done_resolved"
    if sc == "done":
        return "done"
    if sc == "indeterminate":
        return "indeterminate"
    return "new"


def assign_bucket(row: dict) -> str:
    """Return the bucket for one candidate row.

    CLAUDE.md §5 Step 2 semantics, verbatim:
      LATEST     — updated_at OR resolved_at within LATEST_DAYS
                   OR resolved with substantive content
                   (resolved_at IS NOT NULL AND comment_count >= 2)
      STALE_OPEN — status_category IN {new, indeterminate}
                   AND days_since(updated_at) > STALE_DAYS
      HISTORICAL — everything else
    """
    days_updated  = _days_since(row.get("updated_at"))
    days_resolved = _days_since(row.get("resolved_at"))
    # Substantive-resolution branch: resolved with 2+ comments overrides age.
    if row.get("resolved_at") is not None and (row.get("comment_count") or 0) >= 2:
        return "latest"
    if days_updated is not None and days_updated <= LATEST_DAYS:
        return "latest"
    if days_resolved is not None and days_resolved <= LATEST_DAYS:
        return "latest"
    sc = (row.get("status_category") or "").lower()
    if sc in {"new", "indeterminate"} and days_updated is not None and days_updated > STALE_DAYS:
        return "stale_open"
    return "historical"


def timeline_score(row: dict) -> float:
    """Continuous decay × status-tier multiplier, floored at 0.05."""
    days_updated  = _days_since(row.get("updated_at"))
    days_resolved = _days_since(row.get("resolved_at"))
    # Use the more recent of updated / resolved for decay.
    ages = [d for d in (days_updated, days_resolved) if d is not None]
    days = min(ages) if ages else float("inf")
    decay = 0.5 ** (days / HALFLIFE_DAYS) if math.isfinite(days) else 0.0
    status = STATUS_WEIGHTS[_status_tier(row)]
    return max(decay * status, _FLOOR)
```

- [ ] **Step 4: Run tests, verify all 8 pass**

Run: `venv/bin/pytest tests/retrieval/v2/test_timeline.py -v`
Expected: 8 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/retrieval/v2/timeline.py tests/retrieval/v2/test_timeline.py
git commit -m "feat(retrieval-v2): timeline module — bucket + score pure fns (spec §5.1)

New backend/retrieval/v2/timeline.py owns bucket assignment
(latest/historical/stale_open) per CLAUDE.md §5 Step 2 verbatim, plus a
continuous timeline_score (exp-decay × status-tier, floored at 0.05).

Pure functions only — mutation and sort come in the next commit."
```

---

### Task 2: apply_timeline + bucket_counts helpers

**Files:**
- Modify: `backend/retrieval/v2/timeline.py` (append two functions)
- Test: `tests/retrieval/v2/test_timeline.py` (append)

**Interfaces:**
- Consumes: `assign_bucket`, `timeline_score` from Task 1.
- Produces:
  - `apply_timeline(candidates: list[dict]) -> list[dict]` — mutates in-place, re-sorts by `fused_score * timeline_score` descending, returns the same list (chainable).
  - `bucket_counts(candidates: Iterable[dict]) -> dict[str, int]` — counts of `bucket` values across a list.

- [ ] **Step 1: Write failing tests**

Append to `tests/retrieval/v2/test_timeline.py`:

```python
def test_apply_timeline_attaches_bucket_and_score(monkeypatch):
    from backend.retrieval.v2 import timeline
    monkeypatch.setattr(timeline, "_utcnow", _now)
    cands = [
        {"key": "TS-1", "fused_score": 0.04, **_row(days_ago_updated=10)},
        {"key": "TS-2", "fused_score": 0.03, **_row(days_ago_updated=800)},
    ]
    out = timeline.apply_timeline(cands)
    assert out is cands  # in-place mutation; same list returned
    for c in out:
        assert "bucket" in c and "timeline_score" in c


def test_apply_timeline_sorts_by_fused_times_timeline(monkeypatch):
    from backend.retrieval.v2 import timeline
    monkeypatch.setattr(timeline, "_utcnow", _now)
    cands = [
        # Same fused_score, but TS-old is ancient.
        {"key": "TS-old",    "fused_score": 0.04, **_row(days_ago_updated=800)},
        {"key": "TS-recent", "fused_score": 0.04, **_row(days_ago_updated=1)},
    ]
    out = timeline.apply_timeline(cands)
    assert out[0]["key"] == "TS-recent"


def test_bucket_counts_aggregates_labels():
    from backend.retrieval.v2 import timeline
    cands = [
        {"bucket": "latest"},
        {"bucket": "latest"},
        {"bucket": "historical"},
        {"bucket": "stale_open"},
    ]
    counts = timeline.bucket_counts(cands)
    assert counts == {"latest": 2, "historical": 1, "stale_open": 1}
```

- [ ] **Step 2: Run tests, verify 3 new tests fail**

Run: `venv/bin/pytest tests/retrieval/v2/test_timeline.py::test_apply_timeline_attaches_bucket_and_score tests/retrieval/v2/test_timeline.py::test_apply_timeline_sorts_by_fused_times_timeline tests/retrieval/v2/test_timeline.py::test_bucket_counts_aggregates_labels -v`
Expected: 3 failed with `AttributeError: module 'backend.retrieval.v2.timeline' has no attribute 'apply_timeline'` / `bucket_counts`.

- [ ] **Step 3: Implement apply_timeline + bucket_counts**

Append to `backend/retrieval/v2/timeline.py`:

```python
def apply_timeline(candidates: list[dict]) -> list[dict]:
    """Attach `bucket` and `timeline_score` to each candidate (in-place) and
    re-sort by `fused_score * timeline_score` descending. Returns the same
    list (for chaining).
    """
    for c in candidates:
        c["bucket"] = assign_bucket(c)
        c["timeline_score"] = timeline_score(c)
    candidates.sort(
        key=lambda c: (c.get("fused_score") or 0.0) * c["timeline_score"],
        reverse=True,
    )
    return candidates


def bucket_counts(candidates: Iterable[dict]) -> dict[str, int]:
    """Return {latest: N, historical: N, stale_open: N} counts."""
    out = {"latest": 0, "historical": 0, "stale_open": 0}
    for c in candidates:
        b = c.get("bucket")
        if b in out:
            out[b] += 1
    return out
```

- [ ] **Step 4: Run all timeline tests, verify all 11 pass**

Run: `venv/bin/pytest tests/retrieval/v2/test_timeline.py -v`
Expected: 11 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/retrieval/v2/timeline.py tests/retrieval/v2/test_timeline.py
git commit -m "feat(retrieval-v2): apply_timeline + bucket_counts (spec §5.1)

apply_timeline mutates candidates in-place (adds bucket + timeline_score)
and re-sorts by fused_score × timeline_score. bucket_counts aggregates
labels for the gate's diagnostics dict."
```

---

### Task 3: Wire apply_timeline into hybrid_search

**Files:**
- Modify: `backend/retrieval/v2/hybrid.py:103-128` (import + one line inside `hybrid_search`)
- Test: `tests/retrieval/v2/test_hybrid.py` (extend)

**Interfaces:**
- Consumes: `timeline.apply_timeline` from Task 2.
- Produces: `hybrid_search` now returns candidates with `bucket` and `timeline_score` fields present on every row.

- [ ] **Step 1: Write failing test**

Append to `tests/retrieval/v2/test_hybrid.py`:

```python
def test_hybrid_search_result_carries_bucket_and_timeline_score(monkeypatch):
    """Verify hybrid_search wires timeline.apply_timeline into the return path.

    Uses monkeypatch to swap the SQL layer for a fake fusion result — we're
    testing the plumbing, not the SQL (SQL is covered by test_e2e_integration).
    """
    from datetime import datetime, timezone, timedelta
    from unittest.mock import MagicMock
    from backend.retrieval.v2 import hybrid

    now = datetime.now(timezone.utc)
    fake_rows = [
        {"key": "TS-recent", "fused_score": 0.03,
         "updated_at": now - timedelta(days=10), "resolved_at": None,
         "status_category": "indeterminate", "comment_count": 0},
        {"key": "TS-old", "fused_score": 0.03,
         "updated_at": now - timedelta(days=800), "resolved_at": None,
         "status_category": "indeterminate", "comment_count": 0},
    ]

    class FakeCur:
        def __init__(self): self._rows = None
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def execute(self, *a, **k): self._rows = list(fake_rows)
        def fetchall(self): return self._rows
    class FakeConn:
        def cursor(self, **k): return FakeCur()

    out = hybrid.hybrid_search(FakeConn(), ["q"], [[0.0]*768], {}, limit=10)
    keys = [r["key"] for r in out]
    for r in out:
        assert "bucket" in r
        assert "timeline_score" in r
    # Same fused_score, but recent should rank first.
    assert keys[0] == "TS-recent"
```

- [ ] **Step 2: Run test, verify it fails**

Run: `venv/bin/pytest tests/retrieval/v2/test_hybrid.py::test_hybrid_search_result_carries_bucket_and_timeline_score -v`
Expected: FAIL — assertion `"bucket" in r` fails because `hybrid_search` doesn't call `apply_timeline` yet.

- [ ] **Step 3: Wire apply_timeline into hybrid.py**

Edit `backend/retrieval/v2/hybrid.py`. Add import near the top (after line 12):

```python
from backend.retrieval.v2 import timeline
```

Edit `hybrid_search` — replace the final 3 lines (currently `fused = _rrf_fuse(per_sub)` / `return fused[:limit]`) with:

```python
    fused = _rrf_fuse(per_sub)
    fused = timeline.apply_timeline(fused)
    return fused[:limit]
```

- [ ] **Step 4: Run tests, verify hybrid tests pass**

Run: `venv/bin/pytest tests/retrieval/v2/test_hybrid.py -v`
Expected: all tests pass (existing 5 + new 1).

- [ ] **Step 5: Commit**

```bash
git add backend/retrieval/v2/hybrid.py tests/retrieval/v2/test_hybrid.py
git commit -m "feat(retrieval-v2): hybrid_search applies timeline weighting (spec §5.2)

One-line addition: fused = timeline.apply_timeline(fused) after RRF fusion.
Every returned candidate now carries bucket + timeline_score fields, and
the sort order reflects fused_score × timeline_score. SQL unchanged."
```

---

### Task 4: Gate bucket-mix penalty + diagnostics.bucket_counts

**Files:**
- Modify: `backend/retrieval/v2/gate.py:39-87`
- Test: `tests/retrieval/v2/test_gate.py` (extend)

**Interfaces:**
- Consumes: `timeline.bucket_counts` from Task 2.
- Produces:
  - `gate.apply()` output now downgrades confidence by 1 tier if top-3 candidates are all `"historical"`, and by 2 tiers if all `"stale_open"`.
  - `diagnostics["bucket_counts"]` populated on every non-abstain result.

- [ ] **Step 1: Write failing tests**

Append to `tests/retrieval/v2/test_gate.py`:

```python
def _scored_with_buckets(*items):
    """items: (key, functional_area, bucket, score)"""
    return [({"key": k, "summary": "s", "functional_area": fa, "bucket": b}, s)
            for k, fa, b, s in items]


def test_gate_downgrades_high_to_medium_when_top3_all_historical():
    from backend.retrieval.v2 import gate
    r = gate.apply(_scored_with_buckets(
        ("TS-1", "A", "historical", 0.9),
        ("TS-2", "A", "historical", 0.85),
        ("TS-3", "A", "historical", 0.8),
    ))
    assert r.confidence == "Medium"
    assert "historical" in r.message.lower()


def test_gate_downgrades_medium_to_low_when_top3_all_historical():
    from backend.retrieval.v2 import gate
    r = gate.apply(_scored_with_buckets(
        ("TS-1", "A", "historical", 0.65),
        ("TS-2", "A", "historical", 0.60),
        ("TS-3", "A", "historical", 0.55),
    ))
    assert r.confidence == "Low"


def test_gate_downgrades_high_to_low_when_top3_all_stale_open():
    from backend.retrieval.v2 import gate
    r = gate.apply(_scored_with_buckets(
        ("TS-1", "A", "stale_open", 0.9),
        ("TS-2", "A", "stale_open", 0.85),
        ("TS-3", "A", "stale_open", 0.8),
    ))
    assert r.confidence == "Low"
    assert "stale" in r.message.lower()


def test_gate_no_downgrade_when_top3_mixed_buckets():
    from backend.retrieval.v2 import gate
    r = gate.apply(_scored_with_buckets(
        ("TS-1", "A", "latest",     0.9),
        ("TS-2", "A", "historical", 0.85),
        ("TS-3", "A", "latest",     0.8),
    ))
    assert r.confidence == "High"


def test_gate_diagnostics_includes_bucket_counts():
    from backend.retrieval.v2 import gate
    r = gate.apply(_scored_with_buckets(
        ("TS-1", "A", "latest",     0.9),
        ("TS-2", "A", "historical", 0.85),
        ("TS-3", "A", "latest",     0.8),
    ))
    assert r.diagnostics["bucket_counts"] == {"latest": 2, "historical": 1, "stale_open": 0}
```

- [ ] **Step 2: Run tests, verify 5 new tests fail**

Run: `venv/bin/pytest tests/retrieval/v2/test_gate.py -v`
Expected: 5 new failures (confidence not downgraded, or bucket_counts absent). Existing 5 tests still pass.

- [ ] **Step 3: Update gate.py**

Edit `backend/retrieval/v2/gate.py`. After the existing `_top3_agree` helper (around line 37), add:

```python
_TIER_ORDER = ["Abstain", "Low", "Medium", "High"]


def _downgrade(conf: str, steps: int) -> str:
    """Move `conf` down `steps` tiers in _TIER_ORDER, clamped at Low."""
    if conf not in _TIER_ORDER:
        return conf
    idx = max(_TIER_ORDER.index(conf) - steps, _TIER_ORDER.index("Low"))
    return _TIER_ORDER[idx]


def _top3_bucket_penalty(scored: list) -> tuple[int, str]:
    """Return (tier_steps_to_downgrade, reason_word).

    - Top-3 all `stale_open`  → downgrade 2 tiers.
    - Top-3 all `historical`  → downgrade 1 tier.
    - Otherwise              → downgrade 0.
    """
    if len(scored) < 3:
        return 0, ""
    top_buckets = {c.get("bucket") for c, _ in scored[:3]}
    if top_buckets == {"stale_open"}:
        return 2, "stale-open"
    if top_buckets == {"historical"}:
        return 1, "historical"
    return 0, ""
```

Then, still in `gate.py`, edit `apply()`:

1. Replace the two `diag = {...}` blocks with one that also includes `bucket_counts`. Add import at top:

```python
from backend.retrieval.v2 import timeline
```

2. Rebuild the `diag` dict:

```python
    top_score = scored[0][1]
    diag = {
        "top_score": top_score,
        "candidate_count": len(scored),
        "bucket_counts": timeline.bucket_counts(c for c, _ in scored),
    }
```

3. At the end of `apply()`, just before every `return RetrievalResult(...)` for the non-abstain paths, wrap with penalty logic. The cleanest structure is to compute the result first, then downgrade:

Replace the block from `if len(scored) == 1:` down through the end of the function with:

```python
    # Compute base result.
    if len(scored) == 1:
        result = RetrievalResult(
            tickets=tickets, confidence="Low", abstain=False,
            message="single-source evidence — only one ticket supports this.",
            diagnostics=diag,
        )
    elif top_score >= high_t:
        if _top3_agree(scored):
            result = RetrievalResult(tickets=tickets, confidence="High", abstain=False,
                                     message="strong, agreeing evidence", diagnostics=diag)
        else:
            result = RetrievalResult(tickets=tickets, confidence="Medium", abstain=False,
                                     message="strong evidence but tickets do not fully agree",
                                     diagnostics=diag)
    else:
        # abstain_t <= top_score < high_t
        if _top3_agree(scored):
            result = RetrievalResult(tickets=tickets, confidence="Medium", abstain=False,
                                     message="moderate, agreeing evidence", diagnostics=diag)
        else:
            result = RetrievalResult(tickets=tickets, confidence="Low", abstain=False,
                                     message="moderate evidence, tickets disagree", diagnostics=diag)

    # Bucket-mix penalty (CLAUDE.md §5 Step 2: HISTORICAL / STALE-OPEN evidence
    # is weak; if top-3 are all in one of those buckets, downgrade confidence).
    steps, reason = _top3_bucket_penalty(scored)
    if steps:
        new_conf = _downgrade(result.confidence, steps)
        if new_conf != result.confidence:
            result.confidence = new_conf
            result.message += f" (downgraded: top candidates are {reason})"
    return result
```

- [ ] **Step 4: Run tests, verify all gate tests pass**

Run: `venv/bin/pytest tests/retrieval/v2/test_gate.py -v`
Expected: 10 passed (5 existing + 5 new). If any existing test fails, check that the `_scored` helper in the existing tests still works — it doesn't set `bucket`, and `_top3_bucket_penalty` requires bucket to be a specific set value; missing bucket → `top_buckets == {None}` → no downgrade. Verify this by re-reading existing test cases.

- [ ] **Step 5: Commit**

```bash
git add backend/retrieval/v2/gate.py tests/retrieval/v2/test_gate.py
git commit -m "feat(retrieval-v2): gate bucket-mix penalty + bucket_counts diag (spec §5.3)

Top-3 all historical → downgrade 1 tier.
Top-3 all stale_open → downgrade 2 tiers (clamped at Low).
Mixed buckets → no penalty (existing behavior preserved).
diagnostics.bucket_counts populated on every non-abstain result."
```

---

### Task 5: Shadow logger emits bucket_counts

**Files:**
- Modify: `backend/retrieval/v2/shadow.py`
- Test: `tests/retrieval/v2/test_shadow.py` (create)

**Interfaces:**
- Consumes: `RetrievalResult.diagnostics["bucket_counts"]` from Task 4.
- Produces: `shadow.log(...)` now emits a `logger.info(...)` line containing `bucket_counts` on every shadow log call, in addition to the existing SQL insert. No schema change.

- [ ] **Step 1: Write failing test**

Create `tests/retrieval/v2/test_shadow.py`:

```python
"""shadow.log emits bucket_counts via Python logger (no schema change in Phase 1)."""
from unittest.mock import MagicMock, patch
from dataclasses import dataclass


@dataclass
class _FakeResult:
    tickets: list
    confidence: str = "Medium"
    diagnostics: dict = None


def test_shadow_log_emits_bucket_counts_via_logger(caplog):
    import logging
    from backend.retrieval.v2 import shadow

    result = _FakeResult(
        tickets=[{"key": "TS-1", "reranker_score": 0.8}],
        diagnostics={"bucket_counts": {"latest": 1, "historical": 0, "stale_open": 0}},
    )

    with patch("backend.retrieval.v2.shadow.db") as mock_db:
        # Make the SQL insert into a no-op (we only care about the logger call).
        mock_db.connection.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = MagicMock()
        with caplog.at_level(logging.INFO, logger="backend.retrieval.v2.shadow"):
            shadow.log(trace_id="t1", question="q",
                       v1_keys=["TS-9"], v2_result=result,
                       v2_latency_ms=100, served_v2=False)

    log_text = " ".join(r.getMessage() for r in caplog.records)
    assert "bucket_counts" in log_text
    assert "'latest': 1" in log_text or '"latest": 1' in log_text


def test_shadow_log_no_bucket_counts_when_diagnostics_missing(caplog):
    """Gracefully handle results with no diagnostics (defensive)."""
    import logging
    from backend.retrieval.v2 import shadow

    result = _FakeResult(tickets=[], diagnostics=None)

    with patch("backend.retrieval.v2.shadow.db") as mock_db:
        mock_db.connection.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = MagicMock()
        with caplog.at_level(logging.INFO, logger="backend.retrieval.v2.shadow"):
            shadow.log(trace_id="t1", question="q",
                       v1_keys=[], v2_result=result,
                       v2_latency_ms=0, served_v2=False)

    # Should not raise, and should not include the string 'bucket_counts'.
    log_text = " ".join(r.getMessage() for r in caplog.records)
    assert "bucket_counts" not in log_text
```

- [ ] **Step 2: Run tests, verify they fail**

Run: `venv/bin/pytest tests/retrieval/v2/test_shadow.py -v`
Expected: `test_shadow_log_emits_bucket_counts_via_logger` fails — no logger call in current `shadow.log`. `test_shadow_log_no_bucket_counts_when_diagnostics_missing` may pass if code is defensive; otherwise fails when we add naive access.

- [ ] **Step 3: Update shadow.py to emit bucket_counts**

Edit `backend/retrieval/v2/shadow.py`. Full replacement:

```python
"""Write retrieval-v2 results to retrieval_shadow_log for offline comparison.

Phase 1 (2026-07-02): also emits bucket_counts via logger.info so timeline
weighting can be verified without a schema change to retrieval_shadow_log.
Grep production logs for 'shadow.bucket_counts' to aggregate.
"""
from __future__ import annotations
import logging
from backend import db

log_ = logging.getLogger(__name__)

_INSERT = """
    INSERT INTO retrieval_shadow_log
        (trace_id, question, v1_keys, v2_keys, v2_scores, v2_confidence,
         v2_latency_ms, served_v2)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
"""

def log(*, trace_id: str | None, question: str,
        v1_keys: list[str], v2_result, v2_latency_ms: int,
        served_v2: bool) -> None:
    v2_keys = [t.get("key") for t in (v2_result.tickets or [])]
    v2_scores = [float(t.get("reranker_score") or 0.0) for t in (v2_result.tickets or [])]

    # Phase 1 bucket_counts logging — grep-key: 'shadow.bucket_counts'.
    diag = getattr(v2_result, "diagnostics", None) or {}
    bc = diag.get("bucket_counts")
    if bc is not None:
        log_.info("shadow.bucket_counts trace=%s served_v2=%s bucket_counts=%r",
                  trace_id, served_v2, bc)

    try:
        with db.connection() as conn, conn.cursor() as cur:
            cur.execute(_INSERT, (
                trace_id, question, v1_keys, v2_keys, v2_scores,
                v2_result.confidence, v2_latency_ms, served_v2,
            ))
            conn.commit()
    except Exception:
        # fail-open: shadow logging never breaks production retrieval
        pass
```

- [ ] **Step 4: Run tests, verify shadow tests pass**

Run: `venv/bin/pytest tests/retrieval/v2/test_shadow.py -v`
Expected: 2 passed.

- [ ] **Step 5: Full retrieval-v2 test sweep**

Run: `venv/bin/pytest tests/retrieval/v2/ -v --ignore=tests/retrieval/v2/test_e2e_integration.py`
Expected: all pass. If e2e integration test also runs (opt-in Postgres fixture), it should also pass — nothing in the SQL layer changed.

- [ ] **Step 6: Commit**

```bash
git add backend/retrieval/v2/shadow.py tests/retrieval/v2/test_shadow.py
git commit -m "feat(retrieval-v2): shadow logs bucket_counts via logger (spec §5.6)

log_.info(\"shadow.bucket_counts ...\") emitted alongside existing SQL
insert. No schema change — verification is via log aggregation (grep
'shadow.bucket_counts'). Phase 2 may promote to a table column."
```

---

### Task 6: Push branch, open PR

**Files:** none (git + Bitbucket).

- [ ] **Step 1: Verify clean working tree + commits stacked correctly**

Run: `git status && git log --oneline main..HEAD`
Expected: clean tree; 5 new commits (Tasks 1–5) on top of the current branch's Round 3 reranker-swap commit.

- [ ] **Step 2: Push branch**

If reusing the current branch `fix/query-handler-threadpool`, decide whether to (a) fold these commits into the same PR, or (b) create a new branch. Recommended: **new branch** — the reranker swap and timeline weighting are logically separate changes and should be reviewed independently.

```bash
git checkout -b feat/retrieval-v2-timeline
git push -u bitbucket feat/retrieval-v2-timeline
```

- [ ] **Step 3: Open PR #38 in Bitbucket UI**

Title: `feat(retrieval-v2): timeline weighting — bucket + timeline_score, gate penalty`

Body:
```
Closes spec §5 (Phase 1 of docs/superpowers/specs/2026-07-02-retrieval-v2-timeline-and-comments-design.md).

Bridges the gap between deep_system_prompt.py's Latest/Historical
narrative template and hybrid.py's timeline-blind RRF. Every candidate
now carries bucket ∈ {latest, historical, stale_open} + a continuous
timeline_score; gate.py downgrades confidence when the top 3 are all
historical or all stale_open.

No schema change. Shadow logging via Python logger.

Tests: 21 new (11 timeline + 5 gate + 1 hybrid + 2 shadow + adjustments).
```

- [ ] **Step 4: Monitor CI, respond to review comments**

Iterate until CI green + reviewer LGTM. Merge via Bitbucket UI (squash-merge to match project convention).

---

## Post-merge

- Enable `CONWO_RETRIEVAL_V2=shadow` on prod (if not already). Wait 1–2 days.
- Grep production logs for `shadow.bucket_counts`. Sanity-check: for queries where v1 returned a known-correct answer, verify v2's top-3 include that ticket AND that its bucket is `latest` when appropriate.
- If shadow signal is healthy, proceed to Phase 2 plan (`2026-07-02-retrieval-v2-comments-embedding.md`).
- If signal is bad (e.g., relevant HISTORICAL evidence is being suppressed too aggressively), tune `CONWO_RETRIEVAL_V2_TIMELINE_HALFLIFE_DAYS` upward before Phase 2.
