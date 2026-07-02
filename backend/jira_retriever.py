"""
Jira retriever — wraps fetch_ranked() from scripts/query_jira_ranked.py.

Opens the SQLite DB read-only (safe for concurrent backend access).
Extracts a search keyword from the user's free-text question.
"""
from __future__ import annotations

import os
import random
import re
import sys
import time
from pathlib import Path

# Make scripts/ importable without installing as a package
_SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from query_jira_ranked import fetch_ranked, render_markdown  # noqa: E402

from backend import db
from backend.retrieval.v2 import shadow as _shadow_mod

# Common English stop-words to strip before keyword extraction
_STOPWORDS = {
    "a", "an", "the", "is", "in", "on", "at", "to", "for", "of", "and",
    "or", "not", "with", "what", "how", "why", "when", "where", "which",
    "does", "do", "can", "will", "should", "would", "could", "has", "have",
    "this", "that", "it", "be", "are", "was", "were", "by", "from",
}


# Read access goes through the shared Postgres pool (backend.db.connection()).
# The old _open_readonly() SQLite helper is gone; tickets live in Postgres now.


# ── v2 dispatch ───────────────────────────────────────────────────────────────

def _date_str(value) -> str | None:
    """Format a datetime (or datetime-like) value as YYYY-MM-DD; falsy input -> None."""
    if not value:
        return None
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d")
    return str(value)[:10]


# Maps the lowercase per-ticket `bucket` tag that timeline.apply_timeline()
# attaches (inside hybrid_search(), upstream of gate.apply()) to the
# uppercase top-level bucket key that preflight.format_jira_buckets_for_seed()
# reads from.
_BUCKET_TOP_KEY = {"latest": "LATEST", "historical": "HISTORICAL", "stale_open": "STALE-OPEN"}


def _v2_search(question: str, *, functional_area: str | None = None,
               limit: int = 10, **kwargs):
    # kwargs (e.g. include_stale, trace_id) are v1-only and intentionally not
    # passed to the v2 pipeline yet. Callers (e.g. jira_tools.py) may pass
    # include_stale=True; v2 always returns all recency buckets via its own
    # reranker, so the flag has no v2 equivalent. This is a known behaviour
    # delta — callers should expect it when CONWO_RETRIEVAL_V2 flips to 'on'.
    from backend.retrieval.v2.pipeline import search as _p
    result = _p(question, functional_area=functional_area, limit=limit)
    tickets = result.tickets  # list[dict] with reranker_score

    # Normalise field names to match v1's dict shape so preflight.py,
    # PreflightBundle, and build_seed_message work without modification.
    # v2 hybrid SQL returns `updated_at`/`resolved_at` as real datetime objects
    # (psycopg maps timestamptz -> datetime); v1 formatters expect `updated`/
    # `resolved` as date-only strings, so we go through _date_str() rather
    # than naive string slicing. Each ticket also already carries a lowercase
    # `bucket` tag (latest/historical/stale_open) set by timeline.apply_timeline()
    # upstream — route each ticket into the matching uppercase top-level bucket
    # that preflight.format_jira_buckets_for_seed() reads from, instead of
    # dumping every ticket into LATEST regardless of its actual tag.
    buckets: dict[str, list[dict]] = {"LATEST": [], "HISTORICAL": [], "STALE-OPEN": []}
    for t in tickets:
        if "updated" not in t:
            t["updated"] = _date_str(t.get("updated_at")) or "?"
        if "resolved" not in t:
            t["resolved"] = _date_str(t.get("resolved_at"))
        bucket_val = t.get("bucket") or "latest"
        t["bucket"] = bucket_val
        top_key = _BUCKET_TOP_KEY.get(bucket_val, "LATEST")
        buckets[top_key].append(t)

    return {
        "keywords": extract_keywords(question),
        "markdown": result.message,
        "rows": tickets,
        "buckets": buckets,
    }


def _v2_by_module(module_slug: str, query: str, limit: int = 5, **kwargs):
    from backend.retrieval.v2.pipeline import by_module as _bm
    return _bm(module_slug, query, limit=limit)


_shadow_log = _shadow_mod.log  # test seam


def _mode() -> str:
    return (os.getenv("CONWO_RETRIEVAL_V2") or "off").lower()


def _ab_serve_v2() -> bool:
    try:
        pct = int(os.getenv("CONWO_RETRIEVAL_V2_PCT", "0"))
    except ValueError:
        pct = 0
    return random.randint(1, 100) <= pct


