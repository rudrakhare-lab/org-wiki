"""
Wiki tools — search and read wiki pages.

Security:
  wiki_read_page: only allows paths under wiki/. Blocks .. traversal
  and absolute paths at both string level and filesystem level.
"""
from __future__ import annotations

from backend import wiki_retriever
from backend.config import WIKI_DIR

# ── Schemas ───────────────────────────────────────────────────────────────────

WIKI_SEARCH_SCHEMA: dict = {
    "name": "wiki_search",
    "description": (
        "Search the WorkInSync wiki for pages relevant to a question, topic, module, "
        "or config property name. Returns ranked excerpts from matching pages. "
        "Use this as a first step for any question about product features, modules, "
        "or architecture. Call wiki_read_page to get the full content of a promising result."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query — a question, topic, feature name, or property name.",
            },
            "top_n": {
                "type": "integer",
                "description": "Number of results to return. Default 5, max 10.",
                "default": 5,
                "minimum": 1,
                "maximum": 10,
            },
        },
        "required": ["query"],
    },
}

WIKI_READ_PAGE_SCHEMA: dict = {
    "name": "wiki_read_page",
    "description": (
        "Read the full content of a specific wiki page by its relative path "
        "(e.g. 'modules/visitor-management.md', 'configs/visitor.md'). "
        "Use this after wiki_search to get complete documentation for a relevant page. "
        "Only pages under the wiki/ directory are accessible."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": (
                    "Relative path to the wiki page, e.g. 'modules/visitor-management.md' "
                    "or 'configs/meeting-rooms.md'. Do not include 'wiki/' prefix."
                ),
            },
        },
        "required": ["path"],
    },
}


# ── Handlers ──────────────────────────────────────────────────────────────────

def _wiki_search_handler(inp: dict) -> dict:
    query = str(inp.get("query", "")).strip()
    if not query:
        return {"error": "query is required", "code": "missing_input"}
    top_n = min(int(inp.get("top_n", 5)), 10)
    pages = wiki_retriever.search(query, top_n=top_n)
    return {
        "results": [
            {
                "path": p.path,
                "title": p.title,
                "excerpt": p.excerpt(300),
            }
            for p in pages
        ],
        "total": len(pages),
    }


def _wiki_read_page_handler(inp: dict) -> dict:
    path = str(inp.get("path", "")).strip()
    if not path:
        return {"error": "path is required", "code": "missing_input"}

    # Layer 1: string-level checks (fast, catches the obvious cases)
    if ".." in path or path.startswith("/"):
        return {"error": "Path traversal not allowed.", "code": "path_traversal"}

    # Layer 2: filesystem containment check (catches symlink-based escapes)
    try:
        resolved = (WIKI_DIR / path).resolve()
        wiki_root = WIKI_DIR.resolve()
        # The resolved path must be the wiki root itself or a descendant
        if resolved != wiki_root and wiki_root not in resolved.parents:
            return {"error": "Path outside wiki directory.", "code": "path_traversal"}
    except Exception:
        return {"error": "Invalid path.", "code": "path_traversal"}

    page = wiki_retriever.get_page(path)
    if page is None:
        return {"error": f"Page not found: {path}", "code": "not_found"}
    return {"path": page.path, "title": page.title, "content": page.full_text}


WIKI_PROPOSE_EDIT_SCHEMA = {
    "name": "wiki_propose_edit",
    "description": (
        "Submit a proposed correction to a wiki page for admin review. "
        "Use when tool results contradict existing wiki content or you spot an error. "
        "Does NOT write directly to the wiki — creates a proposal requiring admin approval."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "page_path": {
                "type": "string",
                "description": "Relative wiki path, e.g. 'modules/visitor-management.md'",
            },
            "proposed_change": {
                "type": "string",
                "description": "What is incorrect and what it should say instead.",
            },
            "answer_id": {
                "type": "string",
                "description": "The answer_id this proposal is based on (optional).",
            },
        },
        "required": ["page_path", "proposed_change"],
    },
}


def _wiki_propose_edit_handler(inp: dict) -> dict:
    """Write a proposal to wiki_proposals.jsonl — never to wiki/."""
    from backend.wiki_proposals import create_proposal

    page_path = str(inp.get("page_path", "")).strip()
    proposed_change = str(inp.get("proposed_change", "")).strip()
    answer_id = inp.get("answer_id")

    if not page_path or not proposed_change:
        return {"error": "page_path and proposed_change are required", "code": "missing_fields"}

    proposal_id = create_proposal(
        page_path=page_path,
        proposed_change=proposed_change,
        submitter_email="agent",
        answer_id=answer_id,
    )
    return {
        "status": "submitted",
        "proposal_id": proposal_id,
        "message": (
            f"Proposal submitted for admin review. "
            f"The wiki page '{page_path}' has NOT been changed. "
            "An admin will review and apply or reject this proposal."
        ),
    }
