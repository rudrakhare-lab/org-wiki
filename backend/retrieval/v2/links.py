"""Relationship expansion and supersession-aware ranking.

Two transforms applied on the candidate list before reranking:
  1. Supersession drop: if candidate X has `supersedes -> Y` and Y is newer,
     replace X with Y (only if Y not already in the set).
  2. 1-hop expansion: for the top-N candidates, pull every directly-linked
     ticket and append (capped). The reranker then decides if they're relevant.
"""
from __future__ import annotations
from psycopg.rows import dict_row

_LINKS_FOR_SRC_SQL = """
    SELECT src_key, dst_key, link_type
    FROM ticket_links
    WHERE src_key = ANY(%s)
"""

_TICKETS_BY_KEY_SQL = """
    SELECT key, summary, description_text, comments_text,
           status_category, priority, updated_at, resolved_at,
           functional_area, links_json, comment_count
    FROM tickets
    WHERE key = ANY(%s)
"""

def _drop_superseded(conn, candidates: list[dict]) -> list[dict]:
    """If candidate X supersedes Y and Y is newer, swap. Use only the
    `supersedes` link type."""
    if not candidates:
        return candidates
    keys = [c["key"] for c in candidates]
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(_LINKS_FOR_SRC_SQL, (keys,))
        rows = cur.fetchall()
    superseding: dict[str, str] = {}
    for r in rows:
        if r["link_type"] == "supersedes":
            superseding[r["src_key"]] = r["dst_key"]
    if not superseding:
        return candidates
    # Fetch replacement rows; only swap when replacement is newer.
    repl_keys = list(set(superseding.values()))
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(_TICKETS_BY_KEY_SQL, (repl_keys,))
        repl_rows = {r["key"]: r for r in cur.fetchall()}
    out: list[dict] = []
    seen: set[str] = set()
    for c in candidates:
        rk = superseding.get(c["key"])
        if rk and rk in repl_rows and repl_rows[rk]["updated_at"] > c["updated_at"]:
            if rk not in seen:
                merged = {**repl_rows[rk], "fused_score": c.get("fused_score", 0.0)}
                out.append(merged)
                seen.add(rk)
        else:
            if c["key"] not in seen:
                out.append(c); seen.add(c["key"])
    return out

def _one_hop_expand(conn, candidates: list[dict], top_for_expansion: int,
                    max_added: int) -> list[dict]:
    if not candidates or max_added <= 0:
        return candidates
    seeds = [c["key"] for c in candidates[:top_for_expansion]]
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(_LINKS_FOR_SRC_SQL, (seeds,))
        link_rows = cur.fetchall()
    existing = {c["key"] for c in candidates}
    add_keys: list[str] = []
    for r in link_rows:
        if r["dst_key"] not in existing and r["dst_key"] not in add_keys:
            add_keys.append(r["dst_key"])
        if len(add_keys) >= max_added:
            break
    if not add_keys:
        return candidates
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(_TICKETS_BY_KEY_SQL, (add_keys,))
        added = [{**r, "fused_score": 0.0} for r in cur.fetchall()]
    return candidates + added

def expand(conn, candidates: list[dict], *,
           top_for_expansion: int = 20, max_added: int = 20) -> list[dict]:
    candidates = _drop_superseded(conn, candidates)
    candidates = _one_hop_expand(conn, candidates, top_for_expansion, max_added)
    return candidates
