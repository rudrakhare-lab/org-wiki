# Layer 1 — Server-Key Auth Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Unblock non-admin users by serving the Anthropic key server-side; harden auth with token expiry, conversation ownership, role-scoped tool dispatch, and per-user rate limiting; restrict Claude Code stream to admins.

**Architecture:** `resolve_api_key()` in `config.py` checks `ANTHROPIC_API_KEY` env var first so users never need to supply keys. `ToolRegistry` gains a `user_role` param so the dispatch layer can enforce per-tool access in a single place. A new in-memory `rate_limit.py` counts daily queries per token. Conversation ownership is enforced by adding a `user_email` column to the conversations table via an idempotent migration.

**Tech Stack:** Python 3.12, FastAPI, SQLite (WAL), pytest, Angular 17 signals

> **Note:** `admin_api.apply_patch()` already calls `wiki_retriever.rebuild_index()` (lines 158–160). That guardrail is already implemented — no task required.

---

## File Structure

| Action | Path | Responsibility |
|--------|------|----------------|
| Modify | `backend/config.py` | `resolve_api_key()`, token expiry check |
| Modify | `backend/tools/registry.py` | `user_role` param, `_TOOL_PERMISSIONS`, role check |
| Modify | `backend/tools/__init__.py` | `build_registry(user_role=)` |
| Modify | `backend/orchestrator.py` | Thread `user_role` to `build_registry()` and `run()` signature |
| Modify | `backend/api.py` | Stream endpoints → admin-only, optional `claude_api_key`, `has_server_key` in health, rate limit, `user_email` to store |
| Modify | `backend/conversation_store.py` | `user_email` column + idempotent migration + `list_conversations()` filter |
| Create | `backend/rate_limit.py` | In-memory 30-query/day counter per token |
| Modify | `config/allowed_users.toml` | Document `expires_at` field |
| Modify | `frontend/src/app/core/api.service.ts` | Add `has_server_key` to health response type |
| Modify | `frontend/src/app/features/ask/ask.ts` | Hide API key input when server key present |
| Create | `tests/test_auth.py` | `resolve_api_key()` + token expiry tests |
| Modify | `tests/test_tools.py` | Role enforcement + `build_registry(user_role=)` tests |
| Create | `tests/test_rate_limit.py` | Daily limit, admin bypass, midnight reset |
| Modify | `tests/test_conversations.py` | `user_email` migration + ownership filter tests |

---

## Task 1: Config hardening — `resolve_api_key()` + token expiry

**Files:**
- Modify: `backend/config.py`
- Create: `tests/test_auth.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_auth.py
import os
import pytest
from datetime import date
from unittest.mock import patch

from backend.config import resolve_api_key, lookup_user_by_token


def test_resolve_api_key_prefers_server_key(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-server-key")
    assert resolve_api_key("sk-caller-key") == "sk-server-key"


def test_resolve_api_key_falls_back_to_caller(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert resolve_api_key("sk-caller-key") == "sk-caller-key"


def test_resolve_api_key_raises_when_neither(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(ValueError, match="No Anthropic API key"):
        resolve_api_key(None)


def test_lookup_user_by_token_rejects_expired_token(monkeypatch):
    fake_users = {
        "alice": {
            "email": "alice@moveinsync.com",
            "role": "contributor",
            "token": "abc123",
            "expires_at": "2020-01-01",  # past date
        }
    }
    with patch("backend.config._load_users", return_value=fake_users):
        result = lookup_user_by_token("abc123")
    assert result is None


def test_lookup_user_by_token_accepts_valid_token(monkeypatch):
    fake_users = {
        "alice": {
            "email": "alice@moveinsync.com",
            "role": "contributor",
            "token": "abc123",
            "expires_at": "2099-01-01",
        }
    }
    with patch("backend.config._load_users", return_value=fake_users):
        result = lookup_user_by_token("abc123")
    assert result is not None
    assert result["email"] == "alice@moveinsync.com"


def test_lookup_user_by_token_no_expiry_always_valid():
    fake_users = {
        "admin": {
            "email": "admin@moveinsync.com",
            "role": "admin",
            "token": "admintoken",
        }
    }
    with patch("backend.config._load_users", return_value=fake_users):
        result = lookup_user_by_token("admintoken")
    assert result is not None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd org-wiki && venv/bin/pytest tests/test_auth.py -v 2>&1 | head -30
```

