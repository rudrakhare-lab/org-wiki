"""Wiki knowledge graph API.

GET /api/wiki/graph — returns {nodes, links} suitable for force-graph rendering.

Nodes:  {id, label, type, path, val}   where val = degree (for node sizing)
Links:  {source, target}                deduped, undirected
"""
from __future__ import annotations

import pathlib
import re

from fastapi import APIRouter

from backend import db

router = APIRouter(prefix="/api/wiki")

_WIKI_DIR = pathlib.Path(__file__).resolve().parent.parent / "wiki"

_SKIP: set[str] = set()  # show all pages


def _page_type(text: str) -> str:
    parts = text.split("---\n", 2)
    if len(parts) < 3:
        return "unknown"
    m = re.search(r"^type:\s*(\S+)", parts[1], re.MULTILINE)
    return m.group(1).strip("'\"") if m else "unknown"


def _extract_links(text: str) -> list[str]:
    # [[target]] or [[target|alias]] or [[target#anchor]]
    return re.findall(r"\[\[([^\]|#]+?)(?:[|#][^\]]+)?\]\]", text)


def _add_config_layer(
    nodes: dict[str, dict],
    links: list[dict],
    seen: set[tuple[str, str]],
) -> None:
    """Overlay PMS config nodes and edges onto the wiki graph."""
    try:
        with db.connection() as con:
            # Build a jira_link_count lookup keyed by property_name
            jira_counts: dict[str, int] = {}
            for row in con.execute(
                "SELECT property_name, COUNT(*) AS cnt FROM jira_links GROUP BY property_name"
            ):
                jira_counts[row[0]] = row[1]

            # Add config nodes for each unique (property_name, service) pair
            for row in con.execute(
                "SELECT DISTINCT property_name, service FROM configs"
            ):
                property_name, service = row[0], row[1]
                node_id = f"configs/{property_name}"
                if node_id not in nodes:
                    nodes[node_id] = {
                        "id": node_id,
                        "label": property_name,
                        "type": "config",
                        "service": service,
                        "path": node_id,
                        "val": max(1, jira_counts.get(property_name, 0)),
                    }

            # Add service_match edges: config node → module node
            for row in con.execute(
                "SELECT property_name, module_slug FROM module_links WHERE link_type='service_match'"
            ):
                property_name, module_slug = row[0], row[1]
                source = f"configs/{property_name}"
                target = module_slug
                if source not in nodes or target not in nodes:
                    continue
                key = (min(source, target), max(source, target))
                if key in seen:
                    continue
                seen.add(key)
                links.append({"source": source, "target": target})

            # Add dependency edges
            for row in con.execute(
                "SELECT property_a, property_b, dep_type FROM dependencies WHERE confidence >= 0.7"
            ):
                source, target, dep_type = f"configs/{row[0]}", f"configs/{row[1]}", row[2]
                if source not in nodes or target not in nodes:
                    continue
                key = (min(source, target), max(source, target))
                if key in seen:
                    continue
                seen.add(key)
                links.append({"source": source, "target": target, "dep_type": dep_type})
    except Exception:
        # Config catalog unavailable — skip the overlay (graph still renders).
        return


@router.get("/graph")
async def wiki_graph(include_configs: bool = False) -> dict:
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

    if include_configs:
        _add_config_layer(nodes, links, seen)

    return {"nodes": list(nodes.values()), "links": links}
