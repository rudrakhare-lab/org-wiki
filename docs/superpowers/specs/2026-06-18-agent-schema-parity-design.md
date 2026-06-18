# Conwo ↔ Created-Agent Schema Parity — Design

_Date: 2026-06-18 · Status: approved for planning · Builds on: self-service agent creation (backend + frontend, branch `claude/hopeful-roentgen-cda2f4`)_

## 1. Problem

Created agents (`schema_kind='generic'`, wiki-only) are meant to replicate every Conwo
capability, but several code paths silently assume Conwo's WorkInSync conventions
(`modules/`/`configs/`/`cross-module/` page types, `[[wikilinks]]`, bare-slug
`depends_on`, frontmatter `type:`, "WorkInSync" branding). When a generic agent produces
a different but valid shape (`concepts/`/`relationships/`/`topics/`, frontmatter page-path
refs, `category:`), those paths degrade quietly. Five such gaps were already found and
fixed during live testing (extract tools, write tools, ingest empty-turn loop, the
ingest-execute guardrail, graph edges-from-frontmatter). This pass finds and fixes the
**remaining** gaps of the same two classes and **centralizes the conventions** so the
class of bug stops recurring.

Two gap classes:
- **Schema-divergence** — code hardcodes WorkInSync page-types/branding, so generic
  content is mishandled.
- **Untested-pipeline** — agent-scoped features built for Conwo, never exercised for a
  wiki-only/generic agent.

**Important framing:** none of the remaining gaps *block* ingest (a generic agent's
create→ingest→graph→query flow works end-to-end). They are correctness, quality, and
cosmetic refinements that make a created agent indistinguishable from Conwo in polish.

## 2. Validated findings (10 gaps)

### Functional / correctness
| # | Gap | File (verified) | Effect on a generic agent |
|---|-----|-----------------|---------------------------|
| 1 | `_page_type` reads frontmatter `type:` only; generic pages use `category:` | `backend/wiki_graph_api.py:25` | All generic graph nodes are `type="unknown"` → legend/coloring dead |
| 2 | `CATEGORY_DIRS` lacks `topics`, `relationships`; validation returns `unknown_category` | `backend/tools/wiki_read_tools.py:15-26,58-59` | `wiki_check_duplicate`/`wiki_list_pages` reject those categories → duplicate detection silently fails → re-ingest can create duplicate pages |
| 3 | `_NEW_PATH_ALLOWLIST` lacks `relationships/`, `topics/`, `entities/` | `backend/tools/wiki_propose_tools.py:49,431` | A generic agent can't **chat-propose** those page types |
| 4 | System-prompt header hardcodes "WorkInSync Knowledge Query System" for every agent | `backend/system_prompt.py:99` | A Legal/Infosec agent is told it's a WorkInSync system → mis-frames answers |
| 5 | Ingest plan/execute prompt **prose** is WorkInSync-biased (modules, depends_on/used_by, BIDIRECTIONALITY, `raw/modules/<slug>`) | `backend/ingest_api.py:61-119,~130-195` | Generic agent reads instructions it can't follow → lower-quality plans |
| 6 | `_SCALAR_FIELDS` lacks `category` | `backend/tools/wiki_write_tools.py:25-26` | Fragile — a future list-append could corrupt the scalar `category` |

### Cosmetic / UX
| # | Gap | File (verified) |
|---|-----|-----------------|
| 7 | Graph legend `TYPE_COLORS` lacks `topics`/`relationships` | `frontend/src/app/features/graph/graph-page.ts:16-27` |
| 8 | Source drawer always renders an empty "PMS configs" section for wiki-only agents | `frontend/src/app/shared/source-drawer/source-drawer.ts:56-64` |
| 9 | Ingest plan-step `hasExistingModule()` only checks `wiki/modules/` | `frontend/src/app/features/ingest/plan-step.ts` |
| 10 | No auto-generated `index.md` for created agents (bare homepage) | provisioning/ingest |

### Already handled (do not re-touch)
extract tools, wiki write tools, ingest empty-turn loop, ingest-execute guardrail
(`allow_writes`), graph edges-from-frontmatter, per-agent index, deep-system-prompt
Jira/PMS gating, preflight Jira-skip for wiki-only agents.

## 3. Approach — centralize + point-fix

### 3.1 New source of truth: `backend/wiki_schema.py`
A dependency-light module (imports nothing from `agent_registry`; takes a `schema_kind`
string) defining per-schema conventions:

```
@dataclass(frozen=True)
class SchemaConventions:
    kind: str                       # 'workinsync' | 'generic'
    categories: tuple[str, ...]     # page-type folder names
    propose_allowlist: tuple[str, ...]   # folders chat-propose may create (e.g. "concepts/")
    page_types: dict[str, PageTypeMeta]  # name -> {label, color}  (legend source of truth)

WORKINSYNC = SchemaConventions(kind="workinsync",
    categories=("modules","entities","sources","concepts","decisions",
                "cross-module","configs","integrations","persons","patterns"), ...)
GENERIC = SchemaConventions(kind="generic",
    categories=("concepts","relationships","topics","entities","sources","decisions"), ...)

# Module-level shared constants (schema-agnostic):
SCALAR_FRONTMATTER_FIELDS: frozenset[str]   # includes "category"
RELATION_FRONTMATTER_FIELDS: frozenset[str] # party_a/party_b/sourced_from/related_concepts/depends_on/used_by/...
ALL_CATEGORIES: frozenset[str]              # union across schemas — for permissive validation

def for_kind(kind: str) -> SchemaConventions   # default WORKINSYNC on unknown
def for_agent(agent) -> SchemaConventions      # agent.schema_kind -> for_kind
def page_type(text: str) -> str                # frontmatter type: then category: then "unknown"
```

