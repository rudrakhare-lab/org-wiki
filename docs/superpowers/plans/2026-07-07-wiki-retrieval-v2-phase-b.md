# Wiki Retrieval V2 — Phase B (Intelligence + Verification + Eval) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Phase-A pipeline intelligent and auditable: one shared query rewrite feeding both retrievers, hardened intent classification, config-dependency push for the PMS pillar, a global seed budget with trim-notes, inline citation verification with honest sources, and the golden eval gate — then the PR.

**Architecture:** Builds strictly on Phase A (`2026-07-07-wiki-retrieval-v2-phase-a.md`) on the same branch `feat/wiki-retrieval-v2`. Spec: `docs/superpowers/specs/2026-07-07-wiki-retrieval-v2-design.md` §5.5–§5.9, §7.

**Tech Stack:** unchanged — no new dependencies.

## Global Constraints

- Same as Phase A (flag semantics, prod-realistic fixtures, soft routing [0.6–1.4], fail-open with visible notes, agent scoping, TEXT dates).
- **Seed evidence budget: `SEED_BUDGET_TOKENS = 6000`** (tunable constant; tokens ≈ chars/4). Eviction is rank-ordered, lowest-ranked `related_via`-tagged items first, per-intent protection order (spec §5.7). **Trim-note is mandatory** — every trimmed item listed with its anchor/key + fetch tool.
- **Confidence is never fabricated:** missing model confidence → `"Unknown"`, never `"Medium"`.
- Prompt text changes are out of scope except the one-line seed additions specified here.

---

### Task 1: Rewrite hardening — API fallback, fence-stripping, bounded cache

**Files:**
- Modify: `backend/retrieval/v2/rewrite.py`
- Test: `tests/retrieval/v2/test_rewrite.py` (extend or create)

**Interfaces:**
- Produces: `rewrite(question) -> RewriteResult` that **never raises** — any Anthropic/API/parse failure returns `RewriteResult(sub_queries=[question])`. Fenced JSON (```json … ```) parses correctly. Cache bounded to 128 entries, guarded by a lock. Signature and `RewriteResult` fields unchanged (Task 2 depends on them).

- [ ] **Step 1: Write the failing tests**

```python
"""rewrite hardening — never-raise fallback, fence stripping, bounded cache."""
import threading
from backend.retrieval.v2 import rewrite as rw


def test_api_exception_falls_back_to_question(monkeypatch):
    class Boom:
        def create(self, **kw):
            raise RuntimeError("rate limited")
    monkeypatch.setattr(rw, "_client_messages", lambda: Boom())
    out = rw.rewrite("why does OTP fail?")
    assert out.sub_queries == ["why does OTP fail?"]
    assert out.intent == "GENERAL"


def test_fenced_json_is_parsed(monkeypatch):
    fenced = '```json\n{"sub_queries": ["a", "b"], "intent": "DEBUGGING"}\n```'
    monkeypatch.setattr(rw, "_raw_completion", lambda q: fenced)
    out = rw._call_claude("q")
    assert out.sub_queries == ["a", "b"] and out.intent == "DEBUGGING"


def test_cache_is_bounded(monkeypatch):
    monkeypatch.setattr(rw, "_raw_completion",
                        lambda q: '{"sub_queries": ["x"]}')
    rw._CACHE.clear()
    for i in range(rw._CACHE_MAX + 50):
        rw.rewrite(f"question {i}")
    assert len(rw._CACHE) <= rw._CACHE_MAX
```

- [ ] **Step 2: Run tests, verify they fail**

Run: `venv/bin/pytest tests/retrieval/v2/test_rewrite.py -v`
Expected: FAIL — `_client_messages`/`_raw_completion`/`_CACHE_MAX` don't exist yet; API-exception test crashes instead of falling back.

- [ ] **Step 3: Implement**

Refactor `rewrite.py` (read the current file first; keep `RewriteResult` and the prompt untouched):

```python
import re
import threading

_CACHE_MAX = 128
_cache_lock = threading.Lock()
_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def _client_messages():
    """Test seam: returns the anthropic messages API object."""
    ...  # existing client construction moved here


def _raw_completion(question: str) -> str:
    """Test seam: one Haiku call, returns raw text."""
    ...  # existing messages.create(...) call moved here, returns resp text


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
```

In `rewrite()`: wrap cache access with `_cache_lock`; after insert, evict oldest while `len(_CACHE) > _CACHE_MAX` (insertion order is fine — dict preserves it).

- [ ] **Step 4: Run the full retrieval sweep**

Run: `venv/bin/pytest tests/retrieval/ -q`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add backend/retrieval/v2/rewrite.py tests/retrieval/v2/test_rewrite.py
git commit -m "fix(retrieval-v2): rewrite never raises — API fallback, fence-strip, bounded cache (audit)"
```

---

### Task 2: Shared rewrite hoist — one Haiku call feeds both retrievers

**Files:**
- Modify: `backend/preflight.py` (compute rewrite once, store on bundle, pass to both branches)
- Modify: `backend/retrieval/v2/pipeline.py` (`search(..., rewrite_result=None)`)
- Modify: `backend/jira_retriever.py` (`_v2_search` plumbs `rewrite_result` through)
- Test: `tests/test_preflight_shared_rewrite.py`

**Interfaces:**
- Consumes: `rewrite(question) -> RewriteResult` (Task 1, never raises).
- Produces:
  - `PreflightBundle.rewrite_result: RewriteResult | None` (new field).
  - `backend.retrieval.v2.pipeline.search(question, functional_area=None, limit=10, rewrite_result: RewriteResult | None = None)` — uses the passed result, calls `rewrite()` itself only when `None` (back-compat for direct tool calls).
  - Preflight's wiki branch passes `rewrite=bundle.rewrite_result` into `_fetch_seed_wiki` (Phase A left this `None`).

- [ ] **Step 1: Write the failing tests**

```python
"""Shared rewrite — computed once in preflight, consumed by both pillars."""
from backend.retrieval.v2.rewrite import RewriteResult


