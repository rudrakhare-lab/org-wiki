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
import time
from dataclasses import dataclass, field

from backend import jira_retriever, trace_store, wiki_graph, wiki_retriever
from backend.tools import build_registry
from backend.tools.registry import ToolRegistry, ToolTraceEntry
from backend.intent_classifier import classify_intent, IntentResult, QueryIntent
from backend.retrieval.v2.rewrite import rewrite
from backend.retrieval.wiki_v2 import pipeline as _wiki_v2
from backend.retrieval.wiki_v2.pipeline import WikiV2Unavailable

_wiki_v2_search = _wiki_v2.search  # test seam

_PREFLIGHT_LATEST_LIMIT = 2     # auto-fetch top N LATEST tickets
_PREFLIGHT_WIKI_TOP_N = 3       # number of wiki pages to seed
_PREFLIGHT_WIKI_EXCERPT = 800   # wiki excerpt chars per page (was 300)

# Step 5 — module-tagged + related-module preflight (Phase 2)
_PREFLIGHT_DIRECT_LIMIT       = 5   # tickets per direct module
_PREFLIGHT_RELATED_LIMIT      = 2   # tickets per related module
_PREFLIGHT_RELATED_TOTAL_CAP  = 15  # max related tickets aggregated across all parents
_PREFLIGHT_MODULE_TOTAL_CAP   = 25  # max (direct + related) total


def extract_slug_from_path(page_path: str) -> str:
    """Return module slug from a wiki module-page path.

    Examples:
      "modules/meal-management.md" → "meal-management"
      "modules/floor-kiosk.md"     → "floor-kiosk"

    Pre-condition: callers in run_preflight() guard with
    `if not page.path.startswith("modules/"): continue`.
    """
    name = page_path
    if name.startswith("modules/"):
        name = name[len("modules/"):]
    if name.endswith(".md"):
        name = name[:-3]
    return name


def extract_module_dependencies(wiki_page) -> dict:
    """Read depends_on + used_by from page.frontmatter. Tolerant of missing/non-list values."""
    fm = getattr(wiki_page, "frontmatter", None) or {}

    def _list_or_empty(value):
        if isinstance(value, list):
            return [str(s).strip() for s in value if s]
        return []

    return {
        "depends_on": _list_or_empty(fm.get("depends_on")),
        "used_by":    _list_or_empty(fm.get("used_by")),
    }


@dataclass
class PreflightBundle:
    """All preflight retrieval results, ready to be formatted."""
    seed_wiki: list = field(default_factory=list)   # list of wiki Page objects
    seed_jira: dict = field(default_factory=dict)   # full jira_retriever.search result
    preflight_tickets: list[dict] = field(default_factory=list)  # full ticket dicts
    preflight_trace: list[ToolTraceEntry] = field(default_factory=list)
    # Step 5 — module-tagged + related-module pre-fetched tickets
    module_tagged_jira: list[dict] = field(default_factory=list)
    related_module_jira: list[dict] = field(default_factory=list)
    intent_result: "IntentResult | None" = field(default=None)
    seed_wiki_chunks: list = field(default_factory=list)  # list[ChunkHit] (wiki v2 path)
    degradations: list = field(default_factory=list)      # visible seed notes
    # Phase B Task 2 — shared Haiku rewrite, computed once, fed to both pillars
    rewrite_result: object = None                          # RewriteResult | None

    def latest_keys(self) -> list[str]:
        return [r["key"] for r in self.seed_jira.get("buckets", {}).get("LATEST", [])]

    def stats(self) -> dict:
        buckets = self.seed_jira.get("buckets", {})
        return {
            "wiki_pages_seeded": len(self.seed_wiki),
            "jira_latest": len(buckets.get("LATEST", [])),
            "jira_historical": len(buckets.get("HISTORICAL", [])),
            "tickets_prefetched": len(self.preflight_tickets),
            "module_tagged_count": len(self.module_tagged_jira),
            "related_module_count": len(self.related_module_jira),
            "keywords": self.seed_jira.get("keywords", []),
        }


