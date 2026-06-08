# Query Intent Classification — Design Spec

**Date:** 2026-06-08
**Status:** Approved
**Feature:** Lightweight intent classification layer for the Conwo RAG pipeline

---

## Goal

Add a zero-cost (no extra LLM call) intent classification layer that runs before retrieval on every query. It detects the user's intent, rewrites vague questions, adjusts retrieval strategy per intent, exposes the classified intent in the API response, and shows an intent badge in the Angular chat UI.

---

## Architecture Overview

```
User question
    │
    ▼
run_preflight(question, ...)
    │
    ├─► classify_intent(question)  ← NEW — pure regex/keyword, no I/O
    │       └─ IntentResult { intent, rewritten_query, confidence, retrieval_hints }
    │
    ├─► wiki_retriever.search(rewritten_query, top_n=hints["wiki_top_n"])
    ├─► jira_retriever.search(rewritten_query, ...)
    └─► auto-fetch LATEST tickets (limit=hints["jira_latest_limit"])
    │
    ▼
PreflightBundle { ..., intent_result: IntentResult }
    │
    ├─► build_seed_message()  — includes "**Intent:** DEBUGGING (0.91)" header
    ├─► build_agent_preamble() — same header
    │
    ▼
OrchestratorResult { ..., intent, rewritten_query, intent_confidence }
    │
    ▼
QueryResponse (API) { ..., intent, rewritten_query, intent_confidence }
    │
    ▼
Angular ChatMessage { ..., intent, rewritten_query, intent_confidence }
    └─► Intent badge: ⚙️ Configuration  🐛 Debugging  📝 Definition …
```

Constraint: `classify_intent()` has zero external dependencies — no subprocess, no SQLite, no HTTP. It is pure Python and runs in microseconds.

---

## Section 1 — Intent Classifier (`backend/intent_classifier.py`)

### 1.1 `QueryIntent` enum

```python
class QueryIntent(str, Enum):
    DEFINITION    = "DEFINITION"
    CONFIGURATION = "CONFIGURATION"
    DEBUGGING     = "DEBUGGING"
    HOW_TO        = "HOW_TO"
    COMPARISON    = "COMPARISON"
    ARCHITECTURAL = "ARCHITECTURAL"
    STATUS        = "STATUS"
    GENERAL       = "GENERAL"
```

### 1.2 `IntentResult` dataclass

```python
@dataclass
class IntentResult:
    intent: QueryIntent
    rewritten_query: str      # original or context-expanded for vague queries
    confidence: float         # 0.0–1.0
    retrieval_hints: dict     # steers run_preflight() parameters
```

### 1.3 `retrieval_hints` keys

| Key | Type | Default | Effect in `run_preflight()` |
|-----|------|---------|------------------------------|
| `wiki_top_n` | `int` | 3 | Override `_PREFLIGHT_WIKI_TOP_N` |
| `jira_latest_limit` | `int` | 2 | Override `_PREFLIGHT_LATEST_LIMIT` |
| `boost_config_pages` | `bool` | `False` | Force-include `wiki/configs/` pages for any service detected in the query |

### 1.4 Intent → hints mapping

| Intent | `wiki_top_n` | `jira_latest_limit` | `boost_config_pages` |
|--------|-------------|---------------------|----------------------|
| DEFINITION | 4 | 2 | False |
| CONFIGURATION | 4 | 2 | True |
| DEBUGGING | 3 | 4 | False |
| HOW_TO | 4 | 2 | False |
| COMPARISON | 5 | 2 | False |
| ARCHITECTURAL | 4 | 2 | False |
| STATUS | 3 | 4 | False |
| GENERAL | 3 | 2 | False |

### 1.5 Classification logic

Patterns are evaluated in priority order (first match wins). Each pattern contributes a signal score. If total score ≥ 2.0, confidence is High (≥ 0.85); score 1.0 → Medium (0.65); below → GENERAL fallback.

**Priority order (most specific first):**

