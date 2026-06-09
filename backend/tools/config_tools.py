"""
Config tools — look up PMS property names in the SQLite config catalog,
falling back to wiki TF-IDF when SQLite has no result or is unavailable.
"""
from __future__ import annotations

import json
import os
import sqlite3

from backend import wiki_retriever

# Absolute path to the configs SQLite database.
# Defined as a module-level global so tests can patch it with patch.object().
_DB_PATH: str = os.path.join(
    os.path.dirname(__file__),  # backend/tools/
    "..", "..",                  # → project root
    "raw", "configs", "configs.sqlite",
)
_DB_PATH = os.path.abspath(_DB_PATH)


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


def _build_enriched(con: sqlite3.Connection, row: sqlite3.Row) -> dict:
    """Build the enriched result dict from a configs row plus linked tables."""
    prop = row["property_name"]

    # Jira tickets (top 10 by relevance)
    jira_rows = con.execute(
        "SELECT jira_key, relevance FROM jira_links WHERE property_name = ? ORDER BY relevance DESC LIMIT 10",
        (prop,),
    ).fetchall()

    # Module pages
    module_rows = con.execute(
        "SELECT module_slug FROM module_links WHERE property_name = ?",
        (prop,),
    ).fetchall()

    # Dependencies — property_a = this property (depends_on)
    try:
        dep_rows = con.execute(
            "SELECT property_b, dep_type, direction, confidence FROM dependencies "
            "WHERE property_a = ? ORDER BY confidence DESC",
            (prop,),
        ).fetchall()
    except sqlite3.OperationalError:
        dep_rows = []

    # Required_by — property_b = this property (other properties depend on this one)
    try:
        req_rows = con.execute(
            "SELECT property_a, dep_type, direction, confidence FROM dependencies "
            "WHERE property_b = ? ORDER BY confidence DESC",
            (prop,),
        ).fetchall()
    except sqlite3.OperationalError:
        req_rows = []

    return {
        "found": True,
        "source": "sqlite",
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

    # If DB doesn't exist, fall through to wiki TF-IDF immediately
    if not os.path.exists(_DB_PATH):
        return _wiki_fallback(property_name, service, server)

    con = sqlite3.connect(_DB_PATH)
    con.row_factory = sqlite3.Row

    try:
        # Build optional WHERE clauses for service and server filters
        filters = ["LOWER(property_name) = LOWER(?)"]
        params: list = [property_name]

        if service:
            filters.append("LOWER(service) = LOWER(?)")
            params.append(service)
        if server:
            filters.append("server IN (?, 'both')")
            params.append(server)

        where_clause = " AND ".join(filters)
        row = con.execute(
            f"SELECT * FROM configs WHERE {where_clause} LIMIT 1",
            params,
        ).fetchone()

        # Fuzzy FTS5 fallback when exact match misses
        if row is None and fuzzy:
            try:
                # Quote the term to avoid FTS5 syntax errors with camelCase names
                fts_term = f'"{property_name}"'
                fts_filters = ["configs_fts MATCH ?"]
                fts_params: list = [fts_term]

                if service:
                    fts_filters.append("LOWER(c.service) = LOWER(?)")
                    fts_params.append(service)
                if server:
                    fts_filters.append("c.server IN (?, 'both')")
                    fts_params.append(server)

                fts_where = " AND ".join(fts_filters)
                row = con.execute(
                    f"SELECT c.* FROM configs c "
                    f"JOIN configs_fts f ON c.id = f.rowid "
                    f"WHERE {fts_where} "
                    f"ORDER BY f.rank LIMIT 1",
                    fts_params,
                ).fetchone()
            except sqlite3.OperationalError:
                row = None

        if row is not None:
            return _build_enriched(con, row)

    finally:
        con.close()

    # Nothing found in SQLite — fall through to wiki TF-IDF
    return _wiki_fallback(property_name, service, server)
