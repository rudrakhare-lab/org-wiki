#!/usr/bin/env python3
"""
Log every agent answer with a stable answer_id, so user feedback can be linked
back to the exact question, answer text, confidence, and cited sources.

Answer records may contain customer context and live config values, so the
default store is `raw/feedback/answer_log.jsonl` (gitignored).

The answer_id is the 12-char sha1 prefix of `question + answer_text + created_at`.

Commands:
  log    — append one record to the answer log
  get    — print one record by --answer-id
  list   — print recent records (most recent first)
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_STORE = ROOT / "raw" / "feedback" / "answer_log.jsonl"

CONFIDENCE_VALUES = {"High", "Medium", "Low"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store", type=Path, default=DEFAULT_STORE)

    sub = parser.add_subparsers(dest="command", required=True)

    log_cmd = sub.add_parser("log", help="Append one answer record")
    log_cmd.add_argument("--question", required=True)
    log_cmd.add_argument("--answer-text", required=True)
    log_cmd.add_argument("--confidence", required=True, choices=sorted(CONFIDENCE_VALUES))
    log_cmd.add_argument(
        "--wiki",
        default="",
        help="Comma-separated wiki page paths cited (e.g. wiki/modules/visitor-management.md)",
    )
    log_cmd.add_argument(
        "--jira",
        default="",
        help="Comma-separated Jira ticket keys cited (e.g. TS-36471,PB-66727)",
    )
    log_cmd.add_argument(
        "--pms",
        default="",
        help="Comma-separated PMS configs cited (e.g. VISITOR:kioskRequireOTPBeforeRegister)",
    )
    log_cmd.add_argument(
        "--retrieval-notes",
        default="",
        help="Optional: keywords searched, buckets used, retrieval path",
    )
    log_cmd.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress the 'Logged ...' confirmation line; print only the answer_id",
    )

    get_cmd = sub.add_parser("get", help="Print one answer record by id")
    get_cmd.add_argument("--answer-id", required=True)

    list_cmd = sub.add_parser("list", help="List recent answer records")
    list_cmd.add_argument("--limit", type=int, default=10)

    return parser.parse_args()


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def split_csv(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


def make_answer_id(question: str, answer_text: str, created_at: str) -> str:
    base = f"{question}\n{answer_text}\n{created_at}"
    return hashlib.sha1(base.encode("utf-8")).hexdigest()[:12]


def load_records(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))
    return records


def append_record(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def cmd_log(args: argparse.Namespace) -> int:
    created_at = utc_now()
    answer_id = make_answer_id(args.question, args.answer_text, created_at)
    record = {
        "answer_id": answer_id,
        "created_at": created_at,
        "question": args.question,
        "answer_text": args.answer_text,
        "confidence": args.confidence,
        "sources": {
            "wiki": split_csv(args.wiki),
            "jira": split_csv(args.jira),
            "pms": split_csv(args.pms),
        },
        "retrieval_notes": args.retrieval_notes,
    }
    append_record(args.store, record)
    if args.quiet:
        print(answer_id)
    else:
        print(f"Logged answer {answer_id} → {args.store}")
    return 0


def cmd_get(args: argparse.Namespace) -> int:
    records = load_records(args.store)
    for r in records:
        if r.get("answer_id") == args.answer_id:
            print(json.dumps(r, indent=2, ensure_ascii=False))
            return 0
    print(f"No answer record found for id={args.answer_id}", file=sys.stderr)
    return 1


def cmd_list(args: argparse.Namespace) -> int:
    records = load_records(args.store)
    records = sorted(records, key=lambda r: r.get("created_at", ""), reverse=True)
    for r in records[: args.limit]:
        sources = r.get("sources", {}) or {}
        n_wiki = len(sources.get("wiki", []))
        n_jira = len(sources.get("jira", []))
        n_pms = len(sources.get("pms", []))
        print(
            f"{r.get('answer_id')} | {r.get('confidence'):<6} | "
            f"wiki={n_wiki} jira={n_jira} pms={n_pms} | {r.get('created_at')}"
        )
        question = (r.get("question") or "").replace("\n", " ")
        print(f"  Q: {question[:120]}")
    return 0


def main() -> int:
    args = parse_args()
    if args.command == "log":
        return cmd_log(args)
    if args.command == "get":
        return cmd_get(args)
    if args.command == "list":
        return cmd_list(args)
    raise SystemExit(f"Unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
