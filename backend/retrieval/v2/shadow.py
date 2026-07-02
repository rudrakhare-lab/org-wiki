"""Write retrieval-v2 results to retrieval_shadow_log for offline comparison.

Phase 1 (2026-07-02): also emits bucket_counts via logger.info so timeline
weighting can be verified without a schema change to retrieval_shadow_log.
Grep production logs for 'shadow.bucket_counts' to aggregate.
"""
from __future__ import annotations
import logging
from backend import db

log_ = logging.getLogger(__name__)

_INSERT = """
    INSERT INTO retrieval_shadow_log
        (trace_id, question, v1_keys, v2_keys, v2_scores, v2_confidence,
         v2_latency_ms, served_v2)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
"""

def log(*, trace_id: str | None, question: str,
        v1_keys: list[str], v2_result, v2_latency_ms: int,
        served_v2: bool) -> None:
    v2_keys = [t.get("key") for t in (v2_result.tickets or [])]
    v2_scores = [float(t.get("reranker_score") or 0.0) for t in (v2_result.tickets or [])]

    # Phase 1 bucket_counts logging — grep-key: 'shadow.bucket_counts'.
    diag = getattr(v2_result, "diagnostics", None) or {}
    bc = diag.get("bucket_counts")
    if bc is not None:
        log_.info("shadow.bucket_counts trace=%s served_v2=%s bucket_counts=%r",
                  trace_id, served_v2, bc)

    try:
        with db.connection() as conn, conn.cursor() as cur:
            cur.execute(_INSERT, (
                trace_id, question, v1_keys, v2_keys, v2_scores,
                v2_result.confidence, v2_latency_ms, served_v2,
            ))
            conn.commit()
    except Exception:
        # fail-open: shadow logging never breaks production retrieval
        pass
