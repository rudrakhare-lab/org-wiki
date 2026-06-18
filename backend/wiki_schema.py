"""Per-schema wiki conventions — the single source of truth.

Conwo (schema_kind='workinsync') keeps its WorkInSync page-types; created agents
(schema_kind='generic') use a domain-neutral set. Scattered hardcoded lists across
the backend route through this module so the two schemas never silently diverge.

Zero dependency on agent_registry: callers pass a schema_kind string (or an object
with a .schema_kind attribute), so tools can import this cheaply and resolve the
active agent's kind via agent_context.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class SchemaConventions:
    kind: str
    categories: tuple[str, ...]
    propose_allowlist: tuple[str, ...]
    page_types: dict[str, dict]  # name -> {"label": str, "color": str}


WORKINSYNC = SchemaConventions(
    kind="workinsync",
    categories=("modules", "entities", "sources", "concepts", "decisions",
                "cross-module", "configs", "integrations", "persons", "patterns"),
    propose_allowlist=("concepts/", "cross-module/", "decisions/", "answers/",
                       "sources/", "entities/"),
    page_types={
        "module": {"label": "Module", "color": "#3b82f6"},
        "entity": {"label": "Entity", "color": "#22c55e"},
        "concept": {"label": "Concept", "color": "#a855f7"},
        "config": {"label": "Config", "color": "#f59e0b"},
        "decision": {"label": "Decision", "color": "#ef4444"},
        "source": {"label": "Source", "color": "#94a3b8"},
        "cross-module": {"label": "Cross-Module", "color": "#14b8a6"},
        "integration": {"label": "Integration", "color": "#eab308"},
        "person": {"label": "Person", "color": "#ec4899"},
        "pattern": {"label": "Pattern", "color": "#f97316"},
    },
)

GENERIC = SchemaConventions(
    kind="generic",
    categories=("concepts", "relationships", "topics", "entities", "sources", "decisions"),
    propose_allowlist=("concepts/", "relationships/", "topics/", "entities/",
                       "decisions/", "sources/", "answers/"),
    page_types={
        "concept": {"label": "Concept", "color": "#a855f7"},
        "relationships": {"label": "Relationship", "color": "#14b8a6"},
        "topics": {"label": "Topic", "color": "#3b82f6"},
        "entity": {"label": "Entity", "color": "#22c55e"},
        "source": {"label": "Source", "color": "#94a3b8"},
        "decision": {"label": "Decision", "color": "#ef4444"},
    },
)

_BY_KIND = {"workinsync": WORKINSYNC, "generic": GENERIC}

ALL_CATEGORIES: frozenset[str] = frozenset(
    c for s in _BY_KIND.values() for c in s.categories
)

SCALAR_FRONTMATTER_FIELDS: frozenset[str] = frozenset({
    "type", "status", "owner", "module", "last_updated", "ingested",
    "doc_type", "date", "auto_generated", "human_edited", "cluster_id",
    "category", "slug", "title",
})

RELATION_FRONTMATTER_FIELDS: frozenset[str] = frozenset({
    "party_a", "party_b", "sourced_from", "related_concepts", "related_modules",
    "related_topics", "related_decisions", "related_entities", "depends_on",
    "used_by", "related",
})


def for_kind(kind: str | None) -> SchemaConventions:
    return _BY_KIND.get((kind or "").strip().lower(), WORKINSYNC)


def for_agent(agent) -> SchemaConventions:
    return for_kind(getattr(agent, "schema_kind", None))


def page_type(text: str) -> str:
    """Resolve a page's node type from frontmatter: `type:` wins, then `category:`."""
    parts = text.split("---\n", 2)
    if len(parts) < 3:
        return "unknown"
    fm = parts[1]
    for key in ("type", "category"):
        m = re.search(rf"^{key}:\s*(\S+)", fm, re.MULTILINE)
        if m:
            return m.group(1).strip("'\"")
    return "unknown"
