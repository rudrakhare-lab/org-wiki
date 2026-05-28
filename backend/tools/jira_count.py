"""
STEP 6 DRAFT — backend/tools/jira_count.py (new file).

Closes G-NEW-43: API mode previously could not answer "how many tickets" questions
because jira_search_ranked returns bucketed/truncated lists and the model can't
aggregate accurately across pages. This tool returns exact counts + priority and
status breakdowns from the SQLite mirror.

==============================================================================
CARRIED-FORWARD CORRECTIONS (the corrected enums, not the original plan's)
==============================================================================

  type_bucket:     task | bug | story | epic | other            (NO feature/pb/spike)
  status_bucket:   resolved | in_progress | open | other        (derived from status_category)
  priority_bucket: p0 | p1 | p3 | other                         (NO p2 — not in data)

==============================================================================
CRITICAL DATE-HANDLING NOTE — DO NOT REGRESS
==============================================================================

  tickets.updated_at and tickets.resolved_at are ISO 8601 strings WITH a
  '+0530' timezone suffix (e.g. '2026-05-26T01:52:37.511+0530'). SQLite's
  built-in datetime() function does NOT recognize the +HHMM offset and
  returns NULL for every row. Using `datetime(t.updated_at) >= datetime('now', '-7 days')`
  in a WHERE clause silently filters out EVERY row — producing 0-count answers
  that look legitimate.

  This bug was caught during Step 2 validation when the original Test 2 anchor
  ('substr <= datetime(now,-7d)' variant) returned 0 against ~72 known matches.
  The fix below uses string-prefix comparison on substr(<col>, 1, 10) — works
  because ISO 8601 sorts lexicographically.

  IF YOU EVER edit this file, do not change the date-comparison expressions to
  datetime() without first confirming the timezone-suffix issue has been fixed
  upstream (i.e. updated_at no longer stores the +HHMM suffix).

==============================================================================
TEST CASES (for Step 9 verification)
==============================================================================

  1. jira_count(module="meal-management", type_bucket="bug")
       → exact count of meal-management bugs

  2. jira_count(functional_area="WP-admin", priority_bucket="p0",
                updated_within_days=7)

     For Step 9 verification, the test query is:
       jira_count(functional_area='WP-admin',
                  priority_bucket='p0',
                  updated_within_days=7)

     The expected count DRIFTS with the current date — running today the
     7-day window evaluates relative to date('now'), and the data window
     is bounded by the mirror's last-sync timestamp. For reproducible
     verification, manually compare the tool result against the pinned
     2026-05-19 anchor (expected: 72) by running the equivalent SQL with
     substr(updated_at,1,10) >= '<reference-date>' directly:

       sqlite3 raw/jira/tickets.sqlite "
         SELECT COUNT(*) FROM tickets
         WHERE functional_area='WP-admin'
           AND priority='P0'
           AND substr(updated_at,1,10) >= '2026-05-19';"
       -- expected: 72

     When running Step 9 on a future date, anchor the expected value by
     running this pinned-date SQL with a chosen reference-date and compare
     the tool's output to the SQL's output (they should match for an
     equivalent window).

  3. jira_count(status_bucket="open", priority_bucket="p0")
       → all currently-open P0s across the system

  4. jira_count()  -- no filters
       → 37,267 (total tickets — explicit, never silent)

  5. jira_count(updated_within_days=999)
       → returns error (out-of-range; schema cap is 365)
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone

from backend.config import JIRA_DB


# ── Schema ────────────────────────────────────────────────────────────────────

JIRA_COUNT_SCHEMA: dict = {
    "name": "jira_count",
    "description": (
        "Return the EXACT count of Jira tickets matching a combination of filters, "
        "plus distributions by priority and status. Use this tool for any 'how many', "
        "'total', 'count', or aggregation question — DO NOT estimate from "
        "jira_search_ranked results, which return only bucketed truncated lists. "
        "All filters are optional and AND together. Date filters look back N days "
        "from 'now' against the local mirror; the answer is therefore as fresh as "
        "the last Jira sync."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "module": {
                "type": "string",
                "description": (
                    "Filter to tickets tagged to this module (e.g. 'meal-management', "
                    "'meeting-rooms'). Uses ticket_module_tags with confidence >= 0.5."
                ),
            },
            "functional_area": {
                "type": "string",
                "description": (
                    "Filter by Jira functional_area (e.g. 'WF-empexp', 'WP-admin', "
                    "'WF-wis-meeting-vms'). Direct equality on tickets.functional_area."
                ),
            },
            "type_bucket": {
                "type": "string",
                "enum": ["task", "bug", "story", "epic", "other"],
                "description": (
                    "Issue-type bucket. task = Task+Sub-task, bug = Bug, story = Story, "
                    "epic = Epic, other = Request/Data Fix/Issue/Data Request."
                ),
            },
            "status_bucket": {
                "type": "string",
                "enum": ["resolved", "in_progress", "open", "other"],
                "description": (
                    "Status bucket. Derived from status_category: "
                    "resolved = done, in_progress = indeterminate, open = new, "
                    "other = undefined."
                ),
            },
            "priority_bucket": {
                "type": "string",
                "enum": ["p0", "p1", "p3", "other"],
                "description": (
                    "Priority bucket. p0/p1/p3 mirror Jira priority values (this Jira "
                    "instance does NOT use P2). other catches unset/unknown."
                ),
            },
            "updated_within_days": {
                "type": "integer",
                "minimum": 1,
                "maximum": 365,
                "description": (
                    "Restrict to tickets with substr(updated_at,1,10) >= date('now', '-N days'). "
                    "Useful for 'tickets updated in last week' style queries."
                ),
            },
            "resolved_within_days": {
                "type": "integer",
                "minimum": 1,
                "maximum": 365,
                "description": (
                    "Restrict to tickets with substr(resolved_at,1,10) >= date('now', '-N days'). "
                    "Useful for 'tickets resolved in last quarter' style queries."
                ),
            },
        },
    },
}


# ── DB ────────────────────────────────────────────────────────────────────────

def _open_ro() -> sqlite3.Connection:
    """Open the Jira SQLite read-only. Mirrors jira_retriever._open_readonly."""
    uri = f"file:{JIRA_DB}?mode=ro&immutable=1"
    return sqlite3.connect(uri, uri=True, check_same_thread=False)


# ── Handler ───────────────────────────────────────────────────────────────────

def _jira_count_handler(inp: dict) -> dict:
    """
    Returns:
      {
        "count": int,
        "breakdown": {
          "by_priority": {"p0": N, "p1": N, "p3": N, "other": N},
          "by_status":   {"resolved": N, "in_progress": N, "open": N, "other": N}
        },
        "filters_applied": {echo of all set inputs},
        "query_window": {
          "updated_after":  "YYYY-MM-DD" or null,
          "resolved_after": "YYYY-MM-DD" or null
        }
      }

    On error: {"error": "...", "code": "..."} per registry convention.
    """
    # ── 1. Validate / normalize inputs ────────────────────────────────────────
    module           = (inp.get("module") or "").strip() or None
    functional_area  = (inp.get("functional_area") or "").strip() or None
    type_bucket      = (inp.get("type_bucket") or "").strip() or None
    status_bucket    = (inp.get("status_bucket") or "").strip() or None
    priority_bucket  = (inp.get("priority_bucket") or "").strip() or None

    try:
        updated_within  = int(inp["updated_within_days"])  if inp.get("updated_within_days")  is not None else None
        resolved_within = int(inp["resolved_within_days"]) if inp.get("resolved_within_days") is not None else None
    except (TypeError, ValueError):
        return {"error": "updated_within_days/resolved_within_days must be integers", "code": "invalid_input"}

    for label, val in (("updated_within_days", updated_within), ("resolved_within_days", resolved_within)):
        if val is not None and (val < 1 or val > 365):
            return {"error": f"{label}={val} is out of range (1-365)", "code": "invalid_input"}

    # Defensive enum checks (schema enforces but the handler must be robust)
    if type_bucket and type_bucket not in {"task", "bug", "story", "epic", "other"}:
        return {"error": f"invalid type_bucket: {type_bucket!r}", "code": "invalid_input"}
    if status_bucket and status_bucket not in {"resolved", "in_progress", "open", "other"}:
        return {"error": f"invalid status_bucket: {status_bucket!r}", "code": "invalid_input"}
    if priority_bucket and priority_bucket not in {"p0", "p1", "p3", "other"}:
        return {"error": f"invalid priority_bucket: {priority_bucket!r}", "code": "invalid_input"}

    if not JIRA_DB.exists():
        return {"error": "Jira SQLite database not found.", "code": "db_not_found"}

    # ── 2. Build WHERE clauses + params ───────────────────────────────────────
    where: list[str] = []
    params: dict = {}

    if module:
        # Module filter is a subquery on ticket_module_tags. confidence >= 0.5 floor
        # (the script's MIN_CONFIDENCE_TO_WRITE=0.65 means values < 0.65 don't exist
        #  in production data anyway, but 0.5 leaves room for future source='manual' rows).
        where.append(
            "t.key IN (SELECT ticket_key FROM ticket_module_tags "
            "WHERE module_slug = :module AND confidence >= 0.5)"
        )
        params["module"] = module

    if functional_area:
        where.append("t.functional_area = :fa")
        params["fa"] = functional_area

    if type_bucket:
        where.append("c.type_bucket = :type_bucket")
        params["type_bucket"] = type_bucket

    if status_bucket:
        where.append("c.status_bucket = :status_bucket")
        params["status_bucket"] = status_bucket

    if priority_bucket:
        where.append("c.priority_bucket = :priority_bucket")
        params["priority_bucket"] = priority_bucket

    # ── DATE FILTERS — substr(...,1,10) NOT datetime() — see top-of-file note ─
    if updated_within is not None:
        where.append("substr(t.updated_at, 1, 10) >= date('now', :uwd)")
        params["uwd"] = f"-{updated_within} days"

    if resolved_within is not None:
        where.append("substr(t.resolved_at, 1, 10) >= date('now', :rwd)")
        params["rwd"] = f"-{resolved_within} days"

    where_sql = " AND ".join(where) if where else "1=1"

    # Whether we need to join ticket_classifications.
    # We JOIN whenever ANY bucket filter is set OR the breakdown queries
    # need it (always — breakdowns group on bucket columns).
    # Simpler: always LEFT JOIN; cost is negligible (index on ticket_key).

    base_from = (
        "FROM tickets t "
        "LEFT JOIN ticket_classifications c ON t.key = c.ticket_key"
    )

    # ── 3. Execute the three queries ──────────────────────────────────────────
    conn = _open_ro()
    try:
        # Total count
        count_sql = f"SELECT COUNT(DISTINCT t.key) {base_from} WHERE {where_sql}"
        total = conn.execute(count_sql, params).fetchone()[0] or 0

        # by_priority breakdown
        priority_sql = (
            f"SELECT COALESCE(c.priority_bucket, 'unclassified') AS bucket, "
            f"       COUNT(DISTINCT t.key) AS cnt "
            f"{base_from} WHERE {where_sql} "
            f"GROUP BY bucket"
        )
        by_priority = {row[0]: row[1] for row in conn.execute(priority_sql, params).fetchall()}

        # by_status breakdown
        status_sql = (
            f"SELECT COALESCE(c.status_bucket, 'unclassified') AS bucket, "
            f"       COUNT(DISTINCT t.key) AS cnt "
            f"{base_from} WHERE {where_sql} "
            f"GROUP BY bucket"
        )
        by_status = {row[0]: row[1] for row in conn.execute(status_sql, params).fetchall()}
    except sqlite3.Error as exc:
        return {"error": f"SQLite error: {exc}", "code": "sqlite_error"}
    finally:
        conn.close()

    # ── 4. Compute query_window for transparency ──────────────────────────────
    today = datetime.now(timezone.utc).date()
    query_window = {
        "updated_after":  (today - timedelta(days=updated_within)).isoformat()  if updated_within  is not None else None,
        "resolved_after": (today - timedelta(days=resolved_within)).isoformat() if resolved_within is not None else None,
    }

    # ── 5. Echo non-null filters (omit None to keep the response clean) ───────
    filters_applied = {}
    if module:           filters_applied["module"] = module
    if functional_area:  filters_applied["functional_area"] = functional_area
    if type_bucket:      filters_applied["type_bucket"] = type_bucket
    if status_bucket:    filters_applied["status_bucket"] = status_bucket
    if priority_bucket:  filters_applied["priority_bucket"] = priority_bucket
    if updated_within  is not None: filters_applied["updated_within_days"]  = updated_within
    if resolved_within is not None: filters_applied["resolved_within_days"] = resolved_within

    return {
        "count": total,
        "breakdown": {
            "by_priority": by_priority,
            "by_status":   by_status,
        },
        "filters_applied": filters_applied,
        "query_window": query_window,
    }


# ── End of file ──────────────────────────────────────────────────────────────
#
# Edge cases this handler covers:
#   - All filters empty            → count = 37,267 (every ticket), breakdowns
#                                    are global distributions.
#   - module specified but unknown → count = 0 (no module_tags rows match).
#   - functional_area unknown      → count = 0 (functional_area = X never matches).
#   - Bucket filter set to value that doesn't exist (e.g. status_bucket='other'
#     when no tickets have status_category='undefined') → count = 0.
#   - Both updated_within and resolved_within set → ANDed; restrictive.
#   - SQLite read error            → structured error, no crash.
#
# What this handler does NOT do (by design):
#   - It does NOT return ticket keys (that's jira_search_ranked's job).
#   - It does NOT respect classifier_version (counts include all versions).
#     If we ever do a v2.0 reclassify, we may want to add a version filter.
#   - It does NOT respect confidence_floor as an input — fixed at 0.5 for now.
#     Can be added if eval shows need.
