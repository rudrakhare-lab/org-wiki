"""
Jira retriever — wraps fetch_ranked() from scripts/query_jira_ranked.py.

Opens the SQLite DB read-only (safe for concurrent backend access).
Extracts a search keyword from the user's free-text question.
"""
from __future__ import annotations

import re
import sqlite3
import sys
from pathlib import Path

# Make scripts/ importable without installing as a package
_SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from query_jira_ranked import fetch_ranked, render_markdown  # noqa: E402

from backend.config import JIRA_DB

# Common English stop-words to strip before keyword extraction
_STOPWORDS = {
    "a", "an", "the", "is", "in", "on", "at", "to", "for", "of", "and",
    "or", "not", "with", "what", "how", "why", "when", "where", "which",
    "does", "do", "can", "will", "should", "would", "could", "has", "have",
    "this", "that", "it", "be", "are", "was", "were", "by", "from",
}


def _open_readonly() -> sqlite3.Connection:
    if not JIRA_DB.exists():
        raise FileNotFoundError(f"Jira SQLite DB not found: {JIRA_DB}")
    # mode=ro prevents accidental writes; immutable=1 skips WAL lock acquisition
    uri = f"file:{JIRA_DB}?mode=ro&immutable=1"
    return sqlite3.connect(uri, uri=True, check_same_thread=False)


def extract_keywords(question: str, max_terms: int = 3) -> list[str]:
    """
    Extract 1–3 meaningful search terms from a free-text question.

    Returns a list ordered from most-specific (full camelCase property names,
    quoted strings) to most-general (plain words).
    """
    # Quoted strings are most explicit
    quoted = re.findall(r'"([^"]+)"', question)

    # Full camelCase tokens (the whole word, e.g. kioskRequireOTPBeforeRegister)
    # A camelCase word contains at least one internal uppercase letter
    all_tokens = re.findall(r"\b[a-zA-Z][a-zA-Z0-9]+\b", question)
    camel = [t for t in all_tokens if re.search(r"[a-z][A-Z]", t) or re.search(r"[A-Z]{2,}", t)]

    # Remaining meaningful tokens (>3 chars, not a stopword)
    plain = [t.lower() for t in all_tokens if t.lower() not in _STOPWORDS and len(t) > 3]

    # Build deduplicated ordered list: quoted → camel → plain
    seen: set[str] = set()
    result: list[str] = []
    for term in quoted + camel + plain:
        key = term.lower()
        if key not in seen:
            seen.add(key)
            result.append(term)
        if len(result) >= max_terms:
            break

    return result or plain[:1] or [question[:40]]


def search(
    question: str,
    functional_area: str | None = None,
    limit: int = 25,
    include_stale: bool = False,
) -> dict:
    """
    Run ranked Jira search for a question. Returns a dict with:
      - keywords: list of terms searched
      - markdown: formatted evidence string (ready for system prompt)
      - rows: raw row dicts from fetch_ranked()
      - buckets: {"LATEST": [...], "HISTORICAL": [...], "STALE-OPEN": [...]}
    """
    keywords = extract_keywords(question)
    if not keywords:
        return {
            "keywords": [],
            "markdown": "No Jira search performed — no meaningful keywords found.",
            "rows": [],
            "buckets": {"LATEST": [], "HISTORICAL": [], "STALE-OPEN": []},
        }

    conn = _open_readonly()
    try:
        # Search with the best keyword; merge if multiple terms
        all_rows: list[dict] = []
        seen_keys: set[str] = set()
        for kw in keywords:
            rows = fetch_ranked(conn, kw, functional_area, limit)
            for r in rows:
                if r["key"] not in seen_keys:
                    seen_keys.add(r["key"])
                    all_rows.append(r)
    finally:
        conn.close()

    # Re-sort merged rows by bucket order then recency (fetch_ranked already sorts,
    # but merging across keywords can shuffle)
    bucket_order = {"LATEST": 0, "HISTORICAL": 1, "STALE-OPEN": 2}
    all_rows.sort(key=lambda r: (bucket_order.get(r["bucket"], 3), -r.get("content_size", 0)))

    buckets: dict[str, list] = {"LATEST": [], "HISTORICAL": [], "STALE-OPEN": []}
    for r in all_rows:
        buckets[r["bucket"]].append(r)

    primary_kw = keywords[0]
    markdown = render_markdown(primary_kw, all_rows, functional_area, include_stale)

    return {
        "keywords": keywords,
        "markdown": markdown,
        "rows": all_rows,
        "buckets": buckets,
    }
