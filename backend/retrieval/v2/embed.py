"""Gemini embeddings for Jira retrieval v2.

Asymmetric: distinct task types for documents vs queries. Mixing them silently
degrades recall, so we expose two separate functions and never a generic one.

SDK: google-genai (new SDK, replaces deprecated google-generativeai).
Model: gemini-embedding-001 with output_dimensionality=768 to match the
vector(768) column in migration 150.
"""
from __future__ import annotations
import os

from google import genai
from google.genai import types

_MODEL = "models/gemini-embedding-001"
_DIM = 768
_BATCH = 100  # Gemini accepts batches; 100 is comfortably under the limit.


def _make_client() -> genai.Client:
    key = os.getenv("GOOGLE_GENAI_API_KEY")
    if not key:
        raise RuntimeError(
            "GOOGLE_GENAI_API_KEY not set; required for retrieval v2 embeddings."
        )
    return genai.Client(api_key=key)


class _ModelsProxy:
    """Forwards embed_content to the real SDK client.models lazily.

    Stored as embed._client.models so tests can do:
        patch.object(embed._client, "models") as mock_models
    without triggering a real API key check at patch time.
    """

    def __init__(self) -> None:
        self._real_client: genai.Client | None = None

    def _ensure(self) -> genai.Client:
        if self._real_client is None:
            self._real_client = _make_client()
        return self._real_client

    def embed_content(self, **kwargs):  # type: ignore[override]
        return self._ensure().models.embed_content(**kwargs)


class _LazyClient:
    """Wraps the SDK client; exposes .models as a plain instance attribute so
    unittest.mock.patch.object can intercept it without triggering key validation."""

    def __init__(self) -> None:
        self.models: _ModelsProxy = _ModelsProxy()


# Module-level client; tests patch embed._client.models.embed_content.
_client: _LazyClient = _LazyClient()


def embed_query(text: str) -> list[float]:
    resp = _client.models.embed_content(
        model=_MODEL,
        contents=text,
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_QUERY",
            output_dimensionality=_DIM,
        ),
    )
    vec = resp.embeddings[0].values
    return [float(x) for x in vec]


def embed_documents(texts: list[str]) -> list[list[float]]:
    out: list[list[float]] = []
    for i in range(0, len(texts), _BATCH):
        batch = texts[i:i + _BATCH]
        resp = _client.models.embed_content(
            model=_MODEL,
            contents=batch,
            config=types.EmbedContentConfig(
                task_type="RETRIEVAL_DOCUMENT",
                output_dimensionality=_DIM,
            ),
        )
        for emb in resp.embeddings:
            out.append([float(x) for x in emb.values])
    return out
