#!/usr/bin/env python3
"""
Small safe CLI for PMS config dashboard APIs.

Secrets are read from environment variables:
  PMS_TOKEN   required, bearer token without the "Bearer " prefix
  PMS_COOKIE  optional but usually needed for the CMS dashboard session

Examples:
  PMS_TOKEN=... PMS_COOKIE=... python scripts/pms_api_client.py default-properties --service VISITOR

  PMS_TOKEN=... PMS_COOKIE=... python scripts/pms_api_client.py properties \
    --service VISITOR --buid genpactindia-GInd

  PMS_TOKEN=... PMS_COOKIE=... python scripts/pms_api_client.py properties \
    --service VISITOR --buid genpactindia-GInd --criteria OFFICEID --value 000-0000-0000-000000096334

  PMS_TOKEN=... PMS_COOKIE=... python scripts/pms_api_client.py properties \
    --service PROJECT-MANAGEMENT-SERVICE --buid example-BU --criteria ROLE --value employee
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any
from urllib import error as urlerror
from urllib import request as urlrequest


_SERVERS: dict[str, dict[str, str]] = {
    "com": {
        "base_url": "https://cmsapp.moveinsync.com/propmanagement/api",
        "cms_origin": "https://cmsapp.moveinsync.com",
    },
    "in": {
        "base_url": "https://cmsapp.moveinsync.in/propmanagement/api",
        "cms_origin": "https://cmsapp.moveinsync.in",
    },
}
DEFAULT_BASE_URL = _SERVERS["com"]["base_url"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--server", default="com", choices=["com", "in"],
        help="WorkInSync server: 'com' (global, default) or 'in' (India region). Overridden by --base-url.",
    )
    parser.add_argument("--base-url", default=None, help="Override base URL (takes priority over --server)")
    parser.add_argument("--token", default=os.getenv("PMS_TOKEN", ""))
    parser.add_argument("--cookie", default=os.getenv("PMS_COOKIE", ""))
    parser.add_argument("--out", type=Path, help="Optional path to write JSON response")
    parser.add_argument("--dry-run", action="store_true", help="Print request details without calling API")

    sub = parser.add_subparsers(dest="command", required=True)

    default_props = sub.add_parser("default-properties", help="Get service property metadata")
    default_props.add_argument("--service", required=True)

    roles = sub.add_parser("roles", help="Get service access role and available BUIDs")
    roles.add_argument("--service", required=True)

    criteria = sub.add_parser("criteria-values", help="Get allowed values for a criterion")
    criteria.add_argument("--service", required=True)
    criteria.add_argument("--criteria", required=True, help="Example: OFFICEID, ROOMID, ROLE")

    props = sub.add_parser("properties", help="Get current properties for BUID/criterion")
    props.add_argument("--service", required=True)
    props.add_argument("--buid", required=True)
    props.add_argument("--criteria", help="Example: OFFICEID, ROOMID, ROLE")
    props.add_argument("--value", help="Criterion value, e.g. office id, room id, role")

    return parser.parse_args()


def request_json(
    *,
    method: str,
    url: str,
    service: str,
    token: str,
    cookie: str,
    body: dict[str, Any] | None = None,
    dry_run: bool = False,
    cms_origin: str = _SERVERS["com"]["cms_origin"],
) -> Any:
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "ServiceId": service,
        "Referer": f"{cms_origin}/property-dashboard/bu-properties",
        "Origin": cms_origin,
    }
    if cookie:
        headers["Cookie"] = cookie

    encoded = None
    if body is not None:
        encoded = json.dumps(body).encode("utf-8")

    if dry_run:
        sanitized_headers = dict(headers)
        sanitized_headers["Authorization"] = "Bearer <PMS_TOKEN>"
        if "Cookie" in sanitized_headers:
            sanitized_headers["Cookie"] = "<PMS_COOKIE>"
        return {
            "method": method,
            "url": url,
            "headers": sanitized_headers,
            "body": body,
        }

    req = urlrequest.Request(url, data=encoded, headers=headers, method=method)
    try:
        with urlrequest.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode("utf-8")
    except urlerror.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {detail}") from exc
    except urlerror.URLError as exc:
        raise RuntimeError(f"Network error: {exc}") from exc

    return json.loads(raw) if raw.strip() else None


def build_request(args: argparse.Namespace) -> tuple[str, str, str, dict[str, Any] | None]:
    base = args.base_url.rstrip("/") if args.base_url else _SERVERS.get(args.server, _SERVERS["com"])["base_url"]
    if args.command == "default-properties":
        return "GET", f"{base}/{args.service}/default-properties/details", args.service, None
    if args.command == "roles":
        return "GET", f"{base}/user/service/{args.service}/roles", args.service, None
    if args.command == "criteria-values":
        return "GET", f"{base}/{args.service}/criteria-value-list/{args.criteria}", args.service, None
    if args.command == "properties":
        body: dict[str, Any] = {"BUID": args.buid}
        if args.criteria or args.value:
            if not args.criteria or args.value is None:
                raise SystemExit("--criteria and --value must be provided together")
            body[args.criteria] = args.value
        return "POST", f"{base}/{args.service}/properties/v2", args.service, body
    raise SystemExit(f"Unknown command: {args.command}")


def write_output(data: Any, out: Path | None) -> None:
    text = json.dumps(data, indent=2, ensure_ascii=False, sort_keys=False)
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text + "\n", encoding="utf-8")
        print(f"Wrote {out}")
    else:
        print(text)


def main() -> int:
    args = parse_args()
    if not args.token and not args.dry_run:
        print("ERROR: set PMS_TOKEN or pass --token.", file=sys.stderr)
        return 2

    srv = _SERVERS.get(args.server, _SERVERS["com"])
    cms_origin = srv["cms_origin"] if not args.base_url else args.base_url.rstrip("/").rsplit("/propmanagement", 1)[0]

    method, url, service, body = build_request(args)
    data = request_json(
        method=method,
        url=url,
        service=service,
        token=args.token or "<PMS_TOKEN>",
        cookie=args.cookie,
        body=body,
        dry_run=args.dry_run,
        cms_origin=cms_origin,
    )
    write_output(data, args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
