"""Hybrid retrieval: BM25 (tsvector) + dense (pgvector) fused by RRF.

The fused candidate pool feeds the reranker. One Postgres call per sub-query;
the fusion across sub-queries happens in Python.

Named-parameter binding (%(name)s) is used throughout to avoid positional
ordering issues when filter clauses appear twice (once in lex CTE, once in
dense CTE).
"""
from __future__ import annotations
from typing import Any
from psycopg.rows import dict_row

RRF_K = 60  # standard Reciprocal Rank Fusion constant.

_BASE_SQL = """
WITH lex AS (
    SELECT key,
           ts_rank_cd(search_tsv, q) AS lex_score,
           ROW_NUMBER() OVER (ORDER BY ts_rank_cd(search_tsv, q) DESC) AS lex_rnk
    FROM tickets, websearch_to_tsquery('english', %(q_text)s) q
    WHERE search_tsv @@ q
    {filter_sql_lex}
    LIMIT 100
),
dense AS (
    SELECT key,
           1 - (embedding <=> %(q_vec)s::vector) AS dense_score,
           ROW_NUMBER() OVER (ORDER BY embedding <=> %(q_vec)s::vector) AS dense_rnk
    FROM tickets
    WHERE embedding IS NOT NULL
    {filter_sql_dense}
    ORDER BY embedding <=> %(q_vec)s::vector
    LIMIT 100
),
fused AS (
    SELECT key, SUM(1.0 / (%(k)s + rnk)) AS rrf
    FROM (
        SELECT key, lex_rnk  AS rnk FROM lex
        UNION ALL
        SELECT key, dense_rnk AS rnk FROM dense
    ) u
    GROUP BY key
)
SELECT t.key, t.summary, t.description_text, t.comments_text,
       t.status_category, t.priority, t.updated_at, t.resolved_at,
       t.functional_area, t.links_json,
       f.rrf
FROM fused f
JOIN tickets t USING (key)
ORDER BY f.rrf DESC
LIMIT %(limit)s
"""


def _build_filters_sql(filters: dict) -> tuple[str, dict]:
    """Build an AND-clause fragment + named params dict. Empty when no filters.

    Returns named placeholders (%(name)s) so the same dict can be merged into
    the main params dict and referenced in both lex and dense CTEs without
    positional ordering issues.
    """
    if not filters:
        return "", {}
    parts: list[str] = []
    params: dict[str, Any] = {}
    if filters.get("functional_area"):
        parts.append("AND functional_area = %(fa)s")
        params["fa"] = filters["functional_area"]
    if filters.get("resolved_after"):
        parts.append("AND resolved_at >= %(resolved_after)s")
        params["resolved_after"] = filters["resolved_after"]
    if filters.get("status_category"):
        parts.append("AND status_category = %(status_category)s")
        params["status_category"] = filters["status_category"]
    if not parts:
        return "", {}
    return " ".join(parts), params


def _rrf_fuse(per_subquery_results: list[list[dict]]) -> list[dict]:
    """Merge results from multiple sub-queries by summing their fused scores.

    Inputs are already-ranked lists from individual sub-query runs; here we
    just collapse duplicates and re-sort by the summed score. Note: we do NOT
    re-rank by rank-position across sub-queries — the per-sub-query RRF score
    already encodes the rank position. Summing is a reasonable approximation
    for "appears in multiple sub-queries".
    """
    by_key: dict[str, dict] = {}
    for batch in per_subquery_results:
        for row in batch:
            k = row["key"]
            if k in by_key:
                by_key[k]["rrf"] += row["rrf"]
            else:
                by_key[k] = {**row}
    out = list(by_key.values())
    out.sort(key=lambda r: r["rrf"], reverse=True)
    return out


def hybrid_search(conn, sub_queries: list[str], query_vecs: list[list[float]],
                  filters: dict, limit: int = 50) -> list[dict]:
    """Run hybrid retrieval per sub-query, fuse, return top-`limit` candidates."""
    if not sub_queries:
        return []
    filter_clause, filter_params = _build_filters_sql(filters or {})
    sql = _BASE_SQL.format(
        filter_sql_lex=filter_clause,
        filter_sql_dense=filter_clause,
    )
    per_sub: list[list[dict]] = []
    with conn.cursor(row_factory=dict_row) as cur:
        for q_text, q_vec in zip(sub_queries, query_vecs):
            params: dict[str, Any] = {
                "q_text": q_text,
                "q_vec": q_vec,
                "k": RRF_K,
                "limit": limit,
                **filter_params,
            }
            cur.execute(sql, params)
            rows = list(cur.fetchall())
            per_sub.append([{"key": r["key"], "rrf": float(r["rrf"]), **r} for r in rows])

    fused = _rrf_fuse(per_sub)
    return fused[:limit]
