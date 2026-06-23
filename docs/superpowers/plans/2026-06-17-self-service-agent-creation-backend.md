# Self-Service Agent Creation — Backend Plan (Phases 1–3)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Let an admin create a complete, Conwo-grade wiki agent at runtime by name — backend foundation: a DB-backed agent registry, a generic ingest schema, and a provisioning service + admin endpoints (`POST/PATCH/DELETE /admin/agents`), verifiable by `curl`.

**Architecture:** Move agent definitions from `config/agents.toml` to a Postgres `agents` table (Conwo/Infosec seeded). `agent_registry` reads the DB behind a short-TTL cache (multi-replica safe). A provisioning service atomically creates an agent's row + PVC dirs + templated CLAUDE.md, auto-assigns an accent, and generates an identity via one Anthropic call (validated, with a deterministic fallback). All of Conwo's orchestrator/tools/ingest/graph is already agent-parameterized and inherited automatically.

**Tech Stack:** Python 3.11+, FastAPI, psycopg3 pool, pytest (isolated `wis_conwo_test` DB), Anthropic SDK (`claude-sonnet-4-6`).

**Companion spec:** `docs/superpowers/specs/2026-06-17-self-service-agent-creation-design.md`
**Scope note:** Frontend (Create-Agent UI + per-agent accent theming) is **Plan 2**, after this milestone.

---

## Conventions for every task
- Run from worktree root. Tests: `/Users/rudrakhare/Desktop/my-wiki/org-wiki/venv/bin/python -m pytest <path> -v` (auto-uses `wis_conwo_test`).
- DB tests take the `clean_db` fixture (`tests/conftest.py`). Admin-endpoint tests stub auth via `app.dependency_overrides[_get_user]`.
- The full suite has ~5 known pre-existing failures (PMS creds, `.env` reload, ingest lock) — not regressions.
- **Conwo + Infosec must keep working identically** — regression-check each phase.
- Commit after every task. Never write `.py` while a `--reload` backend runs.

---

## File Structure
- **New:** `migrations/postgres/100_agents.sql`, `backend/agent_provisioning.py`, `tests/test_agents_table.py`, `tests/test_agent_provisioning.py`, `tests/test_admin_agents_api.py`.
- **Modify:** `backend/agent_registry.py` (read DB + cache), `backend/ingest_api.py` (schema split), `backend/api.py` (3 admin endpoints), `backend/conversation_store.py`/`backend/trace_store.py` (delete-cleanup helpers).

---

## PHASE 1 — DB-backed registry

### Task 1: `agents` table + seed Conwo/Infosec

**Files:** Create `migrations/postgres/100_agents.sql`, `tests/test_agents_table.py`

- [ ] **Step 1: Write the migration** `migrations/postgres/100_agents.sql`:

```sql
-- 100_agents.sql — dynamic agent registry. Idempotent. Seeds the two built-ins.
CREATE TABLE IF NOT EXISTS agents (
    id           TEXT PRIMARY KEY,           -- slug
    display_name TEXT NOT NULL,
    identity     TEXT NOT NULL DEFAULT '',
    accent       TEXT NOT NULL DEFAULT '#a78bfa',
    theme_base   TEXT NOT NULL DEFAULT 'dark',   -- 'light' | 'dark'
    schema_kind  TEXT NOT NULL DEFAULT 'generic', -- 'generic' | 'workinsync'
    modes        TEXT[] NOT NULL DEFAULT '{api}',
    tools        TEXT[] NOT NULL DEFAULT '{wiki_search,wiki_read_page,wiki_grep,wiki_list_pages,wiki_check_duplicate,wiki_propose_new,wiki_propose_edit,wiki_propose_append,wiki_propose_multi_edit,feedback_record}',
    has_jira     BOOLEAN NOT NULL DEFAULT false,
    has_pms      BOOLEAN NOT NULL DEFAULT false,
    wiki_dir     TEXT NOT NULL,
    raw_dir      TEXT NOT NULL,
    claude_md    TEXT NOT NULL,
    prompt_sections INT[] NOT NULL DEFAULT '{}',
    status       TEXT NOT NULL DEFAULT 'active',  -- 'active' | 'archived'
    created_by   TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Seed the two built-ins (idempotent).
INSERT INTO agents (id, display_name, identity, accent, theme_base, schema_kind, modes, tools,
                    has_jira, has_pms, wiki_dir, raw_dir, claude_md, prompt_sections, created_by)
VALUES
  ('conwo', 'Conwo',
   'You are Conwo, an AI assistant that answers product, config, and debugging questions about WorkInSync.',
   '#1e293b', 'light', 'workinsync', '{api,agent}', '{*}',
   true, true, 'wiki', 'raw', 'CLAUDE.md', '{5,9,12}', 'system'),
  ('infosec', 'Infosec',
   'You are the Infosec assistant, answering information-security questions from the organization''s security knowledge base.',
   '#a78bfa', 'dark', 'generic', '{api}',
   '{wiki_search,wiki_read_page,wiki_grep,wiki_list_pages,wiki_check_duplicate,wiki_propose_new,wiki_propose_edit,wiki_propose_append,wiki_propose_multi_edit,feedback_record}',
   false, false, 'agents/infosec/wiki', 'agents/infosec/raw', 'agents/infosec/CLAUDE.md', '{}', 'system')
ON CONFLICT (id) DO NOTHING;
```