def _compute_rewrite(question: str):
    """Shared Haiku rewrite — one call feeds both retrieval pillars.

    Test seam: tests monkeypatch `preflight.rewrite` and call this directly.
    rewrite() never raises (v2 Task 1 guarantee) — no try/except needed.
    """
    return rewrite(question)


def _fetch_seed_wiki(question: str, top_n: int, intent: str, rewrite):
    """Returns (pages, chunk_hits, degradation_note). Exactly one of
    pages/chunk_hits is populated. Fail-open: v2 failure → keyword path."""
    if _wiki_v2.wiki_v2_enabled():
        try:
            hits = _wiki_v2_search(
                question,
                sub_queries=getattr(rewrite, "sub_queries", None),
                expansions=getattr(rewrite, "expansions", None),
                intent=intent, top_k=top_n * 3)
            return [], hits, None
        except WikiV2Unavailable as exc:
            note = (f"wiki semantic search unavailable ({exc}) — "
                    f"fell back to keyword search; results may be less complete.")
            return wiki_retriever.search(question, top_n=top_n), [], note
    return wiki_retriever.search(question, top_n=top_n), [], None


def format_wiki_chunks_for_seed(hits) -> str:
    if not hits:
        return "No relevant wiki sections found in preflight."
    parts = []
    for h in hits:
        head = f"### `{h.anchor}` — {h.section_title or h.page_path}"
        if h.related_via:
            head += f"\n_(related via: {h.related_via})_"
        parts.append(f"{head}\n\n{h.chunk_text}")
    return "\n\n---\n\n".join(parts)


# ── Preflight runner ────────────────────────────────────────────────────────

