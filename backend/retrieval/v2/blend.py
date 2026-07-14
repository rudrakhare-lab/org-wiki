"""Blend rerank + recency + fusion into one ranking score (spec A1).

Before this, the reranker score alone decided ordering + confidence, and the
RRF `fused_score` and recency `timeline_score` (both computed upstream) were
discarded after admitting candidates. This folds all three back in.

All three inputs are in [0,1] (reranker is sigmoid-calibrated; timeline_score
is a 0..1 decay×status weight; fused_score is min-max normalized within the
candidate set here), and the weights sum to 1.0, so the blended score is in
[0,1] and gate.py's thresholds stay meaningful.
"""
from __future__ import annotations
import os


def _w(env: str, default: float) -> float:
    try:
        return float(os.getenv(env, str(default)))
    except (TypeError, ValueError):
        return default


def enabled() -> bool:
    return os.getenv("CONWO_RANK_BLEND", "on").strip().lower() != "off"


def weights() -> tuple[float, float, float]:
    return (
        _w("CONWO_RANK_W_RERANK", 0.5),
        _w("CONWO_RANK_W_TIMELINE", 0.3),
        _w("CONWO_RANK_W_FUSED", 0.2),
    )


def blend_scores(scored: list[tuple[dict, float]]) -> list[tuple[dict, float]]:
    """Attach `reranker_score` + `blend_score` to each candidate and return the
    list re-sorted by blend descending.

    `scored` is the reranker output: [(candidate_dict, rerank_prob), ...].
    When disabled (CONWO_RANK_BLEND=off), blend_score == rerank_prob (identity),
    but reranker_score is still stashed so the gate can attach it uniformly.
    """
    if not scored:
        return []
    w_r, w_t, w_f = weights()
    on = enabled()
    fused_vals = [float(c.get("fused_score") or 0.0) for c, _ in scored]
    lo, hi = min(fused_vals), max(fused_vals)
    span = hi - lo
    out: list[tuple[dict, float]] = []
    for c, rr in scored:
        c["reranker_score"] = rr
        if on:
            f = float(c.get("fused_score") or 0.0)
            nf = (f - lo) / span if span > 0 else 0.0
            ts = float(c.get("timeline_score") or 0.0)
            b = w_r * rr + w_t * ts + w_f * nf
        else:
            b = rr
        c["blend_score"] = b
        out.append((c, b))
    out.sort(key=lambda x: x[1], reverse=True)
    return out
