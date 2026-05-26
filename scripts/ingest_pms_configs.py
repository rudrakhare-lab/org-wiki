#!/usr/bin/env python3
"""
ingest_pms_configs.py — Auto-generate wiki/configs/<service>.md pages from
PMS Config CSV files for both .in and .com servers.

For each WorkInSync service (Meeting Rooms, VMS, Booking Rule Engine, etc.) this
script:
  1. Reads the .in and .com config CSVs.
  2. Enriches missing descriptions from:
       a. Copy of Workplace_PMS Description (Cleaned) sheets
       b. wis_unique_configs master list
  3. Writes wiki/configs/<service-slug>.md with a dual-server comparison table.
  4. Creates wiki/sources/pms-configs-in.md and wiki/sources/pms-configs-com.md.
  5. Appends entries to wiki/log.md and updates wiki/index.md.

Idempotent — re-running overwrites wiki/configs/ pages and updates the sources.

Usage:
  python scripts/ingest_pms_configs.py
  python scripts/ingest_pms_configs.py --dry-run
  python scripts/ingest_pms_configs.py --service meeting-rooms
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WIKI = ROOT / "wiki"
RAW = ROOT / "raw"

# ---------------------------------------------------------------------------
# Service map — maps (in_sheet_stem, com_sheet_stem) → service config
# ---------------------------------------------------------------------------

SERVICES: list[dict] = [
    {
        "slug": "pms",
        "label": "Project Management Service (PMS)",
        "module": None,  # cross-cutting, no single module page
        "in_csv": RAW / "modules/pms-configs-in/All WIS CONFIGS/1. PMS.csv",
        "com_csv": RAW / "modules/pms-configs-com/wis_service_configs/1. PMS.csv",
        "desc_csv": RAW / "modules/_root/Copy of Workplace_PMS Description (Cleaned)/ProjectMgmtService.csv",
    },
    {
        "slug": "visitor-management",
        "label": "Visitor Management Service (VMS)",
        "module": "visitor-management",
        "in_csv": RAW / "modules/pms-configs-in/All WIS CONFIGS/2. Visitor Mgmt.csv",
        "com_csv": RAW / "modules/pms-configs-com/wis_service_configs/2. VMS.csv",
        "desc_csv": RAW / "modules/_root/Copy of Workplace_PMS Description (Cleaned)/Visitor.csv",
    },
    {
        "slug": "meeting-rooms",
        "label": "Meeting Rooms Service",
        "module": "meeting-rooms",
        "in_csv": RAW / "modules/pms-configs-in/All WIS CONFIGS/3. Meeting Rooms.csv",
        "com_csv": RAW / "modules/pms-configs-com/wis_service_configs/3. Meeting Rooms.csv",
        "desc_csv": RAW / "modules/_root/Copy of Workplace_PMS Description (Cleaned)/MeetingRooms.csv",
    },
    {
        "slug": "booking-rule-engine",
        "label": "Booking Rule Engine",
        "module": None,  # cross-cutting
        "in_csv": RAW / "modules/pms-configs-in/All WIS CONFIGS/4. Booking Rule Engine.csv",
        "com_csv": RAW / "modules/pms-configs-com/wis_service_configs/4. Booking Rule Engine.csv",
        "desc_csv": RAW / "modules/_root/Copy of Workplace_PMS Description (Cleaned)/BookingRuleEngine.csv",
    },
    {
        "slug": "wis-seat-booking",
        "label": "WIS Seat Booking Service",
        "module": "desk-management",
        "in_csv": RAW / "modules/pms-configs-in/All WIS CONFIGS/5. WIS Seat Booking.csv",
        "com_csv": RAW / "modules/pms-configs-com/wis_service_configs/5. WIS Seat Booking.csv",
        "desc_csv": RAW / "modules/_root/Copy of Workplace_PMS Description (Cleaned)/WisSeatBooking.csv",
    },
    {
        "slug": "guard-app",
        "label": "Guard App Service",
        "module": "guard-app-kiosks",
        "in_csv": RAW / "modules/pms-configs-in/All WIS CONFIGS/6. Guard App.csv",
        "com_csv": RAW / "modules/pms-configs-com/wis_service_configs/6. Guard App.csv",
        "desc_csv": RAW / "modules/_root/Copy of Workplace_PMS Description (Cleaned)/GuardApp.csv",
    },
    {
        "slug": "emp-experience-email",
        "label": "Employee Experience — Email Service",
        "module": "employee-experience",
        "in_csv": RAW / "modules/pms-configs-in/All WIS CONFIGS/7. Email Emp Experience.csv",
        "com_csv": RAW / "modules/pms-configs-com/wis_service_configs/7. Email Emp Experience.csv",
        "desc_csv": None,
    },
    {
        "slug": "emp-experience-internal",
        "label": "Employee Experience — Internal Config",
        "module": "employee-experience",
        "in_csv": RAW / "modules/pms-configs-in/All WIS CONFIGS/8. Emp Exp Internal Config.csv",
        "com_csv": RAW / "modules/pms-configs-com/wis_service_configs/8. Emp Exp Internal Config.csv",
        "desc_csv": RAW / "modules/_root/Copy of Workplace_PMS Description (Cleaned)/EmpExpInternal.csv",
    },
    {
        "slug": "emp-experience-common",
        "label": "Employee Experience — Common Config",
        "module": "employee-experience",
        "in_csv": RAW / "modules/pms-configs-in/All WIS CONFIGS/9. Emp Exp Common Config.csv",
        "com_csv": RAW / "modules/pms-configs-com/wis_service_configs/9. Emp Exp Common Config.csv",
        "desc_csv": RAW / "modules/_root/Copy of Workplace_PMS Description (Cleaned)/EmpExpCommon.csv",
    },
    # MobileAppServer exists in the Description file only.
    {
        "slug": "mobile-app-server",
        "label": "Mobile App Server Config",
        "module": "mobile-app",
        "in_csv": None,
        "com_csv": None,
        "desc_csv": RAW / "modules/_root/Copy of Workplace_PMS Description (Cleaned)/MobileAppServer.csv",
    },
    # APP_SERVER_CONFIG — added 2026-05-14.
    # .in server data is embedded as sheet 11 in the .com xlsx (same 3-col format as .com).
    # in_com_csv is parsed with parse_com_csv and merged into in_props.
    {
        "slug": "app-server-config",
        "label": "App Server Config",
        "module": None,
        "in_csv": None,
        "in_com_csv": RAW / "modules/pms-configs-com/wis_service_configs/11. App Server Config (.in).csv",
        "com_csv": RAW / "modules/pms-configs-com/wis_service_configs/10. App Server Config.csv",
        "desc_csv": None,
    },
]

UNIQUE_CONFIGS_CSV = RAW / "modules/pms-configs-in/wis_unique_configs/Unique Configs.csv"

TODAY = datetime.now(timezone.utc).strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------

def parse_in_csv(path: Path) -> dict[str, str]:
    """Parse a .in config CSV. Returns {property_name: description}.
    Skips metadata rows (service name, total count) before the header.
    """
    props: dict[str, str] = {}
    if not path or not path.exists():
        return props
    in_header = False
    for row in csv.reader(path.open(encoding="utf-8-sig")):
        clean = [c.strip() for c in row]
        if not any(clean):
            continue
        if not in_header:
            if clean[0] == "Property Name":
                in_header = True
            continue
        name = clean[0]
        desc = clean[1] if len(clean) > 1 else ""
        if name:
            props[name] = desc
    return props


def parse_com_csv(path: Path) -> dict[str, tuple[str, str]]:
    """Parse a .com config CSV. Returns {property_name: (data_type, description)}.
    First row is the header: Property Name | Data Type | Description.
    """
    props: dict[str, tuple[str, str]] = {}
    if not path or not path.exists():
        return props
    header_done = False
    for row in csv.reader(path.open(encoding="utf-8-sig")):
        clean = [c.strip() for c in row]
        if not any(clean):
            continue
        if not header_done:
            header_done = True
            continue
        name = clean[0]
        dtype = clean[1] if len(clean) > 1 else ""
        desc = clean[2] if len(clean) > 2 else ""
        if name:
            props[name] = (dtype, desc)
    return props


def parse_desc_csv(path: Path) -> dict[str, str]:
    """Parse a PMS Description Cleaned CSV. Returns {property_name: description}.
    Handles optional metadata rows before the header.
    """
    props: dict[str, str] = {}
    if not path or not path.exists():
        return props
    in_header = False
    for row in csv.reader(path.open(encoding="utf-8-sig")):
        clean = [c.strip() for c in row]
        if not any(clean):
            continue
        if not in_header:
            if clean[0] == "Property Name":
                in_header = True
            continue
        name = clean[0]
        desc = clean[1] if len(clean) > 1 else ""
        if name and not name.startswith("Anirban"):  # skip editorial notes
            props[name] = desc
    return props


def parse_unique_configs() -> dict[str, str]:
    """Parse wis_unique_configs. Returns {property_name: description}."""
    props: dict[str, str] = {}
    if not UNIQUE_CONFIGS_CSV.exists():
        return props
    in_header = False
    for row in csv.reader(UNIQUE_CONFIGS_CSV.open(encoding="utf-8-sig")):
        clean = [c.strip() for c in row]
        if not any(clean):
            continue
        if not in_header:
            if clean[0] == "Property Name":
                in_header = True
            continue
        name = clean[0]
        desc = clean[1] if len(clean) > 1 else ""
        if name:
            props.setdefault(name, desc)  # keep first (dedup is already done)
    return props


# ---------------------------------------------------------------------------
# Description resolution
# ---------------------------------------------------------------------------

def best_description(
    name: str,
    in_desc: str,
    com_desc: str,
    desc_lookup: dict[str, str],
    unique_lookup: dict[str, str],
) -> tuple[str, str]:
    """Return (description, source_tag).
    Preference: .com desc > .in desc > PMS Description Cleaned > wis_unique > ''.
    """
    if com_desc and com_desc not in ("-", "—", "N/A"):
        return com_desc, ".com"
    if in_desc and in_desc not in ("-", "—", "N/A"):
        return in_desc, ".in"
    if name in desc_lookup and desc_lookup[name]:
        return desc_lookup[name], "PMS-desc"
    if name in unique_lookup and unique_lookup[name]:
        return unique_lookup[name], "unique-cfg"
    return "", "undocumented"


# ---------------------------------------------------------------------------
# Wiki page generation
# ---------------------------------------------------------------------------

def _esc(s: str) -> str:
    """Escape pipe chars so they don't break markdown tables."""
    return s.replace("|", "&#124;").replace("\n", " ").strip()


