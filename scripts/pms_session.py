#!/usr/bin/env python3
"""
PMS live config debug session.

Fetches and caches multi-level PMS configs (DEFAULT → BUID → OFFICEID → ROOMID/ROLE)
for one service+buid pair, then lets you compare values and resolve which level is
causing a bug.

Session files live in /tmp/ and are never committed — they hold customer data.

Usage (from other scripts):
    from pms_session import Session

    # .com server (global/international clients) — default
    session = Session.load("VISITOR", "genpactindia-GInd", server="com")

    # .in server (India-region clients)
    session = Session.load("VISITOR", "somebuid-IN", server="in")

    session.fetch_defaults(token)
    session.fetch_level(None, None, token)                          # BUID level
    session.fetch_level("OFFICEID", "LO...-000001", token)         # office level
    print(session.compare_property("checkinBufferFromKiosk"))
    print(session.debug_report("checkinBufferFromKiosk"))
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error as urlerror, request as urlrequest

# Per-server URL configuration.
# Use --server com (default) for global/international clients.
# Use --server in for India-region clients.
# Override individual URLs via env vars PMS_BASE_URL / PMS_BASE_URL_IN if the
# default domain differs from what is documented here.
SERVERS: dict[str, dict[str, str]] = {
    "com": {
        "base_url": "https://cmsapp.moveinsync.com/propmanagement/api",
        "cms_origin": "https://cmsapp.moveinsync.com",
        "mis_security_url": "https://mis-security.moveinsync.com/mis-security-guard",
    },
    "in": {
        "base_url": "https://cmsapp.moveinsync.in/propmanagement/api",
        "cms_origin": "https://cmsapp.moveinsync.in",
        "mis_security_url": "https://mis-security.moveinsync.in/mis-security-guard",
    },
}

# Backward-compatible aliases (resolve to .com server)
BASE_URL = SERVERS["com"]["base_url"]
MIS_SECURITY_URL = SERVERS["com"]["mis_security_url"]

SESSION_DIR = Path("/tmp")

# Known ROLE values for PROJECT-MANAGEMENT-SERVICE
PMS_ROLES = [
    "employee",
    "RECEPTIONIST",
    "cd210644-153b-4a57-aa48-5e7213a5da66",
]

# Criteria that apply only to specific services
SERVICE_EXTRA_CRITERIA: dict[str, list[str]] = {
    "MEETING-ROOM": ["ROOM_ID"],
    "MEETING-ROOMS": ["ROOM_ID"],
    "MEETING_ROOMS": ["ROOM_ID"],
    "PROJECT-MANAGEMENT-SERVICE": ["ROLE"],
}

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I
)


# ── HTTP helper ──────────────────────────────────────────────────────────────

def _http(
    *,
    method: str,
    url: str,
    service: str | None = None,
    token: str = "",
    cookie: str = "",
    body: dict[str, Any] | None = None,
    cms_origin: str = SERVERS["com"]["cms_origin"],
) -> Any:
    headers: dict[str, str] = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if service:
        headers["ServiceId"] = service
        headers["Referer"] = f"{cms_origin}/property-dashboard/bu-properties"
        headers["Origin"] = cms_origin
    if cookie:
        headers["Cookie"] = cookie
    data = json.dumps(body).encode() if body is not None else None
    req = urlrequest.Request(url, data=data, headers=headers, method=method)
    try:
        with urlrequest.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw.strip() else None
    except urlerror.HTTPError as exc:
        raise RuntimeError(f"HTTP {exc.code}: {exc.read().decode(errors='replace')}") from exc
    except urlerror.URLError as exc:
        raise RuntimeError(f"Network error: {exc.reason}") from exc


# ── Session ──────────────────────────────────────────────────────────────────

class Session:
    """
    One debug session scoped to a single (service, buid) pair.

    Internal state:
      _defaults   dict[name → full property metadata from default-properties]
      _levels     dict[level_key → {fetched_at, configs: {name → value}}]
                  level_key examples: "BUID", "OFFICEID::LO...", "ROOMID::...", "ROLE::employee"
      _roles      raw response from /user/service/{service}/roles
      _criteria   dict[criteria → list of values]
    """

    def __init__(self, service: str, buid: str, server: str = "com") -> None:
        self.service = service.upper()
        self.buid = buid
        self.server = server.lower()
        srv = SERVERS.get(self.server, SERVERS["com"])
        self.base_url = srv["base_url"]
        self.cms_origin = srv["cms_origin"]
        self.mis_security_url = srv["mis_security_url"]
        self._defaults: dict[str, dict] = {}
        self._levels: dict[str, dict] = {}
        self._roles: dict | None = None
        self._criteria: dict[str, list] = {}
        self._offices: dict[str, str] = {}  # OFFICEID → "Name (City, Country)"
        self._rooms: dict[str, str] = {}    # ROOMID   → "Room Name (Office)"

    # ── Persistence ──────────────────────────────────────────────────────────

    @property
    def path(self) -> Path:
        safe = re.sub(r"[^a-zA-Z0-9_-]", "_", self.buid)
        return SESSION_DIR / f"pms_debug_{self.server}_{self.service}_{safe}.json"

    def save(self) -> None:
        payload = {
            "service": self.service,
            "buid": self.buid,
            "server": self.server,
            "base_url": self.base_url,
            "saved_at": _now(),
            "defaults": self._defaults,
            "levels": self._levels,
            "roles": self._roles,
            "criteria": self._criteria,
            "offices": self._offices,
            "rooms": self._rooms,
        }
        self.path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")

    @classmethod
    def load(cls, service: str, buid: str, server: str = "com") -> "Session":
        s = cls(service, buid, server)
        if s.path.exists():
            try:
                data = json.loads(s.path.read_text())
                s._defaults = data.get("defaults", {})
                s._levels = data.get("levels", {})
                s._roles = data.get("roles")
                s._criteria = data.get("criteria", {})
                s._offices = data.get("offices", {})
                s._rooms = data.get("rooms", {})
            except (json.JSONDecodeError, KeyError):
                pass  # corrupted session — start fresh
        return s

    # ── API calls ─────────────────────────────────────────────────────────────

    def fetch_defaults(self, token: str, cookie: str = "") -> int:
        """
        Fetch default property metadata for the service.
        Returns the number of properties loaded.
        This gives you: propertyValue (default), dataType, criteriaPriorityList, definition.
        """
        url = f"{self.base_url}/{self.service}/default-properties/details"
        raw: list[dict] = _http(method="GET", url=url, service=self.service, token=token, cookie=cookie, cms_origin=self.cms_origin)
        self._defaults = {item["propertyName"]: item for item in raw}
        self.save()
        return len(self._defaults)

    def fetch_roles(self, token: str, cookie: str = "") -> dict:
        """Fetch the user's role + list of accessible BUIDs for this service."""
        url = f"{self.base_url}/user/service/{self.service}/roles"
        self._roles = _http(method="GET", url=url, service=self.service, token=token, cookie=cookie, cms_origin=self.cms_origin)
        self.save()
        return self._roles

    def fetch_criteria_values(self, criteria: str, token: str, cookie: str = "") -> list:
        """
        List all configured criteria values (e.g. all OFFICEIDs that have overrides).
        criteria: "OFFICEID", "ROOM_ID", or "ROLE"
        """
        url = f"{self.base_url}/{self.service}/criteria-value-list/{criteria}"
        values: list = _http(method="GET", url=url, service=self.service, token=token, cookie=cookie, cms_origin=self.cms_origin)
        self._criteria[criteria] = values or []
        self.save()
        return self._criteria[criteria]

    def fetch_offices(self, token: str = "", cookie: str = "") -> dict[str, str]:
        """
        Fetch all offices for this BUID from the MIS-security API.
        Builds and caches an OFFICEID → "Name (City, Country)" mapping.

        API: GET /premise/offices/{buid}?premiseType=2
        The OFFICEID is read from buIdOfficeGuid[buid] in each record.
        """
        url = f"{self.mis_security_url}/premise/offices/{self.buid}?premiseType=2"
        offices: list[dict] = _http(method="GET", url=url, token=token, cookie=cookie)
        self._offices = {}
        for office in offices or []:
            guid_map = office.get("buIdOfficeGuid", {})
            officeid = guid_map.get(self.buid)
            if not officeid:
                continue
            name = office.get("premiseName") or ""
            city = office.get("city") or ""
            country = office.get("country") or ""
            location = ", ".join(filter(None, [city, country]))
            self._offices[officeid] = f"{name} ({location})" if location else name
        self.save()
        return self._offices

    def office_name(self, officeid: str) -> str:
        """Return human-readable label for an OFFICEID, or the raw ID if not yet mapped."""
        return self._offices.get(officeid, officeid)

    def find_offices(self, query: str) -> list[tuple[str, str]]:
        """
        Case-insensitive substring search across cached office names.
        Returns list of (officeid, full_name) for every office whose name contains query.
        Returns empty list if offices haven't been fetched yet.
        """
        q = query.strip().lower()
        return [(oid, name) for oid, name in self._offices.items() if q in name.lower()]

    def resolve_office(self, query: str) -> str:
        """
        Resolve an office name (or partial name) to its OFFICEID.
        If query already looks like an OFFICEID (starts with 'LO'), return as-is.
        Raises ValueError if no match or ambiguous (multiple matches).
        """
        if query.upper().startswith("LO"):
            return query  # already an ID
        matches = self.find_offices(query)
        if not matches:
            hint = "Run list-offices first to cache the mapping." if not self._offices else \
                   f"Known offices: {', '.join(self._offices.values())}"
            raise ValueError(f"No office matching '{query}'. {hint}")
        if len(matches) > 1:
            choices = "\n  ".join(f"{name}  →  {oid}" for oid, name in matches)
            raise ValueError(f"Ambiguous name '{query}' — {len(matches)} matches:\n  {choices}")
        return matches[0][0]

    # ── Rooms ─────────────────────────────────────────────────────────────────

    def fetch_rooms(self, token: str = "", cookie: str = "") -> dict[str, str]:
        """
        Fetch all ROOMIDs that have config overrides via PMS criteria-value-list.

        API: GET /{service}/criteria-value-list/ROOM_ID
        Returns a flat list of room UUIDs. Junk entries "null" and "Default" are filtered.
        Room names are not available in bulk — they are extracted lazily when
        fetch_level("ROOM_ID", roomid, ...) is called and the room_name property
        is present in the response.
        """
        ids = self.fetch_criteria_values("ROOM_ID", token, cookie)
        for rid in ids:
            if rid and rid not in ("null", "Default") and rid not in self._rooms:
                self._rooms[rid] = ""
        self.save()
        return self._rooms

    def room_name(self, roomid: str) -> str:
        """Return human-readable label for a ROOMID, or the raw ID if not yet mapped."""
        return self._rooms.get(roomid, roomid)

    def find_rooms(self, query: str) -> list[tuple[str, str]]:
        """
        Case-insensitive substring search across cached room names.
        Returns list of (roomid, full_name).
        """
        q = query.strip().lower()
        return [(rid, name) for rid, name in self._rooms.items() if q in name.lower()]

    def resolve_room(self, query: str) -> str:
        """
        Resolve a room name (or partial name) to its ROOMID.
        If query is already a UUID, return it unchanged.
        Raises ValueError if no match or ambiguous.
        """
        if _UUID_RE.match(query):
            return query  # already a UUID
        matches = self.find_rooms(query)
        if not matches:
            named = [n for n in self._rooms.values() if n]
            hint = "Run list-rooms first to cache the mapping." if not self._rooms else \
                   (f"Known rooms: {', '.join(named)}" if named else
                    "Room names not yet loaded — run fetch for each room to populate names.")
            raise ValueError(f"No room matching '{query}'. {hint}")
        if len(matches) > 1:
            choices = "\n  ".join(f"{name}  →  {rid}" for rid, name in matches)
            raise ValueError(f"Ambiguous name '{query}' — {len(matches)} matches:\n  {choices}")
        return matches[0][0]

    def fetch_level(
        self,
        criteria: str | None,
        value: str | None,
        token: str,
        cookie: str = "",
    ) -> list[dict]:
        """
        Fetch configs overridden at a specific level.

        To fetch BUID level:           fetch_level(None, None, token)
        To fetch office level:         fetch_level("OFFICEID", "<officeid>", token)
        To fetch room level:           fetch_level("ROOM_ID", "<roomid>", token)
        To fetch role level (PMS):     fetch_level("ROLE", "employee", token)

        Returns the raw list from the API. Caches in session.
        """
        body: dict[str, Any] = {"BUID": self.buid}
        if criteria and value:
            body[criteria.upper()] = value
            level_key = f"{criteria.upper()}::{value}"
        else:
            level_key = "BUID"

        url = f"{self.base_url}/{self.service}/properties/v2"
        raw: list[dict] = _http(method="POST", url=url, service=self.service, token=token, cookie=cookie, body=body, cms_origin=self.cms_origin)

        self._levels[level_key] = {
            "fetched_at": _now(),
            "configs": {item["propertyName"]: item["propertyValue"] for item in raw},
        }
        # Lazily extract room name from the room_name property when available
        if criteria and criteria.upper() == "ROOM_ID" and value:
            room_name_val = self._levels[level_key]["configs"].get("room_name", "")
            if room_name_val and isinstance(room_name_val, str) and room_name_val.strip():
                self._rooms[value] = room_name_val.strip()
        self.save()
        return raw

    # ── Analysis ──────────────────────────────────────────────────────────────

    def compare_property(self, name: str) -> str:
        """
        Return a markdown table showing the value of one property at every fetched level.
        Also shows the effective (winning) value and which level provides it.
        """
        meta = self._defaults.get(name, {})
        default_val = meta.get("propertyValue", "⚠ run fetch_defaults() first")

        rows: list[tuple[str, str, str]] = []
        rows.append(("DEFAULT", _jval(default_val), "–"))

        # Sort levels: BUID first, then by criteria priority
        sorted_levels = _sorted_levels(self._levels, meta.get("criteriaPriorityList", []))
        for level_key in sorted_levels:
            level_data = self._levels[level_key]
            val = level_data["configs"].get(name)
            ts = level_data.get("fetched_at", "")[:19]
            display_key = _level_label(level_key, self._offices, self._rooms)
            if val is None:
                rows.append((display_key, "*(not overridden at this level)*", ts))
            else:
                rows.append((display_key, _jval(val), ts))

        lines = [
            f"## `{name}` — level comparison",
            "",
            f"**Type:** `{meta.get('propertyDataType', '?')}`  "
            f"**Customizable:** {meta.get('customizable', '?')}  "
            f"**Cloneable:** {meta.get('cloneable', '?')}",
            f"**Definition:** {meta.get('propertyDefinition') or '*(not documented)*'}",
            "",
            "| Level | Value | Fetched at |",
            "|-------|-------|------------|",
        ]
        for level, val, ts in rows:
            lines.append(f"| `{level}` | {val} | {ts} |")

        # Resolution order
        criteria_list = meta.get("criteriaPriorityList", [])
        if criteria_list:
            ordered = sorted(criteria_list, key=lambda x: x["priority"])
            resolution = " → ".join(f"`{c['criteria']}`" for c in ordered) + " → `DEFAULT`"
            lines += ["", f"**Resolution order (most specific first):** {resolution}"]

        effective, source = self._resolve(name)
        lines += [
            "",
            f"**Effective value:** `{_jval(effective)}`  **Winning level:** `{source}`",
        ]
        return "\n".join(lines)

    def debug_report(self, name: str) -> str:
        """Full report: comparison table + fix guidance."""
        if not self._defaults:
            return (
                f"⚠ Defaults not loaded. Run `fetch_defaults()` first so the report "
                f"can include metadata, resolution order, and definitions."
            )
        meta = self._defaults.get(name)
        if meta is None:
            candidates = [k for k in self._defaults if name.lower() in k.lower()]
            hint = f" Did you mean: {', '.join(candidates[:5])}?" if candidates else ""
            return f"Property `{name}` not found in loaded defaults.{hint}"

        comparison = self.compare_property(name)
        effective, source_level = self._resolve(name)
        fix = _fix_guidance(name, source_level, effective, self.buid, self.service, self._offices, self._rooms)
        return f"{comparison}\n\n{fix}"

    def _resolve(self, name: str) -> tuple[Any, str]:
        """
        Compute the effective property value using criteriaPriorityList ordering.
        Returns (value, level_key_that_provided_it).
        """
        meta = self._defaults.get(name, {})
        criteria_list = sorted(
            meta.get("criteriaPriorityList", []),
            key=lambda x: x["priority"],
        )
        for c in criteria_list:
            cname = c["criteria"]
            if cname == "BUID":
                val = self._levels.get("BUID", {}).get("configs", {}).get(name)
                if val is not None:
                    return val, "BUID"
            else:
                for lk, lv in self._levels.items():
                    if lk.startswith(f"{cname}::"):
                        val = lv.get("configs", {}).get(name)
                        if val is not None:
                            return val, lk
        return meta.get("propertyValue"), "DEFAULT"

    def diagnose(
        self,
        name: str,
        reported_value: Any,
        token: str,
        cookie: str = "",
    ) -> str:
        """
        Auto-detect which level is causing a config bug without requiring the
        user to know the level upfront.

        Algorithm:
          1. Ensure BUID level is fetched.
          2. Compare BUID value to expected (reported_value from user).
          3. If BUID already has the wrong value → bug is at BUID level.
          4. If BUID value is correct → a more specific level (OFFICEID/ROOMID/ROLE)
             must be overriding it. Fetch all known criteria values and find which
             specific ID has the wrong value.

        reported_value: what the system is currently doing (the wrong value the user
                        observes), NOT what they expect. e.g. if trigger fires after
                        3 min and should be 360, pass reported_value=3.
        """
        if not self._defaults:
            self.fetch_defaults(token, cookie)

        meta = self._defaults.get(name)
        if meta is None:
            candidates = [k for k in self._defaults if name.lower() in k.lower()]
            hint = f" Did you mean: {', '.join(candidates[:5])}?" if candidates else ""
            return f"Property `{name}` not found.{hint}"

        lines = [
            f"## Diagnosing `{name}` — looking for value `{_jval(reported_value)}`",
            f"**Definition:** {meta.get('propertyDefinition', '(none)')}",
            "",
        ]

        # Step 1: ensure BUID level is loaded
        if "BUID" not in self._levels:
            lines.append("Fetching BUID level...")
            self.fetch_level(None, None, token, cookie)

        buid_val = self._levels["BUID"]["configs"].get(name)
        default_val = meta.get("propertyValue")

        lines += [
            f"**DEFAULT:** `{default_val}`",
            f"**BUID level:** `{buid_val}`",
            "",
        ]

        # Step 2: is the bug at BUID level?
        if _values_match(buid_val, reported_value):
            lines += [
                f"✅ BUID value matches the reported (wrong) value `{_jval(reported_value)}`.",
                f"→ **Bug is at BUID level.** The BUID itself has the wrong value.",
                f"→ Fix: update `{name}` at BUID level in CMS for BUID `{self.buid}`.",
            ]
            return "\n".join(lines)

        # Step 3: BUID value is different — a more specific level must be overriding
        lines += [
            f"BUID value `{_jval(buid_val)}` does NOT match reported value `{_jval(reported_value)}`.",
            f"→ BUID level looks correct. A more specific override is responsible.",
            f"→ Fetching all OFFICEID overrides to find the culprit...",
            "",
        ]

        # Find which criteria this property supports (beyond BUID)
        criteria_list = sorted(meta.get("criteriaPriorityList", []), key=lambda x: x["priority"])
        specific_criteria = [c["criteria"] for c in criteria_list if c["criteria"] != "BUID"]

        if not specific_criteria:
            lines.append(
                "⚠ This property only supports BUID-level overrides — no OFFICEID/ROOMID/ROLE. "
                "The BUID value is already correct; the reported behavior may have a different cause."
            )
            return "\n".join(lines)

        culprits: list[tuple[str, Any]] = []

        for criteria in specific_criteria:
            # Fetch the list of IDs that have any override, if not cached
            if criteria not in self._criteria:
                lines.append(f"Fetching list of all {criteria} IDs with overrides...")
                self.fetch_criteria_values(criteria, token, cookie)

            ids = self._criteria.get(criteria, [])
            lines.append(f"Found {len(ids)} {criteria} IDs with overrides. Scanning for `{_jval(reported_value)}`...")
            lines.append("")

            for cid in ids:
                level_key = f"{criteria}::{cid}"
                if level_key not in self._levels:
                    self.fetch_level(criteria, cid, token, cookie)

                val = self._levels[level_key]["configs"].get(name)
                if val is None:
                    continue  # no override for this property at this ID — inherits BUID

                match = _values_match(val, reported_value)
                icon = "🔴" if match else "✅"
                name_label = self._offices.get(cid) or self._rooms.get(cid, "")
                display = f"`{criteria}::{cid}`" + (f" — {name_label}" if name_label else "")
                lines.append(f"  {icon} {display} → `{val}`" + (" ← **CULPRIT**" if match else ""))

                if match:
                    culprits.append((level_key, val))

        lines.append("")
        if culprits:
            lines.append(f"## Root cause found: {len(culprits)} override(s) with the wrong value")
            for level_key, val in culprits:
                ctype, cid = level_key.split("::", 1)
                office_label = self._offices.get(cid) or self._rooms.get(cid, "")
                display_id = f"`{cid}` ({office_label})" if office_label else f"`{cid}`"
                lines += [
                    f"",
                    f"**Level:** `{level_key}`" + (f"  ({office_label})" if office_label else ""),
                    f"**Wrong value here:** `{val}`",
                    f"**Fix:** Update `{name}` at {ctype} {display_id} in CMS → Property Dashboard.",
                    f"  The BUID-level value `{buid_val}` is correct — only this {ctype} override needs fixing.",
                ]
        else:
            lines += [
                "No OFFICEID/ROOMID/ROLE override found matching the reported value.",
                "Possible causes:",
                "  1. The bug is not caused by a PMS config — check application logic.",
                "  2. The office/room/role experiencing the bug was not in the criteria list (no override set).",
                "  3. The reported value was observed before a recent config change took effect (cache lag).",
            ]

        return "\n".join(lines)

    def list_fetched_levels(self) -> list[str]:
        return list(self._levels.keys())

    def summary(self) -> str:
        lines = [
            f"Server:   {self.server} ({self.base_url})",
            f"Service:  {self.service}",
            f"BUID:     {self.buid}",
            f"Session:  {self.path}",
            f"Defaults: {len(self._defaults)} properties",
            f"Offices:  {len(self._offices)} cached" + (
                f" ({', '.join(list(self._offices.values())[:3])}" +
                ("..." if len(self._offices) > 3 else "") + ")"
                if self._offices else " (run list-offices to map OFFICEID → name)"
            ),
            f"Rooms:    {len(self._rooms)} cached" + (
                f" ({', '.join(list(self._rooms.values())[:3])}" +
                ("..." if len(self._rooms) > 3 else "") + ")"
                if self._rooms else " (run list-rooms to map ROOMID → name)"
            ),
            "Levels fetched:",
        ]
        if not self._levels:
            lines.append("  (none — run fetch_level() first)")
        for k, v in self._levels.items():
            count = len(v.get("configs", {}))
            ts = v.get("fetched_at", "?")[:19]
            lines.append(f"  {k}: {count} overrides (at {ts})")
        lines.append("Criteria values cached:")
        if not self._criteria:
            lines.append("  (none — run fetch_criteria_values() first)")
        for k, v in self._criteria.items():
            lines.append(f"  {k}: {len(v)} values")
        return "\n".join(lines)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _values_match(a: Any, b: Any) -> bool:
    """Loose equality: handles int/float/string coercion for user-supplied values."""
    if a == b:
        return True
    try:
        return float(a) == float(b)
    except (TypeError, ValueError):
        return str(a).strip().lower() == str(b).strip().lower()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _jval(v: Any) -> str:
    if isinstance(v, str):
        return f"`{v}`"
    return f"`{json.dumps(v, ensure_ascii=False, separators=(',', ':'))}`"


