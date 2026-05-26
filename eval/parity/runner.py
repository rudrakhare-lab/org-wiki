#!/usr/bin/env python3
"""
Parity eval runner. Loads eval/parity/questions.json, runs each question against
the chosen system, scores against per-question pass criteria, writes a CSV.

Two drivers:
  - api: POST /query against the FastAPI backend. Requires --api-url and --token.
  - cc:  subprocess `claude -p`. Requires the `claude` CLI on PATH and the project
         root as cwd (.mcp.json / CLAUDE.md / .claude/ are auto-loaded).

Usage:
  python eval/parity/runner.py --system api --api-url http://localhost:8000 \
    --token "$CONWO_TOKEN" --out eval_runs/parity_api_$(date +%F).csv

  python eval/parity/runner.py --system cc --out eval_runs/parity_cc_$(date +%F).csv

  # Compare both side-by-side:
  python eval/parity/runner.py --system both --api-url http://localhost:8000 \
    --token "$CONWO_TOKEN" --out eval_runs/parity_both_$(date +%F).csv

Setup requirements are listed under each question's `requires` field; questions
whose setup isn't satisfied are recorded as SKIPPED, not FAIL.

CSV columns:
  question_id, system, category, status, gap, latency_s, notes, response_snippet

Status values: PASS | FAIL | PARTIAL | SKIPPED | MANUAL_REVIEW | ERROR
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

QUESTIONS_FILE = Path(__file__).parent / "questions.json"
REPO_ROOT = Path(__file__).resolve().parents[2]


# ── Setup detection ─────────────────────────────────────────────────────────

def setup_satisfied(requires: list[str]) -> tuple[bool, str]:
    """Return (ok, reason) for each declared prerequisite."""
    for req in requires or []:
        if req == "pms_creds_com":
            if not (os.getenv("PMS_TOKEN_COM") or os.getenv("PMS_TOKEN")):
                return False, "PMS_TOKEN_COM not set"
        elif req == "pms_creds_in":
            if not (os.getenv("PMS_TOKEN_IN") or os.getenv("PMS_TOKEN")):
                return False, "PMS_TOKEN_IN not set"
        elif req == "fresh_jira_ticket":
            return False, "no fresh ticket configured (edit Q3p question text with a real recent ticket key)"
        elif req == "long_comment_ticket":
            return False, "no long-comment ticket configured (edit Q25 question text)"
        elif req == "raw_doc_safe_reach_prd":
            target = REPO_ROOT / "raw" / "modules" / "safe-reach" / "PRD-v2.pdf"
            if not target.exists():
                return False, f"missing {target.relative_to(REPO_ROOT)}"
        else:
            return False, f"unknown requirement: {req}"
    return True, ""


# ── Drivers ─────────────────────────────────────────────────────────────────

@dataclass
class Response:
    text: str
    latency_s: float
    first_token_s: float = -1.0  # only populated for streaming runs
    error: str = ""
    conversation_id: str | None = None


def call_api(
    api_url: str,
    token: str,
    question: str,
    conversation_id: str | None = None,
    timeout_s: int = 120,
) -> Response:
    """POST /query against the FastAPI backend."""
    body = {
        "question": question,
        "mode": "api",
        "server": "com",
    }
    if conversation_id:
        body["conversation_id"] = conversation_id
    req = urllib.request.Request(
        f"{api_url.rstrip('/')}/query",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    start = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        latency = time.monotonic() - start
        return Response(
            text=payload.get("answer_text", ""),
            latency_s=latency,
            conversation_id=payload.get("conversation_id"),
        )
    except urllib.error.HTTPError as exc:
        body_bytes = b""
        try:
            body_bytes = exc.read()
        except Exception:
            pass
        return Response(
            text="",
            latency_s=time.monotonic() - start,
            error=f"HTTP {exc.code}: {body_bytes.decode('utf-8', errors='replace')[:500]}",
        )
    except Exception as exc:
        return Response(text="", latency_s=time.monotonic() - start, error=str(exc))


def call_cc(question: str, timeout_s: int = 300) -> Response:
    """Subprocess `claude -p` from REPO_ROOT."""
    if not shutil.which("claude"):
        return Response(text="", latency_s=0, error="claude binary not on PATH")
    start = time.monotonic()
    try:
        proc = subprocess.run(
            ["claude", "-p", question, "--output-format", "text"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
        latency = time.monotonic() - start
        if proc.returncode != 0:
            return Response(
                text=proc.stdout or "",
                latency_s=latency,
                error=f"claude exited {proc.returncode}: {proc.stderr[:500]}",
            )
        return Response(text=proc.stdout, latency_s=latency)
    except subprocess.TimeoutExpired:
        return Response(text="", latency_s=time.monotonic() - start, error=f"timeout {timeout_s}s")
    except Exception as exc:
        return Response(text="", latency_s=time.monotonic() - start, error=str(exc))


# ── Scoring ─────────────────────────────────────────────────────────────────

def score(question: dict, response: Response) -> tuple[str, str]:
    """
    Return (status, notes).
    status ∈ {PASS, FAIL, PARTIAL, MANUAL_REVIEW, ERROR}.
    """
    if response.error:
        return "ERROR", response.error

    crit = question.get("pass_criteria", {})
    t = crit.get("type")
    text = response.text or ""

    if t == "regex_all":
        missing = [p for p in crit["patterns"] if not re.search(p, text)]
        if missing:
            return "FAIL", f"missing patterns: {missing}"
        return "PASS", ""

    if t == "regex_any":
        for p in crit["patterns"]:
            if re.search(p, text):
                return "PASS", f"matched: {p}"
        return "FAIL", f"no patterns matched: {crit['patterns']}"

    if t == "any_of_n":
        matched = [p for p in crit["patterns"] if re.search(p, text)]
        if len(matched) >= crit["threshold"]:
            return "PASS", f"matched {len(matched)}/{crit['threshold']} required"
        return "FAIL", f"matched {len(matched)}/{crit['threshold']} required"

    if t == "regex_all_and_none":
        missing = [p for p in crit.get("must_match", []) if not re.search(p, text)]
        present = [p for p in crit.get("must_not_match", []) if re.search(p, text)]
        if missing or present:
            return "FAIL", f"missing={missing} forbidden_present={present}"
        return "PASS", ""

    if t == "file_exists":
        present = [p for p in crit["paths"] if (REPO_ROOT / p).exists()]
        if len(present) == len(crit["paths"]):
            if crit.get("cleanup_after"):
                for p in crit["paths"]:
                    try:
                        (REPO_ROOT / p).unlink()
                    except OSError:
                        pass
            return "PASS", f"created {present}"
        return "FAIL", f"missing files: {set(crit['paths']) - set(present)}"

    if t == "shell_check":
        try:
            cmd_out = subprocess.run(
                crit["command"],
                shell=True,
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
                timeout=30,
            )
        except Exception as exc:
            return "ERROR", f"shell_check command failed: {exc}"
        expected = (cmd_out.stdout or "").strip()
        if crit.get("expect_regex"):
            return ("PASS", f"matched expected pattern") if re.search(crit["expect_regex"], text) else ("FAIL", f"missing pattern: {crit['expect_regex']}")
        if crit.get("expect_response_contains_command_output"):
            return ("PASS", f"contains '{expected}'") if expected and expected in text else ("FAIL", f"expected output '{expected}' not in response")
        return "MANUAL_REVIEW", f"shell_check output: {expected[:200]}"

    if t == "latency_first_token":
        # Observation-only — we don't measure first-token in non-streaming mode.
        return "MANUAL_REVIEW", f"observe first-token latency manually (target ≤{crit['max_seconds']}s)"

    if t == "human":
        checklist = "; ".join(crit.get("checklist", []))
        return "MANUAL_REVIEW", f"checklist: {checklist}"

    return "ERROR", f"unknown pass_criteria type: {t}"


# ── Multi-turn handling ─────────────────────────────────────────────────────

def _turns_for_question(question: dict, bank: dict) -> tuple[list[str] | None, str | None]:
    """Resolve the actual list of turn strings for a question, supporting both
    multi_turn shapes:

      - `{"turns": [...]}`     → explicit list of turn strings
      - `{"preceding_question": "QID"}`  → run the prior question first, then
        the current question's main `question` text as a follow-up turn

    Returns (turns_list, None) on success or (None, error_msg) on failure.
    """
    mt = question.get("multi_turn") or {}
    if "turns" in mt:
        return list(mt["turns"]), None
    if "preceding_question" in mt:
        prior_id = mt["preceding_question"]
        prior = next((q for q in bank["questions"] if q.get("id") == prior_id), None)
        if prior is None:
            return None, f"missing_preceding_question_ref: {prior_id}"
        return [prior["question"], question["question"]], None
    return None, "multi_turn block missing both 'turns' and 'preceding_question'"


def run_multi_turn(
    question: dict,
    system: str,
    driver_kwargs: dict,
    bank: dict,
) -> Response:
    """
    Run a multi-turn conversation. API uses conversation_id; CC currently
    only supports the LAST turn (CC doesn't expose session reuse via -p).
    """
    turns, err = _turns_for_question(question, bank)
    if err:
        return Response(text="", latency_s=0, error=err)
    if system == "api":
        conv_id = None
        last_response = Response(text="", latency_s=0)
        for turn_text in turns:
            last_response = call_api(question=turn_text, conversation_id=conv_id, **driver_kwargs)
            if last_response.conversation_id:
                conv_id = last_response.conversation_id
            if last_response.error:
                break
        return last_response
    elif system == "cc":
        # CC has no built-in session reuse with -p. Concatenate turns into one
        # prompt as a best-effort approximation. Mark notes accordingly.
        joined = "\n\nThen, after my last turn, I will say:\n\n".join(
            [f"Turn {i+1}: {t}" for i, t in enumerate(turns)]
        )
        prompt = (
            "I will give you a sequence of turns. Respond ONLY to the LAST turn, "
            "but consider earlier turns as context that has already been "
            "established between us.\n\n" + joined
        )
        return call_cc(prompt)
    else:
        return Response(text="", latency_s=0, error=f"unsupported system: {system}")


# ── Main ────────────────────────────────────────────────────────────────────

def run(args: argparse.Namespace) -> int:
    with open(QUESTIONS_FILE, encoding="utf-8") as f:
        bank = json.load(f)

    rows: list[dict[str, Any]] = []
    systems = ["api", "cc"] if args.system == "both" else [args.system]

    api_kwargs = {"api_url": args.api_url or "", "token": args.token or "", "timeout_s": args.timeout}

    for q in bank["questions"]:
        ok, reason = setup_satisfied(q.get("requires", []))
        # `requires.system` is a per-question driver allowlist. If present,
        # only the listed systems run the question; others get SKIPPED with
        # a clear reason (used by Q31 which is api-only because CC doesn't
        # have wiki_propose_* wired the same way).
        required_systems = q.get("requires.system")
        for system in systems:
            row: dict[str, Any] = {
                "question_id": q["id"],
                "system": system,
                "category": q["category"],
                "status": "",
                "gap": q.get("gap_if_failure") or "",
                "latency_s": "",
                "notes": "",
                "response_snippet": "",
            }
            if required_systems and system not in required_systems:
                row["status"] = "SKIPPED"
                row["notes"] = f"question is {required_systems}-only"
                rows.append(row)
                print(f"  {q['id']:5s} {system:3s} → SKIPPED (not in required_systems={required_systems})")
                continue
            if not ok:
                row["status"] = "SKIPPED"
                row["notes"] = reason
                rows.append(row)
                print(f"  {q['id']:5s} {system:3s} → SKIPPED ({reason})")
                continue

            if system == "api" and not (args.api_url and args.token):
                row["status"] = "SKIPPED"
                row["notes"] = "api driver requires --api-url and --token"
                rows.append(row)
                continue
            if system == "cc" and not shutil.which("claude"):
                row["status"] = "SKIPPED"
                row["notes"] = "claude CLI not on PATH"
                rows.append(row)
                continue

            # Dispatch
            if "multi_turn" in q:
                resp = run_multi_turn(
                    q, system,
                    api_kwargs if system == "api" else {"timeout_s": args.timeout},
                    bank,
                )
            else:
                if system == "api":
                    resp = call_api(question=q["question"], **api_kwargs)
                else:
                    resp = call_cc(question=q["question"], timeout_s=args.timeout)

            status, notes = score(q, resp)
            row["status"] = status
            row["latency_s"] = f"{resp.latency_s:.2f}" if resp.latency_s else ""
            row["notes"] = notes
            row["response_snippet"] = (resp.text or resp.error or "")[:300].replace("\n", " ")
            rows.append(row)
            tag = {
                "PASS": "✅", "FAIL": "❌", "PARTIAL": "🟡",
                "SKIPPED": "—", "MANUAL_REVIEW": "👁", "ERROR": "⚠️",
            }.get(status, "?")
            print(f"  {q['id']:5s} {system:3s} {tag} {status:13s} ({resp.latency_s:.1f}s) {notes[:80]}")

    # Write CSV
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "question_id", "system", "category", "status", "gap",
            "latency_s", "notes", "response_snippet",
        ])
        writer.writeheader()
        writer.writerows(rows)

    # Summary
    print(f"\nWrote {len(rows)} rows to {out_path}")
    summary = {}
    for r in rows:
        key = (r["system"], r["status"])
        summary[key] = summary.get(key, 0) + 1
    for system in systems:
        passed = summary.get((system, "PASS"), 0)
        failed = summary.get((system, "FAIL"), 0)
        partial = summary.get((system, "PARTIAL"), 0)
        manual = summary.get((system, "MANUAL_REVIEW"), 0)
        skipped = summary.get((system, "SKIPPED"), 0)
        errored = summary.get((system, "ERROR"), 0)
        total = passed + failed + partial + manual + errored
        scored_total = total if total > 0 else 1
        print(
            f"\n{system.upper():3s}: {passed} PASS / {failed} FAIL / {partial} PARTIAL / "
            f"{manual} MANUAL_REVIEW / {errored} ERROR / {skipped} SKIPPED"
        )
        print(f"     auto-scored: {passed}/{scored_total} = {100*passed/scored_total:.0f}% pass")

    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--system", choices=["api", "cc", "both"], required=True)
    p.add_argument("--api-url", help="FastAPI base URL, e.g. http://localhost:8000")
    p.add_argument("--token", help="Bearer token for /query auth")
    p.add_argument("--timeout", type=int, default=180, help="Per-question timeout in seconds")
    p.add_argument("--out", required=True, help="Output CSV path")
    args = p.parse_args()

    if args.system in ("api", "both") and not (args.api_url and args.token):
        print("Note: --api-url and --token are needed for api driver; API questions will be SKIPPED.", file=sys.stderr)
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