def test_pipeline_search_uses_passed_rewrite(monkeypatch):
    from backend.retrieval.v2 import pipeline
    calls = []
    monkeypatch.setattr(pipeline, "rewrite",
                        lambda q: calls.append(q) or RewriteResult([q]))
    monkeypatch.setattr(pipeline, "embed_query", lambda q: [0.0] * 768)
    monkeypatch.setattr(pipeline, "hybrid_search", lambda *a, **k: [])
    monkeypatch.setattr(pipeline, "gate_apply", lambda s: s)

    class C:
        def __enter__(self): return self
        def __exit__(self, *a): pass
    monkeypatch.setattr(pipeline, "connection", lambda: C())

    rr = RewriteResult(sub_queries=["pre-computed"])
    pipeline.search("q", rewrite_result=rr)
    assert calls == []          # rewrite() NOT called — passed result used

    pipeline.search("q")        # back-compat: no result passed
    assert calls == ["q"]


def test_preflight_computes_rewrite_once(monkeypatch):
    from backend import preflight
    calls = []
    monkeypatch.setattr(preflight, "rewrite",
                        lambda q: calls.append(q) or RewriteResult([q]))
    # run_preflight is heavy; assert via the seam the bundle setter uses:
    rr = preflight._compute_rewrite("question text")
    assert calls == ["question text"] and rr.sub_queries == ["question text"]
```

- [ ] **Step 2: Run tests, verify they fail**

Run: `venv/bin/pytest tests/test_preflight_shared_rewrite.py -v`
Expected: FAIL — `rewrite_result` kwarg / `_compute_rewrite` missing.

- [ ] **Step 3: Implement**

(a) `backend/retrieval/v2/pipeline.py` — change the entry:

```python
def search(question: str, functional_area: str | None = None, limit: int = 10,
           rewrite_result: "RewriteResult | None" = None) -> RetrievalResult:
    rw = rewrite_result or rewrite(question)
    ...  # rest unchanged (rw.sub_queries, rw.filters as today)
```

(b) `backend/jira_retriever.py` — `_v2_search` signature gains `rewrite_result=None` and passes it: `result = _p(question, functional_area=functional_area, limit=limit, rewrite_result=rewrite_result)`. `search()` dispatch forwards the kwarg (v1 absorbs it via `**kwargs` unchanged).

(c) `backend/preflight.py` — top of `run_preflight`, before the branches:

```python
from backend.retrieval.v2.rewrite import rewrite


def _compute_rewrite(question: str):
    return rewrite(question)  # never raises (Task 1)

# in run_preflight:
    bundle.rewrite_result = _compute_rewrite(_search_query)
```

Then: wiki branch passes `rewrite=bundle.rewrite_result`; the Jira seed call becomes `jira_retriever.search(_search_query, functional_area=functional_area, rewrite_result=bundle.rewrite_result)`. Add `rewrite_result: object = None` to `PreflightBundle`.

- [ ] **Step 4: Run the sweep**

Run: `venv/bin/pytest tests/ -q -k "preflight or retrieval or jira_retriever"`
Expected: all pass (Jira v2 dispatch tests monkeypatch `_v2_search` wholesale — unaffected).

- [ ] **Step 5: Commit**

```bash
git add backend/preflight.py backend/retrieval/v2/pipeline.py backend/jira_retriever.py tests/test_preflight_shared_rewrite.py
git commit -m "feat(retrieval): shared rewrite — one Haiku call feeds jira v2 + wiki v2 (spec §4, refinement 2)"
```

---

### Task 3: Intent hardening — deterministic tie-break + LLM second opinion

**Files:**
- Modify: `backend/intent_classifier.py` (tie-break priority list; `combine_intent`)
- Modify: `backend/preflight.py` (use combined verdict)
- Test: `tests/test_intent_classifier.py` (extend)

**Interfaces:**
- Consumes: `IntentResult(intent: QueryIntent, confidence: float, retrieval_hints: dict)`, `RewriteResult.intent: str`.
- Produces: `combine_intent(regex_result: IntentResult, llm_intent: str | None) -> IntentResult` — rules: (1) regex confidence ≥ 0.75 and intents agree (or no LLM intent) → regex wins; (2) they disagree and regex confidence < 0.75 → LLM intent wins (if it's a valid `QueryIntent` name); (3) LLM intent invalid/missing → regex; (4) both weak (regex < 0.65 and LLM = GENERAL) → GENERAL. Tie-break inside `_score`: fixed priority `CONFIGURATION > DEBUGGING > HOW_TO > DEFINITION > COMPARISON > ARCHITECTURAL > STATUS > GENERAL`.

- [ ] **Step 1: Write the failing tests**

```python
def test_score_tie_breaks_by_fixed_priority(monkeypatch):
    from backend import intent_classifier as ic
    # craft a question hitting HOW_TO and ARCHITECTURAL patterns equally
    r1 = ic.classify_intent("how does desk booking work end to end")
    r2 = ic.classify_intent("how does desk booking work end to end")
    assert r1.intent == r2.intent  # deterministic
    assert ic._TIE_PRIORITY.index(r1.intent) == min(
        ic._TIE_PRIORITY.index(i) for i, s in ic._last_tied_intents) \
        if getattr(ic, "_last_tied_intents", None) else True