Expected: `ImportError` or `AttributeError: module 'backend.config' has no attribute 'resolve_api_key'`

- [ ] **Step 3: Add `resolve_api_key()` and expiry check to `backend/config.py`**

Add these imports at the top of `backend/config.py` after the existing imports:
```python
from datetime import date
```

Replace the existing `lookup_user_by_token()` function and add `resolve_api_key()` after `token_for_email()`:

```python
def resolve_api_key(request_key: str | None = None) -> str:
    """Return the server-side key if set, else fall back to the caller-supplied key."""
    server_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if server_key:
        return server_key
    if request_key:
        return request_key
    raise ValueError(
        "No Anthropic API key. Set ANTHROPIC_API_KEY on the server "
        "or pass claude_api_key in the request."
    )


def lookup_user_by_token(token: str) -> dict | None:
    for _name, user in _load_users().items():
        if user.get("token") != token:
            continue
        expires = user.get("expires_at")
        if expires:
            try:
                if date.fromisoformat(str(expires)) < date.today():
                    return None   # expired
            except ValueError:
                pass  # malformed date — don't block, let it through
        return user
    return None
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
venv/bin/pytest tests/test_auth.py -v
```

Expected: all 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/config.py tests/test_auth.py
git commit -m "feat(auth): add resolve_api_key() + token expiry check in lookup_user_by_token"
```

---

## Task 2: Role-scoped ToolRegistry

**Files:**
- Modify: `backend/tools/registry.py`
- Modify: `backend/tools/__init__.py`
- Modify: `tests/test_tools.py`

- [ ] **Step 1: Write failing tests**

Add to the bottom of `tests/test_tools.py`:

```python
# ── 9. Role-scoped registry ───────────────────────────────────────────────────

def test_registry_accepts_user_role_param():
    """build_registry should accept user_role without error."""
    registry = build_registry(user_role="contributor")
    assert registry is not None


def test_permission_denied_for_unknown_tool_with_role():
    """A missing tool still returns unknown_tool code regardless of role."""
    registry = build_registry(user_role="admin")
    result_json, trace = registry.execute("nonexistent_tool", {}, round_num=1)
    import json
    result = json.loads(result_json)
    assert result["code"] == "unknown_tool"


def test_role_order_viewer_lt_contributor():
    from backend.tools.registry import _ROLE_ORDER
    assert _ROLE_ORDER["viewer"] < _ROLE_ORDER["contributor"]
    assert _ROLE_ORDER["contributor"] < _ROLE_ORDER["admin"]
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
venv/bin/pytest tests/test_tools.py::test_registry_accepts_user_role_param -v
```

Expected: `TypeError: build_registry() got an unexpected keyword argument 'user_role'`

- [ ] **Step 3: Update `backend/tools/registry.py`**

Replace the current `ToolRegistry` class definition (preserving all existing logic, only changing `__init__` and `execute`):

```python
# Role hierarchy — viewer < contributor < admin
_ROLE_ORDER = {"viewer": 0, "contributor": 1, "admin": 2}

# Map tool name → minimum role required. Empty = all authenticated users.
_TOOL_PERMISSIONS: dict[str, str] = {}


