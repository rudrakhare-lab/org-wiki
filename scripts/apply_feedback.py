#!/usr/bin/env python3
"""
apply_feedback.py — Triage pending feedback and convert corrections into
durable wiki patches.

The pipeline:
  1. Load pending feedback records (score 1-3 by default; score 4-5 optional)
  2. For each: resolve the patch target(s) — explicit `affected`, else infer
     from sources in the linked answer_log, else from the affected ticket /
     property tokens in `correction`
  3. Generate a patch plan (markdown summary)
  4. If --apply: write a "Feedback Notes" block into the affected wiki page(s),
     append wiki/log.md, and mark the feedback as resolved via record_feedback.py
  5. If a label appears 3+ times across pending + resolved feedback, print a
     CLAUDE.md guardrail recommendation (never auto-writes to CLAUDE.md).

The default mode is --dry-run; --apply must be set explicitly to mutate files.

Idempotency: each patch carries an HTML comment marker `<!-- feedback:ID -->`.
Re-applying the same feedback_id is a no-op (detected on the marker).

Examples:
    venv/bin/python scripts/apply_feedback.py --feedback-id abc123def456
    venv/bin/python scripts/apply_feedback.py --all-pending --dry-run
    venv/bin/python scripts/apply_feedback.py --feedback-id abc123 --apply
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_FEEDBACK_STORE = ROOT / "raw" / "feedback" / "answer_feedback.jsonl"
DEFAULT_ANSWER_LOG = ROOT / "raw" / "feedback" / "answer_log.jsonl"
WIKI_ROOT = ROOT / "wiki"
WIKI_LOG = WIKI_ROOT / "log.md"
KNOWN_PATTERNS = WIKI_ROOT / "known-answer-patterns.md"

# Label → preferred patch target path (relative to WIKI_ROOT). The router uses
# this if explicit `affected` is not provided and the answer_log sources do
# not resolve to a single page.
LABEL_PATCH_HINTS = {
    "wrong_config": "configs",            # wiki/configs/<module>.md
    "missing_jira": None,                  # use answer_log.sources.wiki
    "outdated": None,                      # use affected page
    "missing_pms_runtime": "configs",      # config page OR docs/live-config-debug.md
    "wrong_scope": "configs",              # config page (BUID/OFFICEID/ROLE scope)
    "conflicting_evidence": None,          # affected page (add conflict block)
    "missing_runtime_context": "configs",
    "wrong": None,
    "incomplete": None,
    "unclear": None,
    "partially_correct": None,
    "correct": None,
}

GUARDRAIL_THRESHOLD = 3  # 3+ same-label feedbacks → suggest CLAUDE.md guardrail


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)

    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--feedback-id", help="Apply one specific feedback record")
    target.add_argument(
        "--all-pending",
        action="store_true",
        help="Apply all pending records with score 1-3 (or up to --max-score)",
    )

    parser.add_argument(
        "--max-score",
        type=int,
        default=3,
        help="Maximum score eligible for auto-patch (default: 3). Score 4-5 are "
        "considered for known-answer-patterns.md good examples only.",
    )

    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Print patch plan only (default).",
    )
    mode.add_argument(
        "--apply",
        action="store_true",
        help="Write patches to wiki/, append log, mark feedback resolved.",
    )

    parser.add_argument(
        "--feedback-store",
        type=Path,
        default=DEFAULT_FEEDBACK_STORE,
    )
    parser.add_argument(
        "--answer-log",
        type=Path,
        default=DEFAULT_ANSWER_LOG,
    )

    args = parser.parse_args()
    # `--apply` overrides default dry-run
    if args.apply:
        args.dry_run = False
    return args


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def today_date() -> str:
    return dt.datetime.now(dt.timezone.utc).date().isoformat()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


# ---------- target resolution -----------------------------------------------

WIKI_PATH_RE = re.compile(r"(wiki/[A-Za-z0-9_\-/]+\.md)")
CONFIG_TOKEN_RE = re.compile(r"\b([A-Z][A-Z0-9_-]+):([A-Za-z][A-Za-z0-9_]+)")


def resolve_targets(feedback: dict[str, Any]) -> list[Path]:
    """Determine which wiki page(s) to patch for this feedback record.

    Priority order:
      1. `affected` field — explicit user signal (strongest)
      2. answer_log.sources.wiki — pages already cited in the answer
      3. PMS config tokens in `affected` or correction (e.g. VISITOR:foo
         → wiki/configs/visitor-management.md)
      4. Label hint — e.g. wrong_config defaults to wiki/configs/
    """
    targets: list[Path] = []

    # 1. Explicit affected pages
    for item in feedback.get("affected", []) or []:
        wiki_path = _extract_wiki_path(item)
        if wiki_path:
            targets.append(wiki_path)
        else:
            # Config token like VISITOR:propName → map service → config page
            cfg = _extract_config_target(item)
            if cfg:
                targets.append(cfg)

    # 2. answer_log cited wiki pages
    if not targets:
        log = feedback.get("answer_log") or {}
        for path_str in (log.get("sources") or {}).get("wiki", []) or []:
            wiki_path = _extract_wiki_path(path_str)
            if wiki_path:
                targets.append(wiki_path)

    # 3. Config tokens in correction text
    if not targets:
        for token in CONFIG_TOKEN_RE.findall(feedback.get("correction", "") or ""):
            service = token[0]
            cfg = _config_page_for_service(service)
            if cfg:
                targets.append(cfg)

    # Deduplicate preserving order
    seen: set[Path] = set()
    unique: list[Path] = []
    for t in targets:
        if t not in seen:
            unique.append(t)
            seen.add(t)
    return unique


def _extract_wiki_path(token: str) -> Path | None:
    """If token looks like a wiki page path, return the absolute Path."""
    if not token:
        return None
    token = token.strip()
    m = WIKI_PATH_RE.search(token)
    if m:
        candidate = ROOT / m.group(1)
        return candidate if candidate.exists() else candidate  # return even if absent; caller handles
    return None


def _extract_config_target(token: str) -> Path | None:
    """Tokens like VISITOR:kioskRequireOTPBeforeRegister → wiki/configs/visitor-management.md"""
    m = CONFIG_TOKEN_RE.search(token or "")
    if not m:
        return None
    service = m.group(1)
    return _config_page_for_service(service)


SERVICE_TO_CONFIG_PAGE = {
    "VISITOR": "configs/visitor-management.md",
    "MEETING_ROOMS": "configs/meeting-rooms.md",
    "BOOKING-RULE-ENGINE": "configs/booking-rule-engine.md",
    "WIS-SEAT-BOOKING": "configs/wis-seat-booking.md",
    "GUARD-APP": "configs/guard-app.md",
    "EMAIL-EMP-EXPERIENCE": "configs/emp-experience-email.md",
    "EMP-EXP-INTERNAL-CONFIG": "configs/emp-experience-internal.md",
    "EMP-EXP-COMMON-CONFIG": "configs/emp-experience-common.md",
    "PROJECT-MANAGEMENT-SERVICE": "configs/pms.md",
    "PMS": "configs/pms.md",
}


def _config_page_for_service(service: str) -> Path | None:
    rel = SERVICE_TO_CONFIG_PAGE.get(service.upper())
    if not rel:
        return None
    return WIKI_ROOT / rel


# ---------- patch generation ------------------------------------------------

FEEDBACK_NOTES_HEADER = "## Feedback Notes"


def render_patch_block(feedback: dict[str, Any]) -> str:
    """The markdown block inserted into the affected wiki page."""
    fid = feedback["feedback_id"]
    score = feedback.get("score", "?")
    label = feedback.get("label", "?")
    correction = (feedback.get("correction") or "").strip() or "(no correction text)"
    sources = feedback.get("sources", []) or []
    affected = feedback.get("affected", []) or []
    answer_id = feedback.get("answer_id", "")
    date = today_date()

    src_line = ", ".join(sources) if sources else "—"
    aff_line = ", ".join(affected) if affected else "—"

    lines = [
        f"<!-- feedback:{fid} -->",
        f"- **{date}** — score `{score}` · label `{label}` · answer `{answer_id}` · feedback `{fid}`",
        f"    - Correction: {correction}",
        f"    - Sources cited: {src_line}",
        f"    - Affected: {aff_line}",
        "",
    ]
    return "\n".join(lines)


def patch_already_applied(page_text: str, feedback_id: str) -> bool:
    return f"<!-- feedback:{feedback_id} -->" in page_text


def insert_feedback_block(page_text: str, block: str) -> str:
    """Insert the block under a '## Feedback Notes' section (creating it if missing).

    The section lives at the bottom of the page so we never disrupt existing
    content. New blocks are appended within the section in chronological order.
    """
    if FEEDBACK_NOTES_HEADER in page_text:
        # Append the new block right after the header (above any existing entries)
        # so the most recent feedback appears at the top of the list.
        marker = FEEDBACK_NOTES_HEADER
        idx = page_text.index(marker) + len(marker)
        return page_text[: idx] + "\n\n" + block + page_text[idx:]

    # Section absent — append at end of file
    trailing_newline = "" if page_text.endswith("\n") else "\n"
    return f"{page_text}{trailing_newline}\n---\n\n{FEEDBACK_NOTES_HEADER}\n\n{block}"


# ---------- plan + apply ----------------------------------------------------


def build_plan(
    feedback: dict[str, Any],
    targets: list[Path],
) -> dict[str, Any]:
    return {
        "feedback_id": feedback["feedback_id"],
        "score": feedback.get("score"),
        "label": feedback.get("label"),
        "status": feedback.get("status"),
        "answer_id": feedback.get("answer_id"),
        "question": (feedback.get("question") or "")[:200],
        "targets": [str(t.relative_to(ROOT)) if t.is_relative_to(ROOT) else str(t) for t in targets],
        "patch_block": render_patch_block(feedback),
        "patch_strategy": "append Feedback Notes section (idempotent via HTML marker)",
    }


def print_plan(plan: dict[str, Any]) -> None:
    print("─" * 72)
    print(f"feedback_id : {plan['feedback_id']}")
    print(f"score       : {plan['score']}  ·  label: {plan['label']}  ·  status: {plan['status']}")
    print(f"answer_id   : {plan['answer_id']}")
    print(f"question    : {plan['question']}")
    print(f"targets     : {', '.join(plan['targets']) if plan['targets'] else '(none resolved)'}")
    print(f"strategy    : {plan['patch_strategy']}")
    print("patch block:")
    for line in plan["patch_block"].rstrip().splitlines():
        print(f"    {line}")
    print()


def apply_one(feedback: dict[str, Any], targets: list[Path]) -> tuple[list[Path], list[Path]]:
    """Write the feedback block into each target. Returns (written, skipped)."""
    written: list[Path] = []
    skipped: list[Path] = []
    block = render_patch_block(feedback)
    for target in targets:
        if not target.exists():
            print(f"  WARN: target page does not exist: {target.relative_to(ROOT)}")
            skipped.append(target)
            continue
        page_text = target.read_text(encoding="utf-8")
        if patch_already_applied(page_text, feedback["feedback_id"]):
            print(f"  skip (already applied): {target.relative_to(ROOT)}")
            skipped.append(target)
            continue
        new_text = insert_feedback_block(page_text, block)
        target.write_text(new_text, encoding="utf-8")
        print(f"  patched: {target.relative_to(ROOT)}")
        written.append(target)
    return written, skipped


def append_wiki_log(feedback: dict[str, Any], written: list[Path]) -> None:
    """Append a one-paragraph wiki/log.md entry for this apply operation."""
    if not WIKI_LOG.exists():
        return
    timestamp = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M")
    pages = ", ".join(f"[[{p.relative_to(WIKI_ROOT).with_suffix('')}]]" for p in written)
    entry_lines = [
        f"## [{timestamp}] feedback-apply | {feedback.get('label', '?')} — feedback {feedback['feedback_id']}",
        "",
        f"- Score `{feedback.get('score')}` feedback applied as Feedback Notes block.",
        f"- Patched: {pages or '(none — targets did not exist)'}",
        f"- Answer ID: `{feedback.get('answer_id')}`",
        f"- Correction summary: {(feedback.get('correction') or '').strip()[:200]}",
        "",
        "---",
        "",
    ]
    existing = WIKI_LOG.read_text(encoding="utf-8")
    # Insert after the header / first '---', not at top, to preserve structure.
    marker = "---\n"
    first_idx = existing.find(marker)
    if first_idx < 0:
        WIKI_LOG.write_text(existing + "\n" + "\n".join(entry_lines), encoding="utf-8")
        return
    insertion = "\n".join(entry_lines)
    new = existing[: first_idx + len(marker)] + "\n" + insertion + existing[first_idx + len(marker):]
    WIKI_LOG.write_text(new, encoding="utf-8")


def mark_resolved(args: argparse.Namespace, feedback: dict[str, Any], written: list[Path]) -> None:
    """Call record_feedback.py resolve for idempotency and shared store handling."""
    if not written:
        return
    page_ref = ",".join(str(p.relative_to(ROOT)) for p in written)
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "record_feedback.py"),
        "--store",
        str(args.feedback_store),
        "resolve",
        "--feedback-id",
        feedback["feedback_id"],
        "--resolution",
        f"Applied via apply_feedback.py — patched {page_ref}",
        "--wiki-commit-ref",
        page_ref,
    ]
    subprocess.run(cmd, check=True)


def label_counts(records: list[dict[str, Any]]) -> Counter:
    return Counter(r.get("label", "") for r in records if r.get("label"))


def maybe_recommend_guardrail(records: list[dict[str, Any]], label: str) -> None:
    counts = label_counts(records)
    n = counts.get(label, 0)
    if n >= GUARDRAIL_THRESHOLD:
        print()
        print("─" * 72)
        print(f"⚠️  Systematic pattern: label `{label}` appears {n} times across feedback.")
        print(
            "Recommendation: add a CLAUDE.md guardrail. Suggested locations:"
        )
        print("  - Section 5 (QUERY Workflow) — add a step to check this before answering")
        print("  - Section 12 (Live Config Debug) — if scope/runtime related")
        print(
            "Edit CLAUDE.md manually — apply_feedback.py never writes guardrails "
            "automatically."
        )
        print("─" * 72)


# ---------- main ------------------------------------------------------------


def hydrate_answer_log(records: list[dict[str, Any]], answer_log_path: Path) -> None:
    """Attach answer_log records in-place if not already present."""
    if not answer_log_path.exists():
        return
    log_index = {r["answer_id"]: r for r in load_jsonl(answer_log_path) if r.get("answer_id")}
    for r in records:
        if "answer_log" in r:
            continue
        aid = r.get("answer_id")
        if aid and aid in log_index:
            r["answer_log"] = log_index[aid]


def main() -> int:
    args = parse_args()

    records = load_jsonl(args.feedback_store)
    if not records:
        print(f"No feedback records found in {args.feedback_store}")
        return 0

    hydrate_answer_log(records, args.answer_log)

    # Select records to process
    if args.feedback_id:
        target_records = [r for r in records if r.get("feedback_id") == args.feedback_id]
        if not target_records:
            print(f"ERROR: feedback_id={args.feedback_id} not found")
            return 1
    else:
        target_records = [
            r
            for r in records
            if r.get("status") == "pending"
            and (r.get("score") or 0) <= args.max_score
            and (r.get("score") or 0) >= 1
        ]
        if not target_records:
            print(f"No pending feedback with score 1-{args.max_score}.")
            return 0

    mode_str = "APPLY (writing files)" if not args.dry_run else "DRY-RUN (no writes)"
    print(f"apply_feedback.py — {mode_str}")
    print(f"records to process: {len(target_records)}")
    print()

    written_count = 0
    skipped_count = 0
    seen_labels: set[str] = set()

    for feedback in target_records:
        targets = resolve_targets(feedback)
        plan = build_plan(feedback, targets)
        print_plan(plan)
        seen_labels.add(feedback.get("label", ""))

        if not targets:
            print("  ⚠️  No patch targets resolved — feedback recorded but not actionable.")
            print("  Suggest: add `--affected wiki/...md` when recording feedback, or")
            print("  set sources on the answer_log entry before recording feedback.")
            print()
            continue

        if args.dry_run:
            print("  (dry-run: no writes)")
            print()
            continue

        written, _skipped = apply_one(feedback, targets)
        if written:
            append_wiki_log(feedback, written)
            mark_resolved(args, feedback, written)
            written_count += len(written)
        else:
            skipped_count += 1
        print()

    # Suggest guardrails for systematic patterns
    for label in seen_labels:
        if label:
            maybe_recommend_guardrail(records, label)

    if args.dry_run:
        print(f"Dry-run complete. Use --apply to write {len(target_records)} record(s).")
    else:
        print(f"Apply complete. Patched files: {written_count}. Skipped: {skipped_count}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
