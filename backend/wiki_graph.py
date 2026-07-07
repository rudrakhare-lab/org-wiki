"""One wiki knowledge graph, three consumers (spec §5.3).

Built from what already exists in the markdown: frontmatter relations
(depends_on / used_by / module / modules), structural pairs
(configs/X ↔ modules/X etc.), and [[wikilinks]]. In-memory, per-agent,
rebuilt whenever the wiki index rebuilds. Consumers: retrieval expansion
(wiki_v2), the UI force-graph API, and preflight's related-module fetch.
"""
from __future__ import annotations
import re
import threading
from dataclasses import dataclass

EDGE_PRIORITY: dict[str, int] = {
    "config_of": 0, "runbook_of": 0, "decision_for": 0,
    "depends_on": 1, "used_by": 1,
    "wikilink": 2,
}

_WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)")


@dataclass(frozen=True)
class Edge:
    src: str
    dst: str
    type: str


def _resolve(target: str, paths: set[str]) -> str | None:
    """Resolve a wikilink target to an existing page path."""
    t = target.strip().removesuffix(".md")
    for cand in (f"{t}.md", f"modules/{t}.md"):
        if cand in paths:
            return cand
    stem = t.rsplit("/", 1)[-1]
    matches = [p for p in paths if p.removesuffix(".md").rsplit("/", 1)[-1] == stem]
    return matches[0] if len(matches) == 1 else None


def _module_path(slug: str, paths: set[str]) -> str | None:
    p = f"modules/{slug}.md"
    return p if p in paths else None


def _listify(v) -> list[str]:
    if isinstance(v, list):
        return [str(x) for x in v]
    if isinstance(v, str) and v.strip():
        return [v.strip()]
    return []


class WikiGraph:
    def __init__(self, edges: list[Edge], node_count: int) -> None:
        self.edges = edges
        self.node_count = node_count
        self._adj: dict[str, list[tuple[str, str]]] = {}
        for e in edges:
            self._adj.setdefault(e.src, []).append((e.dst, e.type))
            self._adj.setdefault(e.dst, []).append((e.src, e.type))

    def neighbors(self, page_path: str, types: tuple[str, ...] | None = None,
                  limit: int | None = None) -> list[tuple[str, str]]:
        seen: dict[str, str] = {}
        for dst, t in self._adj.get(page_path, []):
            if types and t not in types:
                continue
            # keep the highest-priority edge type per neighbor
            if dst not in seen or EDGE_PRIORITY[t] < EDGE_PRIORITY[seen[dst]]:
                seen[dst] = t
        out = sorted(seen.items(), key=lambda kv: (EDGE_PRIORITY[kv[1]], kv[0]))
        return out[:limit] if limit else out


def build_graph(pages: dict) -> WikiGraph:
    """pages: {path: WikiPage} — the wiki_retriever index's page map."""
    paths = set(pages)
    edges: set[Edge] = set()

    for path, page in pages.items():
        fm = page.frontmatter or {}

        for slug in _listify(fm.get("depends_on")):
            dst = _module_path(slug, paths)
            if dst:
                edges.add(Edge(path, dst, "depends_on"))
        for slug in _listify(fm.get("used_by")):
            dst = _module_path(slug, paths)
            if dst:
                edges.add(Edge(path, dst, "used_by"))

        if path.startswith("configs/"):
            slug = path.removeprefix("configs/").removesuffix(".md")
            for s in _listify(fm.get("module")) or [slug]:
                dst = _module_path(s, paths)
                if dst:
                    edges.add(Edge(path, dst, "config_of"))
        if path.startswith("runbooks/"):
            for s in _listify(fm.get("module")) + _listify(fm.get("modules")):
                dst = _module_path(s, paths)
                if dst:
                    edges.add(Edge(path, dst, "runbook_of"))
        if path.startswith("decisions/"):
            for s in _listify(fm.get("modules")):
                dst = _module_path(s, paths)
                if dst:
                    edges.add(Edge(path, dst, "decision_for"))

        for m in _WIKILINK_RE.finditer(page.full_text):
            dst = _resolve(m.group(1), paths)
            if dst and dst != path:
                edges.add(Edge(path, dst, "wikilink"))

    return WikiGraph(sorted(edges, key=lambda e: (e.src, e.dst, e.type)),
                     node_count=len(paths))


# ── Per-agent cache (mirrors wiki_retriever._INDICES) ────────────────────────
_GRAPHS: dict[str, WikiGraph] = {}
_lock = threading.RLock()


def get_graph(agent_id: str | None = None) -> WikiGraph:
    from backend import agent_context, wiki_retriever
    aid = agent_id or agent_context.get_current_agent_id()
    with _lock:
        g = _GRAPHS.get(aid)
    if g is None:
        idx = wiki_retriever.get_index(aid)
        g = build_graph(idx.pages())
        with _lock:
            _GRAPHS[aid] = g
    return g


def invalidate(agent_id: str | None = None) -> None:
    from backend import agent_context
    aid = agent_id or agent_context.get_current_agent_id()
    with _lock:
        _GRAPHS.pop(aid, None)
