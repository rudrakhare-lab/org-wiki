"""
Track A propose tools — typed wiki edit proposals.

All four tools (wiki_propose_new, wiki_propose_edit, wiki_propose_append,
wiki_propose_multi_edit) queue structured proposals into wiki_proposals.jsonl.
NONE of them write to the wiki filesystem — admin apply (Sub-pass C / G07
closure) is the only path that mutates wiki/ on disk.

Decisions encoded in this module:
  - Q1 (bidirectional links): advisory. When an edit modifies a depends_on or
    used_by frontmatter list, compute the implied reciprocal change and store
    it as suggested_companion_edit on the proposal. Best-effort — any error
    in the computation is logged and the proposal proceeds with an empty
    suggestion.
  - Q4 (frontmatter): permissive at field level, strict at YAML well-formedness.
  - Q5 (append separate from edit): yes — distinct tool.
  - Q8 (AUTO marker blocks): refuse with explicit error, naming the
    responsible script(s).
  - Decision A (path allowlist for wiki_propose_new): concepts/, cross-module/,
    decisions/, answers/, sources/. NOT modules/, entities/, configs/ —
    structural-page edits stay admin-only.

The agent's identity for submitter_email is "agent" by default (same hardcoded
choice as the legacy wiki_propose_edit handler). Real per-user identity
threading is tracked in TODOs and a deferred gap.
"""
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

import frontmatter  # type: ignore[import-not-found]
import yaml  # type: ignore[import-not-found]

from backend import wiki_retriever, wiki_proposals
from backend.config import WIKI_DIR

_log = logging.getLogger(__name__)

# Decision A: paths the agent is allowed to PROPOSE creating.
# Structural subtrees (modules/, entities/, configs/) stay admin-only.
_NEW_PATH_ALLOWLIST = ("concepts/", "cross-module/", "decisions/", "answers/", "sources/")

# Decision A: append tool is currently log-only. Other append targets are an
# explicit opt-in via this allowlist.
_APPEND_PATH_ALLOWLIST = ("log.md",)

# Q8: AUTO marker blocks reserved for scripts. We must not let agent edits
# overlap them. The marker regex is intentionally tight to avoid false
# positives on user-written `<!--` comments.
_AUTO_BLOCK_RE = re.compile(
    r"<!--\s*BEGIN\s+AUTO:([A-Z_]+)\s*-->.*?<!--\s*END\s+AUTO:\1\s*-->",
    re.DOTALL,
)

# Q8: which script owns which AUTO marker. Used in the error message so the
# admin knows who to ask.
_AUTO_BLOCK_OWNERS = {
    "RECENT_ACTIVITY": "scripts/enrich_modules.py",
    "KNOWN_ISSUES": "scripts/enrich_modules.py",
    "RELATED_PATTERNS": "scripts/enrich_modules.py",
}

# Wiki log entry format check (CLAUDE.md §3 line 449)
_LOG_ENTRY_HEADER_RE = re.compile(r"^##\s+\[\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}\]\s")

# G38: feedback-loop marker reserved for scripts/apply_feedback.py. Any proposal
# whose new content embeds this marker is refused — only the feedback flow may
# write it, since the idempotency check at scripts/apply_feedback.py:271 keys on it.
_FEEDBACK_MARKER_RE = re.compile(r"<!--\s*feedback:[^>]*-->")


# ── Path validation (shared) ──────────────────────────────────────────────────

def _validate_path(path: str) -> tuple[Path | None, dict | None]:
    """Validate a wiki-relative path. Returns (resolved_path, None) on success
    or (None, error_dict) on failure. Identical guards to wiki_read_page."""
    p = (path or "").strip()
    if not p:
        return None, {"error": "path is required", "code": "missing_input"}
    if ".." in p or p.startswith("/"):
        return None, {"error": "Path traversal not allowed.", "code": "path_traversal"}
    try:
        resolved = (WIKI_DIR / p).resolve()
        wiki_root = WIKI_DIR.resolve()
        if resolved != wiki_root and wiki_root not in resolved.parents:
            return None, {"error": "Path outside wiki directory.", "code": "path_traversal"}
    except Exception:
        return None, {"error": "Invalid path.", "code": "path_traversal"}
    return resolved, None


