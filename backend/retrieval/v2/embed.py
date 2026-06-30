"""Gemini embeddings for Jira retrieval v2.

Asymmetric: distinct task types for documents vs queries. Mixing them silently
degrades recall, so we expose two separate functions and never a generic one.
"""
from __future__ import annotations
import os
from typing import Any

import google.generativeai as genai

_MODEL = "models/text-embedding-004"
_BATCH = 100  # Gemini accepts batches; 100 is comfortably under the limit.

def _ensure_configured() -> None:
    key = os.getenv("GOOGLE_GENAI_API_KEY")
    if not key:
        raise RuntimeError(
            "GOOGLE_GENAI_API_KEY not set; required for retrieval v2 embeddings."
        )
    genai.configure(api_key=key)


class _GeminiClient:
    def embed_content(self, *, model: str, content: Any, task_type: str) -> dict:
        _ensure_configured()
        return genai.embed_content(model=model, content=content, task_type=task_type)


_client = _GeminiClient()


def embed_query(text: str) -> list[float]:
    resp = _client.embed_content(model=_MODEL, content=text, task_type="RETRIEVAL_QUERY")
    vec = resp["embedding"]
    return [float(x) for x in vec]

def embed_documents(texts: list[str]) -> list[list[float]]:
    out: list[list[float]] = []
    for i in range(0, len(texts), _BATCH):
        batch = texts[i:i + _BATCH]
        resp = _client.embed_content(model=_MODEL, content=batch, task_type="RETRIEVAL_DOCUMENT")
        vecs = resp["embedding"]
        for v in vecs:
            out.append([float(x) for x in v])
    return out
