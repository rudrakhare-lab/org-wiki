#!/usr/bin/env python3
"""
PMS live config debugger — CLI.

Wraps pms_session.Session for interactive debugging of config issues at
BUID, OFFICEID, ROOMID, or ROLE level.

Credentials are read from env vars:
  PMS_TOKEN   required — bearer token without the "Bearer " prefix
  PMS_COOKIE  optional — CMS session cookie

Credentials — export once per server, then switch freely:
  export PMS_TOKEN_COM="eyJhbGci..."   # .com bearer token (global/international)
  export PMS_TOKEN_IN="eyJhbGci..."    # .in  bearer token (India-region)
  export PMS_COOKIE_COM="JSESSION..."  # optional .com cookie
  export PMS_COOKIE_IN="JSESSION..."   # optional .in  cookie

  # Fallback: if PMS_TOKEN_COM / PMS_TOKEN_IN not set, PMS_TOKEN is used for both servers.

Quick start (.com server — global/international clients, default):
  python scripts/pms_debug.py --service VISITOR --buid genpactindia-GInd init
  python scripts/pms_debug.py --service VISITOR --buid genpactindia-GInd fetch
  python scripts/pms_debug.py --service VISITOR --buid genpactindia-GInd report --property checkinBufferFromKiosk

Quick start (.in server — India-region clients):
  python scripts/pms_debug.py --server in --service VISITOR --buid someIndiaBuid init
  python scripts/pms_debug.py --server in --service VISITOR --buid someIndiaBuid fetch
  python scripts/pms_debug.py --server in --service VISITOR --buid someIndiaBuid report --property checkinBufferFromKiosk

All subcommands work identically on both servers. Sessions are stored separately:
  .com → /tmp/pms_debug_com_{SERVICE}_{BUID}.json
  .in  → /tmp/pms_debug_in_{SERVICE}_{BUID}.json
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Allow running from repo root without installing
sys.path.insert(0, str(Path(__file__).parent))
from pms_session import Session


def _get_creds(server: str = "com") -> tuple[str, str]:
    """
    Resolve bearer token and cookie for the given server.

    Lookup order for token:
      1. PMS_TOKEN_COM / PMS_TOKEN_IN — server-specific
      2. PMS_TOKEN                     — shared fallback
      3. "" (empty)                    — cookie-only auth (.com accepts this)

    Lookup order for cookie:
      1. PMS_COOKIE_COM / PMS_COOKIE_IN — server-specific
      2. PMS_COOKIE                      — shared fallback

    .com server: cookie-only auth is supported (PMS_TOKEN_COM may be empty).
    .in server:  JWT token required in addition to cookie.
    """
    specific_token_var = f"PMS_TOKEN_{server.upper()}"
    specific_cookie_var = f"PMS_COOKIE_{server.upper()}"

    token = os.environ.get(specific_token_var) or os.environ.get("PMS_TOKEN", "")
    cookie = os.environ.get(specific_cookie_var) or os.environ.get("PMS_COOKIE", "")

    # Strip "Bearer " prefix if user accidentally included it
    if token.startswith("Bearer "):
        token = token[len("Bearer "):]

    if not token and not cookie:
        print(
            f"ERROR: No credentials found for server '{server}'.\n"
            f"Set token and/or cookie:\n"
            f"  export {specific_token_var}='eyJhbGci...'      # JWT token\n"
            f"  export {specific_cookie_var}='property-management-service=...'  # session cookie\n"
            f"\n"
            f"Or use the shared fallback:\n"
            f"  export PMS_TOKEN='eyJhbGci...'\n"
            f"  export PMS_COOKIE='property-management-service=...'",
            file=sys.stderr,
        )
        raise SystemExit(2)

    if not token and server == "in":
        print(
            f"WARNING: PMS_TOKEN_IN is not set. The .in server requires a JWT bearer token.\n"
            f"  export PMS_TOKEN_IN='eyJhbGci...'  (from cmsapp.moveinsync.in DevTools → Authorization header)",
            file=sys.stderr,
        )

    return token, cookie


# ── Subcommand handlers ───────────────────────────────────────────────────────

def cmd_init(args: argparse.Namespace) -> int:
    token, cookie = _get_creds(args.server)
    session = Session.load(args.service, args.buid, args.server)
    print(f"Server:  {session.server} ({session.base_url})")
    print(f"Session: {session.path}")

    print(f"Fetching default property metadata for {args.service}...")
    count = session.fetch_defaults(token, cookie)
    print(f"  Loaded {count} default properties.")

    # Always verify that the BUID is accessible on the declared server.
    # This catches the common mistake of using a .com BUID with --server in (or vice versa).
    print(f"Verifying BUID '{args.buid}' is accessible on '{args.server}' server...")
    try:
        roles = session.fetch_roles(token, cookie)
        raw_buids = roles.get("buids", []) if isinstance(roles, dict) else []
        # buids may be a list of strings or a list of dicts — normalise to strings
        if raw_buids and isinstance(raw_buids[0], dict):
            accessible = [b.get("buid", b.get("id", str(b))) for b in raw_buids]
        else:
            accessible = [str(b) for b in raw_buids]
        if accessible and args.buid not in accessible:
            print(
                f"\n⚠️  BUID '{args.buid}' is NOT in the accessible BUID list for the '{args.server}' server.",
                file=sys.stderr,
            )
            print(
                f"   This BUID may belong to the '{('in' if args.server == 'com' else 'com')}' server instead.",
                file=sys.stderr,
            )
            print(
                f"   Accessible BUIDs on '{args.server}': {', '.join(accessible[:5])}"
                + (" ..." if len(accessible) > 5 else ""),
                file=sys.stderr,
            )
            print(
                f"\n   If you're sure this is the right server, the BUID may exist but not be\n"
                f"   visible with your current credentials. Try the other server:\n"
                f"     python scripts/pms_debug.py --server {'in' if args.server == 'com' else 'com'} "
                f"--service {args.service} --buid {args.buid} init",
                file=sys.stderr,
            )
        elif accessible:
            print(f"  ✅ BUID '{args.buid}' confirmed on '{args.server}' server.")
        else:
            print(f"  Role fetched but BUID list was empty — cannot verify. Proceed with caution.")
        if args.roles:
            print(f"  Role: {roles.get('role')} | Accessible BUIDs: {len(accessible)}")
    except RuntimeError as exc:
        print(f"  ⚠️  Could not verify BUID: {exc}", file=sys.stderr)
        print("  Proceeding without BUID verification.", file=sys.stderr)

    return 0


def _resolve_criteria_value(
    session: Session,
    criteria: str,
    raw_value: str,
) -> str:
    """
    Resolve --value to a real ID.
    If raw_value looks like an ID already (starts with 'LO' for offices, or
    matches a known ROLE value), return it unchanged.
    Otherwise treat it as a human name and look it up in the cached mapping.
    Raises SystemExit(2) with a helpful message if resolution fails.
    """
    crit = criteria.upper()
    if crit == "OFFICEID":
        try:
            return session.resolve_office(raw_value)
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            raise SystemExit(2)
    if crit in ("ROOMID", "ROOM_ID"):
        try:
            return session.resolve_room(raw_value)
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            raise SystemExit(2)
    return raw_value  # ROLE and others: pass through unchanged


def cmd_list_criteria(args: argparse.Namespace) -> int:
    token, cookie = _get_creds(args.server)
    session = Session.load(args.service, args.buid, args.server)
    crit = args.criteria.upper()
    print(f"Fetching {crit} values for service {args.service}...")
    values = session.fetch_criteria_values(crit, token, cookie)
    if not values:
        print("  No values returned (no overrides exist for this criteria).")
        return 0
    print(f"  Found {len(values)} values:")
    for v in values:
        # Annotate with human name if cached
        if crit == "OFFICEID":
            label = session._offices.get(v, "")
        elif crit in ("ROOMID", "ROOM_ID"):
            label = session._rooms.get(v, "")
        else:
            label = ""
        suffix = f"  ({label})" if label else ""
        print(f"    {v}{suffix}")
    return 0


def cmd_fetch(args: argparse.Namespace) -> int:
    token, cookie = _get_creds(args.server)
    session = Session.load(args.service, args.buid, args.server)

    criteria = args.criteria.upper() if args.criteria else None
    raw_value = args.value

    if criteria and not raw_value:
        print("ERROR: --value required when --criteria is set.", file=sys.stderr)
        return 2

    # Resolve name → ID if user gave a human name instead of a raw ID
    value = _resolve_criteria_value(session, criteria, raw_value) if criteria and raw_value else raw_value

    if criteria and value and value != raw_value:
        print(f"  Resolved '{raw_value}' → {value}")

    level_desc = f"{criteria}::{value}" if criteria else "BUID"
    print(f"Fetching {args.service} configs at level [{level_desc}] for BUID [{args.buid}]...")
    raw = session.fetch_level(criteria, value, token, cookie)
    count = len(raw)
    if count == 0:
        print("  No overrides found at this level (all properties use defaults or a parent level's value).")
    else:
        print(f"  Got {count} overridden properties at this level.")
        if args.verbose:
            for item in raw:
                print(f"    {item['propertyName']}: {item['propertyValue']}")
    return 0


def cmd_compare(args: argparse.Namespace) -> int:
    session = Session.load(args.service, args.buid, args.server)
    if not session._defaults and not session._levels:
        print(
            "Session is empty. Run init and fetch first:\n"
            f"  python scripts/pms_debug.py --server {args.server} --service {args.service} --buid {args.buid} init\n"
            f"  python scripts/pms_debug.py --server {args.server} --service {args.service} --buid {args.buid} fetch",
            file=sys.stderr,
        )
        return 1
    print(session.compare_property(args.property))
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    session = Session.load(args.service, args.buid, args.server)
    if not session._defaults and not session._levels:
        print(
            "Session is empty. Run init and fetch first:\n"
            f"  python scripts/pms_debug.py --server {args.server} --service {args.service} --buid {args.buid} init\n"
            f"  python scripts/pms_debug.py --server {args.server} --service {args.service} --buid {args.buid} fetch",
            file=sys.stderr,
        )
        return 1
    print(session.debug_report(args.property))
    return 0


def cmd_diagnose(args: argparse.Namespace) -> int:
    token, cookie = _get_creds(args.server)
    session = Session.load(args.service, args.buid, args.server)
    print(f"Diagnosing `{args.property}` — looking for value `{args.observed}`")
    print(f"Service: {args.service} | BUID: {args.buid}\n")
    print(session.diagnose(args.property, args.observed, token, cookie))
    return 0


def cmd_list_rooms(args: argparse.Namespace) -> int:
    token, cookie = _get_creds(args.server)
    session = Session.load(args.service, args.buid, args.server)
    print(f"Fetching rooms for BUID [{args.buid}]...")
    rooms = session.fetch_rooms(token, cookie)
    if not rooms:
        print("  No rooms returned. The rooms API endpoint may need to be confirmed (see fetch_rooms() TODO).")
        return 0
    print(f"  Found {len(rooms)} rooms:")
    for roomid, name in rooms.items():
        print(f"    {name}")
        print(f"      ROOMID: {roomid}")
    return 0


def cmd_list_offices(args: argparse.Namespace) -> int:
    token, cookie = _get_creds(args.server)
    session = Session.load(args.service, args.buid, args.server)
    print(f"Fetching offices for BUID [{args.buid}]...")
    offices = session.fetch_offices(token, cookie)
    if not offices:
        print("  No offices returned. Verify the BUID is correct.")
        return 0
    print(f"  Found {len(offices)} offices:")
    for officeid, name in offices.items():
        print(f"    {name}")
        print(f"      OFFICEID: {officeid}")
    return 0


def cmd_show_session(args: argparse.Namespace) -> int:
    session = Session.load(args.service, args.buid, args.server)
    print(session.summary())
    return 0


def cmd_clear_session(args: argparse.Namespace) -> int:
    session = Session.load(args.service, args.buid, args.server)
    if session.path.exists():
        session.path.unlink()
        print(f"Deleted session: {session.path}")
    else:
        print("No session file found.")
    return 0


# ── Argument parser ───────────────────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--server", default="com", choices=["com", "in"],
        help="Which WorkInSync server to query: 'com' (global, default) or 'in' (India region)",
    )
    parser.add_argument(
        "--service", required=True,
        help="PMS service ID (VISITOR, BOOKING-RULE-ENGINE, MEETING_ROOMS, PROJECT-MANAGEMENT-SERVICE, ...)",
    )
    parser.add_argument("--buid", required=True, help="Business Unit ID (e.g. genpactindia-GInd)")

    sub = parser.add_subparsers(dest="command", required=True)

    # init
    p = sub.add_parser("init", help="Create/reload session; fetch default property metadata")
    p.add_argument("--roles", action="store_true", help="Also fetch roles + accessible BUIDs")
    p.set_defaults(func=cmd_init)

    # list-criteria
    p = sub.add_parser(
        "list-criteria",
        help="List configured criteria values (OFFICEID, ROOMID, or ROLE)",
    )
    p.add_argument("criteria", help="Criteria type: OFFICEID, ROOMID, or ROLE")
    p.set_defaults(func=cmd_list_criteria)

    # fetch
    p = sub.add_parser("fetch", help="Fetch configs at one level and cache in session")
    p.add_argument(
        "--criteria",
        help="Omit for BUID level. Use OFFICEID/ROOMID/ROLE for specific level.",
    )
    p.add_argument("--value", help="Criteria value (required when --criteria is set)")
    p.add_argument("-v", "--verbose", action="store_true", help="Print all overridden properties")
    p.set_defaults(func=cmd_fetch)

    # compare
    p = sub.add_parser(
        "compare",
        help="Compare a property value across all fetched levels",
    )
    p.add_argument("--property", required=True, help="Exact property name (case-sensitive)")
    p.set_defaults(func=cmd_compare)

    # report
    p = sub.add_parser(
        "report",
        help="Full debug report: comparison table + effective value + fix guidance",
    )
    p.add_argument("--property", required=True, help="Exact property name (case-sensitive)")
    p.set_defaults(func=cmd_report)

    # diagnose
    p = sub.add_parser(
        "diagnose",
        help="Auto-detect which level is causing a bug — no need to know the level upfront",
    )
    p.add_argument("--property", required=True, help="Property name to investigate (case-sensitive)")
    p.add_argument(
        "--observed", required=True,
        help="The WRONG value you are currently observing (e.g. 3 if SafeReach fires after 3 min)",
    )
    p.set_defaults(func=cmd_diagnose)

    # list-offices
    p = sub.add_parser(
        "list-offices",
        help="Fetch and cache all offices for this BUID (OFFICEID → name mapping)",
    )
    p.set_defaults(func=cmd_list_offices)

    # list-rooms
    p = sub.add_parser(
        "list-rooms",
        help="Fetch and cache all rooms for this BUID (ROOMID → name mapping)",
    )
    p.set_defaults(func=cmd_list_rooms)

    # show-session
    p = sub.add_parser("show-session", help="Print current session state (no API call)")
    p.set_defaults(func=cmd_show_session)

    # clear-session
    p = sub.add_parser("clear-session", help="Delete cached session file")
    p.set_defaults(func=cmd_clear_session)

    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    try:
        return args.func(args)
    except RuntimeError as exc:
        print(f"API error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
