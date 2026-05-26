"""
Load the system prompt for the backend QUERY path.

Extracts Sections 5 (QUERY Workflow), 9 (Jira Layer Awareness), and 12
(Live Config Debug Workflow) from CLAUDE.md. Also appends the contents of
wiki/known-answer-patterns.md. Sending the full 53KB CLAUDE.md on every API
call is wasteful and puts unnecessary tokens into the context; these three
sections are the only parts needed for answer generation.

The result is cached in-memory after the first call (the files rarely change
while the backend is running).
"""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

from backend.config import CLAUDE_MD, KNOWN_PATTERNS_MD, SYSTEM_PROMPT_SECTIONS

# Map section number → heading pattern used in CLAUDE.md
_SECTION_HEADING_RE = re.compile(r"^## Section (\d+)", re.MULTILINE)


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


@lru_cache(maxsize=1)
def load_system_prompt() -> str:
    """Return the cached system prompt string for QUERY-mode API calls."""
    if not CLAUDE_MD.exists():
        raise FileNotFoundError(f"CLAUDE.md not found at {CLAUDE_MD}")

    claude_text = CLAUDE_MD.read_text(encoding="utf-8")
    query_sections = _extract_sections(claude_text, SYSTEM_PROMPT_SECTIONS)

    known_patterns = ""
    if KNOWN_PATTERNS_MD.exists():
        known_patterns = KNOWN_PATTERNS_MD.read_text(encoding="utf-8").strip()

    parts = [
        "# Conwo Backend — WorkInSync Knowledge Query System\n\n"
        "You are Conwo, an AI assistant that answers product, config, and debugging "
        "questions about WorkInSync. You have access to pre-retrieved evidence from "
        "the wiki and Jira — it is provided in the user message. Follow the QUERY "
        "workflow below precisely.\n",
        query_sections,
    ]

    if known_patterns:
        parts.append(
            "---\n\n## Known Answer Patterns (load at every session start)\n\n"
            + known_patterns
        )

    # G29 closure — feedback-prompt template for claude-code mode.
    # Mirrors the deep_system_prompt.py block so users in either mode
    # get the same Answer ID + scoring prompt and the substitution in
    # orchestrator.run_single_shot resolves the <ANSWER_ID> placeholder.
    parts.append(
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

    return "\n\n".join(parts)


def invalidate_cache() -> None:
    """Call this if CLAUDE.md or known-answer-patterns.md changes on disk."""
    load_system_prompt.cache_clear()
