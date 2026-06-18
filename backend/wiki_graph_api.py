"""Wiki knowledge graph API.

GET /api/wiki/graph — returns {nodes, links} suitable for force-graph rendering.

Nodes:  {id, label, type, path, val}   where val = degree (for node sizing)
Links:  {source, target}                deduped, undirected
"""
from __future__ import annotations

import re

from fastapi import APIRouter

from backend import agent_context, db

router = APIRouter(prefix="/api/wiki")

_SKIP: set[str] = set()  # show all pages


def _page_type(text: str) -> str:
    from backend import wiki_schema
    return wiki_schema.page_type(text)


def _extract_links(text: str) -> list[str]:
    # [[target]] or [[target|alias]] or [[target#anchor]]
    return re.findall(r"\[\[([^\]|#]+?)(?:[|#][^\]]+)?\]\]", text)


# A page-path reference in frontmatter, e.g. `wiki/concepts/due-diligence.md` or
# `concepts/due-diligence.md`. The generic wiki schema expresses relationships through
# frontmatter fields (party_a/party_b on relationships/ pages, sourced_from on concepts,
# related_concepts on sources, depends_on/used_by, ...) whose values are these paths —
# NOT [[wikilinks]]. Only relationship fields ever hold `.md` paths (tags/title/slug/
# author never do), so extracting every such path from the frontmatter block yields the
# real edges without false positives.
_FM_REF_RE = re.compile(r"(?:wiki/)?[\w\-]+(?:/[\w\-]+)+\.md")


def _frontmatter_refs(text: str) -> list[str]:
    """Return page-path references found in the page's frontmatter block."""
    parts = text.split("---\n", 2)
    if len(parts) < 3:
        return []
    return _FM_REF_RE.findall(parts[1])


def _frontmatter_relation_values(text: str) -> list[str]:
    """Values of known relationship frontmatter fields — scalars, inline lists, or
    YAML list items. Captures bare slugs/titles AND paths (party_a: corporate-compliance,
    related: [a, b], sourced_from:\n  - wiki/sources/x.md)."""
    parts = text.split("---\n", 2)
    if len(parts) < 3:
        return []
    from backend import wiki_schema
    rel = wiki_schema.RELATION_FRONTMATTER_FIELDS
    out: list[str] = []
    cur_rel = False
    for line in parts[1].splitlines():
        m = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if m:
            key, val = m.group(1).strip().lower(), m.group(2).strip()
            cur_rel = key in rel
            if cur_rel and val and val not in ("[]", "''", '""'):
                if val.startswith("[") and val.endswith("]"):
                    out += [v.strip().strip('"\'') for v in val[1:-1].split(",") if v.strip()]
                else:
                    out.append(val.strip('"\''))
            continue
        lm = re.match(r"^\s*-\s*(.+)$", line)
        if lm and cur_rel:
            out.append(lm.group(1).strip().strip('"\''))
    return out


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
    agent = agent_context.get_current_agent()
    wiki_dir = agent.wiki_dir

    nodes: dict[str, dict] = {}
    texts: dict[str, str] = {}

    for path in sorted(wiki_dir.rglob("*.md")):
        if path.name in _SKIP:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue

        node_id = str(path.relative_to(wiki_dir)).replace("\\", "/").removesuffix(".md")
        label = path.stem.replace("-", " ").replace("_", " ").title()
        nodes[node_id] = {
            "id": node_id,
            "label": label,
            "type": _page_type(text),
            "path": node_id,
            "val": 1,
        }
        texts[node_id] = text

    # ── Build edges (format-agnostic reference resolution) ──────────────────
    # Resolve a reference written as a full path, a bare slug, or a title to a node id.
    slug_to_id: dict[str, str] = {}
    title_to_id: dict[str, str] = {}
    for nid, n in nodes.items():
        slug_to_id.setdefault(nid.rsplit("/", 1)[-1], nid)
        title_to_id.setdefault(str(n["label"]).strip().lower(), nid)

    def _resolve(ref: str) -> str | None:
        r = ref.strip().strip('"\'').removeprefix("wiki/").removesuffix(".md").strip()
        if not r:
            return None
        if r in nodes:
            return r
        seg = r.rsplit("/", 1)[-1]
        if seg in slug_to_id:
            return slug_to_id[seg]
        if r.replace("-", " ").lower() in title_to_id:
            return title_to_id[r.replace("-", " ").lower()]
        if r.lower() in title_to_id:
            return title_to_id[r.lower()]
        return None

    seen: set[tuple[str, str]] = set()
    links: list[dict] = []
    degree: dict[str, int] = {k: 0 for k in nodes}

    def _add(a: str, b: str | None) -> None:
        if not b or a == b:
            return
        key = (min(a, b), max(a, b))
        if key in seen:
            return
        seen.add(key)
        links.append({"source": a, "target": b})
        degree[a] = degree.get(a, 0) + 1
        degree[b] = degree.get(b, 0) + 1

    for node_id, text in texts.items():
        for raw in _extract_links(text) + _frontmatter_refs(text) + _frontmatter_relation_values(text):
            _add(node_id, _resolve(raw))
        # Relationship pages connect their endpoints by slug halves, even when the
        # frontmatter is sparse: relationships/<a>-<b>.md → edge to nodes a and b.
        if node_id.startswith("relationships/"):
            rslug = node_id.split("/", 1)[1]
            for other_id in list(nodes):
                if other_id == node_id:
                    continue
                oslug = other_id.rsplit("/", 1)[-1]
                if oslug and (rslug.startswith(oslug + "-") or rslug.endswith("-" + oslug)
                              or ("-" + oslug + "-") in ("-" + rslug + "-")):
                    _add(node_id, other_id)

    for nid, d in degree.items():
        nodes[nid]["val"] = max(1, d)

    if include_configs and agent.has_pms:
        _add_config_layer(nodes, links, seen)

    return {"nodes": list(nodes.values()), "links": links}