- [ ] **Step 2: Write failing test** `tests/test_agents_table.py`:

```python
def test_agents_table_seeded(clean_db):
    from backend import db
    with db.connection() as c:
        rows = {r["id"]: r for r in c.execute(
            "SELECT id, display_name, has_jira, schema_kind, theme_base FROM agents").fetchall()}
    assert {"conwo", "infosec"} <= set(rows)
    assert rows["conwo"]["has_jira"] is True
    assert rows["conwo"]["schema_kind"] == "workinsync"
    assert rows["infosec"]["has_jira"] is False
    assert rows["infosec"]["schema_kind"] == "generic"
    assert rows["infosec"]["theme_base"] == "dark"
```

- [ ] **Step 3: Run — FAIL** (no `agents` table) until `init_db()` applies 100. If the pre-existing `wis_conwo_test` predates it, the session fixture's `init_db()` applies new `*.sql` on the next run.
Run: `/Users/rudrakhare/Desktop/my-wiki/org-wiki/venv/bin/python -m pytest tests/test_agents_table.py -v`

- [ ] **Step 4: Run — PASS** after migration applies.

- [ ] **Step 5: Commit**
```bash
git add migrations/postgres/100_agents.sql tests/test_agents_table.py
git commit -m "feat(agents): agents table + seed conwo/infosec rows"
```

---

### Task 2: `agent_registry` reads the DB (with new AgentSpec fields)

**Files:** Modify `backend/agent_registry.py`; Test: `tests/test_agent_registry.py` (extend) + `tests/test_agents_table.py`

- [ ] **Step 1: Append failing test** to `tests/test_agents_table.py`:

```python
def test_registry_loads_from_db(clean_db):
    from backend import agent_registry
    agent_registry.invalidate_cache()
    ids = {a.id for a in agent_registry.all()}
    assert {"conwo", "infosec"} <= ids
    conwo = agent_registry.get("conwo")
    assert conwo.accent == "#1e293b" and conwo.theme_base == "light"
    assert conwo.schema_kind == "workinsync" and conwo.has_jira is True
    info = agent_registry.get("infosec")
    assert info.accent == "#a78bfa" and info.theme_base == "dark"
    assert info.schema_kind == "generic"
    assert agent_registry.get("nope").id == "conwo"   # fallback preserved
```

- [ ] **Step 2: Run — FAIL** (`AgentSpec` has no `accent`; registry reads TOML).

- [ ] **Step 3: Refactor `backend/agent_registry.py`** — add fields + read DB:

```python
from __future__ import annotations
import time
from dataclasses import dataclass
from pathlib import Path
from threading import RLock
from backend.config import _BASE

DEFAULT_AGENT_ID = "conwo"
_CACHE_TTL_SECONDS = 30  # multi-replica: a create elsewhere is visible within this window


@dataclass(frozen=True)
class AgentSpec:
    id: str
    display_name: str
    identity: str
    accent: str
    theme_base: str          # 'light' | 'dark'
    schema_kind: str         # 'generic' | 'workinsync'
    wiki_dir: Path
    raw_dir: Path
    claude_md: Path
    prompt_sections: tuple[int, ...]
    tools: tuple[str, ...]
    modes: tuple[str, ...]
    has_jira: bool
    has_pms: bool
    status: str = "active"
    description: str = ""    # kept for back-compat with any caller

    def tool_allowed(self, name: str) -> bool:
        return "*" in self.tools or name in self.tools

    def mode_allowed(self, mode: str) -> bool:
        return mode in self.modes


def _resolve(p: str) -> Path:
    path = Path(p)
    return path if path.is_absolute() else (_BASE / path)


# Built-in conwo fallback if the agents table is ever empty/unreachable — the app
# must always boot with at least conwo.
_CONWO_FALLBACK = AgentSpec(
    id="conwo", display_name="Conwo",
    identity="You are Conwo, an AI assistant that answers product, config, and debugging questions about WorkInSync.",
    accent="#1e293b", theme_base="light", schema_kind="workinsync",
    wiki_dir=_resolve("wiki"), raw_dir=_resolve("raw"), claude_md=_resolve("CLAUDE.md"),
    prompt_sections=(5, 9, 12), tools=("*",), modes=("api", "agent"),
    has_jira=True, has_pms=True,
)

_lock = RLock()
_cache: dict[str, AgentSpec] | None = None
_cache_at: float = 0.0


def _row_to_spec(r) -> AgentSpec:
    return AgentSpec(
        id=r["id"], display_name=r["display_name"], identity=r["identity"],
        accent=r["accent"], theme_base=r["theme_base"], schema_kind=r["schema_kind"],
        wiki_dir=_resolve(r["wiki_dir"]), raw_dir=_resolve(r["raw_dir"]),
        claude_md=_resolve(r["claude_md"]),
        prompt_sections=tuple(r["prompt_sections"] or ()),
        tools=tuple(r["tools"] or ()), modes=tuple(r["modes"] or ("api",)),
        has_jira=bool(r["has_jira"]), has_pms=bool(r["has_pms"]),
        status=r["status"],
    )


def _load() -> dict[str, AgentSpec]:
    global _cache, _cache_at
    with _lock:
        if _cache is not None and (time.monotonic() - _cache_at) < _CACHE_TTL_SECONDS:
            return _cache
        try:
            from backend import db
            with db.connection() as c:
                rows = c.execute(
                    "SELECT * FROM agents WHERE status = 'active'").fetchall()
            specs = {r["id"]: _row_to_spec(r) for r in rows}
        except Exception:
            specs = {}
        if DEFAULT_AGENT_ID not in specs:
            specs[DEFAULT_AGENT_ID] = _CONWO_FALLBACK
        _cache = specs
        _cache_at = time.monotonic()
        return _cache


def all() -> list[AgentSpec]:
    return list(_load().values())


def get(agent_id: str | None) -> AgentSpec:
    agents = _load()
    return agents.get(agent_id or "", agents[DEFAULT_AGENT_ID])


def default() -> AgentSpec:
    return _load()[DEFAULT_AGENT_ID]


def invalidate_cache() -> None:
    global _cache, _cache_at
    with _lock:
        _cache = None
        _cache_at = 0.0
```

> Note: existing tests in `tests/test_agent_registry.py` assert the OLD shape (e.g. `wiki_dir.parts[-3:]`, `tool_allowed`, `mode_allowed`, fallback). Those assertions still hold (DB seed mirrors the TOML). If any test referenced `description` or `prompt_sections` defaults, confirm they pass; adjust the test only if it asserted a TOML-specific detail. Delete `config/agents.toml` and its `tomllib` import.

- [ ] **Step 4: Run** the new test + existing registry tests:
`/Users/rudrakhare/Desktop/my-wiki/org-wiki/venv/bin/python -m pytest tests/test_agents_table.py tests/test_agent_registry.py tests/test_agent_context.py -q`
Expected: PASS (fix any old TOML-specific assertion to match the DB seed).

- [ ] **Step 5: Broad regression** — `/Users/rudrakhare/Desktop/my-wiki/org-wiki/venv/bin/python -m pytest tests/ -q` (only the ~5 known failures).

