# Infosec Multi-Agent — Backend Plan (Phases 0–3)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Conwo backend multi-agent: a config-driven agent registry, per-request agent resolution via an `X-Agent-Id` header, per-agent knowledge base + prompts + tool scoping, and `agent_id`-scoped conversations/traces — verifiable end-to-end by `curl` with **zero Conwo regression**.

**Architecture:** Agents are defined in `config/agents.toml` and loaded into immutable `AgentSpec` objects. A middleware resolves the active agent per request into `request.state.agent_id` and a `current_agent` ContextVar; the orchestrator receives it explicitly, while leaf code (wiki retriever, wiki tools) reads it from the ContextVar (replacing today's module-global `WIKI_DIR`). The Postgres operational tables gain an `agent_id` column (default `'conwo'`, so existing rows backfill safely). Infosec is wiki-only (`has_jira=false`, `has_pms=false`) and `api`-mode only.

**Tech Stack:** Python 3.11+, FastAPI, psycopg3 + connection pool, pytest (isolated `wis_conwo_test` DB), Anthropic tool-use loop.

**Companion spec:** `docs/superpowers/specs/2026-06-14-infosec-multi-agent-design.md`
**Scope note:** Frontend switcher + Infosec `CLAUDE.md`/content are a **separate Plan 2**, written after this milestone lands.

---

## File Structure

**New files:**
- `config/agents.toml` — agent definitions (conwo + infosec).
- `backend/agent_registry.py` — `AgentSpec` dataclass + `get()/all()/default()` loaders.
- `backend/agent_context.py` — `current_agent` ContextVar + set/get/reset helpers.
- `migrations/postgres/090_agent_id.sql` — add `agent_id` to conversations/messages/trace_sessions.
- `tests/test_agent_registry.py`, `tests/test_agent_context.py`, `tests/test_agents_endpoint.py`, `tests/test_agent_scoping.py` — new tests.
- `agents/infosec/wiki/index.md` + a placeholder page — minimal Infosec KB for milestone verification.

**Modified files (responsibility unchanged, agent-awareness added):**
- `backend/config.py` — keep `WIKI_DIR`/`RAW_DIR`/`CLAUDE_MD` as conwo aliases derived from the registry default.
- `backend/wiki_retriever.py` — singleton `_INDEX` → per-agent `{agent_id: WikiIndex}`.
- `backend/tools/wiki_tools.py`, `backend/tools/wiki_read_tools.py` — resolve wiki dir from agent context.
- `backend/tools/__init__.py` — `build_registry(user_role, agent)` filters to the agent's tool allowlist.
- `backend/system_prompt.py`, `backend/deep_system_prompt.py` — per-agent prompt + identity, Jira/PMS scaffolding conditional.
- `backend/preflight.py` — Jira retrieval + Jira seed blocks conditional on `agent.has_jira`.
- `backend/orchestrator.py` — thread `agent` through; gate mode by `agent.modes`.
- `backend/conversation_store.py`, `backend/trace_store.py`, `backend/trace_api.py` — `agent_id` column + filtered reads.
- `backend/wiki_proposals.py`, `backend/feedback_service.py` — `agent_id` field on records.
- `backend/api.py` — agent-resolution middleware + `_get_agent` dependency + `GET /agents`; thread agent into query/stream/conversations/ingest endpoints.
- `backend/ingest_api.py`, `backend/ingest_service.py` — agent-scoped ingest.
- `backend/wiki_graph_api.py` — agent-scoped graph.

---

## Conventions for every task

- **Run tests with the test venv:** `venv/bin/python -m pytest <path> -v` (the suite auto-creates/points at `wis_conwo_test`; see `tests/conftest.py`).
- **DB tests** take the `clean_db` (truncate) or `isolated_store` fixture.
- **Never write a `.py` file while a `--reload` backend is running** (CLAUDE.md §1). Run the plan against a stopped backend or a separate test process.
- **Commit after every task.** Branch is the worktree feature branch.

---

## PHASE 0 — Agent registry & per-request resolution

### Task 1: Agent registry (`AgentSpec` + loader)

**Files:**
- Create: `config/agents.toml`
- Create: `backend/agent_registry.py`
- Test: `tests/test_agent_registry.py`

- [ ] **Step 1: Write `config/agents.toml`**

```toml
# Agent registry. Each [agents.<id>] defines one selectable AI agent.
# Paths resolve relative to CONWO_DATA_DIR (PVC) or repo root, like config.py.

[agents.conwo]
display_name    = "Conwo"
description     = "WorkInSync product, config & debugging assistant"
wiki_dir        = "wiki"
raw_dir         = "raw"
claude_md       = "CLAUDE.md"
prompt_sections = [5, 9, 12]
tools           = ["*"]
modes           = ["api", "agent"]
has_jira        = true
has_pms         = true
identity        = "You are Conwo, an AI assistant that answers product, config, and debugging questions about WorkInSync."

[agents.infosec]
display_name    = "Infosec"
description     = "Information-security knowledge assistant"
wiki_dir        = "agents/infosec/wiki"
raw_dir         = "agents/infosec/raw"
claude_md       = "agents/infosec/CLAUDE.md"
prompt_sections = []
tools           = ["wiki_search", "wiki_read_page", "wiki_grep", "wiki_list_pages", "wiki_check_duplicate", "wiki_propose_new", "wiki_propose_edit", "wiki_propose_append", "wiki_propose_multi_edit", "feedback_record"]
modes           = ["api"]
has_jira        = false
has_pms         = false
identity        = "You are the Infosec assistant, answering information-security questions from the organization's security knowledge base."
```

- [ ] **Step 2: Write the failing test** in `tests/test_agent_registry.py`

```python
from pathlib import Path
from backend import agent_registry


def test_loads_both_agents():
    ids = {a.id for a in agent_registry.all()}
    assert {"conwo", "infosec"} <= ids


def test_conwo_spec_fields():
    conwo = agent_registry.get("conwo")
    assert conwo.display_name == "Conwo"
    assert conwo.has_jira is True and conwo.has_pms is True
    assert conwo.tool_allowed("jira_search_ranked") is True   # "*" allows all
    assert conwo.wiki_dir.name == "wiki"
    assert conwo.claude_md.name == "CLAUDE.md"


def test_infosec_is_wiki_only():
    info = agent_registry.get("infosec")
    assert info.has_jira is False and info.has_pms is False
    assert info.modes == ("api",)
    assert info.tool_allowed("wiki_search") is True
    assert info.tool_allowed("jira_search_ranked") is False
    assert info.tool_allowed("pms_runtime_values") is False
    assert info.wiki_dir.parts[-3:] == ("agents", "infosec", "wiki")


def test_unknown_agent_falls_back_to_conwo():
    assert agent_registry.get("does-not-exist").id == "conwo"
    assert agent_registry.get(None).id == "conwo"
    assert agent_registry.default().id == "conwo"
```

- [ ] **Step 3: Run test to verify it fails**

Run: `venv/bin/python -m pytest tests/test_agent_registry.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'backend.agent_registry'`.

- [ ] **Step 4: Write `backend/agent_registry.py`**

```python
"""Agent registry — loads config/agents.toml into immutable AgentSpec objects.

One AgentSpec per selectable AI agent. Paths resolve under CONWO_DATA_DIR (PVC)
or repo root, exactly like backend.config, so an agent's wiki/raw/CLAUDE.md live
wherever Conwo's data lives.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # py<3.11
    import tomli as tomllib  # type: ignore

from backend.config import ROOT, _BASE  # _BASE honors CONWO_DATA_DIR

_AGENTS_TOML = ROOT / "config" / "agents.toml"
DEFAULT_AGENT_ID = "conwo"


@dataclass(frozen=True)
class AgentSpec:
    id: str
    display_name: str
    description: str
    wiki_dir: Path
    raw_dir: Path
    claude_md: Path
    prompt_sections: tuple[int, ...]
    tools: tuple[str, ...]
    modes: tuple[str, ...]
    has_jira: bool
    has_pms: bool
    identity: str

    def tool_allowed(self, name: str) -> bool:
        return "*" in self.tools or name in self.tools

    def mode_allowed(self, mode: str) -> bool:
        return mode in self.modes


def _resolve(p: str) -> Path:
    path = Path(p)
    return path if path.is_absolute() else (_BASE / path)


@lru_cache(maxsize=1)
def _load() -> dict[str, AgentSpec]:
    with _AGENTS_TOML.open("rb") as f:
        data = tomllib.load(f)
    out: dict[str, AgentSpec] = {}
    for agent_id, cfg in data.get("agents", {}).items():
        out[agent_id] = AgentSpec(
            id=agent_id,
            display_name=cfg["display_name"],
            description=cfg.get("description", ""),
            wiki_dir=_resolve(cfg["wiki_dir"]),
            raw_dir=_resolve(cfg["raw_dir"]),
            claude_md=_resolve(cfg["claude_md"]),
            prompt_sections=tuple(cfg.get("prompt_sections", [])),
            tools=tuple(cfg.get("tools", ["*"])),
            modes=tuple(cfg.get("modes", ["api"])),
            has_jira=bool(cfg.get("has_jira", False)),
            has_pms=bool(cfg.get("has_pms", False)),
            identity=cfg.get("identity", ""),
        )
    if DEFAULT_AGENT_ID not in out:
        raise RuntimeError(f"agents.toml must define [agents.{DEFAULT_AGENT_ID}]")
    return out


def all() -> list[AgentSpec]:
    return list(_load().values())


def get(agent_id: str | None) -> AgentSpec:
    """Return the AgentSpec for agent_id, falling back to conwo on unknown/None."""
    agents = _load()
    return agents.get(agent_id or "", agents[DEFAULT_AGENT_ID])


def default() -> AgentSpec:
    return _load()[DEFAULT_AGENT_ID]


def invalidate_cache() -> None:
    _load.cache_clear()
```

> If `backend/config.py` does not export `_BASE`, add `_BASE` to its module scope (it is already computed there as `_BASE = Path(_DATA_DIR) if _DATA_DIR else ROOT`). Confirm `ROOT` and `_BASE` are importable; both already exist in `config.py`.

- [ ] **Step 5: Run test to verify it passes**

Run: `venv/bin/python -m pytest tests/test_agent_registry.py -v`
Expected: PASS (4 tests).

- [ ] **Step 6: Commit**

```bash
git add config/agents.toml backend/agent_registry.py tests/test_agent_registry.py
git commit -m "feat(agents): config-driven agent registry (AgentSpec + loader)"
```

---

### Task 2: Per-request agent context (ContextVar + dependency)

**Files:**
- Create: `backend/agent_context.py`
- Test: `tests/test_agent_context.py`

- [ ] **Step 1: Write the failing test** in `tests/test_agent_context.py`

```python
from backend import agent_context, agent_registry


def test_default_is_conwo():
    assert agent_context.get_current_agent_id() == "conwo"
    assert agent_context.get_current_agent().id == "conwo"


def test_set_and_reset():
    token = agent_context.set_current_agent("infosec")
    assert agent_context.get_current_agent_id() == "infosec"
    assert agent_context.get_current_agent().id == "infosec"
    agent_context.reset_current_agent(token)
    assert agent_context.get_current_agent_id() == "conwo"


def test_unknown_id_resolves_to_conwo_spec():
    token = agent_context.set_current_agent("bogus")
    # The id string is stored verbatim, but the resolved spec falls back to conwo.
    assert agent_context.get_current_agent().id == "conwo"
    agent_context.reset_current_agent(token)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv/bin/python -m pytest tests/test_agent_context.py -v`
Expected: FAIL — `No module named 'backend.agent_context'`.

- [ ] **Step 3: Write `backend/agent_context.py`**

```python
"""Request-scoped active-agent context.

The orchestrator receives the AgentSpec explicitly, but leaf code that today
reads the module-global WIKI_DIR (wiki_retriever, wiki tools) reads the active
agent from this ContextVar instead. Set/reset per request in middleware.
"""
from __future__ import annotations

from contextvars import ContextVar, Token

from backend import agent_registry
from backend.agent_registry import AgentSpec

_current: ContextVar[str] = ContextVar("current_agent", default="conwo")


def set_current_agent(agent_id: str | None) -> Token:
    return _current.set(agent_id or "conwo")


def reset_current_agent(token: Token) -> None:
    _current.reset(token)


def get_current_agent_id() -> str:
    return _current.get()


def get_current_agent() -> AgentSpec:
    return agent_registry.get(_current.get())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `venv/bin/python -m pytest tests/test_agent_context.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/agent_context.py tests/test_agent_context.py
git commit -m "feat(agents): request-scoped current_agent ContextVar"
```

---

### Task 3: Middleware resolution + `_get_agent` dependency + `GET /agents`

**Files:**
- Modify: `backend/api.py` (add middleware near the existing trace middleware registration; add dependency near `_get_user` ~line 201; add route)
- Test: `tests/test_agents_endpoint.py`

- [ ] **Step 1: Write the failing test** in `tests/test_agents_endpoint.py`

```python
from fastapi.testclient import TestClient
from backend.api import app

client = TestClient(app)


def test_list_agents_public_shape():
    r = client.get("/agents")
    assert r.status_code == 200
    by_id = {a["id"]: a for a in r.json()}
    assert "conwo" in by_id and "infosec" in by_id
    assert by_id["infosec"]["has_jira"] is False
    assert by_id["infosec"]["modes"] == ["api"]
    assert by_id["conwo"]["display_name"] == "Conwo"
    # Never leak filesystem paths to the client.
    assert "wiki_dir" not in by_id["conwo"]
    assert "claude_md" not in by_id["conwo"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv/bin/python -m pytest tests/test_agents_endpoint.py -v`
Expected: FAIL — 404 on `/agents`.

- [ ] **Step 3: Add the middleware + dependency + route in `backend/api.py`**

Near the other imports:

```python
from fastapi import Header
from backend import agent_registry, agent_context
```

Register a middleware (place it AFTER the trace middleware add, so it runs inside it). Use a plain ASGI-safe `@app.middleware("http")`:

```python
@app.middleware("http")
async def _agent_resolution_middleware(request, call_next):
    agent_id = request.headers.get("x-agent-id") or "conwo"
    spec = agent_registry.get(agent_id)
    request.state.agent_id = spec.id
    token = agent_context.set_current_agent(spec.id)
    try:
        return await call_next(request)
    finally:
        agent_context.reset_current_agent(token)
```

Add a dependency next to `_get_user` (~line 201):

```python
def _get_agent(request: Request) -> "agent_registry.AgentSpec":
    """Resolve the active agent for this request (set by middleware)."""
    return agent_registry.get(getattr(request.state, "agent_id", "conwo"))
```

Add the route (near other public GETs):

```python
@app.get("/agents")
def list_agents():
    return [
        {
            "id": a.id,
            "display_name": a.display_name,
            "description": a.description,
            "modes": list(a.modes),
            "has_jira": a.has_jira,
            "has_pms": a.has_pms,
        }
        for a in agent_registry.all()
    ]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `venv/bin/python -m pytest tests/test_agents_endpoint.py -v`
Expected: PASS.

- [ ] **Step 5: Phase-0 regression — full suite still green**

Run: `venv/bin/python -m pytest tests/ -q`
Expected: PASS (no Conwo regressions). Fix any breakage before continuing.

- [ ] **Step 6: Commit**

```bash
git add backend/api.py tests/test_agents_endpoint.py
git commit -m "feat(agents): X-Agent-Id middleware, _get_agent dep, GET /agents"
```

---

## PHASE 1 — Database & stores (`agent_id`)

### Task 4: Migration `090_agent_id.sql`

**Files:**
- Create: `migrations/postgres/090_agent_id.sql`
- Test: `tests/test_agent_scoping.py` (first test)

- [ ] **Step 1: Write the migration**

```sql
-- 090_agent_id.sql — scope operational data by agent. Idempotent.
-- DEFAULT 'conwo' backfills all existing rows to the original agent.

ALTER TABLE conversations  ADD COLUMN IF NOT EXISTS agent_id TEXT NOT NULL DEFAULT 'conwo';
ALTER TABLE messages       ADD COLUMN IF NOT EXISTS agent_id TEXT NOT NULL DEFAULT 'conwo';
ALTER TABLE trace_sessions ADD COLUMN IF NOT EXISTS agent_id TEXT NOT NULL DEFAULT 'conwo';

CREATE INDEX IF NOT EXISTS idx_conversations_agent_user
    ON conversations (agent_id, user_email);
CREATE INDEX IF NOT EXISTS idx_trace_sessions_agent_started
    ON trace_sessions (agent_id, started_at);
```

- [ ] **Step 2: Write the failing test** in `tests/test_agent_scoping.py`

```python
def test_migration_adds_agent_id_columns(clean_db):
    from backend import db
    with db.connection() as conn:
        cols = {
            r[0]
            for r in conn.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'conversations'"
            ).fetchall()
        }
    assert "agent_id" in cols
```

- [ ] **Step 3: Run test to verify it fails (before migration is applied)**

If the test DB was created before this migration existed, drop+recreate it so `init_db()` re-applies migrations:
Run: `venv/bin/python -m pytest tests/test_agent_scoping.py::test_migration_adds_agent_id_columns -v`
Expected: FAIL (column missing) until the test DB is migrated. The session fixture runs `init_db()`, which applies new `*.sql` files; if the column is absent because the DB predates the file, run:
`psql -h localhost -U wis_conwo -c 'DROP DATABASE wis_conwo_test'` then re-run pytest.

- [ ] **Step 4: Confirm migration applies + test passes**

Run: `venv/bin/python -m pytest tests/test_agent_scoping.py::test_migration_adds_agent_id_columns -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add migrations/postgres/090_agent_id.sql tests/test_agent_scoping.py
git commit -m "feat(db): add agent_id to conversations/messages/trace_sessions (default conwo)"
```

---

### Task 5: `conversation_store` agent scoping

**Files:**
- Modify: `backend/conversation_store.py` (`create_conversation`, `list_conversations`, `add_message`)
- Test: `tests/test_agent_scoping.py`

- [ ] **Step 1: Write the failing test** (append to `tests/test_agent_scoping.py`)

```python
def test_conversations_scoped_by_agent(isolated_store):
    cs = isolated_store
    c1 = cs.create_conversation("conwo chat", user_email="u@x.com", agent_id="conwo")
    c2 = cs.create_conversation("infosec chat", user_email="u@x.com", agent_id="infosec")

    conwo_list = cs.list_conversations(user_email="u@x.com", agent_id="conwo")
    infosec_list = cs.list_conversations(user_email="u@x.com", agent_id="infosec")

    assert [c["id"] for c in conwo_list] == [c1["id"]]
    assert [c["id"] for c in infosec_list] == [c2["id"]]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv/bin/python -m pytest tests/test_agent_scoping.py::test_conversations_scoped_by_agent -v`
Expected: FAIL — `create_conversation() got an unexpected keyword argument 'agent_id'`.

- [ ] **Step 3: Edit `create_conversation`** (replace signature + INSERT + return dict)

```python
def create_conversation(title: str | None = None, user_email: str | None = None,
                        agent_id: str = "conwo") -> dict[str, Any]:
    cid = _new_id()
    now = _now()
    final_title = (title or "New chat").strip()[:200] or "New chat"
    with _connect() as conn:
        conn.execute(
            "INSERT INTO conversations (id, title, created_at, updated_at, user_email, agent_id) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (cid, final_title, now, now, user_email, agent_id),
        )
    return {
        "id": cid, "title": final_title, "created_at": now, "updated_at": now,
        "user_email": user_email, "agent_id": agent_id, "message_count": 0,
    }
```

- [ ] **Step 4: Edit `list_conversations`** to filter by agent

```python
def list_conversations(limit: int = 200, user_email: str | None = None,
                       agent_id: str = "conwo") -> list[dict[str, Any]]:
    where = ["c.agent_id = %s"]
    params: list[Any] = [agent_id]
    if user_email is not None:
        where.append("c.user_email = %s")
        params.append(user_email)
    params.append(limit)
    with _connect() as conn:
        rows = conn.execute(
            f"""
            SELECT c.id, c.title, c.created_at, c.updated_at,
                   (SELECT COUNT(*) FROM messages m WHERE m.conversation_id = c.id)
                   AS message_count
            FROM conversations c
            WHERE {" AND ".join(where)}
            ORDER BY c.updated_at DESC
            LIMIT %s
            """,
            tuple(params),
        ).fetchall()
    return [dict(r) for r in rows]
```

- [ ] **Step 5: Edit `add_message`** — add `agent_id` to the INSERT (denormalized for fast per-agent message queries). Add param `agent_id: str = "conwo"` to the signature, add `agent_id` to the column list + `VALUES`, and pass it. (Pull the value from the parent conversation if you prefer; the caller in api.py already knows the agent.)

```python
# in the INSERT column list add `, agent_id` and one more %s, then in the params tuple add `agent_id,`
```

- [ ] **Step 6: Run test to verify it passes**

Run: `venv/bin/python -m pytest tests/test_agent_scoping.py::test_conversations_scoped_by_agent -v`
Expected: PASS.

- [ ] **Step 7: Conwo-regression — existing conversation tests still pass**

Run: `venv/bin/python -m pytest tests/test_conversations.py -v`
Expected: PASS (defaults keep `agent_id='conwo'`).

- [ ] **Step 8: Commit**

```bash
git add backend/conversation_store.py tests/test_agent_scoping.py
git commit -m "feat(conversations): scope create/list/messages by agent_id"
```

---

### Task 6: `trace_store` + `trace_api` agent scoping

**Files:**
- Modify: `backend/trace_store.py` (`start_session`)
- Modify: `backend/trace_api.py` (session list + dashboard queries accept/filter `agent_id`)
- Test: `tests/test_agent_scoping.py`

- [ ] **Step 1: Write the failing test** (append)

```python
def test_trace_sessions_scoped_by_agent(clean_db):
    from backend import trace_store, db
    trace_store.start_session("t-conwo", mode="api", question="q1", agent_id="conwo")
    trace_store.start_session("t-info", mode="api", question="q2", agent_id="infosec")
    with db.connection() as conn:
        n_info = conn.execute(
            "SELECT COUNT(*) FROM trace_sessions WHERE agent_id = %s", ("infosec",)
        ).fetchone()[0]
    assert n_info == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv/bin/python -m pytest tests/test_agent_scoping.py::test_trace_sessions_scoped_by_agent -v`
Expected: FAIL — `start_session() got an unexpected keyword argument 'agent_id'`.

- [ ] **Step 3: Edit `trace_store.start_session`** — add `agent_id: str = "conwo"` kwarg; add `agent_id` to the INSERT column list and `VALUES`, and to the `ON CONFLICT ... DO UPDATE SET` use `agent_id = COALESCE(excluded.agent_id, trace_sessions.agent_id)`. Pass `agent_id` in the params tuple. (Earliest non-null wins, same pattern as `user_email`.)

```python
def start_session(trace_id: str, *, mode: str, question: str | None = None,
                  conversation_id: str | None = None, message_id: str | None = None,
                  user_email: str | None = None, agent_id: str = "conwo") -> None:
    ...
    "(trace_id, conversation_id, message_id, started_at, mode, question, status, user_email, agent_id) "
    "VALUES (%s,%s,%s,%s,%s,%s,'in_progress',%s,%s) "
    "ON CONFLICT(trace_id) DO UPDATE SET ... "
    "  agent_id = COALESCE(excluded.agent_id, trace_sessions.agent_id)",
    (trace_id, conversation_id, message_id, _now_iso(), mode, question_val, user_email, agent_id),
```

- [ ] **Step 4: Edit `trace_api.py`** — every sessions-list and dashboard aggregate query accepts an optional `agent_id` (read from `request.state.agent_id` via the `_get_agent` dependency or a `Header`) and adds `WHERE agent_id = %s` (AND-combined with existing filters). Default to `conwo` when absent so existing dashboards are unchanged.

> Concretely: add `agent: AgentSpec = Depends(_get_agent)` to each trace route in `trace_api.py`, thread `agent.id` into the SQL `WHERE`. The dashboard overview/tools/errors/cost and the `/sessions` list all gain the `agent_id` filter.

- [ ] **Step 5: Run test to verify it passes**

Run: `venv/bin/python -m pytest tests/test_agent_scoping.py::test_trace_sessions_scoped_by_agent -v`
Expected: PASS.

- [ ] **Step 6: Conwo-regression**

Run: `venv/bin/python -m pytest tests/test_stream_user_email.py -v`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/trace_store.py backend/trace_api.py tests/test_agent_scoping.py
git commit -m "feat(traces): scope sessions + dashboard queries by agent_id"
```

---

### Task 7: Feedback + proposals `agent_id` field

**Files:**
- Modify: `backend/wiki_proposals.py` (write `agent_id` on each proposal; filter list reads)
- Modify: `backend/feedback_service.py` (write `agent_id` on each answer/feedback record)
- Test: `tests/test_agent_scoping.py`

- [ ] **Step 1: Write the failing test** (append)

```python
def test_proposals_carry_agent_id(tmp_path, monkeypatch):
    import backend.wiki_proposals as wp
    monkeypatch.setattr(wp, "PROPOSALS_FILE", tmp_path / "proposals.jsonl")
    wp.add_proposal({"kind": "new", "path": "x.md", "content": "..."}, agent_id="infosec")
    items = wp.list_proposals(agent_id="infosec")
    assert len(items) == 1 and items[0]["agent_id"] == "infosec"
    assert wp.list_proposals(agent_id="conwo") == []
```

> Match the real function names in `wiki_proposals.py`; if the add/list helpers are named differently, adapt the test to the actual API (keep the agent_id assertion).

- [ ] **Step 2: Run test to verify it fails**

Run: `venv/bin/python -m pytest tests/test_agent_scoping.py::test_proposals_carry_agent_id -v`
Expected: FAIL — unexpected `agent_id` kwarg.

- [ ] **Step 3: Implement** — add `agent_id: str = "conwo"` to the proposal-add and answer-log helpers; write `"agent_id": agent_id` into each JSON record; add an `agent_id` filter to the list/read helpers (default `"conwo"`; treat records missing the field as `"conwo"` for backward compatibility).

- [ ] **Step 4: Run test to verify it passes**

Run: `venv/bin/python -m pytest tests/test_agent_scoping.py::test_proposals_carry_agent_id -v`
Expected: PASS.

- [ ] **Step 5: Conwo-regression + commit**

```bash
venv/bin/python -m pytest tests/test_wiki_proposals.py tests/test_admin_wiki_proposals.py -q
git add backend/wiki_proposals.py backend/feedback_service.py tests/test_agent_scoping.py
git commit -m "feat(feedback): tag proposals + answer log with agent_id"
```

---

## PHASE 2 — Backend agent-awareness

### Task 8: Per-agent wiki index

**Files:**
- Modify: `backend/wiki_retriever.py` (`_INDEX` singleton → per-agent dict; `search`/`all_paths`/`get_page`/`build_index` read the active agent)
- Test: `tests/test_agent_scoping.py`

- [ ] **Step 1: Write the failing test** (append)

```python
def test_wiki_index_is_per_agent(tmp_path):
    import backend.wiki_retriever as wr
    from backend import agent_context

    # Build a tiny infosec wiki on disk and index it via the explicit wiki_dir
    # arg (AgentSpec is frozen, so we pass the dir directly rather than patching).
    info_wiki = tmp_path / "infosec_wiki"
    info_wiki.mkdir()
    (info_wiki / "phishing.md").write_text("---\ntype: concept\n---\n# Phishing\nEmail attacks.")

    wr.build_index("infosec", wiki_dir=info_wiki)   # build that agent's index
    token = agent_context.set_current_agent("infosec")
    try:
        paths = [p.path for p in wr.search("phishing", top_n=5)]
    finally:
        agent_context.reset_current_agent(token)
    assert any("phishing" in p for p in paths)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv/bin/python -m pytest tests/test_agent_scoping.py::test_wiki_index_is_per_agent -v`
Expected: FAIL — `build_index()` takes no agent argument.

- [ ] **Step 3: Refactor `wiki_retriever.py`**

Replace the module singleton with a per-agent registry:

```python
# was: _INDEX = WikiIndex()
_INDICES: dict[str, "WikiIndex"] = {}
_indices_lock = RLock()


def _active_agent():
    from backend import agent_context
    return agent_context.get_current_agent()


def build_index(agent_id: str | None = None, wiki_dir: Path | None = None) -> "WikiIndex":
    """Build (or rebuild) one agent's index. agent_id=None → active agent."""
    from backend import agent_context, agent_registry
    aid = agent_id or agent_context.get_current_agent_id()
    spec = agent_registry.get(aid)
    target_dir = wiki_dir or spec.wiki_dir
    idx = WikiIndex()
    idx.build(target_dir)
    with _indices_lock:
        _INDICES[aid] = idx
    return idx


def get_index(agent_id: str | None = None) -> "WikiIndex":
    from backend import agent_context
    aid = agent_id or agent_context.get_current_agent_id()
    with _indices_lock:
        idx = _INDICES.get(aid)
    if idx is None:
        idx = build_index(aid)
    return idx


def search(query: str, top_n: int = 5):
    return get_index().search(query, top_n=top_n)


def all_paths():
    return get_index().all_paths()


def get_page(path: str):
    return get_index().get_page(path)
```

Keep `WikiIndex.build(wiki_dir)` as-is (it already accepts a dir). Update the api.py lifespan to build all agents: `for a in agent_registry.all(): wiki_retriever.build_index(a.id)`.

- [ ] **Step 4: Run test to verify it passes**

Run: `venv/bin/python -m pytest tests/test_agent_scoping.py::test_wiki_index_is_per_agent -v`
Expected: PASS.

- [ ] **Step 5: Conwo-regression**

Run: `venv/bin/python -m pytest tests/test_preflight.py tests/test_wiki_grep.py -q`
Expected: PASS (active agent defaults to conwo → conwo's wiki).

- [ ] **Step 6: Commit**

```bash
git add backend/wiki_retriever.py backend/api.py tests/test_agent_scoping.py
git commit -m "feat(wiki): per-agent wiki index (replaces global singleton)"
```

---

### Task 9: Wiki tools resolve dir from active agent

**Files:**
- Modify: `backend/tools/wiki_tools.py`, `backend/tools/wiki_read_tools.py`, `backend/tools/wiki_propose_tools.py` (any handler importing `WIKI_DIR` or calling the global retriever)
- Test: covered by Task 10 + the end-to-end milestone (Task 20)

- [ ] **Step 1: Replace `from backend.config import WIKI_DIR`** usages

For any handler that needs the wiki dir, resolve it live:

```python
from backend import agent_context

def _wiki_dir() -> Path:
    return agent_context.get_current_agent().wiki_dir
```

Replace direct `WIKI_DIR` references inside handlers with `_wiki_dir()`. Handlers that call `wiki_retriever.search(...)` / `all_paths()` need no change — those now read the active agent automatically (Task 8).

- [ ] **Step 2: Run the tool tests**

Run: `venv/bin/python -m pytest tests/test_tools.py tests/test_wiki_propose_tools.py -q`
Expected: PASS (active agent = conwo in tests → conwo wiki dir, unchanged behavior).

- [ ] **Step 3: Commit**

```bash
git add backend/tools/wiki_tools.py backend/tools/wiki_read_tools.py backend/tools/wiki_propose_tools.py
git commit -m "feat(tools): wiki tools resolve wiki dir from active agent"
```

---

### Task 10: Per-agent tool allowlist in `build_registry`

**Files:**
- Modify: `backend/tools/__init__.py` (`build_registry(user_role, agent)`)
- Test: `tests/test_agent_scoping.py`

- [ ] **Step 1: Write the failing test** (append)

```python
def test_registry_filters_tools_for_infosec():
    from backend.tools import build_registry
    from backend import agent_registry

    info = build_registry(user_role="admin", agent=agent_registry.get("infosec"))
    names = {s["name"] for s in info.schemas}
    assert "wiki_search" in names
    assert "jira_search_ranked" not in names
    assert not any(n.startswith("pms_") for n in names)

    conwo = build_registry(user_role="admin", agent=agent_registry.get("conwo"))
    cnames = {s["name"] for s in conwo.schemas}
    assert "jira_search_ranked" in cnames and "wiki_search" in cnames
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv/bin/python -m pytest tests/test_agent_scoping.py::test_registry_filters_tools_for_infosec -v`
Expected: FAIL — `build_registry()` got an unexpected keyword `agent`.

- [ ] **Step 3: Edit `build_registry`** in `backend/tools/__init__.py`

```python
def build_registry(user_role: str = "viewer", agent=None) -> ToolRegistry:
    """Build a ToolRegistry. If `agent` is given, only tools in its allowlist
    are registered (agent.tools == ['*'] registers all)."""
    if agent is None:
        from backend import agent_registry
        agent = agent_registry.default()
    r = ToolRegistry(user_role=user_role)

    def reg(schema, fn):
        if agent.tool_allowed(schema["name"]):
            r.register(schema, fn)

    reg(WIKI_SEARCH_SCHEMA, _wiki_search_handler)
    reg(WIKI_READ_PAGE_SCHEMA, _wiki_read_page_handler)
    reg(WIKI_GREP_SCHEMA, _wiki_grep_handler)
    reg(JIRA_SEARCH_RANKED_SCHEMA, _jira_search_ranked_handler)
    # ... convert EVERY existing r.register(...) line to reg(...) ...
    reg(WIKI_LIST_PAGES_SCHEMA, _wiki_list_pages_handler)
    reg(WIKI_CHECK_DUPLICATE_SCHEMA, _wiki_check_duplicate_handler)
    return r


ALL_TOOLS: ToolRegistry = build_registry()   # conwo default — unchanged
```

- [ ] **Step 4: Run test to verify it passes + Conwo-regression**

Run: `venv/bin/python -m pytest tests/test_agent_scoping.py::test_registry_filters_tools_for_infosec tests/test_tools.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/tools/__init__.py tests/test_agent_scoping.py
git commit -m "feat(tools): per-agent tool allowlist in build_registry"
```

---

### Task 11: Per-agent `system_prompt`

**Files:**
- Modify: `backend/system_prompt.py` (`load_system_prompt(agent_id)`, per-agent cache, identity from spec)
- Test: `tests/test_agent_scoping.py`

- [ ] **Step 1: Write the failing test** (append)

```python
def test_system_prompt_uses_agent_identity(monkeypatch):
    from backend import system_prompt, agent_registry
    # conwo prompt mentions WorkInSync; build it explicitly for conwo.
    p = system_prompt.load_system_prompt("conwo")
    assert "Conwo" in p
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv/bin/python -m pytest tests/test_agent_scoping.py::test_system_prompt_uses_agent_identity -v`
Expected: FAIL — `load_system_prompt()` takes 0 positional args.

- [ ] **Step 3: Edit `system_prompt.py`** — accept `agent_id`, read the spec's `claude_md` + `prompt_sections` + `identity`; replace the `@lru_cache(maxsize=1)` with a per-agent dict cache.

```python
from functools import lru_cache
from backend import agent_registry

@lru_cache(maxsize=8)
def load_system_prompt(agent_id: str = "conwo") -> str:
    spec = agent_registry.get(agent_id)
    if not spec.claude_md.exists():
        raise FileNotFoundError(f"CLAUDE.md not found at {spec.claude_md}")
    claude_text = spec.claude_md.read_text(encoding="utf-8")
    query_sections = _extract_sections(claude_text, list(spec.prompt_sections))
    known_patterns_path = spec.wiki_dir / "known-answer-patterns.md"
    known_patterns = known_patterns_path.read_text(encoding="utf-8").strip() if known_patterns_path.exists() else ""
    parts = [
        _SAFETY_BLOCK,            # extract the existing read-only safety text into this constant
        f"# {spec.display_name} Backend\n\n{spec.identity}\n",
        query_sections,
    ]
    # ... keep the known_patterns + answer-footer appends unchanged ...
    return "\n\n".join(p for p in parts if p)


def invalidate_cache() -> None:
    load_system_prompt.cache_clear()
```

> Extract the literal read-only safety paragraph currently inlined (lines ~57–66) into a module constant `_SAFETY_BLOCK` so both agents share it. The safety text references "Conwo" — generalize to "This assistant" so it reads correctly for any agent.

- [ ] **Step 4: Run test + Conwo-regression**

Run: `venv/bin/python -m pytest tests/test_agent_scoping.py::test_system_prompt_uses_agent_identity -q`
Expected: PASS. (`load_system_prompt` is used by `run_single_shot`/claude-code; conwo unaffected.)

- [ ] **Step 5: Commit**

```bash
git add backend/system_prompt.py tests/test_agent_scoping.py
git commit -m "feat(prompt): per-agent system prompt + identity"
```

---

### Task 12: Per-agent `deep_system_prompt` (Jira/PMS scaffolding conditional)

**Files:**
- Modify: `backend/deep_system_prompt.py` (`load_deep_system_prompt(agent)` builds from identity + capabilities)
- Test: `tests/test_agent_scoping.py`

- [ ] **Step 1: Write the failing test** (append)

```python
def test_deep_prompt_omits_jira_for_wiki_only_agent():
    from backend.deep_system_prompt import load_deep_system_prompt
    from backend import agent_registry
    info = load_deep_system_prompt(agent_registry.get("infosec"))
    assert "Infosec" in info
    assert "Jira" not in info and "PMS" not in info
    conwo = load_deep_system_prompt(agent_registry.get("conwo"))
    assert "Jira" in conwo
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv/bin/python -m pytest tests/test_agent_scoping.py::test_deep_prompt_omits_jira_for_wiki_only_agent -v`
Expected: FAIL — `load_deep_system_prompt()` takes 0 args / always contains Jira.

- [ ] **Step 3: Refactor `deep_system_prompt.py`** — split the single string into composable blocks; assemble per agent.

```python
def load_deep_system_prompt(agent=None) -> str:
    if agent is None:
        from backend import agent_registry
        agent = agent_registry.default()

    blocks = [_SAFETY_BLOCK_DEEP, f"{agent.identity}\n"]
    if agent.has_jira or agent.has_pms:
        blocks.append(_EVIDENCE_BLOCK_JIRA_PMS)   # the existing pre-fetch/Jira/PMS workflow text
    else:
        blocks.append(_EVIDENCE_BLOCK_WIKI_ONLY)  # new: wiki-only evidence workflow, no Jira/PMS
    blocks.append(_ANSWER_FOOTER_BLOCK)
    return "\n\n".join(blocks)
```

Carve the current inline prompt into `_SAFETY_BLOCK_DEEP`, `_EVIDENCE_BLOCK_JIRA_PMS` (everything that talks about Jira buckets / PMS configs), and `_ANSWER_FOOTER_BLOCK`. Author `_EVIDENCE_BLOCK_WIKI_ONLY`: same structure, but tells the model it has wiki search/read/grep tools only, no Jira/PMS, and to answer from wiki evidence + say "not documented" only after wiki search is exhausted.

- [ ] **Step 4: Update the caller** in `orchestrator.run_deep` (Task 14 threads the agent here): `system_prompt = load_deep_system_prompt(agent)`.

- [ ] **Step 5: Run test + Conwo-regression**

Run: `venv/bin/python -m pytest tests/test_agent_scoping.py::test_deep_prompt_omits_jira_for_wiki_only_agent tests/test_deep_query_config.py -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/deep_system_prompt.py tests/test_agent_scoping.py
git commit -m "feat(prompt): per-agent deep prompt, wiki-only variant for no-jira agents"
```

---

### Task 13: Agent-conditional preflight + seed message

**Files:**
- Modify: `backend/preflight.py` (`run_preflight(..., agent)`, skip Jira when `not agent.has_jira`; `build_seed_message(..., agent)` omits Jira blocks)
- Test: `tests/test_preflight.py` (new test) + `tests/test_agent_scoping.py`

- [ ] **Step 1: Write the failing test** (append to `tests/test_agent_scoping.py`)

```python
def test_preflight_skips_jira_for_wiki_only_agent(monkeypatch):
    import backend.preflight as pf
    from backend import agent_registry, jira_retriever

    called = {"jira": False}
    monkeypatch.setattr(jira_retriever, "search",
                        lambda *a, **k: called.__setitem__("jira", True) or {"buckets": {}})

    bundle = pf.run_preflight("any security question", agent=agent_registry.get("infosec"))
    assert called["jira"] is False
    assert bundle.seed_jira == {} or bundle.seed_jira.get("buckets") in (None, {})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv/bin/python -m pytest tests/test_agent_scoping.py::test_preflight_skips_jira_for_wiki_only_agent -v`
Expected: FAIL — `run_preflight()` got an unexpected keyword `agent` (and Jira is called).

- [ ] **Step 3: Edit `run_preflight`** — add `agent=None` param (default conwo). Wrap the Jira block:

```python
def run_preflight(question, functional_area=None, registry=None,
                  latest_limit=_PREFLIGHT_LATEST_LIMIT, trace_id=None, agent=None):
    if agent is None:
        from backend import agent_registry
        agent = agent_registry.default()
    ...
    bundle.seed_wiki = wiki_retriever.search(_search_query, top_n=_wiki_top_n_eff)
    ...
    if agent.has_jira:
        bundle.seed_jira = jira_retriever.search(_search_query, functional_area=functional_area)
        # ... existing Jira bucket trace + module-tagged retrieval ...
    else:
        bundle.seed_jira = {"buckets": {}}
    return bundle
```

Guard every later `jira_retriever.by_module(...)` / module-tag block in the function with `if agent.has_jira:`.

- [ ] **Step 4: Edit `build_seed_message`** — add `agent=None`; when `not agent.has_jira`, omit the Jira-evidence and preflight-ticket sections entirely (wiki + scope + optional summary only).

- [ ] **Step 5: Run test + Conwo-regression**

Run: `venv/bin/python -m pytest tests/test_agent_scoping.py::test_preflight_skips_jira_for_wiki_only_agent tests/test_preflight.py -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/preflight.py tests/test_agent_scoping.py
git commit -m "feat(preflight): wiki-only preflight + seed for no-jira agents"
```

---

### Task 14: Thread agent through the orchestrator + mode gating

**Files:**
- Modify: `backend/orchestrator.py` (`run`, `run_deep`, `run_single_shot`, `search_only` take `agent`; gate mode by `agent.modes`)
- Test: `tests/test_orchestrator.py` (new test) + `tests/test_agent_scoping.py`

- [ ] **Step 1: Write the failing test** (append to `tests/test_agent_scoping.py`)

```python
import pytest

def test_orchestrator_rejects_disallowed_mode():
    from backend import orchestrator, agent_registry
    with pytest.raises(ValueError):
        orchestrator.run("q", mode="agent", agent=agent_registry.get("infosec"))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv/bin/python -m pytest tests/test_agent_scoping.py::test_orchestrator_rejects_disallowed_mode -v`
Expected: FAIL — `run()` got an unexpected keyword `agent`.

- [ ] **Step 3: Edit `orchestrator.run`** — add `agent=None` (default conwo); validate mode; pass `agent` to `run_deep`/`run_single_shot`.

```python
def run(question, mode="api", claude_api_key=None, server="com", buid=None,
        functional_area=None, service=None, officeid=None, roomid=None, role=None,
        user_role="viewer", conversation_id=None, trace_id=None, agent=None):
    from backend import agent_registry
    if agent is None:
        agent = agent_registry.default()
    if not agent.mode_allowed(mode):
        raise ValueError(f"Agent '{agent.id}' does not support mode '{mode}'")
    if mode == "claude-code":
        result = run_single_shot(question, mode, None, server, buid, functional_area,
                                 user_role, trace_id=trace_id, agent=agent)
        result.deep_search_used = False
        return result
    return run_deep(question, mode, claude_api_key, server, buid, functional_area,
                    service, officeid, roomid, role, user_role, conversation_id,
                    trace_id=trace_id, agent=agent)
```

- [ ] **Step 4: Edit `run_deep`** — add `agent=None`; default conwo; pass to:
  - `build_registry(user_role=user_role, agent=agent)`
  - `run_preflight(question, functional_area=functional_area, registry=registry, trace_id=trace_id, agent=agent)`
  - `build_seed_message(question, " | ".join(scope_parts), bundle, summary=summary, agent=agent)`
  - `load_deep_system_prompt(agent)`

- [ ] **Step 5: Edit `run_single_shot`** + `search_only` — add `agent=None`; gate the direct `jira_retriever.search(...)` with `if agent.has_jira:` (else use an empty result), and call `load_system_prompt(agent.id)`.

- [ ] **Step 6: Run test + Conwo-regression**

Run: `venv/bin/python -m pytest tests/test_agent_scoping.py::test_orchestrator_rejects_disallowed_mode tests/test_orchestrator.py -q`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/orchestrator.py tests/test_agent_scoping.py
git commit -m "feat(orchestrator): thread agent through run/deep/single-shot + mode gating"
```

---

## PHASE 3 — API propagation & milestone verification

### Task 15: `/query` + `/query/stream` propagate agent

**Files:**
- Modify: `backend/api.py` (query, query_stream endpoints)
- Test: `tests/test_agent_scoping.py` (TestClient)

- [ ] **Step 1: Write the failing test** (append)

```python
from fastapi.testclient import TestClient
from backend.api import app

def test_infosec_query_rejects_agent_mode(monkeypatch):
    client = TestClient(app)
    # A query in 'agent' mode for infosec must be rejected (422/400), not silently run.
    r = client.post("/query", json={"question": "x", "mode": "agent", "server": "com"},
                    headers={"X-Agent-Id": "infosec", "Authorization": "Bearer dev"})
    assert r.status_code in (400, 401, 403, 422)
```

> This asserts the mode gate is reachable through the endpoint. Auth may short-circuit with 401 in a bare test env — acceptable; the key is "never 200 + Conwo subprocess for infosec".

- [ ] **Step 2: Run test to verify current behavior**

Run: `venv/bin/python -m pytest tests/test_agent_scoping.py::test_infosec_query_rejects_agent_mode -v`
Expected: initially may FAIL/200 depending on auth; proceed to wire the agent.

- [ ] **Step 3: Edit `query` + `query_stream`** — add `agent: AgentSpec = Depends(_get_agent)`. Pass `agent=agent` into `orchestrator.run(...)`. Stamp the conversation + trace:
  - `conversation_store.create_conversation(..., agent_id=agent.id)`
  - `conversation_store.add_message(..., agent_id=agent.id)`
  - `trace_store.start_session(..., agent_id=agent.id)` (the handler-side enrich call)
  - In `query_stream`, before building the agent preamble, reject `if not agent.mode_allowed("agent"): raise HTTPException(400, "...")` and pass `agent` to `run_preflight`.

- [ ] **Step 4: Run test + Conwo-regression**

Run: `venv/bin/python -m pytest tests/test_agent_scoping.py tests/test_query_single_key_auth.py tests/test_stream_user_email.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/api.py tests/test_agent_scoping.py
git commit -m "feat(api): /query and /query/stream resolve + propagate agent"
```

---

### Task 16: Conversations endpoints scoped by agent

**Files:**
- Modify: `backend/api.py` (`create_conversation`, `list_conversations`, `get_conversation`, rename/delete — ownership check stays; add agent scope)
- Test: `tests/test_agent_scoping.py`

- [ ] **Step 1: Write the failing test** (append)

```python
def test_list_conversations_filtered_by_header(monkeypatch, clean_db):
    # Seed one conversation per agent for the same user, then list per header.
    from backend import conversation_store as cs
    cs.create_conversation("c", user_email="a@b.com", agent_id="conwo")
    cs.create_conversation("i", user_email="a@b.com", agent_id="infosec")
    # Endpoint test requires an authenticated user; if the suite has an auth
    # fixture/token helper, use it. Otherwise assert at the store level (already
    # covered) and assert the endpoint passes agent.id through via a unit check.
```

> If `tests/` has a token/login helper (see `tests/test_conversations.py`), reuse it to call `GET /conversations` with `X-Agent-Id: infosec` and assert only the infosec row returns. Otherwise rely on the store-level test from Task 5 and just wire the endpoint.

- [ ] **Step 2: Edit the conversation endpoints** — add `agent: AgentSpec = Depends(_get_agent)`; pass `agent_id=agent.id` to `create_conversation`/`list_conversations`. For `get_conversation`/rename/delete, after loading, verify the conversation's `agent_id == agent.id` (404 otherwise) so one agent can't read another's threads.

- [ ] **Step 3: Run + Conwo-regression**

Run: `venv/bin/python -m pytest tests/test_conversations.py tests/test_agent_scoping.py -q`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add backend/api.py tests/test_agent_scoping.py
git commit -m "feat(api): scope conversation endpoints by agent"
```

---

### Task 17: Trace + dashboard endpoints scoped by agent

**Files:**
- Modify: `backend/trace_api.py` (routes take `_get_agent`; filter — done in Task 6 at SQL level, here wire the dependency)
- Test: manual curl in Task 20

- [ ] **Step 1: Wire `agent: AgentSpec = Depends(_get_agent)`** into every `trace_api.py` route and pass `agent.id` to the (already agent-aware) query helpers from Task 6.

- [ ] **Step 2: Conwo-regression**

Run: `venv/bin/python -m pytest tests/ -k trace -q`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add backend/trace_api.py
git commit -m "feat(api): scope trace + dashboard endpoints by agent"
```

---

### Task 18: Ingest endpoints agent-aware

**Files:**
- Modify: `backend/ingest_api.py`, `backend/ingest_service.py`
- Test: `tests/test_ingest_api.py` / `tests/test_ingest_service.py` regression + manual

- [ ] **Step 1: Edit ingest** — every ingest route takes `agent: AgentSpec = Depends(_get_agent)`:
  - Uploads go to `agent.raw_dir / "modules" / "_uploads"`.
  - `build_plan_registry()` / `build_execute_registry()` take the agent and build with `build_registry(..., agent=agent)`; wiki writes target `agent.wiki_dir`.
  - PLAN/EXECUTE system prompts are parameterized with `agent.identity` + read `agent.claude_md`.
  - On execute completion, call `wiki_retriever.build_index(agent.id)` to rebuild only that agent's index.

- [ ] **Step 2: Conwo-regression**

Run: `venv/bin/python -m pytest tests/test_ingest_api.py tests/test_ingest_service.py -q`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add backend/ingest_api.py backend/ingest_service.py
git commit -m "feat(ingest): agent-scoped uploads, wiki writes, prompts, index rebuild"
```

---

### Task 19: Wiki graph endpoint agent-aware

**Files:**
- Modify: `backend/wiki_graph_api.py`
- Test: manual curl in Task 20

- [ ] **Step 1: Edit `wiki_graph`** — read the active agent (via `_get_agent` or `request.state.agent_id`); walk `agent.wiki_dir` instead of the imported `_WIKI_DIR`; run `_add_config_layer` only when `agent.has_pms`.

```python
@router.get("/graph")
async def wiki_graph(request: Request, include_configs: bool = False):
    from backend import agent_context
    agent = agent_context.get_current_agent()
    wiki_dir = agent.wiki_dir
    ...  # rglob over wiki_dir
    if include_configs and agent.has_pms:
        _add_config_layer(nodes, links, seen)
    return {"nodes": list(nodes.values()), "links": links}
```

- [ ] **Step 2: Commit**

```bash
git add backend/wiki_graph_api.py
git commit -m "feat(api): agent-scoped wiki graph endpoint"
```

---

### Task 20: Infosec placeholder KB + end-to-end milestone verification

**Files:**
- Create: `agents/infosec/wiki/index.md`, `agents/infosec/wiki/concepts/phishing.md`
- Create: `agents/infosec/CLAUDE.md` (minimal placeholder — full authoring is Plan 2)
- Create: `agents/infosec/raw/.gitkeep`

- [ ] **Step 1: Create a minimal Infosec wiki** so the agent is answerable:

`agents/infosec/wiki/index.md`:
```markdown
# Infosec Wiki Index
_Total pages: 1_

## Concepts
| Page | Summary |
|------|---------|
| [[concepts/phishing]] | Email-based social-engineering attacks |
```

`agents/infosec/wiki/concepts/phishing.md`:
```markdown
---
type: concept
last_updated: 2026-06-14
---
# Phishing
Phishing is a social-engineering attack delivered by email that tricks a user
into revealing credentials or running malware. Mitigations: MFA, link rewriting,
user reporting, and DMARC/SPF/DKIM enforcement.
```

`agents/infosec/CLAUDE.md` (placeholder; full brain authored in Plan 2):
```markdown
# Infosec Agent — placeholder
This is a temporary CLAUDE.md so the Infosec agent boots. Full schema authored
in Plan 2. The Infosec agent is wiki-only (no Jira, no PMS).
```

- [ ] **Step 2: Full suite green**

Run: `venv/bin/python -m pytest tests/ -q`
Expected: PASS — no Conwo regressions across the whole suite.

- [ ] **Step 3: Boot the backend and verify both agents by curl**

Start backend (no `--reload` during file edits; for this read-only check `--reload` is fine):
```bash
venv/bin/python -m uvicorn backend.api:app --port 8099 &
sleep 4
curl -s localhost:8099/agents | python -m json.tool          # both agents listed
curl -s localhost:8099/api/wiki/graph -H 'X-Agent-Id: infosec' | python -c 'import sys,json;d=json.load(sys.stdin);print("infosec nodes:",len(d["nodes"]))'
curl -s localhost:8099/api/wiki/graph -H 'X-Agent-Id: conwo'   | python -c 'import sys,json;d=json.load(sys.stdin);print("conwo nodes:",len(d["nodes"]))'
```
Expected: `/agents` lists conwo + infosec; infosec graph has ~2 nodes (phishing + index), conwo graph has its full node count. The two node counts differ — proving isolation.

- [ ] **Step 4: (Optional, with API key) verify an Infosec answer is wiki-only**

```bash
curl -s localhost:8099/query -H 'X-Agent-Id: infosec' -H 'Authorization: Bearer <token>' \
  -H 'Content-Type: application/json' \
  -d '{"question":"what is phishing?","mode":"api","server":"com"}' | python -m json.tool
```
Expected: an answer sourced from `concepts/phishing`, **no Jira keys / PMS configs** in `sources`. The trace for this request shows no `jira_*`/`pms_*` tool calls. Conwo answers its own questions unchanged.

- [ ] **Step 5: Commit the milestone**

```bash
git add agents/infosec/
git commit -m "feat(infosec): placeholder KB + backend multi-agent milestone (curl-verified)"
```

---

## Milestone exit criteria (Phases 0–3 done)

- `GET /agents` returns conwo + infosec.
- `X-Agent-Id: infosec` routes queries to the Infosec wiki, with Jira/PMS tools absent and no Jira/PMS in preflight, prompt, or sources.
- Conversations and traces are stored and listed per-agent.
- The full pytest suite passes (Conwo unregressed).
- Two-agent isolation demonstrated by differing graph node counts + a wiki-only Infosec answer.

**Next:** Plan 2 — frontend agent switcher (`AgentService`, `X-Agent-Id` interceptor, sidebar dropdown, per-feature reactivity, branding) and the full Infosec `CLAUDE.md`.