def _read_page_content(rel_path: str, resolved: Path) -> str | None:
    """Return current content of a page (preferring index, falling back to
    disk). Returns None when the page does not exist."""
    page = wiki_retriever.get_page(rel_path)
    if page is not None:
        return page.full_text or ""
    if resolved.is_file():
        try:
            return resolved.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return None
    return None


# ── Q8: AUTO marker overlap check ─────────────────────────────────────────────

def _feedback_marker_error(new_content: str) -> dict | None:
    """G38: refuse proposals that embed the `<!-- feedback:ID -->` marker.
    That marker is reserved for scripts/apply_feedback.py's idempotency check —
    if a proposal smuggles it in, a later real feedback application would be
    treated as already-applied and silently skipped."""
    m = _FEEDBACK_MARKER_RE.search(new_content)
    if m is None:
        return None
    return {
        "error": (
            "Content contains a `<!-- feedback:... -->` marker, which is "
            "reserved for scripts/apply_feedback.py. Remove the marker — only "
            "the feedback flow may write it."
        ),
        "code": "reserved_marker",
        "marker": m.group(0)[:80],
    }


def _auto_block_overlap_error(
    page_text: str, old_string: str
) -> dict | None:
    """Return an error dict if old_string overlaps an `<!-- BEGIN AUTO:X -->`
    block in page_text. None otherwise."""
    for match in _AUTO_BLOCK_RE.finditer(page_text):
        block_text = match.group(0)
        marker_name = match.group(1)
        # Overlap detection: old_string appears INSIDE the block
        if old_string in block_text:
            owner = _AUTO_BLOCK_OWNERS.get(marker_name, "(unknown script)")
            return {
                "error": (
                    f"Edit overlaps an `<!-- BEGIN AUTO:{marker_name} -->` "
                    f"block — that content is reserved for `{owner}`. "
                    f"Propose your edit outside this block, or ask an admin "
                    f"if you genuinely need to override."
                ),
                "code": "auto_block_overlap",
                "marker": marker_name,
                "owner_script": owner,
            }
    return None


# ── Q1: bidirectional link advisory ───────────────────────────────────────────


def _extract_frontmatter(text: str) -> tuple[dict, str] | dict | None:
    """Return (parsed_frontmatter_dict, body) if text starts with a `---` block
    and parses as a YAML mapping. Returns an error dict if the block is present
    but malformed. Returns None if no frontmatter block at all (caller decides
    whether that's an error).

    G35: uses python-frontmatter so `---` separators in the body (e.g. horizontal
    rules) don't confuse parsing — the library only consumes the leading block.
    """
    if not text.startswith("---"):
        return None
    try:
        post = frontmatter.loads(text)
    except yaml.YAMLError as exc:
        return {
            "error": f"frontmatter YAML is malformed: {exc}",
            "code": "invalid_frontmatter",
        }
    metadata = post.metadata if isinstance(post.metadata, dict) else None
    if metadata is None:
        return {
            "error": "frontmatter must parse as a YAML mapping (key: value)",
            "code": "invalid_frontmatter",
        }
    return metadata, post.content


