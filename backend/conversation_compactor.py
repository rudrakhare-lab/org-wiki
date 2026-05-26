"""
Conversation compaction — summarize old turns into a rolling 5-bullet summary.

Two-tier history strategy (G03):
  - Last 12 messages (6 turns) are kept verbatim in prior_messages.
  - Everything older is collapsed into a short summary stored on the conversation
    row (compacted_summary + compaction_at_turn).
  - The summary is prepended to the seed user_message by build_seed_message,
    NOT injected into prior_messages (which would break Anthropic's role
    alternation requirement).

NO-API-KEY FALLBACK (most important failure mode):
  summarize_old_turns() catches the ValueError from resolve_api_key() and
  returns "" — the caller (load_conversation_summary in orchestrator) treats
  an empty summary as "skip compaction, fall back to plain truncation." This
  is the silent-degradation behavior; the query still works but the model
  loses memory of pre-window turns. We document the behavior so future
  readers don't expect compaction to always run.

ANTHROPIC ERROR FALLBACK:
  If the Anthropic API call raises (rate limit, network, etc.),
  summarize_old_turns() also returns "" — never blocks a query on a
  summarization failure.
"""
from __future__ import annotations

import os

RECENT_WINDOW = 12          # last N messages kept verbatim (== 6 turns × 2 roles)
THRESHOLD_NEW_MESSAGES = 6  # refresh after this many new messages since last compaction
MAX_MESSAGE_CHARS = 500     # per-message cap when feeding the summarizer
MAX_INPUT_CHARS = 50_000    # total cap on summarizer input text
_DEFAULT_MODEL = "claude-haiku-4-5"
_TIMEOUT_SECONDS = 30.0     # G33: bound the Anthropic call so a hang can't block a query
                            #      Anthropic SDK default is ~600s; haiku-4-5 typical p99 < 5s.


def should_refresh(total_messages: int, compaction_at_turn: int | None) -> bool:
    """Return True if compaction is needed given the current state.

    - No compaction needed when all messages fit in the recent window.
    - First-time compaction needed when there ARE older messages and no
      summary exists yet (compaction_at_turn is None).
    - Refresh needed when ≥THRESHOLD_NEW_MESSAGES messages have been added
      since the last compaction.
    """
    old_count = max(0, total_messages - RECENT_WINDOW)
    if old_count == 0:
        return False
    if compaction_at_turn is None:
        return True
    return (total_messages - compaction_at_turn) >= THRESHOLD_NEW_MESSAGES


def messages_to_summarize(all_messages: list[dict]) -> list[dict]:
    """Return the slice that should be summarized — everything before the
    recent window. Returns [] when nothing needs summarizing."""
    if len(all_messages) <= RECENT_WINDOW:
        return []
    return all_messages[:-RECENT_WINDOW]


def _format_messages_for_summary(messages: list[dict]) -> str:
    """Format messages as plain text, truncating per-message and total to
    keep the summarizer input bounded. Preserves chronological order so
    early constraints survive truncation; cuts later turns if the total
    blows MAX_INPUT_CHARS."""
    out: list[str] = []
    total = 0
    for m in messages:
        content = (m.get("content") or "")
        if len(content) > MAX_MESSAGE_CHARS:
            content = content[:MAX_MESSAGE_CHARS] + "…[truncated]"
        line = f"[{m.get('role', '?')}] {content}"
        if total + len(line) > MAX_INPUT_CHARS:
            out.append("\n[earlier turns omitted due to size]")
            break
        out.append(line)
        total += len(line)
    return "\n\n".join(out)


_SYSTEM_PROMPT = (
    "You are summarizing a prior conversation segment so it can replace "
    "the original turns in future context. Output EXACTLY 5 bullets, "
    "each ≤25 words. Preserve:\n"
    "- Constraints/assumptions the user established (server, BUID, scope, "
    "service, role)\n"
    "- References to specific tickets, configs, file paths, or properties\n"
    "- Decisions or facts the user agreed to / corrected\n"
    "- Open questions or unresolved errors\n\n"
    "Do not editorialize. Do not invent. Output only the bullets, no preamble, "
    "no closing remarks."
)


def summarize_old_turns(messages: list[dict]) -> str:
    """Summarize a list of {role, content} dicts into a 5-bullet summary.

    Returns "" in any of these cases (caller falls back to plain truncation):
      - messages is empty
      - resolve_api_key() raises ValueError (no API key configured anywhere)
      - the anthropic SDK isn't importable (package missing)
      - the Anthropic API call raises any exception (rate limit, network, etc.)

    Never raises. Use os env ANTHROPIC_COMPACTOR_MODEL to override the default
    model (claude-haiku-4-5).
    """
    if not messages:
        return ""

    # Resolve key — most important failure mode is "no key configured" → "".
    try:
        from backend.config import resolve_api_key
        api_key = resolve_api_key(None)
    except (ValueError, ImportError):
        return ""
    if not api_key:
        return ""

    try:
        from anthropic import Anthropic
    except ImportError:
        return ""

    model = os.getenv("ANTHROPIC_COMPACTOR_MODEL", _DEFAULT_MODEL)
    convo_text = _format_messages_for_summary(messages)
    if not convo_text.strip():
        return ""

    try:
        # G33: explicit per-call timeout so a hang can't block the query.
        client = Anthropic(api_key=api_key, timeout=_TIMEOUT_SECONDS)
        resp = client.messages.create(
            model=model,
            max_tokens=300,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": f"Conversation segment to summarize:\n\n{convo_text}"}],
        )
    except Exception:
        # Includes APITimeoutError, APIConnectionError, RateLimitError, etc.
        # Caller falls back to previous cached summary (or no summary).
        return ""

    # SDK returns Message with .content as a list of TextBlock-like objects.
    text = ""
    for block in getattr(resp, "content", []) or []:
        chunk = getattr(block, "text", None)
        if chunk is None and isinstance(block, dict):
            chunk = block.get("text", "")
        if chunk:
            text += chunk
    return text.strip()
