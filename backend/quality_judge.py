"""
quality_judge.py — async LLM-as-judge scoring for completed query traces.

Fired after a trace's end_session() (design spec 2026-07-02-dashboard-overview-
tab-design.md §6) via api.py's BackgroundTasks — runs AFTER the response is
sent, adding zero latency/cost to the user's request.

Scores the answer against 4 rubric dimensions using Haiku 4.5, re-fetching the
CURRENT content of whatever wiki pages / Jira tickets the answer cited (no
frozen snapshot of retrieved context is stored at query time — accepted
trade-off per the design spec: the judge grades against live wiki/Jira truth,
which doesn't drift mid-session).

Fail-open: mirrors trace_store.py's discipline. judge_trace() must never raise
— a judge failure must never surface to the user or break a request.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone

import anthropic

from backend import db, feedback_service, wiki_retriever

_log = logging.getLogger("quality_judge")

_MODEL = "claude-haiku-4-5-20251001"
_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))

_SYSTEM = (
    "You are a quality judge for an internal knowledge-base assistant (Conwo). "
    "You will be shown a user's question, the assistant's answer, the assistant's "
    "stated confidence (High/Medium/Low), and the CURRENT content of the wiki "
    "pages / Jira tickets the answer cited as sources. Score the answer 0-100 on "
    "each of these four dimensions:\n"
    "  groundedness: does the answer's content match the cited source material, "
    "with no fabricated facts absent from the sources?\n"
    "  completeness: does the answer fully address the user's actual question?\n"
    "  confidence_calibration: does the stated confidence level match how strong "
    "the cited evidence actually is (e.g. weak evidence + High confidence = low score)?\n"
    "  source_usage: did the answer actually draw on and cite real sources, "
    "rather than answering from general knowledge alone?\n"
    "Output JSON only, no prose, with this exact shape:\n"
    '{"groundedness": <0-100>, "completeness": <0-100>, '
    '"confidence_calibration": <0-100>, "source_usage": <0-100>, '
    '"rationale": "<one sentence>"}'
)


def _fetch_cited_context(wiki_pages: list[str], jira_keys: list[str]) -> str:
    """Re-fetch the CURRENT content of cited sources — see module docstring for
    why this is not a frozen snapshot from query time."""
    parts: list[str] = []
    for path in wiki_pages[:10]:
        page = wiki_retriever.get_page(path)
        if page:
            parts.append(f"## Wiki: {page.path}\n{page.full_text[:2000]}")
    if jira_keys:
        keys = jira_keys[:10]
        placeholders = ",".join(["%s"] * len(keys))
        with db.connection() as conn:
            rows = conn.execute(
                f"SELECT key, summary, description_text FROM tickets WHERE key IN ({placeholders})",
                keys,
            ).fetchall()
        for r in rows:
            desc = (r["description_text"] or "")[:1500]
            parts.append(f"## Jira {r['key']}: {r['summary']}\n{desc}")
    return "\n\n".join(parts) if parts else "(no cited sources found)"


def _call_judge(question: str, answer_text: str, confidence: str, context: str) -> dict:
    user_message = (
        f"QUESTION:\n{question}\n\n"
        f"ASSISTANT'S ANSWER:\n{answer_text}\n\n"
        f"ASSISTANT'S STATED CONFIDENCE: {confidence}\n\n"
        f"CITED SOURCES (current content):\n{context}"
    )
    resp = _client.messages.create(
        model=_MODEL, max_tokens=400, system=_SYSTEM,
        messages=[{"role": "user", "content": user_message}],
    )
    raw = resp.content[0].text if resp.content else ""
    data = json.loads(raw)
    g = float(data.get("groundedness", 0))
    c = float(data.get("completeness", 0))
    cc = float(data.get("confidence_calibration", 0))
    su = float(data.get("source_usage", 0))
    return {
        "overall_score": round((g + c + cc + su) / 4, 2),
        "groundedness_score": g,
        "completeness_score": c,
        "confidence_calibration_score": cc,
        "source_usage_score": su,
        "rationale": str(data.get("rationale", ""))[:500],
    }


def _write_judgment(trace_id: str, scores: dict) -> None:
    now = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
    with db.connection() as conn:
        conn.execute(
            "INSERT INTO quality_judgments "
            "(trace_id, overall_score, groundedness_score, completeness_score, "
            "confidence_calibration_score, source_usage_score, rationale, judge_model, judged_at) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (trace_id) DO UPDATE SET "
            "  overall_score = excluded.overall_score, "
            "  groundedness_score = excluded.groundedness_score, "
            "  completeness_score = excluded.completeness_score, "
            "  confidence_calibration_score = excluded.confidence_calibration_score, "
            "  source_usage_score = excluded.source_usage_score, "
            "  rationale = excluded.rationale, "
            "  judge_model = excluded.judge_model, "
            "  judged_at = excluded.judged_at",
            (
                trace_id, scores["overall_score"], scores["groundedness_score"],
                scores["completeness_score"], scores["confidence_calibration_score"],
                scores["source_usage_score"], scores["rationale"], _MODEL, now,
            ),
        )


def judge_trace(trace_id: str) -> None:
    """Score one completed trace's answer quality. Fail-open: never raises."""
    if not trace_id:
        return
    try:
        record = feedback_service.find_answer_by_trace_id(trace_id)
        if record is None:
            return  # no linked answer yet (or ever) — nothing to judge
        answer_text = record.get("answer_text", "")
        if not answer_text.strip():
            return
        question = record.get("question", "")
        confidence = record.get("confidence", "Medium")
        sources = record.get("sources") or {}
        wiki_pages = list(sources.get("wiki") or [])
        jira_keys = list(sources.get("jira") or [])

        context = _fetch_cited_context(wiki_pages, jira_keys)
        scores = _call_judge(question, answer_text, confidence, context)
        _write_judgment(trace_id, scores)
    except Exception as exc:
        _log.warning("quality_judge.judge_trace failed for trace_id=%s (ignored): %s", trace_id, exc)