def _compute_companion_edit(
    page_path: str,
    old_string: str,
    new_string: str,
) -> dict | None:
    """If the edit touches a `depends_on:` or `used_by:` frontmatter line on
    a module page, compute the implied reciprocal change on the OTHER module.
    Returns a companion edit dict or None.

    Best-effort: any parse failure logs a warning and returns None.
    """
    try:
        # Only meaningful for module pages
        if not page_path.startswith("modules/"):
            return None
        if "depends_on" not in old_string and "used_by" not in old_string:
            if "depends_on" not in new_string and "used_by" not in new_string:
                return None

        # G34: parse via YAML so block-style (`field:\n  - x`) and inline
        # (`field: [x, y]`) both produce the same set. Best-effort — any parse
        # error returns None and the advisory falls through.
        def _parse_list(s: str, field: str) -> set[str] | None:
            try:
                parsed = yaml.safe_load(s)
            except yaml.YAMLError:
                return None
            if not isinstance(parsed, dict):
                return None
            val = parsed.get(field)
            if val is None:
                return None
            if not isinstance(val, list):
                return None
            return {str(x).strip() for x in val if str(x).strip() != ""}

        for field in ("depends_on", "used_by"):
            old_set = _parse_list(old_string, field)
            new_set = _parse_list(new_string, field)
            if old_set is None and new_set is None:
                continue
            old_set = old_set or set()
            new_set = new_set or set()
            added = new_set - old_set
            removed = old_set - new_set
            if not (added or removed):
                continue

            this_slug = Path(page_path).stem  # modules/visitor-management.md → visitor-management
            reciprocal_field = "used_by" if field == "depends_on" else "depends_on"

            # For each added/removed module, the OTHER page needs the reciprocal field updated
            companions = []
            for other_slug in (added | removed):
                other_path = f"modules/{other_slug}.md"
                companions.append({
                    "page_path": other_path,
                    "reciprocal_field": reciprocal_field,
                    "add": this_slug if other_slug in added else None,
                    "remove": this_slug if other_slug in removed else None,
                })
            if companions:
                return {
                    "kind": "bidirectional_link",
                    "field": field,
                    "edits": companions,
                    "note": (
                        f"This edit modifies `{field}` on {page_path}. "
                        f"CLAUDE.md §7 line 536 requires reciprocal updates on the linked pages. "
                        f"Admin: review and apply manually or as a multi_edit proposal."
                    ),
                }
    except Exception as exc:
        _log.warning("companion-edit computation failed for %s: %s", page_path, exc)
        return None
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Schemas
# ─────────────────────────────────────────────────────────────────────────────

WIKI_PROPOSE_NEW_SCHEMA: dict = {
    "name": "wiki_propose_new",
    "description": (
        "Propose creating a NEW wiki page. Does NOT write to the wiki — queues "
        "a proposal for admin review. Tell the user the change is pending.\n\n"
        "Allowed subtrees: concepts/, cross-module/, decisions/, answers/, "
        "sources/. Structural subtrees (modules/, entities/, configs/) stay "
        "admin-only — propose those by talking to an admin.\n\n"
        "Frontmatter must parse as valid YAML between `---` delimiters. Field "
        "schemas are not strictly enforced — admin reviews during apply."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "page_path": {
                "type": "string",
                "description": "Relative wiki path, e.g. 'concepts/meal-cutoff.md'. Must end in .md.",
            },
            "content": {
                "type": "string",
                "description": "Full markdown content for the new page, including frontmatter delimited by `---`.",
            },
            "reason": {
                "type": "string",
                "description": "One-sentence justification for creating this page (audit trail).",
            },
            "answer_id": {
                "type": "string",
                "description": "Optional: answer_id from log_answer this proposal stems from.",
            },
        },
        "required": ["page_path", "content"],
    },
}


WIKI_PROPOSE_EDIT_SCHEMA: dict = {
    "name": "wiki_propose_edit",
    "description": (
        "Propose a str_replace-style edit to an EXISTING wiki page. Does NOT "
        "write to the wiki — queues a structured proposal for admin review.\n\n"
        "old_string must appear EXACTLY ONCE in the current page. If it appears "
        "multiple times, include more surrounding context to make it unique. "
        "If old_string overlaps an `<!-- BEGIN AUTO:X -->` block, the proposal "
        "is rejected — that content is owned by a script.\n\n"
        "If the edit modifies `depends_on` or `used_by` frontmatter on a module "
        "page, the handler computes the implied reciprocal update on the linked "
        "page and stores it as a `suggested_companion_edit` on the proposal "
        "(advisory; admin decides at apply time)."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "page_path": {"type": "string", "description": "Relative wiki path."},
            "old_string": {
                "type": "string",
                "description": "Existing text to replace. Must be unique within the page.",
            },
            "new_string": {
                "type": "string",
                "description": "Replacement text. Can be empty to delete the matched text.",
            },
            "reason": {"type": "string", "description": "One-sentence justification (audit trail)."},
            "answer_id": {"type": "string", "description": "Optional: linked answer_id."},
        },
        "required": ["page_path", "old_string", "new_string"],
    },
}