class ToolRegistry:
    def __init__(self, user_role: str = "viewer") -> None:
        self._user_role = user_role
        self._handlers: dict[str, Callable] = {}
        self._schemas: list[dict] = []

    def register(self, schema: dict, fn: Callable) -> None:
        self._handlers[schema["name"]] = fn
        self._schemas.append(schema)

    @property
    def schemas(self) -> list[dict]:
        return list(self._schemas)

    def execute(
        self,
        name: str,
        tool_input: dict,
        round_num: int,
    ) -> tuple[str, ToolTraceEntry]:
        # Permission check before dispatch
        required_role = _TOOL_PERMISSIONS.get(name, "viewer")
        if _ROLE_ORDER.get(self._user_role, 0) < _ROLE_ORDER.get(required_role, 0):
            result = json.dumps({
                "error": f"Role '{self._user_role}' cannot call '{name}'",
                "code": "permission_denied",
            })
            entry: ToolTraceEntry = {
                "round": round_num,
                "tool_name": name,
                "input": self._sanitize_dict(tool_input),
                "output_summary": result[:300],
            }
            return result, entry

        handler = self._handlers.get(name)
        if handler is None:
            result = json.dumps({"error": f"Unknown tool: {name!r}", "code": "unknown_tool"})
        else:
            try:
                output = handler(tool_input)
                result = json.dumps(output, ensure_ascii=False, default=str)
            except Exception as exc:
                result = json.dumps({"error": str(exc), "code": "tool_exception"})

        entry = {
            "round": round_num,
            "tool_name": name,
            "input": self._sanitize_dict(tool_input),
            "output_summary": self._sanitize_str(result)[:300],
        }
        return result, entry

    # ── Sanitizers ────────────────────────────────────────────────────────────

    def _sanitize_dict(self, d: dict) -> dict:
        try:
            return json.loads(self._sanitize_str(json.dumps(d, default=str)))
        except Exception:
            return {}

    def _sanitize_str(self, s: str) -> str:
        return _SECRET_RE.sub("[REDACTED]", s)
```

- [ ] **Step 4: Update `backend/tools/__init__.py`** — add `user_role` param to `build_registry()`

Find the `def build_registry()` signature in `backend/tools/__init__.py` and change it to:

```python
def build_registry(user_role: str = "viewer") -> ToolRegistry:
    r = ToolRegistry(user_role=user_role)
    # rest of the function body unchanged
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
venv/bin/pytest tests/test_tools.py -v
```

Expected: all 11 tests PASS (8 original + 3 new)

- [ ] **Step 6: Commit**

```bash
git add backend/tools/registry.py backend/tools/__init__.py tests/test_tools.py
git commit -m "feat(tools): add user_role to ToolRegistry + _TOOL_PERMISSIONS dict"
```

---

## Task 3: Thread `user_role` through orchestrator

**Files:**
- Modify: `backend/orchestrator.py`

- [ ] **Step 1: Add `user_role` param to `run()`, `run_deep()`, and `run_single_shot()`**

In `backend/orchestrator.py`, update the three function signatures:

```python
def run(
    question: str,
    mode: Literal["api", "claude-code"] = "api",
    claude_api_key: str | None = None,
    server: str = "com",
    buid: str | None = None,
    functional_area: str | None = None,
    service: str | None = None,
    officeid: str | None = None,
    roomid: str | None = None,
    role: str | None = None,
    user_role: str = "viewer",          # ← add this
) -> OrchestratorResult:
    if mode == "claude-code":
        result = run_single_shot(question, mode, None, server, buid, functional_area, user_role)
        result.deep_search_used = False
        return result
    return run_deep(
        question, mode, claude_api_key, server, buid, functional_area,
        service, officeid, roomid, role, user_role,
    )


def run_deep(
    question: str,
    mode: str,
    claude_api_key: str | None,
    server: str = "com",
    buid: str | None = None,
    functional_area: str | None = None,
    service: str | None = None,
    officeid: str | None = None,
    roomid: str | None = None,
    role: str | None = None,
    user_role: str = "viewer",          # ← add this
) -> OrchestratorResult:
    # ... existing code ...
    # Change ONE line — pass user_role to build_registry:
    registry = build_registry(user_role=user_role)
    # rest unchanged


def run_single_shot(
    question: str,
    mode: str,
    claude_api_key: str | None,
    server: str = "com",
    buid: str | None = None,
    functional_area: str | None = None,
    user_role: str = "viewer",          # ← add this
) -> OrchestratorResult:
    # ... existing code ...
    # Change ONE line — pass user_role to build_registry if used; otherwise unchanged
```

- [ ] **Step 2: Run existing tests to confirm nothing broke**

```bash
venv/bin/pytest tests/ -v --ignore=tests/test_auth.py --ignore=tests/test_rate_limit.py -q
```

Expected: all existing tests pass

- [ ] **Step 3: Commit**

```bash
git add backend/orchestrator.py
git commit -m "feat(orchestrator): thread user_role param to build_registry"
```

---

## Task 4: API hardening — stream endpoints + health + QueryRequest

**Files:**
- Modify: `backend/api.py`

- [ ] **Step 1: Change `/query/stream` and `/agent/log-answer` to require admin**

In `backend/api.py`, find the two function signatures:

```python
# Line ~350 — query_stream
async def query_stream(
    req: AgentStreamRequest,
    user: dict = Depends(_require_user_or_local_dev),   # ← change this line
):