def search(question: str, *, functional_area: str | None = None,
           limit: int = 10, **kwargs):
    mode = _mode()
    if mode == "off":
        return _v1_search(question, functional_area=functional_area, limit=limit, **kwargs)
    if mode == "on":
        return _v2_search(question, functional_area=functional_area, limit=limit, **kwargs)
    if mode == "ab":
        if _ab_serve_v2():
            return _v2_search(question, functional_area=functional_area, limit=limit, **kwargs)
        return _v1_search(question, functional_area=functional_area, limit=limit, **kwargs)
    # shadow: serve v1, run v2 alongside, log both
    v1_result = _v1_search(question, functional_area=functional_area, limit=limit, **kwargs)
    t0 = time.perf_counter()
    try:
        v2_result = _v2_search(question, functional_area=functional_area, limit=limit, **kwargs)
        dt = int((time.perf_counter() - t0) * 1000)
        v1_keys = _extract_v1_keys(v1_result)
        _shadow_log(trace_id=kwargs.get("trace_id"), question=question,
                    v1_keys=v1_keys, v2_result=v2_result,
                    v2_latency_ms=dt, served_v2=False)
    except Exception:
        pass
    return v1_result


def by_module(module_slug: str, query: str, limit: int = 5, **kwargs):
    mode = _mode()
    if mode == "off":
        return _v1_by_module(module_slug, query, limit=limit, **kwargs)
    if mode == "on":
        return _v2_by_module(module_slug, query, limit=limit, **kwargs)
    if mode == "ab" and _ab_serve_v2():
        return _v2_by_module(module_slug, query, limit=limit, **kwargs)
    return _v1_by_module(module_slug, query, limit=limit, **kwargs)


def _extract_v1_keys(v1_result) -> list[str]:
    """Best-effort extraction of ticket keys from a v1 retrieval result."""
    if v1_result is None:
        return []
    rows = getattr(v1_result, "rows", None) or getattr(v1_result, "results", None) or v1_result
    out = []
    try:
        for r in rows:
            if isinstance(r, dict) and "key" in r:
                out.append(r["key"])
    except Exception:
        pass
    return out


# ─────────────────────────────────────────────────────────────────────────────

def extract_keywords(question: str, max_terms: int = 3) -> list[str]:
    """
    Extract 1–3 meaningful search terms from a free-text question.

    Returns a list ordered from most-specific (full camelCase property names,
    quoted strings) to most-general (plain words).
    """
    # Quoted strings are most explicit
    quoted = re.findall(r'"([^"]+)"', question)

    # Full camelCase tokens (the whole word, e.g. kioskRequireOTPBeforeRegister)
    # A camelCase word contains at least one internal uppercase letter
    all_tokens = re.findall(r"\b[a-zA-Z][a-zA-Z0-9]+\b", question)
    camel = [t for t in all_tokens if re.search(r"[a-z][A-Z]", t) or re.search(r"[A-Z]{2,}", t)]

    # Remaining meaningful tokens (>3 chars, not a stopword)
    plain = [t.lower() for t in all_tokens if t.lower() not in _STOPWORDS and len(t) > 3]

    # Build deduplicated ordered list: quoted → camel → plain
    seen: set[str] = set()
    result: list[str] = []
    for term in quoted + camel + plain:
        key = term.lower()
        if key not in seen:
            seen.add(key)
            result.append(term)
        if len(result) >= max_terms:
            break

    return result or plain[:1] or [question[:40]]