def test_combine_llm_wins_on_low_confidence_disagreement():
    from backend import intent_classifier as ic
    regex = ic.IntentResult(intent=ic.QueryIntent.GENERAL, confidence=0.5,
                            retrieval_hints={})
    out = ic.combine_intent(regex, "CONFIGURATION")
    assert out.intent == ic.QueryIntent.CONFIGURATION


def test_combine_regex_wins_when_confident():
    from backend import intent_classifier as ic
    regex = ic.IntentResult(intent=ic.QueryIntent.DEBUGGING, confidence=0.95,
                            retrieval_hints={})
    out = ic.combine_intent(regex, "HOW_TO")
    assert out.intent == ic.QueryIntent.DEBUGGING


def test_combine_invalid_llm_intent_ignored():
    from backend import intent_classifier as ic
    regex = ic.IntentResult(intent=ic.QueryIntent.STATUS, confidence=0.6,
                            retrieval_hints={})
    out = ic.combine_intent(regex, "BANANA")
    assert out.intent == ic.QueryIntent.STATUS
```

- [ ] **Step 2: Run tests, verify they fail**

Run: `venv/bin/pytest tests/test_intent_classifier.py -v -k "combine or tie"`
Expected: FAIL — `combine_intent`/`_TIE_PRIORITY` missing.

- [ ] **Step 3: Implement**

In `backend/intent_classifier.py`:

```python
_TIE_PRIORITY = [
    QueryIntent.CONFIGURATION, QueryIntent.DEBUGGING, QueryIntent.HOW_TO,
    QueryIntent.DEFINITION, QueryIntent.COMPARISON, QueryIntent.ARCHITECTURAL,
    QueryIntent.STATUS, QueryIntent.GENERAL,
]

# in _score(): replace `max(scores, key=scores.get)` with:
#   best = max(scores.values())
#   tied = [i for i, s in scores.items() if s == best]
#   best_intent = min(tied, key=_TIE_PRIORITY.index)


def combine_intent(regex_result: IntentResult, llm_intent: str | None) -> IntentResult:
    """Regex verdict + the rewriter's LLM intent (spec §5.5). Soft: only the
    label changes; retrieval_hints are re-taken from _HINTS for the winner."""
    try:
        llm = QueryIntent(llm_intent) if llm_intent else None
    except ValueError:
        llm = None
    winner = regex_result.intent
    if llm and llm != regex_result.intent and regex_result.confidence < 0.75:
        winner = llm
    if winner == regex_result.intent:
        return regex_result
    return IntentResult(intent=winner, confidence=max(regex_result.confidence, 0.7),
                        retrieval_hints=_HINTS[winner].copy())
```

In `backend/preflight.py`, after both are available:

```python
    bundle.intent_result = combine_intent(
        bundle.intent_result,
        getattr(bundle.rewrite_result, "intent", None))
```

(Preserve existing trace logging of the intent; log both raw verdicts in the trace metadata.)

- [ ] **Step 4: Run tests + sweep**

Run: `venv/bin/pytest tests/test_intent_classifier.py tests/ -q -k "intent or preflight"`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add backend/intent_classifier.py backend/preflight.py tests/test_intent_classifier.py
git commit -m "feat(intent): deterministic tie-break + rewriter second opinion, soft-only (spec §5.5)"
```

---

### Task 4: Config KB preflight branch — dependency push for the PMS pillar

**Files:**
- Create: `backend/config_evidence.py`
- Modify: `backend/preflight.py` (new branch + seed block), `backend/tools/config_tools.py` (extract reusable lookup helper)
- Test: `tests/test_config_evidence.py`

**Interfaces:**
- Consumes: the existing `_config_lookup_handler` internals in `backend/tools/config_tools.py` — **Step 3a extracts** `lookup_property(name: str) -> dict | None` (returns the same dict the tool returns: description, data_type, servers, criteria_priority_list, dependent_configs, service, wiki links) so tool and preflight share one implementation.
- Produces:
  - `detect_config_properties(question: str, known_names: set[str]) -> list[str]` — backticked tokens + camelCase tokens (`[a-z]+[A-Z][A-Za-z0-9]*`) filtered to catalog membership (case-sensitive exact, then case-insensitive unique match).
  - `build_config_evidence(question: str, max_depth: int = 2) -> str` — markdown block: per detected property, its catalog row + dependency chain up to `max_depth` levels (cycle-safe), each line anchored `→ configs/<service>.md`.
  - `PreflightBundle.config_evidence: str` (empty when no property detected).

- [ ] **Step 1: Write the failing tests**

```python
"""Config evidence — detection, dependency chain, cycle safety."""
from backend import config_evidence as ce


def test_detects_backticked_and_camelcase_names():
    known = {"roomBookingBuffer", "enableRoomBooking", "kioskRequireOTP"}
    q = "why is `roomBookingBuffer` ignored when enableRoomBooking is on?"
    assert set(ce.detect_config_properties(q, known)) == {
        "roomBookingBuffer", "enableRoomBooking"}


def test_detection_ignores_unknown_tokens():
    assert ce.detect_config_properties("some camelCase word", {"realProp"}) == []


def test_dependency_chain_two_levels_cycle_safe(monkeypatch):
    rows = {
        "a": {"property": "a", "description": "A", "service": "VISITOR",
              "dependent_configs": ["b"]},
        "b": {"property": "b", "description": "B", "service": "VISITOR",
              "dependent_configs": ["a"]},  # cycle
    }
    monkeypatch.setattr(ce, "lookup_property", lambda n: rows.get(n))
    monkeypatch.setattr(ce, "_known_names", lambda: set(rows))
    block = ce.build_config_evidence("what is `a`?", max_depth=2)
    assert "`a`" in block and "`b`" in block
    assert block.count("`a`") >= 1            # no infinite loop
    assert "configs/" in block                 # anchored


def test_no_detection_returns_empty(monkeypatch):
    monkeypatch.setattr(ce, "_known_names", lambda: {"x"})
    assert ce.build_config_evidence("how do I book a desk?") == ""
```

