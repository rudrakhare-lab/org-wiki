"""New wiki read tools for the ingestion phase-1 agent.

wiki_list_pages   — list all pages in a category (modules, entities, etc.)
wiki_check_duplicate — check whether a slug already exists on disk
"""
from __future__ import annotations

import pathlib

from backend import wiki_retriever, wiki_schema


def _wiki_dir() -> pathlib.Path:
    """Return the active agent's wiki directory (resolved at call time)."""
    from backend import agent_context
    return pathlib.Path(agent_context.get_current_agent().wiki_dir)

# ── wiki_list_pages ──────────────────────────────────────────────────────────

WIKI_LIST_PAGES_SCHEMA: dict = {
    "name": "wiki_list_pages",
    "description": (
        "List all existing wiki pages, optionally filtered by category "
        "(modules, entities, sources, concepts, decisions, cross-module, configs). "
        "Use this at the start of ingestion to know what already exists."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "category": {
                "type": "string",
                "description": (
                    "Filter to one category folder. "
                    "One of: modules, entities, sources, concepts, decisions, "
                    "cross-module, configs, integrations, persons. "
                    "Omit to list all pages."
                ),
            }
        },
        "required": [],
    },
}


def _wiki_list_pages_handler(inp: dict) -> dict:
    category = inp.get("category", "").strip().lower()

    if category and category not in wiki_schema.ALL_CATEGORIES:
        return {"error": f"Unknown category: {category!r}", "code": "unknown_category"}

    wiki_dir = _wiki_dir()
    search_root = wiki_dir / category if category else wiki_dir

    pages = []
    if search_root.is_dir():
        for path in sorted(search_root.rglob("*.md")):
            slug = path.stem
            rel_path = str(path.relative_to(wiki_dir))
            try:
                text = path.read_text(encoding="utf-8")
            except OSError:
                text = ""
            title = wiki_retriever._extract_title(text, fallback=slug)
            pages.append({"path": rel_path, "title": title, "slug": slug})

    return {"pages": pages, "total": len(pages)}


# ── wiki_check_duplicate ─────────────────────────────────────────────────────

WIKI_CHECK_DUPLICATE_SCHEMA: dict = {
    "name": "wiki_check_duplicate",
    "description": (
        "Check whether a wiki page already exists for a given slug and category. "
        "Always call this before proposing to create a new page."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "slug": {
                "type": "string",
                "description": "The page slug, e.g. 'visitor-management'",
            },
            "category": {
                "type": "string",
                "description": (
                    "The category folder to check. "
                    "One of: modules, entities, sources, concepts, decisions, "
                    "cross-module, configs."
                ),
            },
        },
        "required": ["slug", "category"],
    },
}


def _wiki_check_duplicate_handler(inp: dict) -> dict:
    slug = str(inp.get("slug", "")).strip()
    category = str(inp.get("category", "")).strip().lower()

    if not slug:
        return {"error": "slug is required", "code": "missing_input"}
    if category not in wiki_schema.ALL_CATEGORIES:
        return {"error": f"Unknown category: {category!r}", "code": "unknown_category"}

    wiki_dir = _wiki_dir()
    candidate = wiki_dir / category / f"{slug}.md"
    exists = candidate.exists()
    return {
        "exists": exists,
        "path": str(candidate.relative_to(wiki_dir)) if exists else None,
    }
