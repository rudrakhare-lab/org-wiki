"""Wiki write tools — only registered in the Phase-2 ingest agent registry.

NEVER register these in the main query tool registry.
Safety properties:
- All paths validated to be inside wiki/ (no traversal)
- wiki_create_page refuses to overwrite existing files
- wiki_edit_page requires unique old_str (no silent multi-replace)
- wiki_rebuild_index calls wiki_retriever.build_index() in-process
  (does NOT touch backend/api.py — avoids the reload/wiki-destruction risk)
"""
from __future__ import annotations

import pathlib
import re

from backend import wiki_retriever


def _wiki_dir():
    """Return the active agent's wiki directory (resolved at call time)."""
    from backend import agent_context
    return agent_context.get_current_agent().wiki_dir

# Fields that are always scalars — never allow treating them as lists
_SCALAR_FIELDS = {"type", "status", "owner", "module", "last_updated", "ingested",
                  "doc_type", "date", "auto_generated", "human_edited", "cluster_id"}


def _safe_path(rel_path: str) -> pathlib.Path | None:
    """Return resolved Path if rel_path is inside wiki/, else None.

    Resolves the active agent's wiki_dir at call time so that the path is
    always relative to the correct agent's wiki directory.
    """
    wiki_dir = _wiki_dir()
    wiki_subdir = wiki_dir.resolve()
    # rel_path is already relative to wiki/ (e.g. "wiki/modules/foo.md"),
    # so join against the parent of wiki_dir to preserve the "wiki/" prefix.
    wiki_root = wiki_dir.parent
    candidate = (wiki_root / rel_path).resolve()
    try:
        candidate.relative_to(wiki_subdir)
        return candidate
    except ValueError:
        return None


# ── wiki_create_page ─────────────────────────────────────────────────────────

WIKI_CREATE_PAGE_SCHEMA: dict = {
    "name": "wiki_create_page",
    "description": (
        "Create a new wiki markdown page. Refuses to overwrite an existing file. "
        "Path must be inside wiki/ (e.g. 'wiki/modules/visitor-management.md')."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Relative path, e.g. wiki/modules/foo.md"},
            "frontmatter": {"type": "object", "description": "YAML frontmatter as a dict"},
            "body": {"type": "string", "description": "Markdown body below the frontmatter"},
        },
        "required": ["path", "frontmatter", "body"],
    },
}


def _wiki_create_page_handler(inp: dict) -> dict:
    rel = str(inp.get("path", "")).strip()
    target = _safe_path(rel)
    if target is None:
        return {"error": f"Path {rel!r} is outside wiki/", "code": "invalid_path"}
    if target.exists():
        return {"error": f"{rel} already exists", "code": "already_exists"}

    import yaml  # pyyaml, already in requirements

    fm = inp.get("frontmatter") or {}
    body = str(inp.get("body", ""))
    fm_str = yaml.dump(fm, default_flow_style=False, allow_unicode=True).strip()
    content = f"---\n{fm_str}\n---\n\n{body}\n"

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return {"created": True, "path": rel}


# ── wiki_edit_page ───────────────────────────────────────────────────────────

WIKI_EDIT_PAGE_SCHEMA: dict = {
    "name": "wiki_edit_page",
    "description": (
        "Targeted string replacement in an existing wiki page. "
        "old_str must appear exactly once — errors if not found or ambiguous."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "old_str": {"type": "string", "description": "Exact string to replace (must be unique in file)"},
            "new_str": {"type": "string", "description": "Replacement string"},
        },
        "required": ["path", "old_str", "new_str"],
    },
}


def _wiki_edit_page_handler(inp: dict) -> dict:
    rel = str(inp.get("path", "")).strip()
    target = _safe_path(rel)
    if target is None:
        return {"error": f"Path {rel!r} is outside wiki/", "code": "invalid_path"}
    if not target.exists():
        return {"error": f"{rel} does not exist", "code": "not_found"}

    old_str = str(inp.get("old_str", ""))
    new_str = str(inp.get("new_str", ""))
    text = target.read_text(encoding="utf-8")

    count = text.count(old_str)
    if count == 0:
        return {"error": f"old_str not found in {rel}", "code": "not_found"}
    if count > 1:
        return {"error": f"old_str appears {count} times in {rel} — provide more context", "code": "ambiguous"}

    target.write_text(text.replace(old_str, new_str, 1), encoding="utf-8")
    return {"edited": True, "path": rel}


# ── wiki_append_section ──────────────────────────────────────────────────────

WIKI_APPEND_SECTION_SCHEMA: dict = {
    "name": "wiki_append_section",
    "description": (
        "Append a new ## section to an existing wiki page. "
        "Errors if the heading already exists."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "heading": {"type": "string", "description": "Section heading text (without ##)"},
            "content": {"type": "string", "description": "Section body in markdown"},
        },
        "required": ["path", "heading", "content"],
    },
}


