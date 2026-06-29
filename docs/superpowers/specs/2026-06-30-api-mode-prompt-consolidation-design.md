# Design — API-mode answering prompt consolidation + claude-code UI removal

- **Date:** 2026-06-30
- **Status:** approved (brainstorming), pending spec review
- **Branch:** `feat/api-prompt-consolidation` (off `main` @ 34bb19e)
- **Author:** Rudra Khare (+ Claude)

---

## 1. Problem

Production `/query` runs in **api mode**, whose answering agent reads **only**
`backend/deep_system_prompt.py`. Two other surfaces exist but do NOT reach the api answer path:

- `CLAUDE.md §5` (QUERY workflow) is shipped only to the **legacy `claude-code` single-shot mode**
  (via `backend/system_prompt.py`, which extracts `spec.prompt_sections=(5,9,12)`).
- `CLAUDE.md` as a whole is read only by the **authoring agent** (Claude Code), never by either answering path.

Consequences:
1. Good accuracy rules that live in `CLAUDE.md §5` **never reach production** answers.
2. `deep_system_prompt.py` has a **duplication defect**: for conwo (Jira/PMS agent) it ships the
   "Required answer format" + "Confidence calibration" **twice** — once in `_EVIDENCE_BLOCK_JIRA_PMS`
   (lines ~266–315) and again in `_ANSWER_FOOTER_BLOCK` (lines ~377–416) — two competing templates.
3. The legacy `claude-code` mode is half-removed from the UI but still present in the type system
   and backend, creating confusion about which path is canonical.

**Goal:** make `deep_system_prompt.py` the single, complete, non-contradictory source of truth for
api-mode answering, and remove `claude-code` from the UI so api is unambiguously the only mode.

## 2. The three-layer frame (resolves "which is better?")

These are not competing options — they are different layers; accuracy needs all three:

| Layer | File(s) | Role |
|---|---|---|
| **Retrieval (hybrid search)** | `preflight.py`, `wiki_retriever.py`, tools | *What evidence* the agent sees (wiki TF-IDF + Jira ranked + config SQLite + module/dependency-graph tickets) |
| **Synthesis prompt** | `deep_system_prompt.py` | *How* the agent reasons over + formats evidence — **the only prompt api mode reads** |
| **Authoring / legacy** | `CLAUDE.md` | Authoring instructions + legacy claude-code path |

This design changes only the **synthesis prompt** layer (+ the UI mode). Retrieval is unchanged.

## 3. Gap analysis (deep_system_prompt.py vs CLAUDE.md §5)