**Resolution rules (the key design decisions, already approved):**
- **Category validation uses the UNION** (`ALL_CATEGORIES`): a category is "known" if *any*
  schema uses it. This fixes #2 without requiring agent context in the validation path and
  never wrongly rejects.
- **Allowlists / labels resolve per the ACTIVE agent's schema** via `agent_context`
  (chat-propose, etc.), because a workinsync agent should not propose `topics/`.
- **Safe default = WORKINSYNC** so any path lacking agent context reproduces Conwo's exact
  behavior (back-compat).

### 3.2 Backend consumers routed through it
- `wiki_graph_api.py` → `_page_type` delegates to `wiki_schema.page_type` (type→category fallback). (#1)
- `wiki_read_tools.py` → category validation checks `wiki_schema.ALL_CATEGORIES`; keep
  `CATEGORY_DIRS` path mapping but extend it to cover all categories incl. `topics`/`relationships`. (#2)
- `wiki_propose_tools.py` → `_NEW_PATH_ALLOWLIST` replaced by
  `wiki_schema.for_agent(agent_context.get_current_agent()).propose_allowlist`. (#3)
- `wiki_write_tools.py` → `_SCALAR_FIELDS` sourced from `wiki_schema.SCALAR_FRONTMATTER_FIELDS` (+`category`). (#6)
- `system_prompt.py` → header no longer hardcodes "WorkInSync"; use a neutral product line
  derived from `spec.display_name`/identity (no WorkInSync unless the agent IS workinsync). (#4)
- `ingest_api.py` → the prompt **prose** blocks become schema-aware (extend the existing
  `_wiki_structure`/`_classification_*` split to the narrative: generic variant drops
  modules/BIDIRECTIONALITY/`raw/modules/` and uses concept/relationship/topic language). (#5)

### 3.3 Frontend alignment (canonical = backend; legend stays a small synced static map)
- `graph-page.ts` → add `topics`/`relationships` to `TYPE_COLORS` (now colored because the
  backend emits real types after #1). (#7)
- `source-drawer.ts` → render the PMS section only when the active agent `has_pms`. (#8)
- `plan-step.ts` → `hasExistingModule()` generalized to "operation targets an existing page"
  regardless of category (check against the plan's existing-page set, not the `modules/` prefix). (#9)
- `index.md` generation (#10): provisioning already writes a minimal `index.md`; extend it to
  a schema-appropriate stub, and have ingest-execute refresh a simple page-count/section list
  (reuse the existing `wiki_rebuild_index` or write the index in `_run_ingest_job` after build).

### 3.4 Parity regression test: `tests/test_schema_parity.py`
Pure/unittest assertions that lock the conventions:
- `wiki_schema.page_type("---\ncategory: concepts\n---\n")` == "concepts"; `type:` still wins when present.
- `"topics" in ALL_CATEGORIES` and `"relationships" in ALL_CATEGORIES`.
- `for_kind("generic").propose_allowlist` contains `relationships/`, `topics/`, `entities/`;
  `for_kind("workinsync")` does not contain `topics/`.
- `"category" in SCALAR_FRONTMATTER_FIELDS`.
- `system_prompt.load_system_prompt(<generic agent>)` contains no "WorkInSync"; the workinsync agent still does.
- `for_kind("workinsync").categories` equals today's exact CATEGORY_DIRS keys (Conwo unchanged).

## 4. Error handling & back-compat
- Unknown `schema_kind` → `for_kind` returns WORKINSYNC (never raises).
- No agent context → resolvers fall back to WORKINSYNC / union; tools never crash.
- Conwo paths must stay byte-identical: the full existing pytest suite (currently 473 pass /
  5 known pre-existing failures) must stay green with 0 new failures, and `npx ng build` clean.

## 5. Non-goals (YAGNI)
- No backend→frontend conventions API; the frontend legend remains a small static map kept in
  sync with `wiki_schema` (documented as such).
- No change to Conwo behavior or new page types.
- No re-ingest required for already-created agents (fixes apply to existing content).

## 6. Definition of done
- All 10 gaps fixed; `wiki_schema.py` is the single backend source of truth and the scattered
  hardcoded lists route through it.
- `tests/test_schema_parity.py` green; full backend suite green (only the 5 known failures);
  `npx ng build` clean.
- Manual: a created agent's graph shows colored, typed, connected nodes; re-ingesting the same
  doc does not create duplicates; its system prompt/identity carries no "WorkInSync"; the source
  drawer has no empty PMS section; its homepage `index.md` is non-empty.
