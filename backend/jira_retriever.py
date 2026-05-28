"""
Jira retriever — wraps fetch_ranked() from scripts/query_jira_ranked.py.

Opens the SQLite DB read-only (safe for concurrent backend access).
Extracts a search keyword from the user's free-text question.
"""
from __future__ import annotations

import re
import sqlite3
import sys
from pathlib import Path

# Make scripts/ importable without installing as a package
_SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from query_jira_ranked import fetch_ranked, render_markdown  # noqa: E402

from backend.config import JIRA_DB

# Common English stop-words to strip before keyword extraction
_STOPWORDS = {
    "a", "an", "the", "is", "in", "on", "at", "to", "for", "of", "and",
    "or", "not", "with", "what", "how", "why", "when", "where", "which",
    "does", "do", "can", "will", "should", "would", "could", "has", "have",
    "this", "that", "it", "be", "are", "was", "were", "by", "from",
}


def _open_readonly() -> sqlite3.Connection:
    if not JIRA_DB.exists():
        raise FileNotFoundError(f"Jira SQLite DB not found: {JIRA_DB}")
    # mode=ro prevents accidental writes; immutable=1 skips WAL lock acquisition
    uri = f"file:{JIRA_DB}?mode=ro&immutable=1"
    return sqlite3.connect(uri, uri=True, check_same_thread=False)


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


def search(
    question: str,
    functional_area: str | None = None,
    module: str | None = None,
    limit: int = 25,
    include_stale: bool = False,
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

    conn = _open_readonly()
    try:
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
    finally:
        conn.close()

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
        "WHERE module_slug = ? AND confidence >= ?",
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
    placeholders = ",".join("?" for _ in keys)
    sql = (
        "SELECT ticket_key, module_slug, confidence "
        "FROM ticket_module_tags "
        f"WHERE ticket_key IN ({placeholders}) AND confidence >= ? "
        "ORDER BY ticket_key, confidence DESC"
    )
    params = list(keys) + [confidence_floor]
    cur = conn.execute(sql, params)
    out: dict[str, list[dict]] = {}
    for ticket_key, module_slug, confidence in cur.fetchall():
        out.setdefault(ticket_key, []).append({"slug": module_slug, "confidence": confidence})
    return out


def by_module(
    module_slug: str,
    query: str | None = None,
    limit: int = 5,
    confidence_floor: float = 0.5,
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
    conn = _open_readonly()
    try:
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
    finally:
        conn.close()


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
            f"(t.summary LIKE :kw{i} COLLATE NOCASE "
            f"OR t.description_text LIKE :kw{i} COLLATE NOCASE "
            f"OR t.comments_text LIKE :kw{i} COLLATE NOCASE)"
        )
    kw_where = " OR ".join(kw_filters)

    sql = f"""
        SELECT
          CASE
            WHEN substr(t.updated_at, 1, 10) >= :cutoff_date
              OR substr(t.resolved_at, 1, 10) >= :cutoff_date THEN 'LATEST'
            WHEN t.status_category IN ('new', 'indeterminate')
              AND substr(t.updated_at, 1, 10) < :cutoff_date THEN 'STALE-OPEN'
            ELSE 'HISTORICAL'
          END AS bucket,
          t.key, t.status_category, t.priority,
          substr(t.updated_at, 1, 10)  AS updated,
          substr(t.resolved_at, 1, 10) AS resolved,
          t.comment_count,
          COALESCE(length(t.description_text), 0)
            + COALESCE(length(t.comments_text), 0) AS content_size,
          CASE WHEN t.summary LIKE :kw0 COLLATE NOCASE THEN 1 ELSE 0 END AS hit_summary,
          CASE WHEN t.description_text LIKE :kw0 COLLATE NOCASE THEN 1 ELSE 0 END AS hit_desc,
          t.links_json,
          t.summary,
          m.confidence AS module_confidence
        FROM tickets t
        JOIN ticket_module_tags m ON t.key = m.ticket_key
        WHERE m.module_slug = :module_slug
          AND m.confidence  >= :conf_floor
          AND ({kw_where})
        ORDER BY
          CASE
            WHEN substr(t.updated_at, 1, 10) >= :cutoff_date
              OR substr(t.resolved_at, 1, 10) >= :cutoff_date THEN 0
            WHEN t.status_category IN ('new', 'indeterminate')
              AND substr(t.updated_at, 1, 10) < :cutoff_date THEN 2
            ELSE 1
          END,
          hit_summary DESC,
          hit_desc DESC,
          CASE WHEN t.status_category = 'done' AND t.resolved_at IS NOT NULL THEN 0 ELSE 1 END,
          updated DESC,
          content_size DESC
        LIMIT :limit
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
            WHEN substr(t.updated_at, 1, 10) >= :cutoff_date
              OR substr(t.resolved_at, 1, 10) >= :cutoff_date THEN 'LATEST'
            WHEN t.status_category IN ('new', 'indeterminate')
              AND substr(t.updated_at, 1, 10) < :cutoff_date THEN 'STALE-OPEN'
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
        WHERE m.module_slug = :module_slug
          AND m.confidence  >= :conf_floor
        ORDER BY
          CASE
            WHEN substr(t.updated_at, 1, 10) >= :cutoff_date
              OR substr(t.resolved_at, 1, 10) >= :cutoff_date THEN 0
            ELSE 1
          END,
          m.confidence DESC,
          content_size DESC,
          updated DESC
        LIMIT :limit
    """
    cur = conn.execute(
        sql,
        {"module_slug": module_slug, "conf_floor": confidence_floor,
         "cutoff_date": cutoff, "limit": limit},
    )
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]
