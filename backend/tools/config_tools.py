"""
Config tools — look up PMS property names in the wiki config catalog.
"""
from __future__ import annotations

from backend import wiki_retriever

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
        },
        "required": ["property_name"],
    },
}


def _config_lookup_handler(inp: dict) -> dict:
    property_name = str(inp.get("property_name", "")).strip()
    if not property_name:
        return {"error": "property_name is required", "code": "missing_input"}

    service = inp.get("service", "")
    server = inp.get("server", "")

    # Build targeted search query: property name + optional service
    query_parts = [property_name]
    if service:
        query_parts.append(service)
    if server:
        query_parts.append(f".{server}")
    query = " ".join(query_parts)

    pages = wiki_retriever.search(query, top_n=5)

    # Filter to config pages when property lookup is the intent
    config_pages = [p for p in pages if "configs/" in p.path]
    other_pages = [p for p in pages if "configs/" not in p.path]
    ranked = config_pages + other_pages  # config pages first

    return {
        "property_name": property_name,
        "found": len(ranked) > 0,
        "wiki_matches": [
            {"path": p.path, "title": p.title, "excerpt": p.excerpt(300)}
            for p in ranked[:5]
        ],
    }