def _wiki_append_section_handler(inp: dict) -> dict:
    rel = str(inp.get("path", "")).strip()
    target = _safe_path(rel)
    if target is None:
        return {"error": f"Path {rel!r} is outside wiki/", "code": "invalid_path"}
    if not target.exists():
        return {"error": f"{rel} does not exist", "code": "not_found"}

    heading = str(inp.get("heading", "")).strip()
    content = str(inp.get("content", "")).strip()

    if not heading:
        return {"error": "heading cannot be empty", "code": "missing_input"}

    text = target.read_text(encoding="utf-8")

    # Check heading only in the body (after frontmatter)
    parts = text.split("---\n", 2)
    body_to_check = parts[2] if len(parts) >= 3 else text

    if f"## {heading}" in body_to_check:
        return {"error": f"Heading '## {heading}' already exists in {rel}", "code": "heading_exists"}

    new_text = text.rstrip() + f"\n\n## {heading}\n{content}\n"
    target.write_text(new_text, encoding="utf-8")
    return {"appended": True, "path": rel, "heading": heading}


# ── wiki_update_frontmatter ──────────────────────────────────────────────────

WIKI_UPDATE_FRONTMATTER_SCHEMA: dict = {
    "name": "wiki_update_frontmatter",
    "description": (
        "Append a value to a list field in an existing wiki page's frontmatter. "
        "Works with any list field: depends_on, used_by, modules, servers, alternate_paths, "
        "contributing_tickets, related_modules, or any new list field. "
        "No-ops if the value is already present. "
        "Cannot be used on scalar fields like type, status, owner."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "field": {"type": "string", "description": "List field name, e.g. 'used_by'"},
            "value": {"type": "string", "description": "Value to append, e.g. 'visitor-management'"},
        },
        "required": ["path", "field", "value"],
    },
}


def _wiki_update_frontmatter_handler(inp: dict) -> dict:
    rel = str(inp.get("path", "")).strip()
    target = _safe_path(rel)
    if target is None:
        return {"error": f"Path {rel!r} is outside wiki/", "code": "invalid_path"}
    if not target.exists():
        return {"error": f"{rel} does not exist", "code": "not_found"}

    field = str(inp.get("field", "")).strip()
    value = str(inp.get("value", "")).strip()

    if not value:
        return {"error": "value cannot be empty", "code": "missing_input"}
    if field in _SCALAR_FIELDS:
        return {"error": f"Field {field!r} is a scalar field and cannot be used as a list",
                "code": "scalar_field"}

    import yaml

    text = target.read_text(encoding="utf-8")

    # Split into frontmatter + body
    # Format: "---\n<yaml>\n---\n<body>"
    parts = text.split("---\n", 2)
    if len(parts) < 3:
        return {"error": "No frontmatter block found in file", "code": "no_frontmatter"}

    # parts[0] is empty string before first "---\n"
    # parts[1] is the YAML content
    # parts[2] is the body after second "---\n"
    fm_str = parts[1]
    body = parts[2]

    try:
        fm = yaml.safe_load(fm_str) or {}
    except yaml.YAMLError as e:
        return {"error": f"Cannot parse frontmatter: {e}", "code": "parse_error"}

    # Get or initialize the list field
    current = fm.get(field)
    if current is None:
        current = []  # new field — create as list
    elif isinstance(current, list):
        pass  # already a list
    elif isinstance(current, str):
        current = [current]  # upgrade single string to list
    elif isinstance(current, (int, float, bool)):
        # Existing scalar value — refuse to corrupt it
        return {"error": f"Field {field!r} exists as a scalar ({current!r}), not a list",
                "code": "scalar_field"}
    else:
        current = list(current)

    if value in current:
        return {"updated": True, "path": rel, "note": "already present — no change"}

    current.append(value)
    fm[field] = current

    new_fm_str = yaml.dump(fm, default_flow_style=False, allow_unicode=True)
    new_text = f"---\n{new_fm_str}---\n{body}"
    target.write_text(new_text, encoding="utf-8")
    return {"updated": True, "path": rel}


# ── wiki_rebuild_index ───────────────────────────────────────────────────────

WIKI_REBUILD_INDEX_SCHEMA: dict = {
    "name": "wiki_rebuild_index",
    "description": (
        "Rebuild the in-memory wiki search index after all pages have been written. "
        "Call this as the final step after all wiki_create_page / wiki_edit_page calls."
    ),
    "input_schema": {"type": "object", "properties": {}, "required": []},
}


def _wiki_rebuild_index_handler(_inp: dict) -> dict:
    try:
        wiki_retriever.build_index()
        count = wiki_retriever.page_count()
        return {"rebuilt": True, "pages_indexed": count}
    except Exception as exc:
        return {"error": str(exc), "code": "rebuild_failed"}
