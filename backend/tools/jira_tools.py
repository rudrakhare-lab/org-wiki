"""
Jira tools — search ranked tickets, fetch full ticket details, run named queries.

Security:
  jira_search_ranked: wraps jira_retriever (existing safe wrapper around fetch_ranked).
  jira_get_ticket: validates key format; opens SQLite read-only.
  jira_named_query: whitelisted query names only; all params as positional ? placeholders.
"""
from __future__ import annotations

import re
import sqlite3
from typing import Any

from backend import jira_retriever
from backend.config import JIRA_DB

_KEY_RE = re.compile(r"^[A-Z][A-Z0-9]+-\d+$")

# ── Named query registry ──────────────────────────────────────────────────────
# Tuples of (sql_template, required_param_builder_fn).
# ALL values go through positional ? — never f-string substitution.

def _tickets_by_area_params(p: dict) -> tuple:
    return (p.get("functional_area", ""), min(int(p.get("limit", 20)), 50))

def _recently_resolved_params(p: dict) -> tuple:
    return (str(int(p.get("days", 90))), min(int(p.get("limit", 20)), 50))

def _open_by_priority_params(p: dict) -> tuple:
    priority = p.get("priority", "P0")
    if priority not in ("P0", "P1", "P2", "P3"):
        priority = "P0"
    return (priority, min(int(p.get("limit", 20)), 50))

def _tickets_linking_key_params(p: dict) -> tuple:
    return (f"%{p.get('key', '')}%",)

_NAMED_QUERIES: dict[str, tuple[str, Any]] = {
    "tickets_by_area": (
        "SELECT key, summary, status_category, priority, "
        "substr(updated_at,1,10) AS updated, substr(resolved_at,1,10) AS resolved, "
        "comment_count, functional_area "
        "FROM tickets WHERE functional_area = ? "
        "ORDER BY updated_at DESC LIMIT ?",
        _tickets_by_area_params,
    ),
    "recently_resolved": (
        "SELECT key, summary, status_category, priority, "
        "substr(updated_at,1,10) AS updated, substr(resolved_at,1,10) AS resolved, "
        "comment_count, functional_area "
        "FROM tickets WHERE status_category = 'done' AND resolved_at IS NOT NULL "
        "AND substr(resolved_at,1,10) >= date('now', '-' || ? || ' days') "
        "ORDER BY resolved_at DESC LIMIT ?",
        _recently_resolved_params,
    ),
    "open_by_priority": (
        "SELECT key, summary, status_category, priority, "
        "substr(updated_at,1,10) AS updated, comment_count, functional_area "
        "FROM tickets WHERE status_category != 'done' AND priority = ? "
        "ORDER BY updated_at DESC LIMIT ?",
        _open_by_priority_params,
    ),
    "tickets_linking_key": (
        "SELECT key, summary, status_category, "
        "substr(updated_at,1,10) AS updated "
        "FROM tickets WHERE links_json LIKE ? "
        "ORDER BY updated_at DESC LIMIT 20",
        _tickets_linking_key_params,
    ),
}

_ALLOWED_QUERY_NAMES = list(_NAMED_QUERIES.keys())


# ── Schemas ───────────────────────────────────────────────────────────────────

JIRA_SEARCH_RANKED_SCHEMA: dict = {
    "name": "jira_search_ranked",
    "description": (
        "Search Jira tickets ranked by recency, status, and content quality. "
        "Results are bucketed into LATEST (≤180 days updated/resolved), "
        "HISTORICAL (older, may be stale), and STALE_OPEN (abandoned). "
        "Always use this alongside wiki_search — Jira captures operational history the wiki may not. "
        "LATEST tickets represent current behavior; HISTORICAL may be outdated. "
        "If LATEST and HISTORICAL disagree, surface the conflict explicitly."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Keyword or property name to search for in Jira.",
            },
            "functional_area": {
                "type": "string",
                "description": (
                    "Optional Jira functional_area filter (e.g. 'WF-empexp', "
                    "'WF-wis-meeting-vms', 'WP-admin'). "
                    "See config/functional_area_to_module.toml for the full mapping."
                ),
            },
            "include_stale": {
                "type": "boolean",
                "description": "Include STALE_OPEN bucket. Default false — only use if you need abandoned tickets.",
                "default": False,
            },
            "limit": {
                "type": "integer",
                "description": "Max results per bucket. Default 10, max 25.",
                "default": 10,
                "minimum": 1,
                "maximum": 25,
            },
        },
        "required": ["query"],
    },
}

