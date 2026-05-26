#!/usr/bin/env python3
"""
Normalize PMS default-properties/details API responses into CSV.

The API response is service metadata, not a runtime customer value dump. It
describes each property definition, default value, data type, and the hierarchy
criteria where the property can be configured.

Usage:
  python scripts/parse_pms_default_properties.py \
    --service VISITOR \
    --input raw/pms-default-properties/VISITOR.json \
    --out docs/visitor-default-properties.csv
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--service", required=True, help="PMS service id, for example VISITOR")
    parser.add_argument("--input", required=True, type=Path, help="Saved JSON response")
    parser.add_argument("--out", required=True, type=Path, help="CSV output path")
    return parser.parse_args()


def load_response(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if isinstance(data, dict):
        for key in ("data", "properties", "defaultProperties", "result", "response"):
            value = data.get(key)
            if isinstance(value, list):
                return [x for x in value if isinstance(x, dict)]
        # Some APIs return {"success": true, "data": {"properties": [...]}}
        for value in data.values():
            if isinstance(value, dict):
                nested = value.get("properties") or value.get("defaultProperties")
                if isinstance(nested, list):
                    return [x for x in nested if isinstance(x, dict)]
    raise ValueError(f"Could not find a property list in {path}")


def compact_value(value: Any, max_len: int = 240) -> str:
    text = json.dumps(value, ensure_ascii=False, sort_keys=True)
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def criteria_parts(criteria_list: Any) -> tuple[str, str, str, str]:
    if not isinstance(criteria_list, list):
        return "", "", "", ""
    pairs: list[tuple[str, int | None]] = []
    for item in criteria_list:
        if not isinstance(item, dict):
            continue
        criteria = str(item.get("criteria") or "").strip()
        raw_priority = item.get("priority")
        try:
            priority = int(raw_priority)
        except (TypeError, ValueError):
            priority = None
        if criteria:
            pairs.append((criteria, priority))

    raw = ", ".join(
        f"{criteria}:{priority if priority is not None else ''}" for criteria, priority in pairs
    )
    levels = ", ".join(criteria for criteria, _ in pairs)
    low_to_high = " > ".join(
        criteria for criteria, _ in sorted(pairs, key=lambda p: 10**9 if p[1] is None else p[1])
    )
    high_to_low = " > ".join(
        criteria for criteria, _ in sorted(pairs, key=lambda p: -1 if p[1] is None else -p[1])
    )
    return raw, levels, low_to_high, high_to_low


def main() -> int:
    args = parse_args()
    rows = load_response(args.input)
    args.out.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "service_id",
        "property_name",
        "property_data_type",
        "default_value_preview",
        "default_value_json",
        "customizable",
        "cloneable",
        "group_name",
        "criteria_levels",
        "criteria_priority_raw",
        "criteria_order_low_to_high",
        "criteria_order_high_to_low",
        "property_definition",
    ]
    with args.out.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            raw_priority, levels, low_to_high, high_to_low = criteria_parts(
                row.get("criteriaPriorityList")
            )
            value = row.get("propertyValue")
            writer.writerow(
                {
                    "service_id": args.service,
                    "property_name": row.get("propertyName", ""),
                    "property_data_type": row.get("propertyDataType", ""),
                    "default_value_preview": compact_value(value),
                    "default_value_json": json.dumps(value, ensure_ascii=False, sort_keys=True),
                    "customizable": row.get("customizable", ""),
                    "cloneable": row.get("cloneable", ""),
                    "group_name": row.get("groupName", ""),
                    "criteria_levels": levels,
                    "criteria_priority_raw": raw_priority,
                    "criteria_order_low_to_high": low_to_high,
                    "criteria_order_high_to_low": high_to_low,
                    "property_definition": row.get("propertyDefinition", ""),
                }
            )

    print(f"Wrote {len(rows)} rows to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
