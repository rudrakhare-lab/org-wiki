#!/usr/bin/env python3
"""
Ask a fixed bank of 60 cafeteria-property questions to a model and save answers.

This script uses an OpenAI-compatible Chat Completions API.

Environment variables:
  MODEL_API_KEY   (required)
  MODEL_BASE_URL  (optional, default: https://api.openai.com)

Usage:
  python scripts/eval_questions.py \
    --model gpt-4.1-mini \
    --out-dir eval_runs/cafeteria_eval

  # With optional comparison against expected answers
  python scripts/eval_questions.py \
    --model gpt-4.1-mini \
    --out-dir eval_runs/cafeteria_eval \
    --gold-file eval_runs/cafeteria_gold.json

Gold file format (JSON):
{
  "1": "enableSeparateMealOption",
  "2": "False",
  ...
}
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import difflib
import json
import os
import sys
import time
from pathlib import Path
from typing import Any
from urllib import error as urlerror
from urllib import request as urlrequest


QUESTIONS: list[str] = [
    "What property enables meal-only booking?",
    "What is the default value of enableSeparateMealOption?",
    "Which existing master property must be enabled along with enableSeparateMealOption?",
    "What is the property used for meal booking creation cut-off?",
    "What is the property used for meal booking edit/cancel cut-off?",
    "What is the default value of mealCancelCutoffInMinutes?",
    "What does enableMealBookingNudge do and where is it maintained?",
    "What property configures meal options on kiosk (Scan Meal QR, View Today’s Order)?",
    "What property restricts employees to their profile office cafeterias?",
    "What property enables the Configure Kiosk button on meal dashboard?",
    "What property enables meal fallback flow?",
    "What property controls meal QR print button?",
    "What property excludes meal-only bookings from active booking count?",
    "What property allows only one meal booking per employee per day?",
    "What property defines final status of meal booking?",
    "What property configures search filters in vendor kiosk View Today’s Order?",
    "What property configures meal notifications?",
    "What property enables go-paperless on kiosk?",
    "What property enables multi-selection of meal items in a category?",
    "If enableSeparateMealOption=true but mealBookingEnabled=false, what should happen?",
    "If both enableSeparateMealOption=true and mealBookingEnabled=true, what UI change should user see?",
    "If showEmployeeProfileOfficeOnly=true, can a user book meal in cross-office cafeteria?",
    "If excludeMealOnlyBookingsFromActiveBookingCount=true, do adhoc meal bookings affect active booking limits?",
    "If enableMealConfigureKiosk=false, should Configure Kiosk button be visible?",
    "If enableMealBookingNudge=true, where should this be effective (BUID vs Office)?",
    "If enableGoPaperless=true, what operational behavior should kiosk support?",
    "If enableMultiMealSelect=false, how should category item selection behave?",
    "Explain how mealCancelCutoffInMinutes = -1440 works in plain language.",
    "Is mealCancelCutoffInMinutes calculated from booking start time or from midnight of booking day?",
    "If booking is for tomorrow and mealCancelCutoffInMinutes=-1440, by when can user cancel?",
    "Which property controls booking creation cutoff vs cancellation cutoff?",
    "If mealCutoffInMinutes is strict but cancel cutoff is relaxed, which actions are blocked first?",
    "Should creation and edit both use mealCutoffInMinutes per notes?",
    "What is the expected type of enableMealFallbackFlow?",
    "What is the expected type of allowedMealBookingPerEmployee?",
    "What is the expected type of mealCheckinOptions?",
    "What is the expected type of mealFinalStage?",
    "What is the expected type of searchCriteriaVendorKiosk?",
    "Is allowedMealBookingPerEmployee truly boolean or integer? Identify inconsistency in notes.",
    "Is enableMealQrPrintButtonenableMealQrPrint one property or typo/composite? Explain.",
    "Are there duplicate mentions of showEmployeeProfileOfficeOnly? How should docs be normalized?",
    "A customer wants meal-only booking and those bookings excluded from active booking count. Which properties and values?",
    "A customer wants only one meal per day and no cross-office booking. Which properties configure this?",
    "A customer wants kiosk search by employee email and order ID only. What property value should be set?",
    "A customer wants to disable QR scanning and allow only View Today’s Order. Which property controls that?",
    "A customer wants paperless mode + no print badge + fallback enabled. Which properties apply?",
    "A customer wants nudges only in one office, not all offices. Which property scope matters?",
    "A customer says Configure Kiosk button is missing. What property should be checked first?",
    "A customer says meal booking appears but meal-only option does not. What two-property dependency should be validated?",
    "A customer says meal-only bookings are reducing active booking quota unexpectedly. Which property controls this behavior?",
    "Identify all ambiguous or inconsistent statements in this property spec.",
    "Which properties are marked existing vs new and why does that matter for rollout?",
    "Which properties are BUID-level vs Office-level, and where can wrong scope cause bugs?",
    "Are creation/edit/cancel cutoff rules clearly separated or partially conflicting?",
    "What doc corrections should be made before engineering implementation?",
    "Create a normalized table: property_name | type | default | scope | purpose | depends_on.",
    "Generate a JSON schema for all these properties.",
    "Generate validation rules and error messages for each property.",
    "Produce a rollout checklist for enabling meal-only booking safely.",
    "Produce a QA test matrix with positive/negative test cases for each property.",
]


DEFAULT_SYSTEM_PROMPT = (
    "You are a product configuration analyst. Answer concisely and accurately. "
    "If information is missing or contradictory, explicitly call that out."
)


def call_model(
    *,
    base_url: str,
    api_key: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float,
    timeout_s: int,
) -> tuple[str, dict[str, Any]]:
    url = f"{base_url.rstrip('/')}/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "temperature": temperature,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }
    body = json.dumps(payload).encode("utf-8")
    req = urlrequest.Request(url, data=body, headers=headers, method="POST")
    try:
        with urlrequest.urlopen(req, timeout=timeout_s) as resp:
            raw_text = resp.read().decode("utf-8")
            data = json.loads(raw_text)
    except urlerror.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code}: {detail}") from e
    except urlerror.URLError as e:
        raise RuntimeError(f"Network error: {e}") from e

    content = data["choices"][0]["message"]["content"]
    return content, data


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def timestamp_slug() -> str:
    return dt.datetime.now().strftime("%Y%m%d_%H%M%S")


def load_gold(path: Path) -> dict[str, str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    out: dict[str, str] = {}
    for k, v in data.items():
        out[str(k)] = str(v)
    return out


def similarity(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


def main() -> int:
    ap = argparse.ArgumentParser(description="Run 60-question model eval.")
    ap.add_argument("--model", required=True, help="Model name for OpenAI-compatible endpoint")
    ap.add_argument("--out-dir", default=f"eval_runs/cafeteria_eval_{timestamp_slug()}")
    ap.add_argument("--base-url", default=os.getenv("MODEL_BASE_URL", "https://api.openai.com"))
    ap.add_argument("--api-key", default=os.getenv("MODEL_API_KEY", ""))
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--sleep-ms", type=int, default=150)
    ap.add_argument("--timeout-s", type=int, default=90)
    ap.add_argument("--system-prompt", default=DEFAULT_SYSTEM_PROMPT)
    ap.add_argument(
        "--context-file",
        help="Optional plaintext spec/context to prepend before each question",
    )
    ap.add_argument(
        "--gold-file",
        help="Optional JSON map {question_id: expected_answer} for similarity report",
    )
    args = ap.parse_args()

    if not args.api_key:
        print("ERROR: Missing MODEL_API_KEY (or pass --api-key).", file=sys.stderr)
        return 2

    out_dir = Path(args.out_dir).resolve()
    ensure_dir(out_dir)
    answers_jsonl = out_dir / "answers.jsonl"
    run_meta = out_dir / "run_meta.json"
    compare_csv = out_dir / "compare.csv"
    errors_jsonl = out_dir / "errors.jsonl"

    context = ""
    if args.context_file:
        context = Path(args.context_file).read_text(encoding="utf-8").strip()

    meta = {
        "started_at": dt.datetime.now().isoformat(),
        "model": args.model,
        "base_url": args.base_url,
        "temperature": args.temperature,
        "question_count": len(QUESTIONS),
        "context_file": args.context_file,
        "gold_file": args.gold_file,
    }
    run_meta.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    gold: dict[str, str] = {}
    if args.gold_file:
        gold = load_gold(Path(args.gold_file))

    # Initialize files
    answers_jsonl.write_text("", encoding="utf-8")
    errors_jsonl.write_text("", encoding="utf-8")

    compare_rows: list[dict[str, Any]] = []

    for idx, question in enumerate(QUESTIONS, start=1):
        qid = str(idx)
        prompt = question
        if context:
            prompt = f"Context:\n{context}\n\nQuestion #{qid}:\n{question}"

        started = time.time()
        try:
            answer, raw = call_model(
                base_url=args.base_url,
                api_key=args.api_key,
                model=args.model,
                system_prompt=args.system_prompt,
                user_prompt=prompt,
                temperature=args.temperature,
                timeout_s=args.timeout_s,
            )
            elapsed_ms = int((time.time() - started) * 1000)
            usage = raw.get("usage", {})
            rec = {
                "id": qid,
                "question": question,
                "answer": answer,
                "elapsed_ms": elapsed_ms,
                "usage": usage,
                "model": raw.get("model", args.model),
                "created": raw.get("created"),
            }
            with answers_jsonl.open("a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")

            expected = gold.get(qid, "")
            score = similarity(answer, expected) if expected else None
            compare_rows.append(
                {
                    "id": qid,
                    "question": question,
                    "expected": expected,
                    "answer": answer,
                    "similarity": "" if score is None else f"{score:.3f}",
                    "elapsed_ms": elapsed_ms,
                }
            )
            print(f"[{qid:>2}/60] OK  {elapsed_ms}ms")
        except Exception as e:  # noqa: BLE001
            elapsed_ms = int((time.time() - started) * 1000)
            err_rec = {
                "id": qid,
                "question": question,
                "error": str(e),
                "elapsed_ms": elapsed_ms,
            }
            with errors_jsonl.open("a", encoding="utf-8") as f:
                f.write(json.dumps(err_rec, ensure_ascii=False) + "\n")
            compare_rows.append(
                {
                    "id": qid,
                    "question": question,
                    "expected": gold.get(qid, ""),
                    "answer": "",
                    "similarity": "",
                    "elapsed_ms": elapsed_ms,
                }
            )
            print(f"[{qid:>2}/60] ERR {elapsed_ms}ms  {e}")

        if args.sleep_ms > 0:
            time.sleep(args.sleep_ms / 1000.0)

    # Write compare.csv (manual review friendly)
    with compare_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["id", "question", "expected", "answer", "similarity", "elapsed_ms"],
        )
        writer.writeheader()
        for row in compare_rows:
            writer.writerow(row)

    done_meta = {
        **meta,
        "finished_at": dt.datetime.now().isoformat(),
        "answers_jsonl": str(answers_jsonl),
        "errors_jsonl": str(errors_jsonl),
        "compare_csv": str(compare_csv),
    }
    run_meta.write_text(json.dumps(done_meta, indent=2), encoding="utf-8")

    print("\nDone.")
    print(f"- Answers : {answers_jsonl}")
    print(f"- Errors  : {errors_jsonl}")
    print(f"- Compare : {compare_csv}")
    print(f"- Meta    : {run_meta}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