- [ ] **Step 6: Commit**
```bash
git add backend/agent_registry.py tests/ config/agents.toml
git commit -m "feat(agents): registry reads from DB with short-TTL cache (replaces TOML)"
```

---

## PHASE 2 — generic ingest schema

### Task 3: Split ingest schema by `schema_kind`

**Files:** Modify `backend/ingest_api.py`; Test: `tests/test_agents_table.py` (append) or `tests/test_ingest_api.py`

- [ ] **Step 1: Append failing test**:

```python
def test_ingest_schema_is_generic_for_non_conwo():
    import backend.ingest_api as ing
    from backend import agent_registry
    conwo_prompt = ing._render_plan_prompt(agent_registry.get("conwo"))
    info_prompt = ing._render_plan_prompt(agent_registry.get("infosec"))
    # Conwo keeps the WorkInSync schema; generic agents must NOT mention modules/configs.
    assert "wiki/modules/" in conwo_prompt and "wiki/configs/" in conwo_prompt
    assert "wiki/modules/" not in info_prompt and "wiki/configs/" not in info_prompt
    assert "wiki/concepts/" in info_prompt and "wiki/sources/" in info_prompt
```

- [ ] **Step 2: Run — FAIL** (today both render the same hardcoded WorkInSync schema).

- [ ] **Step 3: Edit `backend/ingest_api.py`** — extract the schema block into two constants and pick by `agent.schema_kind`:

```python
_WIKI_STRUCTURE_WORKINSYNC = """\
WIKI STRUCTURE:
- wiki/sources/<slug>.md       — every ingested doc gets one
- wiki/modules/<slug>.md       — product modules
- wiki/entities/<slug>.md      — data models / domain objects
- wiki/cross-module/<a>-<b>.md — when two modules connect
- wiki/decisions/<date>-<title>.md — architecture decisions
- wiki/configs/<slug>.md       — PMS config tables"""

_WIKI_STRUCTURE_GENERIC = """\
WIKI STRUCTURE:
- wiki/sources/<slug>.md        — every ingested doc gets one
- wiki/concepts/<slug>.md       — a concept, term, or topic
- wiki/entities/<slug>.md       — data models / domain objects
- wiki/relationships/<a>-<b>.md — when two topics connect
- wiki/decisions/<date>-<title>.md — decisions/rationale
- wiki/topics/<slug>.md         — a subject area that groups concepts"""

def _wiki_structure(agent) -> str:
    return _WIKI_STRUCTURE_WORKINSYNC if agent.schema_kind == "workinsync" else _WIKI_STRUCTURE_GENERIC
```

Then in `_render_plan_prompt(agent)`, replace the inline `WIKI STRUCTURE:` block with `{_wiki_structure(agent)}`, and adjust the CLASSIFICATION list's `config|...` enum: keep `module|...config...` for workinsync, use `concept|entity|topic|source|decision|relationship` for generic (interpolate a `_classification_kinds(agent)` string the same way). `_render_execute_prompt` is schema-agnostic (it just maps op types → tools) — no change.

- [ ] **Step 4: Run** the new test + ingest regression:
`/Users/rudrakhare/Desktop/my-wiki/org-wiki/venv/bin/python -m pytest tests/test_agents_table.py -k ingest_schema tests/test_ingest_api.py tests/test_ingest_service.py -q`
Expected: PASS (conwo path unchanged; generic for others).

- [ ] **Step 5: Commit**
```bash
git add backend/ingest_api.py tests/test_agents_table.py
git commit -m "feat(ingest): generic Conwo-methodology schema for non-workinsync agents"
```

---

## PHASE 3 — provisioning service + admin endpoints

### Task 4: Accent + slug + identity helpers (pure/unit-testable)

**Files:** Create `backend/agent_provisioning.py`; Test: `tests/test_agent_provisioning.py`

- [ ] **Step 1: Write failing test** `tests/test_agent_provisioning.py`:

```python
from backend import agent_provisioning as ap


def test_slugify():
    assert ap.slugify("Legal") == "legal"
    assert ap.slugify("HR Policies & Ops") == "hr-policies-ops"


def test_accent_is_deterministic_hex():
    a1 = ap.accent_for_slug("legal")
    a2 = ap.accent_for_slug("legal")
    assert a1 == a2 and a1.startswith("#") and len(a1) == 7
    assert ap.accent_for_slug("finance") != a1   # different slug → different hue


def test_identity_fallback_when_no_llm(monkeypatch):
    # Force the LLM path to fail → deterministic template fallback.
    monkeypatch.setattr(ap, "_llm_identity", lambda name: None)
    out = ap.generate_identity("Legal")
    assert "Legal" in out and "knowledge base" in out.lower()
```

- [ ] **Step 2: Run — FAIL** (module missing).

- [ ] **Step 3: Write `backend/agent_provisioning.py`** (helpers; provisioning added next task):

```python
"""Runtime agent provisioning — create/rename/archive agents from the UI."""
from __future__ import annotations

import hashlib
import re
import colorsys

RESERVED_SLUGS = {"conwo", "infosec", "admin", "api", "agents", "health", "auth",
                  "query", "search", "wiki", "status", "traces", "dashboard", "ingest"}


def slugify(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (name or "").strip().lower()).strip("-")
    return s


def accent_for_slug(slug: str) -> str:
    """Deterministic, pleasant hex from the slug (stable hue, fixed S/L for dark bg)."""
    h = int(hashlib.sha1(slug.encode()).hexdigest(), 16)
    hue = (h % 360) / 360.0
    r, g, b = colorsys.hls_to_rgb(hue, 0.68, 0.62)  # light, saturated → readable on dark
    return "#%02x%02x%02x" % (int(r * 255), int(g * 255), int(b * 255))


def _llm_identity(name: str) -> str | None:
    """One Anthropic call to draft the agent identity. Returns None on any failure."""
    try:
        from backend.config import resolve_api_key
        from backend.providers.anthropic_api import AnthropicAPIProvider
        provider = AnthropicAPIProvider(resolve_api_key())
        sys = ("Write a single 1-2 sentence identity line for an internal company "
               "knowledge assistant. It answers ONLY from documents later ingested into "
               "its wiki. Output ONLY the sentence(s), no preamble.")
        res = provider.generate(sys, f"The assistant is named: {name}")
        if not res.ok:
            return None
        text = (res.raw_answer or "").strip()
        if not (10 <= len(text) <= 400):
            return None
        return text
    except Exception:
        return None


def generate_identity(name: str) -> str:
    out = _llm_identity(name)
    if out:
        return out
    return (f"You are the {name} assistant, answering questions from the "
            f"organization's {name} knowledge base. Answer only from ingested documents.")
```

- [ ] **Step 4: Run — PASS** (3 tests).
- [ ] **Step 5: Commit**
```bash
git add backend/agent_provisioning.py tests/test_agent_provisioning.py
git commit -m "feat(agents): provisioning helpers (slug, accent, identity+fallback)"
```

---

### Task 5: `create_agent` provisioning (atomic, with rollback)

**Files:** Modify `backend/agent_provisioning.py`; Test: `tests/test_agent_provisioning.py`

- [ ] **Step 1: Append failing test**:

```python
def test_create_agent_provisions_row_and_dirs(clean_db, tmp_path, monkeypatch):
    from backend import agent_provisioning as ap, agent_registry, db, config
    # Point agent data dirs at tmp so the test writes nowhere real.
    monkeypatch.setattr(config, "_BASE", tmp_path, raising=False)
    monkeypatch.setattr(agent_registry, "_BASE", tmp_path, raising=False)

    spec = ap.create_agent("Legal", created_by="admin@x.com")
    assert spec.id == "legal" and spec.has_jira is False and spec.schema_kind == "generic"
    # DB row exists + active
    with db.connection() as c:
        row = c.execute("SELECT * FROM agents WHERE id='legal'").fetchone()
    assert row and row["status"] == "active"
    # Dirs + seeded index created under tmp
    assert (tmp_path / "agents" / "legal" / "wiki" / "index.md").is_file()
    assert (tmp_path / "agents" / "legal" / "raw").is_dir()
    # Appears in the registry
    agent_registry.invalidate_cache()
    assert "legal" in {a.id for a in agent_registry.all()}


def test_create_agent_rejects_duplicate_and_reserved(clean_db, tmp_path, monkeypatch):
    from backend import agent_provisioning as ap, config, agent_registry
    monkeypatch.setattr(config, "_BASE", tmp_path, raising=False)
    monkeypatch.setattr(agent_registry, "_BASE", tmp_path, raising=False)
    import pytest
    with pytest.raises(ap.AgentExists):
        ap.create_agent("Infosec", created_by="a")   # reserved/existing
    ap.create_agent("Legal", created_by="a")
    with pytest.raises(ap.AgentExists):
        ap.create_agent("legal", created_by="a")      # duplicate slug
```