# Line ~439 — log_agent_answer  
def log_agent_answer(req: AgentLogRequest, user: dict = Depends(_require_user_or_local_dev)):  # ← change
```

Change both to:

```python
async def query_stream(
    req: AgentStreamRequest,
    user: dict = Depends(_require_admin),
):

def log_agent_answer(req: AgentLogRequest, user: dict = Depends(_require_admin)):
```

- [ ] **Step 2: Update `QueryRequest` validator to allow missing `claude_api_key` when server key is set**

Find the `_validate_api_key` model validator in `QueryRequest` and replace it:

```python
@model_validator(mode="after")
def _validate_api_key(self) -> "QueryRequest":
    if self.mode != "api":
        return self
    # If the server has ANTHROPIC_API_KEY set, the caller key is optional.
    if os.getenv("ANTHROPIC_API_KEY", "").strip():
        return self
    if not self.claude_api_key:
        raise ValueError("claude_api_key is required when mode is 'api' and no server key is set")
    if len(self.claude_api_key) < 10:
        raise ValueError("claude_api_key appears invalid (too short)")
    return self
```

Also add `import os` at the top of `api.py` if not already present. (Check first — it may already be there.)

- [ ] **Step 3: Add `has_server_key` to `/health` and pass `user_email` + `user_role` to orchestrator**

In `backend/api.py`, update `health()` and `query()`:

```python
@app.get("/health")
def health():
    return {
        "status": "ok",
        "wiki_pages": wiki_retriever.page_count(),
        "has_server_key": bool(os.getenv("ANTHROPIC_API_KEY", "").strip()),
    }
```

In `query()`, update the `create_conversation()` call and `orchestrator.run()` call:

```python
# In query():
# When creating a new conversation, pass the user's email
user_email = (user or {}).get("email")

if not conversation_id:
    conv = conversation_store.create_conversation(
        title=conversation_store.auto_title_from_question(req.question),
        user_email=user_email,
    )
    conversation_id = conv["id"]

# Resolve API key server-side
from backend.config import resolve_api_key
resolved_key = resolve_api_key(req.claude_api_key)

# Thread user_role to orchestrator
user_role = (user or {}).get("role", "viewer")

result = orchestrator.run(
    question=req.question,
    mode=req.mode,
    claude_api_key=resolved_key,
    server=req.server,
    buid=req.buid,
    functional_area=req.functional_area,
    service=req.service,
    officeid=req.officeid,
    roomid=req.roomid,
    role=req.role,
    user_role=user_role,
)
```

- [ ] **Step 4: Update `GET /conversations` to filter by user (non-admin sees own only)**

In `backend/api.py`, find `list_conversations()` endpoint and update it:

```python
@app.get("/conversations")
def list_conversations(limit: int = 200, user: dict | None = Depends(_get_user)):
    if limit < 1:
        limit = 1
    if limit > 500:
        limit = 500
    # Admins see all conversations; everyone else sees only their own
    user_email = None
    if user and user.get("role") != "admin":
        user_email = user.get("email")
    return {"conversations": conversation_store.list_conversations(limit=limit, user_email=user_email)}
```

- [ ] **Step 5: Run the full test suite**

```bash
venv/bin/pytest tests/ -v -q
```

Expected: all existing tests pass. Some tests that hit `/query` may fail if they don't send a key but have no env var set — that's expected; they'll be fixed when rate_limit and conversation tests are updated.

- [ ] **Step 6: Commit**

```bash
git add backend/api.py
git commit -m "feat(api): admin-only stream, optional claude_api_key, has_server_key in health"
```

---

## Task 5: Rate limiting

**Files:**
- Create: `backend/rate_limit.py`
- Modify: `backend/api.py`
- Create: `tests/test_rate_limit.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_rate_limit.py
import importlib
from unittest.mock import patch
import pytest


