#!/usr/bin/env python3
"""
Audit config-key coverage across the LLM wiki corpus.

Input:
  CSV/TSV with at least a "Property Name" column and optional "Description".

What it checks:
  - exact config-key mentions in wiki/, raw/, docs/, and config/
  - where the mention appears (wiki page vs source/raw only)
  - whether the config appears to have weak coverage

Outputs:
  - markdown summary report
  - csv row-level report

Example:
  python3 scripts/audit_config_coverage.py \
    --input raw/configs/config_inventory.csv \
    --report docs/config-coverage-report.md \
    --csv docs/config-coverage-report.csv
"""

from __future__ import annotations

import argparse
import csv
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SCAN_DIRS = [
    ROOT / "wiki",
    ROOT / "raw",
    ROOT / "docs",
    ROOT / "config",
]
TEXT_EXTS = {
    ".md", ".txt", ".csv", ".tsv", ".json", ".yaml", ".yml", ".toml", ".py"
}


@dataclass
class Match:
    path: Path
    line_no: int
    line: str


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", required=True, type=Path, help="CSV/TSV config inventory")
    p.add_argument(
        "--report",
        type=Path,
        default=ROOT / "docs" / "config-coverage-report.md",
        help="Markdown report output path",
    )
    p.add_argument(
        "--csv",
        type=Path,
        default=ROOT / "docs" / "config-coverage-report.csv",
        help="Row-level CSV output path",
    )
    return p.parse_args()


def detect_delimiter(path: Path) -> str:
    if path.suffix.lower() == ".tsv":
        return "\t"
    sample = path.read_text(encoding="utf-8", errors="ignore")[:2048]
    try:
        return csv.Sniffer().sniff(sample, delimiters=",\t;|").delimiter
    except csv.Error:
        return ","


def load_inventory(path: Path) -> list[dict[str, str]]:
    delim = detect_delimiter(path)
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter=delim)
        rows = []
        for row in reader:
            normalized = {str(k).strip(): (v or "").strip() for k, v in row.items() if k}
            if normalized:
                rows.append(normalized)
        return rows


def iter_text_files() -> list[Path]:
    files: list[Path] = []
    for scan_dir in DEFAULT_SCAN_DIRS:
        if not scan_dir.exists():
            continue
        for path in scan_dir.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix.lower() not in TEXT_EXTS:
                continue
            files.append(path)
    return sorted(files)


def find_matches(key: str, files: list[Path]) -> list[Match]:
    pattern = re.compile(rf"(?<![A-Za-z0-9_]){re.escape(key)}(?![A-Za-z0-9_])", re.IGNORECASE)
    matches: list[Match] = []
    for path in files:
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for i, line in enumerate(text.splitlines(), start=1):
            if pattern.search(line):
                matches.append(Match(path=path, line_no=i, line=line.strip()))
    return matches


def classify(matches: list[Match]) -> tuple[str, str]:
    if not matches:
        return "missing", "No exact config-key mention found anywhere in scanned corpus."

    wiki_matches = [m for m in matches if "/wiki/" in str(m.path)]
    module_matches = [m for m in wiki_matches if "/wiki/modules/" in str(m.path)]
    source_matches = [m for m in wiki_matches if "/wiki/sources/" in str(m.path)]
    raw_matches = [m for m in matches if "/raw/" in str(m.path)]

    if module_matches:
        if len(module_matches) >= 2 or len(wiki_matches) >= 3:
            return "covered", "Config is documented in wiki pages with multi-page context."
        return "thin", "Config is present in wiki, but only with limited page coverage."

    if source_matches:
        return "raw-only", "Config is captured in source summaries but not elevated into module knowledge."

    if raw_matches:
        return "raw-only", "Config exists in raw ingested sources, but not in wiki pages."

    return "thin", "Config is mentioned outside wiki sources/modules but lacks clear module-level coverage."


def jira_match_count(db_path: Path, key: str) -> int:
    if not db_path.exists():
        return 0
    conn = sqlite3.connect(str(db_path))
    try:
        row = conn.execute(
            """
            SELECT COUNT(*) FROM tickets
            WHERE lower(coalesce(summary, '')) LIKE '%' || lower(?) || '%'
               OR lower(coalesce(description_text, '')) LIKE '%' || lower(?) || '%'
               OR lower(coalesce(comments_text, '')) LIKE '%' || lower(?) || '%'
            """,
            (key, key, key),
        ).fetchone()
        return int(row[0] or 0)
    finally:
        conn.close()