- [ ] **Step 2: Run — FAIL** (`create_agent` undefined).

- [ ] **Step 3: Implement** in `backend/agent_provisioning.py`:

```python
class AgentError(Exception): ...
class AgentExists(AgentError): ...
class InvalidAgentName(AgentError): ...

_GENERIC_TOOLS = ["wiki_search", "wiki_read_page", "wiki_grep", "wiki_list_pages",
                  "wiki_check_duplicate", "wiki_propose_new", "wiki_propose_edit",
                  "wiki_propose_append", "wiki_propose_multi_edit", "feedback_record"]


def _claude_md_template(name: str, identity: str) -> str:
    return (f"# CLAUDE.md — {name} Agent (auto-generated)\n\n"
            f"{identity}\n\n"
            "Wiki-only agent. Knowledge comes solely from documents ingested into "
            f"`agents/{slugify(name)}/wiki/`. Uses the shared generic wiki methodology "
            "(sources/concepts/entities/relationships/decisions/topics). No Jira/PMS.\n")


def create_agent(name: str, created_by: str):
    from backend import agent_registry, db, wiki_retriever
    from backend.config import _BASE

    slug = slugify(name)
    if not slug:
        raise InvalidAgentName(f"Cannot derive a slug from {name!r}")
    if slug in RESERVED_SLUGS:
        raise AgentExists(f"'{slug}' is reserved")
    with db.connection() as c:
        if c.execute("SELECT 1 FROM agents WHERE id=%s", (slug,)).fetchone():
            raise AgentExists(f"Agent '{slug}' already exists")

    accent = accent_for_slug(slug)
    identity = generate_identity(name)
    wiki_rel, raw_rel, claude_rel = (f"agents/{slug}/wiki", f"agents/{slug}/raw",
                                     f"agents/{slug}/CLAUDE.md")
    wiki_abs = _BASE / wiki_rel
    created_paths = []
    try:
        (wiki_abs / "concepts").mkdir(parents=True, exist_ok=True)
        (_BASE / raw_rel).mkdir(parents=True, exist_ok=True)
        created_paths.append(_BASE / "agents" / slug)
        (wiki_abs / "index.md").write_text(
            f"# {name} Wiki Index\n_Total pages: 0_\n\n(Empty — ingest documents to populate.)\n",
            encoding="utf-8")
        (_BASE / claude_rel).write_text(_claude_md_template(name, identity), encoding="utf-8")

        with db.connection() as c:
            c.execute(
                "INSERT INTO agents (id, display_name, identity, accent, theme_base, "
                "schema_kind, modes, tools, has_jira, has_pms, wiki_dir, raw_dir, "
                "claude_md, prompt_sections, status, created_by) VALUES "
                "(%s,%s,%s,%s,'dark','generic','{api}',%s,false,false,%s,%s,%s,'{}','active',%s)",
                (slug, name.strip(), identity, accent, _GENERIC_TOOLS,
                 wiki_rel, raw_rel, claude_rel, created_by),
            )
    except Exception:
        # Rollback: remove dirs + any row so no half-created agent remains.
        import shutil
        for p in created_paths:
            shutil.rmtree(p, ignore_errors=True)
        try:
            with db.connection() as c:
                c.execute("DELETE FROM agents WHERE id=%s", (slug,))
        except Exception:
            pass
        raise

    agent_registry.invalidate_cache()
    try:
        wiki_retriever.build_index(slug)
    except Exception:
        pass  # index builds lazily on first use anyway
    return agent_registry.get(slug)
```

- [ ] **Step 4: Run — PASS** (both tests).
- [ ] **Step 5: Commit**
```bash
git add backend/agent_provisioning.py tests/test_agent_provisioning.py
git commit -m "feat(agents): create_agent provisioning (dirs+row+index, atomic rollback)"
```

