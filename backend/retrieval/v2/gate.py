"""Strict confidence gate. Translates reranker scores → confidence label and
the abstain-or-answer decision. Thresholds are env-tunable."""
from __future__ import annotations
import os
from dataclasses import dataclass, field
from typing import Any

from backend.retrieval.v2 import timeline

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

_TIER_ORDER = ["Abstain", "Low", "Medium", "High"]


def _downgrade(conf: str, steps: int) -> str:
    """Move `conf` down `steps` tiers in _TIER_ORDER, clamped at Low."""
    if conf not in _TIER_ORDER:
        return conf
    idx = max(_TIER_ORDER.index(conf) - steps, _TIER_ORDER.index("Low"))
    return _TIER_ORDER[idx]


def _top3_bucket_penalty(scored: list) -> tuple[int, str]:
    """Return (tier_steps_to_downgrade, reason_word).

    - Top-3 all `stale_open`  → downgrade 2 tiers.
    - Top-3 all `historical`  → downgrade 1 tier.
    - Otherwise              → downgrade 0.
    """
    if len(scored) < 3:
        return 0, ""
    top_buckets = {c.get("bucket") for c, _ in scored[:3]}
    if top_buckets == {"stale_open"}:
        return 2, "stale-open"
    if top_buckets == {"historical"}:
        return 1, "historical"
    return 0, ""

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
    diag = {
        "top_score": top_score,
        "candidate_count": len(scored),
        "bucket_counts": timeline.bucket_counts(c for c, _ in scored),
    }

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

    # Compute base result.
    if len(scored) == 1:
        result = RetrievalResult(
            tickets=tickets, confidence="Low", abstain=False,
            message="single-source evidence — only one ticket supports this.",
            diagnostics=diag,
        )
    elif top_score >= high_t:
        if _top3_agree(scored):
            result = RetrievalResult(tickets=tickets, confidence="High", abstain=False,
                                     message="strong, agreeing evidence", diagnostics=diag)
        else:
            result = RetrievalResult(tickets=tickets, confidence="Medium", abstain=False,
                                     message="strong evidence but tickets do not fully agree",
                                     diagnostics=diag)
    else:
        # abstain_t <= top_score < high_t
        if _top3_agree(scored):
            result = RetrievalResult(tickets=tickets, confidence="Medium", abstain=False,
                                     message="moderate, agreeing evidence", diagnostics=diag)
        else:
            result = RetrievalResult(tickets=tickets, confidence="Low", abstain=False,
                                     message="moderate evidence, tickets disagree", diagnostics=diag)

    # Bucket-mix penalty (CLAUDE.md §5 Step 2: HISTORICAL / STALE-OPEN evidence
    # is weak; if top-3 are all in one of those buckets, downgrade confidence).
    steps, reason = _top3_bucket_penalty(scored)
    if steps:
        new_conf = _downgrade(result.confidence, steps)
        if new_conf != result.confidence:
            result.confidence = new_conf
            result.message += f" (downgraded: top candidates are {reason})"
    return result
