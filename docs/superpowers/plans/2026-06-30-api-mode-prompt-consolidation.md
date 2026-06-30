# API-mode Prompt Consolidation + Legacy claude-code UI Removal — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `backend/deep_system_prompt.py` the single, complete, non-contradictory source of truth for api-mode answering, and remove the legacy `'claude-code'` single-shot mode from the frontend.

**Architecture:** api mode (production default) routes `orchestrator.run` → `run_deep` → `load_deep_system_prompt`. That assembler currently emits the answer-format + confidence spec TWICE for Jira/PMS agents (once in `_EVIDENCE_BLOCK_JIRA_PMS`, once in `_ANSWER_FOOTER_BLOCK`). We split the footer into a universal hard-rules block + a wiki-only answer-format block so every agent gets exactly one answer template, then port three accuracy rules from CLAUDE.md §5 (cross-source corroboration, intent-adaptive formatting, history-layer handling) into the Jira/PMS (and, for the history rule, wiki-only) evidence blocks. Frontend narrows `QueryMode` to drop the already-hidden `'claude-code'` value and its dead guards.

**Tech Stack:** Python 3 / pytest (backend prompt assembly), Angular / TypeScript (frontend mode selector).

## Global Constraints

- **Reload-safety (CRITICAL):** Editing `backend/*.py` while the backend runs with `--reload` triggers a lifespan rebuild that has caused data loss. The backend MUST be stopped before any backend `.py` edit. Verified not running at plan-authoring time; re-verify before Task 1 (`ps aux | grep -i uvicorn | grep -v grep` → empty).
- **Worktree:** all work happens in `.claude/worktrees/api-prompt-consolidation` (branch `feat/api-prompt-consolidation`, based on `main`/`ea921f2`). Never edit the main checkout.
- **Run backend tests with the repo venv from the worktree root:** `cd <worktree> && /Users/rudrakhare/Desktop/my-wiki/org-wiki/venv/bin/python -m pytest <path> -v`.
- **Scope guard:** Do NOT remove `mode='agent'` (the visible "Claude Code" live-session button) — only the legacy hidden `'claude-code'` single-shot value. Do NOT touch `CLAUDE.md`. Do NOT change retrieval/preflight (trust-tagging is a deferred fast-follow). Do NOT remove the backend `claude-code` branch (deferred).
- **Commit message footer:** end each commit body with `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`. Git identity in this worktree may be unset — if a commit fails with "Author identity unknown", run `git config user.name "Rudra Khare" && git config user.email "rudrakhare@Rudra-Khares-MacBook-Pro-M4.local"` then retry.

---

### Task 1: Backend — de-duplicate the answer-format/confidence spec

**Files:**
- Modify: `backend/deep_system_prompt.py` (split `_ANSWER_FOOTER_BLOCK`; update `load_deep_system_prompt`)
- Test: `tests/test_deep_system_prompt.py` (create)

**Interfaces:**
- Consumes: `load_deep_system_prompt(agent=None) -> str` (existing).
- Produces: same signature. New module-level constants `_HARD_RULES_BLOCK: str` and `_WIKI_ONLY_ANSWER_FORMAT: str`. `_ANSWER_FOOTER_BLOCK` is removed. Behaviour change: a Jira/PMS agent's prompt contains exactly ONE `"## Required answer format"` heading and ONE `"**Confidence calibration:**"`; a wiki-only agent's prompt also contains exactly one of each; both contain `"## Hard rules"`.

- [ ] **Step 1: Confirm backend is stopped**

Run: `ps aux | grep -iE "uvicorn|backend.api" | grep -v grep`
Expected: no output (empty). If anything prints, stop the backend before proceeding.

- [ ] **Step 2: Write the failing test**

Create `tests/test_deep_system_prompt.py`:

```python
"""Structural assertions on the assembled deep-search system prompt."""
from backend.deep_system_prompt import load_deep_system_prompt
from backend import agent_registry


def _conwo():
    return agent_registry.get("conwo")


def test_jira_pms_agent_has_exactly_one_answer_format_and_calibration():
    prompt = load_deep_system_prompt(_conwo())
    assert prompt.count("## Required answer format") == 1, "duplicate answer-format block"
    assert prompt.count("**Confidence calibration:**") == 1, "duplicate confidence calibration"


def test_all_agents_get_universal_hard_rules():
    prompt = load_deep_system_prompt(_conwo())
    assert "## Hard rules" in prompt
    assert "Never invent property names" in prompt
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd /Users/rudrakhare/Desktop/my-wiki/org-wiki/.claude/worktrees/api-prompt-consolidation && /Users/rudrakhare/Desktop/my-wiki/org-wiki/venv/bin/python -m pytest tests/test_deep_system_prompt.py -v`
Expected: `test_jira_pms_agent_has_exactly_one_answer_format_and_calibration` FAILS (count == 2, because both `_EVIDENCE_BLOCK_JIRA_PMS` and `_ANSWER_FOOTER_BLOCK` contain the format). The hard-rules test passes already.

- [ ] **Step 4: Replace `_ANSWER_FOOTER_BLOCK` with two new constants**

In `backend/deep_system_prompt.py`, DELETE the entire `_ANSWER_FOOTER_BLOCK = """..."""` definition (the block starting `# ── Block 3: Answer footer` through its closing `"""`) and replace it with these two constants:

```python
# ── Block 3a: Answer format — wiki-only agents (no Jira/PMS) ──────────────────

_WIKI_ONLY_ANSWER_FORMAT = """\
## Required answer format

```
**Answer:**
<best current answer in 1–3 sentences>

**Detail:**
<supporting evidence from the knowledge base — pages read, key facts found>

**Confidence:** High | Medium | Low
<one-line reason>

**Sources:**
- Wiki/docs: <page paths or "—">

---
**Review this answer:** Score 1–5 (5 = fully correct).
**Answer ID:** `<ANSWER_ID>`
If score ≤3, tell me what was wrong or what the answer should have said.
```

**Confidence calibration:**
- High — multiple wiki pages agree; no conflicts; clear documentation
- Medium — single page, or mild conflict, or partial coverage
- Low — strong conflict, or topic only partially covered, or nothing found
"""

# ── Block 3b: Hard rules — universal (all agents) ────────────────────────────

_HARD_RULES_BLOCK = """\
## Hard rules

- Never invent property names, page paths, or facts — only cite content from tool results.
- Never include auth tokens, Bearer headers, or cookies in your answer.
- If a tool returns an error, treat it as informational and note the limitation in your answer.
- If critical information is still missing after tool use, list it under a \
"Missing context:" heading at the end of your answer.
- Self-check before sending: if you give category counts, they must sum to the
  stated total, and no single item may be counted in two buckets of the same total
  (flag a genuine cross-cut separately — don't double-add it).
- Use the user's OWN category labels. If they asked for "tech / implementation /
  configuration", answer in those exact buckets — don't silently rename one.
"""
```

- [ ] **Step 5: Update the assembler**

Replace the body of `load_deep_system_prompt` (the `blocks = [...]` / `if/else` / `blocks.append(_ANSWER_FOOTER_BLOCK)` section) with:

```python
    blocks = [_SAFETY_BLOCK_DEEP, f"{agent.identity}\n"]

    if agent.has_jira or agent.has_pms:
        # Jira/PMS agents get their single answer format inside the evidence block.
        blocks.append(_EVIDENCE_BLOCK_JIRA_PMS)
    else:
        # Wiki-only agents get the evidence block + the wiki-only answer format.
        blocks.append(_EVIDENCE_BLOCK_WIKI_ONLY)
        blocks.append(_WIKI_ONLY_ANSWER_FORMAT)

    # Hard rules are universal — appended for every agent, exactly once.
    blocks.append(_HARD_RULES_BLOCK)

    return "\n\n".join(blocks)
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd /Users/rudrakhare/Desktop/my-wiki/org-wiki/.claude/worktrees/api-prompt-consolidation && /Users/rudrakhare/Desktop/my-wiki/org-wiki/venv/bin/python -m pytest tests/test_deep_system_prompt.py -v`
Expected: both tests PASS. Also run the existing suite touchpoint: `... -m pytest tests/test_orchestrator.py -v` → no new failures.

- [ ] **Step 7: Commit**