---

### Task 6: rename + archive/delete

**Files:** Modify `backend/agent_provisioning.py`; Test: `tests/test_agent_provisioning.py`

- [ ] **Step 1: Append failing test**:

```python
def test_rename_and_archive(clean_db, tmp_path, monkeypatch):
    from backend import agent_provisioning as ap, agent_registry, config, db
    monkeypatch.setattr(config, "_BASE", tmp_path, raising=False)
    monkeypatch.setattr(agent_registry, "_BASE", tmp_path, raising=False)
    ap.create_agent("Legal", created_by="a")
    ap.update_agent("legal", display_name="Legal & Compliance", identity="New identity here.")
    agent_registry.invalidate_cache()
    assert agent_registry.get("legal").display_name == "Legal & Compliance"
    ap.archive_agent("legal")
    agent_registry.invalidate_cache()
    assert "legal" not in {a.id for a in agent_registry.all()}   # archived → hidden
    import pytest
    with pytest.raises(ap.AgentError):
        ap.archive_agent("conwo")   # built-ins protected
```

- [ ] **Step 2: Run — FAIL**.
- [ ] **Step 3: Implement**:

```python
PROTECTED = {"conwo", "infosec"}


def update_agent(agent_id: str, *, display_name: str | None = None, identity: str | None = None):
    from backend import db, agent_registry
    sets, params = [], []
    if display_name is not None: sets.append("display_name=%s"); params.append(display_name)
    if identity is not None:     sets.append("identity=%s");     params.append(identity)
    if not sets:
        return
    params.append(agent_id)
    with db.connection() as c:
        c.execute(f"UPDATE agents SET {', '.join(sets)} WHERE id=%s", tuple(params))
    agent_registry.invalidate_cache()


def archive_agent(agent_id: str):
    if agent_id in PROTECTED:
        raise AgentError(f"'{agent_id}' is a built-in agent and cannot be removed")
    from backend import db, agent_registry
    with db.connection() as c:
        c.execute("UPDATE agents SET status='archived' WHERE id=%s", (agent_id,))
    agent_registry.invalidate_cache()
```

(Hard-delete + dir/row cleanup is deferred; archive hides the agent and is reversible. If a hard delete is needed later, add `delete_agent` that also removes dirs + agent-scoped rows in a transaction.)

- [ ] **Step 4: Run — PASS**.
- [ ] **Step 5: Commit**
```bash
git add backend/agent_provisioning.py tests/test_agent_provisioning.py
git commit -m "feat(agents): update (rename/identity) + archive; protect built-ins"
```

---

### Task 7: Admin endpoints `POST/PATCH/DELETE /admin/agents`

**Files:** Modify `backend/api.py`; Test: `tests/test_admin_agents_api.py`

- [ ] **Step 1: Write failing test** `tests/test_admin_agents_api.py`:

```python
from fastapi.testclient import TestClient
from backend.api import app, _get_user


def _admin():
    return {"email": "admin@x.com", "role": "admin", "approved": True}


def test_create_agent_endpoint(clean_db, tmp_path, monkeypatch):
    from backend import config, agent_registry
    monkeypatch.setattr(config, "_BASE", tmp_path, raising=False)
    monkeypatch.setattr(agent_registry, "_BASE", tmp_path, raising=False)
    app.dependency_overrides[_get_user] = _admin
    try:
        c = TestClient(app)
        r = c.post("/admin/agents", json={"name": "Legal"})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["id"] == "legal" and body["accent"].startswith("#")
        # Now visible in the public list
        ids = {a["id"] for a in c.get("/agents").json()}
        assert "legal" in ids
        # Duplicate → 409
        assert c.post("/admin/agents", json={"name": "legal"}).status_code == 409
    finally:
        app.dependency_overrides.clear()
```

- [ ] **Step 2: Run — FAIL** (404).

- [ ] **Step 3: Add endpoints in `backend/api.py`** (near other `/admin/*`, using `_require_admin`):

