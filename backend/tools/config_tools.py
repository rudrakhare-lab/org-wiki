"""
Config tools — look up PMS property names in the SQLite config catalog,
falling back to wiki TF-IDF when SQLite has no result or is unavailable.
"""
from __future__ import annotations

import json

from backend import db, wiki_retriever


CONFIG_LOOKUP_SCHEMA: dict = {
    "name": "config_lookup",
    "description": (
        "Look up a PMS config property name in the wiki config catalog. "
        "Returns wiki pages that document this property — description, service, "
        ".in/.com server presence, and related properties. "
        "Use this when a question mentions a specific property name like "
        "'kioskRequireOTPBeforeRegister' or 'mealCutoffInMinutes'."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "property_name": {
                "type": "string",
                "description": "The PMS config property name to look up (case-sensitive).",
            },
            "service": {
                "type": "string",
                "description": "Optional PMS service to narrow the search (e.g. 'VISITOR', 'MEETING_ROOMS').",
            },
            "server": {
                "type": "string",
                "enum": ["com", "in"],
                "description": "Optional server filter ('com' or 'in').",
            },
            "fuzzy": {
                "type": "boolean",
                "description": "If true (default), try fuzzy FTS match when exact match misses.",
            },
        },
        "required": ["property_name"],
    },
}


def _wiki_fallback(property_name: str, service: str, server: str) -> dict:
    """Fall through to wiki TF-IDF search and return the standardised fallback dict."""
    query_parts = [property_name]
    if service:
        query_parts.append(service)
    if server:
        query_parts.append(f".{server}")
    query = " ".join(query_parts)

    ranked = wiki_retriever.search(query, top_n=5)
    return {
        "found": len(ranked) > 0,
        "source": "wiki_tfidf",
        "property_name": property_name,
        "wiki_matches": [
            {"path": p.path, "title": p.title, "excerpt": p.excerpt(300)}
            for p in ranked[:5]
        ],
    }


_known_names_cache: set[str] | None = None


def known_property_names() -> set[str]:
    """Return the set of all distinct property_name values in the config
    catalog. Cached per-process — the catalog only changes via re-ingest +
    restart (see CLAUDE.md §1), so no invalidation is needed."""
    global _known_names_cache
    if _known_names_cache is not None:
        return _known_names_cache
    try:
        with db.connection() as con:
            rows = con.execute("SELECT DISTINCT property_name FROM configs").fetchall()
            _known_names_cache = {r["property_name"] for r in rows}
    except Exception:
        _known_names_cache = set()
    return _known_names_cache


def lookup_property(name: str) -> dict | None:
    """Shared lookup core used by both the `config_lookup` tool and the
    preflight config-evidence push (backend/config_evidence.py). Exact match
    only (case-insensitive) — no fuzzy fallback, no wiki fallback; callers
    that need those wrap this (see `_config_lookup_handler`).

    Returns the same enriched dict shape as `_build_enriched`, or None if
    the property isn't in the catalog / the DB is unavailable.
    """
    try:
        with db.connection() as con:
            row = con.execute(
                "SELECT * FROM configs WHERE LOWER(property_name) = LOWER(%s) LIMIT 1",
                (name,),
            ).fetchone()
            if row is None:
                return None
            return _build_enriched(con, row)
    except Exception:
        return None