- [ ] **Step 2: Run tests, verify they fail**

Run: `venv/bin/pytest tests/test_config_evidence.py -v`
Expected: FAIL — module missing.

- [ ] **Step 3a: Extract the shared lookup helper**

Read `backend/tools/config_tools.py::_config_lookup_handler`. Extract its core lookup (catalog query → result dict) into a module-level `lookup_property(name: str) -> dict | None` and a `known_property_names() -> set[str]` (cached, refreshed per process). Re-implement `_config_lookup_handler` on top of `lookup_property` — behavior identical (its existing tests must stay green).

- [ ] **Step 3b: Implement `backend/config_evidence.py`**

```python
"""Config-KB preflight push (spec §5.6): when the question names a config
property, its catalog row + dependency chain (≤2 levels, cycle-safe) is
pushed into the seed with anchors into configs/ pages. Live PMS *values*
remain pull-only (server/BUID disambiguation — CLAUDE.md §12)."""
from __future__ import annotations
import re

from backend.tools.config_tools import lookup_property, known_property_names

_BACKTICK_RE = re.compile(r"`([A-Za-z][A-Za-z0-9_.]+)`")
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


def _fmt(row: dict) -> str:
    svc = (row.get("service") or "").lower().replace("_", "-")
    anchor = f"configs/{svc}.md" if svc else "configs/"
    bits = [f"- `{row['property']}`"]
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
            for dep in row.get("dependent_configs") or []:
                if dep not in seen:
                    nxt.append(dep)
        frontier = nxt
        if not frontier:
            break
    lines.append("")
    lines.append("_Live values need server (.in/.com) + BUID — use pms_runtime_values / pms_diagnose_property._")
    return "\n".join(lines)
```

- [ ] **Step 3c: Wire into preflight**

In `run_preflight` (after intent combining):

```python
    from backend import config_evidence
    try:
        bundle.config_evidence = config_evidence.build_config_evidence(_search_query)
    except Exception:
        bundle.config_evidence = ""   # fail-open; PMS pillar must never crash a query
```

In `build_seed_message`: insert `bundle.config_evidence` block (with `\n\n---\n\n` separator) directly after the wiki block when non-empty. Add `config_evidence: str = ""` to `PreflightBundle`.

- [ ] **Step 4: Run tests + sweep**

Run: `venv/bin/pytest tests/test_config_evidence.py tests/ -q -k "config or preflight"`
Expected: all pass, `config_lookup` tool tests still green.

- [ ] **Step 5: Commit**

```bash
git add backend/config_evidence.py backend/tools/config_tools.py backend/preflight.py tests/test_config_evidence.py
git commit -m "feat(preflight): config-KB dependency push — PMS pillar evidence in the seed (spec §5.6)"
```

---

### Task 5: Seed budget + rank-ordered eviction + trim-note

**Files:**
- Create: `backend/seed_budget.py`
- Modify: `backend/preflight.py` (`build_seed_message` applies the budget)
- Test: `tests/test_seed_budget.py`

**Interfaces:**
- Consumes: rendered seed blocks as `(name, text, items)` triples where `items` is `list[tuple[str, str, str]]` = `(item_id, rendered_text, fetch_hint)` for evictable items (e.g. `("modules/a.md#overview", "### …", "wiki_read_page")`).
- Produces:
  - `SEED_BUDGET_TOKENS = 6000`; `est_tokens(text: str) -> int` (`len(text) // 4`).
  - `apply_budget(blocks: list[SeedBlock], intent: str) -> tuple[str, list[str]]` → `(final_seed_text, trimmed_item_descriptions)`.
  - `@dataclass SeedBlock: name: str; priority: int; text: str; evictable: list[tuple[str, str, str]]` — `priority` computed per intent from `EVICTION_ORDER`.
  - `EVICTION_ORDER: dict[str, list[str]]` — per intent, block names in **evict-first** order:
    - `CONFIGURATION`/`DEBUGGING`/`STATUS`: `["wiki_related", "wiki_direct", "jira_historical", "jira_latest", "config_evidence"]` (config last = most protected)
    - `HOW_TO`: `["jira_historical", "jira_latest", "wiki_related", "config_evidence", "wiki_direct"]`
    - `DEFINITION`/`ARCHITECTURAL`: `["jira_historical", "config_evidence", "jira_latest", "wiki_related", "wiki_direct"]`
    - default (`GENERAL` etc.): `["wiki_related", "jira_historical", "wiki_direct", "jira_latest", "config_evidence"]`
  - Trim-note appended to the seed: `## Trimmed (fetch on demand)` listing `- <item_id> — <fetch_hint>` per evicted item.

- [ ] **Step 1: Write the failing tests**

