"""
STEP 6.5 DRAFT — backend/tools/jira_cross_module.py (new file).

Provides EXPLICITLY agent-initiated cross-module Jira retrieval. Distinct
from Step 5 preflight (which auto-pulls module-tagged + 1-hop tickets for
any module page that appears in seed_wiki) in two ways:

  1. Agent triggers it on demand — for follow-up "why does X depend on Y?"
     questions that aren't satisfied by preflight's auto-fetch.
  2. Tighter scoping — agent specifies primary_module + include_relations
     (depends_on / used_by / both) + optional type/status filters.

==============================================================================
CARRIED-FORWARD CORRECTED ENUMS (from Step 0/2/3 findings)
==============================================================================

  type_bucket:    task | bug | story | epic | other            (NO feature/pb/spike)
  status_bucket:  resolved | in_progress | open | other        (derived from status_category)

==============================================================================
DESIGN CHOICE 1 — frontmatter read: direct file vs wiki_retriever
==============================================================================

Decision: DIRECT FILE READ via python-frontmatter.

Reasons:
  - This handler is on-demand (agent-initiated), not on the preflight hot path.
    The Step-5 wiki_retriever frontmatter cache is justified by preflight's
    every-query overhead; here we read one file per call.
  - No dependency on wiki_retriever being initialized — works even in cold-start
    or subprocess contexts.
  - Simpler error path: file existence check is local, doesn't depend on the
    in-memory index state.
  - Same library (python-frontmatter) as wiki_propose_tools and the Step 5
    wiki_retriever extension — semantics are identical.

==============================================================================
DESIGN CHOICE 2 — type_bucket / status_bucket filtering: post-filter vs SQL JOIN
==============================================================================

Decision: POST-FILTER (Option A from the plan).

Reasons:
  - Keeps the Step-4 by_module() contract stable. by_module is now well-tested
    (Step 4 + Step 5 reviewed it). Extending its signature with two more
    filter kwargs would mean re-approving Step 4.
  - Cross-module is a CONTEXT tool, not an exhaustive enumeration tool. If
    the post-filter reduces results, the agent can call by_module directly
    with a different filter, or call jira_count for exact totals.
  - The bucket lookup is one batched SELECT against ticket_classifications
    (indexed PK) — covers ALL collected keys across primary + all related
    modules in a single roundtrip.

Trade-off accepted: when type_bucket/status_bucket are set, by_module's
limit_per_module is the PRE-filter limit. Post-filter may return fewer
matches. The response includes a `pre_filter_count` per group so the agent
can detect this case ("we fetched 5, only 1 matched the bug filter").

==============================================================================
TEST CASES (for Step 9 verification)
==============================================================================

  1. jira_search_cross_module(primary_module="meal-management",
                              query="check-in failing")
     Expected:
       primary.module = "meal-management"
       primary.tickets matches "check-in failing" keywords
       related[*].module ∈ {access-management, floor-kiosk,
                            desk-management, meeting-rooms}  (from meal-mgmt's depends_on)
       related[*].module also includes used_by entries (just "access-management")
       Each related[*].tickets is query-filtered to the same keywords.

  2. jira_search_cross_module(primary_module="desk-management")
     (stub module: depends_on=[], used_by=[access-management, delegation,
      implementation, meal-management, parking-management])
     Expected:
       primary.tickets — top general-signal desk-management tickets (no query filter)
       related[*] — five entries with relation="used_by"
       depends_on contributes nothing (empty)

  3. jira_search_cross_module(primary_module="employee-experience",
                              include_relations=["depends_on"])
     Expected:
       primary.tickets — top employee-experience tickets
       related = [] (employee-experience has empty depends_on; used_by excluded
                    by include_relations)

  4. jira_search_cross_module(primary_module="bogus-module")
     Expected: {"error": "module_not_found", "module": "bogus-module"}

  5. jira_search_cross_module(primary_module="meal-management",
                              type_bucket="bug")
     Expected:
       primary.tickets filtered to type_bucket=bug
       related[*].tickets each filtered to type_bucket=bug
       Each group's `pre_filter_count` shows how many were fetched before
       the type filter trimmed.
"""
from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