def short_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def write_row_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "property_name",
                "description",
                "status",
                "match_count",
                "wiki_match_count",
                "module_match_count",
                "jira_match_count",
                "sample_paths",
                "notes",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(
    path: Path,
    source_path: Path,
    total: int,
    status_counts: dict[str, int],
    rows: list[dict[str, str]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "# Config Coverage Report",
        "",
        f"Source inventory: `{short_path(source_path)}`",
        "",
        "## Summary",
        "",
        f"- Total configs audited: **{total}**",
        f"- Covered: **{status_counts.get('covered', 0)}**",
        f"- Thin coverage: **{status_counts.get('thin', 0)}**",
        f"- Raw-only: **{status_counts.get('raw-only', 0)}**",
        f"- Jira-only: **{status_counts.get('jira-only', 0)}**",
        f"- Missing: **{status_counts.get('missing', 0)}**",
        "",
        "## Status Meanings",
        "",
        "- `covered`: appears in wiki module/context pages strongly enough to answer questions",
        "- `thin`: appears in wiki, but context is likely too shallow for confident support usage",
        "- `raw-only`: exists in raw/source material, but has not been promoted into wiki knowledge",
        "- `jira-only`: not in wiki/docs, but appears in ticket evidence",
        "- `missing`: not found as an exact key anywhere scanned",
        "",
        "## Audit Table",
        "",
        "| Property Name | Status | Corpus Matches | Jira Hits | Sample Paths | Notes |",
        "|---|---|---:|---:|---|---|",
    ]

    for row in rows:
        lines.append(
            f"| `{row['property_name']}` | `{row['status']}` | {row['match_count']} | {row['jira_match_count']} | "
            f"{row['sample_paths'] or '—'} | {row['notes']} |"
        )

    lines.extend([
        "",
        "## Recommended Next Actions",
        "",
        "1. Promote all `raw-only` and `jira-only` configs into the relevant module pages.",
        "2. Review all `thin` configs and add module-level sections for enable/disable behavior, defaults, scope, and dependencies.",
        "3. Create a dedicated config inventory in the wiki once the first audit is complete.",
        "4. Re-run this audit after each ingest or config-doc upload.",
        "",
    ])

    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    args = parse_args()
    inventory = load_inventory(args.input)
    if not inventory:
        raise SystemExit(f"No rows found in {args.input}")

    files = iter_text_files()
    results: list[dict[str, str]] = []
    status_counts: dict[str, int] = {}
    jira_db = ROOT / "raw" / "jira" / "tickets.sqlite"

    for row in inventory:
        property_name = (
            row.get("Property Name")
            or row.get("property_name")
            or row.get("Property")
            or row.get("property")
            or ""
        ).strip()
        description = (
            row.get("Description")
            or row.get("description")
            or ""
        ).strip()
        if not property_name:
            continue

        matches = find_matches(property_name, files)
        jira_hits = jira_match_count(jira_db, property_name)
        status, notes = classify(matches)

        if status == "missing" and jira_hits > 0:
            status = "jira-only"
            notes = "Config key is not documented in wiki/raw docs, but does appear in Jira evidence."
        status_counts[status] = status_counts.get(status, 0) + 1

        wiki_match_count = sum(1 for m in matches if "/wiki/" in str(m.path))
        module_match_count = sum(1 for m in matches if "/wiki/modules/" in str(m.path))
        sample_paths = ", ".join(dict.fromkeys(short_path(m.path) for m in matches[:5]))

        results.append({
            "property_name": property_name,
            "description": description,
            "status": status,
            "match_count": str(len(matches)),
            "wiki_match_count": str(wiki_match_count),
            "module_match_count": str(module_match_count),
            "jira_match_count": str(jira_hits),
            "sample_paths": sample_paths,
            "notes": notes,
        })

    results.sort(key=lambda r: (r["status"], r["property_name"].lower()))
    write_row_csv(args.csv, results)
    write_markdown(args.report, args.input, len(results), status_counts, results)

    print(f"Wrote markdown report: {short_path(args.report)}")
    print(f"Wrote row-level CSV:   {short_path(args.csv)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