def generate_config_page(svc: dict, unique_lookup: dict[str, str], dry_run: bool) -> str:
    slug = svc["slug"]
    label = svc["label"]
    module = svc["module"]

    in_props = parse_in_csv(svc["in_csv"])
    # in_com_csv: .in server data stored in .com 3-column format (e.g. App Server Config sheet 11)
    in_com_csv = svc.get("in_com_csv")
    if in_com_csv:
        for name, (dtype, desc) in parse_com_csv(in_com_csv).items():
            if name not in in_props:
                in_props[name] = desc  # fold into in_props as description-only
    com_props = parse_com_csv(svc["com_csv"])
    desc_lookup = parse_desc_csv(svc["desc_csv"])

    all_names = sorted(set(list(in_props) + list(com_props) + list(desc_lookup)), key=str.lower)

    # ---- Build rows ----
    both: list[tuple] = []
    in_only: list[tuple] = []
    com_only: list[tuple] = []
    undocumented: list[str] = []

    for name in all_names:
        in_present = name in in_props
        com_present = name in com_props
        in_desc = in_props.get(name, "")
        com_dtype, com_desc = com_props.get(name, ("", ""))

        desc, src = best_description(name, in_desc, com_desc, desc_lookup, unique_lookup)
        if not desc:
            undocumented.append(name)

        row = (name, in_present, com_present, com_dtype, desc, src)
        if in_present and com_present:
            both.append(row)
        elif in_present:
            in_only.append(row)
        elif com_present:
            com_only.append(row)
        else:
            # Only in desc_lookup — document as reference
            both.append(row)

    # ---- Build markdown ----
    has_in_data = bool(svc["in_csv"] or svc.get("in_com_csv"))
    module_link = f"[[modules/{module}]]" if module else f"`{slug}` (no module page yet — needs stub)"
    in_src = "pms-configs-in-all-wis-configs" if svc["in_csv"] else (
        "pms-configs-com-wis-service-configs" if svc.get("in_com_csv") else "N/A"
    )
    com_src = "pms-configs-com-wis-service-configs" if svc["com_csv"] else "N/A"

    lines: list[str] = [
        "---",
        f"type: config",
        f"module: {module or 'none'}",
        f"servers:",
    ]
    if has_in_data:
        lines.append("  - in")
    if svc["com_csv"]:
        lines.append("  - com")
    lines += [
        f"last_updated: {TODAY}",
        f"sources:",
        f"  in: \"[[sources/{in_src}]]\"" if has_in_data else "  in: N/A",
        f"  com: \"[[sources/{com_src}]]\"" if svc["com_csv"] else "  com: N/A",
        "---",
        "",
        f"# {label} — Config Properties",
        "",
        "## Service",
        f"{label}. Linked module: {module_link}.",
        "",
        f"_Source: [[sources/{in_src}]] | [[sources/{com_src}]]_"
        if has_in_data and svc["com_csv"]
        else f"_Source: [[sources/{com_src}]]_",
        "",
        "## Config Comparison",
        "",
        f"> **Server key:** ✅ = property present in that server's config list | — = absent",
        f"> **Description source:** `.com` description preferred; falls back to `.in`, PMS Description Cleaned, then `wis_unique_configs`.",
        f"> ⚠️ `undocumented` = no description found in any source — contact the owning team.",
        "",
        "| Property Name | .in | .com | Data Type | Description |",
        "|---------------|-----|------|-----------|-------------|",
    ]

    def row_line(r: tuple) -> str:
        name, in_p, com_p, dtype, desc, src = r
        in_col = "✅" if in_p else "—"
        com_col = "✅" if com_p else "—"
        desc_out = _esc(desc) if desc else "⚠️ undocumented"
        return f"| `{name}` | {in_col} | {com_col} | {_esc(dtype) or '—'} | {desc_out} |"

    for r in both:
        lines.append(row_line(r))
    for r in in_only:
        lines.append(row_line(r))
    for r in com_only:
        lines.append(row_line(r))

    if in_only:
        lines += [
            "",
            "## .in-only Configs",
            f"_{len(in_only)} properties present on the `.in` server but absent from the `.com` config list._",
            "",
        ]
        for r in in_only:
            desc_out = r[4] or "⚠️ undocumented"
            lines.append(f"- `{r[0]}` — {_esc(desc_out)}")

    if com_only:
        lines += [
            "",
            "## .com-only Configs",
            f"_{len(com_only)} properties present on the `.com` server but absent from the `.in` config list._",
            "",
        ]
        for r in com_only:
            desc_out = r[4] or "⚠️ undocumented"
            lines.append(f"- `{r[0]}` — {_esc(desc_out)}")

    if undocumented:
        lines += [
            "",
            "## Missing Descriptions",
            f"_{len(undocumented)} properties have no description in any source (PMS config files, PMS Description Cleaned, or wis_unique_configs)._",
            "Contact the owning service team for documentation.",
            "",
        ]
        for name in undocumented:
            lines.append(f"- `{name}`")

    lines += [
        "",
        f"_Last updated: {TODAY}_",
        f"_Source: [[sources/{in_src}]] | [[sources/{com_src}]]_",
    ]

    content = "\n".join(lines) + "\n"

    out_path = WIKI / "configs" / f"{slug}.md"
    if not dry_run:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(content, encoding="utf-8")

    stats = {
        "both": len(both),
        "in_only": len(in_only),
        "com_only": len(com_only),
        "undocumented": len(undocumented),
        "total": len(all_names),
    }
    return stats


