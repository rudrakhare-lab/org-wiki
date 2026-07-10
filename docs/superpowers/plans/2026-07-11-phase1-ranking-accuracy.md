# Phase 1 — Ranking Accuracy (blend + smart rerank window) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Jira v2 final ranking + confidence use the blend of reranker + recency + fusion signals (not the bare reranker score), and let the reranker judge on the query-relevant slice of a ticket instead of a truncated head — with a Jira golden-eval gate proving no regression.

**Architecture:** Two code changes in the shared `backend/retrieval/v2/` layer — `gate.py` (blend, Jira-only) and `rerank.py` (smart window, shared by Jira + wiki). Both are guarded by env kill-switches defaulting to the new behavior and read at call-time so the eval harness can toggle them live. A new Jira golden-eval harness (mirroring the existing wiki one) is the accuracy gate; the wiki golden set is populated so the shared-rerank change is guarded on the wiki side too.

**Tech Stack:** Python 3, psycopg (Postgres/pgvector), sentence-transformers CrossEncoder (ms-marco-MiniLM-L-6-v2), pytest.

## Global Constraints

- **Accuracy over latency** — no change may trade correctness for speed; no query-time timeout is in scope.
- **Every ranking change is env-kill-switchable, defaulting to the new behavior**, and the flag is read at call-time (not import-time module constant) so the eval harness can toggle it in-process. Exact flags: `CONWO_RANK_BLEND` (default `on`), `CONWO_RERANK_SMART_WINDOW` (default `on`), `CONWO_RERANK_MAX_LENGTH` (default `512`). Blend weights: `CONWO_RANK_W_RERANK` (0.5), `CONWO_RANK_W_TIMELINE` (0.3), `CONWO_RANK_W_FUSED` (0.2), `CONWO_RANK_BLEND_HIGH_THRESHOLD` (0.55).
- **Abstain safety net stays on the calibrated reranker score** (`CONWO_RETRIEVAL_V2_ABSTAIN_THRESHOLD`, default 0.5). The blend changes ordering + High/Medium/Low tiering, NOT the abstain decision.
- **Operational safety (CLAUDE.md §1):** never write a `.py` in the repo tree while the backend runs with `--reload`; if unsure, stop the backend first. Throwaway scratch goes in `/tmp/`.
- **DRY / YAGNI / TDD / frequent commits.** Reuse the wiki harness's pure metric functions — do not re-implement recall@k / MRR.
- **The `_doc_text` field contract is shared:** any change to reranker input must keep working for both a Jira ticket dict (`summary`, `description_text`, `comments_text`) and a wiki chunk shaped by `wiki_v2.pipeline._to_rerank_shape` (same three keys). Never assume Jira-only fields (`key`, `functional_area`) inside `_doc_text`.

---

### Task 1: Jira golden set + seed helper

**Files:**
- Create: `docs/eval/jira-golden.jsonl`
- Create: `scripts/seed_jira_golden.py`
- Test: `tests/scripts/test_seed_jira_golden.py`

**Interfaces:**
- Produces: `docs/eval/jira-golden.jsonl` — one JSON object per line, schema `{"question": str, "expected_keys": [str, ...]}`. Consumed by Task 2's harness.
- Produces: `seed_jira_golden.build_rows(tickets: list[dict]) -> list[dict]` — pure function turning ticket dicts (`{"key","summary","links_json"}`) into golden rows; unit-tested with zero I/O.

- [ ] **Step 1: Write the failing test for the pure row-builder**

```python
# tests/scripts/test_seed_jira_golden.py
import json
from scripts.seed_jira_golden import build_rows


def test_build_rows_self_referential_with_links():
    tickets = [
        {"key": "TS-100", "summary": "Kiosk OTP fails before registration",
         "links_json": json.dumps([{"key": "TS-101"}, {"key": "TS-102"}])},
        {"key": "PB-200", "summary": "Meeting room auto-release timeout", "links_json": None},
    ]
    rows = build_rows(tickets)
    assert rows[0] == {
        "question": "Kiosk OTP fails before registration",
        "expected_keys": ["TS-100", "TS-101", "TS-102"],
    }
    assert rows[1] == {"question": "Meeting room auto-release timeout",
                       "expected_keys": ["PB-200"]}


def test_build_rows_skips_empty_summary():
    assert build_rows([{"key": "X-1", "summary": "  ", "links_json": None}]) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv/bin/pytest tests/scripts/test_seed_jira_golden.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.seed_jira_golden'`

- [ ] **Step 3: Implement `scripts/seed_jira_golden.py`**