JIRA_GET_TICKET_SCHEMA: dict = {
    "name": "jira_get_ticket",
    "description": (
        "Fetch the full details of a specific Jira ticket by its key (e.g. 'TS-12345'). "
        "Returns summary, description, comments, status, dates, and linked tickets. "
        "Use this when a jira_search_ranked result looks directly relevant and you need "
        "the full content to understand what was actually resolved or implemented.\n\n"
        "Description and comments are returned in chunks (default 2000 chars each). "
        "Check `description_has_more` / `comments_has_more` — if true, call again "
        "with `description_offset` / `comments_offset` set to the corresponding "
        "`_next_offset` value to retrieve the next chunk. `_total_length` tells "
        "you the full size so you know when to stop. This matters for tickets "
        "with long comment threads (TS-19xxx incident-type tickets often have "
        "10+ comments totaling 5–20 KB)."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "key": {
                "type": "string",
                "description": "Jira ticket key, e.g. 'TS-12345' or 'PB-67890'. Must be PROJECT-NUMBER format.",
            },
            "description_offset": {
                "type": "integer",
                "description": "Optional: byte offset into description_text for pagination. Default 0.",
            },
            "comments_offset": {
                "type": "integer",
                "description": "Optional: byte offset into comments_text for pagination. Default 0.",
            },
            "field_chunk_size": {
                "type": "integer",
                "description": "Optional: chunk size per text field. Default 2000. Cap at 8000 for safety.",
            },
        },
        "required": ["key"],
    },
}

JIRA_NAMED_QUERY_SCHEMA: dict = {
    "name": "jira_named_query",
    "description": (
        "Run a named aggregate Jira query for pattern analysis. "
        f"Allowed query names: {', '.join(_ALLOWED_QUERY_NAMES)}. "
        "Use 'tickets_by_area' for all tickets in a functional area. "
        "Use 'recently_resolved' for recently closed tickets. "
        "Use 'open_by_priority' for high-priority open issues. "
        "Use 'tickets_linking_key' to find tickets that reference a given key."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query_name": {
                "type": "string",
                "description": f"One of: {', '.join(_ALLOWED_QUERY_NAMES)}",
                "enum": _ALLOWED_QUERY_NAMES,
            },
            "params": {
                "type": "object",
                "description": (
                    "Query parameters. "
                    "tickets_by_area: {functional_area, limit?}. "
                    "recently_resolved: {days? (default 90), limit?}. "
                    "open_by_priority: {priority: P0|P1|P2, limit?}. "
                    "tickets_linking_key: {key}."
                ),
            },
        },
        "required": ["query_name", "params"],
    },
}


# ── Handlers ──────────────────────────────────────────────────────────────────

def _open_ro() -> sqlite3.Connection:
    uri = f"file:{JIRA_DB}?mode=ro&immutable=1"
    return sqlite3.connect(uri, uri=True, check_same_thread=False)


def _jira_search_ranked_handler(inp: dict) -> dict:
    query = str(inp.get("query", "")).strip()
    if not query:
        return {"error": "query is required", "code": "missing_input"}
    limit = min(int(inp.get("limit", 10)), 25)
    result = jira_retriever.search(
        question=query,
        functional_area=inp.get("functional_area"),
        limit=limit,
        include_stale=bool(inp.get("include_stale", False)),
    )

    def _trim(row: dict) -> dict:
        return {
            "key": row.get("key"),
            "summary": (row.get("summary") or "")[:120],
            "status_category": row.get("status_category"),
            "updated": row.get("updated"),
            "resolved": row.get("resolved"),
            "comment_count": row.get("comment_count", 0),
            "hit_summary": bool(row.get("hit_summary")),
        }

    stale_key = "STALE-OPEN"
    return {
        "keywords": result["keywords"],
        "buckets": {
            "LATEST": [_trim(r) for r in result["buckets"].get("LATEST", [])],
            "HISTORICAL": [_trim(r) for r in result["buckets"].get("HISTORICAL", [])],
            "STALE_OPEN": [_trim(r) for r in result["buckets"].get(stale_key, [])],
        },
        "total": len(result["rows"]),
    }


