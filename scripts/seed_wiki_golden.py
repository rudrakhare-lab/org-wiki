#!/usr/bin/env python3
"""
Draft-golden generator for the wiki retrieval eval harness (scripts/eval_wiki_retrieval.py).

Extracts candidate questions from prior answer logs and emits a DRAFT JSONL
with `expected_pages` left EMPTY for a human to fill in.

This script is a checkpoint, not an automation: it never fabricates expected
pages/anchors. A human must curate the output (fill in `expected_pages` from
wiki knowledge) before it is usable as `docs/eval/wiki-golden.jsonl`.

Sources tried, in order:
  1. scripts/log_answer.py's answer log store (default: raw/feedback/answer_log.jsonl)
     — each record has "question" and "sources": {"wiki": [...], ...}.
     The cited wiki pages are carried over as a *hint*, not as expected_pages,
     because a cited page is not proof the retriever should have surfaced it
     as a top-k hit — a human must confirm relevance and page path.
  2. wiki/log.md "query |" entries (## [timestamp] query | <question>)
     — used as a fallback if the answer log is missing/empty.

Usage:
    venv/bin/python scripts/seed_wiki_golden.py --out /tmp/wiki-golden-draft.jsonl
    venv/bin/python scripts/seed_wiki_golden.py --limit 40
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ANSWER_LOG = ROOT / "raw" / "feedback" / "answer_log.jsonl"
DEFAULT_WIKI_LOG = ROOT / "wiki" / "log.md"
DEFAULT_OUT = ROOT / "docs" / "eval" / "wiki-golden.draft.jsonl"

# `## [2026-05-26 13:01] query | <question>`
QUERY_LOG_RE = re.compile(r"^## \[[^\]]+\]\s*query\s*\|\s*(?P<question>.+?)\s*$")


def load_answer_log_questions(path: Path) -> list[dict[str, Any]]:
    """Read scripts/log_answer.py records; return draft rows with wiki_hint."""
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            question = (record.get("question") or "").strip()
            if not question or question in seen:
                continue
            seen.add(question)
            wiki_hint = (record.get("sources") or {}).get("wiki") or []
            rows.append(_draft_row(question, wiki_hint=wiki_hint))
    return rows


def load_wiki_log_questions(path: Path) -> list[dict[str, Any]]:
    """Fallback: parse `## [...] query | <question>` entries from wiki/log.md."""
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            match = QUERY_LOG_RE.match(line.strip())
            if not match:
                continue
            question = match.group("question").strip()
            if not question or question in seen:
                continue
            seen.add(question)
            rows.append(_draft_row(question, wiki_hint=[]))
    return rows


def _draft_row(question: str, wiki_hint: list[str]) -> dict[str, Any]:
    """A draft golden row. expected_pages is intentionally empty — human fills
    it in. wiki_hint (pages cited when this question was originally answered)
    is carried along as a non-schema field to speed up curation; strip it
    before the file is used as the real golden set.
    """
    return {
        "question": question,
        "expected_pages": [],
        "_draft": True,
        "_wiki_hint": wiki_hint,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--answer-log", type=Path, default=DEFAULT_ANSWER_LOG)
    parser.add_argument("--wiki-log", type=Path, default=DEFAULT_WIKI_LOG)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument(
        "--limit", type=int, default=0,
        help="Max number of draft questions to emit (0 = no limit)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    rows = load_answer_log_questions(args.answer_log)
    source_used = str(args.answer_log)
    if not rows:
        rows = load_wiki_log_questions(args.wiki_log)
        source_used = str(args.wiki_log)

    if not rows:
        print(
            "No candidate questions found in either "
            f"{args.answer_log} or {args.wiki_log}. Nothing to draft.",
            file=sys.stderr,
        )
        return 1

    if args.limit:
        rows = rows[: args.limit]

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"Wrote {len(rows)} draft golden rows from {source_used} -> {args.out}")
    print(
        "STOP-AND-CURATE: fill in `expected_pages` (and optionally "
        "`expected_anchors`/`intent`) for each row by hand before using this "
        "as docs/eval/wiki-golden.jsonl. Do not mechanically fabricate "
        "expected_pages from _wiki_hint without verifying relevance."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
