"""
Live Jira ticket fetch — bypasses the local SQLite mirror.

Use sparingly: only when the user names a specific ticket key AND the mirror
returned not_found OR the question implies "current/live/just-filed" status.
The deep_system_prompt instructs the model not to call this speculatively.

Auth: Atlassian Basic auth with email + API token (JIRA_EMAIL + JIRA_API_TOKEN
env vars, same as scripts/jira_sync.py).
"""
from __future__ import annotations

# Inject the OS trust store BEFORE urllib imports its SSL machinery — same
# pattern as scripts/lib/jira_client.py. On corporate networks (e.g.
# MoveInSync) outbound HTTPS is intercepted by a proxy with a self-signed
# root CA; without truststore the call fails with CERTIFICATE_VERIFY_FAILED.
# Best-effort: if truststore isn't installed, fall through.
try:
    import truststore  # type: ignore
    truststore.inject_into_ssl()
except ImportError:  # pragma: no cover
    pass

import base64
import json
import os
import re
import urllib.error
import urllib.request

from backend.config import JIRA_BASE_URL

_KEY_RE = re.compile(r"^[A-Z][A-Z0-9]+-\d+$")

# Fields requested from /rest/api/3/issue/{key}. Kept narrow so the response
# is small and contains only what the model needs to answer status queries.
_FIELDS = "summary,status,priority,resolution,updated,created,assignee,reporter"


JIRA_LIVE_GET_TICKET_SCHEMA: dict = {
    "name": "jira_live_get_ticket",
    "description": (
        "Fetch a Jira ticket's CURRENT state directly from Atlassian Cloud, "
        "bypassing the local mirror. Use ONLY when: (a) jira_get_ticket "
        "returned not_found and the user named a specific key, OR (b) the "
        "user explicitly asks for live/current status. Do not call "
        "speculatively — the local mirror covers 99% of cases.\n\n"
        "Note: priority field returned as Atlassian-native name "
        "(e.g. 'Critical', 'High', 'Medium', 'Low', 'Lowest'), NOT the "
        "P0-P4 codes used by jira_get_ticket from the local mirror. "
        "When comparing across tools, use the mapping: Highest≈P0, "
        "High≈P1, Medium≈P2, Low≈P3, Lowest≈P4.\n\n"
        "Note: status_category 'done' means lifecycle-complete, not "
        "necessarily successful resolution. Check the resolution field — "
        "values like 'Won't Fix', 'Rejected', 'Duplicate' mean closed-"
        "without-fix; only 'Done' / 'Fixed' indicate successful resolution."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "key": {
                "type": "string",
                "description": "Jira ticket key, e.g. TS-12345.",
            },
        },
        "required": ["key"],
    },
}


def _jira_live_get_ticket_handler(inp: dict) -> dict:
    """Live Jira lookup. Returns structured ticket dict or error envelope."""
    key = str(inp.get("key") or "").strip()
    if not _KEY_RE.match(key):
        return {"error": "Invalid key format", "code": "invalid_key_format"}

    if not JIRA_BASE_URL:
        return {"error": "JIRA_BASE_URL not configured", "code": "credentials_required"}

    token = os.getenv("JIRA_API_TOKEN", "").strip()
    email = os.getenv("JIRA_EMAIL", "").strip()
    if not (token and email):
        return {"error": "JIRA credentials not configured", "code": "credentials_required"}

    url = f"{JIRA_BASE_URL}/rest/api/3/issue/{key}?fields={_FIELDS}"
    auth = base64.b64encode(f"{email}:{token}".encode()).decode()
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Basic {auth}",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            rate_limit_remaining = resp.headers.get("X-RateLimit-Remaining")
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return {"error": f"Ticket {key} not found in Jira", "code": "not_found"}
        if exc.code in (401, 403):
            return {"error": f"Jira auth failed ({exc.code})", "code": "auth_failed"}
        return {"error": f"Jira API error {exc.code}", "code": "api_error"}
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return {"error": str(exc), "code": "network_error"}

    f = data.get("fields", {}) or {}
    result: dict = {
        "key": data.get("key"),
        "summary": f.get("summary"),
        "status": (f.get("status") or {}).get("name"),
        "status_category": ((f.get("status") or {}).get("statusCategory") or {}).get("key"),
        "priority": (f.get("priority") or {}).get("name"),
        "resolution": (f.get("resolution") or {}).get("name"),
        "created": f.get("created"),
        "updated": f.get("updated"),
        "assignee": (f.get("assignee") or {}).get("displayName"),
        "reporter": (f.get("reporter") or {}).get("displayName"),
        "source": "live",
    }
    if rate_limit_remaining is not None:
        result["_rate_limit_remaining"] = rate_limit_remaining
    return result