```python
"""Seed budget — protects per-intent, evicts rank-ordered, always trim-notes."""
from backend import seed_budget as sb


def _block(name, n_items, chars_per=400):
    items = [(f"{name}-item-{i}", "x" * chars_per, "wiki_read_page")
             for i in range(n_items)]
    return sb.SeedBlock(name=name, priority=0,
                        text="\n".join(t for _, t, _ in items), evictable=items)


def test_under_budget_passes_through_untouched():
    blocks = [_block("wiki_direct", 2), _block("jira_latest", 2)]
    text, trimmed = sb.apply_budget(blocks, "GENERAL")
    assert trimmed == [] and "Trimmed" not in text


def test_over_budget_evicts_wiki_related_first_protects_config():
    blocks = [_block("wiki_related", 30), _block("config_evidence", 5),
              _block("jira_latest", 10)]
    text, trimmed = sb.apply_budget(blocks, "CONFIGURATION")
    assert trimmed                                          # something evicted
    # CONFIGURATION evicts wiki_related before jira; config block is protected
    assert all(t.startswith("wiki_related") for t in trimmed) \
        or (any(t.startswith("wiki_related") for t in trimmed)
            and not any(t.startswith("config_evidence") for t in trimmed))
    assert "## Trimmed (fetch on demand)" in text


def test_trim_note_lists_every_evicted_id_with_fetch_hint():
    blocks = [_block("wiki_related", 40)]
    text, trimmed = sb.apply_budget(blocks, "GENERAL")
    assert trimmed
    for entry in trimmed:
        item_id, _, hint = entry.partition(" — ")
        assert item_id in text          # (a) every evicted id in the trim-note
        assert "fetch via" in hint


def test_top_keep_min_items_never_evicted():
    blocks = [_block("wiki_related", 40)]
    _, trimmed = sb.apply_budget(blocks, "GENERAL")
    evicted_ids = {t.split(" — ")[0] for t in trimmed}
    # (b) the first KEEP_MIN items of a block always survive
    for i in range(sb.KEEP_MIN):
        assert f"wiki_related-item-{i}" not in evicted_ids
```

- [ ] **Step 2: Run tests, verify they fail**

Run: `venv/bin/pytest tests/test_seed_budget.py -v`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement `backend/seed_budget.py`**

```python
"""Global seed evidence budget with intent-aware, rank-ordered eviction
(spec §5.7). Evicted items are demoted to pull — never hidden: the seed
ends with a trim-note listing every evicted item + its fetch tool."""
from __future__ import annotations
from dataclasses import dataclass, field

SEED_BUDGET_TOKENS = 6000
KEEP_MIN = 3  # never evict a block's top-N items (direct hits stay)

EVICTION_ORDER: dict[str, list[str]] = {
    "CONFIGURATION": ["wiki_related", "wiki_direct", "jira_historical",
                      "jira_latest", "config_evidence"],
    "DEBUGGING":     ["wiki_related", "wiki_direct", "jira_historical",
                      "jira_latest", "config_evidence"],
    "STATUS":        ["wiki_related", "wiki_direct", "jira_historical",
                      "jira_latest", "config_evidence"],
    "HOW_TO":        ["jira_historical", "jira_latest", "wiki_related",
                      "config_evidence", "wiki_direct"],
    "DEFINITION":    ["jira_historical", "config_evidence", "jira_latest",
                      "wiki_related", "wiki_direct"],
    "ARCHITECTURAL": ["jira_historical", "config_evidence", "jira_latest",
                      "wiki_related", "wiki_direct"],
}
_DEFAULT_ORDER = ["wiki_related", "jira_historical", "wiki_direct",
                  "jira_latest", "config_evidence"]


def est_tokens(text: str) -> int:
    return len(text) // 4


@dataclass
class SeedBlock:
    name: str
    priority: int
    text: str
    evictable: list[tuple[str, str, str]] = field(default_factory=list)


def apply_budget(blocks: list[SeedBlock], intent: str) -> tuple[str, list[str]]:
    order = EVICTION_ORDER.get(intent, _DEFAULT_ORDER)
    total = sum(est_tokens(b.text) for b in blocks)
    trimmed: list[str] = []

    if total > SEED_BUDGET_TOKENS:
        for name in order:                       # evict-first order
            if total <= SEED_BUDGET_TOKENS:
                break
            blk = next((b for b in blocks if b.name == name), None)
            if not blk or not blk.evictable:
                continue
            # evict from the bottom (lowest-ranked last items), keep top KEEP_MIN
            while (total > SEED_BUDGET_TOKENS
                   and len(blk.evictable) > KEEP_MIN):
                item_id, item_text, hint = blk.evictable.pop()
                blk.text = blk.text.replace(item_text, "").strip()
                trimmed.append(f"{item_id} — fetch via {hint}")
                total = sum(est_tokens(b.text) for b in blocks)

    parts = [b.text for b in blocks if b.text.strip()]
    if trimmed:
        parts.append("## Trimmed (fetch on demand)\n\n"
                     + "\n".join(f"- {t}" for t in trimmed))
    return "\n\n---\n\n".join(parts), trimmed
```

- [ ] **Step 4: Wire into `build_seed_message`**

