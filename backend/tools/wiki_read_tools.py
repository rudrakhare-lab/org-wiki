"""New wiki read tools for the ingestion phase-1 agent.

wiki_list_pages   — list all pages in a category (modules, entities, etc.)
wiki_check_duplicate — check whether a slug already exists on disk
"""
from __future__ import annotations

import os
import pathlib

from backend import wiki_retriever

# Resolved at import time so tests can patch it
WIKI_ROOT = str(pathlib.Path(__file__).resolve().parents[2])

CATEGORY_DIRS = {
    "modules": "wiki/modules",
    "entities": "wiki/entities",
    "sources": "wiki/sources",
    "concepts": "wiki/concepts",
    "decisions": "wiki/decisions",
    "cross-module": "wiki/cross-module",
    "configs": "wiki/configs",
    "integrations": "wiki/integrations",
    "persons": "wiki/persons",
    "patterns": "wiki/patterns",
}

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
    all_pages = wiki_retriever.all_pages()

    if category and category in CATEGORY_DIRS:
        prefix = f"wiki/{category}/"
        filtered = [p for p in all_pages if p.path.startswith(prefix)]
    else:
        filtered = all_pages

    pages = []
    for p in filtered:
        slug = pathlib.Path(p.path).stem
        pages.append({"path": p.path, "title": p.title, "slug": slug})

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
    if category not in CATEGORY_DIRS:
        return {"error": f"Unknown category: {category!r}", "code": "unknown_category"}

    rel_dir = CATEGORY_DIRS[category]
    candidate = pathlib.Path(WIKI_ROOT) / rel_dir / f"{slug}.md"
    exists = candidate.exists()
    return {
        "exists": exists,
        "path": str(candidate.relative_to(WIKI_ROOT)) if exists else None,
    }