```python
#!/usr/bin/env python3
"""Seed a STARTER Jira golden set for the ranking eval gate.

Samples resolved, substantive tickets from the DB and emits self-referential
golden rows: question = the ticket summary, expected_keys = that ticket plus
its directly-linked tickets. This is a legitimate ranking-regression signal
(does the pipeline surface the right ticket + its neighbours in top-k?) and is
generated without manual labelling. Hand-curated rows may be appended to the
output file afterwards; re-running with --append preserves them.

Usage:
    venv/bin/python scripts/seed_jira_golden.py --limit 25 \
        --out docs/eval/jira-golden.jsonl
"""
from __future__ import annotations
import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "docs" / "eval" / "jira-golden.jsonl"

SAMPLE_SQL = """
    SELECT key, summary, links_json
    FROM tickets
    WHERE status_category = 'done'
      AND resolved_at IS NOT NULL
      AND comment_count >= 2
      AND length(coalesce(description_text, '')) >= 500
      AND summary IS NOT NULL AND btrim(summary) <> ''
    ORDER BY updated_at DESC
    LIMIT %(limit)s
"""


def _linked_keys(links_json) -> list[str]:
    """Extract linked ticket keys from a links_json value (str or list or None)."""
    if not links_json:
        return []
    data = links_json
    if isinstance(links_json, str):
        try:
            data = json.loads(links_json)
        except (ValueError, TypeError):
            return []
    out: list[str] = []
    for link in data or []:
        k = (link or {}).get("key")
        if k:
            out.append(k)
    return out


def build_rows(tickets: list[dict]) -> list[dict]:
    """Pure: ticket dicts -> golden rows. Skips rows with blank summaries."""
    rows: list[dict] = []
    for t in tickets:
        summary = (t.get("summary") or "").strip()
        if not summary:
            continue
        keys = [t["key"], *_linked_keys(t.get("links_json"))]
        # de-dup preserving order
        seen: dict[str, None] = {}
        for k in keys:
            seen.setdefault(k, None)
        rows.append({"question": summary, "expected_keys": list(seen)})
    return rows


def _fetch(limit: int) -> list[dict]:
    import psycopg
    from psycopg.rows import dict_row
    dsn = os.getenv("CONWO_DSN") or os.getenv("DATABASE_URL")
    if not dsn:
        # Fall back to backend's discrete-var DSN resolution.
        sys.path.insert(0, str(ROOT))
        from backend.db import _dsn
        dsn = _dsn()
    with psycopg.connect(dsn) as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute(SAMPLE_SQL, {"limit": limit})
        return list(cur.fetchall())


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--limit", type=int, default=25)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--append", action="store_true",
                    help="Append to --out instead of overwriting (preserves curated rows).")
    args = ap.parse_args(argv)

    rows = build_rows(_fetch(args.limit))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if args.append else "w"
    with args.out.open(mode, encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"wrote {len(rows)} rows to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `venv/bin/pytest tests/scripts/test_seed_jira_golden.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Generate the starter golden set from prod-shaped data**

Run (against a DB with tickets — local or via `CONWO_DSN`):
`venv/bin/python scripts/seed_jira_golden.py --limit 25 --out docs/eval/jira-golden.jsonl`
Expected: `wrote N rows to docs/eval/jira-golden.jsonl` (N ~= 25).
Then open the file and **hand-verify 3–5 rows** read like real questions; delete any whose summary is not a meaningful question. If the DB is unavailable in the dev env, hand-author at least 10 rows using real ticket keys from `sqlite3`/psql lookups — the gate needs a non-trivial set.

- [ ] **Step 6: Commit**

```bash
git add scripts/seed_jira_golden.py tests/scripts/test_seed_jira_golden.py docs/eval/jira-golden.jsonl
git commit -m "test(eval): Jira golden set + seed helper for ranking gate"
```

---

### Task 2: Jira eval harness (baseline vs candidate)

**Files:**
- Create: `scripts/eval_jira_retrieval.py`
- Test: `tests/scripts/test_eval_jira_retrieval.py`

**Interfaces:**
- Consumes: `recall_at_k`, `mrr` from `scripts.eval_wiki_retrieval` (pure, already unit-tested).
- Consumes: `docs/eval/jira-golden.jsonl` (Task 1).
- Consumes: `backend.retrieval.v2.pipeline.search(question, limit=k) -> RetrievalResult` (`.tickets` is a list of dicts each with `"key"`).
- Produces: `load_jira_golden(path) -> list[dict]`, `run_jira(question, k) -> list[str]`, `reset_rerank_cache()`, `evaluate_config(items, k, env) -> dict`. Used by Task 4/5 eval steps.

- [ ] **Step 1: Write the failing test (pure loader + env-diff parsing)**

