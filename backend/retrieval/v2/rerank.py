"""Cross-encoder rerank step.

Uses ms-marco-MiniLM-L-6-v2 (23M params, ~90MB) — a 24× smaller model than the
previous bge-reranker-v2-m3 (568M, ~560MB). Inference is ~20-100ms on 1 CPU core
vs 3-4 minutes under CPU throttle with the larger model.

The model is preloaded at FastAPI startup (see `backend/api.py` lifespan →
`rerank.preload()`) so the first user query never pays the model-load latency.
If preload didn't run (unit tests, ad-hoc REPL), the first call to `score()`
will lazy-load via `_model_or_load()`.

The model is baked into the Docker image at /app/models/ms-marco-MiniLM-L-6-v2 by
scripts/download_reranker_model.py; RERANKER_MODEL_DIR env var picks it up.
If neither the env var nor the baked directory is present, sentence-transformers
falls back to downloading cross-encoder/ms-marco-MiniLM-L-6-v2 from HuggingFace
on first use (one-time ~5-10s per pod restart, then cached in pod memory).

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

MODEL_DIR = os.getenv("RERANKER_MODEL_DIR", "cross-encoder/ms-marco-MiniLM-L-6-v2")

@lru_cache(maxsize=1)
def _load_model():
    import torch
    torch.set_num_threads(2)  # Cap intra-op parallelism — prevents torch from competing with uvicorn workers.
    from sentence_transformers import CrossEncoder
    return CrossEncoder(MODEL_DIR, max_length=256)

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

_SUMMARY_MAX  = 200
_DESC_MAX     = 500
_COMMENTS_MAX = 300


def _doc_text(c: dict) -> str:
    """Fixed-budget layout for reranker input — ~1013 chars max total.

    Layout (each field independently trimmed):
      summary            : 0..200 chars
      description_text   : 0..500 chars
      [comments] ...     : 0..300 chars (prefix omitted when empty)

    Max total is 200+500+300 plus the '[comments] ' prefix (11) and two '\\n'
    separators = 1013 chars — safe under MiniLM cross-encoder's 256-token
    limit even at ~4 chars/token. Fields joined with '\\n'; empty fields
    skipped.
    """
    summary  = (c.get("summary")          or "").strip()[:_SUMMARY_MAX]
    desc     = (c.get("description_text") or "").strip()[:_DESC_MAX]
    comments = (c.get("comments_text")    or "").strip()[:_COMMENTS_MAX]
    parts: list[str] = []
    if summary:  parts.append(summary)
    if desc:     parts.append(desc)
    if comments: parts.append(f"[comments] {comments}")
    return "\n".join(parts)

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