```bash
git add backend/deep_system_prompt.py tests/test_deep_system_prompt.py
git commit -m "fix(prompt): de-duplicate answer-format/confidence in deep_system_prompt

Split _ANSWER_FOOTER_BLOCK into universal _HARD_RULES_BLOCK + wiki-only
_WIKI_ONLY_ANSWER_FORMAT. Jira/PMS agents now get exactly one answer
template (from the evidence block), not two.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Backend — port the three CLAUDE.md §5 accuracy rules

**Files:**
- Modify: `backend/deep_system_prompt.py` (`_EVIDENCE_BLOCK_JIRA_PMS` + `_EVIDENCE_BLOCK_WIKI_ONLY`)
- Test: `tests/test_deep_system_prompt.py` (extend)

**Interfaces:**
- Consumes: the constants from Task 1.
- Produces: `_EVIDENCE_BLOCK_JIRA_PMS` gains three subsections (corroboration, intent-format, history); `_EVIDENCE_BLOCK_WIKI_ONLY` gains the history subsection. No signature change.

- [ ] **Step 1: Write the failing tests (extend the test file)**

Append to `tests/test_deep_system_prompt.py`:

```python
def test_jira_pms_prompt_has_ported_accuracy_rules():
    prompt = load_deep_system_prompt(_conwo())
    assert "Corroborate across sources" in prompt          # G1+G2
    assert "Shape the body to the question's intent" in prompt  # G3
    assert "Release-notes history pages" in prompt          # history rule


def test_wiki_only_prompt_has_history_rule():
    # A wiki-only agent (no jira, no pms). Build a minimal stand-in if no such
    # agent is registered: load conwo's assembler path is jira/pms; for wiki-only
    # use any registered agent with has_jira == has_pms == False, else skip.
    import pytest
    wiki_only = next(
        (a for a in agent_registry.all() if not a.has_jira and not a.has_pms),
        None,
    )
    if wiki_only is None:
        pytest.skip("no wiki-only agent registered in this environment")
    prompt = load_deep_system_prompt(wiki_only)
    assert "Release-notes history pages" in prompt
```

Note: if `agent_registry` exposes the list under a different name than `all()`, use the actual accessor (check `backend/agent_registry.py`; the conwo lookup uses `agent_registry.get("conwo")`). If no enumeration helper exists, keep only `test_jira_pms_prompt_has_ported_accuracy_rules` and assert the history string is present in the `_EVIDENCE_BLOCK_WIKI_ONLY` constant directly: `from backend.deep_system_prompt import _EVIDENCE_BLOCK_WIKI_ONLY; assert "Release-notes history pages" in _EVIDENCE_BLOCK_WIKI_ONLY`.

- [ ] **Step 2: Run to verify failure**

Run: `... -m pytest tests/test_deep_system_prompt.py -v`
Expected: the new test(s) FAIL (strings absent).

- [ ] **Step 3: Add the corroboration subsection (G1+G2)**

In `_EVIDENCE_BLOCK_JIRA_PMS`, immediately AFTER the paragraph that ends `...your tool budget is for\n*expanding* the evidence, not duplicating it.` (end of the "What the backend has already done" intro), insert:

```
## Corroborate across sources — never stop at the first hit

Combine ALL applicable sources before answering: the wiki page(s) + Jira (+ the PMS
config page / config_lookup when the question names a property). Preflight already ran
wiki AND Jira, so synthesize across them — a clear hit from one source does NOT let you
skip the others; cross-source agreement is what makes an answer trustworthy. "Not
documented" / "unknown" is a valid conclusion ONLY after wiki AND Jira (AND the config
sources, when a property is named) have all returned nothing relevant. Corroboration
means checking the OTHER sources — not re-running the same keyword preflight already used.
```

- [ ] **Step 4: Add the intent-format subsection (G3)**

In `_EVIDENCE_BLOCK_JIRA_PMS`, inside the `## Required answer format — fixed spine, flexible body` section, immediately AFTER the line `DEFAULT skeleton for evidence-heavy queries, not a cage.` and BEFORE the opening ```` ``` ```` of the template, insert:

```
**Shape the body to the question's intent** (subordinate to the rule above — match what
the user actually asked; never pad a short ask with a table it didn't request):
- CONFIGURATION (a config/property question) → a markdown table:
  `Property | Service | Type | Default | Server`; below it a `> ⚠️ Related configs: …`
  note for configs that must be set together.
- DEBUGGING → group by failure mode (bold heading each), then a `- [ ]` checklist of
  configs/tickets to verify under each, one line on what each controls.
- COMPARISON → a side-by-side table (rows = aspects, columns = the things compared).
- ARCHITECTURAL → an ASCII flow diagram (│ ▼ ─) of the data/state flow.
- DEFINITION → 2–5 sentences of plain prose, no table.
- HOW_TO → numbered steps, ending with `> ⚠️` caveats (prereqs, server limits).
- GENERAL / STATUS → omit the middle/Detail section entirely.
Always backtick config/property/service names and enum values. Use ⚠️ only for caveats.
```

