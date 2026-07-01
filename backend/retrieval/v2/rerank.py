"""Cross-encoder rerank step.

The bge-reranker-v2-m3 model is preloaded at FastAPI startup (see
`backend/api.py` lifespan → `rerank.preload()`) so the first user query never
pays the ~5 sec model-load latency. If preload didn't run (unit tests, scripts,
ad-hoc REPL), the first call to `score()` will lazy-load via `_model_or_load()`.

CPU inference is sufficient for Conwo's internal QPS (~200 ms for 50 candidates).
The model is baked into the Docker image at /app/models/bge-reranker-v2-m3 by
scripts/download_reranker_model.py; RERANKER_MODEL_DIR env var picks it up.

`score_async()` wraps the CPU-bound synchronous `predict()` in
`asyncio.to_thread()` so the FastAPI event loop stays responsive while scoring
runs — critical for keeping `/health` liveness probes answering during a query.
A blocked event loop is what was killing pods via liveness timeout before this
change.
"""
from __future__ import annotations
import asyncio
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

def preload() -> None:
    """Force-load the model into RAM. Called from the FastAPI lifespan at
    startup (wrapped in `asyncio.to_thread` so it doesn't block the event loop
    during boot). Safe to call multiple times — subsequent calls are no-ops
    because `_load_model` is memoized via `lru_cache`.
    """
    _model_or_load()

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

async def score_async(query: str, candidates: list[dict]) -> list[tuple[dict, float]]:
    """Async wrapper: runs the CPU-bound `predict()` off the event loop so
    concurrent `/health` probes and other requests stay responsive during
    scoring. Prefer this from any async caller (FastAPI handlers, the async
    pipeline)."""
    if not candidates:
        return []
    return await asyncio.to_thread(score, query, candidates)
