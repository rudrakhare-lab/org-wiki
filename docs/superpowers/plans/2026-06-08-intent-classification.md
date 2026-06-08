# Query Intent Classification — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add zero-cost (no LLM call) query intent classification that runs inside `run_preflight()` before every retrieval, tunes retrieval params per intent, surfaces `intent`/`rewritten_query`/`intent_confidence` in the API response, and shows an intent badge in the Angular chat UI.

**Architecture:** `classify_intent()` (pure regex/keyword, no I/O) is called at the top of `run_preflight()`. Its `IntentResult` is stored in `PreflightBundle` and used to (a) rewrite the search query, (b) override `wiki_top_n` and `jira_latest_limit`, and (c) add an intent header to the seed message. The intent travels through `OrchestratorResult → QueryResponse → ChatMessage` to the Angular badge.

**Tech Stack:** Python 3.13, dataclasses, stdlib `re`; FastAPI Pydantic models; Angular 17 `@if` control flow, CSS attribute selectors.

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `backend/intent_classifier.py` | CREATE | `QueryIntent` enum, `IntentResult` dataclass, `classify_intent()` |
| `tests/test_intent_classifier.py` | CREATE | 18 test cases (written first — TDD) |
| `backend/preflight.py` | MODIFY | `PreflightBundle.intent_result`, hints applied in `run_preflight()`, header in `build_seed_message()` + `build_agent_preamble()` |
| `backend/orchestrator.py` | MODIFY | `OrchestratorResult` new fields, populated in `run_deep()` |
| `backend/api.py` | MODIFY | `QueryResponse` Pydantic model new fields, populated in `/query` handler |
| `frontend/src/app/core/api.service.ts` | MODIFY | `QueryResponse` + `ChatMessage` TS interfaces |
| `frontend/src/app/features/ask/ask.ts` | MODIFY | badge template, helper methods, `appendAssistantFromResponse()` |
| `frontend/src/app/features/ask/ask.scss` | MODIFY | `.pill-intent` styles |

---

### Task 1: TDD — write all tests before any implementation

**Files:**
- Create: `tests/test_intent_classifier.py`

- [ ] **Step 1: Create the test file with all 18 test cases**

```python
# tests/test_intent_classifier.py
"""
Tests for backend.intent_classifier.
All tests are pure — no DB, no HTTP, no subprocess.
Run: venv/bin/pytest tests/test_intent_classifier.py -v
"""
import pytest
from backend.intent_classifier import classify_intent, QueryIntent, IntentResult


# ── CONFIGURATION ──────────────────────────────────────────────────────────────

def test_camelcase_what_is_is_configuration():
    r = classify_intent("what is kioskRequireOTPBeforeRegister")
    assert r.intent == QueryIntent.CONFIGURATION
    assert r.confidence >= 0.85


def test_how_to_configure_is_configuration():
    r = classify_intent("how to configure visitor OTP")
    assert r.intent == QueryIntent.CONFIGURATION
    assert r.retrieval_hints["boost_config_pages"] is True


def test_camelcase_config_noun_is_configuration():
    r = classify_intent("showEmployeeOfficePlan config")
    assert r.intent == QueryIntent.CONFIGURATION
    assert r.confidence >= 0.80


# ── DEBUGGING ──────────────────────────────────────────────────────────────────

def test_not_working_is_debugging():
    r = classify_intent("OTP not working for visitors")
    assert r.intent == QueryIntent.DEBUGGING
    assert r.retrieval_hints["jira_latest_limit"] >= 4


def test_broken_beats_status_in_debugging():
    # "broken" (strong debug signal) must beat "latest update" (status signal)
    r = classify_intent("visitor check-in broken after latest update")
    assert r.intent == QueryIntent.DEBUGGING


def test_error_with_simple_camel_is_debugging_not_config():
    # kioskMode has only 1 uppercase → weak config signal; "error" wins
    r = classify_intent("kioskMode error on floor kiosk")
    assert r.intent == QueryIntent.DEBUGGING


# ── DEFINITION ─────────────────────────────────────────────────────────────────

def test_what_is_plain_term_is_definition():
    r = classify_intent("what is SSO")
    assert r.intent == QueryIntent.DEFINITION
    assert r.rewritten_query == "what is SSO"   # short but no config kw → no rewrite


def test_define_keyword_is_definition():
    r = classify_intent("define meal management")
    assert r.intent == QueryIntent.DEFINITION


# ── HOW_TO ─────────────────────────────────────────────────────────────────────

def test_how_do_i_enable_is_how_to():
    r = classify_intent("how do I enable desk booking")
    assert r.intent == QueryIntent.HOW_TO


def test_steps_to_is_how_to():
    r = classify_intent("steps to set up parking management")
    assert r.intent == QueryIntent.HOW_TO


# ── COMPARISON ─────────────────────────────────────────────────────────────────

def test_difference_between_is_comparison():
    r = classify_intent("difference between .in and .com server")
    assert r.intent == QueryIntent.COMPARISON
    assert r.retrieval_hints["wiki_top_n"] >= 5


def test_vs_is_comparison():
    r = classify_intent("visitor vs meeting rooms")
    assert r.intent == QueryIntent.COMPARISON


# ── ARCHITECTURAL ──────────────────────────────────────────────────────────────

def test_how_does_flow_work_is_architectural():
    r = classify_intent("how does the SSO auth flow work")
    assert r.intent == QueryIntent.ARCHITECTURAL


def test_architecture_keyword_is_architectural():
    r = classify_intent("architecture of the booking rule engine")
    assert r.intent == QueryIntent.ARCHITECTURAL
    assert r.retrieval_hints["wiki_top_n"] >= 4


# ── STATUS ─────────────────────────────────────────────────────────────────────

def test_status_of_is_status():
    r = classify_intent("status of visitor rollout")
    assert r.intent == QueryIntent.STATUS
    assert r.retrieval_hints["jira_latest_limit"] >= 4


def test_latest_update_with_jira_key_is_status():
    r = classify_intent("latest update on PB-12345")
    assert r.intent == QueryIntent.STATUS


# ── GENERAL ────────────────────────────────────────────────────────────────────

def test_vague_query_is_general_low_confidence():
    r = classify_intent("tell me about WorkInSync")
    assert r.intent == QueryIntent.GENERAL
    assert r.confidence < 0.65


def test_single_word_is_general_query_unchanged():
    r = classify_intent("help")
    assert r.intent == QueryIntent.GENERAL
    assert r.rewritten_query == "help"


# ── BEHAVIORAL / CROSS-CUTTING ─────────────────────────────────────────────────

def test_complex_camelcase_alone_is_high_confidence_configuration():
    # Long property name alone (≥3 uppercase transitions) → strong CONFIGURATION
    r = classify_intent("kioskRequireOTPBeforeRegister")
    assert r.intent == QueryIntent.CONFIGURATION
    assert r.confidence >= 0.85


def test_debugging_hints_have_high_jira_limit():
    r = classify_intent("something is broken")
    assert r.intent == QueryIntent.DEBUGGING
    assert r.retrieval_hints["jira_latest_limit"] >= 4


def test_long_query_rewritten_query_preserved():
    q = "how does the booking rule engine prioritize desk reservations for employees"
    r = classify_intent(q)
    assert r.rewritten_query == q   # ≥5 tokens → no rewriting


def test_intent_result_is_dataclass_with_all_fields():
    r = classify_intent("what is SSO")
    assert isinstance(r, IntentResult)
    assert isinstance(r.intent, QueryIntent)
    assert isinstance(r.rewritten_query, str)
    assert 0.0 <= r.confidence <= 1.0
    assert "wiki_top_n" in r.retrieval_hints
    assert "jira_latest_limit" in r.retrieval_hints
    assert "boost_config_pages" in r.retrieval_hints
```