- [ ] **Step 5: Add the history-layer rule to BOTH evidence blocks**

Define this exact text once and paste it into both constants:

```
## Release-notes history pages are dated changelog, not current truth

`history/release-notes-*` pages are a dated product changelog (sales/PM source-of-truth),
NOT authoritative current behavior. Rank them BELOW the module/config pages for the same
topic. Use them to answer "when did X ship / change?" and to show how a feature evolved.
If a history page disagrees with a current module/config page, the module/config page wins
and the release note is historical context — surface the difference with ⚠️ (Current vs
Previously); never let a dated changelog override the current page.
```

- In `_EVIDENCE_BLOCK_JIRA_PMS`: insert immediately AFTER the `## Jira evidence — time-aware ranking` section (after its line `Never treat a 2023 ticket and a 2026 ticket as equal-weight evidence.`).
- In `_EVIDENCE_BLOCK_WIKI_ONLY`: insert immediately AFTER the `## Evidence approach` section (after the "...try at least two search angles..." paragraph).

- [ ] **Step 6: Run tests to verify they pass**

Run: `... -m pytest tests/test_deep_system_prompt.py -v`
Expected: all tests PASS.

- [ ] **Step 7: Eyeball render (manual sanity)**

Run: `cd <worktree> && /Users/.../venv/bin/python -c "from backend.deep_system_prompt import load_deep_system_prompt; from backend import agent_registry; p=load_deep_system_prompt(agent_registry.get('conwo')); print('FORMAT COUNT', p.count('## Required answer format')); print('HISTORY', 'Release-notes history pages' in p); print('CORROBORATE', 'Corroborate across sources' in p); print('INTENT', \"Shape the body\" in p)"`
Expected: `FORMAT COUNT 1`, `HISTORY True`, `CORROBORATE True`, `INTENT True`.

- [ ] **Step 8: Commit**

```bash
git add backend/deep_system_prompt.py tests/test_deep_system_prompt.py
git commit -m "feat(prompt): port §5 accuracy rules into api-mode deep prompt

Add cross-source corroboration (never stop at first hit + 'not documented'
discipline), intent-adaptive Detail formatting, and the release-notes
history-layer rule to the deep-search evidence blocks.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Frontend — remove legacy `'claude-code'` from QueryMode

**Files:**
- Modify: `frontend/src/app/core/api.service.ts` (`QueryMode` type line 5; `getStoredMode` ~line 647; comment ~line 361)
- Modify: `frontend/src/app/features/ask/ask.ts` (coercion ~line 454)
- Modify: `frontend/src/app/shared/mode-selector/mode-selector.ts` (dead guard line 118; docstring lines 7–8)

**Interfaces:**
- Produces: `export type QueryMode = 'api' | 'agent';`. `getStoredMode()` returns only `'api' | 'agent'`. No runtime behavior change for current users (legacy value was already hidden + coerced); this removes dead code and tightens the type. `modeLabel(m: string)` is intentionally left untouched — it still maps historical `'claude-code'` values for display of old messages/traces (its param is `string`, not `QueryMode`).

- [ ] **Step 1: Narrow the QueryMode type**

`frontend/src/app/core/api.service.ts` line 5 — change:
```typescript
export type QueryMode = 'api' | 'claude-code' | 'agent';
```
to:
```typescript
export type QueryMode = 'api' | 'agent';
```

- [ ] **Step 2: Update `getStoredMode` to drop the legacy value**

`frontend/src/app/core/api.service.ts` ~line 645–649 — change:
```typescript
  getStoredMode(): QueryMode {
    const v = localStorage.getItem(MODE_STORAGE);
    if (v === 'claude-code' || v === 'agent') return v;
    return 'api';
  }
```
to:
```typescript
  getStoredMode(): QueryMode {
    const v = localStorage.getItem(MODE_STORAGE);
    if (v === 'agent') return v;
    return 'api';   // any other/stale value (incl. legacy 'claude-code') → api
  }
```

- [ ] **Step 3: Update the comment that references claude-code**

`frontend/src/app/core/api.service.ts` ~line 361 — change the trailing comment `// api | claude-code` to `// api | agent`. (Cosmetic; keeps the doc honest.)

