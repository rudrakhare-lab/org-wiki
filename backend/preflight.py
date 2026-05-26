"""
Deterministic evidence preflight.

Runs the SAME retrieval steps for EVERY query before the LLM is invoked:
  1. wiki_retriever.search(question, top_n=3)        — keyword search
  2. jira_retriever.search(question, functional_area) — ranked LATEST/HISTORICAL/STALE
  3. jira_get_ticket on the top 1–2 LATEST tickets    — full body, via ToolRegistry

All ticket reads go through ToolRegistry.execute() so:
  - secrets are sanitized
  - trace entries are produced (round_num=0 marks them as preflight)
  - handler errors are JSON-error dicts, not exceptions

The output is intended to be formatted into the seed user message for
Deep Search and prepended to the question for Claude Code agent mode.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

from backend import jira_retriever, wiki_retriever
from backend.tools import build_registry
from backend.tools.registry import ToolRegistry, ToolTraceEntry

_PREFLIGHT_LATEST_LIMIT = 2     # auto-fetch top N LATEST tickets
_PREFLIGHT_WIKI_TOP_N = 3       # number of wiki pages to seed
_PREFLIGHT_WIKI_EXCERPT = 800   # wiki excerpt chars per page (was 300)


@dataclass
class PreflightBundle:
    """All preflight retrieval results, ready to be formatted."""
    seed_wiki: list = field(default_factory=list)   # list of wiki Page objects
    seed_jira: dict = field(default_factory=dict)   # full jira_retriever.search result
    preflight_tickets: list[dict] = field(default_factory=list)  # full ticket dicts
    preflight_trace: list[ToolTraceEntry] = field(default_factory=list)

    def latest_keys(self) -> list[str]:
        return [r["key"] for r in self.seed_jira.get("buckets", {}).get("LATEST", [])]

    def stats(self) -> dict:
        buckets = self.seed_jira.get("buckets", {})
        return {
            "wiki_pages_seeded": len(self.seed_wiki),
            "jira_latest": len(buckets.get("LATEST", [])),
            "jira_historical": len(buckets.get("HISTORICAL", [])),
            "tickets_prefetched": len(self.preflight_tickets),
            "keywords": self.seed_jira.get("keywords", []),
        }


# ── Preflight runner ────────────────────────────────────────────────────────

def run_preflight(
    question: str,
    functional_area: str | None = None,
    registry: ToolRegistry | None = None,
    latest_limit: int = _PREFLIGHT_LATEST_LIMIT,
) -> PreflightBundle:
    """Run the deterministic preflight retrieval. Always runs for every query."""
    bundle = PreflightBundle()
    bundle.seed_wiki = wiki_retriever.search(question, top_n=_PREFLIGHT_WIKI_TOP_N)
    bundle.seed_jira = jira_retriever.search(question, functional_area=functional_area)

    if registry is None:
        registry = build_registry()

    # Auto-fetch top LATEST tickets so the model NEVER has to guess based on
    # the summary alone. Goes through the registry so the trace is sanitized
    # and consistent with model-initiated tool calls.
    keys_to_fetch = bundle.latest_keys()[:latest_limit]
    for key in keys_to_fetch:
        json_output, entry = registry.execute(
            name="jira_get_ticket",
            tool_input={"key": key},
            round_num=0,   # 0 = preflight (model rounds start at 1)
        )
        bundle.preflight_trace.append(entry)
        try:
            ticket = json.loads(json_output)
            if not ticket.get("error"):
                bundle.preflight_tickets.append(ticket)
        except (ValueError, TypeError):
            pass  # registry already produced a sanitized trace entry

    return bundle


# ── Formatters ──────────────────────────────────────────────────────────────

def format_wiki_for_seed(pages: list, excerpt_chars: int = _PREFLIGHT_WIKI_EXCERPT) -> str:
    if not pages:
        return "No relevant wiki pages found in preflight."
    parts = []
    for page in pages:
        parts.append(f"### {page.title} — `{page.path}`\n\n{page.excerpt(excerpt_chars)}")
    return "\n\n---\n\n".join(parts)


def format_jira_buckets_for_seed(jira_result: dict) -> str:
    buckets = jira_result.get("buckets", {})
    if not any(buckets.get(b) for b in ("LATEST", "HISTORICAL", "STALE-OPEN")):
        return "No relevant Jira tickets found in preflight."

    lines: list[str] = []
    for bucket in ("LATEST", "HISTORICAL", "STALE-OPEN"):
        rows = buckets.get(bucket, [])
        if not rows:
            continue
        lines.append(f"**{bucket}:**")
        for row in rows[:3]:
            summary = (row.get("summary") or "")[:120]
            updated = row.get("updated", "?")
            resolved = row.get("resolved")
            tail = f" (resolved {resolved})" if resolved else f" (updated {updated})"
            lines.append(f"  - `{row.get('key')}` — {summary}{tail}")
    return "\n".join(lines)


def format_preflight_tickets(tickets: list[dict]) -> str:
    if not tickets:
        return "No LATEST ticket bodies were pre-fetched."
    parts: list[str] = []
    for t in tickets:
        desc = (t.get("description_text") or "").strip()
        comments = (t.get("comments_text") or "").strip()
        head = (
            f"### Jira {t.get('key')} — {(t.get('summary') or '').strip()}\n"
            f"Status: **{t.get('status_category', '?')}** · "
            f"Priority: {t.get('priority') or '—'} · "
            f"Updated: {t.get('updated', '?')}"
        )
        if t.get("resolved"):
            head += f" · Resolved: {t.get('resolved')}"
        head += f" · Comments: {t.get('comment_count', 0)}"
        body = ""
        if desc:
            body += f"\n\n**Description:**\n{desc[:1200]}"
        if comments:
            body += f"\n\n**Comments:**\n{comments[:800]}"
        parts.append(head + body)
    return "\n\n---\n\n".join(parts)


def build_seed_message(
    question: str,
    scope_line: str,
    bundle: PreflightBundle,
    summary: str = "",
) -> str:
    """User message for the Deep Search tool-use loop.

    The optional `summary` parameter (G03) is a compacted rolling summary of
    older turns in the same conversation. When non-empty, it's prepended
    after the Question/Scope as a dedicated `**Prior conversation summary**`
    section so the model sees pre-window context without polluting the
    prior_messages role alternation.
    """
    from backend.operational_context import get_context_block
    op_block = get_context_block()
    summary_block = ""
    if summary and summary.strip():
        summary_block = (
            "---\n\n"
            "**Prior conversation summary** (older turns compacted):\n\n"
            f"{summary.strip()}\n\n"
        )
    wiki_text = format_wiki_for_seed(bundle.seed_wiki)
    jira_text = format_jira_buckets_for_seed(bundle.seed_jira)
    tickets_text = format_preflight_tickets(bundle.preflight_tickets)
    latest_count = len(bundle.seed_jira.get("buckets", {}).get("LATEST", []))
    return (
        f"{op_block}"
        f"**Question:** {question}\n"
        f"**Scope:** {scope_line}\n\n"
        f"{summary_block}"
        f"---\n\n"
        f"## Pre-fetched wiki evidence (top {len(bundle.seed_wiki)} pages, ~800-char excerpts)\n\n"
        f"{wiki_text}\n\n"
        f"---\n\n"
        f"## Pre-fetched Jira ranked search ({latest_count} LATEST shown)\n\n"
        f"{jira_text}\n\n"
        f"---\n\n"
        f"## Pre-fetched LATEST ticket bodies ({len(bundle.preflight_tickets)})\n\n"
        f"{tickets_text}\n\n"
        f"---\n\n"
        f"This pre-fetched evidence is your starting context. The wiki + Jira ranked "
        f"search already ran; the top LATEST tickets' full bodies are above. Call "
        f"additional tools (wiki_read_page, jira_get_ticket for a different key, "
        f"jira_search_ranked with a refined keyword, config_lookup, pms_runtime_values) "
        f"ONLY if the pre-fetched evidence is insufficient. Always cite Jira keys "
        f"from the LATEST bucket and treat HISTORICAL/STALE as weaker evidence."
    )


def build_agent_preamble(bundle: PreflightBundle) -> str:
    """Block prepended to the user's question for Claude Code agent mode."""
    wiki_text = format_wiki_for_seed(bundle.seed_wiki)
    jira_text = format_jira_buckets_for_seed(bundle.seed_jira)
    tickets_text = format_preflight_tickets(bundle.preflight_tickets)
    return (
        "## Pre-fetched evidence from Conwo backend\n\n"
        "The Conwo backend has already searched the wiki and Jira mirror and "
        "fetched the most relevant LATEST ticket bodies. Use this as your "
        "starting context, then verify and extend with your own tools "
        "(Read, Grep, Bash on tickets.sqlite, MCP) as needed. Follow the "
        "QUERY workflow in CLAUDE.md Section 5 for the answer structure.\n\n"
        f"### Wiki — top {len(bundle.seed_wiki)} pages (~800-char excerpts)\n\n"
        f"{wiki_text}\n\n"
        f"### Jira — ranked search results (LATEST first)\n\n"
        f"{jira_text}\n\n"
        f"### Jira — full LATEST ticket bodies ({len(bundle.preflight_tickets)})\n\n"
        f"{tickets_text}\n\n"
        "---\n\n"
    )