_FIELD_CHUNK_SIZE = 2000  # default chunk per text field per call


def _slice_field(text: str | None, offset: int, limit: int) -> tuple[str, dict]:
    """Return (chunk, meta) for a long-text field. meta has total_length,
    has_more, next_offset. Backwards-compat default: offset=0, limit=2000
    reproduces the pre-G09 behavior (first 2000 chars, no pagination info)."""
    full = text or ""
    total = len(full)
    start = max(0, offset)
    end = start + max(0, limit)
    chunk = full[start:end]
    has_more = end < total
    meta = {
        "total_length": total,
        "has_more": has_more,
        "next_offset": end if has_more else None,
    }
    return chunk, meta


def _jira_get_ticket_handler(inp: dict) -> dict:
    """Fetch one Jira ticket from the local SQLite mirror.

    G09: pagination — optional `description_offset` / `comments_offset` (int,
    default 0) and `field_chunk_size` (int, default 2000) let the model
    retrieve content beyond the first 2000 chars. Default behavior is
    unchanged from pre-G09: description_text and comments_text return the
    first 2000 chars, total_length/has_more/next_offset fields are added
    so the model can decide whether to paginate.
    """
    key = str(inp.get("key", "")).strip()
    if not _KEY_RE.match(key):
        return {
            "error": f"Invalid Jira key format: {key!r}. Expected PROJECT-NUMBER (e.g. TS-12345).",
            "code": "invalid_key_format",
        }
    if not JIRA_DB.exists():
        return {"error": "Jira SQLite database not found.", "code": "db_not_found"}

    description_offset = int(inp.get("description_offset") or 0)
    comments_offset = int(inp.get("comments_offset") or 0)
    chunk_size = int(inp.get("field_chunk_size") or _FIELD_CHUNK_SIZE)

    conn = _open_ro()
    try:
        cur = conn.execute(
            "SELECT key, summary, status_category, priority, "
            "substr(updated_at,1,10) AS updated, substr(resolved_at,1,10) AS resolved, "
            "description_text, comments_text, comment_count, links_json, "
            "functional_area, epic_key "
            "FROM tickets WHERE key = ?",
            (key,),
        )
        row = cur.fetchone()
    finally:
        conn.close()

    if row is None:
        return {"error": f"Ticket not found: {key}", "code": "not_found"}

    cols = [
        "key", "summary", "status_category", "priority",
        "updated", "resolved",
        "description_text", "comments_text", "comment_count",
        "links_json", "functional_area", "epic_key",
    ]
    d = dict(zip(cols, row))
    desc_chunk, desc_meta = _slice_field(d["description_text"], description_offset, chunk_size)
    comm_chunk, comm_meta = _slice_field(d["comments_text"], comments_offset, chunk_size)
    d["description_text"] = desc_chunk
    d["description_total_length"] = desc_meta["total_length"]
    d["description_has_more"] = desc_meta["has_more"]
    d["description_next_offset"] = desc_meta["next_offset"]
    d["comments_text"] = comm_chunk
    d["comments_total_length"] = comm_meta["total_length"]
    d["comments_has_more"] = comm_meta["has_more"]
    d["comments_next_offset"] = comm_meta["next_offset"]
    return d


def _jira_named_query_handler(inp: dict) -> dict:
    query_name = str(inp.get("query_name", "")).strip()
    params = inp.get("params") or {}
    if not isinstance(params, dict):
        params = {}

    if query_name not in _NAMED_QUERIES:
        return {
            "error": f"Unknown query name: {query_name!r}",
            "allowed_names": _ALLOWED_QUERY_NAMES,
            "code": "unknown_query",
        }

    if not JIRA_DB.exists():
        return {"error": "Jira SQLite database not found.", "code": "db_not_found"}

    sql, param_fn = _NAMED_QUERIES[query_name]
    sql_params = param_fn(params)

    conn = _open_ro()
    try:
        cur = conn.execute(sql, sql_params)
        col_names = [d[0] for d in cur.description]
        rows = [dict(zip(col_names, row)) for row in cur.fetchall()]
    finally:
        conn.close()

    return {"query_name": query_name, "rows": rows, "total": len(rows)}
