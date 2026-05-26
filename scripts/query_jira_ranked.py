#!/usr/bin/env python3
"""
query_jira_ranked.py — Time-aware Jira evidence retrieval for the QUERY workflow.

Searches the Jira SQLite mirror for tickets matching a keyword, ranks them by
recency + status + content richness, and buckets them into:

    LATEST       — current behavior (≤180 days, or resolved with substantive content)
    HISTORICAL   — older context, may be stale
    STALE-OPEN   — open but no activity in >180 days (usually noise)

Outputs markdown ready to drop into the QUERY answer template defined in
CLAUDE.md Section 5.

Usage:
    python scripts/query_jira_ranked.py "<keyword>"
    python scripts/query_jira_ranked.py "createBookingIfNotPresent"
    python scripts/query_jira_ranked.py "RFID" --area WP-workflows
    python scripts/query_jira_ranked.py "SSO" --include-stale --limit 30
    python scripts/query_jira_ranked.py "wayfinding" --json
"""

import argparse
import json
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "raw" / "jira" / "tickets.sqlite"
RECENCY_DAYS = 180
SUBSTANTIVE_COMMENT_THRESHOLD = 2
SUBSTANTIVE_CONTENT_CHARS = 500


def fetch_ranked(conn, keyword, functional_area=None, limit=25):
    """
    Returns ranked, bucketed matches.

    Notes on date handling:
      Jira timestamps in this DB include a `+0530` tz offset (e.g.
      `2025-04-21T11:59:26.482+0530`). SQLite's `date()` function returns NULL
      for that format. We use `substr(_, 1, 10)` to extract the date prefix,
      and rely on ISO 8601 lexicographic comparison for thresholds.
    """
    sql = """
    WITH matches AS (
      SELECT key, status_category, priority, summary,
             description_text, comments_text,
             updated_at, resolved_at, comment_count,
             links_json,
             length(description_text) + length(coalesce(comments_text, '')) AS content_size,
             -- Date prefix (timezone-safe)
             substr(updated_at, 1, 10)  AS updated_date,
             substr(resolved_at, 1, 10) AS resolved_date,
             -- Direct hit in summary is the strongest signal
             CASE WHEN summary LIKE :kw_like COLLATE NOCASE THEN 1 ELSE 0 END AS hit_summary,
             CASE WHEN description_text LIKE :kw_like COLLATE NOCASE THEN 1 ELSE 0 END AS hit_desc
      FROM tickets
      WHERE (summary          LIKE :kw_like COLLATE NOCASE
          OR description_text LIKE :kw_like COLLATE NOCASE
          OR comments_text    LIKE :kw_like COLLATE NOCASE)
        {area_clause}
    )
    SELECT
      CASE
        -- LATEST = actual recent activity (updated OR resolved within window)
        WHEN updated_date  >= :cutoff_date THEN 'LATEST'
        WHEN resolved_date >= :cutoff_date THEN 'LATEST'
        -- STALE-OPEN = open ticket with no recent update (likely abandoned)
        WHEN status_category IN ('new', 'indeterminate')
             AND updated_date < :cutoff_date THEN 'STALE-OPEN'
        -- HISTORICAL = old closed ticket (describes past behavior)
        ELSE 'HISTORICAL'
      END AS bucket,
      key, status_category, priority,
      updated_date  AS updated,
      resolved_date AS resolved,
      comment_count, content_size,
      hit_summary, hit_desc,
      links_json,
      summary
    FROM matches
    ORDER BY
      -- Bucket order: Latest > Historical > Stale-open
      CASE
        WHEN updated_date  >= :cutoff_date THEN 0
        WHEN resolved_date >= :cutoff_date THEN 0
        WHEN status_category IN ('new', 'indeterminate')
             AND updated_date < :cutoff_date THEN 2
        ELSE 1
      END,
      -- Direct summary hit ranks above content-only hit
      hit_summary DESC,
      hit_desc DESC,
      -- Resolved with content > resolved without > open
      CASE WHEN status_category = 'done' AND resolved_at IS NOT NULL THEN 0 ELSE 1 END,
      -- Recency
      updated_date DESC,
      -- Richer ticket breaks ties
      content_size DESC
    LIMIT :limit
    """
    area_clause = ""
    params = {
        "kw_like": f"%{keyword}%",
        "limit": limit,
    }
    # Compute cutoff date in Python for portability (avoids SQLite's date() limitations)
    from datetime import datetime, timedelta, timezone
    cutoff = (datetime.now(timezone.utc) - timedelta(days=RECENCY_DAYS)).date().isoformat()
    params["cutoff_date"] = cutoff

    if functional_area:
        area_clause = "AND functional_area = :area"
        params["area"] = functional_area
    sql = sql.format(area_clause=area_clause)

    cur = conn.execute(sql, params)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def linked_keys(links_json):
    """Extract linked ticket keys for evolution detection."""
    if not links_json:
        return []
    try:
        links = json.loads(links_json)
    except (json.JSONDecodeError, TypeError):
        return []
    out = []
    for link in links:
        for direction in ("outward", "inward"):
            key = link.get(direction)
            ltype = link.get("type", "")
            if key:
                out.append((ltype, direction, key))
    return out


