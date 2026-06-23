# Conwo ↔ Created-Agent Schema Parity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make created (generic) agents behave identically in polish to Conwo by centralizing per-schema wiki conventions in one module and routing every scattered hardcoded WorkInSync assumption through it, fixing 10 parity gaps + 1 agent-scoping bug.

**Architecture:** Add `backend/wiki_schema.py` as the single source of truth for per-`schema_kind` conventions (categories, propose-allowlist, scalar fields, page-type resolution, display labels/colors). Route the backend consumers (graph, read tools, propose tools, write tools, system prompt, ingest prompts) through it. Align the frontend cosmetics. Lock it with a parity regression test. Conwo (`schema_kind='workinsync'`) stays byte-identical — its conventions reproduce today's exact hardcoded lists.

**Tech Stack:** Python 3.13 + pytest (backend, gate: `venv/bin/python -m pytest`), Angular + SCSS (frontend, gate: `npx ng build`). Postgres-backed agent registry; `agent_context` ContextVar carries the active agent.

## Global Constraints

- Worktree only: all paths under `/Users/rudrakhare/Desktop/my-wiki/org-wiki/.claude/worktrees/hopeful-roentgen-cda2f4`. Branch must be `claude/hopeful-roentgen-cda2f4`. NEVER touch `/Users/rudrakhare/Desktop/my-wiki/org-wiki/...` (the user's main checkout, different branch).
- Python interpreter for tests/builds: `/Users/rudrakhare/Desktop/my-wiki/org-wiki/venv/bin/python`. Frontend cwd: `<worktree>/frontend`.
- **Operational safety:** the backend may be running with `--reload`; a `.py` write triggers a reload. Before each task that edits backend `.py`, the controller ensures the backend is stopped. Subagents must NOT start/stop servers; just edit + run pytest (test DB) / ng build.
- **Back-compat is non-negotiable:** `wiki_schema.for_kind('workinsync')` must reproduce today's exact category list, scalar fields, and propose-allowlist. The full backend suite must stay green except the 5 known pre-existing failures (`test_google_login_returns_500_when_client_id_not_configured`, `test_plan_returns_409_when_locked`, `test_list_offices_no_credentials_returns_credentials_required`, `test_lifespan_warns_when_anthropic_key_missing`, `test_pms_runtime_values_no_credentials`). 0 new failures. `npx ng build` clean.
- `ng test` cannot run green in this environment (Node 25 webstorage breaks localStorage); `npx ng build` is the frontend gate.
- Co-author trailer on every commit: `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.

---

## File Structure

| File | Responsibility | Change |
|------|----------------|--------|
| `backend/wiki_schema.py` | Per-schema conventions source of truth | **Create** |
| `backend/wiki_graph_api.py` | Graph node typing | `_page_type` → `wiki_schema.page_type` (type→category fallback) |
| `backend/tools/wiki_read_tools.py` | `wiki_check_duplicate`/`wiki_list_pages` | Agent-scope to `agent.wiki_dir`; categories from `wiki_schema` |
| `backend/tools/wiki_propose_tools.py` | Chat propose allowlist | Per-active-agent `propose_allowlist` |
| `backend/tools/wiki_write_tools.py` | Frontmatter write guards | `_SCALAR_FIELDS` from `wiki_schema` (+`category`) |
| `backend/system_prompt.py` | Query system prompt header | Drop hardcoded "WorkInSync" for non-workinsync agents |
| `backend/ingest_api.py` | Ingest plan/execute prompts | Schema-aware prose (generic variant) |
| `backend/ingest_service.py` | Ingest execute job | Write a schema-appropriate `index.md` after build |
| `backend/agent_provisioning.py` | Agent creation | Seed a schema-appropriate `index.md` stub |
| `frontend/.../graph/graph-page.ts` | Graph legend | Add `topics`/`relationships` colors |
| `frontend/.../shared/source-drawer/source-drawer.ts` | Source drawer | Gate PMS section on `has_pms` |
| `frontend/.../features/ingest/plan-step.ts` | Ingest plan UI | Generalize `hasExistingModule()` |
| `tests/test_schema_parity.py` | Regression guard | **Create** |

---

## Task 1: Create `backend/wiki_schema.py` (source of truth)

**Files:**
- Create: `backend/wiki_schema.py`
- Test: `tests/test_schema_parity.py` (create, grow across tasks)

**Interfaces:**
- Produces:
  - `SchemaConventions` frozen dataclass: `kind: str`, `categories: tuple[str,...]`, `propose_allowlist: tuple[str,...]`, `page_types: dict[str, dict]` (each `{"label": str, "color": str}`)
  - `WORKINSYNC`, `GENERIC`: `SchemaConventions`
  - `ALL_CATEGORIES: frozenset[str]` (union of both schemas' categories)
  - `SCALAR_FRONTMATTER_FIELDS: frozenset[str]` (includes `"category"`)
  - `RELATION_FRONTMATTER_FIELDS: frozenset[str]`
  - `for_kind(kind: str) -> SchemaConventions` (unknown → WORKINSYNC)
  - `for_agent(agent) -> SchemaConventions` (reads `agent.schema_kind`)
  - `page_type(text: str) -> str` (frontmatter `type:` → `category:` → `"unknown"`)

- [ ] **Step 1: Write the failing test** — append to `tests/test_schema_parity.py`:

```python
from backend import wiki_schema as ws


def test_workinsync_categories_match_legacy():
    # Conwo unchanged: these are exactly today's CATEGORY_DIRS keys.
    assert ws.for_kind("workinsync").categories == (
        "modules", "entities", "sources", "concepts", "decisions",
        "cross-module", "configs", "integrations", "persons", "patterns",
    )


def test_generic_categories():
    g = ws.for_kind("generic").categories
    assert "concepts" in g and "relationships" in g and "topics" in g and "sources" in g


def test_all_categories_is_union():
    assert "topics" in ws.ALL_CATEGORIES and "relationships" in ws.ALL_CATEGORIES
    assert "modules" in ws.ALL_CATEGORIES and "configs" in ws.ALL_CATEGORIES


def test_unknown_kind_defaults_to_workinsync():
    assert ws.for_kind("banana").kind == "workinsync"


def test_page_type_prefers_type_then_category():
    assert ws.page_type("---\ntype: module\n---\n# x") == "module"
    assert ws.page_type("---\ncategory: concepts\n---\n# x") == "concepts"
    assert ws.page_type("# no frontmatter") == "unknown"


def test_scalar_fields_include_category():
    assert "category" in ws.SCALAR_FRONTMATTER_FIELDS
    # legacy scalars preserved
    assert {"type", "status", "owner"} <= ws.SCALAR_FRONTMATTER_FIELDS


def test_generic_propose_allowlist_has_relationships_topics_entities():
    al = ws.for_kind("generic").propose_allowlist
    assert "relationships/" in al and "topics/" in al and "entities/" in al


def test_workinsync_propose_allowlist_excludes_generic_only_types():
    al = ws.for_kind("workinsync").propose_allowlist
    assert "topics/" not in al and "relationships/" not in al
```

- [ ] **Step 2: Run — FAIL** (module missing):
`/Users/rudrakhare/Desktop/my-wiki/org-wiki/venv/bin/python -m pytest tests/test_schema_parity.py -q`

- [ ] **Step 3: Create `backend/wiki_schema.py`**:

```python
"""Per-schema wiki conventions — the single source of truth.

Conwo (schema_kind='workinsync') keeps its WorkInSync page-types; created agents
(schema_kind='generic') use a domain-neutral set. Scattered hardcoded lists across
the backend route through this module so the two schemas never silently diverge.

Zero dependency on agent_registry: callers pass a schema_kind string (or an object
with a .schema_kind attribute), so tools can import this cheaply and resolve the
active agent's kind via agent_context.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class SchemaConventions:
    kind: str
    categories: tuple[str, ...]
    propose_allowlist: tuple[str, ...]
    page_types: dict[str, dict]  # name -> {"label": str, "color": str}


# Colors mirror the frontend legend palette (frontend/.../graph/graph-page.ts).
WORKINSYNC = SchemaConventions(
    kind="workinsync",
    categories=("modules", "entities", "sources", "concepts", "decisions",
                "cross-module", "configs", "integrations", "persons", "patterns"),
    # Folders chat-propose may create (matches today's _NEW_PATH_ALLOWLIST + entities).
    propose_allowlist=("concepts/", "cross-module/", "decisions/", "answers/",
                       "sources/", "entities/"),
    page_types={
        "module": {"label": "Module", "color": "#3b82f6"},
        "entity": {"label": "Entity", "color": "#22c55e"},
        "concept": {"label": "Concept", "color": "#a855f7"},
        "config": {"label": "Config", "color": "#f59e0b"},
        "decision": {"label": "Decision", "color": "#ef4444"},
        "source": {"label": "Source", "color": "#94a3b8"},
        "cross-module": {"label": "Cross-Module", "color": "#14b8a6"},
        "integration": {"label": "Integration", "color": "#eab308"},
        "person": {"label": "Person", "color": "#ec4899"},
        "pattern": {"label": "Pattern", "color": "#f97316"},
    },
)

GENERIC = SchemaConventions(
    kind="generic",
    categories=("concepts", "relationships", "topics", "entities", "sources", "decisions"),
    propose_allowlist=("concepts/", "relationships/", "topics/", "entities/",
                       "decisions/", "sources/", "answers/"),
    page_types={
        "concept": {"label": "Concept", "color": "#a855f7"},
        "relationships": {"label": "Relationship", "color": "#14b8a6"},
        "topics": {"label": "Topic", "color": "#3b82f6"},
        "entity": {"label": "Entity", "color": "#22c55e"},
        "source": {"label": "Source", "color": "#94a3b8"},
        "decision": {"label": "Decision", "color": "#ef4444"},
    },
)

_BY_KIND = {"workinsync": WORKINSYNC, "generic": GENERIC}

ALL_CATEGORIES: frozenset[str] = frozenset(
    c for s in _BY_KIND.values() for c in s.categories
)

# Frontmatter fields that must stay scalars (never auto-upgraded to lists).
SCALAR_FRONTMATTER_FIELDS: frozenset[str] = frozenset({
    "type", "status", "owner", "module", "last_updated", "ingested",
    "doc_type", "date", "auto_generated", "human_edited", "cluster_id",
    "category", "slug", "title",
})

# Frontmatter fields whose values are page-path references (graph edges).
RELATION_FRONTMATTER_FIELDS: frozenset[str] = frozenset({
    "party_a", "party_b", "sourced_from", "related_concepts", "related_modules",
    "related_topics", "related_decisions", "related_entities", "depends_on",
    "used_by", "related",
})


def for_kind(kind: str | None) -> SchemaConventions:
    return _BY_KIND.get((kind or "").strip().lower(), WORKINSYNC)


def for_agent(agent) -> SchemaConventions:
    return for_kind(getattr(agent, "schema_kind", None))


def page_type(text: str) -> str:
    """Resolve a page's node type from frontmatter: `type:` wins, then `category:`."""
    parts = text.split("---\n", 2)
    if len(parts) < 3:
        return "unknown"
    fm = parts[1]
    for key in ("type", "category"):
        m = re.search(rf"^{key}:\s*(\S+)", fm, re.MULTILINE)
        if m:
            return m.group(1).strip("'\"")
    return "unknown"
```

- [ ] **Step 4: Run — PASS** (8 tests):
`/Users/rudrakhare/Desktop/my-wiki/org-wiki/venv/bin/python -m pytest tests/test_schema_parity.py -q`

- [ ] **Step 5: Commit**
```bash
git add backend/wiki_schema.py tests/test_schema_parity.py
git commit -m "feat(schema): wiki_schema.py — per-schema conventions source of truth"
```

---

## Task 2: Graph node typing via `wiki_schema.page_type` (gap #1)

**Files:**
- Modify: `backend/wiki_graph_api.py` (`_page_type`, ~lines 21-26)
- Test: `tests/test_schema_parity.py` (append)

**Interfaces:**
- Consumes: `wiki_schema.page_type(text) -> str` (Task 1)

- [ ] **Step 1: Append failing test**:

```python
def test_graph_page_type_reads_category(monkeypatch):
    import backend.wiki_graph_api as wg
    assert wg._page_type("---\ncategory: relationships\nslug: a-b\n---\n# x") == "relationships"
    assert wg._page_type("---\ntype: module\n---\n# x") == "module"
```

- [ ] **Step 2: Run — FAIL** (current `_page_type` reads only `type:` → returns "unknown" for the category case).

- [ ] **Step 3: Edit `backend/wiki_graph_api.py`** — replace the body of `_page_type` (keep the function name; other code calls it) so it delegates:

```python
def _page_type(text: str) -> str:
    from backend import wiki_schema
    return wiki_schema.page_type(text)
```
(Remove the now-unused local `re`-based parsing in `_page_type` only; leave the module's other `re` usage, e.g. `_extract_links`, intact.)

- [ ] **Step 4: Run** the new test + the existing graph tests:
`/Users/rudrakhare/Desktop/my-wiki/org-wiki/venv/bin/python -m pytest tests/test_schema_parity.py -k page_type "tests/test_agent_scoping.py::test_wiki_graph_uses_active_agent_dir" "tests/test_agent_scoping.py::test_wiki_graph_edges_from_frontmatter_refs" -q`
Expected: PASS.

- [ ] **Step 5: Commit**
```bash
git add backend/wiki_graph_api.py tests/test_schema_parity.py
git commit -m "fix(graph): node type falls back to frontmatter category (generic schema)"
```

---

## Task 3: Agent-scope `wiki_read_tools` + schema categories (gap #2 + scoping bug)

**Files:**
- Modify: `backend/tools/wiki_read_tools.py`
- Test: `tests/test_schema_parity.py` (append)

**Context:** Today `wiki_check_duplicate`/`wiki_list_pages` resolve against
`WIKI_ROOT = repo root` + `CATEGORY_DIRS["concepts"]="wiki/concepts"`, i.e. ALWAYS
Conwo's wiki — never the active agent's. And `CATEGORY_DIRS` lacks `topics`/`relationships`.
Fix both: resolve `agent_context.get_current_agent().wiki_dir` (like `wiki_tools._wiki_dir`),
and validate categories against `wiki_schema.ALL_CATEGORIES`. Conwo is unaffected: its
`wiki_dir` resolves to the same `wiki/` directory (`_BASE/wiki`) that `WIKI_ROOT/wiki` pointed
to when `CONWO_DATA_DIR` is unset, and is strictly more correct when it is set.

**Interfaces:**
- Consumes: `wiki_schema.ALL_CATEGORIES`, `agent_context.get_current_agent().wiki_dir`

- [ ] **Step 1: Read** the whole file `backend/tools/wiki_read_tools.py` (it is small) — note `CATEGORY_DIRS` (lines 15-26), `WIKI_ROOT` (line 13), `_wiki_list_pages_handler` (55-76), `_wiki_check_duplicate_handler` (109-124).

- [ ] **Step 2: Find existing tests that patch `WIKI_ROOT`** so you can update them:
`grep -rn "wiki_read_tools" tests/ | grep -i "WIKI_ROOT\|list_pages\|check_duplicate"`
Read those tests; they likely set `wiki_read_tools.WIKI_ROOT = tmp`. After this change the handlers use the active agent's `wiki_dir`, so those tests must instead point the active agent at tmp (set `agent_context` to a `SimpleNamespace(wiki_dir=tmp_path/'wiki', ...)` or monkeypatch a `_wiki_dir`). Update them in this task so they stay green.

- [ ] **Step 3: Append failing test** to `tests/test_schema_parity.py`:

```python
def test_check_duplicate_is_agent_scoped_and_knows_generic_categories(tmp_path, monkeypatch):
    import types
    from backend import agent_context
    import backend.tools.wiki_read_tools as rt

    wiki = tmp_path / "wiki"
    (wiki / "relationships").mkdir(parents=True)
    (wiki / "relationships" / "a-b.md").write_text("---\ncategory: relationships\n---\n# x")

    fake = types.SimpleNamespace(id="legal", schema_kind="generic", wiki_dir=wiki)
    monkeypatch.setattr(agent_context, "get_current_agent", lambda: fake, raising=False)

    # generic category is accepted (not 'unknown_category') AND scoped to this agent's dir
    hit = rt._wiki_check_duplicate_handler({"slug": "a-b", "category": "relationships"})
    assert hit.get("exists") is True
    miss = rt._wiki_check_duplicate_handler({"slug": "nope", "category": "topics"})
    assert miss.get("exists") is False and "code" not in miss
```

- [ ] **Step 4: Run — FAIL** (today: `unknown_category` for relationships/topics, and wrong dir).

- [ ] **Step 5: Edit `backend/tools/wiki_read_tools.py`**:
  - Add an agent-scoped dir helper near the top (after imports):
    ```python
    def _wiki_dir():
        from backend import agent_context
        return agent_context.get_current_agent().wiki_dir
    ```
  - In `_wiki_check_duplicate_handler`: replace the category check + path build:
    ```python
    from backend import wiki_schema
    if category not in wiki_schema.ALL_CATEGORIES:
        return {"error": f"Unknown category: {category!r}", "code": "unknown_category"}
    wiki_dir = _wiki_dir()
    candidate = wiki_dir / category / f"{slug}.md"
    exists = candidate.exists()
    return {"exists": exists,
            "path": str(candidate.relative_to(wiki_dir)) if exists else None}
    ```
  - In `_wiki_list_pages_handler`: validate `category` against `wiki_schema.ALL_CATEGORIES` (not `CATEGORY_DIRS`), and list from `_wiki_dir()` (its `*.md` files), filtering by `category` prefix when given. Preserve the existing return shape (list of page paths/objects — match what the current code returns; read it in Step 1 and keep the same structure, only changing the root dir + category validation).
  - Keep `WIKI_ROOT` defined (harmless) if other code imports it, but stop using it for these two handlers. (Grep `grep -rn "WIKI_ROOT" backend/` — if nothing else uses it, you may remove it; if tests import it, keep it.)

- [ ] **Step 6: Run** the new test + the read-tools tests you updated + the ingest tests:
`/Users/rudrakhare/Desktop/my-wiki/org-wiki/venv/bin/python -m pytest tests/test_schema_parity.py -k check_duplicate tests/test_ingest_api.py tests/test_ingest_service.py -q`
Expected: PASS (the known `test_plan_returns_409_when_locked` may still fail — that is pre-existing).

- [ ] **Step 7: Commit**
```bash
git add backend/tools/wiki_read_tools.py tests/
git commit -m "fix(wiki): check_duplicate/list_pages agent-scoped + schema-aware categories"
```

---

## Task 4: Chat-propose allowlist per active agent's schema (gap #3)

**Files:**
- Modify: `backend/tools/wiki_propose_tools.py` (line 49 `_NEW_PATH_ALLOWLIST`, line ~431 check)
- Test: `tests/test_schema_parity.py` (append)

**Interfaces:**
- Consumes: `wiki_schema.for_agent(...).propose_allowlist`, `agent_context.get_current_agent()`

- [ ] **Step 1: Append failing test**:

```python
def test_propose_new_allows_generic_paths(monkeypatch):
    import types
    from backend import agent_context
    import backend.tools.wiki_propose_tools as pt
    fake = types.SimpleNamespace(id="legal", schema_kind="generic", wiki_dir=None)
    monkeypatch.setattr(agent_context, "get_current_agent", lambda: fake, raising=False)
    # The allowlist resolved for a generic agent must include relationships/ + topics/.
    al = pt._allowed_new_prefixes()
    assert "relationships/" in al and "topics/" in al
```

- [ ] **Step 2: Run — FAIL** (`_allowed_new_prefixes` doesn't exist; allowlist is a static tuple).

- [ ] **Step 3: Edit `backend/tools/wiki_propose_tools.py`**:
  - Replace the module-level `_NEW_PATH_ALLOWLIST = (...)` with a resolver:
    ```python
    def _allowed_new_prefixes() -> tuple[str, ...]:
        from backend import wiki_schema, agent_context
        return wiki_schema.for_agent(agent_context.get_current_agent()).propose_allowlist
    ```
  - At the check site (~line 431), replace usage:
    ```python
    allow = _allowed_new_prefixes()
    if not any(page_path.startswith(p) for p in allow):
        return {... f"page_path must start with one of: {', '.join(allow)}. " ...}
    ```
    Keep the rest of the error payload identical.

- [ ] **Step 4: Run** the new test + existing propose tests:
`/Users/rudrakhare/Desktop/my-wiki/org-wiki/venv/bin/python -m pytest tests/test_schema_parity.py -k propose tests/test_agent_scoping.py -k propose -q`
Expected: PASS. (If an existing propose test asserted the old conwo allowlist via a conwo/none agent context, it still passes because `for_agent(None/workinsync)` returns the workinsync allowlist which is a superset of the old tuple + `entities/`. If a test asserts `entities/` is rejected, update it — `entities/` is now allowed for workinsync too, which is correct.)

- [ ] **Step 5: Commit**
```bash
git add backend/tools/wiki_propose_tools.py tests/test_schema_parity.py
git commit -m "fix(propose): new-page allowlist resolves per active agent schema"
```

---

## Task 5: `_SCALAR_FIELDS` from `wiki_schema` (gap #6)

**Files:**
- Modify: `backend/tools/wiki_write_tools.py` (`_SCALAR_FIELDS`, ~lines 25-26)
- Test: `tests/test_schema_parity.py` (append)

**Interfaces:**
- Consumes: `wiki_schema.SCALAR_FRONTMATTER_FIELDS`

- [ ] **Step 1: Append failing test**:

```python
def test_write_tools_scalar_fields_include_category():
    import backend.tools.wiki_write_tools as wt
    assert "category" in wt._SCALAR_FIELDS
    assert {"type", "status", "owner"} <= wt._SCALAR_FIELDS
```

- [ ] **Step 2: Run — FAIL** (`category` not in `_SCALAR_FIELDS`).

- [ ] **Step 3: Edit `backend/tools/wiki_write_tools.py`** — replace the hardcoded `_SCALAR_FIELDS = {...}` with a sourced value (keep the name `_SCALAR_FIELDS` since the file references it):
```python
from backend import wiki_schema
_SCALAR_FIELDS = set(wiki_schema.SCALAR_FRONTMATTER_FIELDS)
```
Place the import with the other top-level imports; keep `_SCALAR_FIELDS` defined at module scope where it is now.

- [ ] **Step 4: Run** the new test + write-tool/append tests:
`/Users/rudrakhare/Desktop/my-wiki/org-wiki/venv/bin/python -m pytest tests/test_schema_parity.py -k scalar tests/ -k "write or append or frontmatter" -q`
Expected: PASS.

- [ ] **Step 5: Commit**
```bash
git add backend/tools/wiki_write_tools.py tests/test_schema_parity.py
git commit -m "fix(wiki): scalar frontmatter fields sourced from wiki_schema (+category)"
```

---

## Task 6: De-WorkInSync the system-prompt header (gap #4)

**Files:**
- Modify: `backend/system_prompt.py` (line ~99)
- Test: `tests/test_schema_parity.py` (append)

**Context:** Line 99 currently: `f"# {spec.display_name} Backend — WorkInSync Knowledge Query System\n\n"`. Conwo should keep WorkInSync framing; generic agents must not claim to be a WorkInSync system.

**Interfaces:**
- Consumes: `agent_registry.get(...)` (existing), `spec.schema_kind`

- [ ] **Step 1: Append failing test**:

```python
def test_system_prompt_no_workinsync_for_generic():
    from backend import system_prompt
    info = system_prompt.load_system_prompt("infosec")   # generic, seeded
    assert "WorkInSync" not in info
    conwo = system_prompt.load_system_prompt("conwo")     # workinsync
    assert "WorkInSync" in conwo
```

- [ ] **Step 2: Run — FAIL** (every agent gets "WorkInSync" today).

- [ ] **Step 3: Edit `backend/system_prompt.py`** — read around line 99 to see how `spec` is obtained. Replace the hardcoded header line with a schema-aware one:
```python
_product = "WorkInSync " if getattr(spec, "schema_kind", "workinsync") == "workinsync" else ""
header = f"# {spec.display_name} Backend — {_product}Knowledge Query System\n\n"
```
Use `header` where the literal was used. Do not change any other prompt content.

- [ ] **Step 4: Run** the new test + existing system-prompt tests:
`/Users/rudrakhare/Desktop/my-wiki/org-wiki/venv/bin/python -m pytest tests/test_schema_parity.py -k system_prompt "tests/test_agent_scoping.py::test_system_prompt_uses_agent_identity" -q`
Expected: PASS.

- [ ] **Step 5: Commit**
```bash
git add backend/system_prompt.py tests/test_schema_parity.py
git commit -m "fix(prompt): WorkInSync header only for workinsync-schema agents"
```

---

## Task 7: Schema-aware ingest prompt prose (gap #5)

**Files:**
- Modify: `backend/ingest_api.py` (`_render_plan_prompt` ~61-117, `_render_execute_prompt` ~120-195)
- Test: `tests/test_schema_parity.py` (append)

**Context:** The JSON structure is already schema-split (`_wiki_structure`/`_classification_order`/`_classification_kinds`/`_cross_ref_example`). The remaining WorkInSync-biased PROSE: "SLUG RULES: ... match the module folder name", "BIDIRECTIONALITY: if module A depends_on B...", "CLASSIFICATION ORDER" mentions of modules/config, "Folder context — raw/modules/<slug>/". Make these schema-aware.

**Interfaces:**
- Consumes: `agent.schema_kind`

- [ ] **Step 1: Append failing test**:

```python
def test_ingest_plan_prose_is_generic_for_generic_agent():
    import backend.ingest_api as ing
    from backend import agent_registry
    g = ing._render_plan_prompt(agent_registry.get("infosec"))
    c = ing._render_plan_prompt(agent_registry.get("conwo"))
    # Generic prompt must not push WorkInSync-only narrative.
    assert "BIDIRECTIONALITY" not in g and "module folder" not in g and "raw/modules/" not in g
    # Conwo keeps it.
    assert "BIDIRECTIONALITY" in c
```

- [ ] **Step 2: Run — FAIL** (both share the same prose today).

- [ ] **Step 3: Edit `backend/ingest_api.py`** — add a helper that returns schema-specific prose blocks, and interpolate them into `_render_plan_prompt` (replace the literal SLUG RULES / BIDIRECTIONALITY / folder-context lines):

```python
def _schema_guidance(agent) -> str:
    if agent.schema_kind == "workinsync":
        return (
            "SLUG RULES: lowercase-hyphenated, match the module folder name.\n"
            "BIDIRECTIONALITY: if module A depends_on B, then B must have used_by A. "
            "Flag any asymmetry as a warning in your plan.\n"
            "Folder context — raw/modules/<slug>/ tells you the module."
        )
    return (
        "SLUG RULES: lowercase-hyphenated, derived from the concept/topic name.\n"
        "RELATIONSHIPS: when two concepts relate, create a relationships/<a>-<b>.md page "
        "whose frontmatter names party_a and party_b (page paths); cite the source via "
        "sourced_from. Do not invent module/config structure.\n"
        "Classify by concept, entity, topic, relationship, decision, or source."
    )
```
Replace the corresponding literal lines in `_render_plan_prompt` with `{_schema_guidance(agent)}`. Leave `_render_execute_prompt` prose as-is IF it contains no WorkInSync-only narrative (it maps op types → tools); if it references modules/bidirectionality, apply the same `{_schema_guidance(agent)}` swap there. Keep all f-string braces (`{{`/`}}`) intact.

- [ ] **Step 4: Run** the new test + the existing ingest-schema test + ingest suite:
`/Users/rudrakhare/Desktop/my-wiki/org-wiki/venv/bin/python -m pytest tests/test_schema_parity.py -k prose "tests/test_agents_table.py::test_ingest_schema_is_generic_for_non_conwo" tests/test_ingest_service.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**
```bash
git add backend/ingest_api.py tests/test_schema_parity.py
git commit -m "fix(ingest): schema-aware planner prose (generic agents)"
```

---

## Task 8: Schema-appropriate `index.md` for created agents (gap #10)

**Files:**
- Modify: `backend/agent_provisioning.py` (`create_agent`, the `index.md` write)
- Modify: `backend/ingest_api.py` (`_run_ingest_job`, after `wiki_retriever.build_index(aid)`)
- Test: `tests/test_agent_provisioning.py` (append)

**Context:** `create_agent` already writes a minimal `index.md`. Make it list the schema's
categories so the homepage isn't bare, and refresh a page count after ingest.

**Interfaces:**
- Consumes: `wiki_schema.for_kind(spec.schema_kind).categories`

- [ ] **Step 1: Append failing test** to `tests/test_agent_provisioning.py` (reuse the existing `clean_db`, `no_extra_agents`, `tmp_path`, `monkeypatch` fixtures already in that file):

```python
def test_created_agent_index_lists_schema_categories(clean_db, no_extra_agents, tmp_path, monkeypatch):
    from backend import agent_provisioning as ap, agent_registry, config
    monkeypatch.setattr(config, "_BASE", tmp_path, raising=False)
    monkeypatch.setattr(agent_registry, "_BASE", tmp_path, raising=False)
    ap.create_agent("Legal", created_by="a")
    idx = (tmp_path / "agents" / "legal" / "wiki" / "index.md").read_text()
    assert "Concepts" in idx and "Relationships" in idx and "Topics" in idx
```

- [ ] **Step 2: Run — FAIL** (current stub doesn't list categories).

- [ ] **Step 3: Edit `backend/agent_provisioning.py`** — in `create_agent`, replace the `index.md` write with a schema-aware stub:
```python
from backend import wiki_schema
_cats = wiki_schema.for_kind("generic").categories  # created agents are generic
_sections = "\n".join(f"- **{c.replace('-', ' ').title()}** — `{c}/`" for c in _cats)
(wiki_abs / "index.md").write_text(
    f"# {name} Wiki Index\n_Total pages: 0_\n\n"
    f"Empty knowledge base — ingest documents to populate it. Page categories:\n\n"
    f"{_sections}\n",
    encoding="utf-8")
```

- [ ] **Step 4: Edit `backend/ingest_api.py`** — in `_run_ingest_job`, right after the existing `wiki_retriever.build_index(aid)` success path, refresh the page count in `index.md` (best-effort, never fail the job):
```python
try:
    wiki_dir = agent.wiki_dir
    idx = wiki_dir / "index.md"
    n = sum(1 for _ in wiki_dir.rglob("*.md")) - 1  # exclude index.md itself
    if idx.exists():
        body = idx.read_text(encoding="utf-8")
        import re as _re
        body = _re.sub(r"_Total pages: \d+_", f"_Total pages: {max(0, n)}_", body, count=1)
        idx.write_text(body, encoding="utf-8")
except Exception:
    pass
```

- [ ] **Step 5: Run**:
`/Users/rudrakhare/Desktop/my-wiki/org-wiki/venv/bin/python -m pytest tests/test_agent_provisioning.py -q`
Expected: PASS (all provisioning tests).

- [ ] **Step 6: Commit**
```bash
git add backend/agent_provisioning.py backend/ingest_api.py tests/test_agent_provisioning.py
git commit -m "feat(agents): schema-aware index.md stub + page-count refresh on ingest"
```

---

## Task 9: Frontend cosmetics (gaps #7, #8, #9)

**Files:**
- Modify: `frontend/src/app/features/graph/graph-page.ts` (`TYPE_COLORS`, ~16-27)
- Modify: `frontend/src/app/shared/source-drawer/source-drawer.ts` (PMS section, ~56-64)
- Modify: `frontend/src/app/features/ingest/plan-step.ts` (`hasExistingModule()`)

**Context:** Frontend gate is `npx ng build` (run from `<worktree>/frontend`). No unit tests (Node-25 env). Read each file before editing.

- [ ] **Step 1: Graph legend (#7)** — in `graph-page.ts`, read the `TYPE_COLORS` map and add the generic page types so they color (matching `wiki_schema.GENERIC.page_types` colors):
```typescript
  relationships: '#14b8a6',
  topics: '#3b82f6',
```
Add these keys to the existing `TYPE_COLORS` object (keep all existing entries). If the legend is rendered from a separate list, add "Relationship" and "Topic" entries there too so the legend shows them.

- [ ] **Step 2: Source drawer (#8)** — in `source-drawer.ts`, read how the "PMS configs" section is rendered (~56-64) and how the active agent is available (likely `AgentService`). Wrap the PMS section in a guard so it renders only when the active agent has PMS. If `AgentService` exposes the active agent, use `agentSvc.active()?.has_pms`; otherwise inject `AgentService` and add a `hasPms()` accessor. Render the section only when true.

- [ ] **Step 3: Ingest plan-step (#9)** — in `plan-step.ts`, read `hasExistingModule()`. Generalize it from `o.path.startsWith('wiki/modules/')` to "the operation targets a page that already exists" — i.e. check the operation `type` is an edit/append/update (not `create`), OR (if the component has the existing-pages set) that the path is in it. The minimal robust change: rename intent to `isEditingExisting(o)` returning `o.type !== 'create'`, and update the template usage. Keep the name if other code references it; just change the predicate to not be `modules/`-specific.

- [ ] **Step 4: Verify build**:
```bash
cd /Users/rudrakhare/Desktop/my-wiki/org-wiki/.claude/worktrees/hopeful-roentgen-cda2f4/frontend
npx ng build   # must succeed
```

- [ ] **Step 5: Commit**
```bash
cd /Users/rudrakhare/Desktop/my-wiki/org-wiki/.claude/worktrees/hopeful-roentgen-cda2f4
git add frontend/src/app/features/graph/graph-page.ts frontend/src/app/shared/source-drawer/source-drawer.ts frontend/src/app/features/ingest/plan-step.ts
git commit -m "fix(fe): graph legend topics/relationships; gate PMS drawer; generic plan-step"
```

---

## Task 10: Full verification

**Files:** none (verification + any fixups).

- [ ] **Step 1: Full backend suite**:
`/Users/rudrakhare/Desktop/my-wiki/org-wiki/venv/bin/python -m pytest tests/ -q`
Expected: only the 5 known pre-existing failures; 0 new. `tests/test_schema_parity.py` all green.

- [ ] **Step 2: Frontend build**:
`cd <worktree>/frontend && npx ng build` → clean.

- [ ] **Step 3: Conwo-unchanged spot check**:
`/Users/rudrakhare/Desktop/my-wiki/org-wiki/venv/bin/python -c "from backend import wiki_schema as ws; assert ws.for_kind('workinsync').categories[0]=='modules'; print('conwo categories ok')"`
And confirm no `[[wikilink]]`/Conwo graph regression: `pytest tests/test_agent_scoping.py -q`.

- [ ] **Step 4: Commit any fixups; done.**

---

## Milestone exit criteria
- `backend/wiki_schema.py` is the single source of truth; graph typing, read-tool categories+scoping, propose allowlist, scalar fields, system-prompt header, and ingest prose all route through it.
- A created agent: graph nodes are typed/colored/connected; `wiki_check_duplicate`/`wiki_list_pages` hit its OWN wiki and accept `topics`/`relationships`; it can chat-propose those types; its system prompt carries no "WorkInSync"; its planner prose is generic; its `index.md` lists categories + a live page count; the source drawer hides the empty PMS section.
- Conwo unchanged; full backend suite green (5 known failures only); `npx ng build` clean; `tests/test_schema_parity.py` green.