@pytest.fixture(autouse=True)
def reset_rate_limit():
    """Each test starts with a clean rate-limit state."""
    import backend.rate_limit as rl
    rl._COUNTS.clear()
    yield
    rl._COUNTS.clear()


def test_viewer_allowed_up_to_limit():
    import backend.rate_limit as rl
    for i in range(30):
        assert rl.check_rate_limit("tok1", "viewer") is True
    # 31st call should be denied
    assert rl.check_rate_limit("tok1", "viewer") is False


def test_contributor_same_limit():
    import backend.rate_limit as rl
    for i in range(30):
        rl.check_rate_limit("tok2", "contributor")
    assert rl.check_rate_limit("tok2", "contributor") is False


def test_admin_unlimited():
    import backend.rate_limit as rl
    for i in range(100):
        assert rl.check_rate_limit("tokadmin", "admin") is True


def test_different_tokens_independent():
    import backend.rate_limit as rl
    for i in range(30):
        rl.check_rate_limit("user_a", "viewer")
    # user_a is exhausted; user_b has a fresh counter
    assert rl.check_rate_limit("user_b", "viewer") is True


def test_counter_resets_on_new_day():
    import backend.rate_limit as rl
    from datetime import date, timedelta
    # Exhaust quota
    for i in range(30):
        rl.check_rate_limit("tok3", "viewer")
    assert rl.check_rate_limit("tok3", "viewer") is False
    # Simulate next day by patching _RESET_DATE to yesterday
    rl._RESET_DATE = date.today() - timedelta(days=1)
    assert rl.check_rate_limit("tok3", "viewer") is True
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
venv/bin/pytest tests/test_rate_limit.py -v 2>&1 | head -20
```

Expected: `ModuleNotFoundError: No module named 'backend.rate_limit'`

- [ ] **Step 3: Create `backend/rate_limit.py`**

```python
"""
In-memory per-user rate limiter.

Counter resets at midnight UTC. Thread-safe via a single lock.
Admin role bypasses the limit entirely.
"""
from __future__ import annotations

import threading
from datetime import date, datetime, timezone

_COUNTS: dict[str, int] = {}
_RESET_DATE: date = date.today()
_LOCK = threading.Lock()

DAILY_LIMIT = 30


def check_rate_limit(token: str, role: str) -> bool:
    """Return True if the request is allowed, False if the daily limit is exceeded."""
    if role == "admin":
        return True

    global _RESET_DATE
    today = datetime.now(timezone.utc).date()

    with _LOCK:
        if today != _RESET_DATE:
            _COUNTS.clear()
            _RESET_DATE = today
        current = _COUNTS.get(token, 0)
        if current >= DAILY_LIMIT:
            return False
        _COUNTS[token] = current + 1
        return True
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
venv/bin/pytest tests/test_rate_limit.py -v
```

Expected: all 5 tests PASS

- [ ] **Step 5: Wire rate limit into `/query` in `backend/api.py`**

At the top of the `query()` function (after user is resolved, before orchestrator.run):

```python
@app.post("/query", response_model=QueryResponse)
def query(
    req: QueryRequest,
    user: dict | None = Depends(_get_user),
):
    # Rate limit check (skip for unauthenticated — they'll fail at mode level)
    if user:
        from backend.rate_limit import check_rate_limit
        token = user.get("token", "")
        role = user.get("role", "viewer")
        if not check_rate_limit(token, role):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Daily query limit reached (30/day). Resets at midnight UTC.",
            )
    # ... rest of existing function unchanged
```

- [ ] **Step 6: Commit**

```bash
git add backend/rate_limit.py backend/api.py tests/test_rate_limit.py
git commit -m "feat(rate-limit): 30 queries/day for viewer/contributor, unlimited admin"
```

---

## Task 6: Conversation ownership

**Files:**
- Modify: `backend/conversation_store.py`
- Modify: `tests/test_conversations.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_conversations.py`:

```python
def test_user_email_column_added_via_migration(isolated_store):
    """create_conversation with user_email stores the value."""
    cs = isolated_store
    c = cs.create_conversation("Test", user_email="alice@example.com")
    assert c["id"]
    # Verify the value was stored by checking the raw DB
    import sqlite3
    from backend import config
    conn = sqlite3.connect(str(config.CONVERSATIONS_DB))
    row = conn.execute(
        "SELECT user_email FROM conversations WHERE id = ?", (c["id"],)
    ).fetchone()
    conn.close()
    assert row[0] == "alice@example.com"


