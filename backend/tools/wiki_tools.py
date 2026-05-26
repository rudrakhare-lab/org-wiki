"""
Wiki tools — search and read wiki pages.

Security:
  wiki_read_page: only allows paths under wiki/. Blocks .. traversal
  and absolute paths at both string level and filesystem level.
"""
from __future__ import annotations

from backend import wiki_retriever
from backend.config import WIKI_DIR
# Note: the old `from backend.wiki_proposals import create_proposal` was
# removed in Track A Sub-pass B. The structured wiki_propose_* tools live in
# backend/tools/wiki_propose_tools.py and call typed creators directly.

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
        "Read the content of a specific wiki page by its relative path "
        "(e.g. 'modules/visitor-management.md', 'configs/visitor.md'). "
        "Use this after wiki_search to get complete documentation for a relevant page. "
        "Only pages under the wiki/ directory are accessible.\n\n"
        "G09/G20: returns the full page by default. For very long pages "
        "(synthesized pattern pages, auto-enriched modules), pass `offset` "
        "and `limit` to paginate. Response includes `total_length`, "
        "`has_more`, and `next_offset` so the model can decide whether to "
        "continue reading."
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
            "offset": {
                "type": "integer",
                "description": "Optional: byte offset into the page content. Default 0 (start).",
            },
            "limit": {
                "type": "integer",
                "description": (
                    "Optional: maximum chars to return. Omit/None = return full page (current behavior). "
                    "Set explicitly for pagination on long pages."
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

    # Track A: prefer the in-memory index (fast, gives a parsed title), but
    # fall back to reading directly from disk for files NOT in the index —
    # log.md is intentionally excluded from indexing (WIKI_INDEX_EXCLUDE) and
    # freshly-applied pages may not have been re-indexed yet. Anything under
    # wiki/ that the path-traversal guards approve is fair game.
    page = wiki_retriever.get_page(path)
    if page is not None:
        title = page.title
        full = page.full_text or ""
    else:
        # Disk fallback. resolved was computed above by the path-traversal
        # guard; it's already verified to be under wiki/.
        if not resolved.is_file():
            return {"error": f"Page not found: {path}", "code": "not_found"}
        try:
            full = resolved.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            return {"error": f"Could not read page: {exc}", "code": "io_error"}
        # Title fallback: first H1 or the filename stem
        title = resolved.stem
        for line in full.splitlines():
            stripped = line.strip()
            if stripped.startswith("# "):
                title = stripped[2:].strip() or title
                break
    page_path_out = path
    total = len(full)
    raw_offset = inp.get("offset")
    raw_limit = inp.get("limit")
    offset = max(0, int(raw_offset)) if raw_offset is not None else 0
    if raw_limit is None:
        end = total
    else:
        end = min(total, offset + max(0, int(raw_limit)))
    content = full[offset:end]
    has_more = end < total
    return {
        "path": page_path_out,
        "title": title,
        "content": content,
        "total_length": total,
        "offset": offset,
        "has_more": has_more,
        "next_offset": end if has_more else None,
    }


WIKI_GREP_SCHEMA: dict = {
    "name": "wiki_grep",
    "description": (
        "Literal or regex grep across all wiki pages. Use this when you need "
        "DETERMINISTIC matching — e.g. 'every wiki page that mentions TS-12345' "
        "or 'every config catalog page that contains the property kioskRequireOTP'. "
        "Returns the matching line plus ±2 lines of surrounding context per hit.\n\n"
        "When NOT to call: do not use this in place of wiki_search for "
        "semantic/relevance ranking — wiki_search returns ranked excerpts which "
        "is better for 'what's relevant to this topic?'. wiki_grep is for "
        "completeness ('find ALL pages that cite X') where ranking would lose hits."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "pattern": {
                "type": "string",
                "description": "Substring (default) or regex pattern to match against each line.",
            },
            "regex": {
                "type": "boolean",
                "description": "If true, `pattern` is a Python regex; case-insensitive. Default false (substring match).",
                "default": False,
            },
            "path_glob": {
                "type": "string",
                "description": (
                    "Optional fnmatch-style glob to filter which pages are searched, "
                    "e.g. 'modules/*.md' or 'configs/*'. Default: search all wiki pages."
                ),
            },
            "max_matches": {
                "type": "integer",
                "description": "Cap on returned matches across all pages. Default 50.",
            },
        },
        "required": ["pattern"],
    },
}


# Old free-text WIKI_PROPOSE_EDIT_SCHEMA and _wiki_propose_edit_handler were
# REPLACED in Track A Sub-pass B by structured propose tools in
# backend/tools/wiki_propose_tools.py. The new wiki_propose_edit takes
# old_string/new_string instead of a free-text proposed_change. Existing
# pending proposals from the old shape are auto-tagged proposal_type="legacy_text"
# on load and surfaced via wiki_proposals.warn_if_legacy_pending() at startup.


# ── G13: wiki_grep — literal/regex grep across all wiki pages ─────────────────

import fnmatch
import re as _re

_CONTEXT_LINES = 2  # ±N lines around each match
_DEFAULT_MAX_MATCHES = 50


def _wiki_grep_handler(inp: dict) -> dict:
    """Iterate wiki_retriever's in-memory page index and return matches with
    ±2 lines of surrounding context. Complements wiki_search (ranked) with
    deterministic completeness semantics."""
    pattern = str(inp.get("pattern") or "").strip()
    if not pattern:
        return {"error": "pattern is required", "code": "missing_input"}

    use_regex = bool(inp.get("regex", False))
    path_glob = inp.get("path_glob")
    if path_glob is not None:
        path_glob = str(path_glob).strip() or None
    max_matches = int(inp.get("max_matches") or _DEFAULT_MAX_MATCHES)

    matcher: object
    if use_regex:
        try:
            matcher = _re.compile(pattern, _re.IGNORECASE)
        except _re.error as exc:
            return {"error": f"Invalid regex: {exc}", "code": "invalid_pattern"}

        def hit(line: str) -> bool:
            return bool(matcher.search(line))  # type: ignore[union-attr]
    else:
        needle = pattern.lower()

        def hit(line: str) -> bool:
            return needle in line.lower()

    matches: list[dict] = []
    truncated = False
    for path in wiki_retriever.all_paths():
        if path_glob and not fnmatch.fnmatch(path, path_glob):
            continue
        page = wiki_retriever.get_page(path)
        if page is None:
            continue
        lines = (page.full_text or "").splitlines()
        for i, line in enumerate(lines):
            if not hit(line):
                continue
            if len(matches) >= max_matches:
                truncated = True
                break
            start = max(0, i - _CONTEXT_LINES)
            end = min(len(lines), i + _CONTEXT_LINES + 1)
            matches.append({
                "path": page.path,
                "line_number": i + 1,  # 1-indexed for display
                "line_text": line,
                "surrounding_context": "\n".join(lines[start:end]),
            })
        if truncated:
            break

    return {
        "pattern": pattern,
        "regex": use_regex,
        "path_glob": path_glob,
        "matches": matches,
        "total_matches": len(matches),
        "has_more": truncated,
    }
