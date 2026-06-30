"""Embedder uses the correct Gemini task types for doc vs query."""
from unittest.mock import patch, MagicMock

def test_embed_query_uses_retrieval_query_task_type():
    from backend.retrieval.v2 import embed
    with patch.object(embed, "_client") as client:
        client.embed_content.return_value = {"embedding": [0.0]*768}
        embed.embed_query("test question")
        kwargs = client.embed_content.call_args.kwargs
        assert kwargs["task_type"] == "RETRIEVAL_QUERY"
        assert kwargs["model"].endswith("text-embedding-004")

def test_embed_documents_uses_retrieval_document_task_type():
    from backend.retrieval.v2 import embed
    with patch.object(embed, "_client") as client:
        client.embed_content.return_value = {"embedding": [[0.0]*768, [0.0]*768]}
        embed.embed_documents(["doc1", "doc2"])
        kwargs = client.embed_content.call_args.kwargs
        assert kwargs["task_type"] == "RETRIEVAL_DOCUMENT"

def test_embed_query_returns_768d_list_of_floats():
    from backend.retrieval.v2 import embed
    with patch.object(embed, "_client") as client:
        client.embed_content.return_value = {"embedding": list(range(768))}
        v = embed.embed_query("x")
        assert isinstance(v, list)
        assert len(v) == 768
        assert all(isinstance(x, float) for x in v)

def test_embed_documents_batches_in_chunks_of_100():
    from backend.retrieval.v2 import embed
    with patch.object(embed, "_client") as client:
        client.embed_content.return_value = {"embedding": [[0.0]*768]*100}
        embed.embed_documents(["x"]*250)
        # 250 docs / 100 per batch = 3 calls
        assert client.embed_content.call_count == 3