def test_list_conversations_filters_by_user_email(isolated_store):
    cs = isolated_store
    cs.create_conversation("Alice conv", user_email="alice@example.com")
    cs.create_conversation("Bob conv", user_email="bob@example.com")
    cs.create_conversation("Shared conv", user_email=None)

    alice_convs = cs.list_conversations(user_email="alice@example.com")
    assert len(alice_convs) == 1
    assert alice_convs[0]["title"] == "Alice conv"


def test_list_conversations_admin_sees_all(isolated_store):
    cs = isolated_store
    cs.create_conversation("Alice conv", user_email="alice@example.com")
    cs.create_conversation("Bob conv", user_email="bob@example.com")
    all_convs = cs.list_conversations(user_email=None)
    assert len(all_convs) == 2
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
venv/bin/pytest tests/test_conversations.py::test_user_email_column_added_via_migration -v
```

Expected: `TypeError: create_conversation() got an unexpected keyword argument 'user_email'`

- [ ] **Step 3: Update `backend/conversation_store.py`**

Add the `_MIGRATION` string and `_apply_migrations()` function, and update `create_conversation()` and `list_conversations()`:

```python
# Add after _SCHEMA definition:

_MIGRATION_ADD_USER_EMAIL = """
ALTER TABLE conversations ADD COLUMN user_email TEXT;
"""

def _apply_migrations(conn: sqlite3.Connection) -> None:
    """Idempotently apply schema migrations. Safe to call on every startup."""
    # Check if user_email column exists
    cols = {row[1] for row in conn.execute("PRAGMA table_info(conversations)")}
    if "user_email" not in cols:
        conn.execute(_MIGRATION_ADD_USER_EMAIL)
```

Update `init_schema()` to call `_apply_migrations()`:

```python
def init_schema() -> None:
    """Create tables and indexes if they don't exist. Safe to call repeatedly."""
    with _connect() as conn:
        conn.executescript(_SCHEMA)
        _apply_migrations(conn)
```

Update `create_conversation()` signature and INSERT:

```python
def create_conversation(title: str | None = None, user_email: str | None = None) -> dict[str, Any]:
    init_schema()
    cid = _new_id()
    now = _now()
    final_title = (title or "New chat").strip()[:200] or "New chat"
    with _connect() as conn:
        conn.execute(
            "INSERT INTO conversations (id, title, created_at, updated_at, user_email) "
            "VALUES (?, ?, ?, ?, ?)",
            (cid, final_title, now, now, user_email),
        )
    return {
        "id": cid,
        "title": final_title,
        "created_at": now,
        "updated_at": now,
        "user_email": user_email,
        "message_count": 0,
    }
