"""
lib/normalize.py — Jira issue JSON → SQLite row dict.

The single entry point is `normalize_issue(raw_issue, *, fa_field_id, source_filter)`
which returns a dict with keys matching `lib/db._TICKET_COLUMNS`.

Normalization rules:
- ADF (description, comments) → plaintext via adf_to_text
- Comments concatenated as `[<author>, <date>] <body>` separated by blank lines
- Priority strings mapped to canonical P0..P4 (or NULL if missing/unknown)
- External URLs extracted via regex over description + comments
- Empty-shell detection sets triage_reason = 'empty-shell' so the classifier
  can short-circuit
- All datetimes preserved in their Jira ISO 8601 form (UTC)

Robustness: every accessor uses .get() with sensible defaults. Jira occasionally
omits fields that "should" always be there (e.g. priority on really old tickets).
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any

from .adf_to_text import adf_to_text


# ---------------------------------------------------------------------------
# Priority mapping
# ---------------------------------------------------------------------------

_PRIORITY_MAP = {
    # Highest tier
    "highest": "P0", "p0": "P0", "blocker": "P0", "critical": "P0",
    "sev1": "P0", "s1": "P0",
    # High
    "high": "P1", "p1": "P1", "major": "P1", "sev2": "P1", "s2": "P1",
    # Medium
    "medium": "P2", "p2": "P2", "moderate": "P2", "normal": "P2",
    "sev3": "P2", "s3": "P2",
    # Low
    "low": "P3", "p3": "P3", "minor": "P3", "sev4": "P3", "s4": "P3",
    # Lowest
    "lowest": "P4", "p4": "P4", "trivial": "P4", "cosmetic": "P4",
}


def normalize_priority(raw: str | None) -> str | None:
    if not raw:
        return None
    return _PRIORITY_MAP.get(raw.strip().lower())


# ---------------------------------------------------------------------------
# External URL extraction
# ---------------------------------------------------------------------------

# Matches a wide set of useful link types. Order matters only for capture
# specificity; we dedupe afterward.
_URL_RE = re.compile(r"https?://[^\s<>\"')\]]+", re.IGNORECASE)

_HOST_PATTERNS = [
    re.compile(r"\.atlassian\.net/wiki", re.IGNORECASE),       # Confluence
    re.compile(r"github\.com/.+/(pull|issues|commit)/", re.IGNORECASE),
    re.compile(r"figma\.com/", re.IGNORECASE),
    re.compile(r"docs\.google\.com/", re.IGNORECASE),
    re.compile(r"drive\.google\.com/", re.IGNORECASE),
    re.compile(r"notion\.so/", re.IGNORECASE),
    re.compile(r"miro\.com/", re.IGNORECASE),
    re.compile(r"loom\.com/", re.IGNORECASE),
    re.compile(r"moveinsync\.(com|in)/", re.IGNORECASE),
]


def extract_external_urls(*texts: str) -> list[str]:
    """Return deduplicated list of interesting external URLs found in any input."""
    seen: set[str] = set()
    out: list[str] = []
    for text in texts:
        if not text:
            continue
        for match in _URL_RE.finditer(text):
            url = match.group(0).rstrip(".,;:)")
            if url in seen:
                continue
            if any(p.search(url) for p in _HOST_PATTERNS):
                seen.add(url)
                out.append(url)
    return out


# ---------------------------------------------------------------------------
# Comments
# ---------------------------------------------------------------------------

def render_comments(comment_field: Any) -> tuple[int, str, str]:
    """
    From the Jira comment field structure, return:
      (count, plaintext_concatenation, raw_json_string).
    """
    if not isinstance(comment_field, dict):
        return 0, "", "[]"
    comments = comment_field.get("comments") or []
    if not isinstance(comments, list):
        return 0, "", "[]"

    rendered: list[str] = []
    for c in comments:
        author = ((c.get("author") or {}).get("displayName")) or "unknown"
        created = c.get("created") or ""
        body = c.get("body")
        text = adf_to_text(body) if isinstance(body, dict) else (str(body) if body else "")
        rendered.append(f"[{author}, {created}]\n{text.strip()}")

    return (
        len(comments),
        "\n\n---\n\n".join(rendered).strip(),
        json.dumps(comments, ensure_ascii=False),
    )


# ---------------------------------------------------------------------------
# Issue → row dict
# ---------------------------------------------------------------------------

def normalize_issue(
    raw: dict[str, Any],
    *,
    fa_field_id: str,
    source_filter: str,
    fetched_at: str,
) -> dict[str, Any]:
    """Convert one /search/jql or /issue/{key} response into a tickets row dict."""
    fields = raw.get("fields", {}) or {}
    key = raw.get("key") or ""
    project_key = (fields.get("project") or {}).get("key") or key.split("-")[0]

    # ------------------------- text fields -----------------------------
    description_raw = fields.get("description")
    description_text = adf_to_text(description_raw) if isinstance(description_raw, dict) else (
        str(description_raw or "")
    )
    summary = fields.get("summary") or ""
    resolution_text_field = fields.get("customfield_resolution_text")  # rare; usually empty
    resolution_text = ""
    if isinstance(resolution_text_field, dict):
        resolution_text = adf_to_text(resolution_text_field)
    elif resolution_text_field:
        resolution_text = str(resolution_text_field)

    # ------------------------- comments --------------------------------
    comment_count, comments_text, comments_raw_json = render_comments(fields.get("comment"))

    # ------------------------- status / priority / type ----------------
    status_obj = fields.get("status") or {}
    status_name = status_obj.get("name")
    status_category = ((status_obj.get("statusCategory") or {}).get("key")) or None
    issue_type = (fields.get("issuetype") or {}).get("name")
    priority_raw = (fields.get("priority") or {}).get("name")
    priority_canonical = normalize_priority(priority_raw)
    resolution_obj = fields.get("resolution") or {}
    resolution_name = resolution_obj.get("name") if isinstance(resolution_obj, dict) else None

    # ------------------------- people ----------------------------------
    reporter = fields.get("reporter") or {}
    assignee = fields.get("assignee") or {}

    # ------------------------- structure -------------------------------
    parent = fields.get("parent") or {}
    parent_key = parent.get("key") if isinstance(parent, dict) else None
    # In modern Jira Cloud the "epic" is just a parent of type Epic
    epic_key = None
    if isinstance(parent, dict):
        ptype = ((parent.get("fields") or {}).get("issuetype") or {}).get("name")
        if ptype and ptype.lower() == "epic":
            epic_key = parent_key

    components_json = json.dumps(
        [c.get("name") for c in (fields.get("components") or []) if isinstance(c, dict)],
        ensure_ascii=False,
    )
    labels_json = json.dumps(fields.get("labels") or [], ensure_ascii=False)

    issue_links = []
    for link in fields.get("issuelinks") or []:
        try:
            issue_links.append({
                "type": ((link.get("type") or {}).get("name")),
                "outward": (link.get("outwardIssue") or {}).get("key"),
                "inward":  (link.get("inwardIssue") or {}).get("key"),
            })
        except Exception:
            continue
    links_json = json.dumps(issue_links, ensure_ascii=False)

    attachments = []
    for a in fields.get("attachment") or []:
        if not isinstance(a, dict):
            continue
        attachments.append({
            "filename": a.get("filename"),
            "mimeType": a.get("mimeType"),
            "size":     a.get("size"),
            "created":  a.get("created"),
            "url":      a.get("content"),
        })
    attachments_json = json.dumps(attachments, ensure_ascii=False)

    external_urls = extract_external_urls(description_text, comments_text)
    external_urls_json = json.dumps(external_urls, ensure_ascii=False)

    # ------------------------- functional area -------------------------
    fa_value = _resolve_functional_area(fields.get(fa_field_id))

    # ------------------------- dates -----------------------------------
    created = fields.get("created") or _utcnow_iso()
    updated = fields.get("updated") or created
    resolved = fields.get("resolutiondate")

    # ------------------------- empty-shell flag ------------------------
    is_empty = (
        (not description_text or description_text.strip() == "")
        and comment_count == 0
        and (not resolution_text or resolution_text.strip() == "")
    )

    # ------------------------- raw description JSON --------------------
    description_raw_json = json.dumps(description_raw, ensure_ascii=False) if description_raw else None

    return {
        "key": key,
        "project": project_key,
        "type": issue_type,
        "status": status_name,
        "status_category": status_category,
        "priority": priority_canonical,
        "resolution": resolution_name,

        "summary": summary,
        "description_text": description_text,
        "description_raw_json": description_raw_json,
        "resolution_text": resolution_text or None,

        "comment_count": comment_count,
        "comments_text": comments_text or None,
        "comments_raw_json": comments_raw_json,

        "functional_area": fa_value,
        "components_json": components_json,
        "labels_json": labels_json,

        "reporter_account_id":   reporter.get("accountId") if isinstance(reporter, dict) else None,
        "reporter_display_name": reporter.get("displayName") if isinstance(reporter, dict) else None,
        "assignee_account_id":   assignee.get("accountId") if isinstance(assignee, dict) else None,
        "assignee_display_name": assignee.get("displayName") if isinstance(assignee, dict) else None,

        "parent_key": parent_key,
        "epic_key": epic_key,

        "links_json": links_json,
        "external_urls_json": external_urls_json,
        "attachments_json": attachments_json,

        "created_at": created,
        "updated_at": updated,
        "resolved_at": resolved,

        "fetched_at": fetched_at,
        "normalized_at": _utcnow_iso(),
        "source_filter": source_filter,

        "triage_tier": None,
        "triage_reason": "empty-shell" if is_empty else None,
        "last_triaged_at": None,
        "embedding_id": None,
    }


def _resolve_functional_area(value: Any) -> str | None:
    """Functional Area is a single-select option field. Extract its `value`."""
    if value is None:
        return None
    if isinstance(value, dict):
        return value.get("value") or value.get("name") or None
    if isinstance(value, list) and value:
        first = value[0]
        if isinstance(first, dict):
            return first.get("value") or first.get("name") or None
        return str(first)
    return str(value)


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