1. **CONFIGURATION** — highest priority because camelCase config tokens are unambiguous
   - Any camelCase token with ≥ 2 humps (e.g. `kioskRequireOTPBeforeRegister`)
   - Keywords: `config`, `property`, `setting`, `pms`, `configure`, `configured`, `configuration`, `enable.*property`, `disable.*property`
   - Patterns: `"what (is|does|do) .*(config|property|setting)"`, `"how to (configure|set|enable|disable)"`

2. **DEBUGGING** — "something is broken" signals
   - Keywords: `not working`, `broken`, `bug`, `error`, `failing`, `issue`, `problem`, `doesn't work`, `not showing`, `incorrect`, `wrong value`, `missing`
   - Patterns: `"why (is|does|did|are|isn't|aren't|doesn't|don't) .*(not|broken|fail)"`, `"(not|never) (work|show|load|trigger)"`

3. **DEFINITION** — "what is X"
   - Patterns: `"^what (is|are|does|do)\b"`, `"^define\b"`, `"^explain\b"`, `"meaning of"`, `"what does .* mean"`
   - Excludes: questions containing `"how"` (those are HOW_TO or ARCHITECTURAL)

4. **HOW_TO** — step-by-step / procedural
   - Patterns: `"^how (do|can|should|to)\b"`, `"steps? to"`, `"how (do|can) (i|we|you)\b"`, `"(enable|disable|set up|turn on|turn off|activate|deactivate)`
   - Note: `"how does .* work"` → ARCHITECTURAL (checked first in ARCHITECTURAL pass)

5. **COMPARISON** — A vs B
   - Patterns: `"\bvs\.?\b"`, `"\bversus\b"`, `"difference between"`, `"compare .* (to|with|and)"`, `"(better|worse|same as)"`, `"A or B"` (two distinct entities joined by `or`)

6. **ARCHITECTURAL** — system design / flow
   - Patterns: `"(architecture|design|flow|diagram|dependency|dependencies)"`, `"how does .* work"`, `"how (is|are) .* (built|structured|connected|integrated)"`, `"(data flow|event flow|request flow)"`, `"(module|service|component) (diagram|design|overview)"`

7. **STATUS** — current state / ticket progress
   - Patterns: `"status (of|for|on)"`, `"latest (update|news|status)"`, `"(is|are) .* (working|live|deployed|fixed|resolved)"`, `"what happened (with|to)"`, `"\b[A-Z]{2,5}-\d{3,6}\b"` (Jira key in question)

8. **GENERAL** — fallback

### 1.6 Query rewriting

Rewriting applies only when the question is short (< 6 tokens) or contains pronouns without clear referents ("it", "this", "that"). In those cases, the classifier appends the detected domain from keywords found. Otherwise, `rewritten_query = question` (no change).

Examples:
- `"how does it work"` → `"how does WorkInSync booking work"` (if `booking` was the prior context keyword detected) — but since the classifier is stateless, this is limited to expanding from keywords within the same question.
- `"configure OTP"` → `"how to configure OTP in WorkInSync"` (expanded with product context)
- `"what is SSO"` → unchanged (already specific enough)

For v1, rewriting only applies when `len(question.split()) < 5` AND a clear domain keyword is found. Otherwise `rewritten_query = question`.

---

## Section 2 — Preflight wiring (`backend/preflight.py`)

### 2.1 `PreflightBundle` — new field

```python
@dataclass
class PreflightBundle:
    seed_wiki: list = field(default_factory=list)
    seed_jira: dict = field(default_factory=dict)
    preflight_tickets: list[dict] = field(default_factory=list)
    preflight_trace: list[ToolTraceEntry] = field(default_factory=list)
    module_tagged_jira: list[dict] = field(default_factory=list)
    related_module_jira: list[dict] = field(default_factory=list)
    intent_result: IntentResult | None = None    # NEW
```

### 2.2 `run_preflight()` — intent classification + hint application

At the top of `run_preflight()`, before any retrieval:

```python
from backend.intent_classifier import classify_intent, IntentResult

intent_result = classify_intent(question)
bundle.intent_result = intent_result

search_query = intent_result.rewritten_query   # may differ from question
hints = intent_result.retrieval_hints
wiki_top_n_eff = hints.get("wiki_top_n", _PREFLIGHT_WIKI_TOP_N)
latest_limit_eff = hints.get("jira_latest_limit", latest_limit)
```

