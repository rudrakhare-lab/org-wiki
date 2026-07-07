"""Config-KB preflight push (spec §5.6): when the question names a config
property, its catalog row + dependency chain (≤2 levels, cycle-safe) is
pushed into the seed with anchors into configs/ pages. Live PMS *values*
remain pull-only (server/BUID disambiguation — CLAUDE.md §12).

Key-shape note: the brief that drove this module assumed a lookup dict with
keys `property` / `dependent_configs`. The real `lookup_property()` (backend/
tools/config_tools.py, Postgres-backed) instead returns `property_name` and a
`depends_on` list of dicts `{property, dep_type, direction, confidence}` (the
`dependencies` table is directional: property_a depends on property_b). This
module maps `depends_on` → the plain list of property names via
`_dependent_names()` and reads `property_name` instead of `property`. All
other assumed keys (`description`, `data_type`, `service`,
`criteria_priority_list`) match the real shape as-is.

Regex note: the brief's backtick regex required 2+ chars (`[A-Za-z][A-Za-z0-9_.]+`)
but its own cycle-safety test seeds single-char property names (`` `a` ``, `` `b` ``).
Changed `+` to `*` so the test's fixture is detectable; real config properties are
never single-char, so this is a no-op for production detection.
"""
from __future__ import annotations
import re

from backend.tools.config_tools import lookup_property, known_property_names

_BACKTICK_RE = re.compile(r"`([A-Za-z][A-Za-z0-9_.]*)`")
_CAMEL_RE = re.compile(r"\b([a-z]+[A-Z][A-Za-z0-9]*)\b")


def _known_names() -> set[str]:
    return known_property_names()


def detect_config_properties(question: str, known_names: set[str]) -> list[str]:
    cands = _BACKTICK_RE.findall(question) + _CAMEL_RE.findall(question)
    lower_map = {}
    for n in known_names:
        lower_map.setdefault(n.lower(), []).append(n)
    out: list[str] = []
    for c in cands:
        if c in known_names:
            hit = c
        else:
            matches = lower_map.get(c.lower(), [])
            hit = matches[0] if len(matches) == 1 else None
        if hit and hit not in out:
            out.append(hit)
    return out


def _prop_name(row: dict) -> str:
    """Real catalog rows key the property name as `property_name`; the
    brief's example fixtures (and hand-built dicts in tests) use `property`.
    Accept either so both real rows and test doubles work."""
    return row.get("property_name") or row.get("property") or ""


def _dependent_names(row: dict) -> list[str]:
    """Real catalog rows carry `depends_on: [{"property": ..., ...}, ...]`
    (directional dependency edges from the `dependencies` table). The
    brief's fixtures use a flat `dependent_configs: [name, ...]` list.
    Normalize both into a flat list of property names to walk."""
    if row.get("dependent_configs"):
        return list(row["dependent_configs"])
    out = []
    for dep in row.get("depends_on") or []:
        if isinstance(dep, dict):
            name = dep.get("property")
        else:
            name = dep
        if name:
            out.append(name)
    return out


# Service ID → wiki/configs/ page slug. Verified against the ACTUAL files in
# wiki/configs/ (2026-07-08) and cross-checked with the two existing maps that
# already encode this: scripts/build_config_db.py::SERVICE_META (which writes
# those pages) and scripts/apply_feedback.py::SERVICE_TO_CONFIG_PAGE. The
# brief's naive lowercase transform produced dead anchors for half the real
# services (e.g. VISITOR → configs/visitor.md; real page is
# configs/visitor-management.md).
# NOTE: catalog rows do carry `module_pages`, but those are MODULE page paths
# ("modules/visitor-management", per enrich_config_db.py::SERVICE_TO_MODULE_SLUG),
# not configs/ slugs — unusable for this anchor, hence the explicit table.
# tests/test_config_evidence.py pins every entry to an existing file.
_SERVICE_TO_CONFIG_SLUG: dict[str, str] = {
    "PROJECT-MANAGEMENT-SERVICE": "pms",
    "PMS":                        "pms",
    "VISITOR":                    "visitor-management",
    "MEETING_ROOMS":              "meeting-rooms",
    "BOOKING-RULE-ENGINE":        "booking-rule-engine",
    "WIS-SEAT-BOOKING":           "wis-seat-booking",
    "GUARD-APP":                  "guard-app",
    "EMAIL-EMP-EXPERIENCE":       "emp-experience-email",
    "EMP-EXP-INTERNAL-CONFIG":    "emp-experience-internal",
    "EMP-EXP-COMMON-CONFIG":      "emp-experience-common",
    "APP_SERVER_CONFIG":          "app-server-config",
}


def _config_anchor(service: str) -> str:
    """Resolve a catalog service ID to its wiki/configs/ page path.
    Layered: curated table first (verified against the real pages), then the
    naive lowercase transform as a last resort for unknown future services."""
    svc = (service or "").strip()
    if not svc:
        return "configs/"
    slug = _SERVICE_TO_CONFIG_SLUG.get(svc.upper())
    if slug is None:
        slug = svc.lower().replace("_", "-")
    return f"configs/{slug}.md"


def _fmt(row: dict) -> str:
    anchor = _config_anchor(row.get("service") or "")
    bits = [f"- `{_prop_name(row)}`"]
    if row.get("data_type"):
        bits.append(f"type `{row['data_type']}`")
    if row.get("description"):
        bits.append(str(row["description"])[:200])
    if row.get("criteria_priority_list"):
        bits.append(f"levels: {row['criteria_priority_list']}")
    return " — ".join(bits) + f" → `{anchor}`"


def build_config_evidence(question: str, max_depth: int = 2) -> str:
    detected = detect_config_properties(question, _known_names())
    if not detected:
        return ""
    lines = ["## Config properties detected in your question", ""]
    seen: set[str] = set()
    frontier = list(detected)
    for depth in range(max_depth + 1):
        nxt: list[str] = []
        for name in frontier:
            if name in seen:
                continue
            seen.add(name)
            row = lookup_property(name)
            if not row:
                lines.append(f"- `{name}` — not found in config catalog")
                continue
            indent = "  " * depth
            lines.append(indent + _fmt(row))
            for dep in _dependent_names(row):
                if dep not in seen:
                    nxt.append(dep)
        frontier = nxt
        if not frontier:
            break
    lines.append("")
    lines.append("_Live values need server (.in/.com) + BUID — use pms_runtime_values / pms_diagnose_property._")
    return "\n".join(lines)