`deep_system_prompt.py` already directs the model **better** on the hardest accuracy dimensions:
tool routing (names real api tools), grounding/anti-drift ("anchor to the user's facts", "only cite
keys you've seen"), the internal-consistency confidence downgrade, and PMS disambiguation.

`CLAUDE.md §5` is better on exactly **three** things, which are the gaps to port (translated to
api/tool language — NOT copied verbatim, since §5's tool steps reference CLI scripts that would
misdirect the api agent):

- **G1 — Cross-source corroboration:** the knowledge-source matrix + "never stop after the first good hit."
- **G2 — "Not documented" discipline:** only valid after *all applicable* sources (wiki AND Jira AND config) are empty.
- **G3 — Intent-adaptive Detail formats:** CONFIGURATION→table, DEBUGGING→checklist, COMPARISON→table,
  ARCHITECTURAL→ASCII, DEFINITION→prose, HOW_TO→numbered steps (subordinate to "match the user's actual ask").

## 4. Design — scope items 1–5

### 4.1 De-duplicate the answer-format / confidence spec (the defect)
Split `_ANSWER_FOOTER_BLOCK` into two parts:
- **`_HARD_RULES_BLOCK`** (universal, all agents): keep the existing "Hard rules" (never invent,
  counts must sum, use the user's category labels, no secrets, list missing context). Appended for every agent.
- The footer's **"Required answer format" + "Confidence calibration"** become the **wiki-only** answer
  format, used ONLY for agents without Jira/PMS. Jira/PMS agents (conwo) get their single answer
  format from `_EVIDENCE_BLOCK_JIRA_PMS` (the Latest/Historical/Conflict spine) — no second template.

Result: every agent sees exactly **one** answer-format template + **one** confidence calibration + the
universal hard rules. The assembler (`load_deep_system_prompt`) is updated accordingly.

### 4.2 Port G1 + G2 into `_EVIDENCE_BLOCK_JIRA_PMS`
Add a compact **"Corroborate across sources"** subsection:
> Combine wiki + Jira (+ config when a property is named) on every query — preflight already ran both,
> so synthesize across them; do not stop at the first source that answers. "Not documented" is only a
> valid conclusion after wiki AND Jira (AND config, if a property was named) have all returned nothing.

(Keeps the existing "don't re-search the same keyword" rule — corroboration ≠ duplication.)

### 4.3 Port G3 — intent-adaptive Detail formats
Add a compact **"Shape the body to the question's intent"** subsection to the Jira/PMS answer-format
section, explicitly subordinate to the existing "match the user's actual ask; don't pad a short ask":
> - CONFIGURATION → table: `Property | Service | Type | Default | Server` (+ ⚠️ related-configs note)
> - DEBUGGING → failure-mode groups, each a `- [ ]` checklist of configs to verify
> - COMPARISON → side-by-side table (rows = aspects, columns = the things compared)
> - ARCHITECTURAL → ASCII flow diagram
> - DEFINITION → 2–5 sentence prose, no table
> - HOW_TO → numbered steps + `> ⚠️` caveats
> - GENERAL / STATUS → no Detail section
> Backtick every config/property/service/enum identifier. Use ⚠️ only for caveats.

### 4.4 Add the release-notes history-layer rule
Add to `_EVIDENCE_BLOCK_JIRA_PMS` (and the wiki-only block, since history pages are wiki content) a
compact **"History / release-notes pages"** rule:
> `history/release-notes-*` pages are a dated changelog (sales/PM source-of-truth), NOT authoritative
> current behavior. Rank them BELOW the module/config pages. Use them to answer "when did X ship / change?"
> and to show evolution. Never let a dated changelog override a current module/config page; if they
> disagree, the module/config page is authoritative and the RN is historical context — flag with ⚠️.

### 4.5 Remove `claude-code` mode from the UI
Frontend (`frontend/src/`):
- `core/api.service.ts`: `QueryMode = 'api' | 'claude-code' | 'agent'` → remove `'claude-code'`.
- `shared/mode-selector/mode-selector.ts`: remove the `if (mode === 'claude-code') return;` hidden-mode
  guard (line ~118) and any claude-code references in the picker; api is the only selectable answering mode.
- `features/ask/ask.ts`: remove the coercion `stored === 'claude-code' ? 'api' : stored` (line ~454) —
  with the type narrowed, a stale localStorage value should still fall back to `'api'` safely (keep a
  defensive default, just drop the explicit claude-code branch).
- Audit `traces/*` (`trace-list.ts`, `dashboard.ts`, `trace-detail.ts`) for claude-code mode labels —
  leave historical trace *data* intact (old traces may carry `mode: "claude-code"`), only remove
  UI affordances that let a user *select* it.

**Backend:** out of scope for removal in this pass — `orchestrator.run` / `api.py` keep accepting
`mode="claude-code"` defensively (no UI emits it). A later cleanup pass may remove the backend branch
once telemetry confirms zero usage. (Documented as fast-follow; not done here to keep blast radius small.)

## 5. Decisions locked
- **Intent→format set:** FULL set (config/debug/compare/architectural/definition/how-to), compact,
  subordinate to "match the user's ask."
- **Retrieval trust-tagging** (rank `history/*` below module/config pages *in preflight*): **deferred**
  to a documented fast-follow. §4.4 handles it at the prompt layer for now (the agent is told to rank
  history below module/config); the retrieval-layer guarantee is a separate spec.
- **Backend claude-code removal:** deferred (UI removal only this pass).

## 6. Files changed
| File | Change |
|---|---|
| `backend/deep_system_prompt.py` | Split footer → `_HARD_RULES_BLOCK` (universal) + wiki-only format; add corroboration (G1/G2), intent-format (G3), history-layer rule to the Jira/PMS block; update `load_deep_system_prompt` assembler. |
| `frontend/src/app/core/api.service.ts` | Drop `'claude-code'` from `QueryMode`. |
| `frontend/src/app/shared/mode-selector/mode-selector.ts` | Remove claude-code hidden-mode guard / references. |
| `frontend/src/app/features/ask/ask.ts` | Remove claude-code coercion; keep safe `'api'` default. |
| `CLAUDE.md` §5 (optional mirror) | Add a one-paragraph history-layer recency note so the authoring/legacy surface matches. **The file is otherwise untouched** (this is NOT removing claude-code from CLAUDE.md — only the UI mode is removed). |

## 7. Risks & mitigations
- **Reload-safety:** editing `backend/deep_system_prompt.py` is a backend `.py` write → **stop the
  backend first** (the §1 rule that caused the prior wiki-loss incident). Verify backend is down before editing.
- **History pages live on another branch:** `wiki/history/*` currently exist only on
  `feat/se-runbook-ingest`, not `main`. The §4.4 rule is forward-looking and harmless if the pages
  aren't present yet (agent simply finds none to rank). Note sequencing: ideally the wiki PR merges
  first, but not a blocker.
- **Prompt bloat vs the ~2KB design intent:** the added blocks are compact; net growth is modest and
  offset by removing the duplicated footer template. Keep additions terse.
- **Frontend type narrowing:** removing `'claude-code'` from `QueryMode` may surface TS compile errors
  anywhere it's referenced — the file audit in §4.5 covers the known sites; run `ng build` / typecheck to catch the rest.

## 8. Verification
- Backend: a small unit assertion that `load_deep_system_prompt(conwo)` contains exactly ONE
  "Required answer format" and ONE "Confidence calibration"; and that wiki-only vs Jira/PMS agents each
  get a single, correct format. Add to existing prompt tests if present.
- Backend: spot-render `load_deep_system_prompt()` for conwo and an infosec-style (wiki-only) agent;
  eyeball for one template each + presence of corroboration/intent-format/history rules (Jira/PMS) and
  history rule (wiki-only).
- Frontend: `ng build` (typecheck) passes; mode-selector shows no claude-code option; stale
  `conwo_query_mode=claude-code` in localStorage resolves to api without error.
- Manual: run 3–4 representative queries (a config lookup, a debugging Q, a "when did X change?" Q) and
  confirm the intent-adaptive format + history-as-historical behavior.

## 9. Out of scope
- Retrieval-layer trust-tagging of history pages (fast-follow spec).
- Backend removal of the `claude-code` orchestrator branch (fast-follow).
- Any change to CLAUDE.md beyond the optional one-paragraph history mirror in §5.
- Any wiki-content change (that's the separate `feat/se-runbook-ingest` PR).