WIKI_PROPOSE_APPEND_SCHEMA: dict = {
    "name": "wiki_propose_append",
    "description": (
        "Propose appending content to an APPEND-ONLY wiki file. Currently only "
        "`log.md` is allowlisted (CLAUDE.md §3 line 449 marks it append-only). "
        "Does NOT write to the wiki — queues a proposal for admin review.\n\n"
        "For log.md, content MUST start with a `## [YYYY-MM-DD HH:MM] <op> | <title>` "
        "header per the documented format."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "page_path": {
                "type": "string",
                "description": "Relative path. Today: must equal 'log.md'.",
            },
            "content": {
                "type": "string",
                "description": "Content to append. For log.md, must start with the standard header.",
            },
            "reason": {"type": "string", "description": "One-sentence justification."},
            "answer_id": {"type": "string", "description": "Optional: linked answer_id."},
        },
        "required": ["page_path", "content"],
    },
}


WIKI_PROPOSE_MULTI_EDIT_SCHEMA: dict = {
    "name": "wiki_propose_multi_edit",
    "description": (
        "Propose an ATOMIC multi-file edit. Used primarily for bidirectional-"
        "link maintenance (e.g. updating depends_on on page A and used_by on "
        "page B in one operation). Does NOT write to the wiki — queues a single "
        "proposal containing all edits.\n\n"
        "Each individual edit follows wiki_propose_edit rules (unique old_string, "
        "no AUTO-block overlap). Atomicity is enforced at apply time by the admin "
        "endpoint: all edits succeed, or none do.\n\n"
        "Use this INSTEAD of multiple wiki_propose_edit calls when the edits "
        "must land together."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "edits": {
                "type": "array",
                "description": "List of edits, each with page_path, old_string, new_string.",
                "items": {
                    "type": "object",
                    "properties": {
                        "page_path": {"type": "string"},
                        "old_string": {"type": "string"},
                        "new_string": {"type": "string"},
                    },
                    "required": ["page_path", "old_string", "new_string"],
                },
            },
            "reason": {"type": "string", "description": "One-sentence justification."},
            "answer_id": {"type": "string", "description": "Optional: linked answer_id."},
        },
        "required": ["edits"],
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# Handlers
# ─────────────────────────────────────────────────────────────────────────────

_PROPOSED_OK_MSG = (
    "Pending admin review. The wiki has NOT been changed yet. The user "
    "should be told the change is queued, not applied."
)


def _wiki_propose_new_handler(inp: dict) -> dict:
    page_path = str(inp.get("page_path") or "").strip()
    content = inp.get("content")
    if not isinstance(content, str) or not content.strip():
        return {"error": "content is required (non-empty string)", "code": "missing_input"}
    reason = str(inp.get("reason") or "").strip()
    answer_id = inp.get("answer_id")

    resolved, err = _validate_path(page_path)
    if err:
        return err
    if not page_path.endswith(".md"):
        return {"error": "page_path must end in .md", "code": "invalid_path"}
    if not any(page_path.startswith(p) for p in _NEW_PATH_ALLOWLIST):
        return {
            "error": (
                f"page_path must start with one of: {', '.join(_NEW_PATH_ALLOWLIST)}. "
                f"Structural subtrees (modules/, entities/, configs/) are admin-only — "
                f"ask an admin to create those pages."
            ),
            "code": "path_not_allowed",
        }
    # Refuse if the page already exists (use wiki_propose_edit instead)
    if resolved.exists() or wiki_retriever.get_page(page_path) is not None:
        return {
            "error": f"Page already exists: {page_path}. Use wiki_propose_edit to modify it.",
            "code": "already_exists",
        }
    # G38: refuse feedback-loop marker before any other validation
    marker_err = _feedback_marker_error(content)
    if marker_err:
        return marker_err
    # Validate YAML well-formedness (Q4)
    validation_log: list[str] = []
    fm = _extract_frontmatter(content)
    if fm is None:
        return {
            "error": "content must start with a `---` frontmatter block",
            "code": "missing_frontmatter",
        }
    if isinstance(fm, dict) and "error" in fm:
        return fm  # malformed YAML or non-mapping FM
    parsed, _body = fm  # type: ignore[misc]
    validation_log.append(f"frontmatter parsed OK ({len(parsed)} keys)")

    pid = wiki_proposals.create_new_proposal(
        page_path=page_path,
        content=content,
        submitter_email="agent",  # TODO: thread user identity from registry (existing TODO in wiki_tools)
        reason=reason,
        answer_id=answer_id,
        validation_log=validation_log,
    )
    return {
        "status": "pending",
        "proposal_id": pid,
        "page_path": page_path,
        "proposal_type": "new",
        "message": _PROPOSED_OK_MSG,
    }


def _wiki_propose_edit_handler(inp: dict) -> dict:
    page_path = str(inp.get("page_path") or "").strip()
    old_string = inp.get("old_string")
    new_string = inp.get("new_string")
    if not isinstance(old_string, str) or old_string == "":
        return {"error": "old_string is required (non-empty)", "code": "missing_input"}
    if not isinstance(new_string, str):
        return {"error": "new_string is required", "code": "missing_input"}
    reason = str(inp.get("reason") or "").strip()
    answer_id = inp.get("answer_id")

    resolved, err = _validate_path(page_path)
    if err:
        return err

    # The target page must exist
    current = _read_page_content(page_path, resolved)
    if current is None:
        return {
            "error": f"Page not found: {page_path}. Use wiki_propose_new to create.",
            "code": "not_found",
        }

    # G38: refuse feedback-loop marker in new_string
    marker_err = _feedback_marker_error(new_string)
    if marker_err:
        return marker_err

    # old_string uniqueness check
    occurrences = current.count(old_string)
    if occurrences == 0:
        return {
            "error": "old_string not found in current page content",
            "code": "old_string_not_found",
        }
    if occurrences > 1:
        return {
            "error": (
                f"old_string appears {occurrences} times in the page — must be unique. "
                "Include more surrounding context to disambiguate."
            ),
            "code": "old_string_not_unique",
        }

    # Q8: AUTO marker overlap
    auto_err = _auto_block_overlap_error(current, old_string)
    if auto_err:
        return auto_err

    # Q1 advisory companion edit (best-effort)
    companion = _compute_companion_edit(page_path, old_string, new_string)

    validation_log = [
        "old_string verified unique in current page",
        "no AUTO marker overlap",
    ]
    if companion is not None:
        validation_log.append(f"companion edit suggested: {companion['field']} reciprocity")

    pid = wiki_proposals.create_edit_proposal(
        page_path=page_path,
        old_string=old_string,
        new_string=new_string,
        submitter_email="agent",  # TODO: thread user identity
        reason=reason,
        answer_id=answer_id,
        suggested_companion_edit=companion,
        validation_log=validation_log,
    )
    return {
        "status": "pending",
        "proposal_id": pid,
        "page_path": page_path,
        "proposal_type": "edit",
        "has_companion_edit": companion is not None,
        "message": _PROPOSED_OK_MSG,
    }


def _wiki_propose_append_handler(inp: dict) -> dict:
    page_path = str(inp.get("page_path") or "").strip()
    content = inp.get("content")
    if not isinstance(content, str) or not content.strip():
        return {"error": "content is required (non-empty string)", "code": "missing_input"}
    reason = str(inp.get("reason") or "").strip()
    answer_id = inp.get("answer_id")

    resolved, err = _validate_path(page_path)
    if err:
        return err
    # G38: refuse feedback-loop marker in append content
    marker_err = _feedback_marker_error(content)
    if marker_err:
        return marker_err
    if not any(page_path == p or page_path.endswith("/" + p) for p in _APPEND_PATH_ALLOWLIST):
        return {
            "error": (
                f"Append is allowlisted to: {', '.join(_APPEND_PATH_ALLOWLIST)}. "
                f"Other append targets are not yet supported."
            ),
            "code": "path_not_allowed",
        }

    validation_log: list[str] = []
    # log.md format check
    if page_path.endswith("log.md"):
        first_line = content.strip().splitlines()[0] if content.strip() else ""
        if not _LOG_ENTRY_HEADER_RE.match(first_line):
            return {
                "error": (
                    "log.md entries must start with `## [YYYY-MM-DD HH:MM] <op> | <title>` "
                    "per CLAUDE.md §3 line 449. Got: "
                    + (first_line[:80] or "(empty content)")
                ),
                "code": "invalid_log_format",
            }
        validation_log.append("log.md entry header matches required format")

    pid = wiki_proposals.create_append_proposal(
        page_path=page_path,
        content=content,
        submitter_email="agent",
        reason=reason,
        answer_id=answer_id,
        validation_log=validation_log,
    )
    return {
        "status": "pending",
        "proposal_id": pid,
        "page_path": page_path,
        "proposal_type": "append",
        "message": _PROPOSED_OK_MSG,
    }


def _wiki_propose_multi_edit_handler(inp: dict) -> dict:
    edits = inp.get("edits")
    if not isinstance(edits, list) or not edits:
        return {"error": "edits is required (non-empty list)", "code": "missing_input"}
    reason = str(inp.get("reason") or "").strip()
    answer_id = inp.get("answer_id")

    validation_log: list[str] = []
    # Validate each edit per the single-edit rules. Refuse the whole proposal
    # if any one fails (atomicity is the point of multi_edit).
    for i, e in enumerate(edits):
        if not isinstance(e, dict):
            return {"error": f"edits[{i}] is not an object", "code": "invalid_input"}
        for key in ("page_path", "old_string", "new_string"):
            if key not in e:
                return {"error": f"edits[{i}] missing '{key}'", "code": "missing_input"}
        resolved, err = _validate_path(str(e["page_path"]))
        if err:
            return {**err, "edit_index": i}
        current = _read_page_content(str(e["page_path"]), resolved)
        if current is None:
            return {
                "error": f"edits[{i}].page_path not found: {e['page_path']}",
                "code": "not_found",
                "edit_index": i,
            }
        occ = current.count(e["old_string"])
        if occ == 0:
            return {
                "error": f"edits[{i}].old_string not found in {e['page_path']}",
                "code": "old_string_not_found",
                "edit_index": i,
            }
        if occ > 1:
            return {
                "error": f"edits[{i}].old_string appears {occ} times in {e['page_path']} — must be unique",
                "code": "old_string_not_unique",
                "edit_index": i,
            }
        auto_err = _auto_block_overlap_error(current, str(e["old_string"]))
        if auto_err:
            return {**auto_err, "edit_index": i}
        # G38: refuse feedback-loop marker in any new_string
        marker_err = _feedback_marker_error(str(e["new_string"]))
        if marker_err:
            return {**marker_err, "edit_index": i}
        validation_log.append(f"edits[{i}] {e['page_path']} validated")

    pid = wiki_proposals.create_multi_edit_proposal(
        edits=edits,
        submitter_email="agent",
        reason=reason,
        answer_id=answer_id,
        suggested_companion_edit=None,
        validation_log=validation_log,
    )
    return {
        "status": "pending",
        "proposal_id": pid,
        "proposal_type": "multi_edit",
        "edit_count": len(edits),
        "message": _PROPOSED_OK_MSG,
    }