- [ ] **Step 2: Run tests to confirm they all FAIL (module doesn't exist yet)**

```bash
cd /Users/rudrakhare/Desktop/my-wiki/org-wiki
venv/bin/pytest tests/test_intent_classifier.py -v 2>&1 | head -20
```

Expected: `ModuleNotFoundError: No module named 'backend.intent_classifier'`

---

### Task 2: Implement `backend/intent_classifier.py`

**Files:**
- Create: `backend/intent_classifier.py`

- [ ] **Step 1: Create the file**

```python
# backend/intent_classifier.py
"""
Query intent classifier — pure Python regex/keyword heuristics.
No LLM calls, no I/O, no external dependencies.
Runs in microseconds before every retrieval call.
"""
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
    rewritten_query: str      # original or context-expanded for short vague queries
    confidence: float         # 0.0–1.0
    retrieval_hints: dict     # keys: wiki_top_n, jira_latest_limit, boost_config_pages


# Retrieval parameter overrides per intent
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

# lowerCamelCase: starts lowercase, has ≥1 uppercase transition (kioskMode, showEmployeeOfficePlan)
# UPPER-init camelCase: 2+ uppercase then lowercase (OTPBefore...) — excludes pure-caps like SSO/OTP
_CAMEL_RE = re.compile(
    r"\b[a-z][a-z0-9]*(?:[A-Z][a-z0-9]*)+[a-zA-Z0-9]*\b"
    r"|\b[A-Z]{2,}[a-z][a-zA-Z0-9]*\b"
)

_JIRA_KEY_RE = re.compile(r"\b[A-Z]{2,5}-\d{3,6}\b")

# Debug signal regexes (checked in order of strength)
_DEBUG_STRONG   = re.compile(r"\b(broken|bug|error)\b|not\s+work(?:ing)?|doesn'?t\s+work")
_DEBUG_MODERATE = re.compile(r"\bfailing\b|doesn'?t\s+show|not\s+showing")
_DEBUG_WEAK     = re.compile(r"\b(issue|problem|incorrect|missing)\b|wrong\s+value")


def _count_uppercase(tokens: list[str]) -> int:
    """Return max uppercase-letter count across camelCase tokens.
    Used to distinguish complex property names from simple two-part camelCase."""
    return max((sum(1 for c in t if c.isupper()) for t in tokens), default=0)


def _score(q: str) -> tuple[QueryIntent, float]:
    ql = q.lower()

    camel_tokens = _CAMEL_RE.findall(q)
    has_camel = bool(camel_tokens)
    is_complex_camel = _count_uppercase(camel_tokens) >= 3  # e.g. kioskRequireOTPBeforeRegister

    has_config_verb  = bool(re.search(r"\b(configure|configured|configuration)\b", ql))
    has_config_noun  = bool(re.search(r"\b(config|property|setting|settings|pms)\b", ql))
    has_what_is      = bool(re.search(r"^what\s+(is|are|does|do)\b", ql))

    scores: dict[QueryIntent, float] = {}

    # ── CONFIGURATION (priority 1) ─────────────────────────────────────────────
    if has_camel and has_what_is:
        # "what is kioskRequireOTPBeforeRegister" → property lookup
        scores[QueryIntent.CONFIGURATION] = 3.0
    elif has_config_verb:
        # "configure/configuration" verb is unambiguous config intent
        scores[QueryIntent.CONFIGURATION] = 3.0 + (1.0 if has_camel else 0.0)
    elif has_camel and has_config_noun:
        # camelCase property + config noun together
        scores[QueryIntent.CONFIGURATION] = 3.0
    elif has_config_noun:
        scores[QueryIntent.CONFIGURATION] = 2.0
    elif has_camel:
        # Standalone camelCase: complex property names score high, simple ones score low
        scores[QueryIntent.CONFIGURATION] = 3.0 if is_complex_camel else 1.5

    # ── DEBUGGING (priority 2) ─────────────────────────────────────────────────
    if _DEBUG_STRONG.search(ql):
        scores[QueryIntent.DEBUGGING] = 2.5
    elif _DEBUG_MODERATE.search(ql):
        scores[QueryIntent.DEBUGGING] = 2.0
    elif _DEBUG_WEAK.search(ql):
        scores[QueryIntent.DEBUGGING] = 1.0
    if re.search(r"why\s+(is|does|did|are|isn'?t|aren'?t|doesn'?t|don'?t)\b", ql) \
            and re.search(r"\b(not|broken|fail)\b", ql):
        scores[QueryIntent.DEBUGGING] = max(scores.get(QueryIntent.DEBUGGING, 0), 2.0)

    # ── DEFINITION (priority 3) ────────────────────────────────────────────────
    # Skip "what is <camelCase>" — already scored as CONFIGURATION above
    if has_what_is and not has_camel:
        scores[QueryIntent.DEFINITION] = 2.0
    if re.search(r"^(define|explain)\b", ql):
        scores[QueryIntent.DEFINITION] = max(scores.get(QueryIntent.DEFINITION, 0), 2.0)
    if re.search(r"\bmeaning\s+of\b|what\s+does\s+\w+\s+mean", ql):
        scores[QueryIntent.DEFINITION] = max(scores.get(QueryIntent.DEFINITION, 0), 1.5)

    # ── HOW_TO (priority 4) ────────────────────────────────────────────────────
    # "how to configure" → CONFIGURATION (has_config_verb=True), so exclude here
    if re.search(r"^how\s+(do|can|should)\b", ql):
        scores[QueryIntent.HOW_TO] = 2.0
    elif re.search(r"^how\s+to\b", ql) and not has_config_verb:
        scores[QueryIntent.HOW_TO] = 2.0
    if re.search(r"\bsteps?\s+to\b", ql):
        scores[QueryIntent.HOW_TO] = max(scores.get(QueryIntent.HOW_TO, 0), 2.0)
    if re.search(r"\bhow\s+(do|can)\s+(i|we|you)\b", ql):
        scores[QueryIntent.HOW_TO] = max(scores.get(QueryIntent.HOW_TO, 0), 2.0)
    # "enable/set up/activate" adds bonus on top of existing HOW_TO score
    if re.search(r"\b(enable|disable|set\s+up|turn\s+on|turn\s+off|activate|deactivate)\b", ql) \
            and not has_config_verb:
        scores[QueryIntent.HOW_TO] = scores.get(QueryIntent.HOW_TO, 0) + 1.0

    # ── COMPARISON (priority 5) ────────────────────────────────────────────────
    if re.search(r"\bvs\.?\b|\bversus\b", ql):
        scores[QueryIntent.COMPARISON] = 2.0
    if re.search(r"\bdifference\s+between\b", ql):
        scores[QueryIntent.COMPARISON] = max(scores.get(QueryIntent.COMPARISON, 0), 2.0)
    if re.search(r"\bcompare\b.+\b(to|with|and)\b", ql):
        scores[QueryIntent.COMPARISON] = max(scores.get(QueryIntent.COMPARISON, 0), 1.5)
    if re.search(r"\b(better|worse|same\s+as)\b", ql):
        scores[QueryIntent.COMPARISON] = max(scores.get(QueryIntent.COMPARISON, 0), 1.5)

    # ── ARCHITECTURAL (priority 6) ─────────────────────────────────────────────
    if re.search(r"\b(architecture|architectural|diagram|dependency|dependencies)\b", ql):
        scores[QueryIntent.ARCHITECTURAL] = 2.0
    if re.search(r"\b(design|flow|structured|integrated)\b", ql):
        scores[QueryIntent.ARCHITECTURAL] = max(scores.get(QueryIntent.ARCHITECTURAL, 0), 2.0)
    if re.search(r"how\s+does\s+.+\s+work\b", ql):
        scores[QueryIntent.ARCHITECTURAL] = max(scores.get(QueryIntent.ARCHITECTURAL, 0), 2.0)
    if re.search(r"how\s+(is|are)\s+\w+\s+(built|structured|connected|integrated)", ql):
        scores[QueryIntent.ARCHITECTURAL] = max(scores.get(QueryIntent.ARCHITECTURAL, 0), 2.0)

    # ── STATUS (priority 7) ────────────────────────────────────────────────────
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

    # Score → confidence mapping
    if best_score >= 3.0:
        conf = min(0.95, 0.85 + (best_score - 3.0) * 0.025)
    elif best_score >= 2.0:
        conf = 0.75
    else:
        conf = 0.65

    return best_intent, conf


def _rewrite(question: str) -> str:
    """Expand short vague queries. Only rewrites when < 5 tokens AND a config
    keyword is present — otherwise returns question unchanged."""
    if len(question.split()) >= 5:
        return question
    if re.search(r"\b(configure|config|property|setting)\b", question.lower()):
        return f"how to configure {question.strip()} in WorkInSync"
    return question


def classify_intent(question: str) -> IntentResult:
    """Classify the user's query intent using regex/keyword heuristics.
    Pure function — no I/O, no external dependencies."""
    intent, confidence = _score(question)
    return IntentResult(
        intent=intent,
        rewritten_query=_rewrite(question),
        confidence=confidence,
        retrieval_hints=_HINTS[intent].copy(),
    )
```

- [ ] **Step 2: Run the tests — all should pass**

```bash
cd /Users/rudrakhare/Desktop/my-wiki/org-wiki
venv/bin/pytest tests/test_intent_classifier.py -v
```

Expected: `22 passed` (18 spec tests + 4 behavioral tests).

- [ ] **Step 3: Commit**

```bash
git add backend/intent_classifier.py tests/test_intent_classifier.py
git commit -m "feat: add QueryIntent classifier — pure regex/keyword heuristics, 22 tests"
```

---

### Task 3: Wire intent into `backend/preflight.py`

**Files:**
- Modify: `backend/preflight.py`

**Context:** `preflight.py` has four things to change:
1. Import `classify_intent` and `IntentResult`
2. Add `intent_result` field to `PreflightBundle`
3. In `run_preflight()` — call classifier at the top, apply hints
4. In `build_seed_message()` and `build_agent_preamble()` — add intent header line

- [ ] **Step 1: Add import at the top of `backend/preflight.py`**

The imports block currently ends around line 27 (`from backend.tools.registry import ToolRegistry, ToolTraceEntry`). Add after it:

```python
from backend.intent_classifier import classify_intent, IntentResult
```

- [ ] **Step 2: Add `intent_result` field to `PreflightBundle` (currently at line 71)**

Find the `PreflightBundle` dataclass. Add the new field as the last field:

```python
@dataclass
class PreflightBundle:
    """All preflight retrieval results, ready to be formatted."""
    seed_wiki: list = field(default_factory=list)
    seed_jira: dict = field(default_factory=dict)
    preflight_tickets: list[dict] = field(default_factory=list)
    preflight_trace: list[ToolTraceEntry] = field(default_factory=list)
    module_tagged_jira: list[dict] = field(default_factory=list)
    related_module_jira: list[dict] = field(default_factory=list)
    intent_result: "IntentResult | None" = field(default=None)   # NEW
```

- [ ] **Step 3: Write a quick smoke test for the wiring (run before changing `run_preflight`)**

```bash
cd /Users/rudrakhare/Desktop/my-wiki/org-wiki
venv/bin/python -c "
from backend.preflight import PreflightBundle
b = PreflightBundle()
print('intent_result default:', b.intent_result)
assert b.intent_result is None
print('OK')
"
```

Expected: `intent_result default: None` then `OK`.

- [ ] **Step 4: Update `run_preflight()` to call classifier and apply hints**

In `run_preflight()` (currently starts at line 100), add intent classification at the very top, before the wiki search. Then use `search_query` (instead of `question`) for all searches, and apply hint overrides:

```python
def run_preflight(
    question: str,
    functional_area: str | None = None,
    registry: ToolRegistry | None = None,
    latest_limit: int = _PREFLIGHT_LATEST_LIMIT,
    trace_id: str | None = None,
) -> PreflightBundle:
    """Run the deterministic preflight retrieval. Always runs for every query."""
    bundle = PreflightBundle()

    # ── Intent classification (runs before any retrieval) ──────────────────────
    intent_result = classify_intent(question)
    bundle.intent_result = intent_result
    search_query = intent_result.rewritten_query           # may differ from question
    hints = intent_result.retrieval_hints
    wiki_top_n_eff   = hints.get("wiki_top_n",        _PREFLIGHT_WIKI_TOP_N)
    latest_limit_eff = hints.get("jira_latest_limit", latest_limit)

    _t = time.perf_counter()
    bundle.seed_wiki = wiki_retriever.search(search_query, top_n=wiki_top_n_eff)  # was: question, _PREFLIGHT_WIKI_TOP_N
    trace_store.record_event(
        trace_id, "preflight", "preflight_wiki",
        duration_ms=int((time.perf_counter() - _t) * 1000), round_num=0,
        metadata={"results_count": len(bundle.seed_wiki),
                  "top_paths": [p.path for p in bundle.seed_wiki[:3]],
                  "intent": intent_result.intent.value})   # NEW — add intent to trace

    _t = time.perf_counter()
    bundle.seed_jira = jira_retriever.search(search_query, functional_area=functional_area)  # was: question
    # ... rest of the function unchanged, except the auto-fetch at the bottom uses latest_limit_eff:
```

At the bottom of `run_preflight()`, the line `keys_to_fetch = bundle.latest_keys()[:latest_limit]` must become:

```python
    keys_to_fetch = bundle.latest_keys()[:latest_limit_eff]   # was: [:latest_limit]
```

- [ ] **Step 5: Update `build_seed_message()` to include intent header**

In `build_seed_message()` (currently starts at line 342), find the return statement. The current opening is:

```python
    return (
        f"{op_block}"
        f"**Question:** {question}\n"
        f"**Scope:** {scope_line}\n\n"
        ...
    )
```

Change it to:

```python
    # Build optional intent header line (omit for GENERAL intent)
    intent_line = ""
    if bundle.intent_result and bundle.intent_result.intent.value != "GENERAL":
        ir = bundle.intent_result
        intent_line = (
            f"**Intent:** {ir.intent.value} (conf: {ir.confidence:.2f})"
            + (f" | rewritten: \"{ir.rewritten_query}\"" if ir.rewritten_query != question else "")
            + "\n"
        )

    return (
        f"{op_block}"
        f"**Question:** {question}\n"
        f"**Scope:** {scope_line}\n"
        f"{intent_line}\n"
        f"{summary_block}"
        ...   # rest unchanged
    )
```

- [ ] **Step 6: Update `build_agent_preamble()` with the same header**

In `build_agent_preamble()` (currently starts at line 399), add the same intent header after the preamble intro block:

```python
def build_agent_preamble(bundle: PreflightBundle) -> str:
    """Block prepended to the user's question for Claude Code agent mode."""
    # Intent header (omit for GENERAL)
    intent_line = ""
    if bundle.intent_result and bundle.intent_result.intent.value != "GENERAL":
        ir = bundle.intent_result
        intent_line = f"**Intent:** {ir.intent.value} (conf: {ir.confidence:.2f})\n\n"

    wiki_text = format_wiki_for_seed(bundle.seed_wiki)
    jira_text = format_jira_buckets_for_seed(bundle.seed_jira)
    tickets_text = format_preflight_tickets(bundle.preflight_tickets)
    module_tagged_text  = format_module_tagged_for_seed(bundle.module_tagged_jira)
    related_module_text = format_related_module_for_seed(bundle.related_module_jira)
    module_tagged_block  = (module_tagged_text  + "\n") if module_tagged_text  else ""
    related_module_block = (related_module_text + "\n") if related_module_text else ""
    return (
        "## Pre-fetched evidence from Conwo backend\n\n"
        f"{intent_line}"
        "The Conwo backend has already searched the wiki and Jira mirror and "
        ...   # rest unchanged
    )
```

- [ ] **Step 7: Smoke-test the preflight wiring**

```bash
cd /Users/rudrakhare/Desktop/my-wiki/org-wiki
venv/bin/python -c "
from backend.preflight import run_preflight
from unittest.mock import patch

# Patch the retrievers so we don't need a live DB
with patch('backend.preflight.wiki_retriever.search', return_value=[]), \
     patch('backend.preflight.jira_retriever.search', return_value={'buckets': {}, 'keywords': []}), \
     patch('backend.preflight.build_registry'), \
     patch('backend.preflight.trace_store.record_event'):
    bundle = run_preflight('how to configure visitor OTP', trace_id=None)
    print('intent:', bundle.intent_result.intent.value)
    print('rewritten:', bundle.intent_result.rewritten_query)
    print('wiki_top_n hint:', bundle.intent_result.retrieval_hints['wiki_top_n'])
    assert bundle.intent_result.intent.value == 'CONFIGURATION'
    print('OK')
"
```

Expected:
```
intent: CONFIGURATION
rewritten: how to configure visitor OTP
wiki_top_n hint: 4
OK
```

- [ ] **Step 8: Run the full test suite to check no regressions**

```bash
venv/bin/pytest tests/ --ignore=tests/test_local_claude_code.py -x -q 2>&1 | tail -5
```

Expected: all pass (or the same number that was passing before this task).

- [ ] **Step 9: Commit**

```bash
git add backend/preflight.py
git commit -m "feat: wire intent classifier into run_preflight — applies wiki_top_n + jira_latest_limit hints, adds intent header to seed message"
```

---

### Task 4: Update `backend/orchestrator.py`

**Files:**
- Modify: `backend/orchestrator.py:110-120` (OrchestratorResult)
- Modify: `backend/orchestrator.py:220-280` (run_deep return sites)

**Context:** `OrchestratorResult` is a dataclass at line 110. `run_deep()` has **two** `return OrchestratorResult(...)` calls — one for the error path (line 221) and one for the success path (line 266). Both need the new fields.

- [ ] **Step 1: Add three fields to `OrchestratorResult`**

Find the dataclass (line 109):

```python
@dataclass
class OrchestratorResult:
    answer_id: str
    answer_text: str
    confidence: str          # "High" | "Medium" | "Low"
    sources: SourceInfo
    retrieval: dict          # raw retrieval metadata for debugging
    mode: str = "api"        # which provider was used
    error: str = ""
    tool_trace: list[dict] = field(default_factory=list)
    missing_context: list[str] = field(default_factory=list)
    deep_search_used: bool = False
    intent: str = "GENERAL"           # NEW
    rewritten_query: str = ""         # NEW
    intent_confidence: float = 0.0    # NEW
```

- [ ] **Step 2: Populate intent fields in `run_deep()` — capture from bundle after preflight**

In `run_deep()`, the line `bundle = run_preflight(...)` is at line 182. Add three lines right after it:

```python
    bundle = run_preflight(question, functional_area=functional_area, registry=registry,
                           trace_id=trace_id)

    # Capture intent for both return paths (error + success)
    _intent           = bundle.intent_result.intent.value if bundle.intent_result else "GENERAL"
    _rewritten_query  = bundle.intent_result.rewritten_query if bundle.intent_result else question
    _intent_conf      = bundle.intent_result.confidence if bundle.intent_result else 0.0
```

- [ ] **Step 3: Pass intent fields to the error-path `OrchestratorResult` (line 221)**

```python
    if not deep_result.ok:
        return OrchestratorResult(
            answer_id="",
            answer_text="",
            confidence="Low",
            sources=SourceInfo(),
            retrieval={},
            mode=mode,
            error=deep_result.error,
            tool_trace=deep_result.tool_trace,
            missing_context=deep_result.missing_context,
            deep_search_used=True,
            intent=_intent,                     # NEW
            rewritten_query=_rewritten_query,   # NEW
            intent_confidence=_intent_conf,     # NEW
        )
```

- [ ] **Step 4: Pass intent fields to the success-path `OrchestratorResult` (line 266)**

```python
    return OrchestratorResult(
        answer_id=answer_id,
        answer_text=raw_answer,
        confidence=confidence,
        sources=sources,
        retrieval={
            "rounds_used": deep_result.rounds_used,
            "tool_calls": len(deep_result.tool_trace),
            "preflight": pf_stats,
        },
        mode=mode,
        tool_trace=deep_result.tool_trace,
        missing_context=deep_result.missing_context,
        deep_search_used=True,
        intent=_intent,                     # NEW
        rewritten_query=_rewritten_query,   # NEW
        intent_confidence=_intent_conf,     # NEW
    )
```

- [ ] **Step 5: Verify with a quick import check**

```bash
cd /Users/rudrakhare/Desktop/my-wiki/org-wiki
venv/bin/python -c "
from backend.orchestrator import OrchestratorResult, SourceInfo
r = OrchestratorResult(answer_id='x', answer_text='', confidence='Low', sources=SourceInfo(), retrieval={})
print('intent default:', r.intent)
print('rewritten_query default:', r.rewritten_query)
print('intent_confidence default:', r.intent_confidence)
assert r.intent == 'GENERAL'
assert r.rewritten_query == ''
assert r.intent_confidence == 0.0
print('OK')
"
```

- [ ] **Step 6: Run tests**

```bash
venv/bin/pytest tests/ --ignore=tests/test_local_claude_code.py -x -q 2>&1 | tail -5
```

- [ ] **Step 7: Commit**

```bash
git add backend/orchestrator.py
git commit -m "feat: add intent/rewritten_query/intent_confidence to OrchestratorResult"
```

---

### Task 5: Update `backend/api.py` — `QueryResponse` model and `/query` handler

**Files:**
- Modify: `backend/api.py:215-226` (QueryResponse model)
- Modify: `backend/api.py:467-483` (QueryResponse instantiation in /query handler)

- [ ] **Step 1: Add three fields to `QueryResponse` Pydantic model**

Find `QueryResponse` (around line 215):

```python
class QueryResponse(BaseModel):
    answer_id: str
    answer_text: str
    confidence: str
    sources: dict
    retrieval: dict
    mode: str = "api"
    error: str = ""
    tool_trace: list[dict] = []
    missing_context: list[str] = []
    deep_search_used: bool = False
    conversation_id: str | None = None
    intent: str = "GENERAL"           # NEW
    rewritten_query: str = ""         # NEW
    intent_confidence: float = 0.0    # NEW
```

- [ ] **Step 2: Populate the new fields in the `/query` handler**

Find `return QueryResponse(` in the `/query` endpoint (around line 467). Add three keyword arguments:

```python
        return QueryResponse(
            answer_id=result.answer_id,
            answer_text=result.answer_text,
            confidence=result.confidence,
            sources={
                "wiki_pages": result.sources.wiki_pages,
                "jira_keys": result.sources.jira_keys,
                "pms_configs": result.sources.pms_configs,
            },
            retrieval=result.retrieval,
            mode=result.mode,
            error=result.error,
            tool_trace=result.tool_trace,
            missing_context=result.missing_context,
            deep_search_used=result.deep_search_used,
            conversation_id=conversation_id,
            intent=result.intent,                     # NEW
            rewritten_query=result.rewritten_query,   # NEW
            intent_confidence=result.intent_confidence,  # NEW
        )
```

- [ ] **Step 3: Verify the model serialises correctly**

```bash
cd /Users/rudrakhare/Desktop/my-wiki/org-wiki
venv/bin/python -c "
from backend.api import QueryResponse
r = QueryResponse(answer_id='x', answer_text='hi', confidence='High', sources={}, retrieval={})
d = r.model_dump()
print('intent:', d['intent'])
print('rewritten_query:', d['rewritten_query'])
print('intent_confidence:', d['intent_confidence'])
assert d['intent'] == 'GENERAL'
print('OK')
"
```

- [ ] **Step 4: Run tests**

```bash
venv/bin/pytest tests/ --ignore=tests/test_local_claude_code.py -x -q 2>&1 | tail -5
```

- [ ] **Step 5: Commit**

```bash
git add backend/api.py
git commit -m "feat: expose intent/rewritten_query/intent_confidence in QueryResponse API"
```

---

### Task 6: Update Angular TypeScript interfaces

**Files:**
- Modify: `frontend/src/app/core/api.service.ts`

- [ ] **Step 1: Add fields to `QueryResponse` interface**

In `api.service.ts`, find the `QueryResponse` interface (around line 33):

```typescript
export interface QueryResponse {
  answer_id: string;
  answer_text: string;
  confidence: 'High' | 'Medium' | 'Low';
  sources: SourceInfo;
  retrieval: Record<string, unknown>;
  mode: QueryMode;
  error: string;
  tool_trace: ToolTraceEntry[];
  missing_context: string[];
  deep_search_used: boolean;
  conversation_id?: string;
  intent?: string;              // NEW
  rewritten_query?: string;     // NEW
  intent_confidence?: number;   // NEW
}
```

- [ ] **Step 2: Add fields to `ChatMessage` interface**

Find the `ChatMessage` interface (around line 57):

```typescript
export interface ChatMessage {
  id: string;
  conversation_id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  created_at: string;
  mode?: string | null;
  server?: string | null;
  buid?: string | null;
  answer_id?: string | null;
  confidence?: string | null;
  sources?: SourceInfo | null;
  tool_trace?: ToolTraceEntry[] | null;
  missing_context?: string[] | null;
  intent?: string | null;              // NEW
  rewritten_query?: string | null;     // NEW
  intent_confidence?: number | null;   // NEW
}
```

- [ ] **Step 3: Verify TypeScript compiles**

```bash
cd /Users/rudrakhare/Desktop/my-wiki/org-wiki/frontend
npx tsc --noEmit 2>&1 | head -20
```

Expected: no errors (or only pre-existing errors unrelated to this change).

- [ ] **Step 4: Commit**

```bash
cd /Users/rudrakhare/Desktop/my-wiki/org-wiki
git add frontend/src/app/core/api.service.ts
git commit -m "feat: add intent fields to Angular QueryResponse and ChatMessage interfaces"
```

---

### Task 7: Intent badge in Angular chat UI

**Files:**
- Modify: `frontend/src/app/features/ask/ask.ts`
- Modify: `frontend/src/app/features/ask/ask.scss`

- [ ] **Step 1: Add helper methods to the `AskComponent` class in `ask.ts`**

Open `frontend/src/app/features/ask/ask.ts`. Find the `// ── Template helpers ─────────────────────────────────────────────────` comment (around line 695). Add two methods after `modeLabel()` or any existing helper:

```typescript
  intentEmoji(intent: string): string {
    const map: Record<string, string> = {
      DEBUGGING:     '🐛',
      CONFIGURATION: '⚙️',
      HOW_TO:        '📖',
      DEFINITION:    '📝',
      COMPARISON:    '⚖️',
      ARCHITECTURAL: '🏗️',
      STATUS:        '📊',
    };
    return map[intent] ?? '💬';
  }

  formatIntent(intent: string): string {
    return intent.replace(/_/g, ' ').toLowerCase().replace(/\b\w/g, c => c.toUpperCase());
  }
```

- [ ] **Step 2: Update `appendAssistantFromResponse()` to copy intent fields**

Find `private appendAssistantFromResponse(res: QueryResponse)` (around line 678). Add the three new fields to the `ChatMessage` literal:

```typescript
  private appendAssistantFromResponse(res: QueryResponse) {
    const msg: ChatMessage = {
      id: `local-${Date.now()}`,
      conversation_id: res.conversation_id ?? '',
      role: 'assistant',
      content: res.answer_text,
      created_at: new Date().toISOString(),
      mode: res.mode,
      confidence: res.confidence,
      answer_id: res.answer_id,
      sources: res.sources,
      tool_trace: res.tool_trace,
      missing_context: res.missing_context,
      intent: res.intent,                     // NEW
      rewritten_query: res.rewritten_query,   // NEW
      intent_confidence: res.intent_confidence,  // NEW
    };
    this.messages.update(arr => [...arr, msg]);
  }
```

- [ ] **Step 3: Add intent badge to the template**

In `ask.ts`, find the `<div class="answer-header">` block (around line 92). It currently looks like:

```html
                    <div class="answer-header">
                      @if (m.confidence) {
                        <app-confidence-badge [confidence]="m.confidence" />
                      }
                      @if (m.mode === 'api' || m.mode === 'agent') {
```

Add the intent badge right after the `<app-confidence-badge>` block:

```html
                    <div class="answer-header">
                      @if (m.confidence) {
                        <app-confidence-badge [confidence]="m.confidence" />
                      }
                      @if (m.intent && m.intent !== 'GENERAL') {
                        <span class="pill pill-intent" [attr.data-intent]="m.intent!.toLowerCase()">
                          {{ intentEmoji(m.intent!) }} {{ formatIntent(m.intent!) }}
                        </span>
                      }
                      @if (m.mode === 'api' || m.mode === 'agent') {
```

- [ ] **Step 4: Add `.pill-intent` styles to `ask.scss`**

Open `frontend/src/app/features/ask/ask.scss`. Find the existing `.pill` or `.pill-deep` rule and add after it:

```scss
.pill-intent {
  font-size: 0.72rem;
  padding: 0.15rem 0.55rem;
  border-radius: 999px;
  background: #e8f0fe;
  color: #1a56db;
  font-weight: 500;
  white-space: nowrap;
  cursor: default;

  &[data-intent="debugging"]     { background: #fde8e8; color: #c81e1e; }
  &[data-intent="configuration"] { background: #e8f0fe; color: #1a56db; }
  &[data-intent="how_to"]        { background: #e8f4e8; color: #057a55; }
  &[data-intent="definition"]    { background: #fef3c7; color: #92400e; }
  &[data-intent="comparison"]    { background: #f0e8fe; color: #6c2bd9; }
  &[data-intent="architectural"] { background: #e8f4fe; color: #0369a1; }
  &[data-intent="status"]        { background: #e8fef4; color: #065f46; }
}
```

- [ ] **Step 5: Verify TypeScript still compiles**

```bash
cd /Users/rudrakhare/Desktop/my-wiki/org-wiki/frontend
npx tsc --noEmit 2>&1 | head -20
```

Expected: no errors.

- [ ] **Step 6: Build the frontend**

```bash
cd /Users/rudrakhare/Desktop/my-wiki/org-wiki/frontend
npm run build 2>&1 | tail -10
```

Expected: `Application bundle generation complete.`

- [ ] **Step 7: Verify the badge appears end-to-end**

With both servers running (`venv/bin/uvicorn backend.api:app --reload --port 8000` and `npm start`), open `http://localhost:4200`, sign in, and send a test query with a clear intent:

- `"OTP not working for visitors"` → expect 🐛 Debugging badge
- `"how to configure visitor OTP"` → expect ⚙️ Configuration badge
- `"what is SSO"` → expect 📝 Definition badge
- `"difference between .in and .com"` → expect ⚖️ Comparison badge
- `"tell me about WorkInSync"` → expect **no badge** (GENERAL)

- [ ] **Step 8: Run the full test suite one final time**

```bash
cd /Users/rudrakhare/Desktop/my-wiki/org-wiki
venv/bin/pytest tests/ --ignore=tests/test_local_claude_code.py -q 2>&1 | tail -5
```

Expected: all pass.

- [ ] **Step 9: Commit**

```bash
cd /Users/rudrakhare/Desktop/my-wiki/org-wiki
git add frontend/src/app/features/ask/ask.ts frontend/src/app/features/ask/ask.scss
git commit -m "feat: show intent badge in chat UI — 7 intent types with color-coded pills"
```

---

## Self-Review

### Spec coverage check

| Spec requirement | Task |
|-----------------|------|
| `QueryIntent` enum (7 intents + GENERAL) | Task 2 |
| `IntentResult` dataclass (intent, rewritten_query, confidence, retrieval_hints) | Task 2 |
| `classify_intent()` — pure regex, no I/O | Task 2 |
| 15+ tests in `tests/test_intent_classifier.py` | Task 1 (22 tests) |
| Wire into `run_preflight()` — apply hints | Task 3 |
| Use `rewritten_query` for wiki + Jira search | Task 3 (Step 4) |
| Add intent header to `build_seed_message()` | Task 3 (Step 5) |
| Add intent header to `build_agent_preamble()` | Task 3 (Step 6) |
| `OrchestratorResult` — new `intent`/`rewritten_query`/`intent_confidence` | Task 4 |
| `QueryResponse` Pydantic model — new fields | Task 5 |
| `QueryResponse` TS interface — new fields | Task 6 |
| `ChatMessage` TS interface — new fields | Task 6 |
| `appendAssistantFromResponse()` copies intent fields | Task 7 (Step 2) |
| Intent badge in chat template | Task 7 (Step 3) |
| `.pill-intent` CSS with per-intent colors | Task 7 (Step 4) |

### Type consistency check

- `QueryIntent` enum values (`"CONFIGURATION"` etc.) used as strings via `.value` throughout — consistent.
- `IntentResult.retrieval_hints` keys (`wiki_top_n`, `jira_latest_limit`, `boost_config_pages`) referenced by name in `run_preflight()` — consistent.
- `OrchestratorResult.intent: str` (not `QueryIntent`) — matches what `api.py` `QueryResponse.intent: str` expects.
- Angular `m.intent!` (non-null assertion) used after `@if (m.intent && m.intent !== 'GENERAL')` guard — safe.

### No placeholders

All steps contain actual code. No "TBD", "TODO", or "similar to Task N" patterns.