- [ ] **Step 4: Simplify the ask.ts mode init (remove coercion)**

`frontend/src/app/features/ask/ask.ts` ~line 452–454 — change:
```typescript
    const stored = this.api.getStoredMode();
    // Migrate any user previously on the legacy single-shot mode to Deep Search.
    this.mode.set(stored === 'claude-code' ? 'api' : stored);
```
to:
```typescript
    const stored = this.api.getStoredMode();   // already 'api' | 'agent' (legacy coerced in getStoredMode)
    this.mode.set(stored);
```
(Leave the following `if (this.mode() === 'agent' && !this.agentSupportsAgentMode()) { this.mode.set('api'); }` lines unchanged.)

- [ ] **Step 5: Remove the dead hidden-mode guard + fix the mode-selector docstring**

`frontend/src/app/shared/mode-selector/mode-selector.ts` line 118 — delete the line:
```typescript
    if (mode === 'claude-code') return; // hidden mode — never emitted from the picker
```
(The remaining `selectMode` keeps `if (mode === 'agent' && !this.claudeCodeAvailable()) return;` and `this.modeChanged.emit(mode);`.)

And update the file's top docstring (lines 7–8) — remove the now-obsolete sentence about the legacy single-shot mode:
```typescript
/**
 * Two-option mode selector.
 *
 *   Deep Search   → mode='api'    — Anthropic API key, 9 backend tools, shows trace.
 *   Claude Code   → mode='agent'  — Server's Claude Code session (admin), live agent stream.
 */
```

- [ ] **Step 6: Typecheck / build to catch any remaining references**

Run: `cd /Users/rudrakhare/Desktop/my-wiki/org-wiki/.claude/worktrees/api-prompt-consolidation/frontend && npm run build` (or `npx ng build`).
Expected: build SUCCEEDS. If TypeScript reports a `'claude-code'` no-overlap error anywhere not listed above (e.g. a traces component), fix that site the same way: if it's a `QueryMode`-typed comparison, remove the dead branch; if it's display of historical `string` data, leave it (it's type-safe). Re-run until green.

- [ ] **Step 7: Manual check (stale localStorage)**

In a browser devtools console (or reason through it): set `localStorage.conwo_query_mode = 'claude-code'`, reload the ask view. Expected: app loads in Deep Search (api) mode without error; mode selector shows Deep Search + Claude Code(agent) only.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/app/core/api.service.ts frontend/src/app/features/ask/ask.ts frontend/src/app/shared/mode-selector/mode-selector.ts
git commit -m "refactor(ui): remove legacy 'claude-code' single-shot mode from QueryMode

Narrow QueryMode to 'api' | 'agent'; drop the hidden-mode guard and the
stored-value coercion (legacy value now coerced to api in getStoredMode).
The visible 'Claude Code' (agent) live-session button is unchanged.
modeLabel still renders historical 'claude-code' values for old messages.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Self-Review

**Spec coverage** (spec §4.1–4.5):
- §4.1 de-dup → Task 1. ✅
- §4.2 corroboration (G1+G2) → Task 2 Step 3. ✅
- §4.3 intent-format (G3) → Task 2 Step 4. ✅
- §4.4 history rule → Task 2 Step 5 (both blocks). ✅
- §4.5 claude-code UI removal → Task 3. ✅
- §6 CLAUDE.md mirror → intentionally DROPPED as YAGNI (it would only feed the legacy claude-code path being removed; the authoring agent reads §2k already). Noted here so the omission is deliberate, not a gap.
- §5 deferrals (retrieval trust-tagging, backend claude-code removal) → out of scope, per Global Constraints. ✅

**Placeholder scan:** No TBD/TODO. Every code step shows full content. The one conditional ("if agent_registry has no enumeration helper…") gives an explicit fallback assertion, not a placeholder.

**Type consistency:** `QueryMode = 'api' | 'agent'` used consistently across Task 3 steps; `getStoredMode` return type matches; `load_deep_system_prompt` signature unchanged; new constants `_HARD_RULES_BLOCK` / `_WIKI_ONLY_ANSWER_FORMAT` referenced exactly in the Task 1 assembler.

**Ordering:** Task 1 (dedup) before Task 2 (add rules) so the "exactly one answer-format" assertion is meaningful before new content lands. Task 3 (frontend) is independent and may run any time.