def run_preflight(
    question: str,
    functional_area: str | None = None,
    registry: ToolRegistry | None = None,
    latest_limit: int = _PREFLIGHT_LATEST_LIMIT,
    trace_id: str | None = None,
    agent=None,
) -> PreflightBundle:
    """Run the deterministic preflight retrieval. Always runs for every query.

    Parameters
    ----------
    agent:
        An ``AgentSpec`` instance (from ``backend.agent_registry``).
        When ``None``, defaults to the conwo agent (``has_jira=True``).
        Pass an agent with ``has_jira=False`` (e.g. Infosec) to skip all
        Jira retrieval — wiki search always runs regardless.
    """
    if agent is None:
        from backend import agent_registry
        agent = agent_registry.default()

    bundle = PreflightBundle()

    # classify intent and apply retrieval hints
    _intent_result = classify_intent(question)
    bundle.intent_result = _intent_result
    _hints = _intent_result.retrieval_hints
    _search_query = _intent_result.rewritten_query
    _wiki_top_n_eff = _hints.get("wiki_top_n", _PREFLIGHT_WIKI_TOP_N)
    _latest_limit_eff = _hints.get("jira_latest_limit", latest_limit)

    # Shared Haiku rewrite — computed ONCE, fed to both the wiki v2 seed
    # search and the jira v2 pipeline (Phase B Task 2). Never raises.
    bundle.rewrite_result = _compute_rewrite(_search_query)

    # Wiki search always runs — it is universal to all agents. Tries the wiki
    # v2 semantic pipeline first (default-on); falls back to the keyword
    # index (with a visible degradation note) when v2 is off or unavailable.
    _t = time.perf_counter()
    _pages, _chunk_hits, _degradation_note = _fetch_seed_wiki(
        _search_query, _wiki_top_n_eff,
        intent=bundle.intent_result.intent.value if bundle.intent_result else "GENERAL",
        rewrite=bundle.rewrite_result)
    bundle.seed_wiki = _pages
    bundle.seed_wiki_chunks = _chunk_hits
    if _degradation_note:
        bundle.degradations.append(_degradation_note)
    trace_store.record_event(
        trace_id, "preflight", "preflight_wiki",
        duration_ms=int((time.perf_counter() - _t) * 1000), round_num=0,
        metadata={"results_count": len(bundle.seed_wiki) + len(bundle.seed_wiki_chunks),
                  "engine": "v2" if bundle.seed_wiki_chunks else
                            ("keyword-fallback" if _degradation_note else "keyword"),
                  "top_paths": [p.path for p in bundle.seed_wiki[:3]] or
                               [h.page_path for h in bundle.seed_wiki_chunks[:3]]})

    if agent.has_jira:
        _t = time.perf_counter()
        bundle.seed_jira = jira_retriever.search(
            _search_query, functional_area=functional_area,
            rewrite_result=bundle.rewrite_result)
        _buckets = bundle.seed_jira.get("buckets", {})          # buckets are NESTED under "buckets"
        trace_store.record_event(
            trace_id, "preflight", "preflight_jira",
            duration_ms=int((time.perf_counter() - _t) * 1000), round_num=0,
            metadata={"bucket_counts": {
                "LATEST": len(_buckets.get("LATEST", [])),
                "HISTORICAL": len(_buckets.get("HISTORICAL", [])),
                "STALE-OPEN": len(_buckets.get("STALE-OPEN", []))}})
    else:
        # Wiki-only agent — no Jira retrieval at all.
        bundle.seed_jira = {"buckets": {}}

    if registry is None:
        registry = build_registry()

    if agent.has_jira:
        # Step 5 — module-tagged + related-module pre-fetch.
        # For each module page in seed_wiki, fetch (a) direct module-tagged tickets
        # query-filtered, and (b) related-module tickets via depends_on + used_by
        # (one hop). Dedup: direct wins over related. Total capped at 25.
        seen_modules: set[str] = set()
        # Module-page paths come from whichever seed path actually served:
        # keyword path populates seed_wiki (Page objects), wiki v2 populates
        # seed_wiki_chunks (ChunkHit objects) — union both so the downstream
        # module-tagged/related-module ticket fetch works on either path.
        _module_page_paths = [p.path for p in bundle.seed_wiki]
        _module_page_paths += [h.page_path for h in bundle.seed_wiki_chunks]
        _seen_module_pages: set[str] = set()
        for page_path in _module_page_paths:
            if page_path in _seen_module_pages:
                continue
            _seen_module_pages.add(page_path)
            if not page_path.startswith("modules/"):
                continue
            module_slug = extract_slug_from_path(page_path)
            if module_slug in seen_modules:
                continue
            seen_modules.add(module_slug)

            direct = jira_retriever.by_module(
                module_slug, query=question, limit=_PREFLIGHT_DIRECT_LIMIT
            )
            for t in direct:
                t["_preflight_source"] = "direct"
                t["_preflight_module"] = module_slug
            bundle.module_tagged_jira.extend(direct)

            # Related modules now come from wiki_graph (spec §5.3) instead of
            # reading only this page's own depends_on/used_by frontmatter —
            # neighbors() is bidirectional, so a module declaring
            # `depends_on: [module_slug]` elsewhere also surfaces here. The
            # existing dedup/cap logic below still bounds the fan-out.
            related_edges = wiki_graph.get_graph().neighbors(
                page_path, types=("depends_on", "used_by"))
            for related_path, _edge_type in related_edges:
                related_slug = extract_slug_from_path(related_path)
                if related_slug in seen_modules:
                    continue
                if len(bundle.related_module_jira) >= _PREFLIGHT_RELATED_TOTAL_CAP:
                    break
                seen_modules.add(related_slug)

                related = jira_retriever.by_module(
                    related_slug, query=question, limit=_PREFLIGHT_RELATED_LIMIT
                )
                for t in related:
                    t["_preflight_source"]      = "related"
                    t["_preflight_module"]      = related_slug
                    t["_preflight_relation_to"] = module_slug
                bundle.related_module_jira.extend(related)

        # Dedup: drop related-tickets whose key already appears in direct.
        direct_keys = {t["key"] for t in bundle.module_tagged_jira}
        bundle.related_module_jira = [
            t for t in bundle.related_module_jira if t["key"] not in direct_keys
        ]

        # Total cap — trim related (preserve direct).
        if len(bundle.module_tagged_jira) + len(bundle.related_module_jira) > _PREFLIGHT_MODULE_TOTAL_CAP:
            keep_related = max(0, _PREFLIGHT_MODULE_TOTAL_CAP - len(bundle.module_tagged_jira))
            bundle.related_module_jira = bundle.related_module_jira[:keep_related]

        if bundle.module_tagged_jira:
            trace_store.record_event(
                trace_id, "preflight", "preflight_module_tagged", round_num=0,
                metadata={
                    "module_count": len({t.get("_preflight_module")
                                         for t in bundle.module_tagged_jira if t.get("_preflight_module")}),
                    "ticket_count": len(bundle.module_tagged_jira),
                    "modules": sorted({t.get("_preflight_module")
                                       for t in bundle.module_tagged_jira if t.get("_preflight_module")})})
        if bundle.related_module_jira:
            trace_store.record_event(
                trace_id, "preflight", "preflight_related_module", round_num=0,
                metadata={
                    "module_count": len({t.get("_preflight_module")
                                         for t in bundle.related_module_jira if t.get("_preflight_module")}),
                    "ticket_count": len(bundle.related_module_jira),
                    "via_module": sorted({t.get("_preflight_relation_to")
                                          for t in bundle.related_module_jira if t.get("_preflight_relation_to")})})

        # Auto-fetch top LATEST tickets so the model NEVER has to guess based on
        # the summary alone. Goes through the registry so the trace is sanitized
        # and consistent with model-initiated tool calls.
        keys_to_fetch = bundle.latest_keys()[:_latest_limit_eff]
        for key in keys_to_fetch:
            json_output, entry = registry.execute(
                name="jira_get_ticket",
                tool_input={"key": key},
                round_num=0,   # 0 = preflight (model rounds start at 1)
                trace_id=trace_id,
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


def format_module_tagged_for_seed(rows: list[dict]) -> str:
    """Format direct module-tagged tickets. Returns "" if empty (no header printed)."""
    if not rows:
        return ""
    by_mod: dict[str, list[dict]] = {}
    for r in rows:
        by_mod.setdefault(r.get("_preflight_module", "?"), []).append(r)

    lines: list[str] = [
        "## Pre-fetched module-tagged tickets (query-filtered)",
        "",
    ]
    for mod_slug in sorted(by_mod):
        tickets = by_mod[mod_slug]
        lines.append(f"### `{mod_slug}` ({len(tickets)} ticket(s))")
        for t in tickets:
            summary = (t.get("summary") or "")[:120]
            updated = t.get("updated", "?")
            resolved = t.get("resolved")
            mod_conf = t.get("module_confidence")
            tail = f"resolved {resolved}" if resolved else f"updated {updated}"
            conf_str = f" · module-conf={mod_conf:.2f}" if mod_conf is not None else ""
            other_modules = [
                f"{m['slug']}({m['confidence']:.2f})"
                for m in (t.get("modules") or [])
                if m.get("slug") != mod_slug
            ]
            xmod = f" · also: {', '.join(other_modules)}" if other_modules else ""
            lines.append(f"- `{t.get('key')}` · {tail}{conf_str}{xmod}")
            lines.append(f"  > {summary}")
        lines.append("")
    return "\n".join(lines)


def format_related_module_for_seed(rows: list[dict]) -> str:
    """Format related-module tickets grouped by relation_to → module. Returns "" if empty."""
    if not rows:
        return ""
    by_rel: dict[str, dict[str, list[dict]]] = {}
    for r in rows:
        rel_to = r.get("_preflight_relation_to", "?")
        mod = r.get("_preflight_module", "?")
        by_rel.setdefault(rel_to, {}).setdefault(mod, []).append(r)

    lines: list[str] = [
        "## Pre-fetched related-module tickets (1-hop dependency graph, query-filtered)",
        "",
    ]
    for parent in sorted(by_rel):
        for related in sorted(by_rel[parent]):
            tickets = by_rel[parent][related]
            lines.append(f"### `{parent}` → `{related}` ({len(tickets)} ticket(s))")
            for t in tickets:
                summary = (t.get("summary") or "")[:120]
                updated = t.get("updated", "?")
                resolved = t.get("resolved")
                mod_conf = t.get("module_confidence")
                tail = f"resolved {resolved}" if resolved else f"updated {updated}"
                conf_str = f" · module-conf={mod_conf:.2f}" if mod_conf is not None else ""
                lines.append(f"- `{t.get('key')}` · {tail}{conf_str}")
                lines.append(f"  > {summary}")
            lines.append("")
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
    agent=None,
) -> str:
    """User message for the Deep Search tool-use loop.

    The optional ``summary`` parameter (G03) is a compacted rolling summary of
    older turns in the same conversation. When non-empty, it's prepended
    after the Question/Scope as a dedicated ``**Prior conversation summary**``
    section so the model sees pre-window context without polluting the
    prior_messages role alternation.

    The optional ``agent`` parameter (``AgentSpec``) controls whether Jira
    evidence sections are included. When ``None``, defaults to conwo
    (``has_jira=True``).  For wiki-only agents (``has_jira=False``) the Jira
    ranked search, module-tagged, related-module, and preflight-ticket sections
    are omitted entirely — only wiki evidence and the closing tool-call
    instruction (adjusted for no-Jira) are emitted.
    """
    if agent is None:
        from backend import agent_registry
        agent = agent_registry.default()

    from backend.operational_context import get_context_block
    op_block = get_context_block()
    summary_block = ""
    if summary and summary.strip():
        summary_block = (
            "---\n\n"
            "**Prior conversation summary** (older turns compacted):\n\n"
            f"{summary.strip()}\n\n"
        )
    if bundle.seed_wiki_chunks:
        wiki_text = format_wiki_chunks_for_seed(bundle.seed_wiki_chunks)
        _wiki_evidence_count = len(bundle.seed_wiki_chunks)
        _wiki_evidence_label = "sections"
    else:
        wiki_text = format_wiki_for_seed(bundle.seed_wiki)
        _wiki_evidence_count = len(bundle.seed_wiki)
        _wiki_evidence_label = "pages"
    _intent_line = ""
    if bundle.intent_result and bundle.intent_result.intent != QueryIntent.GENERAL:
        ir = bundle.intent_result
        _intent_line = (
            f"**Intent:** {ir.intent.value} (conf: {ir.confidence:.2f})"
            f" | query: \"{ir.rewritten_query}\"\n"
        )

    degradation_block = ""
    if bundle.degradations:
        degradation_block = (
            "## Degradation notes\n\n"
            + "\n".join(f"- ⚠️ {d}" for d in bundle.degradations)
            + "\n\n---\n\n"
        )

    header = (
        f"{op_block}"
        f"**Question:** {question}\n"
        f"**Scope:** {scope_line}\n"
        f"{_intent_line}\n"
        f"{summary_block}"
        f"---\n\n"
        f"{degradation_block}"
        f"## Pre-fetched wiki evidence (top {_wiki_evidence_count} {_wiki_evidence_label}, ~800-char excerpts)\n\n"
        f"{wiki_text}\n\n"
        f"---\n\n"
    )

    if not agent.has_jira:
        # Wiki-only agent — omit all Jira sections.
        return (
            header
            + "This pre-fetched evidence is your starting context. The wiki search "
            "already ran; call additional tools (wiki_read_page, wiki_search) "
            "ONLY if the pre-fetched evidence is insufficient."
        )

    # Conwo (and any has_jira agent) — include full Jira evidence.
    jira_text = format_jira_buckets_for_seed(bundle.seed_jira)
    tickets_text = format_preflight_tickets(bundle.preflight_tickets)
    module_tagged_text  = format_module_tagged_for_seed(bundle.module_tagged_jira)
    related_module_text = format_related_module_for_seed(bundle.related_module_jira)
    module_tagged_block  = (module_tagged_text  + "\n---\n\n") if module_tagged_text  else ""
    related_module_block = (related_module_text + "\n---\n\n") if related_module_text else ""
    latest_count = len(bundle.seed_jira.get("buckets", {}).get("LATEST", []))

    return (
        header
        + f"## Pre-fetched Jira ranked search ({latest_count} LATEST shown)\n\n"
        f"{jira_text}\n\n"
        f"---\n\n"
        f"{module_tagged_block}"
        f"{related_module_block}"
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


_INTENT_TOOL_SEQUENCES: dict[QueryIntent, str] = {
    QueryIntent.CONFIGURATION: """\
**REQUIRED TOOL SEQUENCE — CONFIGURATION intent (use ALL steps, do not skip):**
1. `config_lookup` — precise definition, data_type, criteria_priority_list, pre-indexed Jira pointers
2. `jira_search_ranked` — **MANDATORY even after config_lookup**; search property name for live operational context (recent bugs, changes, incidents). The `jira_tickets` in config_lookup are pre-indexed and may miss recent activity.
3. `jira_get_ticket` — read the top 3–5 tickets from the Jira search IN FULL (description + resolution + comments)
4. `wiki_read_page` on the relevant `configs/<service>.md` page — see all configs in the same service for related-config context
5. If a BUID is mentioned: `pms_diagnose_property` using `criteria_priority_list` from config_lookup to decide which hierarchy levels to check
**Never stop after step 1. Jira search is mandatory for every config query.**""",

    QueryIntent.DEBUGGING: """\
**REQUIRED TOOL SEQUENCE — DEBUGGING intent (use ALL steps, do not skip):**
1. `jira_search_ranked` — deep search (jira_latest_limit=10); read LATEST bucket first, Historical second
2. `jira_get_ticket` — read top 4–5 matching tickets IN FULL (especially resolution text)
3. `config_lookup` — if a config property name is mentioned or implied
4. `wiki_read_page` on the relevant module page — understand expected behavior to identify the deviation
5. `pms_diagnose_property` — if a BUID is given; walk the hierarchy to find the culprit config value
**Read real ticket content before synthesizing. Do not guess the fix from just the summary.**""",

    QueryIntent.HOW_TO: """\
**REQUIRED TOOL SEQUENCE — HOW_TO intent (use ALL steps):**
1. `wiki_read_page` — the relevant module page(s) for the step-by-step process
2. `config_lookup` — if a config property is mentioned or needed for setup/enablement
3. `jira_search_ranked` — for gotchas, known issues, prerequisites discovered in practice
**Answer must be step-by-step. Combine wiki process + config requirements + Jira-discovered caveats.**""",

    QueryIntent.DEFINITION: """\
**REQUIRED TOOL SEQUENCE — DEFINITION intent:**
1. `wiki_read_page` — the relevant module or concept page for the authoritative definition
2. `config_lookup` — if the question is about a config property name (camelCase token)
3. `jira_search_ranked` — for operational context, real-world usage examples, known edge cases
**Definition = wiki structure + config precision + Jira operational reality. Use all three.**""",

    QueryIntent.STATUS: """\
**REQUIRED TOOL SEQUENCE — STATUS intent:**
1. `jira_search_ranked` — deep search (limit=10), focus on LATEST bucket; read ticket bodies in full
2. `jira_get_ticket` — top 3–5 tickets in the LATEST bucket IN FULL
3. `wiki_read_page` — for background context on the feature/module to frame the status
**Recency wins. A ticket from last month outweighs a wiki page from last year.**""",

    QueryIntent.COMPARISON: """\
**REQUIRED TOOL SEQUENCE — COMPARISON intent:**
1. `wiki_read_page` — read pages for BOTH subjects being compared
2. `config_lookup` — for BOTH configs if comparing config properties
3. `jira_search_ranked` — search BOTH subjects independently for operational differences
**Both sides must be addressed explicitly. Do not compare from memory — read both sources.**""",

    QueryIntent.ARCHITECTURAL: """\
**REQUIRED TOOL SEQUENCE — ARCHITECTURAL intent:**
1. `wiki_read_page` — the relevant module page(s) and any cross-module pages
2. Follow `[[wikilinks]]` in those pages to related modules and read them too
3. `jira_search_ranked` — for architectural decisions, known design changes, integration issues
**Architecture answers must trace actual dependencies in the wiki, not infer them.**""",
}


def build_agent_preamble(bundle: PreflightBundle) -> str:
    """Block prepended to the user's question for Claude Code agent mode."""
    if bundle.seed_wiki_chunks:
        wiki_text = format_wiki_chunks_for_seed(bundle.seed_wiki_chunks)
        _wiki_evidence_count = len(bundle.seed_wiki_chunks)
        _wiki_evidence_label = "sections"
    else:
        wiki_text = format_wiki_for_seed(bundle.seed_wiki)
        _wiki_evidence_count = len(bundle.seed_wiki)
        _wiki_evidence_label = "pages"
    jira_text = format_jira_buckets_for_seed(bundle.seed_jira)
    tickets_text = format_preflight_tickets(bundle.preflight_tickets)
    module_tagged_text  = format_module_tagged_for_seed(bundle.module_tagged_jira)
    related_module_text = format_related_module_for_seed(bundle.related_module_jira)
    module_tagged_block  = (module_tagged_text  + "\n") if module_tagged_text  else ""
    related_module_block = (related_module_text + "\n") if related_module_text else ""

    _intent_line = ""
    _tool_sequence = ""
    if bundle.intent_result and bundle.intent_result.intent != QueryIntent.GENERAL:
        ir = bundle.intent_result
        _intent_line = (
            f"**Intent:** {ir.intent.value} (conf: {ir.confidence:.2f})"
            f" | query: \"{ir.rewritten_query}\"\n\n"
        )
        seq = _INTENT_TOOL_SEQUENCES.get(ir.intent, "")
        if seq:
            _tool_sequence = f"{seq}\n\n"

    degradation_block = ""
    if bundle.degradations:
        degradation_block = (
            "## Degradation notes\n\n"
            + "\n".join(f"- ⚠️ {d}" for d in bundle.degradations)
            + "\n\n---\n\n"
        )

    return (
        f"{_intent_line}"
        f"{_tool_sequence}"
        f"{degradation_block}"
        "## Pre-fetched evidence from Conwo backend\n\n"
        "The Conwo backend has already searched the wiki and Jira mirror and "
        "fetched the most relevant LATEST ticket bodies. Use this as your "
        "starting context, then verify and extend with your own tools "
        "(Read, Grep, Bash on tickets.sqlite, MCP) as needed. Follow the "
        "QUERY workflow in CLAUDE.md Section 5 for the answer structure.\n\n"
        "**IMPORTANT — Do NOT stop after the first good source.** "
        "Every answer must draw from ALL applicable knowledge bases: "
        "wiki pages (structure), config SQLite (precise definitions + hierarchy), "
        "Jira tickets (operational history + recent changes), "
        "PMS live (actual runtime values, only if BUID given). "
        "Combining all sources produces the most accurate answer.\n\n"
        f"### Wiki — top {_wiki_evidence_count} {_wiki_evidence_label} (~800-char excerpts)\n\n"
        f"{wiki_text}\n\n"
        f"### Jira — ranked search results (LATEST first)\n\n"
        f"{jira_text}\n\n"
        f"{module_tagged_block}"
        f"{related_module_block}"
        f"### Jira — full LATEST ticket bodies ({len(bundle.preflight_tickets)})\n\n"
        f"{tickets_text}\n\n"
        "---\n\n"
    )