import frontmatter  # same library used by wiki_propose_tools + Step-5 wiki_retriever

from backend import jira_retriever
from backend.config import JIRA_DB


_LOG = logging.getLogger("jira_cross_module")

REPO = Path(__file__).resolve().parents[2]
WIKI_MODULES_DIR = REPO / "wiki" / "modules"


# ── Schema ────────────────────────────────────────────────────────────────────

JIRA_SEARCH_CROSS_MODULE_SCHEMA: dict = {
    "name": "jira_search_cross_module",
    "description": (
        "Retrieve Jira tickets for a primary module AND its related modules "
        "(via the wiki's depends_on / used_by graph). Use when a question is "
        "module-anchored but spans subsystems (e.g. 'why is meal check-in "
        "failing?' — meal-management depends on access-management + floor-kiosk; "
        "the answer likely needs tickets from all three). Returns primary + list "
        "of related modules, each with its top tickets. Optional query filter "
        "applies keyword search within each module. Optional type/status filters "
        "trim results post-fetch. PREFER calling jira_count for raw aggregation, "
        "and jira_search_ranked for non-module-anchored keyword search."
    ),
    "input_schema": {
        "type": "object",
        "required": ["primary_module"],
        "properties": {
            "primary_module": {
                "type": "string",
                "description": (
                    "Module slug, e.g. 'meal-management', 'meeting-rooms'. Must match "
                    "a file under wiki/modules/<slug>.md."
                ),
            },
            "query": {
                "type": "string",
                "description": (
                    "Optional keyword filter applied within each module (passed through "
                    "to jira_retriever.by_module). Strongly recommended for symptom-based "
                    "queries — without it, results are top general-signal tickets per module."
                ),
            },
            "include_relations": {
                "type": "array",
                "items": {"type": "string", "enum": ["depends_on", "used_by"]},
                "default": ["depends_on", "used_by"],
                "description": (
                    "Which relation edges to follow from primary_module's frontmatter. "
                    "Defaults to both. Empty array → primary only, no related modules."
                ),
            },
            "type_bucket": {
                "type": "string",
                "enum": ["task", "bug", "story", "epic", "other"],
                "description": "Post-filter results to this issue-type bucket.",
            },
            "status_bucket": {
                "type": "string",
                "enum": ["resolved", "in_progress", "open", "other"],
                "description": "Post-filter results to this status bucket.",
            },
            "limit_per_module": {
                "type": "integer",
                "default": 5,
                "minimum": 1,
                "maximum": 10,
                "description": (
                    "Max tickets to fetch per module (BEFORE post-filter). Default 5, "
                    "cap 10. With type/status filters, the post-filtered count may be lower."
                ),
            },
        },
    },
}


# ── DB ────────────────────────────────────────────────────────────────────────

def _open_ro() -> sqlite3.Connection:
    """Read-only SQLite handle. Same pattern as jira_count.py and jira_retriever.py."""
    uri = f"file:{JIRA_DB}?mode=ro&immutable=1"
    return sqlite3.connect(uri, uri=True, check_same_thread=False)


def _fetch_buckets_for_keys(conn, keys: list[str]) -> dict[str, dict]:
    """
    Batched lookup: one SELECT, returns
      {ticket_key: {"type_bucket": str|None, "status_bucket": str|None, ...}}

    Used to attach bucket fields to by_module rows so we can post-filter.
    Indexed by PRIMARY KEY (ticket_key) — fast.
    """
    if not keys:
        return {}
    placeholders = ",".join("?" for _ in keys)
    sql = (
        f"SELECT ticket_key, type_bucket, status_bucket, priority_bucket "
        f"FROM ticket_classifications "
        f"WHERE ticket_key IN ({placeholders})"
    )
    cur = conn.execute(sql, keys)
    out: dict[str, dict] = {}
    for ticket_key, type_b, status_b, priority_b in cur.fetchall():
        out[ticket_key] = {
            "type_bucket": type_b,
            "status_bucket": status_b,
            "priority_bucket": priority_b,
        }
    return out