All subsequent retrieval calls use `search_query` and the effective limit values.

The `boost_config_pages` hint adds an extra forced config-page include step after `wiki_retriever.search()`, parallel to the existing `_mentioned_services` boost but triggered unconditionally for CONFIGURATION intent.

### 2.3 `build_seed_message()` — intent header

After `**Question:**` and `**Scope:**`, add:

```
**Intent:** CONFIGURATION (conf: 0.91) | query: "how to configure visitor OTP"
```

If `bundle.intent_result is None` or `intent == GENERAL`, this line is omitted.

### 2.4 `build_agent_preamble()` — same header

Same one-line addition at the top of the preamble block.

---

## Section 3 — Orchestrator (`backend/orchestrator.py`)

### 3.1 `OrchestratorResult` — new fields

```python
@dataclass
class OrchestratorResult:
    answer_id: str
    answer_text: str
    confidence: str
    sources: SourceInfo
    retrieval: dict
    mode: str = "api"
    error: str = ""
    tool_trace: list[dict] = field(default_factory=list)
    missing_context: list[str] = field(default_factory=list)
    deep_search_used: bool = False
    intent: str = "GENERAL"           # NEW
    rewritten_query: str = ""         # NEW
    intent_confidence: float = 0.0    # NEW
```

### 3.2 `run_deep()` — populate intent fields

After `bundle = run_preflight(...)`:

```python
if bundle.intent_result:
    ir = bundle.intent_result
    # Store on result (populated after provider returns)
    _intent = ir.intent.value
    _rewritten_query = ir.rewritten_query
    _intent_confidence = ir.confidence
```

After `deep_result` returns and `result` is constructed, set:

```python
result.intent = _intent
result.rewritten_query = _rewritten_query
result.intent_confidence = _intent_confidence
```

---

## Section 4 — API response (`backend/api.py`)

### 4.1 `QueryResponse` Pydantic model — new fields

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

### 4.2 `/query` handler — populate new fields

```python
return QueryResponse(
    ...existing fields...,
    intent=result.intent,
    rewritten_query=result.rewritten_query,
    intent_confidence=result.intent_confidence,
)
```

---

## Section 5 — Frontend

### 5.1 `frontend/src/app/core/api.service.ts`

Add to `QueryResponse` interface:
```typescript
export interface QueryResponse {
  ...existing...
  intent?: string;
  rewritten_query?: string;
  intent_confidence?: number;
}
```

Add to `ChatMessage` interface:
```typescript
export interface ChatMessage {
  ...existing...
  intent?: string | null;
  rewritten_query?: string | null;
  intent_confidence?: number | null;
}
```

### 5.2 `frontend/src/app/features/ask/ask.ts`

In the `answer-header` div, after `<app-confidence-badge>`:

```html
@if (m.intent && m.intent !== 'GENERAL') {
  <span class="pill pill-intent" [attr.data-intent]="m.intent?.toLowerCase()">
    {{ intentEmoji(m.intent) }} {{ formatIntent(m.intent) }}
  </span>
}
```

Add `intentEmoji()` and `formatIntent()` methods to the component class:

```typescript
intentEmoji(intent: string): string {
  const map: Record<string, string> = {
    DEBUGGING: '🐛', CONFIGURATION: '⚙️', HOW_TO: '📖',
    DEFINITION: '📝', COMPARISON: '⚖️', ARCHITECTURAL: '🏗️',
    STATUS: '📊',
  };
  return map[intent] ?? '💬';
}

formatIntent(intent: string): string {
  return intent.replace('_', ' ').toLowerCase()
    .replace(/\b\w/g, c => c.toUpperCase());
}
```

In `appendAssistantFromResponse()` (ask.ts:678), add the new fields to the `ChatMessage` literal:

```typescript
intent: res.intent,
rewritten_query: res.rewritten_query,
intent_confidence: res.intent_confidence,
```

### 5.3 `frontend/src/app/features/ask/ask.scss`

