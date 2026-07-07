"""Wiki v2 retrieval pipeline (spec §5.4): hybrid → leashed graph expansion
→ shared rerank → soft intent/temporal selection.

Raises WikiV2Unavailable on any dependency failure (embedding API, empty
chunk table) — the caller (preflight / wiki_search tool) falls back to the
keyword path and notes the degradation. Never crash a query from here.
"""
from __future__ import annotations
import logging
import os
import re
from dataclasses import dataclass

from backend.db import connection as _connection
from backend.retrieval.v2.embed import embed_query
from backend.retrieval.v2.rerank import score as rerank_score
from backend.retrieval.wiki_v2.search import hybrid_chunks

_log = logging.getLogger("wiki_v2")

NEIGHBOR_CAP = 6
EXPAND_DEPTH = {"ARCHITECTURAL": 2}  # every other intent: 1

# Temporal detection (spec §5.10): QueryIntent has no HISTORY member — the
# temporal signal is detected from the question text and switches the boost
# table to "HISTORY" (history/decision pages boosted). Requires `import re`
# at module top alongside `import os`.
_TEMPORAL_RE = re.compile(
    r"\b(when did|when was|what changed|changelog|release note|history of|"
    r"used to|previously|before 20\d\d|since 20\d\d|evolved|timeline)\b",
    re.IGNORECASE)

# Soft multipliers only — [0.6, 1.4]. NEVER 0 (soft-routing invariant, spec §5.5).
TYPE_BOOSTS: dict[str, dict[str, float]] = {
    "CONFIGURATION": {"config": 1.3, "module": 1.1, "history": 0.7},
    "DEBUGGING":     {"config": 1.25, "module": 1.1, "history": 0.7},
    "HOW_TO":        {"runbook": 1.3, "module": 1.1, "history": 0.8},
    "DEFINITION":    {"concept": 1.2, "module": 1.15, "history": 0.7},
    "ARCHITECTURAL": {"cross-module": 1.3, "module": 1.2, "history": 0.8},
    "COMPARISON":    {"config": 1.2, "module": 1.1},
    "STATUS":        {"history": 0.8},
    "GENERAL":       {},
    "HISTORY":       {"history": 1.4, "decision": 1.2},  # temporal intent
}


class WikiV2Unavailable(Exception):
    """Wiki v2 cannot serve (embed API down / chunks not backfilled)."""


@dataclass
class ChunkHit:
    page_path: str
    section_anchor: str
    section_title: str
    page_type: str
    chunk_text: str
    last_updated: str | None
    score: float
    related_via: str | None = None

    @property
    def anchor(self) -> str:
        return (f"{self.page_path}#{self.section_anchor}"
                if self.section_anchor else self.page_path)


def _graph_for(agent_id: str | None):
    from backend import wiki_graph
    return wiki_graph.get_graph(agent_id)


_BEST_CHUNK_SQL = """
    SELECT id, page_path, section_anchor, section_title, page_type,
           chunk_index, chunk_text, last_updated, 0.0 AS fused_score
    FROM wiki_chunks
    WHERE agent_id = %(agent_id)s AND page_path = %(page_path)s
          AND embedding IS NOT NULL
    ORDER BY embedding <=> %(q_vec)s::vector
    LIMIT 1
"""


def _best_chunk_for_page(conn, agent_id: str, page_path: str,
                         q_vec: list[float]) -> dict | None:
    from psycopg.rows import dict_row
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(_BEST_CHUNK_SQL, {"agent_id": agent_id,
                                      "page_path": page_path, "q_vec": q_vec})
        rows = cur.fetchall()
    return dict(rows[0]) if rows else None


def _to_rerank_shape(row: dict) -> dict:
    """Map a chunk row onto rerank._doc_text's expected keys."""
    title = f"{row['page_path']} {row.get('section_title', '')}".strip()
    return {**row, "summary": title, "description_text": row["chunk_text"],
            "comments_text": ""}


def search(question: str, *, sub_queries: list[str] | None = None,
           expansions: dict | None = None, intent: str = "GENERAL",
           agent_id: str | None = None, top_k: int = 10) -> list[ChunkHit]:
    from backend import agent_context
    aid = agent_id or agent_context.get_current_agent_id()
    subs = [q for q in (sub_queries or [question]) if q and q.strip()] or [question]

    try:
        q_vecs = [embed_query(q) for q in subs]
    except Exception as exc:
        raise WikiV2Unavailable(f"query embedding failed: {exc}") from exc

    with _connection() as conn:
        direct = hybrid_chunks(conn, subs, q_vecs, aid,
                               expansions=expansions, limit=24)
        if not direct:
            raise WikiV2Unavailable("wiki_chunks empty or no match "
                                    "(backfill pending?)")

        # ── Graph expansion (the leash: depth, priority, cap, tags) ──────
        # Fail-open: expansion is best-effort. Direct hits already succeeded,
        # so any error here (graph build, neighbor lookup, chunk fetch)
        # degrades to direct-only — never crash the query, never fall all
        # the way back to the keyword path.
        expanded: dict[str, tuple[dict, str]] = {}
        try:
            depth = EXPAND_DEPTH.get(intent, 1)
            graph = _graph_for(aid)
            # Frontier: top-10 direct pages. Exclusion: EVERY direct page —
            # a page already in direct results must never reappear tagged
            # as an expanded hit (direct wins).
            hit_pages = list(dict.fromkeys(r["page_path"] for r in direct[:10]))
            direct_pages = {r["page_path"] for r in direct}
            frontier = hit_pages
            for _hop in range(depth):
                nxt: list[str] = []
                for page in frontier:
                    for npath, etype in graph.neighbors(page, limit=NEIGHBOR_CAP):
                        if npath in direct_pages or npath in expanded:
                            continue
                        if len(expanded) >= NEIGHBOR_CAP:
                            break
                        row = _best_chunk_for_page(conn, aid, npath, q_vecs[0])
                        if row:
                            expanded[npath] = (row, f"{page} —{etype}→ {npath}")
                            nxt.append(npath)
                frontier = nxt
                if len(expanded) >= NEIGHBOR_CAP:
                    break
        except Exception:
            _log.warning("graph expansion failed; degrading to direct-only "
                         "(%d expanded pages kept)", len(expanded),
                         exc_info=True)

    # ── Rerank direct + expanded together ─────────────────────────────────
    tagged: list[tuple[dict, str | None]] = [(r, None) for r in direct]
    tagged += [(row, via) for row, via in expanded.values()]
    shapes = [_to_rerank_shape(r) for r, _ in tagged]
    via_by_id = {id(s): via for s, (_, via) in zip(shapes, tagged)}
    scored = rerank_score(question, shapes)

    # Temporal questions use the HISTORY boost table regardless of the
    # classified intent (spec §5.10) — still soft multipliers only.
    boost_key = "HISTORY" if _TEMPORAL_RE.search(question) else intent
    boosts = TYPE_BOOSTS.get(boost_key, {})
    hits: list[ChunkHit] = []
    for shape, base in scored:
        mult = boosts.get(shape.get("page_type", ""), 1.0)
        hits.append(ChunkHit(
            page_path=shape["page_path"],
            section_anchor=shape.get("section_anchor", ""),
            section_title=shape.get("section_title", ""),
            page_type=shape.get("page_type", ""),
            chunk_text=shape["chunk_text"],
            last_updated=shape.get("last_updated"),
            score=float(base) * mult,
            related_via=via_by_id.get(id(shape)),
        ))
    hits.sort(key=lambda h: h.score, reverse=True)
    return hits[:top_k]
