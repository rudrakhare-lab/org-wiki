#!/usr/bin/env python3
"""
Golden eval harness for wiki retrieval — keyword (old) vs v2 (hybrid semantic
+ graph + intent).

Runs a curated golden question set (docs/eval/wiki-golden.jsonl) through both
retrieval engines and reports recall@k (page-level), MRR, and section-hit-rate
(when `expected_anchors` is given). This is the pre-merge gate for wiki
retrieval v2: exits 1 if v2's recall@k regresses vs. the keyword baseline.

Golden item JSONL schema (one object per line):
    {
      "question": str,
      "expected_pages": [str, ...],
      "expected_anchors": [str, ...]   # optional, e.g. "modules/x.md#section"
      "intent": str                     # optional, informational only
    }

Usage:
    venv/bin/python scripts/eval_wiki_retrieval.py \
        --golden docs/eval/wiki-golden.jsonl --engines keyword,v2 --k 5

NOTE: everything below `run_engine` touches the real retrievers (Postgres +
Gemini for v2). The metric functions (recall_at_k / mrr / section_hit /
load_golden) are pure and imported/unit-tested with zero I/O — do NOT add
top-level `backend.*` imports to this module, or the pure-function tests
will require a live DB just to import it.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_GOLDEN = ROOT / "docs" / "eval" / "wiki-golden.jsonl"


# ─────────────────────────── pure metric functions ───────────────────────────

def recall_at_k(got: list[str], expected: list[str], k: int) -> float:
    """Fraction of `expected` items present in `got[:k]`.

    Returns 0.0 if `expected` is empty (nothing to recall — avoids a
    ZeroDivisionError from a malformed/empty golden row poisoning the gate).
    """
    if not expected:
        return 0.0
    top_k = set(got[:k])
    hits = sum(1 for e in expected if e in top_k)
    return hits / len(expected)


def mrr(got: list[str], expected: list[str]) -> float:
    """Reciprocal rank (1-indexed) of the first `got` item that is in
    `expected`. Returns 0.0 if none of `got` is in `expected` (or either
    list is empty).
    """
    if not got or not expected:
        return 0.0
    expected_set = set(expected)
    for i, item in enumerate(got, start=1):
        if item in expected_set:
            return 1.0 / i
    return 0.0


def section_hit(got_anchors: list[str], expected_anchors: list[str]) -> bool:
    """True if any of `expected_anchors` appears anywhere in `got_anchors`."""
    if not expected_anchors:
        return False
    expected_set = set(expected_anchors)
    return bool(any(a in expected_set for a in got_anchors))


def load_golden(path: Path) -> list[dict[str, Any]]:
    """Load golden set JSONL. Each line must be a JSON object with at least
    `question` and `expected_pages`. Lines are not otherwise validated —
    the golden set is human-curated, not machine-generated.
    """
    items: list[dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSON — {exc}") from exc
            if "question" not in obj or "expected_pages" not in obj:
                raise ValueError(
                    f"{path}:{line_no}: golden item missing required "
                    f"'question'/'expected_pages' key: {obj!r}"
                )
            items.append(obj)
    return items


# ────────────────────────────── engine dispatch ──────────────────────────────

def run_engine(engine: str, question: str, k: int) -> tuple[list[str], list[str]]:
    """Returns (page_paths, anchors). Keyword engine has no anchors.

    Backend imports are local to this function (not top-level) so that the
    pure metric functions above stay importable/testable without a live
    Postgres or Gemini connection.
    """
    if engine == "keyword":
        from backend import wiki_retriever
        pages = [p.path for p in wiki_retriever.search(question, top_n=k)]
        return pages, []

    if engine == "v2":
        from backend.retrieval.wiki_v2 import pipeline
        hits = pipeline.search(question, top_k=k)
        anchors = [h.anchor for h in hits]
        # Page-level dedup preserving rank order — recall@k and MRR compare
        # PAGES against expected_pages; anchors only feed section_hit.
        pages = list(dict.fromkeys(a.split("#", 1)[0] for a in anchors))
        return pages, anchors

    raise ValueError(f"Unknown engine: {engine!r} (expected 'keyword' or 'v2')")


def run_engine_safe(engine: str, question: str, k: int) -> tuple[list[str], list[str]]:
    """run_engine, but v2 failures degrade to empty results + a stderr warning
    instead of aborting the whole eval run (a single bad question shouldn't
    kill the gate).

    Only v2 is degraded. The keyword engine is the trusted baseline the gate
    compares against — if it fails, that is a real error in the eval
    environment (e.g. wiki index unavailable) and must propagate, not
    silently degrade to recall=0.0. Degrading both engines equally would let
    a broken environment produce a false "GATE PASSED: 0.000 >= 0.000".
    """
    if engine != "v2":
        return run_engine(engine, question, k)
    try:
        return run_engine(engine, question, k)
    except Exception as exc:  # noqa: BLE001 - eval harness must not crash on one row
        # Import lazily so this module has no top-level backend dependency.
        try:
            from backend.retrieval.wiki_v2.pipeline import WikiV2Unavailable
        except Exception:  # pragma: no cover - backend unimportable at all
            WikiV2Unavailable = ()  # type: ignore[assignment]
        kind = "unavailable" if isinstance(exc, WikiV2Unavailable) else "error"
        print(
            f"[warn] engine={engine} {kind} for question={question!r}: {exc}",
            file=sys.stderr,
        )
        return [], []


# ──────────────────────────────────── CLI ────────────────────────────────────

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--golden", type=Path, default=DEFAULT_GOLDEN,
        help=f"Path to golden JSONL set (default: {DEFAULT_GOLDEN.relative_to(ROOT)})",
    )
    parser.add_argument(
        "--engines", default="keyword,v2",
        help="Comma-separated engine names to evaluate (keyword, v2)",
    )
    parser.add_argument("--k", type=int, default=5, help="k for recall@k / top_n")
    return parser.parse_args(argv)


def evaluate(engine: str, items: list[dict[str, Any]], k: int) -> dict[str, Any]:
    """Run one engine over all golden items and aggregate metrics."""
    recalls: list[float] = []
    mrrs: list[float] = []
    section_hits: list[bool] = []
    per_question: list[dict[str, Any]] = []

    for item in items:
        question = item["question"]
        expected_pages = item.get("expected_pages", [])
        expected_anchors = item.get("expected_anchors")

        pages, anchors = run_engine_safe(engine, question, k)

        r = recall_at_k(pages, expected_pages, k)
        m = mrr(pages, expected_pages)
        recalls.append(r)
        mrrs.append(m)

        row: dict[str, Any] = {
            "question": question,
            "recall": r,
            "mrr": m,
            "got_pages": pages,
        }
        if expected_anchors:
            hit = section_hit(anchors, expected_anchors)
            section_hits.append(hit)
            row["section_hit"] = hit
        per_question.append(row)

    n = len(items)
    return {
        "engine": engine,
        "n": n,
        "recall_at_k": (sum(recalls) / n) if n else 0.0,
        "mrr": (sum(mrrs) / n) if n else 0.0,
        "section_hit_rate": (
            sum(1 for h in section_hits if h) / len(section_hits)
            if section_hits else None
        ),
        "per_question": per_question,
    }


def print_report(results: dict[str, dict[str, Any]], k: int) -> None:
    print(f"\nWiki retrieval eval — k={k}")
    print(f"{'engine':<10} {'n':>4} {'recall@' + str(k):>10} {'MRR':>8} {'section-hit':>12}")
    for engine, res in results.items():
        shr = res["section_hit_rate"]
        shr_str = f"{shr:.3f}" if shr is not None else "—"
        print(
            f"{engine:<10} {res['n']:>4} {res['recall_at_k']:>10.3f} "
            f"{res['mrr']:>8.3f} {shr_str:>12}"
        )

    engines = list(results.keys())
    if len(engines) < 2:
        return

    # Per-question win/loss table, only meaningful when comparing exactly the
    # keyword vs v2 pair (or any two engines run together).
    print("\nPer-question (recall@k): " + " vs ".join(engines))
    base_engine, other_engine = engines[0], engines[1]
    base_rows = results[base_engine]["per_question"]
    other_rows = results[other_engine]["per_question"]
    for base_row, other_row in zip(base_rows, other_rows):
        question = base_row["question"]
        b_r, o_r = base_row["recall"], other_row["recall"]
        if o_r > b_r:
            verdict = f"{other_engine} WIN"
        elif o_r < b_r:
            verdict = f"{other_engine} LOSS"
        else:
            verdict = "tie"
        short_q = question if len(question) <= 60 else question[:57] + "..."
        print(f"  [{verdict:<12}] {base_engine}={b_r:.2f} {other_engine}={o_r:.2f}  {short_q}")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    engines = [e.strip() for e in args.engines.split(",") if e.strip()]

    try:
        items = load_golden(args.golden)
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error loading golden set: {exc}", file=sys.stderr)
        return 2

    if not items:
        print(f"Golden set {args.golden} has no usable rows — nothing to evaluate.",
              file=sys.stderr)
        return 2

    results = {engine: evaluate(engine, items, args.k) for engine in engines}
    print_report(results, args.k)

    # Merge gate: v2 must not regress recall@k vs. keyword.
    if "keyword" in results and "v2" in results:
        keyword_recall = results["keyword"]["recall_at_k"]
        v2_recall = results["v2"]["recall_at_k"]
        if v2_recall < keyword_recall:
            print(
                f"\nGATE FAILED: v2 recall@{args.k}={v2_recall:.3f} < "
                f"keyword recall@{args.k}={keyword_recall:.3f}",
                file=sys.stderr,
            )
            return 1
        print(
            f"\nGATE PASSED: v2 recall@{args.k}={v2_recall:.3f} >= "
            f"keyword recall@{args.k}={keyword_recall:.3f}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
