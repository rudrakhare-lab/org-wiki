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
        "Check whether a BUID is accessible on a given server (.com or "
        ".in). Returns found:bool plus the list of accessible BUIDs for "
        "that server. Use this FIRST whenever the server is ambiguous "
        "and the user has named a specific BUID — a BUID may exist on "
        ".com but not .in (or vice versa), and wrong-server queries "
        "silently return empty results that look like 'no config set'.\n\n"
        "Strong signal interpretation: found=false ALMOST ALWAYS means "
        "the wrong server was chosen, not that the BUID doesn't exist. "
        "Try the other server before telling the user the BUID is "
        "invalid.\n\n"
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
        "(DEFAULT → BUID → OFFICEID → ROOMID/ROLE). "
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
                "enum": ["OFFICEID", "ROOMID", "ROLE"],
                "description": (
                    "Optional sub-BUID level. Omit to fetch BUID-level configs. "
                    "Use OFFICEID for office overrides, ROOMID for meeting-room overrides, "
                    "ROLE for PROJECT-MANAGEMENT-SERVICE role overrides."
                ),
            },
            "value": {
                "type": "string",
                "description": (
                    "The criteria value (e.g. an OFFICEID string, ROOMID string, "
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


# ── Handlers ──────────────────────────────────────────────────────────────────

def _pms_default_properties_handler(inp: dict) -> dict:
    service = str(inp.get("service", "")).strip().upper()
    server = str(inp.get("server", "com")).strip().lower()

    token, cookie = _get_tokens(server)
    if not token:
        return _credentials_required(server)

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

    if not buid:
        return {"error": "buid is required", "code": "missing_input"}

    token, cookie = _get_tokens(server)
    if not token:
        return _credentials_required(server)

    try:
        from pms_session import Session
    except ImportError as exc:
        return {"error": f"PMS session not available: {exc}", "code": "import_error"}

    session = Session.load(service, buid, server)
    try:
        raw = session.fetch_level(criteria, value, token, cookie)
    except Exception as exc:
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
    if not token:
        return _credentials_required(server)

    try:
        from pms_session import Session
    except ImportError as exc:
        return {"error": f"PMS session not available: {exc}", "code": "import_error"}

    session = Session.load(service, buid, server)
    try:
        offices = session.fetch_offices(token, cookie) or {}
    except Exception as exc:
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
    if not token:
        return _credentials_required(server)

    try:
        from pms_session import Session
    except ImportError as exc:
        return {"error": f"PMS session not available: {exc}", "code": "import_error"}

    session = Session.load(service, buid, server)
    try:
        values = session.fetch_criteria_values(criteria, token, cookie) or []
    except Exception as exc:
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
    if not token:
        return _credentials_required(server)

    try:
        from pms_session import Session
    except ImportError as exc:
        return {"error": f"PMS session not available: {exc}", "code": "import_error"}

    session = Session.load(service, buid, server)
    try:
        roles = session.fetch_roles(token, cookie)
    except Exception as exc:
        return {"error": str(exc), "code": "api_error"}

    accessible = _extract_accessible_buids(roles)
    if accessible is None:
        return {
            "service": service,
            "server": server,
            "buid": buid,
            "found": False,
            "code": "shape_unknown",
            "raw_response": roles,
            "message": (
                "fetch_roles returned an unfamiliar shape — cannot determine "
                "accessibility automatically. Inspect raw_response."
            ),
        }

    # Real PMS returns isAllBuids=true for read-only users with cross-tenant
    # access. In that case the `buids` list is informational (named tenants)
    # rather than gating access — the user can query any BUID even if not
    # explicitly listed.
    is_all_buids = bool(roles.get("isAllBuids")) if isinstance(roles, dict) else False
    in_list = buid in accessible
    other = "in" if server == "com" else "com"

    if in_list:
        found = True
        message = f"BUID '{buid}' is in the .{server} directory and accessible."
    elif is_all_buids:
        # Soft warning: account has cross-tenant access, but the BUID isn't
        # in the named tenant list. Often valid (queries can still succeed);
        # sometimes a typo. Suggest verifying via a config query.
        found = True
        message = (
            f"BUID '{buid}' is NOT in the .{server} directory listing, but "
            f"the account has isAllBuids=true (cross-tenant read access), so "
            f"the BUID may still be queryable. Confirm with pms_diagnose_property "
            f"for a known property; if that errors, the BUID likely lives on "
            f".{other} instead."
        )
    else:
        found = False
        message = (
            f"⚠️ BUID '{buid}' is NOT in the .{server} directory listing AND "
            f"the account does not have cross-tenant access (isAllBuids=false). "
            f"This usually means the wrong server — try .{other} before "
            f"concluding the BUID is invalid."
        )

    return {
        "service": service,
        "server": server,
        "buid": buid,
        "found": found,
        "in_directory": in_list,
        "is_all_buids": is_all_buids,
        "accessible_count": len(accessible),
        # Cap echoed list to avoid bloating the context — model can re-call if needed
        "accessible_buids_sample": accessible[:20],
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

    token, cookie = _get_tokens(server)
    if not token:
        return _credentials_required(server)

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
        return {"error": str(exc), "code": "api_error"}

    value_found = property_name in (session._defaults or {})
    return {
        "property": property_name,
        "buid": buid,
        "server": server,
        "value_found": value_found,
        "report_markdown": report_md,
    }
