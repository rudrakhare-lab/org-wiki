"""Embedder uses the correct Gemini task types for doc vs query."""
from unittest.mock import patch, MagicMock


def _make_embedding(values: list[float]) -> MagicMock:
    """Build a fake ContentEmbedding with a .values attribute."""
    emb = MagicMock()
    emb.values = values
    return emb


def _make_response(embeddings: list[MagicMock]) -> MagicMock:
    """Build a fake EmbedContentResponse with an .embeddings list."""
    resp = MagicMock()
    resp.embeddings = embeddings
    return resp


def test_embed_query_uses_retrieval_query_task_type():
    from backend.retrieval.v2 import embed
    with patch.object(embed._client, "models") as models:
        models.embed_content.return_value = _make_response([_make_embedding([0.0] * 768)])
        embed.embed_query("test question")
        kwargs = models.embed_content.call_args.kwargs
        assert kwargs["config"].task_type == "RETRIEVAL_QUERY"
        assert kwargs["model"].endswith("gemini-embedding-001")


def test_embed_documents_uses_retrieval_document_task_type():
    from backend.retrieval.v2 import embed
    with patch.object(embed._client, "models") as models:
        models.embed_content.return_value = _make_response(
            [_make_embedding([0.0] * 768), _make_embedding([0.0] * 768)]
        )
        embed.embed_documents(["doc1", "doc2"])
        kwargs = models.embed_content.call_args.kwargs
        assert kwargs["config"].task_type == "RETRIEVAL_DOCUMENT"


def test_embed_query_returns_768d_list_of_floats():
    from backend.retrieval.v2 import embed
    with patch.object(embed._client, "models") as models:
        models.embed_content.return_value = _make_response(
            [_make_embedding(list(range(768)))]
        )
        v = embed.embed_query("x")
        assert isinstance(v, list)
        assert len(v) == 768
        assert all(isinstance(x, float) for x in v)


def test_embed_documents_batches_in_chunks_of_100():
    from backend.retrieval.v2 import embed
    with patch.object(embed._client, "models") as models:
        models.embed_content.return_value = _make_response(
            [_make_embedding([0.0] * 768)] * 100
        )
        embed.embed_documents(["x"] * 250)
        # 250 docs / 100 per batch = 3 calls
        assert models.embed_content.call_count == 3