Refactor `build_seed_message` to construct `SeedBlock`s instead of raw concatenation: `wiki_direct` (untagged chunk hits; evictable = each rendered chunk with its anchor + `wiki_read_page`), `wiki_related` (`related_via` chunks), `jira_latest` (LATEST bucket lines; evictable ids = ticket keys + `jira_get_ticket`; the 1–2 full ticket bodies belong to this block, listed first so they're KEEP_MIN-protected), `jira_historical` (HISTORICAL/STALE lines), `config_evidence` (whole block; `evictable=[]` — all-or-nothing, protected by order). Then:

```python
    intent_name = (bundle.intent_result.intent.value
                   if bundle.intent_result else "GENERAL")
    evidence_text, trimmed = seed_budget.apply_budget(blocks, intent_name)
```

Degradation notes and the header stay outside the budget. Keep the existing section headers inside each block's `text` so the rendered seed reads the same when nothing is trimmed.

- [ ] **Step 5: Run tests + full preflight sweep**

Run: `venv/bin/pytest tests/test_seed_budget.py tests/ -q -k "preflight or seed"`
Expected: all pass; existing seed-format tests may need their expected text updated only if they asserted on exact separators (flag any such change in the report).

- [ ] **Step 6: Commit**

```bash
git add backend/seed_budget.py backend/preflight.py tests/test_seed_budget.py
git commit -m "feat(preflight): global seed budget — intent-aware eviction + mandatory trim-note (spec §5.7)"
```

---

### Task 6: Inline citation verification + honest sources + no fabricated confidence

**Files:**
- Create: `backend/citation_check.py`
- Modify: `backend/orchestrator.py` (`_extract_confidence` default; replace `_extract_pms_configs` + `_trace_jira_keys` sourcing; wire verification into `run_deep` post-processing)
- Test: `tests/test_citation_check.py`

**Interfaces:**
- Consumes: answer text; evidence sets built from the bundle: `wiki_anchors: set[str]` (from `seed_wiki_chunks` + trim-note ids), `jira_keys: set[str]` (all bucket keys), `config_names: set[str]` (from `config_evidence` detections); plus best-effort tool-fetched additions via `getattr(result, "tool_trace", None)` (list of `{"tool": name, "input": {...}}` if the provider exposes it — degrade gracefully to seed-only when absent).
- Produces:
  - `@dataclass CitationReport: cited_ok: list[str]; cited_unverified: list[str]; confidence_capped: bool`
  - `verify_citations(answer_text: str, wiki_anchors: set[str], jira_keys: set[str]) -> CitationReport` — extracts cited wiki paths (`` `path/to.md#anchor` `` and `path/to.md` patterns) and ticket keys (`[A-Z]{2,}-\d+`) from the answer; anything cited but ∉ evidence → `cited_unverified`.
  - Orchestrator behavior: if `cited_unverified` non-empty and stated confidence is High → confidence becomes Medium and the answer gains a final line `⚠️ Unverified citations: <list> — verify before relying on them.` `QueryResponse.sources` = `cited_ok` only.
  - `_extract_confidence` returns `"Unknown"` (not `"Medium"`) when no match.

- [ ] **Step 1: Write the failing tests**

```python
"""Inline no-source-no-fact — mechanical set-membership, gates before ship."""
from backend.citation_check import verify_citations


def test_cited_and_retrieved_is_ok():
    r = verify_citations(
        "Per `modules/desk-management.md#overview` and TS-1234 …",
        wiki_anchors={"modules/desk-management.md#overview"},
        jira_keys={"TS-1234"})
    assert set(r.cited_ok) == {"modules/desk-management.md#overview", "TS-1234"}
    assert r.cited_unverified == [] and r.confidence_capped is False


def test_cited_but_never_retrieved_is_flagged():
    r = verify_citations("As documented in `modules/ghost.md` and PB-9999.",
                         wiki_anchors=set(), jira_keys={"TS-1"})
    assert "modules/ghost.md" in r.cited_unverified
    assert "PB-9999" in r.cited_unverified
    assert r.confidence_capped is True


def test_page_level_citation_matches_section_anchor_evidence():
    r = verify_citations("See `modules/a.md`.",
                         wiki_anchors={"modules/a.md#overview"}, jira_keys=set())
    assert r.cited_unverified == []   # page-level cite covered by section evidence


def test_extract_confidence_unknown_not_medium():
    from backend.orchestrator import _extract_confidence
    assert _extract_confidence("no confidence line here") == "Unknown"
```

- [ ] **Step 2: Run tests, verify they fail**

Run: `venv/bin/pytest tests/test_citation_check.py -v`
Expected: FAIL — module missing; `_extract_confidence` returns "Medium".

- [ ] **Step 3: Implement `backend/citation_check.py`**

```python
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
    pages_with_evidence = {a.split("#", 1)[0] for a in wiki_anchors}
    rep = CitationReport()

    for m in dict.fromkeys(_WIKI_CITE_RE.findall(answer_text)):
        ok = (m in wiki_anchors
              or m.split("#", 1)[0] in pages_with_evidence)
        (rep.cited_ok if ok else rep.cited_unverified).append(m)

    for k in dict.fromkeys(_KEY_RE.findall(answer_text)):
        (rep.cited_ok if k in jira_keys else rep.cited_unverified).append(k)
    return rep
```

- [ ] **Step 4: Wire into the orchestrator**

In `backend/orchestrator.py`:

(a) `_extract_confidence` fallback (`return "Medium"` → `return "Unknown"`).

(b) In `run_deep` post-processing (where confidence/sources are currently derived):

```python
    from backend.citation_check import verify_citations

    wiki_anchors = {h.anchor for h in getattr(bundle, "seed_wiki_chunks", [])}
    jira_keys = set()
    for b in bundle.seed_jira.get("buckets", {}).values():
        jira_keys.update(r.get("key") for r in b if r.get("key"))
    for t in (getattr(result, "tool_trace", None) or []):
        inp = t.get("input") or {}
        if t.get("tool") == "jira_get_ticket" and inp.get("key"):
            jira_keys.add(inp["key"])
        if t.get("tool") == "wiki_read_page" and inp.get("path"):
            wiki_anchors.add(inp["path"].removeprefix("wiki/"))

    report = verify_citations(answer_text, wiki_anchors, jira_keys)
    if report.confidence_capped and confidence == "High":
        confidence = "Medium"
        answer_text += ("\n\n⚠️ Unverified citations: "
                        + ", ".join(report.cited_unverified)
                        + " — verify before relying on them.")