```scss
.pill-intent {
  font-size: 0.72rem;
  padding: 0.15rem 0.55rem;
  border-radius: 999px;
  background: #e8f0fe;
  color: #1a56db;
  font-weight: 500;
  white-space: nowrap;

  &[data-intent="debugging"]     { background: #fde8e8; color: #c81e1e; }
  &[data-intent="configuration"] { background: #e8f0fe; color: #1a56db; }
  &[data-intent="how_to"]        { background: #e8f4e8; color: #057a55; }
  &[data-intent="definition"]    { background: #fef3c7; color: #92400e; }
  &[data-intent="comparison"]    { background: #f0e8fe; color: #6c2bd9; }
  &[data-intent="architectural"] { background: #e8f4fe; color: #0369a1; }
  &[data-intent="status"]        { background: #e8fef4; color: #065f46; }
}
```

**Scope note:** The badge only appears on `mode === 'api'` messages (stream/agent mode messages don't return structured metadata). The classifier still runs for agent mode — the intent is prepended to `build_agent_preamble()` as context for the Claude Code agent, it just isn't surfaced as a visual badge.

---

## Section 6 — Tests (`tests/test_intent_classifier.py`)

18 test cases:

| # | Input | Expected intent | Extra assertion |
|---|-------|----------------|----------------|
| 1 | `"what is kioskRequireOTPBeforeRegister"` | CONFIGURATION | conf ≥ 0.85 |
| 2 | `"how to configure visitor OTP"` | CONFIGURATION | boost_config_pages = True |
| 3 | `"showEmployeeOfficePlan config"` | CONFIGURATION | conf ≥ 0.80 |
| 4 | `"OTP not working for visitors"` | DEBUGGING | jira_latest_limit ≥ 4 |
| 5 | `"visitor check-in broken after latest update"` | DEBUGGING | — |
| 6 | `"kioskMode error on floor kiosk"` | DEBUGGING | — |
| 7 | `"what is SSO"` | DEFINITION | rewritten_query == input |
| 8 | `"define meal management"` | DEFINITION | — |
| 9 | `"how do I enable desk booking"` | HOW_TO | — |
| 10 | `"steps to set up parking management"` | HOW_TO | — |
| 11 | `"difference between .in and .com server"` | COMPARISON | wiki_top_n ≥ 5 |
| 12 | `"visitor vs meeting rooms"` | COMPARISON | — |
| 13 | `"how does the SSO auth flow work"` | ARCHITECTURAL | — |
| 14 | `"architecture of the booking rule engine"` | ARCHITECTURAL | wiki_top_n ≥ 4 |
| 15 | `"status of visitor rollout"` | STATUS | jira_latest_limit ≥ 4 |
| 16 | `"latest update on PB-12345"` | STATUS | — |
| 17 | `"tell me about WorkInSync"` | GENERAL | conf < 0.65 |
| 18 | `"help"` | GENERAL | rewritten_query == "help" |

All tests import only `backend.intent_classifier` — no database, no HTTP, no subprocess.

---

## Constraints (from user spec)

- No additional LLM API call — classifier is pure Python regex/heuristics only
- Do NOT change the TF-IDF index structure in `wiki_retriever.py`
- Do NOT change the tool registry
- Do NOT modify `wiki/raw/` files
- Keep the existing preflight always-on guarantee intact (`run_preflight()` runs for every query; the classifier wraps it, not replaces it)

---

## Files Changed

| File | Action |
|------|--------|
| `backend/intent_classifier.py` | CREATE |
| `backend/preflight.py` | MODIFY — PreflightBundle + run_preflight + build_seed_message + build_agent_preamble |
| `backend/orchestrator.py` | MODIFY — OrchestratorResult + run_deep |
| `backend/api.py` | MODIFY — QueryResponse model + /query handler |
| `frontend/src/app/core/api.service.ts` | MODIFY — QueryResponse + ChatMessage interfaces |
| `frontend/src/app/features/ask/ask.ts` | MODIFY — intent badge + helper methods |
| `frontend/src/app/features/ask/ask.scss` | MODIFY — .pill-intent styles |
| `tests/test_intent_classifier.py` | CREATE — 18 test cases |
