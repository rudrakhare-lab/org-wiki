#!/usr/bin/env python3
"""G05 — Live PMS smoke test against REAL servers.

Loads .env, runs the four new G05 handlers against:
  - .com server (always, requires PMS_TOKEN_COM or PMS_TOKEN)
  - .in  server (only if PMS_TOKEN_IN is set)

CRITICAL: First call prints the raw fetch_roles response so we can see
the actual "accessible BUIDs" shape before trusting the handler's parser.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from backend.tools.pms_tools import (
    _pms_list_offices_handler,
    _pms_list_criteria_handler,
    _pms_verify_buid_handler,
    _pms_diagnose_property_handler,
    _get_tokens,
)


def banner(s: str) -> None:
    print("\n" + "═" * 72)
    print(s)
    print("═" * 72)


def print_result(label: str, result: dict, hide_keys: set = frozenset()) -> None:
    pretty = {k: v for k, v in result.items() if k not in hide_keys}
    print(f"[{label}]")
    print(json.dumps(pretty, indent=2, default=str)[:4000])  # cap absurd outputs


# Smoke fixtures — known-real BUID + property from CLAUDE.md examples.
SERVICE = "VISITOR"
BUID = "genpactindia-GInd"
PROPERTY = "kioskRequireOTPBeforeRegister"


# ──────────────────────────────────────────────────────────────────────────────
# Env preflight

banner("Env preflight")
token_com, cookie_com = _get_tokens("com")
token_in, cookie_in = _get_tokens("in")
print(f"  PMS_TOKEN_COM:  {'set (' + str(len(token_com)) + ' chars)' if token_com else 'NOT SET'}")
print(f"  PMS_COOKIE_COM: {'set' if cookie_com else 'not set (optional)'}")
print(f"  PMS_TOKEN_IN:   {'set (' + str(len(token_in)) + ' chars)' if token_in else 'NOT SET (.in smoke will be skipped)'}")
print(f"  PMS_COOKIE_IN:  {'set' if cookie_in else 'not set (optional)'}")
if not token_com:
    print("\n❌ PMS_TOKEN_COM not set — cannot run .com smoke. Abort.")
    sys.exit(1)


# ──────────────────────────────────────────────────────────────────────────────
# CASE 0: raw fetch_roles — see the actual shape BEFORE trusting the parser

banner("CASE 0: RAW fetch_roles response on .com (load-bearing — read carefully)")
print(f"  service={SERVICE}, buid={BUID}, server=com")
# Call Session directly so we see the unmodified response
from pms_session import Session
session = Session.load(SERVICE, BUID, "com")
try:
    raw_roles = session.fetch_roles(token_com, cookie_com)
    print("\nRAW RESPONSE (this drives _extract_accessible_buids):")
    print(json.dumps(raw_roles, indent=2, default=str)[:3000])
except Exception as exc:
    print(f"\n❌ fetch_roles raised: {exc}")
    print("If this is an SSL error, we need truststore. See PLAN.md Conventions.")
    raise


# ──────────────────────────────────────────────────────────────────────────────
# CASE 1: pms_verify_buid on .com (real BUID)

banner(f"CASE 1: pms_verify_buid(server=com, buid={BUID}) — expect found=True")
result1 = _pms_verify_buid_handler({"service": SERVICE, "server": "com", "buid": BUID})
print_result("verify_buid_real", result1, hide_keys={"accessible_buids_sample"})
if "accessible_buids_sample" in result1:
    print(f"  accessible_buids_sample (first 5 of {result1.get('accessible_count')}): "
          f"{result1['accessible_buids_sample'][:5]}")


# ──────────────────────────────────────────────────────────────────────────────
# CASE 2: pms_verify_buid for nonexistent BUID

banner("CASE 2: pms_verify_buid(server=com, buid=nonexistentbuid-FAKE) — expect found=False, ⚠️")
result2 = _pms_verify_buid_handler({"service": SERVICE, "server": "com", "buid": "nonexistentbuid-FAKE"})
print_result("verify_buid_fake", result2, hide_keys={"accessible_buids_sample"})


# ──────────────────────────────────────────────────────────────────────────────
# CASE 3: pms_list_offices on .com

banner(f"CASE 3: pms_list_offices(server=com, buid={BUID})")
result3 = _pms_list_offices_handler({"service": SERVICE, "server": "com", "buid": BUID})
if "error" in result3:
    print_result("list_offices_error", result3)
else:
    print(f"  total offices: {result3['total']}")
    print(f"  first 5: {json.dumps(result3['offices'][:5], indent=2)}")


# ──────────────────────────────────────────────────────────────────────────────
# CASE 4: pms_list_criteria for OFFICEID on .com

banner(f"CASE 4: pms_list_criteria(server=com, buid={BUID}, criteria=OFFICEID)")
result4 = _pms_list_criteria_handler({
    "service": SERVICE, "server": "com", "buid": BUID, "criteria": "OFFICEID",
})
if "error" in result4:
    print_result("list_criteria_error", result4)
else:
    print(f"  total OFFICEIDs with overrides: {result4['total']}")
    print(f"  first 5: {result4['values'][:5]}")


# ──────────────────────────────────────────────────────────────────────────────
# CASE 5: pms_diagnose_property on .com (real BUID + real property)

banner(f"CASE 5: pms_diagnose_property(server=com, buid={BUID}, property={PROPERTY})")
result5 = _pms_diagnose_property_handler({
    "service": SERVICE, "server": "com", "buid": BUID, "property": PROPERTY,
})
print(f"  value_found: {result5.get('value_found')}")
print(f"  property:    {result5.get('property')}")
print(f"  buid:        {result5.get('buid')}")
print(f"  server:      {result5.get('server')}")
if "error" in result5:
    print(f"  ERROR: {result5['error']}")
print("\n  report_markdown (the part the user would see):")
print("  " + "─" * 68)
md = result5.get("report_markdown", "")
for line in md.splitlines()[:40]:  # cap at 40 lines for readability
    print(f"  {line}")
if len(md.splitlines()) > 40:
    print(f"  ... [+{len(md.splitlines()) - 40} more lines]")


# ──────────────────────────────────────────────────────────────────────────────
# CASE 6 (optional): .in server smoke

if token_in:
    banner(f"CASE 6: pms_verify_buid(server=in, buid={BUID}) — does this BUID exist on .in?")
    result6 = _pms_verify_buid_handler({"service": SERVICE, "server": "in", "buid": BUID})
    print_result("verify_buid_in", result6, hide_keys={"accessible_buids_sample"})
    if "accessible_buids_sample" in result6:
        print(f"  accessible_buids_sample (first 5 of {result6.get('accessible_count')}): "
              f"{result6['accessible_buids_sample'][:5]}")
else:
    banner("CASE 6: SKIPPED — PMS_TOKEN_IN not set")


print("\n" + "═" * 72)
print("Smoke test complete.")
print("═" * 72)
