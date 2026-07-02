"""Retrieval v2 pipeline: rewrite → embed → hybrid → links → rerank → gate."""
from __future__ import annotations
from typing import Any

from backend.db import connection
from backend.retrieval.v2.embed import embed_query
from backend.retrieval.v2.hybrid import hybrid_search
from backend.retrieval.v2.links import expand as expand_links
from backend.retrieval.v2.rerank import score as rerank_score
from backend.retrieval.v2.rewrite import rewrite
from backend.retrieval.v2.gate import apply as gate_apply, RetrievalResult

# Alias so tests can monkeypatch `pipeline.get_conn` without modification.
get_conn = connection


def search(question: str, *, functional_area: str | None = None,
           limit: int = 10) -> RetrievalResult:
    """Run the full v2 retrieval pipeline and return a gated result.

    Steps: rewrite → embed → hybrid → links → rerank → gate.

    Args:
        question: The user's natural-language question.
        functional_area: Optional Jira functional_area filter. Caller-supplied
            value wins over the filter inferred by the rewriter.
        limit: Maximum candidate tickets to pass through hybrid search.

    Returns:
        RetrievalResult — either a populated result or an Abstain result.
    """
    rw = rewrite(question)
    # Caller-supplied functional_area wins over inferred filter
    filters = dict(rw.filters)
    if functional_area:
        filters["functional_area"] = functional_area
    sub_queries = rw.sub_queries or [question]
    query_vecs = [embed_query(q) for q in sub_queries]
    with get_conn() as conn:
        candidates = hybrid_search(conn, sub_queries, query_vecs, filters, limit=20)
        if not candidates:
            return gate_apply([])
        candidates = expand_links(conn, candidates)
        scored = rerank_score(question, candidates)
        return gate_apply(scored)


def by_module(module_slug: str, query: str, limit: int = 5) -> list[dict]:
    """Return tickets semantically close to a module slug + query.

    Replaces the old INNER-JOIN-on-ticket_module_tags path. Instead, we treat
    the module slug as an additional sub-query token so semantic similarity to
    the module description does the routing.
    """
    qvec = embed_query(query)
    mvec = embed_query(module_slug.replace("-", " "))
    sub_queries = [query, module_slug.replace("-", " ")]
    query_vecs = [qvec, mvec]
    with get_conn() as conn:
        candidates = hybrid_search(conn, sub_queries, query_vecs, {}, limit=limit)
        return candidates
