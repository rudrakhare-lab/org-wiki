"""Claude-Haiku query decomposer for Jira Retrieval v2.

Decomposes compound questions into sub-queries, expands synonyms, extracts
filters (functional_area, resolved_after, module). Cached for 5 minutes on
identical question strings to keep cost down at ~₹1 per query.
"""
from __future__ import annotations
import json
import os
import re
import threading
import time
from dataclasses import dataclass, field

import anthropic

_MODEL = "claude-haiku-4-5-20251001"
_CACHE_TTL = 300  # seconds
_CACHE_MAX = 128  # bounded cache — evict oldest insertions beyond this
_cache_lock = threading.Lock()
_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)

@dataclass
class RewriteResult:
    sub_queries: list[str]
    expansions: dict[str, list[str]] = field(default_factory=dict)
    filters: dict = field(default_factory=dict)
    intent: str = "GENERAL"

_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))
_cache: dict[str, tuple[float, RewriteResult]] = {}

_SYSTEM = (
    "You are a query analyzer for a Jira knowledge base. Given a user question, "
    "output a JSON object with these keys:\n"
    "  sub_queries: list[str] — break compound questions into focused sub-queries; "
    "for a single question, return a one-element list of the original or a "
    "lightly normalized version.\n"
    "  expansions: dict[str, list[str]] — acronyms/synonyms only when you are "
    "confident (e.g. {\"OTP\":[\"one-time password\"]}).\n"
    "  filters: dict — set only when the user is explicit. Allowed keys: "
    "functional_area, module, resolved_after (YYYY-MM-DD), status_category.\n"
    "  intent: one of DEBUGGING, STATUS, DEFINITION, CONFIGURATION, COMPARISON, "
    "HOW_TO, ARCHITECTURAL, GENERAL.\n"
    "Output JSON only. No prose."
)

def _client_messages():
    """Test seam: returns the anthropic messages API object."""
    return _client.messages

def _raw_completion(question: str) -> str:
    """Test seam: one Haiku call, returns raw text."""
    resp = _client_messages().create(
        model=_MODEL,
        max_tokens=600,
        system=_SYSTEM,
        messages=[{"role": "user", "content": question}],
    )
    return resp.content[0].text if resp.content else ""

def _call_claude(question: str) -> RewriteResult:
    try:
        raw = _raw_completion(question)
        raw = _FENCE_RE.sub("", raw.strip())
        data = json.loads(raw)
        return RewriteResult(
            sub_queries=list(data.get("sub_queries") or [question]) or [question],
            expansions=dict(data.get("expansions") or {}),
            filters=dict(data.get("filters") or {}),
            intent=str(data.get("intent") or "GENERAL"),
        )
    except Exception:
        # Any failure — API error, fence weirdness, bad JSON — degrades to a
        # pass-through rewrite. A broken rewriter must never kill retrieval.
        return RewriteResult(sub_queries=[question])

def rewrite(question: str) -> RewriteResult:
    now = time.time()
    with _cache_lock:
        cached = _cache.get(question)
        if cached and now - cached[0] < _CACHE_TTL:
            return cached[1]
    result = _call_claude(question)
    with _cache_lock:
        _cache[question] = (now, result)
        while len(_cache) > _CACHE_MAX:
            _cache.pop(next(iter(_cache)))  # evict oldest insertion
    return result
