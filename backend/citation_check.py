"""Inline citation verification (spec §5.9) — mechanical set-membership,
no LLM, runs before the response ships. The async quality judge remains
telemetry-only; this is the gate."""
from __future__ import annotations
import re
from dataclasses import dataclass, field

_WIKI_CITE_RE = re.compile(r"`?([a-z0-9-]+(?:/[a-z0-9._-]+)+\.md(?:#[a-z0-9-]+)?)`?")
_KEY_RE = re.compile(r"\b([A-Z]{2,}-\d{2,6})\b")


@dataclass
class CitationReport:
    cited_ok: list[str] = field(default_factory=list)
    cited_unverified: list[str] = field(default_factory=list)

    @property
    def confidence_capped(self) -> bool:
        return bool(self.cited_unverified)


def verify_citations(answer_text: str, wiki_anchors: set[str],
                     jira_keys: set[str]) -> CitationReport:
    """Extract cited wiki paths/anchors and Jira ticket keys from the answer
    text and check each against the evidence actually retrieved for this
    query. A page-level citation (`modules/a.md`) is considered verified if
    ANY section of that page appears in the evidence set (section-level
    anchors are a stricter form of page-level evidence)."""
    pages_with_evidence = {a.split("#", 1)[0] for a in wiki_anchors}
    rep = CitationReport()

    for m in dict.fromkeys(_WIKI_CITE_RE.findall(answer_text)):
        ok = (m in wiki_anchors
              or m.split("#", 1)[0] in pages_with_evidence)
        (rep.cited_ok if ok else rep.cited_unverified).append(m)

    for k in dict.fromkeys(_KEY_RE.findall(answer_text)):
        (rep.cited_ok if k in jira_keys else rep.cited_unverified).append(k)
    return rep