```python
# tests/scripts/test_eval_jira_retrieval.py
import json
from scripts.eval_jira_retrieval import load_jira_golden, parse_env_overrides


def test_parse_env_overrides():
    assert parse_env_overrides("CONWO_RANK_BLEND=off") == {"CONWO_RANK_BLEND": "off"}
    assert parse_env_overrides("A=1,B=2") == {"A": "1", "B": "2"}
    assert parse_env_overrides("") == {}


def test_load_jira_golden(tmp_path):
    p = tmp_path / "g.jsonl"
    p.write_text(json.dumps({"question": "q1", "expected_keys": ["TS-1"]}) + "\n"
                 + "\n"  # blank line skipped
                 + json.dumps({"question": "q2", "expected_keys": ["PB-2", "PB-3"]}) + "\n",
                 encoding="utf-8")
    items = load_jira_golden(p)
    assert items == [{"question": "q1", "expected_keys": ["TS-1"]},
                     {"question": "q2", "expected_keys": ["PB-2", "PB-3"]}]


def test_load_jira_golden_rejects_missing_key(tmp_path):
    p = tmp_path / "bad.jsonl"
    p.write_text(json.dumps({"question": "q"}) + "\n", encoding="utf-8")
    try:
        load_jira_golden(p)
        assert False, "expected ValueError"
    except ValueError:
        pass
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv/bin/pytest tests/scripts/test_eval_jira_retrieval.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.eval_jira_retrieval'`

- [ ] **Step 3: Implement `scripts/eval_jira_retrieval.py`**

```python
#!/usr/bin/env python3
"""Golden eval harness for Jira retrieval-v2 ranking.

Runs a curated Jira golden set (docs/eval/jira-golden.jsonl) through the v2
Jira pipeline under a BASELINE and a CANDIDATE env configuration and reports
recall@k / MRR on ticket keys. Ranking gate: candidate must not regress
recall@k vs baseline.

Golden schema (one JSON object per line):
    {"question": str, "expected_keys": [str, ...]}

Usage:
    venv/bin/python scripts/eval_jira_retrieval.py --k 10 \
        --baseline "CONWO_RANK_BLEND=off" \
        --candidate "CONWO_RANK_BLEND=on"

Backend imports are local to the functions that need them so the pure helpers
(load_jira_golden / parse_env_overrides) import without a live DB.
"""
from __future__ import annotations
import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))  # so `scripts.*` and `backend.*` import when run directly
DEFAULT_GOLDEN = ROOT / "docs" / "eval" / "jira-golden.jsonl"

from scripts.eval_wiki_retrieval import recall_at_k, mrr  # noqa: E402 (pure, DRY)


def parse_env_overrides(spec: str) -> dict[str, str]:
    """Parse 'K=V,K2=V2' into a dict. Empty string -> {}."""
    out: dict[str, str] = {}
    for pair in spec.split(","):
        pair = pair.strip()
        if not pair:
            continue
        k, _, v = pair.partition("=")
        out[k.strip()] = v.strip()
    return out


def load_jira_golden(path: Path) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if "question" not in obj or "expected_keys" not in obj:
                raise ValueError(
                    f"{path}:{line_no}: golden item needs 'question' + 'expected_keys': {obj!r}")
            items.append(obj)
    return items


def reset_rerank_cache() -> None:
    """Drop the memoized CrossEncoder so a changed CONWO_RERANK_MAX_LENGTH takes
    effect between configs (the model bakes max_length at construction time)."""
    from backend.retrieval.v2 import rerank
    rerank._model = None
    try:
        rerank._load_model.cache_clear()
    except AttributeError:
        pass


def run_jira(question: str, k: int) -> list[str]:
    from backend.retrieval.v2 import pipeline
    res = pipeline.search(question, limit=k)
    return [t["key"] for t in res.tickets][:k]


def evaluate_config(items: list[dict], k: int, env: dict[str, str]) -> dict[str, Any]:
    """Apply env overrides, reset the rerank cache, run all golden items."""
    saved = {kk: os.environ.get(kk) for kk in env}
    os.environ.update(env)
    reset_rerank_cache()
    try:
        recalls, mrrs, per_q = [], [], []
        for item in items:
            expected = item["expected_keys"]
            try:
                got = run_jira(item["question"], k)
            except Exception as exc:  # noqa: BLE001 - one bad row must not kill the gate
                print(f"[warn] jira retrieval error for {item['question']!r}: {exc}",
                      file=sys.stderr)
                got = []
            r, m = recall_at_k(got, expected, k), mrr(got, expected)
            recalls.append(r); mrrs.append(m)
            per_q.append({"question": item["question"], "recall": r, "mrr": m, "got": got})
        n = len(items)
        return {"env": env, "n": n,
                "recall_at_k": (sum(recalls) / n) if n else 0.0,
                "mrr": (sum(mrrs) / n) if n else 0.0,
                "per_question": per_q}
    finally:
        for kk, v in saved.items():
            if v is None:
                os.environ.pop(kk, None)
            else:
                os.environ[kk] = v
        reset_rerank_cache()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--golden", type=Path, default=DEFAULT_GOLDEN)
    ap.add_argument("--k", type=int, default=10)
    ap.add_argument("--baseline", default="CONWO_RANK_BLEND=off,CONWO_RERANK_SMART_WINDOW=off")
    ap.add_argument("--candidate", default="CONWO_RANK_BLEND=on,CONWO_RERANK_SMART_WINDOW=on")
    args = ap.parse_args(argv)

    items = load_jira_golden(args.golden)
    if not items:
        print(f"Golden set {args.golden} is empty.", file=sys.stderr)
        return 2

    base = evaluate_config(items, args.k, parse_env_overrides(args.baseline))
    cand = evaluate_config(items, args.k, parse_env_overrides(args.candidate))

    print(f"\nJira ranking eval — k={args.k}, n={base['n']}")
    print(f"{'config':<12} {'recall@' + str(args.k):>10} {'MRR':>8}")
    print(f"{'baseline':<12} {base['recall_at_k']:>10.3f} {base['mrr']:>8.3f}")
    print(f"{'candidate':<12} {cand['recall_at_k']:>10.3f} {cand['mrr']:>8.3f}")

    if cand["recall_at_k"] < base["recall_at_k"]:
        print(f"\nGATE FAILED: candidate recall {cand['recall_at_k']:.3f} < "
              f"baseline {base['recall_at_k']:.3f}", file=sys.stderr)
        return 1
    print(f"\nGATE PASSED: candidate recall {cand['recall_at_k']:.3f} >= "
          f"baseline {base['recall_at_k']:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `venv/bin/pytest tests/scripts/test_eval_jira_retrieval.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Smoke-run the harness (no-op baseline vs candidate == current code)**