def _v1_search(
    question: str,
    functional_area: str | None = None,
    module: str | None = None,
    limit: int = 25,
    include_stale: bool = False,
    **kwargs,
) -> dict:
    """
    Run ranked Jira search for a question. Returns a dict with:
      - keywords: list of terms searched
      - markdown: formatted evidence string (ready for system prompt)
      - rows: raw row dicts from fetch_ranked()
      - buckets: {"LATEST": [...], "HISTORICAL": [...], "STALE-OPEN": [...]}
    """
    keywords = extract_keywords(question)
    if not keywords:
        return {
            "keywords": [],
            "markdown": "No Jira search performed — no meaningful keywords found.",
            "rows": [],
            "buckets": {"LATEST": [], "HISTORICAL": [], "STALE-OPEN": []},
        }

    with db.connection() as conn:
        # Search with the best keyword; merge if multiple terms
        all_rows: list[dict] = []
        seen_keys: set[str] = set()
        for kw in keywords:
            rows = fetch_ranked(conn, kw, functional_area, limit)
            for r in rows:
                if r["key"] not in seen_keys:
                    seen_keys.add(r["key"])
                    all_rows.append(r)

        # Module post-filter — when set, drop rows for keys not tagged to this module.
        # confidence_floor=0.5 matches the read-path convention; classifier writes ≥0.65.
        if module:
            module_keys = _fetch_module_tagged_keys(conn, module, confidence_floor=0.5)
            all_rows = [r for r in all_rows if r["key"] in module_keys]

        # Batched modules-array enrichment — one query, indexed PK, no N+1.
        if all_rows:
            modules_map = _fetch_modules_for_keys(
                conn, [r["key"] for r in all_rows], confidence_floor=0.5
            )
            for r in all_rows:
                r["modules"] = modules_map.get(r["key"], [])

    # Re-sort merged rows by bucket order then recency (fetch_ranked already sorts,
    # but merging across keywords can shuffle)
    bucket_order = {"LATEST": 0, "HISTORICAL": 1, "STALE-OPEN": 2}
    all_rows.sort(key=lambda r: (bucket_order.get(r["bucket"], 3), -r.get("content_size", 0)))

    buckets: dict[str, list] = {"LATEST": [], "HISTORICAL": [], "STALE-OPEN": []}
    for r in all_rows:
        buckets[r["bucket"]].append(r)

    primary_kw = keywords[0]
    markdown = render_markdown(primary_kw, all_rows, functional_area, include_stale)

    return {
        "keywords": keywords,
        "markdown": markdown,
        "rows": all_rows,
        "buckets": buckets,
    }


# ── Module-tag helpers (Step 4 additions) ─────────────────────────────────────

def _fetch_module_tagged_keys(
    conn,
    module_slug: str,
    confidence_floor: float = 0.5,
) -> set[str]:
    """Set of ticket keys tagged to `module_slug` at or above `confidence_floor`."""
    cur = conn.execute(
        "SELECT ticket_key FROM ticket_module_tags "
        "WHERE module_slug = %s AND confidence >= %s",
        (module_slug, confidence_floor),
    )
    return {row[0] for row in cur.fetchall()}


def _fetch_modules_for_keys(
    conn,
    keys: list[str],
    confidence_floor: float = 0.5,
) -> dict[str, list[dict]]:
    """
    Batched lookup of modules array for many ticket keys.
    Returns {ticket_key: [{"slug": str, "confidence": float}, ...]}.
    Tickets with no tagged modules are absent from the dict (caller defaults to []).
    """
    if not keys:
        return {}
    placeholders = ",".join("%s" for _ in keys)
    sql = (
        "SELECT ticket_key, module_slug, confidence "
        "FROM ticket_module_tags "
        f"WHERE ticket_key IN ({placeholders}) AND confidence >= %s "
        "ORDER BY ticket_key, confidence DESC"
    )
    params = list(keys) + [confidence_floor]
    cur = conn.execute(sql, params)
    out: dict[str, list[dict]] = {}
    for ticket_key, module_slug, confidence in cur.fetchall():
        out.setdefault(ticket_key, []).append({"slug": module_slug, "confidence": confidence})
    return out


def _v1_by_module(
    module_slug: str,
    query: str | None = None,
    limit: int = 5,
    confidence_floor: float = 0.5,
    **kwargs,
) -> list[dict]:
    """
    Query-aware retrieval scoped to a single module.

    If `query` has extractable keywords: returns intersection of
    (module-tagged) ∩ (query-relevant), mirroring fetch_ranked's bucket
    semantics. If `query` is None or yields no keywords: returns top
    general-signal tickets in the module.

    Rows are enriched with the `modules` array for cross-module attribution
    (same enrichment search() does).
    """
    keywords = extract_keywords(query) if query else []
    with db.connection() as conn:
        if keywords:
            rows = _fetch_module_query_intersection(
                conn, module_slug, keywords, limit, confidence_floor
            )
        else:
            rows = _fetch_module_top(conn, module_slug, limit, confidence_floor)

        # Enrich both paths with modules array (Step 4 amendment).
        if rows:
            modules_map = _fetch_modules_for_keys(
                conn, [r["key"] for r in rows], confidence_floor=0.5
            )
            for r in rows:
                r["modules"] = modules_map.get(r["key"], [])
        return rows


