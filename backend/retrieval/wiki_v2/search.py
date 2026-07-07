"""Hybrid chunk retrieval: tsvector + pgvector fused by RRF (spec §5.4 step 1).

Mirrors backend/retrieval/v2/hybrid.py conventions: named params, per-sub-query
SQL call, Python-side RRF across sub-queries, explicit float() casts at the
SQL boundary (numeric SUM returns decimal.Decimal — July outage class).
"""
from __future__ import annotations

RRF_K = 60

_CHUNK_SQL = """
WITH lex AS (
    SELECT id, ROW_NUMBER() OVER (ORDER BY ts_rank_cd(search_tsv, q) DESC) AS rnk
    FROM wiki_chunks, websearch_to_tsquery('english', %(q_text)s) q
    WHERE search_tsv @@ q AND agent_id = %(agent_id)s
    LIMIT 50
),
dense AS (
    SELECT id, ROW_NUMBER() OVER (ORDER BY embedding <=> %(q_vec)s::vector) AS rnk
    FROM wiki_chunks
    WHERE embedding IS NOT NULL AND agent_id = %(agent_id)s
    ORDER BY embedding <=> %(q_vec)s::vector
    LIMIT 50
),
fused AS (
    SELECT id, SUM(1.0 / (%(k)s + rnk)) AS rrf
    FROM (SELECT id, rnk FROM lex UNION ALL SELECT id, rnk FROM dense) u
    GROUP BY id
)
SELECT c.id, c.page_path, c.section_anchor, c.section_title, c.page_type,
       c.chunk_index, c.chunk_text, c.last_updated, f.rrf AS fused_score
FROM fused f JOIN wiki_chunks c USING (id)
ORDER BY f.rrf DESC
LIMIT %(limit)s
"""


def _lex_query(sub_query: str, expansions: dict[str, list[str]] | None) -> str:
    """Append synonym expansions as OR-terms (websearch syntax)."""
    terms = [sub_query]
    for syns in (expansions or {}).values():
        terms.extend(syns)
    return " OR ".join(t for t in terms if t and t.strip())


def hybrid_chunks(conn, sub_queries: list[str], query_vecs: list[list[float]],
                  agent_id: str, expansions: dict[str, list[str]] | None = None,
                  limit: int = 24) -> list[dict]:
    from psycopg.rows import dict_row
    per_sub: list[list[dict]] = []
    with conn.cursor(row_factory=dict_row) as cur:
        for q_text, q_vec in zip(sub_queries, query_vecs):
            cur.execute(_CHUNK_SQL, {
                "q_text": _lex_query(q_text, expansions),
                "q_vec": q_vec, "k": RRF_K,
                "agent_id": agent_id, "limit": limit,
            })
            rows = list(cur.fetchall())
            per_sub.append(
                [{**r, "fused_score": float(r["fused_score"])} for r in rows])

    if len(per_sub) == 1:
        return per_sub[0]

    # RRF across sub-queries, keyed by chunk id.
    scores: dict = {}
    rowmap: dict = {}
    for rows in per_sub:
        for rank, r in enumerate(rows, start=1):
            scores[r["id"]] = scores.get(r["id"], 0.0) + 1.0 / (RRF_K + rank)
            rowmap[r["id"]] = r
    fused = sorted(rowmap.values(),
                   key=lambda r: scores[r["id"]], reverse=True)
    for r in fused:
        r["fused_score"] = float(scores[r["id"]])
    return fused[:limit]
