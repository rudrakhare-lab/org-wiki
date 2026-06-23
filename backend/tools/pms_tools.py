"""
PMS tools — fetch default property metadata and live runtime config values.

Auth: reads PMS_TOKEN_{COM/IN} and PMS_COOKIE_{COM/IN} env vars only.
If credentials are absent → returns {status: "credentials_required"} (never raises).
Tokens are NEVER included in return values or tool trace output.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure scripts/ is importable
_SCRIPTS = Path(__file__).resolve().parent.parent.parent / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))


_VALID_SERVICES = frozenset({
    "VISITOR", "MEETING_ROOMS", "BOOKING-RULE-ENGINE", "WIS-SEAT-BOOKING",
    "GUARD-APP", "EMAIL-EMP-EXPERIENCE", "EMP-EXP-INTERNAL-CONFIG",
    "EMP-EXP-COMMON-CONFIG", "PROJECT-MANAGEMENT-SERVICE", "APP_SERVER_CONFIG", "ETS",
})

# Services with NO live PMS API endpoint. They stay in _VALID_SERVICES so the
# LLM recognises the names, but there is no POST /{service}/properties to call:
#   - APP_SERVER_CONFIG: static reference, ingested from wis_service_configs.xlsx
#     (sheets 10-11) → wiki/configs/app-server-config.md.
#   - ETS: not present in any ingested PMS config file; properties are Jira-sourced
#     only (PB-52960, SE-51628, SE-47565). No live endpoint exists.
# Live-fetch handlers short-circuit on these with a clear, honest message instead
# of issuing a request that 404s/401s.
_NO_LIVE_ENDPOINT = frozenset({"APP_SERVER_CONFIG", "ETS"})


def _no_live_endpoint(service: str) -> dict:
    """Clear response for a service that has no live PMS API endpoint."""
    where = ("wiki/configs/app-server-config.md (static reference)"
             if service == "APP_SERVER_CONFIG"
             else "Jira tickets only (PB-52960, SE-51628, SE-47565)")
    return {
        "status": "no_live_endpoint",
        "code": "no_live_endpoint",
        "service": service,
        "message": (
            f"'{service}' has no live PMS API endpoint — it cannot be fetched via "
            f"the PMS debug tools. Source: {where}. Answer from the wiki/Jira "
            f"evidence instead of attempting a live lookup."
        ),
    }

# ── Schemas ───────────────────────────────────────────────────────────────────

PMS_DEFAULT_PROPERTIES_SCHEMA: dict = {
    "name": "pms_default_properties",
    "description": (
        "Fetch PMS default property metadata for a service — property names, "
        "default values, data types, customizability, criteria priority list, and definitions. "
        "Use this for questions about what configs exist for a service and their defaults. "
        "Does NOT return live/customer-specific values — use pms_runtime_values for those."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "service": {
                "type": "string",
                "description": (
                    "PMS service ID. One of: VISITOR, MEETING_ROOMS, BOOKING-RULE-ENGINE, "
                    "WIS-SEAT-BOOKING, GUARD-APP, EMAIL-EMP-EXPERIENCE, EMP-EXP-INTERNAL-CONFIG, "
                    "EMP-EXP-COMMON-CONFIG, PROJECT-MANAGEMENT-SERVICE, APP_SERVER_CONFIG, ETS."
                ),
            },
            "server": {
                "type": "string",
                "enum": ["com", "in"],
                "description": "Server: 'com' for global/international, 'in' for India-region.",
                "default": "com",
            },
        },
        "required": ["service"],
    },
}

PMS_LIST_OFFICES_SCHEMA: dict = {
    "name": "pms_list_offices",
    "description": (
        "List all offices under a BUID with their human-readable names. "
        "Returns each office as {officeid, name} where name is "
        "'Premise Name (City, Country)'. Use this to translate office "
        "names mentioned by the user into OFFICEIDs, or to enumerate "
        "the offices that exist for a BUID.\n\n"
        "Hits a DIFFERENT host (mis-security.moveinsync.*) from the rest "
        "of the PMS API — has its own credential path but reuses PMS_TOKEN.\n\n"
        "When NOT to call: do not call this to learn what properties are "
        "configured — use pms_default_properties for that. Do not call to "
        "discover offices with overrides — use pms_list_criteria with "
        "criteria='OFFICEID' for that. Do not call without an established "
        "server+BUID — verify first with pms_verify_buid if uncertain."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "service": {
                "type": "string",
                "description": "PMS service ID (e.g. VISITOR). Required for auth header.",
            },
            "server": {
                "type": "string",
                "enum": ["com", "in"],
                "description": "Server: 'com' for global, 'in' for India-region.",
            },
            "buid": {
                "type": "string",
                "description": "The BUID to enumerate offices for.",
            },
        },
        "required": ["service", "server", "buid"],
    },
}


PMS_LIST_CRITERIA_SCHEMA: dict = {
    "name": "pms_list_criteria",
    "description": (
        "List the criteria values that have configuration overrides at a "
        "sub-BUID level. For criteria='OFFICEID' returns the OFFICEIDs "
        "that have any override (NOT all offices — only the customized "
        "ones). For criteria='ROOM_ID' returns rooms with overrides. "
        "For criteria='ROLE' returns roles with overrides (PROJECT-"
        "MANAGEMENT-SERVICE only).\n\n"
        "When NOT to call: do not call this to enumerate ALL offices "
        "(use pms_list_offices — different endpoint, returns names). "
        "Do not call to read property values (use pms_runtime_values or "
        "pms_diagnose_property)."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "service": {
                "type": "string",
                "description": "PMS service ID.",
            },
            "server": {
                "type": "string",
                "enum": ["com", "in"],
                "description": "Server: 'com' for global, 'in' for India-region.",
            },
            "buid": {
                "type": "string",
                "description": "The BUID whose overrides to enumerate.",
            },
            "criteria": {
                "type": "string",
                "enum": ["OFFICEID", "ROOM_ID", "ROLE"],
                "description": "Which override level to list.",
            },
        },
        "required": ["service", "server", "buid", "criteria"],
    },
}


PMS_VERIFY_BUID_SCHEMA: dict = {
    "name": "pms_verify_buid",
    "description": (
        "Check whether a BUID exists on a given server (.com or .in). "
        "Verifies via the token-free offices endpoint: returns found:bool "
        "plus office_count and a small offices_sample. Use this FIRST "
        "whenever the server is ambiguous and the user has named a "
        "specific BUID — a BUID may exist on .com but not .in (or vice "
        "versa), and wrong-server queries silently return empty results "
        "that look like 'no config set'.\n\n"
        "Strong signal interpretation: found=false (zero offices) ALMOST "
        "ALWAYS means the wrong server was chosen, not that the BUID "
        "doesn't exist. Try the other server before telling the user the "
        "BUID is invalid.\n\n"
        "When NOT to call: do not use this for general BUID lookup or "
        "discovery — only to verify a specific candidate the user named. "
        "Do not call before every config query — call once per BUID per "
        "turn; the result is stable within a session."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "service": {
                "type": "string",
                "description": "PMS service ID (e.g. VISITOR).",
            },
            "server": {
                "type": "string",
                "enum": ["com", "in"],
                "description": "Server to check the BUID against.",
            },
            "buid": {
                "type": "string",
                "description": "The BUID candidate to verify.",
            },
        },
        "required": ["service", "server", "buid"],
    },
}


PMS_DIAGNOSE_PROPERTY_SCHEMA: dict = {
    "name": "pms_diagnose_property",
    "description": (
        "PRIMARY tool for live PMS config debug. Generates a full "
        "diagnostic report for one property at one BUID: calls "
        "fetch_defaults + fetch_level(BUID) + (optionally) "
        "fetch_level(OFFICEID), then returns a markdown report with "
        "values at every level, the effective (winning) value, and fix "
        "guidance.\n\n"
        "Returns: {report_markdown (for the user), property, buid, "
        "server, value_found (bool — for your reasoning, true if the "
        "property exists in service defaults)}.\n\n"
        "When NOT to call: do not call pms_runtime_values separately to "
        "assemble the same data — this tool does the whole hierarchy "
        "walk in one call. Do not call pms_default_properties first — "
        "this tool calls fetch_defaults internally. Do not call without "
        "a property name; if the user described a behavior without "
        "naming a property, search wiki/config_lookup first to find "
        "the property name, then call this."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "service": {
                "type": "string",
                "description": "PMS service ID (e.g. VISITOR).",
            },
            "server": {
                "type": "string",
                "enum": ["com", "in"],
                "description": "Server: 'com' for global, 'in' for India-region.",
            },
            "buid": {
                "type": "string",
                "description": "BUID for the diagnostic (e.g. 'genpactindia-GInd').",
            },
            "property": {
                "type": "string",
                "description": "Case-sensitive PMS property name (e.g. 'kioskRequireOTPBeforeRegister').",
            },
            "officeid": {
                "type": "string",
                "description": (
                    "Optional OFFICEID to also fetch at the office level. "
                    "Use when the user is debugging an office-specific override."
                ),
            },
        },
        "required": ["service", "server", "buid", "property"],
    },
}


PMS_RUNTIME_VALUES_SCHEMA: dict = {
    "name": "pms_runtime_values",
    "description": (
        "Fetch live PMS config values for a specific BUID at a specific level of the hierarchy "
        "(DEFAULT → BUID → OFFICEID → ROOM_ID/ROLE). "
        "Config hierarchy: a property set at OFFICEID level overrides BUID, which overrides DEFAULT. "
        "Returns credentials_required if PMS tokens are not configured — treat this as "
        "informational and answer with wiki/Jira evidence instead. "
        "Use this when a user provides a BUID and asks about actual config behavior."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "service": {
                "type": "string",
                "description": "PMS service ID (e.g. VISITOR, MEETING_ROOMS).",
            },
            "server": {
                "type": "string",
                "enum": ["com", "in"],
                "description": "Server: 'com' for global, 'in' for India-region.",
            },
            "buid": {
                "type": "string",
                "description": "The BUID to fetch configs for (e.g. 'genpactindia-GInd').",
            },
            "criteria": {
                "type": "string",
                "enum": ["OFFICEID", "ROOM_ID", "ROLE"],
                "description": (
                    "Optional sub-BUID level. Omit to fetch BUID-level configs. "
                    "Use OFFICEID for office overrides, ROOM_ID for meeting-room overrides, "
                    "ROLE for PROJECT-MANAGEMENT-SERVICE role overrides."
                ),
            },
            "value": {
                "type": "string",
                "description": (
                    "The criteria value (e.g. an OFFICEID string, ROOM_ID string, "
                    "or role name like 'employee'). Required when criteria is set."
                ),
            },
        },
        "required": ["service", "server", "buid"],
    },
}


# ── Auth helpers ──────────────────────────────────────────────────────────────

def _get_tokens(server: str) -> tuple[str, str]:
    """Return (token, cookie). Never raises. Returns ('', '') if not configured."""
    s = server.lower()
    if s == "in":
        token = os.getenv("PMS_TOKEN_IN") or os.getenv("PMS_TOKEN", "")
        cookie = os.getenv("PMS_COOKIE_IN") or os.getenv("PMS_COOKIE", "")
    else:
        token = os.getenv("PMS_TOKEN_COM") or os.getenv("PMS_TOKEN", "")
        cookie = os.getenv("PMS_COOKIE_COM") or os.getenv("PMS_COOKIE", "")
    return token, cookie


def _credentials_required(server: str) -> dict:
    suffix = "IN" if server.lower() == "in" else "COM"
    return {
        "status": "credentials_required",
        "message": (
            f"PMS credentials not configured for server='{server}'. "
            f"Set PMS_TOKEN_{suffix} (and optionally PMS_COOKIE_{suffix}) "
            f"environment variables to enable live config lookups. "
            f"Fallbacks: PMS_TOKEN / PMS_COOKIE."
        ),
        "needed_env_vars": [f"PMS_TOKEN_{suffix}", f"PMS_COOKIE_{suffix}"],
    }


def _is_auth_error(exc: Exception) -> bool:
    """True when the PMS API returned HTTP 401 — credentials needed."""
    return "401" in str(exc)


def _is_route_unavailable(exc: Exception) -> bool:
    """True when the PMS API has no such route server-side.

    The token-free server-side scheme (cms…/propmanagement/{service}/…) only
    exposes property-data routes (default-properties, properties, offices).
    The BUID-roles and criteria-value-list endpoints exist ONLY under the
    auth-gated /api scheme, so calling them server-side returns a Spring
    NoResourceFoundException ("No static resource …"). Detect that so we can
    report it clearly instead of as a generic API error or a false "outage".
    """
    s = str(exc)
    return "NoResourceFoundException" in s or "No static resource" in s


def _route_unavailable(tool: str) -> dict:
    """Clear, honest response for a PMS endpoint with no token-free server-side route."""
    return {
        "status": "unavailable_server_side",
        "code": "route_unavailable",
        "message": (
            f"'{tool}' is not available from the server: this PMS endpoint exists "
            "only on the auth-gated /api scheme, and Conwo calls PMS token-free "
            "(server-side) in production. Live config values still work via "
            "pms_runtime_values / pms_diagnose_property; office names via "
            "pms_list_offices. This helper requires an authenticated PMS session."
        ),
    }


# ── Handlers ──────────────────────────────────────────────────────────────────

def _pms_default_properties_handler(inp: dict) -> dict:
    service = str(inp.get("service", "")).strip().upper()
    server = str(inp.get("server", "com")).strip().lower()

    if service in _NO_LIVE_ENDPOINT:
        return _no_live_endpoint(service)

    token, cookie = _get_tokens(server)

    try:
        from pms_api_client import request_json, _SERVERS as _API_SERVERS
    except ImportError as exc:
        return {"error": f"PMS client not available: {exc}", "code": "import_error"}

    srv = _API_SERVERS.get(server, _API_SERVERS["com"])
    url = f"{srv['base_url']}/{service}/default-properties/details"
    try:
        raw = request_json(
            method="GET",
            url=url,
            service=service,
            token=token,
            cookie=cookie,
            cms_origin=srv["cms_origin"],
        )
    except Exception as exc:
        if _is_auth_error(exc):
            return _credentials_required(server)
        return {"error": str(exc), "code": "api_error"}

    props = []
    for item in (raw or []):
        props.append({
            "propertyName": item.get("propertyName"),
            "value": item.get("propertyValue"),
            "dataType": item.get("propertyDataType"),
            "customizable": item.get("customizable"),
            "criteriaPriorityList": item.get("criteriaPriorityList", []),
            "definition": item.get("propertyDefinition"),
        })

    return {"service": service, "server": server, "properties": props, "total": len(props)}


def _pms_runtime_values_handler(inp: dict) -> dict:
    service = str(inp.get("service", "")).strip().upper()
    server = str(inp.get("server", "com")).strip().lower()
    buid = str(inp.get("buid", "")).strip()
    criteria = inp.get("criteria")
    value = inp.get("value")

    # Normalise the legacy 'ROOMID' spelling to the API's 'ROOM_ID' (the POST
    # body key and criteria-value-list path both use the underscore form).
    if isinstance(criteria, str) and criteria.strip().upper() == "ROOMID":
        criteria = "ROOM_ID"

    if not buid:
        return {"error": "buid is required", "code": "missing_input"}

    if service in _NO_LIVE_ENDPOINT:
        return _no_live_endpoint(service)

    token, cookie = _get_tokens(server)

    try:
        from pms_session import Session
    except ImportError as exc:
        return {"error": f"PMS session not available: {exc}", "code": "import_error"}

    session = Session.load(service, buid, server)
    try:
        raw = session.fetch_level(criteria, value, token, cookie)
    except Exception as exc:
        if _is_auth_error(exc):
            return _credentials_required(server)
        return {"error": str(exc), "code": "api_error"}

    # Return property data only — never token/cookie values
    return {
        "properties": [
            {"propertyName": item.get("propertyName"), "value": item.get("propertyValue")}
            for item in (raw or [])
        ],
        "scope": {
            "buid": buid,
            "criteria": criteria,
            "criteria_value": value,
        },
        "effective_level": f"{criteria}::{value}" if criteria and value else "BUID",
        "total": len(raw or []),
    }


# ── G05 handlers: list_offices, list_criteria, verify_buid, diagnose_property ─

def _pms_list_offices_handler(inp: dict) -> dict:
    service = str(inp.get("service", "")).strip().upper()
    server = str(inp.get("server", "com")).strip().lower()
    buid = str(inp.get("buid", "")).strip()

    if not buid:
        return {"error": "buid is required", "code": "missing_input"}

    token, cookie = _get_tokens(server)

    try:
        from pms_session import Session
    except ImportError as exc:
        return {"error": f"PMS session not available: {exc}", "code": "import_error"}

    session = Session.load(service, buid, server)
    try:
        offices = session.fetch_offices(token, cookie) or {}
    except Exception as exc:
        if _is_auth_error(exc):
            return _credentials_required(server)
        return {"error": str(exc), "code": "api_error"}

    return {
        "service": service,
        "server": server,
        "buid": buid,
        "offices": [{"officeid": oid, "name": name} for oid, name in offices.items()],
        "total": len(offices),
    }


def _pms_list_criteria_handler(inp: dict) -> dict:
    service = str(inp.get("service", "")).strip().upper()
    server = str(inp.get("server", "com")).strip().lower()
    buid = str(inp.get("buid", "")).strip()
    criteria = str(inp.get("criteria", "")).strip().upper()

    if not buid or not criteria:
        return {"error": "buid and criteria are required", "code": "missing_input"}

    token, cookie = _get_tokens(server)

    try:
        from pms_session import Session
    except ImportError as exc:
        return {"error": f"PMS session not available: {exc}", "code": "import_error"}

    session = Session.load(service, buid, server)
    try:
        values = session.fetch_criteria_values(criteria, token, cookie) or []
    except Exception as exc:
        if _is_auth_error(exc):
            return _credentials_required(server)
        if _is_route_unavailable(exc):
            return _route_unavailable("pms_list_criteria")
        return {"error": str(exc), "code": "api_error"}

    return {
        "service": service,
        "server": server,
        "buid": buid,
        "criteria": criteria,
        "values": [str(v) for v in values],
        "total": len(values),
    }


def _extract_accessible_buids(roles: object) -> list[str] | None:
    """Best-effort extraction of accessible BUID strings from a fetch_roles
    response. Refined post-smoke-test against real PMS (2026-05-22):

    Real shape on .com / .in:
      {
        "serviceId": "VISITOR",
        "role": "ROLE_READ_ONLY",
        "isAllBuids": true,
        "buids": [
          {"buid": "pwcind-PWCPOC", "tenantName": "...", "stratus": false},
          ...
        ]
      }

    The list contains DICTS, not strings — we extract the "buid" field
    from each. Returns None when the shape is unrecognized so the caller
    can surface the raw response for debugging.
    """
    if not isinstance(roles, dict):
        return None
    for key in (
        "buids", "BUIDs", "accessibleBUIDs", "accessible_buids",
        "buidList", "BUIDList", "accessibleBuidList", "buIds",
    ):
        val = roles.get(key)
        if isinstance(val, list):
            extracted: list[str] = []
            for item in val:
                if isinstance(item, str):
                    extracted.append(item)
                elif isinstance(item, dict):
                    bid = item.get("buid") or item.get("BUID") or item.get("id")
                    if bid:
                        extracted.append(str(bid))
            return extracted
    # Common wrappers
    for wrapper in ("data", "user", "result", "response"):
        nested = roles.get(wrapper)
        if isinstance(nested, dict):
            inner = _extract_accessible_buids(nested)
            if inner is not None:
                return inner
    return None


def _pms_verify_buid_handler(inp: dict) -> dict:
    service = str(inp.get("service", "")).strip().upper()
    server = str(inp.get("server", "com")).strip().lower()
    buid = str(inp.get("buid", "")).strip()

    if not buid:
        return {"error": "buid is required", "code": "missing_input"}

    token, cookie = _get_tokens(server)

    try:
        from pms_session import Session
    except ImportError as exc:
        return {"error": f"PMS session not available: {exc}", "code": "import_error"}

    session = Session.load(service, buid, server)
    # Verify BUID existence via the TOKEN-FREE offices endpoint instead of the
    # auth-gated roles endpoint. The roles route (/user/service/{service}/roles)
    # exists only on the /api scheme; called token-free server-side it returns a
    # Spring NoResourceFoundException (route_unavailable), so the old check was
    # permanently broken in production. The offices endpoint is reachable
    # token-free and discriminates cleanly: a valid BUID on the correct server
    # returns offices; a wrong-server or invalid BUID returns an empty list.
    try:
        offices = session.fetch_offices(token, cookie) or {}
    except Exception as exc:
        if _is_auth_error(exc):
            return _credentials_required(server)
        return {"error": str(exc), "code": "api_error"}

    other = "in" if server == "com" else "com"
    office_count = len(offices)
    found = office_count > 0
    # Cap echoed list to avoid bloating the context — model can re-call if needed
    offices_sample = [name for _, name in list(offices.items())[:10]]

    if found:
        message = (
            f"BUID '{buid}' exists on the .{server} server "
            f"({office_count} office(s) found) — server/BUID confirmed."
        )
    else:
        message = (
            f"⚠️ BUID '{buid}' returned NO offices on the .{server} server. "
            f"This usually means the wrong server — try .{other} before "
            f"concluding the BUID is invalid."
        )

    return {
        "service": service,
        "server": server,
        "buid": buid,
        "found": found,
        "office_count": office_count,
        "offices_sample": offices_sample,
        "message": message,
    }


def _pms_diagnose_property_handler(inp: dict) -> dict:
    service = str(inp.get("service", "")).strip().upper()
    server = str(inp.get("server", "com")).strip().lower()
    buid = str(inp.get("buid", "")).strip()
    property_name = str(inp.get("property", "")).strip()
    officeid = inp.get("officeid")

    if not buid or not property_name:
        return {"error": "buid and property are required", "code": "missing_input"}

    if service in _NO_LIVE_ENDPOINT:
        return _no_live_endpoint(service)

    token, cookie = _get_tokens(server)

    try:
        from pms_session import Session
    except ImportError as exc:
        return {"error": f"PMS session not available: {exc}", "code": "import_error"}

    session = Session.load(service, buid, server)
    try:
        if not session._defaults:
            session.fetch_defaults(token, cookie)
        session.fetch_level(None, None, token, cookie)
        if officeid:
            session.fetch_level("OFFICEID", str(officeid), token, cookie)
        report_md = session.debug_report(property_name)
    except Exception as exc:
        if _is_auth_error(exc):
            return _credentials_required(server)
        return {"error": str(exc), "code": "api_error"}

    value_found = property_name in (session._defaults or {})
    return {
        "property": property_name,
        "buid": buid,
        "server": server,
        "value_found": value_found,
        "report_markdown": report_md,
    }