```python
from pydantic import BaseModel
from backend import agent_provisioning

class CreateAgentRequest(BaseModel):
    name: str

class UpdateAgentRequest(BaseModel):
    display_name: str | None = None
    identity: str | None = None

def _agent_public(a) -> dict:
    return {"id": a.id, "display_name": a.display_name, "description": a.identity,
            "identity": a.identity, "accent": a.accent, "theme_base": a.theme_base,
            "modes": list(a.modes), "has_jira": a.has_jira, "has_pms": a.has_pms}

@app.post("/admin/agents")
def create_agent_endpoint(req: CreateAgentRequest, admin: dict = Depends(_require_admin)):
    try:
        spec = agent_provisioning.create_agent(req.name, created_by=admin.get("email", "admin"))
    except agent_provisioning.AgentExists as e:
        raise HTTPException(status_code=409, detail=str(e))
    except agent_provisioning.InvalidAgentName as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _agent_public(spec)

@app.patch("/admin/agents/{agent_id}")
def update_agent_endpoint(agent_id: str, req: UpdateAgentRequest, admin: dict = Depends(_require_admin)):
    agent_provisioning.update_agent(agent_id, display_name=req.display_name, identity=req.identity)
    from backend import agent_registry
    return _agent_public(agent_registry.get(agent_id))

@app.delete("/admin/agents/{agent_id}")
def delete_agent_endpoint(agent_id: str, admin: dict = Depends(_require_admin)):
    try:
        agent_provisioning.archive_agent(agent_id)
    except agent_provisioning.AgentError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"status": "archived", "id": agent_id}
```

Also update the existing `GET /agents` (`list_agents`) to include `accent` + `theme_base` via `_agent_public` so the frontend can theme.

- [ ] **Step 4: Run** the endpoint test + regression:
`/Users/rudrakhare/Desktop/my-wiki/org-wiki/venv/bin/python -m pytest tests/test_admin_agents_api.py tests/test_agents_endpoint.py tests/test_admin_users.py -q`

- [ ] **Step 5: Full regression** — `/Users/rudrakhare/Desktop/my-wiki/org-wiki/venv/bin/python -m pytest tests/ -q` (only ~5 known failures).

- [ ] **Step 6: Commit**
```bash
git add backend/api.py tests/test_admin_agents_api.py
git commit -m "feat(api): admin create/update/archive agent endpoints; /agents exposes accent"
```

---

### Task 8: End-to-end backend milestone verification

**Files:** none (verification)

- [ ] **Step 1: Full suite green** — `/Users/rudrakhare/Desktop/my-wiki/org-wiki/venv/bin/python -m pytest tests/ -q` (only the 5 known pre-existing failures).

- [ ] **Step 2: Boot + curl** (dev DB; admin token via dev-login as in prior milestones):
```bash
# create
curl -s -X POST localhost:8000/admin/agents -H 'Authorization: Bearer <admin>' \
  -H 'Content-Type: application/json' -d '{"name":"Legal"}' | python -m json.tool
# appears in the list with its own accent
curl -s localhost:8000/agents | python -c 'import sys,json;print([(a["id"],a["accent"]) for a in json.load(sys.stdin)])'
# graph is empty + isolated for the new agent
curl -s localhost:8000/api/wiki/graph -H 'X-Agent-Id: legal' -H 'Authorization: Bearer <admin>' \
  | python -c 'import sys,json;print("legal nodes:",len(json.load(sys.stdin)["nodes"]))'
```
Expected: create returns `{id:"legal", accent:"#…", …}`; `/agents` lists conwo/infosec/legal; legal graph has ~1 node (empty index.md); Conwo/Infosec unchanged.

- [ ] **Step 3: Commit any fixups; milestone done.**

---

## Milestone exit criteria (Phases 1–3)
- `agents` table is the source of truth; Conwo/Infosec seeded and behave identically.
- `POST /admin/agents {name}` provisions a complete agent (row + PVC dirs + index + accent + identity), atomically with rollback; duplicates/reserved rejected.
- New agent appears in `GET /agents` (with accent) and is immediately usable (its own empty graph/ingest/query) — all inherited from shared code.
- Non-Conwo agents use the generic ingest schema (Infosec included); Conwo keeps WorkInSync.
- Full pytest green except the 5 known pre-existing failures.

**Next:** Plan 2 — frontend: Create-Agent + Manage-Agents admin UI, and per-agent accent theming on the shared dark base.
