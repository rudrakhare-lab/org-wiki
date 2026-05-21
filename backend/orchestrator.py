"""
Query orchestrator — coordinates wiki retrieval, Jira retrieval, and LLM call.

Flow (deep mode, default for mode="api"):
  1. Pre-seed compact wiki + Jira context (top_n=3 / limit=10, 300-char excerpts)
  2. Build user message embedding the seeded context
  3. Load deep system prompt
  4. Run DeepQueryProvider.generate_with_tools() — Anthropic tool_use loop, max 8 rounds
  5. Parse response → extract Answer / Confidence / Sources from tool trace
  6. log_answer() → answer_id
  7. Return OrchestratorResult (with tool_trace, missing_context, deep_search_used=True)

Flow (single-shot mode, used for mode="claude-code"):
  1–3 unchanged: full wiki context (top_n=5) + full Jira markdown
  4. ClaudeCodeProvider subprocess call
  5–7 unchanged
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal

from backend import conversation_store, jira_retriever, wiki_retriever
from backend.feedback_service import log_answer
from backend.providers.anthropic_api import AnthropicAPIProvider
from backend.providers.claude_code import ClaudeCodeProvider
from backend.system_prompt import load_system_prompt


def _load_conversation_context(conversation_id: str, max_turns: int = 6) -> list[dict]:
    """Return last N user+assistant message pairs from conversation history.

    Capped at max_turns * 2 messages so context stays within ~12K tokens.
    """
    conv = conversation_store.get_conversation(conversation_id)
    if not conv:
        return []
    msgs = [m for m in conv.get("messages", []) if m["role"] in ("user", "assistant")]
    tail = msgs[-(max_turns * 2):]
    return [{"role": m["role"], "content": m["content"]} for m in tail]


@dataclass
class SourceInfo:
    wiki_pages: list[str] = field(default_factory=list)
    jira_keys: list[str] = field(default_factory=list)
    pms_configs: list[str] = field(default_factory=list)


@dataclass
class OrchestratorResult:
    answer_id: str
    answer_text: str
    confidence: str          # "High" | "Medium" | "Low"
    sources: SourceInfo
    retrieval: dict          # raw retrieval metadata for debugging
    mode: str = "api"        # which provider was used
    error: str = ""
    tool_trace: list[dict] = field(default_factory=list)
    missing_context: list[str] = field(default_factory=list)
    deep_search_used: bool = False


def run(
    question: str,
    mode: Literal["api", "claude-code"] = "api",
    claude_api_key: str | None = None,
    server: str = "com",
    buid: str | None = None,
    functional_area: str | None = None,
    service: str | None = None,
    officeid: str | None = None,
    roomid: str | None = None,
    role: str | None = None,
    user_role: str = "viewer",
    conversation_id: str | None = None,
) -> OrchestratorResult:
    """
    Execute the full QUERY workflow and return a structured result.

    mode="api":          claude_api_key required — runs deep search tool loop.
    mode="claude-code":  claude_api_key ignored — single-shot subprocess call.
    """
    if mode == "claude-code":
        result = run_single_shot(question, mode, None, server, buid, functional_area, user_role)
        result.deep_search_used = False
        return result
    return run_deep(
        question, mode, claude_api_key, server, buid, functional_area,
        service, officeid, roomid, role, user_role, conversation_id,
    )


def run_deep(
    question: str,
    mode: str,
    claude_api_key: str | None,
    server: str = "com",
    buid: str | None = None,
    functional_area: str | None = None,
    service: str | None = None,
    officeid: str | None = None,
    roomid: str | None = None,
    role: str | None = None,
    user_role: str = "viewer",
    conversation_id: str | None = None,
) -> OrchestratorResult:
    """Agentic deep search via Anthropic tool_use loop with deterministic preflight."""
    from backend.deep_system_prompt import load_deep_system_prompt
    from backend.preflight import build_seed_message, run_preflight
    from backend.providers.deep_query import DeepQueryProvider
    from backend.tools import build_registry

    # Build registry once; preflight + tool loop share it
    registry = build_registry(user_role=user_role)

    # 1. Deterministic preflight: wiki search + Jira ranked search +
    #    full bodies of top LATEST tickets. Runs for EVERY query.
    bundle = run_preflight(question, functional_area=functional_area, registry=registry)

    # 2. Build seeded user message (full Jira bodies + larger wiki excerpts)
    scope_parts: list[str] = [f".{server} server"]
    if buid:
        scope_parts.append(f"BUID: `{buid}`")
    if service:
        scope_parts.append(f"service: {service}")
    if officeid:
        scope_parts.append(f"OFFICEID: `{officeid}`")
    if roomid:
        scope_parts.append(f"ROOMID: `{roomid}`")
    if role:
        scope_parts.append(f"role: {role}")

    user_message = build_seed_message(question, " | ".join(scope_parts), bundle)

    # 3. Run tool loop (using the SAME registry that the preflight used)
    system_prompt = load_deep_system_prompt()
    provider = DeepQueryProvider(api_key=claude_api_key or "")
    history = _load_conversation_context(conversation_id) if conversation_id else []
    deep_result = provider.generate_with_tools(
        system_prompt=system_prompt,
        user_message=user_message,
        tool_registry=registry,
        prior_messages=history,
    )

    # Preflight tool calls (round_num=0) appear first in the trace
    deep_result.tool_trace = bundle.preflight_trace + deep_result.tool_trace

    if not deep_result.ok:
        return OrchestratorResult(
            answer_id="",
            answer_text="",
            confidence="Low",
            sources=SourceInfo(),
            retrieval={},
            mode=mode,
            error=deep_result.error,
            tool_trace=deep_result.tool_trace,
            missing_context=deep_result.missing_context,
            deep_search_used=True,
        )

    # 4. Extract sources from tool trace (preflight + model rounds combined)
    raw_answer = deep_result.raw_answer
    confidence = _extract_confidence(raw_answer)
    cited_wiki = _trace_wiki_paths(deep_result.tool_trace, bundle.seed_wiki)
    cited_jira = _trace_jira_keys(deep_result.tool_trace, bundle.seed_jira)
    cited_pms = _extract_pms_configs(raw_answer)
    sources = SourceInfo(wiki_pages=cited_wiki, jira_keys=cited_jira, pms_configs=cited_pms)

    # 5. Log answer
    pf_stats = bundle.stats()
    answer_id = log_answer(
        question=question,
        answer_text=raw_answer,
        confidence=confidence,
        wiki_pages=cited_wiki,
        jira_keys=cited_jira,
        pms_configs=cited_pms,
        retrieval_notes=(
            f"deep_search rounds={deep_result.rounds_used} "
            f"tools={len(deep_result.tool_trace)} "
            f"preflight_tickets={pf_stats['tickets_prefetched']} server={server}"
        ),
    )

    return OrchestratorResult(
        answer_id=answer_id,
        answer_text=raw_answer,
        confidence=confidence,
        sources=sources,
        retrieval={
            "rounds_used": deep_result.rounds_used,
            "tool_calls": len(deep_result.tool_trace),
            "preflight": pf_stats,
        },
        mode=mode,
        tool_trace=deep_result.tool_trace,
        missing_context=deep_result.missing_context,
        deep_search_used=True,
    )


def run_single_shot(
    question: str,
    mode: str,
    claude_api_key: str | None,
    server: str = "com",
    buid: str | None = None,
    functional_area: str | None = None,
    user_role: str = "viewer",
) -> OrchestratorResult:
    """Single-shot RAG — used for mode=claude-code (subprocess can't do tool_use)."""
    # 1. Wiki retrieval
    wiki_pages = wiki_retriever.search(question, top_n=5)

    # 2. Jira retrieval
    jira_result = jira_retriever.search(question, functional_area=functional_area)

    # 3. Build context
    wiki_context = _format_wiki_context(wiki_pages)
    jira_context = jira_result["markdown"]

    # 4. Build user message
    server_note = f"\n**Server context:** .{server} server" + (
        f" | BUID: `{buid}`" if buid else ""
    )
    user_message = (
        f"**Question:** {question}{server_note}\n\n"
        f"---\n\n## Wiki evidence\n\n{wiki_context}\n\n"
        f"---\n\n## Jira evidence\n\n{jira_context}"
    )

    # 5. Select provider and call
    system_prompt = load_system_prompt()
    provider = _select_provider(mode, claude_api_key)
    provider_result = provider.generate(system_prompt, user_message)

    if not provider_result.ok:
        return OrchestratorResult(
            answer_id="",
            answer_text="",
            confidence="Low",
            sources=SourceInfo(),
            retrieval={},
            mode=mode,
            error=provider_result.error,
        )

    # 6. Parse response
    raw_answer = provider_result.raw_answer
    confidence = _extract_confidence(raw_answer)
    cited_wiki = [p.path for p in wiki_pages]
    cited_jira = _extract_jira_keys(jira_result["rows"])
    cited_pms = _extract_pms_configs(raw_answer)
    sources = SourceInfo(wiki_pages=cited_wiki, jira_keys=cited_jira, pms_configs=cited_pms)

    # 7. Log answer
    answer_id = log_answer(
        question=question,
        answer_text=raw_answer,
        confidence=confidence,
        wiki_pages=cited_wiki,
        jira_keys=cited_jira,
        pms_configs=cited_pms,
        retrieval_notes=f"mode={mode} keywords={jira_result['keywords']} server={server}",
    )

    return OrchestratorResult(
        answer_id=answer_id,
        answer_text=raw_answer,
        confidence=confidence,
        sources=sources,
        retrieval={
            "wiki_pages_count": len(wiki_pages),
            "jira_keywords": jira_result["keywords"],
            "jira_latest": len(jira_result["buckets"]["LATEST"]),
            "jira_historical": len(jira_result["buckets"]["HISTORICAL"]),
        },
        mode=mode,
    )


def search_only(question: str, server: str = "com") -> dict:
    """Retrieval-only path — no LLM. Returns raw wiki + Jira results."""
    wiki_pages = wiki_retriever.search(question, top_n=5)
    jira_result = jira_retriever.search(question)
    return {
        "wiki_pages": [
            {"path": p.path, "title": p.title, "excerpt": p.excerpt(400)}
            for p in wiki_pages
        ],
        "jira_markdown": jira_result["markdown"],
        "jira_buckets": {
            k: [_row_summary(r) for r in v]
            for k, v in jira_result["buckets"].items()
        },
        "jira_keywords": jira_result["keywords"],
    }


def claude_code_available() -> bool:
    return ClaudeCodeProvider.available()


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _select_provider(mode: str, api_key: str | None):
    if mode == "claude-code":
        return ClaudeCodeProvider()
    return AnthropicAPIProvider(api_key or "")


def _format_seed_wiki(pages: list) -> str:
    if not pages:
        return "No relevant wiki pages found in initial seed."
    parts: list[str] = []
    for page in pages:
        parts.append(f"- **{page.title}** (`{page.path}`): {page.excerpt(300)}")
    return "\n".join(parts)


def _format_seed_jira(jira_result: dict) -> str:
    buckets = jira_result.get("buckets", {})
    lines: list[str] = []
    for bucket, rows in buckets.items():
        if not rows:
            continue
        lines.append(f"**{bucket}:**")
        for row in rows[:2]:
            lines.append(
                f"  - {row.get('key')} — {(row.get('summary') or '')[:100]} "
                f"(updated {row.get('updated', '?')})"
            )
    return "\n".join(lines) if lines else "No relevant Jira tickets found in initial seed."


def _trace_wiki_paths(tool_trace: list[dict], seed_pages: list) -> list[str]:
    """Extract wiki paths from wiki_read_page tool calls in the trace."""
    paths = [p.path for p in seed_pages]
    for entry in tool_trace:
        if entry.get("tool_name") == "wiki_read_page":
            p = entry.get("input", {}).get("path", "")
            if p and p not in paths:
                paths.append(p)
    return paths


def _trace_jira_keys(tool_trace: list[dict], seed_jira: dict) -> list[str]:
    """Extract Jira keys from jira_get_ticket calls + LATEST seed bucket."""
    keys = [r["key"] for r in seed_jira.get("buckets", {}).get("LATEST", [])]
    for entry in tool_trace:
        if entry.get("tool_name") == "jira_get_ticket":
            k = entry.get("input", {}).get("key", "")
            if k and k not in keys:
                keys.append(k)
    return keys[:10]


def _format_wiki_context(pages: list) -> str:
    if not pages:
        return "No relevant wiki pages found."
    parts: list[str] = []
    for page in pages:
        parts.append(f"### {page.title} (`{page.path}`)\n\n{page.full_text[:3000]}")
    return "\n\n---\n\n".join(parts)


def _extract_confidence(text: str) -> str:
    m = re.search(r"\*{0,2}Confidence[:\s*]+\*{0,2}(High|Medium|Low)", text, re.IGNORECASE)
    if m:
        return m.group(1).capitalize()
    m2 = re.search(r"Suggested confidence[:\s]+(High|Medium|Low)", text, re.IGNORECASE)
    if m2:
        return m2.group(1).capitalize()
    return "Medium"


def _extract_jira_keys(rows: list[dict]) -> list[str]:
    return [r["key"] for r in rows if r.get("bucket") == "LATEST"][:10]


def _extract_pms_configs(text: str) -> list[str]:
    matches = re.findall(r"`([A-Z]{2,}:[a-zA-Z][a-zA-Z0-9]+)`|`([a-z][a-zA-Z0-9]{5,})`", text)
    configs: list[str] = []
    for m in matches:
        val = m[0] or m[1]
        if val and val not in configs:
            configs.append(val)
    return configs[:10]


def _row_summary(row: dict) -> dict:
    return {
        "key": row.get("key"),
        "summary": (row.get("summary") or "")[:120],
        "status": row.get("status_category"),
        "updated": row.get("updated"),
        "resolved": row.get("resolved"),
        "comment_count": row.get("comment_count", 0),
        "hit_summary": bool(row.get("hit_summary")),
    }
