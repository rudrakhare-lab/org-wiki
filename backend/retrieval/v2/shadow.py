"""Write retrieval-v2 results to retrieval_shadow_log for offline comparison."""
from __future__ import annotations
import time
from backend import db

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