```

Update `list_conversations()` to accept and filter by `user_email`:

```python
def list_conversations(limit: int = 200, user_email: str | None = None) -> list[dict[str, Any]]:
    init_schema()
    with _connect() as conn:
        if user_email is not None:
            rows = conn.execute(
                """
                SELECT c.id, c.title, c.created_at, c.updated_at,
                       (SELECT COUNT(*) FROM messages m WHERE m.conversation_id = c.id)
                       AS message_count
                FROM conversations c
                WHERE c.user_email = ?
                ORDER BY c.updated_at DESC
                LIMIT ?
                """,
                (user_email, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT c.id, c.title, c.created_at, c.updated_at,
                       (SELECT COUNT(*) FROM messages m WHERE m.conversation_id = c.id)
                       AS message_count
                FROM conversations c
                ORDER BY c.updated_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
    return [dict(r) for r in rows]
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
venv/bin/pytest tests/test_conversations.py -v
```

Expected: all tests pass (original + 3 new)

- [ ] **Step 5: Commit**

```bash
git add backend/conversation_store.py tests/test_conversations.py
git commit -m "feat(store): add user_email column via idempotent migration, filter list_conversations"
```

---

## Task 7: Frontend — server key awareness

**Files:**
- Modify: `frontend/src/app/core/api.service.ts`
- Modify: `frontend/src/app/features/ask/ask.ts`

- [ ] **Step 1: Update `health()` return type in `api.service.ts`**

Find line 507 in `frontend/src/app/core/api.service.ts`:
```typescript
health(): Observable<{ status: string; wiki_pages: number }> {
  return this.http.get<{ status: string; wiki_pages: number }>(`${API_BASE}/health`);
```

Replace with:
```typescript
health(): Observable<{ status: string; wiki_pages: number; has_server_key: boolean }> {
  return this.http.get<{ status: string; wiki_pages: number; has_server_key: boolean }>(`${API_BASE}/health`);
```

- [ ] **Step 2: Add `hasServerKey` signal to `Ask` component and call `health()` in `ngOnInit`**

In `frontend/src/app/features/ask/ask.ts`, add the signal to the class body (near the other signals around line 324):

```typescript
hasServerKey = signal(false);
```

In `ngOnInit()`, add a call to `health()` after the existing checks:

```typescript
this.api.health().subscribe({
  next: h => this.hasServerKey.set(h.has_server_key ?? false),
  error: () => {},
});
```

- [ ] **Step 3: Update the API key input condition in the template**

Find line 193 in `ask.ts`:
```typescript
@if (mode() === 'api' && !apiKey) {
```

Replace with:
```typescript
@if (mode() === 'api' && !apiKey && !hasServerKey()) {
```

- [ ] **Step 4: Build the frontend to confirm no TypeScript errors**

```bash
cd frontend && npm run build 2>&1 | tail -20
```

Expected: build succeeds with no errors

- [ ] **Step 5: Commit**

```bash
git add frontend/src/app/core/api.service.ts frontend/src/app/features/ask/ask.ts
git commit -m "feat(frontend): hide API key input when server-side key is configured"
```

---

## Task 8: Document `expires_at` in TOML

**Files:**
- Modify: `config/allowed_users.toml`

- [ ] **Step 1: Read current TOML**

```bash
cat config/allowed_users.toml
```

- [ ] **Step 2: Add `expires_at` comment block to show the field**

Add a comment block at the top of `config/allowed_users.toml` explaining the `expires_at` field:

```toml
# expires_at (optional) — ISO date string (YYYY-MM-DD). Token rejected after this date.
# Omit for no-expiry (recommended for admin accounts only).
# Example: expires_at = "2026-12-31"
```

For each non-admin user entry that should have an expiry, add:
```toml
[users.alice]
email = "alice@moveinsync.com"
role = "contributor"
token = "<existing-token>"
expires_at = "2026-12-31"
```

- [ ] **Step 3: Commit**

```bash
git add config/allowed_users.toml
git commit -m "docs(auth): document expires_at field in allowed_users.toml"
```

---

## Task 9: Final Layer 1 verification

- [ ] **Step 1: Run full test suite**

```bash
cd org-wiki && venv/bin/pytest tests/ -v
```

Expected: all tests pass

- [ ] **Step 2: Security checklist**

Manually verify:
- [ ] `ANTHROPIC_API_KEY` is not returned in any API response — check `GET /health` output
- [ ] `POST /query/stream` returns 403 for a Bearer token with `role = "contributor"` (test with `curl`)
- [ ] `pms_runtime_values` returns `credentials_required` (not `permission_denied`) for a viewer-role token when no PMS env vars set — confirms all authenticated users can call PMS tools
- [ ] An expired token returns 401 — update one token's `expires_at` to yesterday and test

```bash
# Quick smoke test (replace <TOKEN> with a viewer token)
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <TOKEN>" \
  -d '{"question": "What is visitor management?", "mode": "api", "server": "com"}'
# Expected: response with answer (no claude_api_key needed when ANTHROPIC_API_KEY is set)

curl -X POST http://localhost:8000/query/stream \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <VIEWER_TOKEN>" \
  -d '{"question": "test"}'
# Expected: {"detail": "Admin access required"} with 403
```

- [ ] **Step 3: Final Layer 1 commit**

```bash
git add -A
git commit -m "feat(layer1): Layer 1 complete — server key, auth hardening, rate limit, conversation ownership"
```