# ---------------------------------------------------------------------------
# Source summary pages
# ---------------------------------------------------------------------------

def write_source_page(slug: str, title: str, raw_path: str, services: list[str], dry_run: bool):
    content = f"""---
type: source
raw_path: {raw_path}
ingested: {TODAY}
doc_type: config
---

# {title}

## Source Title
{title}

## Date
{TODAY} (ingested)

## Type
Config — PMS service property list

## Key Takeaways
- Contains PMS configuration properties for {len(services)} WorkInSync services.
- Services covered: {', '.join(services)}
- Each property maps to a PMS key-value pair stored per client in the property management service.
- Used to answer "what configs does service X have?" and "is config Y available on this server?"

## Entities Mentioned
- PMS config properties (see `wiki/configs/<service>.md` pages)

## Modules Mentioned
{chr(10).join(f'- [[modules/{m}]]' for m in ['meeting-rooms', 'visitor-management', 'desk-management', 'guard-app-kiosks', 'employee-experience'] if m)}

## Decisions Extracted
None.

## Wiki Pages Created/Updated
{chr(10).join(f'- [[configs/{svc}]]' for svc in services)}

_Source: raw/{raw_path}_
"""
    out_path = WIKI / "sources" / f"{slug}.md"
    if not dry_run:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# Log + Index updates
