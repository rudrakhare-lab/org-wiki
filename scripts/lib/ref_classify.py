"""Classify a URL into a crawl ref_type and extract a Drive file-ID."""
from __future__ import annotations

import re

_DRIVE_ID = re.compile(r"/d/([a-zA-Z0-9_-]+)")
_API_HOST = re.compile(r"(moveinsync\.com|moveinsync\.in|workinsync\.io|amazonaws\.com)", re.I)


def _file_id(url: str) -> str | None:
    m = _DRIVE_ID.search(url)
    return m.group(1) if m else None


def classify_url(url: str) -> tuple[str, str | None]:
    u = url.lower()
    if "docs.google.com/document/" in u:
        return "gdoc", _file_id(url)
    if "docs.google.com/spreadsheets/" in u:
        return "gsheet", _file_id(url)
    if "docs.google.com/presentation/" in u:
        return "gslide", _file_id(url)
    if "atlassian.net/browse/" in u or "atlassian.net/issues/" in u:
        return "jira", None
    if u.startswith("mailto:"):
        return "external", None
    if _API_HOST.search(u):
        return "api", None
    return "external", None