def _fetch_module_query_intersection(
    conn,
    module_slug: str,
    keywords: list[str],
    limit: int,
    confidence_floor: float,
) -> list[dict]:
    """Intersection of: tickets tagged to module AND matching any keyword.
    Bucket/ordering mirrors fetch_ranked()'s WITH matches CTE."""
    from datetime import datetime, timedelta, timezone
    cutoff = (datetime.now(timezone.utc) - timedelta(days=180)).date().isoformat()

    kw_filters: list[str] = []
    kw_params: dict = {
        "module_slug": module_slug,
        "conf_floor": confidence_floor,
        "cutoff_date": cutoff,
        "limit": limit,
    }
    for i, kw in enumerate(keywords):
        kw_params[f"kw{i}"] = f"%{kw}%"
        kw_filters.append(
            f"(t.summary ILIKE %(kw{i})s "
            f"OR t.description_text ILIKE %(kw{i})s "
            f"OR t.comments_text ILIKE %(kw{i})s)"
        )
    kw_where = " OR ".join(kw_filters)

    sql = f"""
        SELECT
          CASE
            WHEN substr(t.updated_at, 1, 10) >= %(cutoff_date)s
              OR substr(t.resolved_at, 1, 10) >= %(cutoff_date)s THEN 'LATEST'
            WHEN t.status_category IN ('new', 'indeterminate')
              AND substr(t.updated_at, 1, 10) < %(cutoff_date)s THEN 'STALE-OPEN'
            ELSE 'HISTORICAL'
          END AS bucket,
          t.key, t.status_category, t.priority,
          substr(t.updated_at, 1, 10)  AS updated,
          substr(t.resolved_at, 1, 10) AS resolved,
          t.comment_count,
          COALESCE(length(t.description_text), 0)
            + COALESCE(length(t.comments_text), 0) AS content_size,
          CASE WHEN t.summary ILIKE %(kw0)s THEN 1 ELSE 0 END AS hit_summary,
          CASE WHEN t.description_text ILIKE %(kw0)s THEN 1 ELSE 0 END AS hit_desc,
          t.links_json,
          t.summary,
          m.confidence AS module_confidence
        FROM tickets t
        JOIN ticket_module_tags m ON t.key = m.ticket_key
        WHERE m.module_slug = %(module_slug)s
          AND m.confidence  >= %(conf_floor)s
          AND ({kw_where})
        ORDER BY
          CASE
            WHEN substr(t.updated_at, 1, 10) >= %(cutoff_date)s
              OR substr(t.resolved_at, 1, 10) >= %(cutoff_date)s THEN 0
            WHEN t.status_category IN ('new', 'indeterminate')
              AND substr(t.updated_at, 1, 10) < %(cutoff_date)s THEN 2
            ELSE 1
          END,
          hit_summary DESC,
          hit_desc DESC,
          CASE WHEN t.status_category = 'done' AND t.resolved_at IS NOT NULL THEN 0 ELSE 1 END,
          updated DESC,
          content_size DESC
        LIMIT %(limit)s
    """
    cur = conn.execute(sql, kw_params)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def _fetch_module_top(
    conn,
    module_slug: str,
    limit: int,
    confidence_floor: float,
) -> list[dict]:
    """No-keyword path: top tickets in module by bucket + confidence + recency."""
    from datetime import datetime, timedelta, timezone
    cutoff = (datetime.now(timezone.utc) - timedelta(days=180)).date().isoformat()

    sql = """
        SELECT
          CASE
            WHEN substr(t.updated_at, 1, 10) >= %(cutoff_date)s
              OR substr(t.resolved_at, 1, 10) >= %(cutoff_date)s THEN 'LATEST'
            WHEN t.status_category IN ('new', 'indeterminate')
              AND substr(t.updated_at, 1, 10) < %(cutoff_date)s THEN 'STALE-OPEN'
            ELSE 'HISTORICAL'
          END AS bucket,
          t.key, t.status_category, t.priority,
          substr(t.updated_at, 1, 10)  AS updated,
          substr(t.resolved_at, 1, 10) AS resolved,
          t.comment_count,
          COALESCE(length(t.description_text), 0)
            + COALESCE(length(t.comments_text), 0) AS content_size,
          t.links_json,
          t.summary,
          m.confidence AS module_confidence
        FROM tickets t
        JOIN ticket_module_tags m ON t.key = m.ticket_key
        WHERE m.module_slug = %(module_slug)s
          AND m.confidence  >= %(conf_floor)s
        ORDER BY
          CASE
            WHEN substr(t.updated_at, 1, 10) >= %(cutoff_date)s
              OR substr(t.resolved_at, 1, 10) >= %(cutoff_date)s THEN 0
            ELSE 1
          END,
          m.confidence DESC,
          content_size DESC,
          updated DESC
        LIMIT %(limit)s
    """
    cur = conn.execute(
        sql,
        {"module_slug": module_slug, "conf_floor": confidence_floor,
         "cutoff_date": cutoff, "limit": limit},
    )
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]