def format_ticket_line(row, base_url="https://moveinsync.atlassian.net/browse/"):
    parts = [f"`{row['key']}`"]
    parts.append(f"status:`{row['status_category']}`")
    parts.append(f"priority:`{row['priority'] or '—'}`")
    if row["resolved"]:
        parts.append(f"resolved {row['resolved']}")
    parts.append(f"updated {row['updated']}")
    parts.append(f"💬{row['comment_count']}")
    if row.get("hit_summary"):
        parts.append("[summary-hit]")
    meta = " · ".join(parts)
    summary = (row["summary"] or "")[:120].replace("\n", " ")
    return f"- {meta}\n    > {summary}"


def render_markdown(keyword, rows, area=None, include_stale=False):
    buckets = {"LATEST": [], "HISTORICAL": [], "STALE-OPEN": []}
    for r in rows:
        buckets[r["bucket"]].append(r)

    out = []
    header_bits = [f"`{keyword}`"]
    if area:
        header_bits.append(f"area=`{area}`")
    out.append(f"### Ranked Jira evidence for {' · '.join(header_bits)}")
    out.append(
        f"_Buckets: LATEST={len(buckets['LATEST'])} · "
        f"HISTORICAL={len(buckets['HISTORICAL'])} · "
        f"STALE-OPEN={len(buckets['STALE-OPEN'])} "
        f"(recency window: {RECENCY_DAYS}d)_"
    )
    out.append("")

    # Latest
    out.append("**Latest evidence** (current behavior, last ~6 months):")
    if buckets["LATEST"]:
        for r in buckets["LATEST"]:
            out.append(format_ticket_line(r))
    else:
        out.append("- —")
    out.append("")

    # Historical
    out.append("**Historical evidence** (older context, may be stale):")
    if buckets["HISTORICAL"]:
        for r in buckets["HISTORICAL"]:
            out.append(format_ticket_line(r))
    else:
        out.append("- —")
    out.append("")

    # Stale-open (only if requested)
    if include_stale:
        out.append("**Stale-open** (open but no activity >180 days — usually noise):")
        if buckets["STALE-OPEN"]:
            for r in buckets["STALE-OPEN"]:
                out.append(format_ticket_line(r))
        else:
            out.append("- —")
        out.append("")

    # Evolution hints — any latest tickets with links to older ones?
    evolution = []
    for r in buckets["LATEST"]:
        links = linked_keys(r["links_json"])
        if links:
            link_str = ", ".join(f"{lt} → `{k}`" for lt, _, k in links[:5])
            evolution.append(f"- `{r['key']}` links: {link_str}")
    if evolution:
        out.append("**Linked-issue evolution** (check for supersedes/blocks/duplicates):")
        out.extend(evolution)
        out.append("")

    # Confidence hint
    latest_n = len(buckets["LATEST"])
    historical_n = len(buckets["HISTORICAL"])
    if latest_n >= 2:
        conf = "High — 2+ latest tickets available"
    elif latest_n == 1 and historical_n == 0:
        conf = "Medium — single latest ticket, no conflict"
    elif latest_n == 1 and historical_n >= 1:
        conf = "Medium — latest + historical present; check for conflict"
    elif latest_n == 0 and historical_n >= 1:
        conf = "Low — only historical evidence; may be stale"
    else:
        conf = "Low — no Jira evidence; rely on wiki + runtime"
    out.append(f"**Suggested confidence:** {conf}")

    return "\n".join(out)


def main():
    parser = argparse.ArgumentParser(
        description="Time-aware Jira evidence retrieval. Buckets matches into Latest / "
        "Historical / Stale-open per CLAUDE.md Section 5."
    )
    parser.add_argument("keyword", help="Keyword or property name to search for")
    parser.add_argument(
        "--area",
        dest="functional_area",
        help="Restrict to a Jira functional_area (e.g. WF-empexp, WP-workflows)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=25,
        help="Max rows to fetch (default: 25)",
    )
    parser.add_argument(
        "--include-stale",
        action="store_true",
        help="Include the STALE-OPEN bucket in output (default: hidden)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON instead of markdown",
    )
    args = parser.parse_args()

    if not DB_PATH.exists():
        print(f"ERROR: SQLite DB not found at {DB_PATH}", file=sys.stderr)
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    try:
        rows = fetch_ranked(conn, args.keyword, args.functional_area, args.limit)
    finally:
        conn.close()

    if not rows:
        if args.json:
            print(json.dumps({"keyword": args.keyword, "rows": []}))
        else:
            print(f"No Jira tickets matched `{args.keyword}`"
                  + (f" in area `{args.functional_area}`" if args.functional_area else "")
                  + ".")
        return

    if args.json:
        print(json.dumps({"keyword": args.keyword, "rows": rows}, indent=2, default=str))
    else:
        print(render_markdown(args.keyword, rows, args.functional_area, args.include_stale))


if __name__ == "__main__":
    main()