def _build_enriched(con, row) -> dict:
    """Build the enriched result dict from a configs row plus linked tables."""
    prop = row["property_name"]

    # Jira tickets (top 10 by relevance)
    jira_rows = con.execute(
        "SELECT jira_key, relevance FROM jira_links WHERE property_name = %s ORDER BY relevance DESC LIMIT 10",
        (prop,),
    ).fetchall()

    # Module pages
    module_rows = con.execute(
        "SELECT module_slug FROM module_links WHERE property_name = %s",
        (prop,),
    ).fetchall()

    # Dependencies — property_a = this property (depends_on)
    try:
        dep_rows = con.execute(
            "SELECT property_b, dep_type, direction, confidence FROM dependencies "
            "WHERE property_a = %s ORDER BY confidence DESC",
            (prop,),
        ).fetchall()
    except Exception:
        dep_rows = []

    # Required_by — property_b = this property (other properties depend on this one)
    try:
        req_rows = con.execute(
            "SELECT property_a, dep_type, direction, confidence FROM dependencies "
            "WHERE property_b = %s ORDER BY confidence DESC",
            (prop,),
        ).fetchall()
    except Exception:
        req_rows = []

    return {
        "found": True,
        "source": "config_db",
        "property_name": row["property_name"],
        "service": row["service"],
        "server": row["server"],
        "description": row["description"] or "",
        "data_type": row["data_type"] or "",
        "default_value": row["default_value"] or "",
        "customizable": bool(row["customizable"]) if row["customizable"] is not None else None,
        "criteria_priority_list": json.loads(row["criteria_priority_list"]) if row["criteria_priority_list"] else [],
        "jira_tickets": [
            {"key": r["jira_key"], "relevance": r["relevance"]}
            for r in jira_rows
        ],
        "module_pages": [r["module_slug"] for r in module_rows],
        "depends_on": [
            {"property": r["property_b"], "dep_type": r["dep_type"], "direction": r["direction"], "confidence": r["confidence"]}
            for r in dep_rows
        ],
        "required_by": [
            {"property": r["property_a"], "dep_type": r["dep_type"], "direction": r["direction"], "confidence": r["confidence"]}
            for r in req_rows
        ],
    }


def _config_lookup_handler(inp: dict) -> dict:
    property_name = str(inp.get("property_name", "")).strip()
    if not property_name:
        return {"error": "property_name is required", "code": "missing_input"}

    service = inp.get("service") or ""
    server = inp.get("server") or ""
    fuzzy = inp.get("fuzzy", True)

    # No service/server filter → the shared lookup_property() core (exact,
    # case-insensitive match) covers this call exactly, so tool and preflight
    # share one implementation. Fall through to fuzzy/wiki below on a miss.
    if not service and not server:
        enriched = lookup_property(property_name)
        if enriched is not None:
            return enriched

    try:
        with db.connection() as con:
            # Build optional WHERE clauses for service and server filters
            filters = ["LOWER(property_name) = LOWER(%s)"]
            params: list = [property_name]

            if service:
                filters.append("LOWER(service) = LOWER(%s)")
                params.append(service)
            if server:
                filters.append("server IN (%s, 'both')")
                params.append(server)

            where_clause = " AND ".join(filters)
            row = con.execute(
                f"SELECT * FROM configs WHERE {where_clause} LIMIT 1",
                params,
            ).fetchone()

            # Fuzzy fallback when exact match misses — pg_trgm similarity
            # (replaces SQLite FTS5 MATCH; uses the trigram GIN index on
            #  property_name). Cascades to wiki TF-IDF below if still nothing.
            if row is None and fuzzy:
                fz_filters = ["c.property_name ILIKE %(like)s"]
                fz_params: dict = {"term": property_name, "like": f"%{property_name}%"}
                if service:
                    fz_filters.append("LOWER(c.service) = LOWER(%(service)s)")
                    fz_params["service"] = service
                if server:
                    fz_filters.append("c.server IN (%(server)s, 'both')")
                    fz_params["server"] = server
                fz_where = " AND ".join(fz_filters)
                row = con.execute(
                    f"SELECT c.*, similarity(c.property_name, %(term)s) AS _sim "
                    f"FROM configs c WHERE {fz_where} "
                    f"ORDER BY _sim DESC LIMIT 1",
                    fz_params,
                ).fetchone()

            if row is not None:
                return _build_enriched(con, row)
    except Exception:
        # DB unavailable or schema missing → fall through to wiki TF-IDF.
        return _wiki_fallback(property_name, service, server)

    # Nothing found in Postgres — fall through to wiki TF-IDF
    return _wiki_fallback(property_name, service, server)
