#!/usr/bin/env python3
"""
jira_daily_sync.py — Daily Jira delta + classification orchestrator.

Target install path: scripts/jira_daily_sync.py
(scripts/ is outside the backend reload path — safe to land directly.)

──────────────────────────────────────────────────────────────────────────────
CRONTAB ENTRY (production install)
──────────────────────────────────────────────────────────────────────────────

# Daily Jira delta sync + classification (2 AM local time)
# 0 2 * * * cd /Users/rudrakhare/Desktop/my-wiki/org-wiki && \
#   ./venv/bin/python scripts/jira_daily_sync.py >> logs/jira_sync.log 2>&1

──────────────────────────────────────────────────────────────────────────────
MANUAL TEST COMMANDS
──────────────────────────────────────────────────────────────────────────────

    # Full sync + classification:
    ./venv/bin/python scripts/jira_daily_sync.py

    # Skip Jira sync, only re-classify recently-updated tickets:
    ./venv/bin/python scripts/jira_daily_sync.py --classification-only

    # Custom delta window (days back to look for classification):
    ./venv/bin/python scripts/jira_daily_sync.py --classification-days 7

    # Verbose: print structured log lines to stderr too:
    ./venv/bin/python scripts/jira_daily_sync.py --verbose

──────────────────────────────────────────────────────────────────────────────
TWO STAGES
──────────────────────────────────────────────────────────────────────────────

  Stage 1 — sync     ./venv/bin/python scripts/jira_sync.py --incremental
                     (writes raw/jira/sync.log internally; we capture the
                      summary line from stdout/stderr)

  Stage 2 — classify ./venv/bin/python scripts/classify_jira.py --delta N --yes
                     (default N = 2; covers tickets the sync touched in
                      the last 2 days, plus any unclassified tickets)

──────────────────────────────────────────────────────────────────────────────
LOG FORMAT (appended to logs/jira_sync.log)
──────────────────────────────────────────────────────────────────────────────

    [2026-05-29T02:00:00Z] STAGE_START sync
    [2026-05-29T02:00:14Z] STAGE_OK sync — fetched 47, new 12, updated 35
    [2026-05-29T02:00:14Z] STAGE_START classify
    [2026-05-29T02:00:23Z] STAGE_OK classify — 47 tickets, $0.04
    [2026-05-29T02:00:23Z] DONE total=23s cost=$0.04

──────────────────────────────────────────────────────────────────────────────
EXIT CODES
──────────────────────────────────────────────────────────────────────────────

    0  both stages succeeded
    1  sync failed (Jira API issue)
    2  classification failed
    3  both failed
    10 environment misconfiguration (missing ANTHROPIC_API_KEY etc)
    11 disk full or unwritable logs/ directory
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
VENV_PY = REPO / "venv" / "bin" / "python"
LOG_DIR = REPO / "logs"
LOG_FILE = LOG_DIR / "jira_sync.log"
SYNC_SCRIPT = HERE / "jira_sync.py"
CLASSIFY_SCRIPT = HERE / "classify_jira.py"

# Stage timeouts (seconds) — tunable. Stage 1 typically <60s; Stage 2 depends
# on delta size (47 tickets ≈ 30s, 500 tickets ≈ 6min).
SYNC_TIMEOUT_S = 600          # 10 minutes for incremental sync
CLASSIFY_TIMEOUT_S = 3600     # 60 minutes (handles backlog if cron missed days)


# ── Logging (own format, separate from jira_sync.py's JSON-lines log) ─────────

def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _ensure_log_dir() -> None:
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        # Disk full / permission — try to surface to stderr at least.
        print(f"FATAL: could not create {LOG_DIR}: {exc}", file=sys.stderr)
        sys.exit(11)


def log(line: str, *, verbose: bool = False) -> None:
    """Append one timestamped line to logs/jira_sync.log; mirror to stderr if verbose.

    Graceful degradation: if the log file becomes unwritable mid-run, we still
    print to stderr so the operator sees the partial output.
    """
    stamped = f"[{_ts()}] {line}"
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as fh:
            fh.write(stamped + "\n")
    except OSError as exc:
        print(f"WARN: failed to write log line ({exc}): {stamped}", file=sys.stderr)
    if verbose:
        print(stamped, file=sys.stderr)


# ── Stage runners ─────────────────────────────────────────────────────────────

def run_sync_stage(verbose: bool) -> tuple[bool, str]:
    """
    Returns (success, summary). summary is the human-readable counts line
    extracted from the sync script's output, or empty string on failure.
    """
    log("STAGE_START sync", verbose=verbose)
    if not SYNC_SCRIPT.exists():
        log("STAGE_FAIL sync — scripts/jira_sync.py not found", verbose=verbose)
        return False, ""

    try:
        proc = subprocess.run(
            [str(VENV_PY), str(SYNC_SCRIPT), "--incremental"],
            cwd=str(REPO),
            capture_output=True,
            text=True,
            timeout=SYNC_TIMEOUT_S,
        )
    except subprocess.TimeoutExpired:
        log(f"STAGE_FAIL sync — timed out after {SYNC_TIMEOUT_S}s", verbose=verbose)
        return False, ""
    except OSError as exc:
        log(f"STAGE_FAIL sync — could not spawn: {exc}", verbose=verbose)
        return False, ""

    # Parse the sync output for the "ALL DONE: fetched=X new=Y updated=Z unchanged=W" line.
    # The script logs JSON to a file; the human-readable line lands on stderr.
    summary = ""
    combined = (proc.stdout or "") + (proc.stderr or "")
    m = re.search(r"ALL DONE:\s*fetched=(\d+)\s+new=(\d+)\s+updated=(\d+)\s+unchanged=(\d+)", combined)
    if m:
        summary = f"fetched={m.group(1)}, new={m.group(2)}, updated={m.group(3)}, unchanged={m.group(4)}"

    if proc.returncode != 0:
        log(f"STAGE_FAIL sync — exit {proc.returncode}: {summary or 'no summary captured'}", verbose=verbose)
        # Surface stderr tail so the operator can diagnose
        tail = (proc.stderr or "").splitlines()[-5:]
        for line in tail:
            log(f"  sync.stderr: {line}", verbose=verbose)
        return False, summary

    log(f"STAGE_OK sync — {summary or '(no count parsed)'}", verbose=verbose)
    return True, summary


def run_classify_stage(days: int, verbose: bool) -> tuple[bool, str]:
    """
    Returns (success, summary). summary is "N tickets, $X.XX" parsed from
    classify_jira.py's SUMMARY block.
    """
    log("STAGE_START classify", verbose=verbose)
    if not CLASSIFY_SCRIPT.exists():
        log("STAGE_FAIL classify — scripts/classify_jira.py not found", verbose=verbose)
        return False, ""

    try:
        proc = subprocess.run(
            [str(VENV_PY), str(CLASSIFY_SCRIPT), "--delta", str(int(days)), "--yes"],
            cwd=str(REPO),
            capture_output=True,
            text=True,
            timeout=CLASSIFY_TIMEOUT_S,
        )
    except subprocess.TimeoutExpired:
        log(f"STAGE_FAIL classify — timed out after {CLASSIFY_TIMEOUT_S}s", verbose=verbose)
        return False, ""
    except OSError as exc:
        log(f"STAGE_FAIL classify — could not spawn: {exc}", verbose=verbose)
        return False, ""

    # Parse classify_jira's summary block. Looks for "Tickets classified : N" and "Total cost : $X.XX"
    combined = (proc.stdout or "") + (proc.stderr or "")
    m_tickets = re.search(r"Tickets classified\s*:\s*(\d+)", combined)
    m_cost = re.search(r"Total cost\s*:\s*\$([0-9.]+)", combined)
    n_tickets = m_tickets.group(1) if m_tickets else "?"
    cost = m_cost.group(1) if m_cost else "?"
    summary = f"{n_tickets} tickets, ${cost}"

    if proc.returncode != 0:
        log(f"STAGE_FAIL classify — exit {proc.returncode}: {summary}", verbose=verbose)
        tail = (proc.stderr or "").splitlines()[-5:]
        for line in tail:
            log(f"  classify.stderr: {line}", verbose=verbose)
        return False, summary

    log(f"STAGE_OK classify — {summary}", verbose=verbose)
    return True, summary


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="Daily Jira delta sync + classification")
    parser.add_argument(
        "--classification-only",
        action="store_true",
        help="Skip Stage 1 (Jira sync). Useful for re-classifying after a "
             "classifier_version bump without re-fetching from Jira.",
    )
    parser.add_argument(
        "--classification-days",
        type=int,
        default=2,
        help="Pass --delta N to classify_jira.py. Default 2 (yesterday + today).",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Mirror log lines to stderr as they're written.",
    )
    args = parser.parse_args()

    _ensure_log_dir()

    # ── Environment check (fail fast) ─────────────────────────────────────────
    # The Anthropic SDK reads ANTHROPIC_API_KEY from env; if absent, classify
    # would fail mid-batch. Cheaper to fail at the top.
    # We DON'T need to load .env here — classify_jira.py does that itself
    # via the calling shell + dotenv. But we do a sanity check.
    if not os.environ.get("ANTHROPIC_API_KEY"):
        # Try to load .env (in case the cron environment is bare)
        env_path = REPO / ".env"
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                if line.startswith("ANTHROPIC_API_KEY="):
                    key = line.split("=", 1)[1].strip().strip('"').strip("'")
                    if key:
                        os.environ["ANTHROPIC_API_KEY"] = key
                    break
    if not os.environ.get("ANTHROPIC_API_KEY"):
        log("FATAL: ANTHROPIC_API_KEY missing from environment and .env", verbose=True)
        return 10

    start = time.time()
    sync_ok = True
    classify_ok = True
    sync_summary = ""
    classify_summary = ""

    if args.classification_only:
        log("MODE classification_only — skipping Stage 1", verbose=args.verbose)
    else:
        sync_ok, sync_summary = run_sync_stage(verbose=args.verbose)

    # Run classify even if sync failed — there may be unclassified tickets from
    # a prior partial run that we can still process. Idempotent skip handles it.
    classify_ok, classify_summary = run_classify_stage(args.classification_days, verbose=args.verbose)

    elapsed = time.time() - start
    cost = "?"
    m_cost = re.search(r"\$([0-9.]+)", classify_summary)
    if m_cost:
        cost = m_cost.group(1)

    log(f"DONE total={elapsed:.0f}s cost=${cost} sync_ok={sync_ok} classify_ok={classify_ok}",
        verbose=args.verbose)

    # Exit code: 0=both ok, 1=sync fail, 2=classify fail, 3=both
    code = 0
    if not sync_ok:     code += 1
    if not classify_ok: code += 2
    return code


if __name__ == "__main__":
    sys.exit(main())