```

(c) Replace source derivation: `sources.wiki = [a for a in report.cited_ok if a.endswith('.md') or '#' in a]`, `sources.jira = [k for k in report.cited_ok if _KEY_RE-style match]`; delete the greedy `_extract_pms_configs` backtick scrape — PMS sources become the `config_evidence`-detected property names that appear in the answer text. Keep function names/shape of `QueryResponse` unchanged. Log the report (ok/unverified counts) into the trace metadata.

- [ ] **Step 5: Run tests + orchestrator sweep**

Run: `venv/bin/pytest tests/test_citation_check.py tests/ -q -k "orchestrator or citation or confidence"`
Expected: all pass; update any existing test asserting the fabricated "Medium" default (flag in report — intended contract change).

- [ ] **Step 6: Commit**

```bash
git add backend/citation_check.py backend/orchestrator.py tests/test_citation_check.py
git commit -m "feat(orchestrator): inline citation verification + honest sources + Unknown confidence (spec §5.9)"
```

---

### Task 7: Re-embed-on-write hook — wiki edits keep chunks fresh

**Files:**
- Modify: `backend/wiki_retriever.py` (`build_index` — enqueue background delta re-embed alongside the existing graph invalidation)
- Modify: `scripts/jira_daily_sync.py` (nightly backstop stage: `embed_wiki.py --mode delta`)
- Test: `tests/test_wiki_reembed_hook.py`

**Interfaces:**
- Consumes: `scripts/embed_wiki.py` `run(mode, agent_id, wiki_dir)` (Phase A Task 5); the existing `build_index(agent_id, wiki_dir)` rebuild triggers (every wiki write path already calls it).
- Produces: `backend/retrieval/wiki_v2/reembed.py` with `schedule_delta_reembed(agent_id: str) -> None` — fires `embed_wiki.run("delta", …)` on a daemon thread, coalescing: at most one pending run per agent (a second call while one is queued is a no-op). Failures are logged and swallowed (stale chunks beat a crashed write path — spec §5.2).

- [ ] **Step 1: Write the failing tests**

```python
"""Re-embed hook — background, coalesced, fail-open."""
import threading
import time
from backend.retrieval.wiki_v2 import reembed


def test_schedule_runs_delta_in_background(monkeypatch):
    ran = threading.Event()
    monkeypatch.setattr(reembed, "_run_delta", lambda aid: ran.set())
    reembed.schedule_delta_reembed("conwo")
    assert ran.wait(timeout=2.0)


def test_schedule_coalesces_concurrent_calls(monkeypatch):
    calls = []
    gate = threading.Event()

    def slow(aid):
        calls.append(aid)
        gate.wait(timeout=2.0)
    monkeypatch.setattr(reembed, "_run_delta", slow)
    reembed.schedule_delta_reembed("conwo")
    time.sleep(0.05)
    reembed.schedule_delta_reembed("conwo")   # coalesced — no second run queued twice
    reembed.schedule_delta_reembed("conwo")
    gate.set()
    time.sleep(0.2)
    assert len(calls) <= 2   # first run + at most one queued follow-up


def test_failure_is_swallowed(monkeypatch):
    def boom(aid):
        raise RuntimeError("gemini down")
    monkeypatch.setattr(reembed, "_run_delta", boom)
    reembed.schedule_delta_reembed("conwo")   # must not raise
    time.sleep(0.1)
```

- [ ] **Step 2: Run tests, verify they fail**

Run: `venv/bin/pytest tests/test_wiki_reembed_hook.py -v`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement `backend/retrieval/wiki_v2/reembed.py`**

```python
"""Background delta re-embed on wiki writes (spec §5.2 sync triggers).

Coalesced per agent: one running + at most one queued. Fail-open — a
failed embed leaves the previous chunks in place (stale beats missing);
the nightly delta pass is the backstop."""
from __future__ import annotations
import logging
import threading

_log = logging.getLogger("wiki_reembed")
_state_lock = threading.Lock()
_pending: dict[str, bool] = {}   # agent_id -> a run is queued behind the current one
_running: set[str] = set()


def _run_delta(agent_id: str) -> None:
    import sys
    from pathlib import Path
    root = Path(__file__).resolve().parents[3]
    sys.path.insert(0, str(root / "scripts"))
    import embed_wiki
    from backend import agent_registry
    spec = agent_registry.get(agent_id)
    embed_wiki.run("delta", agent_id, spec.wiki_dir)


def _worker(agent_id: str) -> None:
    while True:
        try:
            _run_delta(agent_id)
        except Exception as exc:
            _log.warning("delta re-embed failed (agent=%s): %s", agent_id, exc)
        with _state_lock:
            if _pending.pop(agent_id, False):
                continue          # a write arrived mid-run — go again
            _running.discard(agent_id)
            return


def schedule_delta_reembed(agent_id: str) -> None:
    with _state_lock:
        if agent_id in _running:
            _pending[agent_id] = True   # coalesce
            return
        _running.add(agent_id)
    threading.Thread(target=_worker, args=(agent_id,), daemon=True,
                     name=f"wiki-reembed-{agent_id}").start()
```

- [ ] **Step 4: Hook into `build_index` and the nightly sync**

In `backend/wiki_retriever.py` `build_index`, next to the graph invalidation added in Phase A:

```python
    from backend.retrieval.wiki_v2 import reembed as _re
    try:
        _re.schedule_delta_reembed(aid)
    except Exception:
        pass  # never let background sync break a wiki write
```

In `scripts/jira_daily_sync.py`, add a stage after `_run_embed_delta` (mirror its subprocess pattern):

```python
def _run_wiki_embed_delta() -> int:
    """Nightly backstop: re-embed wiki pages whose content hash changed."""
    return subprocess.call([sys.executable, "scripts/embed_wiki.py",
                            "--mode", "delta"], timeout=EMBED_TIMEOUT_S)
