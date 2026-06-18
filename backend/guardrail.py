"""
Safety guardrail for Conwo — blocks destructive or write operations requested
through the chat interface.

Three layers:
  Layer 1 (input filter)  — called in api.py before the LLM sees the question
  Layer 2 (tool filter)   — called in tools/registry.py before any tool executes
  Layer 3 (system prompt) — instruction added to both system prompts

Only Layer 1 and 2 logic lives here.  Layer 3 is in deep_system_prompt.py and
system_prompt.py.
"""
from __future__ import annotations

import logging
import re
from typing import Any

_log = logging.getLogger("guardrail")

# ---------------------------------------------------------------------------
# Refusal message — used consistently across all three layers
# ---------------------------------------------------------------------------

REFUSAL_MESSAGE = (
    "I'm not able to perform destructive or write operations. Conwo is a "
    "read-only knowledge assistant — I can search, explain, and answer "
    "questions, but I cannot delete, modify, or remove any data. If you "
    "need to make changes, please contact your admin."
)

# ---------------------------------------------------------------------------
# Layer 1 — input patterns
#
# Design goal: HIGH precision, not HIGH recall.
#
# "why does the delete button not work?" → NOT blocked (standalone "delete")
# "what config removes the NDA screen?"  → NOT blocked (targeted, legitimate)
# "drop table tickets"                   → BLOCKED (SQL DDL)
# "delete all wiki pages"                → BLOCKED (targeted bulk destroy)
# "wipe out all visitor configs"         → BLOCKED
# ---------------------------------------------------------------------------

_INPUT_PATTERNS: list[str] = [
    # SQL DDL / DML — these strings never appear in legitimate Q&A
    r"drop\s+(?:table|database|index|view)\b",
    r"truncate\s+(?:table\s+)?\w+",
    r"delete\s+from\s+\w+",
    r"update\s+\w+\s+set\s+",
    r"alter\s+table\s+\w+",
    r"insert\s+into\s+\w+",

    # Extreme destructive phrases — no plausible benign use in a knowledge bot
    r"wipe\s+(?:out|all|everything|the\s+(?:database|data|wiki|configs?))",
    r"erase\s+(?:all|everything|the\s+(?:database|data|wiki|configs?))",
    r"clear\s+all\s+(?:the\s+)?(?:data|tickets?|configs?|database|db|wiki|pages?)",
    r"destroy\s+(?:the\s+)?(?:database|db|wiki|all\s+data|everything)",
    r"reset\s+(?:the\s+)?(?:database|db|all\s+data|all\s+configs?|all\s+tickets?|all\s+wiki)",
    r"purge\s+(?:all|the)\s+(?:tickets?|data|configs?|wiki|users?)",

    # Targeted bulk delete of knowledge-base objects
    r"delete\s+(?:all|every)\s+(?:wiki|tickets?|configs?|data|pages?|users?|files?)",
    r"remove\s+(?:all|every)\s+(?:users?|data|tickets?|configs?|wiki|pages?)",
]

_INPUT_RE = re.compile(
    "|".join(f"(?:{p})" for p in _INPUT_PATTERNS),
    re.IGNORECASE,
)


def is_destructive_input(question: str) -> str | None:
    """Return the matched text if the question looks destructive, else None."""
    m = _INPUT_RE.search(question)
    return m.group(0) if m else None


# ---------------------------------------------------------------------------
# Layer 2 — tool-call patterns
#
# Checked inside ToolRegistry.execute() BEFORE dispatching to any handler.
# ---------------------------------------------------------------------------

# Write tools must never be called from the query loop — they are only
# for the ingest agent's internal registry.
_BLOCKED_TOOL_NAMES: frozenset[str] = frozenset({
    "wiki_create_page",
    "wiki_edit_page",
    "wiki_append_section",
    "wiki_rebuild_index",
    "wiki_update_frontmatter",
})

# SQL statements that are not SELECT — should never appear in tool inputs
_WRITE_SQL_RE = re.compile(
    r"\b(?:INSERT\s+INTO|UPDATE\s+\w+\s+SET|DELETE\s+FROM|DROP\s+TABLE|"
    r"TRUNCATE(?:\s+TABLE)?|ALTER\s+TABLE|CREATE\s+TABLE|REPLACE\s+INTO|"
    r"MERGE\s+INTO)\b",
    re.IGNORECASE,
)


def _iter_str_values(obj: Any) -> list[str]:
    """Recursively collect all string leaf values from a dict/list/scalar."""
    results: list[str] = []
    if isinstance(obj, str):
        results.append(obj)
    elif isinstance(obj, dict):
        for v in obj.values():
            results.extend(_iter_str_values(v))
    elif isinstance(obj, list):
        for item in obj:
            results.extend(_iter_str_values(item))
    return results


def is_destructive_tool_call(
    tool_name: str, tool_input: dict, allow_writes: bool = False
) -> str | None:
    """Return reason string if the tool call should be blocked, else None.

    `allow_writes` is True only for the admin-gated ingest EXECUTE registry, where
    wiki write tools are the whole point. It is False everywhere else — most
    importantly the chat/query registry — so the chat loop stays strictly read-only.
    The write-SQL check always applies: no tool, in any mode, may run write SQL.
    """
    if not allow_writes and tool_name in _BLOCKED_TOOL_NAMES:
        return f"tool '{tool_name}' is not available in query mode"
    for val in _iter_str_values(tool_input):
        if _WRITE_SQL_RE.search(val):
            return "tool input contains a write SQL statement"
    return None


# ---------------------------------------------------------------------------
# Shared logging helper
# ---------------------------------------------------------------------------

def log_blocked(
    *,
    user_email: str | None,
    question: str,
    trigger: str,
    where: str,
) -> None:
    """Emit a structured WARNING log entry for a blocked attempt."""
    _log.warning(
        "GUARDRAIL_BLOCKED where=%s trigger=%r user=%s question=%r",
        where,
        trigger,
        user_email or "anonymous",
        question[:300],
    )