# ---------------------------------------------------------------------------

def append_log(entries: list[str], dry_run: bool):
    log_path = WIKI / "log.md"
    if not log_path.exists():
        return
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    block = f"\n## [{ts}] ingest | PMS Config files (.in + .com servers)\n"
    block += "- Created: " + ", ".join(f"[[{e}]]" for e in entries) + "\n"
    block += f"- Sources: pms-configs-in (All WIS CONFIGS.xlsx), pms-configs-com (wis_service_configs.xlsx)\n"
    block += f"- Notes: Dual-server comparison tables. .com has Data Type column; .in does not. Properties with no description flagged ⚠️ undocumented.\n"
    if not dry_run:
        with log_path.open("a", encoding="utf-8") as f:
            f.write(block)


def update_index(new_config_slugs: list[str], dry_run: bool):
    index_path = WIKI / "index.md"
    if not index_path.exists():
        return
    content = index_path.read_text(encoding="utf-8")

    # Add Configs table if missing
    if "## Configs" not in content:
        config_section = "\n## Configs\n| Page | Service | Servers | Module |\n|------|---------|---------|--------|\n"
        for svc in SERVICES:
            if svc["slug"] in new_config_slugs:
                module_link = f"[[modules/{svc['module']}]]" if svc["module"] else "—"
                servers = []
                if svc["in_csv"]:
                    servers.append(".in")
                if svc["com_csv"]:
                    servers.append(".com")
                srv_str = " + ".join(servers)
                config_section += f"| [[configs/{svc['slug']}]] | {svc['label']} | {srv_str} | {module_link} |\n"

        # Insert before Sources Ingested section
        content = content.replace("\n## Sources Ingested", config_section + "\n## Sources Ingested")

        # Update total page count
        def bump_count(match):
            total = int(match.group(1)) + len(new_config_slugs) + 2  # +2 for source pages
            return f"Total pages: {total}"
        content = re.sub(r"Total pages: (\d+)", bump_count, content)

        # Add source rows for the two PMS config source files
        in_slugs = ", ".join("configs/" + s["slug"] for s in SERVICES if s["in_csv"])
        com_slugs = ", ".join("configs/" + s["slug"] for s in SERVICES if s["com_csv"])
        in_row = f"| [[sources/pms-configs-in-all-wis-configs]] | config | {TODAY} | {in_slugs} |\n"
        com_row = f"| [[sources/pms-configs-com-wis-service-configs]] | config | {TODAY} | {com_slugs} |\n"
        # Append to sources table
        if "## Sources Ingested" in content:
            idx = content.rfind("\n", 0, content.find("\n\n", content.find("## Sources Ingested")))
            content = content[:idx] + "\n" + in_row + com_row + content[idx:]

    if not dry_run:
        index_path.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true", help="Show what would be written without writing")
    ap.add_argument("--service", help="Only process this service slug")
    args = ap.parse_args()

    unique_lookup = parse_unique_configs()
    print(f"Loaded {len(unique_lookup)} entries from wis_unique_configs")
    print()

    created: list[str] = []
    services_to_run = [s for s in SERVICES if not args.service or s["slug"] == args.service]

    for svc in services_to_run:
        slug = svc["slug"]
        in_exists = svc["in_csv"] and svc["in_csv"].exists()
        in_com_exists = svc.get("in_com_csv") and svc["in_com_csv"].exists()
        com_exists = svc["com_csv"] and svc["com_csv"].exists()
        if not in_exists and not in_com_exists and not com_exists and not (svc["desc_csv"] and svc["desc_csv"].exists()):
            print(f"SKIP {slug} — no CSV sources found")
            continue

        print(f"Processing: {slug}")
        stats = generate_config_page(svc, unique_lookup, args.dry_run)
        print(f"  both={stats['both']}  .in-only={stats['in_only']}  .com-only={stats['com_only']}  "
              f"undocumented={stats['undocumented']}  total={stats['total']}")
        if not args.dry_run:
            print(f"  → wrote wiki/configs/{slug}.md")
        created.append(f"configs/{slug}")

    if not args.dry_run:
        in_services = [s["slug"] for s in SERVICES if s["in_csv"] and s["in_csv"].exists()]
        com_services = [s["slug"] for s in SERVICES if s["com_csv"] and s["com_csv"].exists()]
        write_source_page(
            "pms-configs-in-all-wis-configs",
            "PMS Configs — .in Server (All WIS CONFIGS)",
            "modules/pms-configs-in/All WIS CONFIGS.xlsx",
            in_services,
            args.dry_run,
        )
        write_source_page(
            "pms-configs-com-wis-service-configs",
            "PMS Configs — .com Server (wis_service_configs)",
            "modules/pms-configs-com/wis_service_configs.xlsx",
            com_services,
            args.dry_run,
        )
        created += ["sources/pms-configs-in-all-wis-configs", "sources/pms-configs-com-wis-service-configs"]

    append_log(created, args.dry_run)
    update_index([s["slug"] for s in services_to_run if svc["slug"] in [x.split("/")[-1] for x in created]], args.dry_run)

    print()
    print(f"{'[DRY RUN] ' if args.dry_run else ''}Done — {len(created)} pages {'would be ' if args.dry_run else ''}written")
    print()
    print("Next steps:")
    print("  1. Check wiki/configs/ pages in Obsidian")
    print("  2. Update module pages to add ## Config Properties section linking to [[configs/<slug>]]")
    print("  3. Create stub module pages for: pms, booking-rule-engine (no module page exists yet)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
