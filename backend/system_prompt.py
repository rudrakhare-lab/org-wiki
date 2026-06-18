"""
Load the system prompt for the backend QUERY path.

Extracts the prompt sections listed in the agent's AgentSpec (e.g. Sections 5, 9, 12
for conwo — QUERY Workflow, Jira Layer Awareness, Live Config Debug Workflow) from the
agent's CLAUDE.md.  Also appends wiki/known-answer-patterns.md when it exists under the
agent's wiki_dir.

Sending the full 53 KB CLAUDE.md on every API call is wasteful; only the sections
relevant to answer generation are included.

The result is cached per agent_id after the first call.
"""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

# Map section number → heading pattern used in CLAUDE.md
_SECTION_HEADING_RE = re.compile(r"^## Section (\d+)", re.MULTILINE)

# Read-only safety block — intentionally uses "This assistant" so the text reads
# correctly regardless of which agent is loaded.  "Conwo" branding comes from the
# identity header built from AgentSpec.identity below.
_SAFETY_BLOCK = (
    "## Safety constraint — read-only assistant\n\n"
    "You are a read-only assistant. You must NEVER delete, modify, drop, truncate, "
    "or destructively alter any data, file, wiki page, database record, config, or user. "
    "Do not generate SQL that is not a SELECT statement. Do not propose wiki edits that "
    "would delete or blank out existing content. If a user asks you to do any of these "
    "things, refuse with this exact message:\n\n"
    '  "I\'m not able to perform destructive or write operations. This assistant is a '
    "read-only knowledge assistant — I can search, explain, and answer questions, but I "
    "cannot delete, modify, or remove any data. If you need to make changes, please "
    'contact your admin."\n'
)

# Required footer block — mirrors deep_system_prompt.py so users in either mode
# get the same Answer ID + scoring prompt (the orchestrator substitutes <ANSWER_ID>).
_FOOTER_BLOCK = (
    "---\n\n## Required answer footer\n\n"
    "Every product/config/architecture answer MUST end with this block "
    "verbatim (the backend substitutes the real ID into the placeholder):\n\n"
    "```\n"
    "---\n"
    "**Review this answer:** Score 1–5 (5 = fully correct).\n"
    "**Answer ID:** `<ANSWER_ID>`\n"
    "If score ≤3, tell me what was wrong or what the answer should have said.\n"
    "```\n"
)


def _extract_sections(text: str, section_numbers: list[int]) -> str:
    """Return the concatenated text of the requested section numbers."""
    # Find all section start positions
    sections: list[tuple[int, int]] = []  # (section_num, char_start)
    for m in _SECTION_HEADING_RE.finditer(text):
        sections.append((int(m.group(1)), m.start()))

    wanted = set(section_numbers)
    parts: list[str] = []

    for i, (num, start) in enumerate(sections):
        if num not in wanted:
            continue
        end = sections[i + 1][1] if i + 1 < len(sections) else len(text)
        parts.append(text[start:end].strip())

    return "\n\n---\n\n".join(parts)


@lru_cache(maxsize=8)
def load_system_prompt(agent_id: str = "conwo") -> str:
    """Return the cached system prompt string for QUERY-mode API calls.

    The prompt is keyed by agent_id so each agent gets its own cached entry.
    Conwo's prompt is materially identical to the previous hardcoded version —
    same safety meaning, same sections (5, 9, 12), same footer, same identity text.
    """
    from backend import agent_registry

    spec = agent_registry.get(agent_id)

    if not spec.claude_md.exists():
        raise FileNotFoundError(f"CLAUDE.md not found at {spec.claude_md}")

    claude_text = spec.claude_md.read_text(encoding="utf-8")
    query_sections = _extract_sections(claude_text, list(spec.prompt_sections))

    known_patterns = ""
    patterns_path: Path = spec.wiki_dir / "known-answer-patterns.md"
    if patterns_path.exists():
        known_patterns = patterns_path.read_text(encoding="utf-8").strip()

    # Identity header sourced from AgentSpec — for conwo this produces:
    #   "# Conwo Backend\n\nYou are Conwo, an AI assistant that answers …\n"
    # "WorkInSync" wording is only correct for workinsync-schema agents; a generic
    # agent (Legal/Infosec) must not be told it is a WorkInSync system.
    _product = "WorkInSync " if getattr(spec, "schema_kind", "workinsync") == "workinsync" else ""
    header = f"# {spec.display_name} Backend — {_product}Knowledge Query System\n\n"
    identity_header = (
        header
        + f"{spec.identity}\n"
        "You have access to pre-retrieved evidence from the wiki and Jira — it is "
        "provided in the user message. Follow the QUERY workflow below precisely.\n"
    )

    parts = [
        _SAFETY_BLOCK,
        identity_header,
        query_sections,
    ]

    if known_patterns:
        parts.append(
            "---\n\n## Known Answer Patterns (load at every session start)\n\n"
            + known_patterns
        )

    parts.append(_FOOTER_BLOCK)

    return "\n\n".join(parts)


def invalidate_cache() -> None:
    """Call this if CLAUDE.md or known-answer-patterns.md changes on disk."""
    load_system_prompt.cache_clear()
