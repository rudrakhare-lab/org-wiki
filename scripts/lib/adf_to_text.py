"""
lib/adf_to_text.py — Atlassian Document Format → plaintext.

ADF is a JSON tree. We walk it depth-first and emit human-readable text.
Reference: https://developer.atlassian.com/cloud/jira/platform/apis/document/structure/

Design choices:
- Block nodes (paragraph, heading, list, code, etc.) emit a leading newline
  and a trailing blank line. Inline nodes append text with no separator.
- Headings are prefixed with their level as `## `.
- Lists use `- ` for bullets and `1. ` for ordered, indented by 2 spaces per
  nesting level.
- Tables flatten to pipe-separated rows.
- Mentions render as `@DisplayName` if attrs.text is present, else `@user`.
- Status / inlineCard / emoji preserve their visible label.
- Unknown node types fall through and recurse into `content`, so future ADF
  additions degrade gracefully instead of throwing.

Output is intentionally lossy — anything visible to a human reader is kept;
formatting marks (bold, italic, color, link href) are dropped because the
classifier and embedder don't need them.
"""

from __future__ import annotations

from typing import Any


def adf_to_text(node: Any) -> str:
    """Convert an ADF document (or any subtree) to plaintext.

    Accepts a dict, list of dicts, or None. Returns a string with paragraph
    breaks normalized to `\\n\\n` and trailing whitespace trimmed.
    """
    if not node:
        return ""
    if isinstance(node, str):
        return node

    parts: list[str] = []
    _render(node, parts, depth=0, list_kind=None, list_index=None)
    text = "".join(parts)
    return _normalize_blanklines(text).strip()


# ---------------------------------------------------------------------------
# Recursion
# ---------------------------------------------------------------------------

def _render(
    node: Any,
    out: list[str],
    *,
    depth: int,
    list_kind: str | None,
    list_index: int | None,
) -> None:
    if isinstance(node, list):
        for child in node:
            _render(child, out, depth=depth, list_kind=list_kind, list_index=list_index)
        return
    if not isinstance(node, dict):
        return

    ntype = node.get("type", "")
    content = node.get("content", [])
    attrs = node.get("attrs", {}) or {}

    # Block-level
    if ntype == "doc":
        _render_children(content, out, depth=depth)
        return

    if ntype == "paragraph":
        _render_children(content, out, depth=depth)
        out.append("\n\n")
        return

    if ntype == "heading":
        level = int(attrs.get("level", 1))
        out.append("#" * max(1, min(level, 6)) + " ")
        _render_children(content, out, depth=depth)
        out.append("\n\n")
        return

    if ntype == "bulletList":
        for i, item in enumerate(content):
            _render(item, out, depth=depth, list_kind="bullet", list_index=i + 1)
        out.append("\n")
        return

    if ntype == "orderedList":
        start = int(attrs.get("order", 1))
        for i, item in enumerate(content):
            _render(item, out, depth=depth, list_kind="ordered", list_index=start + i)
        out.append("\n")
        return

    if ntype == "listItem":
        prefix = "  " * depth
        bullet = f"{list_index}. " if list_kind == "ordered" else "- "
        out.append(prefix + bullet)
        # listItem children typically include paragraphs & nested lists
        # We render children inline (without their own leading newline) for
        # the first paragraph, then nested blocks normally.
        _render_list_item_children(content, out, depth=depth + 1)
        return

    if ntype == "codeBlock":
        lang = attrs.get("language", "")
        out.append(f"```{lang}\n")
        _render_children(content, out, depth=depth)
        out.append("\n```\n\n")
        return

    if ntype == "blockquote":
        # Capture children into a buffer, prefix each line with "> "
        buf: list[str] = []
        _render_children(content, buf, depth=depth)
        text = "".join(buf).strip("\n")
        for line in text.split("\n"):
            out.append("> " + line + "\n")
        out.append("\n")
        return

    if ntype == "rule":
        out.append("\n---\n\n")
        return

    if ntype == "table":
        _render_table(content, out)
        return

    if ntype in ("mediaSingle", "mediaGroup"):
        _render_children(content, out, depth=depth)
        return

    if ntype == "media":
        # Just note it visually so attachments are visible in plaintext
        alt = attrs.get("alt") or attrs.get("collection") or "attachment"
        out.append(f"[media: {alt}]")
        return

    # Inline-level
    if ntype == "text":
        out.append(node.get("text", ""))
        return

    if ntype == "hardBreak":
        out.append("\n")
        return

    if ntype == "mention":
        text = attrs.get("text") or attrs.get("displayName") or attrs.get("id") or "user"
        out.append(f"@{text.lstrip('@')}")
        return

    if ntype == "emoji":
        out.append(attrs.get("text") or attrs.get("shortName") or "")
        return

    if ntype in ("inlineCard", "blockCard"):
        url = attrs.get("url", "")
        if url:
            out.append(url)
        return

    if ntype == "status":
        out.append(f"[{attrs.get('text', 'status')}]")
        return

    if ntype == "date":
        ts = attrs.get("timestamp", "")
        out.append(f"[date: {ts}]")
        return

    # Unknown: recurse into children so we don't lose text content
    if content:
        _render_children(content, out, depth=depth)


def _render_children(content: Any, out: list[str], *, depth: int) -> None:
    if not isinstance(content, list):
        return
    for child in content:
        _render(child, out, depth=depth, list_kind=None, list_index=None)


def _render_list_item_children(content: Any, out: list[str], *, depth: int) -> None:
    if not isinstance(content, list):
        return
    first_para_done = False
    for child in content:
        if isinstance(child, dict) and child.get("type") == "paragraph":
            _render_children(child.get("content", []), out, depth=depth)
            out.append("\n")
            first_para_done = True
        else:
            _render(child, out, depth=depth, list_kind=None, list_index=None)
    if not first_para_done:
        out.append("\n")


def _render_table(content: Any, out: list[str]) -> None:
    if not isinstance(content, list):
        return
    rows: list[list[str]] = []
    for row in content:
        if not isinstance(row, dict) or row.get("type") != "tableRow":
            continue
        cells: list[str] = []
        for cell in row.get("content", []) or []:
            buf: list[str] = []
            _render_children(cell.get("content", []), buf, depth=0)
            cells.append(" ".join("".join(buf).split()))
        rows.append(cells)
    for r in rows:
        out.append(" | ".join(r) + "\n")
    out.append("\n")


# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------

def _normalize_blanklines(text: str) -> str:
    """Collapse 3+ consecutive newlines down to 2."""
    out: list[str] = []
    blank = 0
    for line in text.split("\n"):
        if line.strip() == "":
            blank += 1
            if blank <= 2:
                out.append("")
        else:
            blank = 0
            out.append(line)
    return "\n".join(out)