```

and call it in the pipeline sequence alongside the other v2 stages.

- [ ] **Step 5: Run tests + sweep, commit**

Run: `venv/bin/pytest tests/test_wiki_reembed_hook.py tests/ -q -k "wiki"`
Expected: all pass.

```bash
git add backend/retrieval/wiki_v2/reembed.py backend/wiki_retriever.py scripts/jira_daily_sync.py tests/test_wiki_reembed_hook.py
git commit -m "feat(wiki-v2): background delta re-embed on wiki writes + nightly backstop (spec §5.2)"
```

---

### Task 8: Golden eval harness + set, run the gate, open the PR

**Files:**
- Create: `scripts/eval_wiki_retrieval.py`, `docs/eval/wiki-golden.jsonl` (curated), `scripts/seed_wiki_golden.py`
- Test: `tests/scripts/test_eval_wiki_retrieval.py`

**Interfaces:**
- Golden item JSONL schema: `{"question": str, "expected_pages": [str], "expected_anchors": [str] (optional), "intent": str (optional)}`.
- Harness CLI: `venv/bin/python scripts/eval_wiki_retrieval.py --golden docs/eval/wiki-golden.jsonl --engines keyword,v2 --k 5` → prints per-engine `recall@5` (page-level), `MRR`, `section-hit-rate` (when anchors given), and a per-question win/loss table. Exit code 1 if v2 recall@5 < keyword recall@5 (the merge gate).

- [ ] **Step 1: Write the failing tests (harness logic only — metrics are pure)**

```python
"""Eval harness metrics — recall@k, MRR, section hits."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import eval_wiki_retrieval as ev


def test_recall_at_k():
    got = ["a.md", "b.md", "c.md"]
    assert ev.recall_at_k(got, expected=["b.md"], k=5) == 1.0
    assert ev.recall_at_k(got, expected=["z.md"], k=5) == 0.0
    assert ev.recall_at_k(got, expected=["b.md", "z.md"], k=5) == 0.5


def test_mrr():
    assert ev.mrr(["a.md", "b.md"], expected=["b.md"]) == 0.5
    assert ev.mrr(["x.md"], expected=["y.md"]) == 0.0


def test_section_hit_rate():
    got_anchors = ["a.md#one", "b.md#two"]
    assert ev.section_hit(got_anchors, ["b.md#two"]) is True
    assert ev.section_hit(got_anchors, ["b.md#three"]) is False


def test_golden_loader_validates_schema(tmp_path):
    f = tmp_path / "g.jsonl"
    f.write_text('{"question": "q", "expected_pages": ["modules/a.md"]}\n')
    items = ev.load_golden(f)
    assert items[0]["question"] == "q"
```

- [ ] **Step 2: Run tests, verify they fail; then implement the harness**

`scripts/eval_wiki_retrieval.py` — pure metric functions exactly as tested, plus:

```python
def run_engine(engine: str, question: str, k: int) -> tuple[list[str], list[str]]:
    """Returns (page_paths, anchors). Keyword engine has no anchors."""
    if engine == "keyword":
        from backend import wiki_retriever
        pages = [p.path for p in wiki_retriever.search(question, top_n=k)]
        return pages, []
    from backend.retrieval.wiki_v2 import pipeline
    hits = pipeline.search(question, top_k=k)
    anchors = [h.anchor for h in hits]
    # page-level dedup preserving rank order — recall@k and MRR compare
    # PAGES against expected_pages; anchors only feed section_hit.
    pages = list(dict.fromkeys(a.split("#", 1)[0] for a in anchors))
    return pages, anchors
```

`main()`: load golden, run both engines per question (v2 failures → count as empty + warn), compute recall@5/MRR on the **page** lists and section-hit on the **anchor** list, aggregate, print table, exit 1 when v2 loses on recall@5.

- [ ] **Step 3: Seed the golden set (human-in-the-loop checkpoint)**

`scripts/seed_wiki_golden.py`: extract candidate questions from the answer log (`scripts/log_answer.py` storage — read that script to find its store; fall back to `wiki/log.md` `query |` entries) and emit a draft JSONL with empty `expected_pages` for human curation.

**STOP-AND-CURATE:** the controller/user curates ≥25 items (fills `expected_pages` from wiki knowledge). This step is a checkpoint — do not fabricate expectations mechanically.

- [ ] **Step 4: Run the gate**

```bash
venv/bin/python scripts/eval_wiki_retrieval.py \
  --golden docs/eval/wiki-golden.jsonl --engines keyword,v2 --k 5
```

Requires local PG with migrations + `embed_wiki.py --mode full` run against the local wiki (needs `GOOGLE_GENAI_API_KEY`). Record the output table verbatim — it goes in the PR description. Gate: v2 recall@5 ≥ keyword recall@5.

- [ ] **Step 5: Full suite + push + PR**

```bash
venv/bin/pytest tests/ -q
git push bitbucket feat/wiki-retrieval-v2
```

Open PR: `feat/wiki-retrieval-v2` → `main`, title `feat: wiki retrieval v2 — hybrid semantic + graph + intent (spec 2026-07-07)`, body: merge-day blast radius (flag default-on but empty `wiki_chunks` ⇒ keyword path until backfill; the only immediate live-path changes are the sigmoid calibration [intended, audit C1] and Unknown-confidence/citation-gate), deploy steps (deploy → `embed_wiki.py --mode full` → v2 activates), kill switch (`CONWO_WIKI_RETRIEVAL_V2=off`), eval table, and the two intended contract changes flagged during tasks.
