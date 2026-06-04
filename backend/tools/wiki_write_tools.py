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

WIKI_ROOT = str(pathlib.Path(__file__).resolve().parents[2])
_WIKI_SUBDIR = str(pathlib.Path(WIKI_ROOT) / "wiki")

LIST_FIELDS = {"depends_on", "used_by", "modules", "servers"}


def _safe_path(rel_path: str) -> pathlib.Path | None:
    """Return resolved Path if rel_path is inside wiki/, else None.

    Reads WIKI_ROOT at call time (not module load time) so that tests can
    patch the module-level constant and have _safe_path reflect the new value.
    """
    wiki_root = pathlib.Path(WIKI_ROOT)
    wiki_subdir = (wiki_root / "wiki").resolve()
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
    text = target.read_text(encoding="utf-8")

    if f"## {heading}" in text:
        return {"error": f"Heading '## {heading}' already exists in {rel}", "code": "heading_exists"}

    new_text = text.rstrip() + f"\n\n## {heading}\n{content}\n"
    target.write_text(new_text, encoding="utf-8")
    return {"appended": True, "path": rel, "heading": heading}


# ── wiki_update_frontmatter ──────────────────────────────────────────────────

WIKI_UPDATE_FRONTMATTER_SCHEMA: dict = {
    "name": "wiki_update_frontmatter",
    "description": (
        "Append a value to a list field (depends_on, used_by, modules) "
        "in an existing wiki page's frontmatter. No-ops if the value is already present."
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

    if field not in LIST_FIELDS:
        return {"error": f"Field {field!r} is not a known list field", "code": "unknown_field"}

    text = target.read_text(encoding="utf-8")

    # Check already present
    if value in text:
        return {"updated": True, "path": rel, "note": "already present — no change"}

    # Find the field line and append value
    pattern = re.compile(r"^(" + re.escape(field) + r":\s*\[)([^\]]*)\]", re.MULTILINE)
    match = pattern.search(text)
    if match:
        existing = match.group(2).strip()
        new_val = f"{existing}, {value}" if existing else value
        new_text = pattern.sub(f"{match.group(1)}{new_val}]", text, count=1)
        target.write_text(new_text, encoding="utf-8")
        return {"updated": True, "path": rel}

    # Field not on one line — append as a new list item after the field
    line_pattern = re.compile(r"^" + re.escape(field) + r":", re.MULTILINE)
    lm = line_pattern.search(text)
    if lm:
        insert_pos = text.index("\n", lm.start()) + 1
        new_text = text[:insert_pos] + f"  - {value}\n" + text[insert_pos:]
        target.write_text(new_text, encoding="utf-8")
        return {"updated": True, "path": rel}

    return {"error": f"Field {field!r} not found in frontmatter of {rel}", "code": "field_not_found"}


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
