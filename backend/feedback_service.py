"""
Feedback service — thin adapters around log_answer.py and record_feedback.py
so the FastAPI layer can call them without going through argparse.
"""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

_SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from log_answer import cmd_log, make_answer_id, utc_now as _la_utc_now, append_record as _la_append
from record_feedback import (
    cmd_record,
    cmd_list,
    cmd_resolve,
    cmd_summary,
    feedback_id as _make_fb_id,
    append_record as _fb_append,
    load_records as _fb_load,
)

from backend.config import ANSWER_LOG, FEEDBACK_LOG


def prepare_answer_id(question: str, answer_text: str) -> tuple[str, str]:
    """Pre-compute (answer_id, created_at) for a question+answer pair.

    Used when the caller needs to substitute the answer_id into the response
    text *before* logging — see backend.orchestrator.run_deep. The id is
    derived from the model's literal output (with placeholders intact) so
    the same input produces the same id on retry.
    """
    created_at = _la_utc_now()
    answer_id = make_answer_id(question, answer_text, created_at)
    return answer_id, created_at


def log_answer(
    question: str,
    answer_text: str,
    confidence: str,
    wiki_pages: list[str] | None = None,
    jira_keys: list[str] | None = None,
    pms_configs: list[str] | None = None,
    retrieval_notes: str = "",
    answer_id: str | None = None,
    created_at: str | None = None,
) -> str:
    """Log an answer record and return the answer_id.

    If `answer_id` and `created_at` are provided (e.g. from prepare_answer_id),
    use them verbatim — useful when the answer_text was post-processed after
    id computation. Otherwise compute fresh.
    """
    if answer_id is None or created_at is None:
        answer_id, created_at = prepare_answer_id(question, answer_text)
    record = {
        "answer_id": answer_id,
        "created_at": created_at,
        "question": question,
        "answer_text": answer_text,
        "confidence": confidence,
        "sources": {
            "wiki": list(wiki_pages or []),
            "jira": list(jira_keys or []),
            "pms": list(pms_configs or []),
        },
        "retrieval_notes": retrieval_notes,
    }
    ANSWER_LOG.parent.mkdir(parents=True, exist_ok=True)
    _la_append(ANSWER_LOG, record)
    return answer_id


def record_feedback(
    answer_id: str,
    question: str,
    score: int,
    label: str,
    correction: str = "",
    expected_answer: str = "",
    sources: list[str] | None = None,
    affected: list[str] | None = None,
    reviewer: str = "",
) -> str:
    """Record feedback and return the feedback_id."""
    args = SimpleNamespace(
        store=FEEDBACK_LOG,
        answer_id=answer_id,
        question=question,
        score=score,
        label=label,
        correction=correction,
        expected_answer=expected_answer,
        sources=",".join(sources or []),
        affected=",".join(affected or []),
        reviewer=reviewer,
        answer_log=ANSWER_LOG,
    )
    FEEDBACK_LOG.parent.mkdir(parents=True, exist_ok=True)
    import io, contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        cmd_record(args)
    output = buf.getvalue().strip()
    # output: "Recorded feedback <fid> in <path>"
    return output.split()[2] if output.startswith("Recorded") else ""


def list_feedback(status: str = "pending", limit: int = 50, label: str | None = None) -> list[dict]:
    records = _fb_load(FEEDBACK_LOG)
    if status:
        records = [r for r in records if r.get("status") == status]
    if label:
        records = [r for r in records if r.get("label") == label]
    return sorted(records, key=lambda r: r.get("created_at", ""), reverse=True)[:limit]


def resolve_feedback(feedback_id: str, resolution: str, wiki_commit_ref: str = "") -> bool:
    args = SimpleNamespace(
        store=FEEDBACK_LOG,
        feedback_id=feedback_id,
        resolution=resolution,
        wiki_commit_ref=wiki_commit_ref,
    )
    return cmd_resolve(args) == 0


def get_summary() -> dict:
    """Return a dict summary of feedback stats."""
    from collections import Counter
    records = _fb_load(FEEDBACK_LOG)
    total = len(records)
    avg = sum(int(r.get("score", 0)) for r in records) / total if total else 0.0
    return {
        "total": total,
        "avg_score": round(avg, 2),
        "by_status": dict(Counter(r.get("status") for r in records)),
        "by_label": dict(Counter(r.get("label") for r in records)),
    }
