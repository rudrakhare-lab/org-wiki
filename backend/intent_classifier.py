from __future__ import annotations
import re
from dataclasses import dataclass
from enum import Enum


class QueryIntent(str, Enum):
    DEFINITION    = "DEFINITION"
    CONFIGURATION = "CONFIGURATION"
    DEBUGGING     = "DEBUGGING"
    HOW_TO        = "HOW_TO"
    COMPARISON    = "COMPARISON"
    ARCHITECTURAL = "ARCHITECTURAL"
    STATUS        = "STATUS"
    GENERAL       = "GENERAL"


@dataclass
class IntentResult:
    intent: QueryIntent
    rewritten_query: str
    confidence: float
    retrieval_hints: dict


_HINTS: dict[QueryIntent, dict] = {
    QueryIntent.DEFINITION:    {"wiki_top_n": 4, "jira_latest_limit": 2, "boost_config_pages": False},
    QueryIntent.CONFIGURATION: {"wiki_top_n": 4, "jira_latest_limit": 2, "boost_config_pages": True},
    QueryIntent.DEBUGGING:     {"wiki_top_n": 3, "jira_latest_limit": 4, "boost_config_pages": False},
    QueryIntent.HOW_TO:        {"wiki_top_n": 4, "jira_latest_limit": 2, "boost_config_pages": False},
    QueryIntent.COMPARISON:    {"wiki_top_n": 5, "jira_latest_limit": 2, "boost_config_pages": False},
    QueryIntent.ARCHITECTURAL: {"wiki_top_n": 4, "jira_latest_limit": 2, "boost_config_pages": False},
    QueryIntent.STATUS:        {"wiki_top_n": 3, "jira_latest_limit": 4, "boost_config_pages": False},
    QueryIntent.GENERAL:       {"wiki_top_n": 3, "jira_latest_limit": 2, "boost_config_pages": False},
}

_CAMEL_RE = re.compile(
    r"\b[a-z][a-z0-9]*(?:[A-Z][a-z0-9]*)+[a-zA-Z0-9]*\b"
    r"|\b[A-Z]{2,}[a-z][a-zA-Z0-9]*\b"
)
_JIRA_KEY_RE = re.compile(r"\b[A-Z]{2,5}-\d{3,6}\b")
_DEBUG_STRONG   = re.compile(r"\b(broken|bug|error)\b|not\s+work(?:ing)?|doesn'?t\s+work")
_DEBUG_MODERATE = re.compile(r"\bfailing\b|doesn'?t\s+show|not\s+showing")
_DEBUG_WEAK     = re.compile(r"\b(issue|problem|incorrect|missing)\b|wrong\s+value")


def _count_uppercase(tokens: list[str]) -> int:
    return max((sum(1 for c in t if c.isupper()) for t in tokens), default=0)