# ── Handler ───────────────────────────────────────────────────────────────────

def _jira_search_cross_module_handler(inp: dict) -> dict:
    """See module docstring."""
    # ── 1. Validate primary_module ────────────────────────────────────────────
    primary_module = (inp.get("primary_module") or "").strip()
    if not primary_module:
        return {"error": "primary_module is required", "code": "missing_input"}

    page_path = WIKI_MODULES_DIR / f"{primary_module}.md"
    if not page_path.exists():
        return {
            "error": f"Module page not found: wiki/modules/{primary_module}.md",
            "code": "module_not_found",
            "module": primary_module,
        }

    # ── 2. Read frontmatter (depends_on + used_by) ────────────────────────────
    try:
        post = frontmatter.load(str(page_path))
        fm = post.metadata if isinstance(post.metadata, dict) else {}
    except Exception as exc:
        return {"error": f"Could not parse frontmatter: {exc}", "code": "frontmatter_error"}

    def _list_or_empty(v) -> list[str]:
        if isinstance(v, list):
            return [str(s).strip() for s in v if s]
        return []

    depends_on = _list_or_empty(fm.get("depends_on"))
    used_by    = _list_or_empty(fm.get("used_by"))

    # ── 3. Filter related slugs by include_relations ──────────────────────────
    include = inp.get("include_relations") or ["depends_on", "used_by"]
    if not isinstance(include, list):
        include = ["depends_on", "used_by"]
    include = [r for r in include if r in ("depends_on", "used_by")]

    related_slugs: list[tuple[str, str]] = []  # [(slug, relation_type), ...]
    seen_slugs = {primary_module}
    if "depends_on" in include:
        for slug in depends_on:
            if slug and slug not in seen_slugs:
                related_slugs.append((slug, "depends_on"))
                seen_slugs.add(slug)
    if "used_by" in include:
        for slug in used_by:
            if slug and slug not in seen_slugs:
                related_slugs.append((slug, "used_by"))
                seen_slugs.add(slug)

    # ── 4. Read remaining filter params ───────────────────────────────────────
    query = inp.get("query") or None
    type_bucket = (inp.get("type_bucket") or "").strip() or None
    status_bucket = (inp.get("status_bucket") or "").strip() or None
    try:
        limit_per_module = int(inp.get("limit_per_module", 5))
    except (TypeError, ValueError):
        return {"error": "limit_per_module must be an integer", "code": "invalid_input"}
    limit_per_module = max(1, min(10, limit_per_module))

    # Defensive enum checks
    if type_bucket and type_bucket not in {"task", "bug", "story", "epic", "other"}:
        return {"error": f"invalid type_bucket: {type_bucket!r}", "code": "invalid_input"}
    if status_bucket and status_bucket not in {"resolved", "in_progress", "open", "other"}:
        return {"error": f"invalid status_bucket: {status_bucket!r}", "code": "invalid_input"}

    # ── 5. Fetch primary tickets ──────────────────────────────────────────────
    primary_rows = jira_retriever.by_module(
        primary_module, query=query, limit=limit_per_module
    )

    # ── 6. Fetch related tickets ──────────────────────────────────────────────
    related_groups: list[dict] = []
    for slug, relation in related_slugs:
        rows = jira_retriever.by_module(slug, query=query, limit=limit_per_module)
        related_groups.append({
            "module": slug,
            "relation": relation,
            "_rows": rows,                  # mutated by filter step
            "_pre_count": len(rows),        # snapshot of pre-filter count
        })

    # ── 7. If type/status filters set, enrich rows with buckets + post-filter ─
    enrichment_warning: str | None = None
    if type_bucket or status_bucket:
        all_rows: list[dict] = list(primary_rows)
        for g in related_groups:
            all_rows.extend(g["_rows"])

        if all_rows:
            buckets_map: dict[str, dict] = {}
            try:
                conn = _open_ro()
                try:
                    buckets_map = _fetch_buckets_for_keys(
                        conn, [r["key"] for r in all_rows]
                    )
                finally:
                    conn.close()
            except sqlite3.Error as exc:
                # Silent → visible: tag the response so the agent knows
                # bucket-based filtering may have dropped legitimate matches.
                _LOG.warning(
                    "bucket enrichment failed during jira_search_cross_module: %s",
                    exc,
                )
                enrichment_warning = (
                    "bucket lookup failed; filter results may be incomplete"
                )

            for r in all_rows:
                b = buckets_map.get(r["key"], {})
                r["type_bucket"]      = b.get("type_bucket")
                r["status_bucket"]    = b.get("status_bucket")
                r["priority_bucket"]  = b.get("priority_bucket")

        # Capture pre-filter counts before trimming so the agent can detect
        # cases where the limit was hit pre-filter but most got trimmed.
        primary_pre_count = len(primary_rows)
        if type_bucket:
            primary_rows = [r for r in primary_rows if r.get("type_bucket") == type_bucket]
            for g in related_groups:
                g["_rows"] = [r for r in g["_rows"] if r.get("type_bucket") == type_bucket]
        if status_bucket:
            primary_rows = [r for r in primary_rows if r.get("status_bucket") == status_bucket]
            for g in related_groups:
                g["_rows"] = [r for r in g["_rows"] if r.get("status_bucket") == status_bucket]

        primary_post_count = len(primary_rows)
        primary_extra = {"pre_filter_count": primary_pre_count,
                         "post_filter_count": primary_post_count}
    else:
        primary_extra = {}

    # ── 8. Build response ─────────────────────────────────────────────────────
    response_primary = {
        "module": primary_module,
        "relation": "primary",
        "tickets": primary_rows,
    }
    response_primary.update(primary_extra)

    response_related: list[dict] = []
    for g in related_groups:
        item = {
            "module": g["module"],
            "relation": g["relation"],
            "tickets": g["_rows"],
        }
        if type_bucket or status_bucket:
            item["pre_filter_count"]  = g["_pre_count"]
            item["post_filter_count"] = len(g["_rows"])
        response_related.append(item)

    filters_applied: dict = {}
    if query:           filters_applied["query"] = query
    if type_bucket:     filters_applied["type_bucket"] = type_bucket
    if status_bucket:   filters_applied["status_bucket"] = status_bucket
    if include != ["depends_on", "used_by"]:
        filters_applied["include_relations"] = include
    if limit_per_module != 5:
        filters_applied["limit_per_module"] = limit_per_module

    result: dict = {
        "primary": response_primary,
        "related": response_related,
        "query_filtered": bool(query),
        "filters_applied": filters_applied,
        "total_modules_searched": 1 + len(related_groups),
    }
    if enrichment_warning is not None:
        result["enrichment_warning"] = enrichment_warning
    return result


# ── End of file ──────────────────────────────────────────────────────────────
#
# Edge cases this handler covers:
#   - primary_module missing                 → invalid_input error
#   - primary_module file not found          → module_not_found error
#   - primary_module frontmatter malformed   → frontmatter_error
#   - primary_module has no depends_on/used_by → related = []
#   - include_relations = []                 → primary only, related = []
#   - include_relations contains unknowns    → unknowns silently dropped
#   - limit_per_module out of range          → clamped to [1, 10]
#   - bucket filter removes all results      → empty tickets arrays, no error
#   - SQLite error during bucket enrichment  → caller still gets primary +
#       related ticket lists (unenriched rows pass through the filter as
#       "no bucket info" → would fail the filter equality and get dropped;
#       this is conservative behavior — surfacing the error explicitly might
#       be better. Tradeoff: handler reliability > strict consistency.)
#
# What this handler does NOT do (by design):
#   - Does NOT do depth > 1 traversal. One hop only per the plan.
#   - Does NOT respect _preflight_source / _preflight_relation_to tagging —
#     those are preflight conventions; this is an agent-initiated tool.
#   - Does NOT cache frontmatter reads across calls. Each call re-reads the
#     primary module's frontmatter (small cost; correctness > cache).
