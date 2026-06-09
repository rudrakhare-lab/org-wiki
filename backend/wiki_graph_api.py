"""Wiki knowledge graph API.

GET /api/wiki/graph — returns {nodes, links} suitable for force-graph rendering.

Nodes:  {id, label, type, path, val}   where val = degree (for node sizing)
Links:  {source, target}                deduped, undirected
"""
from __future__ import annotations

import pathlib
import re

from fastapi import APIRouter

router = APIRouter(prefix="/api/wiki")

_WIKI_DIR = pathlib.Path(__file__).resolve().parent.parent / "wiki"

_SKIP = {
    "index.md",   # links to every page → fake mega-hub, distorts the graph
    "log.md",     # chronological operation log, not a semantic content page
}


def _page_type(text: str) -> str:
    parts = text.split("---\n", 2)
    if len(parts) < 3:
        return "unknown"
    m = re.search(r"^type:\s*(\S+)", parts[1], re.MULTILINE)
    return m.group(1).strip("'\"") if m else "unknown"


def _extract_links(text: str) -> list[str]:
    # [[target]] or [[target|alias]] or [[target#anchor]]
    return re.findall(r"\[\[([^\]|#]+?)(?:[|#][^\]]+)?\]\]", text)


@router.get("/graph")
async def wiki_graph() -> dict:
    nodes: dict[str, dict] = {}
    texts: dict[str, str] = {}

    for path in sorted(_WIKI_DIR.rglob("*.md")):
        if path.name in _SKIP:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue

        node_id = str(path.relative_to(_WIKI_DIR)).replace("\\", "/").removesuffix(".md")
        label = path.stem.replace("-", " ").replace("_", " ").title()
        nodes[node_id] = {
            "id": node_id,
            "label": label,
            "type": _page_type(text),
            "path": node_id,
            "val": 1,
        }
        texts[node_id] = text

    # Build edges
    seen: set[tuple[str, str]] = set()
    links: list[dict] = []
    degree: dict[str, int] = {k: 0 for k in nodes}

    for node_id, text in texts.items():
        for raw in _extract_links(text):
            target = raw.strip().removesuffix(".md")
            if target not in nodes or target == node_id:
                continue
            key = (min(node_id, target), max(node_id, target))
            if key in seen:
                continue
            seen.add(key)
            links.append({"source": node_id, "target": target})
            degree[node_id] = degree.get(node_id, 0) + 1
            degree[target] = degree.get(target, 0) + 1

    for nid, d in degree.items():
        nodes[nid]["val"] = max(1, d)

    return {"nodes": list(nodes.values()), "links": links}
