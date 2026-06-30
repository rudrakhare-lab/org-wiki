"""Strict confidence gate. Translates reranker scores → confidence label and
the abstain-or-answer decision. Thresholds are env-tunable."""
from __future__ import annotations
import os
from dataclasses import dataclass, field
from typing import Any

def _f(env: str, default: float) -> float:
    try:
        return float(os.getenv(env, str(default)))
    except (TypeError, ValueError):
        return default

ABSTAIN = lambda: _f("CONWO_RETRIEVAL_V2_ABSTAIN_THRESHOLD", 0.5)
HIGH    = lambda: _f("CONWO_RETRIEVAL_V2_HIGH_THRESHOLD", 0.7)

@dataclass
class RetrievalResult:
    tickets: list[dict]
    confidence: str
    abstain: bool
    message: str
    diagnostics: dict = field(default_factory=dict)

def _top3_agree(scored: list[tuple[dict, float]]) -> bool:
    if len(scored) < 2:
        return False
    top = scored[:3]
    fas = {c.get("functional_area") for c, _ in top if c.get("functional_area")}
    # share at least one functional area
    if len(fas) <= 1 and fas:
        return True
    # share an epic (epic_key)
    epics = {c.get("epic_key") for c, _ in top if c.get("epic_key")}
    if len(epics) == 1 and epics:
        return True
    return False

def apply(scored: list[tuple[dict, float]]) -> RetrievalResult:
    abstain_t = ABSTAIN()
    high_t = HIGH()
    if not scored:
        return RetrievalResult(
            tickets=[], confidence="Abstain", abstain=True,
            message="I couldn't find any matching tickets.",
            diagnostics={"top_score": None, "candidate_count": 0},
        )
    top_score = scored[0][1]
    diag = {"top_score": top_score, "candidate_count": len(scored)}

    if top_score < abstain_t:
        keys = [c["key"] for c, _ in scored[:5]]
        return RetrievalResult(
            tickets=[],
            confidence="Abstain",
            abstain=True,
            message=(f"I couldn't find strong evidence. "
                     f"Closest matches: {', '.join(keys)}. Please verify."),
            diagnostics=diag,
        )

    # Build the tickets list with attached reranker_score, top-10 max.
    tickets = []
    for c, s in scored[:10]:
        out = {**c, "reranker_score": s}
        tickets.append(out)

    if len(scored) == 1:
        return RetrievalResult(
            tickets=tickets, confidence="Low", abstain=False,
            message="single-source evidence — only one ticket supports this.",
            diagnostics=diag,
        )

    if top_score >= high_t:
        if _top3_agree(scored):
            return RetrievalResult(tickets=tickets, confidence="High", abstain=False,
                                   message="strong, agreeing evidence", diagnostics=diag)
        return RetrievalResult(tickets=tickets, confidence="Medium", abstain=False,
                               message="strong evidence but tickets do not fully agree",
                               diagnostics=diag)
    # abstain_t <= top_score < high_t
    if _top3_agree(scored):
        return RetrievalResult(tickets=tickets, confidence="Medium", abstain=False,
                               message="moderate, agreeing evidence", diagnostics=diag)
    return RetrievalResult(tickets=tickets, confidence="Low", abstain=False,
                           message="moderate evidence, tickets disagree", diagnostics=diag)
