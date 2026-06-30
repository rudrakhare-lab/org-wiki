"""Cross-encoder rerank step. Loads bge-reranker-v2-m3 once at import.

CPU inference is sufficient for Conwo's internal QPS (~200 ms for 50 candidates).
The model is baked into the Docker image; see scripts/download_reranker_model.py.
"""
from __future__ import annotations
import os
from functools import lru_cache

MODEL_DIR = os.getenv("RERANKER_MODEL_DIR", "BAAI/bge-reranker-v2-m3")
MAX_DOC_CHARS = 1500  # Truncate ticket text; Jira tickets front-load the problem.

@lru_cache(maxsize=1)
def _load_model():
    from sentence_transformers import CrossEncoder
    return CrossEncoder(MODEL_DIR, max_length=512)

# Test seam: tests patch `_model`.
_model = None

def _model_or_load():
    global _model
    if _model is None:
        _model = _load_model()
    return _model

def _doc_text(c: dict) -> str:
    summary = (c.get("summary") or "").strip()
    desc = (c.get("description_text") or "").strip()
    text = f"{summary}\n{desc}" if desc else summary
    if len(text) > MAX_DOC_CHARS:
        text = text[:MAX_DOC_CHARS]
    return text

def score(query: str, candidates: list[dict]) -> list[tuple[dict, float]]:
    if not candidates:
        return []
    pairs = [(query, _doc_text(c)) for c in candidates]
    m = _model_or_load() if _model is None else _model
    scores = m.predict(pairs)
    out = list(zip(candidates, (float(s) for s in scores)))
    out.sort(key=lambda x: x[1], reverse=True)
    return out