def _score(q: str) -> tuple[QueryIntent, float]:
    ql = q.lower()
    camel_tokens = _CAMEL_RE.findall(q)
    has_camel = bool(camel_tokens)
    is_complex_camel = _count_uppercase(camel_tokens) >= 3
    has_config_verb  = bool(re.search(r"\b(configure|configured|configuration)\b", ql))
    has_config_noun  = bool(re.search(r"\b(config|property|setting|settings|pms)\b", ql))
    has_what_is      = bool(re.search(r"^what\s+(is|are|does|do)\b", ql))
    scores: dict[QueryIntent, float] = {}

    # CONFIGURATION
    if has_camel and has_what_is:
        scores[QueryIntent.CONFIGURATION] = 3.0
    elif has_config_verb:
        scores[QueryIntent.CONFIGURATION] = 3.0 + (1.0 if has_camel else 0.0)
    elif has_camel and has_config_noun:
        scores[QueryIntent.CONFIGURATION] = 3.0
    elif has_config_noun:
        scores[QueryIntent.CONFIGURATION] = 2.0
    elif has_camel:
        scores[QueryIntent.CONFIGURATION] = 3.0 if is_complex_camel else 1.5

    # DEBUGGING
    if _DEBUG_STRONG.search(ql):
        scores[QueryIntent.DEBUGGING] = 2.5
    elif _DEBUG_MODERATE.search(ql):
        scores[QueryIntent.DEBUGGING] = 2.0
    elif _DEBUG_WEAK.search(ql):
        scores[QueryIntent.DEBUGGING] = 1.0
    if re.search(r"why\s+(is|does|did|are|isn'?t|aren'?t|doesn'?t|don'?t)\b", ql) \
            and re.search(r"\b(not|broken|fail)\b", ql):
        scores[QueryIntent.DEBUGGING] = max(scores.get(QueryIntent.DEBUGGING, 0), 2.0)

    # DEFINITION
    if has_what_is and not has_camel:
        scores[QueryIntent.DEFINITION] = 2.0
    if re.search(r"^(define|explain)\b", ql):
        scores[QueryIntent.DEFINITION] = max(scores.get(QueryIntent.DEFINITION, 0), 2.0)
    if re.search(r"\bmeaning\s+of\b|what\s+does\s+\w+\s+mean", ql):
        scores[QueryIntent.DEFINITION] = max(scores.get(QueryIntent.DEFINITION, 0), 1.5)

    # HOW_TO
    if re.search(r"^how\s+(do|can|should)\b", ql):
        scores[QueryIntent.HOW_TO] = 2.0
    elif re.search(r"^how\s+to\b", ql) and not has_config_verb:
        scores[QueryIntent.HOW_TO] = 2.0
    if re.search(r"\bsteps?\s+to\b", ql):
        scores[QueryIntent.HOW_TO] = max(scores.get(QueryIntent.HOW_TO, 0), 2.0)
    if re.search(r"\bhow\s+(do|can)\s+(i|we|you)\b", ql):
        scores[QueryIntent.HOW_TO] = max(scores.get(QueryIntent.HOW_TO, 0), 2.0)
    if re.search(r"\b(enable|disable|set\s+up|turn\s+on|turn\s+off|activate|deactivate)\b", ql) \
            and not has_config_verb:
        scores[QueryIntent.HOW_TO] = scores.get(QueryIntent.HOW_TO, 0) + 1.0

    # COMPARISON
    if re.search(r"\bvs\.?\b|\bversus\b", ql):
        scores[QueryIntent.COMPARISON] = 2.0
    if re.search(r"\bdifference\s+between\b", ql):
        scores[QueryIntent.COMPARISON] = max(scores.get(QueryIntent.COMPARISON, 0), 2.0)
    if re.search(r"\bcompare\b.+\b(to|with|and)\b", ql):
        scores[QueryIntent.COMPARISON] = max(scores.get(QueryIntent.COMPARISON, 0), 1.5)
    if re.search(r"\b(better|worse|same\s+as)\b", ql):
        scores[QueryIntent.COMPARISON] = max(scores.get(QueryIntent.COMPARISON, 0), 1.5)

    # ARCHITECTURAL
    if re.search(r"\b(architecture|architectural|diagram|dependency|dependencies)\b", ql):
        scores[QueryIntent.ARCHITECTURAL] = 2.0
    if re.search(r"\b(design|flow|structured|integrated)\b", ql):
        scores[QueryIntent.ARCHITECTURAL] = max(scores.get(QueryIntent.ARCHITECTURAL, 0), 2.0)
    if re.search(r"how\s+does\s+.+\s+work\b", ql):
        scores[QueryIntent.ARCHITECTURAL] = max(scores.get(QueryIntent.ARCHITECTURAL, 0), 2.0)
    if re.search(r"how\s+(is|are)\s+\w+\s+(built|structured|connected|integrated)", ql):
        scores[QueryIntent.ARCHITECTURAL] = max(scores.get(QueryIntent.ARCHITECTURAL, 0), 2.0)

    # STATUS
    if re.search(r"\bstatus\s+(of|for|on)\b", ql):
        scores[QueryIntent.STATUS] = 2.0
    if re.search(r"\blatest\s+(update|news|status)\b", ql):
        scores[QueryIntent.STATUS] = max(scores.get(QueryIntent.STATUS, 0), 2.0)
    if re.search(r"\bwhat\s+happened\s+(with|to)\b", ql):
        scores[QueryIntent.STATUS] = max(scores.get(QueryIntent.STATUS, 0), 1.5)
    if _JIRA_KEY_RE.search(q):
        scores[QueryIntent.STATUS] = max(scores.get(QueryIntent.STATUS, 0), 2.0)
    if re.search(r"\b(is|are)\s+\w+\s+(working|live|deployed|fixed|resolved)\b", ql):
        scores[QueryIntent.STATUS] = max(scores.get(QueryIntent.STATUS, 0), 1.5)

    if not scores:
        return QueryIntent.GENERAL, 0.4
    best_intent = max(scores, key=lambda k: scores[k])
    best_score = scores[best_intent]
    if best_score < 1.5:
        return QueryIntent.GENERAL, 0.4
    if best_score >= 3.0:
        conf = min(0.95, 0.85 + (best_score - 3.0) * 0.025)
    elif best_score >= 2.0:
        conf = 0.75
    else:
        conf = 0.65
    return best_intent, conf


def _rewrite(question: str) -> str:
    if len(question.split()) >= 5:
        return question
    ql = question.lower()
    if re.search(r"\b(configure|config|property|setting)\b", ql):
        if not re.search(r"^how\s+(to|do|can)", ql):
            return f"how to configure {question.strip()} in WorkInSync"
    return question


def classify_intent(question: str) -> IntentResult:
    intent, confidence = _score(question)
    return IntentResult(
        intent=intent,
        rewritten_query=_rewrite(question),
        confidence=confidence,
        retrieval_hints=_HINTS[intent].copy(),
    )