Run: `venv/bin/python scripts/eval_jira_retrieval.py --k 10`
Expected: prints a baseline/candidate table and `GATE PASSED` (both configs equal today, since the flags don't exist yet — they no-op to current behavior). If the DB/Gemini is unavailable locally, note that and defer the live run to the pod during verification.

- [ ] **Step 6: Commit**

```bash
git add scripts/eval_jira_retrieval.py tests/scripts/test_eval_jira_retrieval.py
git commit -m "test(eval): Jira ranking eval harness (baseline vs candidate)"
```

---

### Task 3: Populate the wiki golden set (guards the shared reranker)

**Files:**
- Modify: `docs/eval/wiki-golden.jsonl` (replace the two `_example` placeholder rows with curated rows)

**Interfaces:**
- Consumes: `backend/wiki_retriever.search` + `wiki_v2.pipeline.search` via the existing `scripts/eval_wiki_retrieval.py`. No code change — data only.

- [ ] **Step 1: List the actual wiki pages so expected_pages are real**

Run: `ls wiki/modules wiki/configs wiki/runbooks wiki/cross-module wiki/history 2>/dev/null`
Expected: a file listing. Use it to confirm each `expected_pages` value below exists; adjust any that don't.

- [ ] **Step 2: Write curated rows (verified against Step 1) into the golden file**

Replace the file contents with rows like the following, keeping ONLY those whose `expected_pages` you confirmed exist in Step 1 (compose via a `/tmp` heredoc script, not the Edit tool, per CLAUDE.md — `.jsonl` is safe but keep the pattern):

```json
{"question": "why does the one-time passcode fail at the security guard's tablet", "expected_pages": ["modules/guard-app-kiosks.md"], "intent": "DEBUGGING"}
{"question": "which settings control how long before a meeting room auto-releases if nobody shows up", "expected_pages": ["configs/meeting-rooms.md", "modules/meeting-rooms.md"], "intent": "CONFIGURATION"}
{"question": "how do I connect WorkInSync to Microsoft Teams", "expected_pages": ["modules/ms-teams-integration.md"], "intent": "HOW_TO"}
{"question": "what breaks if we change how single sign-on works", "expected_pages": ["modules/sso.md"], "intent": "ARCHITECTURAL"}
{"question": "difference between the India and global servers for visitor management config", "expected_pages": ["configs/visitor-management.md"], "intent": "COMPARISON"}
{"question": "how do employees get added automatically from our HR system", "expected_pages": ["modules/employee-provisioning.md"], "intent": "HOW_TO"}
{"question": "what is safe-reach and when is it used", "expected_pages": ["modules/safe-reach.md"], "intent": "DEFINITION"}
{"question": "show me the config for desk booking buffer time", "expected_pages": ["configs/desk-management.md"], "intent": "CONFIGURATION"}
```

- [ ] **Step 3: Verify the wiki eval runs and gate passes on current code**

Run: `venv/bin/python scripts/eval_wiki_retrieval.py --golden docs/eval/wiki-golden.jsonl --engines keyword,v2 --k 5`
Expected: a report table; `GATE PASSED: v2 recall@5 >= keyword recall@5`. If v2 loses on a row, that is pre-existing wiki behavior — record it, do not fix here (Phase 1 is ranking, not wiki content).

- [ ] **Step 4: Commit**

```bash
git add docs/eval/wiki-golden.jsonl
git commit -m "test(eval): curate wiki golden rows (guards shared reranker for A2)"
```

---

### Task 4: A1 — blend ranking signals in `gate.py`

**Files:**
- Modify: `backend/retrieval/v2/gate.py`
- Test: `tests/retrieval/v2/test_gate_blend.py`

**Interfaces:**
- Consumes: `scored: list[tuple[dict, float]]` where each dict already carries `fused_score` (float) and, for hybrid candidates, `timeline_score` (float, 0..1) and `bucket` (str). Link-expanded candidates may lack `timeline_score`/`bucket` (Phase 2/B1 fixes that) — treat missing as `0.0`/absent.
- Produces: unchanged `apply(scored) -> RetrievalResult`; tickets now ordered by blended score and each carries `blended_score` alongside `reranker_score`. New module-level helpers `_weights()`, `_norm_fused(scored)`, `_blend(scored)`.

- [ ] **Step 1: Write failing tests for the blend behavior**

```python
# tests/retrieval/v2/test_gate_blend.py
import os
import pytest
from backend.retrieval.v2 import gate


def _c(key, fused, timeline, bucket="latest", **extra):
    return {"key": key, "fused_score": fused, "timeline_score": timeline,
            "bucket": bucket, **extra}


def test_blend_reorders_by_all_signals(monkeypatch):
    monkeypatch.setenv("CONWO_RANK_BLEND", "on")
    monkeypatch.setenv("CONWO_RANK_W_RERANK", "0.5")
    monkeypatch.setenv("CONWO_RANK_W_TIMELINE", "0.3")
    monkeypatch.setenv("CONWO_RANK_W_FUSED", "0.2")
    # A: high reranker, stale/low recency+fusion. B: slightly lower reranker but
    # strong recency+fusion. Blend should put B first.
    scored = [(_c("A", fused=0.0, timeline=0.05), 0.80),
              (_c("B", fused=1.0, timeline=1.00), 0.72)]
    res = gate.apply(scored)
    assert res.tickets[0]["key"] == "B"
    assert "blended_score" in res.tickets[0]


def test_blend_off_preserves_reranker_order(monkeypatch):
    monkeypatch.setenv("CONWO_RANK_BLEND", "off")
    scored = [(_c("A", fused=0.0, timeline=0.05), 0.80),
              (_c("B", fused=1.0, timeline=1.00), 0.72)]
    res = gate.apply(scored)
    assert res.tickets[0]["key"] == "A"   # bare reranker wins when blend off


def test_abstain_still_uses_reranker_not_blend(monkeypatch):
    monkeypatch.setenv("CONWO_RANK_BLEND", "on")
    monkeypatch.setenv("CONWO_RETRIEVAL_V2_ABSTAIN_THRESHOLD", "0.5")
    # reranker top 0.30 < abstain 0.5 → abstain, even though fusion/recency are high
    scored = [(_c("A", fused=1.0, timeline=1.0), 0.30)]
    res = gate.apply(scored)
    assert res.abstain is True and res.confidence == "Abstain"


def test_norm_fused_handles_zero_range(monkeypatch):
    monkeypatch.setenv("CONWO_RANK_BLEND", "on")
    # all equal fused → normalized 0.0 for all, no divide-by-zero
    scored = [(_c("A", fused=0.5, timeline=0.9), 0.9),
              (_c("B", fused=0.5, timeline=0.1), 0.6)]
    res = gate.apply(scored)   # must not raise
    assert {t["key"] for t in res.tickets} == {"A", "B"}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `venv/bin/pytest tests/retrieval/v2/test_gate_blend.py -v`
Expected: FAIL (blend not implemented; `blended_score` missing / order wrong).

- [ ] **Step 3: Implement the blend in `gate.py`**

Add these helpers after the `HIGH` lambda (around line 17):

```python
def _weights() -> tuple[float, float, float]:
    return (_f("CONWO_RANK_W_RERANK", 0.5),
            _f("CONWO_RANK_W_TIMELINE", 0.3),
            _f("CONWO_RANK_W_FUSED", 0.2))

BLEND_HIGH = lambda: _f("CONWO_RANK_BLEND_HIGH_THRESHOLD", 0.55)

def _blend_enabled() -> bool:
    import os
    return os.getenv("CONWO_RANK_BLEND", "on").strip().lower() != "off"

def _norm_fused(scored: list[tuple[dict, float]]) -> dict[int, float]:
    """Min-max normalize fused_score across the candidate set → {id(candidate): 0..1}.
    Zero range (all equal) → 0.0 for every candidate (no divide-by-zero)."""
    vals = [float(c.get("fused_score") or 0.0) for c, _ in scored]
    lo, hi = min(vals), max(vals)
    span = hi - lo
    return {id(c): ((float(c.get("fused_score") or 0.0) - lo) / span if span else 0.0)
            for c, _ in scored}

def _blend(scored: list[tuple[dict, float]]) -> list[tuple[dict, float, float]]:
    """Return [(candidate, reranker_score, blended_score), ...] sorted by blend desc."""
    wr, wt, wf = _weights()
    nf = _norm_fused(scored)
    out = []
    for c, r in scored:
        t = float(c.get("timeline_score") or 0.0)
        blended = wr * r + wt * t + wf * nf[id(c)]
        out.append((c, r, blended))
    out.sort(key=lambda x: x[2], reverse=True)
    return out
```

Then replace the body of `apply()` (from `top_score = scored[0][1]` through the end of tier selection) so ordering + tiering use the blend while abstain stays on the reranker. Full replacement of `apply` below:

```python
def apply(scored: list[tuple[dict, float]]) -> RetrievalResult:
    abstain_t = ABSTAIN()
    if not scored:
        return RetrievalResult(
            tickets=[], confidence="Abstain", abstain=True,
            message="I couldn't find any matching tickets.",
            diagnostics={"top_score": None, "candidate_count": 0},
        )

    # Abstain safety net: calibrated reranker score decides "did anything match".
    reranker_top = max(s for _, s in scored)
    diag = {
        "reranker_top": reranker_top,
        "candidate_count": len(scored),
        "bucket_counts": timeline.bucket_counts(c for c, _ in scored),
    }
    if reranker_top < abstain_t:
        keys = [c["key"] for c, _ in scored[:5]]
        return RetrievalResult(
            tickets=[], confidence="Abstain", abstain=True,
            message=(f"I couldn't find strong evidence. "
                     f"Closest matches: {', '.join(keys)}. Please verify."),
            diagnostics=diag,
        )

    # Ordering + tiering: blend of reranker + recency + fusion (or bare reranker
    # when CONWO_RANK_BLEND=off — back-compat).
    if _blend_enabled():
        ranked = _blend(scored)                     # [(c, r, blend)] blend-sorted
        high_t = BLEND_HIGH()
        top_key_score = ranked[0][2]                # blended top
    else:
        ranked = [(c, r, r) for c, r in scored]     # blend == reranker
        ranked.sort(key=lambda x: x[2], reverse=True)
        high_t = HIGH()
        top_key_score = ranked[0][2]
    diag["top_score"] = top_key_score

    tickets = [{**c, "reranker_score": r, "blended_score": b} for c, r, b in ranked[:10]]
    # `scored_like` keeps the (candidate, score) shape the agreement/penalty
    # helpers expect, but in the new blend order.
    scored_like = [(c, b) for c, r, b in ranked]

    if len(ranked) == 1:
        result = RetrievalResult(
            tickets=tickets, confidence="Low", abstain=False,
            message="single-source evidence — only one ticket supports this.",
            diagnostics=diag)
    elif top_key_score >= high_t:
        if _top3_agree(scored_like):
            result = RetrievalResult(tickets=tickets, confidence="High", abstain=False,
                                     message="strong, agreeing evidence", diagnostics=diag)
        else:
            result = RetrievalResult(tickets=tickets, confidence="Medium", abstain=False,
                                     message="strong evidence but tickets do not fully agree",
                                     diagnostics=diag)
    else:
        if _top3_agree(scored_like):
            result = RetrievalResult(tickets=tickets, confidence="Medium", abstain=False,
                                     message="moderate, agreeing evidence", diagnostics=diag)
        else:
            result = RetrievalResult(tickets=tickets, confidence="Low", abstain=False,
                                     message="moderate evidence, tickets disagree",
                                     diagnostics=diag)

    steps, reason = _top3_bucket_penalty(scored_like)
    if steps:
        new_conf = _downgrade(result.confidence, steps)
        if new_conf != result.confidence:
            result.confidence = new_conf
            result.message += f" (downgraded: top candidates are {reason})"
    return result
```

Note: `_top3_agree` and `_top3_bucket_penalty` already accept a `list[tuple[dict, float]]` and only read the dicts — passing `scored_like` is compatible.

- [ ] **Step 4: Run tests to verify they pass**

Run: `venv/bin/pytest tests/retrieval/v2/test_gate_blend.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Run the existing gate tests to confirm no regression**

Run: `venv/bin/pytest tests/retrieval/v2/ -v`
Expected: all pass. If a pre-existing gate test asserts `diagnostics["top_score"]` equals the bare reranker, update it to read `diagnostics["reranker_top"]` for the abstain path (the blend path keeps `top_score` = blended top). Show any such edit in the commit.

- [ ] **Step 6: Run the Jira ranking gate (blend off vs on)**

Run: `venv/bin/python scripts/eval_jira_retrieval.py --k 10 \
  --baseline "CONWO_RANK_BLEND=off" --candidate "CONWO_RANK_BLEND=on"`
Expected: `GATE PASSED` (candidate recall >= baseline). If it FAILS, tune weights via `CONWO_RANK_W_*` and re-run; if no weighting beats baseline, stop and report — do not ship a regression.

- [ ] **Step 7: Commit**

```bash
git add backend/retrieval/v2/gate.py tests/retrieval/v2/test_gate_blend.py
git commit -m "feat(rank): blend reranker + recency + fusion for Jira order & confidence (A1)"
```

---

### Task 5: A2 — smart reranker read-window in `rerank.py`

**Files:**
- Modify: `backend/retrieval/v2/rerank.py`
- Test: `tests/retrieval/v2/test_rerank_window.py`

**Interfaces:**
- Consumes: candidate dicts with `summary` / `description_text` / `comments_text` (shared Jira + wiki contract) plus the `query` string.
- Produces: unchanged public `score(query, candidates)` / `score_async(...)`; internally `_doc_text` now takes the query and selects the query-relevant slice when `CONWO_RERANK_SMART_WINDOW=on`. New helper `_relevant_slice(query, text, max_chars)`. `_load_model` reads `CONWO_RERANK_MAX_LENGTH`.

- [ ] **Step 1: Write failing tests for slice selection + window**

```python
# tests/retrieval/v2/test_rerank_window.py
import os
from backend.retrieval.v2 import rerank


def test_relevant_slice_picks_query_matching_sentence():
    text = ("Intro sentence about nothing. "
            "The kiosk requires an OTP before visitor registration. "
            "Closing unrelated note about parking.")
    out = rerank._relevant_slice("kiosk OTP registration", text, max_chars=80)
    assert "OTP" in out and "registration" in out
    assert "parking" not in out            # least-relevant sentence dropped first
    assert len(out) <= 80


def test_relevant_slice_empty_text():
    assert rerank._relevant_slice("q", "", max_chars=50) == ""


def test_doc_text_smart_window_prefers_relevant(monkeypatch):
    monkeypatch.setenv("CONWO_RERANK_SMART_WINDOW", "on")
    c = {"summary": "Kiosk OTP issue",
         "description_text": ("Filler one. " * 40) + "OTP fails before registration. " + ("Filler two. " * 40),
         "comments_text": "Unrelated. Fixed by setting kioskRequireOTPBeforeRegister=false. More filler."}
    out = rerank._doc_text(c, query="kiosk OTP registration")
    assert "OTP fails before registration" in out
    assert "kioskRequireOTPBeforeRegister" in out   # relevant comment slice kept


def test_doc_text_off_matches_legacy_head(monkeypatch):
    monkeypatch.setenv("CONWO_RERANK_SMART_WINDOW", "off")
    c = {"summary": "S", "description_text": "D" * 1000, "comments_text": "C" * 1000}
    out = rerank._doc_text(c, query="anything")
    # legacy fixed budget: summary + 500 desc + 300 comments with prefix
    assert out.startswith("S\n") and ("D" * 500) in out and ("C" * 300) in out
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `venv/bin/pytest tests/retrieval/v2/test_rerank_window.py -v`
Expected: FAIL (`_relevant_slice` missing; `_doc_text` takes no `query`).

- [ ] **Step 3: Implement the smart window in `rerank.py`**

Change `_load_model` to read the window from env:

```python
def _max_length() -> int:
    try:
        return int(os.getenv("CONWO_RERANK_MAX_LENGTH", "512"))
    except (TypeError, ValueError):
        return 512

@lru_cache(maxsize=1)
def _load_model():
    import torch
    torch.set_num_threads(2)
    from sentence_transformers import CrossEncoder
    return CrossEncoder(MODEL_DIR, max_length=_max_length())
```

Add slice selection + a smart-aware `_doc_text` (replace the existing `_doc_text`). Keep the legacy fixed-budget layout for the flag-off path so behavior is byte-identical when disabled:

```python
import re

# Larger budgets for the 512-token window (still safe at ~4 chars/token).
_SMART_SUMMARY_MAX  = 200
_SMART_DESC_MAX     = 900
_SMART_COMMENTS_MAX = 700

def _tokenize(s: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", s.lower()) if len(w) >= 3}

def _relevant_slice(query: str, text: str, max_chars: int) -> str:
    """Return up to max_chars of the sentences in `text` most lexically
    overlapping with `query`, in original order. Empty text -> ''."""
    text = (text or "").strip()
    if not text:
        return ""
    q = _tokenize(query)
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", text) if s.strip()]
    if not sentences:
        return text[:max_chars]
    scored = sorted(
        enumerate(sentences),
        key=lambda it: (len(q & _tokenize(it[1])), -it[0]),
        reverse=True,
    )
    picked_idx: list[int] = []
    total = 0
    for idx, sent in scored:
        if total + len(sent) + 1 > max_chars and picked_idx:
            break
        picked_idx.append(idx)
        total += len(sent) + 1
    picked_idx.sort()  # restore reading order
    return " ".join(sentences[i] for i in picked_idx)[:max_chars]

def _smart_enabled() -> bool:
    return os.getenv("CONWO_RERANK_SMART_WINDOW", "on").strip().lower() != "off"

def _doc_text(c: dict, query: str = "") -> str:
    """Reranker input. Smart mode selects the query-relevant slice of each
    field; legacy mode uses the fixed head budget (byte-identical to pre-A2)."""
    if not _smart_enabled() or not query:
        summary  = (c.get("summary")          or "").strip()[:_SUMMARY_MAX]
        desc     = (c.get("description_text") or "").strip()[:_DESC_MAX]
        comments = (c.get("comments_text")    or "").strip()[:_COMMENTS_MAX]
        parts = []
        if summary:  parts.append(summary)
        if desc:     parts.append(desc)
        if comments: parts.append(f"[comments] {comments}")
        return "\n".join(parts)

    summary  = (c.get("summary") or "").strip()[:_SMART_SUMMARY_MAX]
    desc     = _relevant_slice(query, c.get("description_text") or "", _SMART_DESC_MAX)
    comments = _relevant_slice(query, c.get("comments_text") or "", _SMART_COMMENTS_MAX)
    parts = []
    if summary:  parts.append(summary)
    if desc:     parts.append(desc)
    if comments: parts.append(f"[comments] {comments}")
    return "\n".join(parts)
```

Update `score()` to pass the query into `_doc_text`:

```python
def score(query: str, candidates: list[dict]) -> list[tuple[dict, float]]:
    if not candidates:
        return []
    pairs = [(query, _doc_text(c, query)) for c in candidates]
    m = _model_or_load() if _model is None else _model
    scores = m.predict(pairs)
    out = list(zip(candidates, (_sigmoid(float(s)) for s in scores)))
    out.sort(key=lambda x: x[1], reverse=True)
    return out
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `venv/bin/pytest tests/retrieval/v2/test_rerank_window.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Run existing rerank tests (incl. the sigmoid regression test)**

Run: `venv/bin/pytest tests/retrieval/v2/test_rerank.py -v`
Expected: all pass (sigmoid behavior unchanged; `_doc_text` back-compat holds for flag-off).

- [ ] **Step 6: Run BOTH eval gates (rerank is shared)**

Run:
`venv/bin/python scripts/eval_jira_retrieval.py --k 10 --baseline "CONWO_RERANK_SMART_WINDOW=off" --candidate "CONWO_RERANK_SMART_WINDOW=on"`
Expected: `GATE PASSED`.
`venv/bin/python scripts/eval_wiki_retrieval.py --golden docs/eval/wiki-golden.jsonl --engines v2 --k 5`
Expected: report prints; record v2 recall@5 with smart window on vs off (run twice with the env var toggled) and confirm no wiki regression.

- [ ] **Step 7: Commit**

```bash
git add backend/retrieval/v2/rerank.py tests/retrieval/v2/test_rerank_window.py
git commit -m "feat(rank): query-relevant reranker window + 512 max_length (A2)"
```

---

### Task 6: Document new flags + record deferrals

**Files:**
- Modify: `docs/superpowers/specs/2026-07-11-retrieval-accuracy-hardening-design.md` (append a "Phase 1 — as-built" note)
- Modify: `CLAUDE.md` (add the new env flags to a config-flags note if one exists; otherwise skip — do not invent a section)

**Interfaces:** none (docs only).

- [ ] **Step 1: Append an as-built note to the design doc**

Add a short section recording: the env flags added (`CONWO_RANK_BLEND`, `CONWO_RANK_W_RERANK/_TIMELINE/_FUSED`, `CONWO_RANK_BLEND_HIGH_THRESHOLD`, `CONWO_RERANK_SMART_WINDOW`, `CONWO_RERANK_MAX_LENGTH`), the eval-tuned weight values chosen (from Task 4 Step 6), and that **A1's cross-gate confidence combination (stricter-of retrieval vs citation-gate confidence) is deferred to Phase 2/B3**, where orchestrator confidence-capping is already being modified. Compose via a `/tmp` heredoc or Edit (both allowed on `.md`).

- [ ] **Step 2: Commit**

```bash
git add docs/superpowers/specs/2026-07-11-retrieval-accuracy-hardening-design.md CLAUDE.md
git commit -m "docs: Phase 1 as-built flags + defer confidence-combination to Phase 2"
```

---

## Verification (after all tasks, in the pod)

Per the spec, verify in prod after the phase merges: startup logs show the reranker still preloads; a live Jira-answering query returns sensibly-ordered tickets; and a quick `venv/bin/python scripts/eval_jira_retrieval.py` run inside the pod shows `GATE PASSED`. Set the eval-tuned `CONWO_RANK_W_*` / `CONWO_RANK_BLEND_HIGH_THRESHOLD` values in the pod env (AWS Secrets Manager `prod/conwo`) only if they differ from the code defaults.

## Deferred to later phases (not in this plan)

- **A1 confidence combination** (stricter-of retrieval vs citation-gate) → Phase 2/B3 (orchestrator confidence work).
- **B1 honest link-expansion** (bucket/label expanded rows) → Phase 2. Until then, blend treats missing `timeline_score` on expanded rows as 0.0, which de-emphasizes them (acceptable interim).
- Injection defense, determinism, caching, conversation-load, failover, streaming → Phases 3–5.
