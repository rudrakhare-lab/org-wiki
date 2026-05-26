#!/usr/bin/env python3
"""
Record and review LLM wiki answer feedback.

Feedback may contain customer context, so the default store is raw/feedback,
which is ignored from git.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_STORE = ROOT / "raw" / "feedback" / "answer_feedback.jsonl"
DEFAULT_ANSWER_LOG = ROOT / "raw" / "feedback" / "answer_log.jsonl"

LABELS = {
    "correct",
    "partially_correct",
    "wrong",
    "incomplete",
    "outdated",
    "conflicting_evidence",
    "wrong_config",
    "wrong_scope",
    "missing_jira",
    "missing_pms_runtime",
    "missing_runtime_context",
    "unclear",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store", type=Path, default=DEFAULT_STORE)

    sub = parser.add_subparsers(dest="command", required=True)

    record = sub.add_parser("record", help="Append one feedback record")
    record.add_argument("--question", required=True)
    record.add_argument("--answer-id", required=True)
    record.add_argument("--score", required=True, type=int, choices=range(1, 6))
    record.add_argument("--label", required=True, choices=sorted(LABELS))
    record.add_argument("--correction", default="")
    record.add_argument("--expected-answer", default="")
    record.add_argument("--sources", default="", help="Comma-separated sources used by the answer")
    record.add_argument("--affected", default="", help="Comma-separated pages/configs/tickets")
    record.add_argument("--reviewer", default="")
    record.add_argument(
        "--answer-log",
        type=Path,
        default=DEFAULT_ANSWER_LOG,
        help="Answer log path. If the answer_id exists there, the linked record is hydrated "
        "into the feedback entry. Use empty string to skip auto-link.",
    )

    list_cmd = sub.add_parser("list", help="List feedback records")
    list_cmd.add_argument("--status", default="pending")
    list_cmd.add_argument("--limit", type=int, default=20)
    list_cmd.add_argument(
        "--label",
        choices=sorted(LABELS),
        help="Filter by label (e.g. missing_pms_runtime)",
    )

    summary = sub.add_parser("summary", help="Print feedback summary")
    summary.add_argument("--status", default="")

    resolve = sub.add_parser(
        "resolve",
        help="Mark a feedback record as resolved with a resolution note",
    )
    resolve.add_argument("--feedback-id", required=True)
    resolve.add_argument("--resolution", required=True)
    resolve.add_argument(
        "--wiki-commit-ref",
        default="",
        help="Optional: git hash, page path, or commit ref linking the patch",
    )

    return parser.parse_args()


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def split_csv(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


def feedback_id(answer_id: str, question: str, correction: str) -> str:
    base = f"{answer_id}\n{question}\n{correction}\n{utc_now()}"
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


def lookup_answer_log(path: Path, answer_id: str) -> dict[str, Any] | None:
    """Return the answer_log record for answer_id, or None if not found."""
    if not path or not Path(path).exists():
        return None
    with Path(path).open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("answer_id") == answer_id:
                return rec
    return None


def cmd_record(args: argparse.Namespace) -> int:
    record = {
        "feedback_id": feedback_id(args.answer_id, args.question, args.correction),
        "created_at": utc_now(),
        "status": "pending",
        "answer_id": args.answer_id,
        "question": args.question,
        "score": args.score,
        "label": args.label,
        "correction": args.correction,
        "expected_answer": args.expected_answer,
        "sources": split_csv(args.sources),
        "affected": split_csv(args.affected),
        "reviewer": args.reviewer,
    }

    # Auto-link the answer_log record if available; warn if the id is unknown.
    answer_log_path = args.answer_log if args.answer_log else None
    if answer_log_path:
        linked = lookup_answer_log(answer_log_path, args.answer_id)
        if linked is not None:
            record["answer_log"] = linked
        else:
            print(
                f"WARN: answer_id={args.answer_id} not found in {answer_log_path}. "
                "Recording feedback without linked answer context.",
            )

    append_record(args.store, record)
    print(f"Recorded feedback {record['feedback_id']} in {args.store}")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    records = load_records(args.store)
    if args.status:
        records = [r for r in records if r.get("status") == args.status]
    if getattr(args, "label", None):
        records = [r for r in records if r.get("label") == args.label]
    records = sorted(records, key=lambda r: r.get("created_at", ""), reverse=True)
    for record in records[: args.limit]:
        print(
            f"{record.get('feedback_id')} | score={record.get('score')} | "
            f"{record.get('label')} | status={record.get('status')} | "
            f"answer={record.get('answer_id')}"
        )
        print(f"  Q: {record.get('question')}")
        correction = record.get("correction") or record.get("expected_answer")
        if correction:
            print(f"  Fix: {correction}")
        affected = ", ".join(record.get("affected", []))
        if affected:
            print(f"  Affected: {affected}")
        resolution = record.get("resolution")
        if resolution:
            print(f"  Resolution: {resolution}")
    return 0


def cmd_resolve(args: argparse.Namespace) -> int:
    """Rewrite the store so the matching feedback_id is marked resolved.

    Idempotent: re-running with the same feedback_id and resolution updates
    the existing resolution text instead of duplicating records.
    """
    records = load_records(args.store)
    found = False
    for record in records:
        if record.get("feedback_id") == args.feedback_id:
            record["status"] = "resolved"
            record["resolution"] = args.resolution
            record["resolved_at"] = utc_now()
            if args.wiki_commit_ref:
                record["wiki_commit_ref"] = args.wiki_commit_ref
            found = True
    if not found:
        print(f"ERROR: feedback_id={args.feedback_id} not found in {args.store}")
        return 1

    args.store.parent.mkdir(parents=True, exist_ok=True)
    with args.store.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    print(f"Resolved feedback {args.feedback_id}")
    return 0


def cmd_summary(args: argparse.Namespace) -> int:
    records = load_records(args.store)
    if args.status:
        records = [r for r in records if r.get("status") == args.status]
    total = len(records)
    score_counts = Counter(str(r.get("score")) for r in records)
    label_counts = Counter(str(r.get("label")) for r in records)
    status_counts = Counter(str(r.get("status")) for r in records)
    avg = 0.0
    if total:
        avg = sum(int(r.get("score", 0)) for r in records) / total

    print(f"Store: {args.store}")
    print(f"Total feedback: {total}")
    print(f"Average score: {avg:.2f}" if total else "Average score: n/a")
    print("By status:")
    for status, count in status_counts.most_common():
        print(f"  {status}: {count}")
    print("By score:")
    for score, count in sorted(score_counts.items()):
        print(f"  {score}: {count}")
    print("Top labels:")
    for label, count in label_counts.most_common(10):
        print(f"  {label}: {count}")
    return 0


def main() -> int:
    args = parse_args()
    if args.command == "record":
        return cmd_record(args)
    if args.command == "list":
        return cmd_list(args)
    if args.command == "summary":
        return cmd_summary(args)
    if args.command == "resolve":
        return cmd_resolve(args)
    raise SystemExit(f"Unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