def _level_label(
    level_key: str,
    offices: dict[str, str],
    rooms: dict[str, str] | None = None,
) -> str:
    """Return a display string for a level key, appending human name when available."""
    if "::" in level_key:
        ctype, cid = level_key.split("::", 1)
        if ctype == "OFFICEID" and cid in offices:
            return f"{level_key}  ({offices[cid]})"
        if ctype in ("ROOMID", "ROOM_ID") and rooms and cid in rooms and rooms[cid]:
            return f"{level_key}  ({rooms[cid]})"
    return level_key


def _sorted_levels(levels: dict, criteria_priority_list: list) -> list[str]:
    """Return level keys ordered from least specific to most specific."""
    priority: dict[str, int] = {}
    for c in criteria_priority_list:
        priority[c["criteria"]] = c["priority"]

    def sort_key(lk: str) -> int:
        if lk == "BUID":
            return priority.get("BUID", 99)
        cname = lk.split("::")[0]
        return priority.get(cname, 50)

    return sorted(levels.keys(), key=sort_key, reverse=True)


def _fix_guidance(
    name: str,
    source_level: str,
    effective: Any,
    buid: str,
    service: str,
    offices: dict[str, str] | None = None,
    rooms: dict[str, str] | None = None,
) -> str:
    lines = ["## Fix guidance", ""]
    val_str = _jval(effective)

    if source_level == "DEFAULT":
        lines += [
            f"The effective value {val_str} is the **system default** — no override exists at any fetched level.",
            "",
            f"**To change it:** set `{name}` at BUID level in CMS → Property Dashboard → BU Properties for `{buid}`.",
            "",
            "If the issue is that the default isn't being picked up at all, check whether a *higher-priority* level "
            "(e.g. an OFFICEID or ROLE override) exists that you haven't fetched yet.",
        ]
    elif source_level == "BUID":
        lines += [
            f"The effective value {val_str} is set at **BUID level** (`{buid}`).",
            "",
            f"**To change it:** update `{name}` at BUID level in CMS → Property Dashboard → BU Properties.",
            "",
            "If only one office should be different, set an **OFFICEID-level override** for that office instead "
            "of changing the BUID-level value (which affects all offices).",
        ]
    else:
        level_type, level_id = source_level.split("::", 1)
        human_label = (offices or {}).get(level_id) or (rooms or {}).get(level_id, "")
        id_display = f"`{level_id}` ({human_label})" if human_label else f"`{level_id}`"
        lines += [
            f"The effective value {val_str} is set at **{level_type} level** ({id_display}).",
            "",
            f"**To change it:** update `{name}` at {level_type} {id_display} in CMS → Property Dashboard.",
        ]
        if level_type == "OFFICEID":
            lines += [
                "",
                "If you also need the fix at BUID level, check whether the BUID-level value needs updating — "
                "the OFFICEID override will always win over BUID level for this office.",
            ]
        elif level_type == "ROLE":
            lines += [
                "",
                f"This is a ROLE-level override — it applies only to users with role `{level_id}` "
                f"within BUID `{buid}`.",
            ]
        elif level_type in ("ROOMID", "ROOM_ID"):
            lines += [
                "",
                f"This is a ROOM-level override — it applies only to room `{level_id}`.",
            ]

    lines += [
        "",
        f"_Service: {service} | BUID: {buid}_",
    ]
    return "\n".join(lines)
