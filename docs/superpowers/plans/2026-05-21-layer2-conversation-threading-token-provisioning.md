# Layer 2 — Conversation Threading + Token Provisioning Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make follow-up questions stateful (prior conversation turns flow into the tool loop) and let admins onboard new users via API instead of editing TOML.

**Architecture:** `DeepQueryProvider.generate_with_tools()` gains a `prior_messages` parameter; `orchestrator.run_deep()` loads the last 6 turns from the conversation store and prepends them. A new `backend/auth_store.py` maintains `users` + `tokens` tables in `raw/auth/auth.sqlite`. `lookup_user_by_token()` checks this SQLite DB first and falls back to TOML so existing users keep working. New `/admin/users` and `/admin/tokens` endpoints let admins provision and revoke access.

**Tech Stack:** Python 3.12, FastAPI, SQLite (WAL), Anthropic SDK, pytest

**Prerequisite:** Layer 1 plan complete and passing.

---

## File Structure

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `backend/auth_store.py` | SQLite users + tokens tables, CRUD helpers |
| Modify | `backend/providers/deep_query.py` | `prior_messages` param on `generate_with_tools()` |
| Modify | `backend/orchestrator.py` | `_load_conversation_context()` + pass history to `run_deep()` |
| Modify | `backend/config.py` | `lookup_user_by_token()` checks auth_store first, TOML fallback |
| Modify | `backend/api.py` | New `/admin/users/*` + `/admin/tokens/*` endpoints |
| Create | `migrations/002_auth_store.sql` | DDL reference (applied by `auth_store.py` at startup) |
| Create | `tests/test_auth_store.py` | auth_store CRUD + token lookup tests |
| Modify | `tests/test_auth.py` | lookup_user_by_token SQLite-first fallback test |

---

## Task 1: `backend/auth_store.py` — SQLite user + token store

**Files:**
- Create: `backend/auth_store.py`
- Create: `migrations/002_auth_store.sql`
- Create: `tests/test_auth_store.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_auth_store.py
import importlib
import pytest
from pathlib import Path


@pytest.fixture
def isolated_auth(tmp_path, monkeypatch):
    """Point auth_store at a fresh SQLite under tmp_path."""
    auth_dir = tmp_path / "raw" / "auth"
    auth_dir.mkdir(parents=True)
    db = auth_dir / "auth.sqlite"

    import backend.auth_store as auth_module
    monkeypatch.setattr(auth_module, "AUTH_DB", db, raising=False)
    monkeypatch.setattr(auth_module, "AUTH_DIR", auth_dir, raising=False)
    importlib.reload(auth_module)
    yield auth_module


def test_create_and_get_user(isolated_auth):
    as_ = isolated_auth
    as_.create_user("alice@example.com", role="contributor", created_by="admin@example.com")
    user = as_.get_user("alice@example.com")
    assert user is not None
    assert user["role"] == "contributor"
    assert user["email"] == "alice@example.com"


def test_create_and_lookup_token(isolated_auth):
    as_ = isolated_auth
    as_.create_user("bob@example.com", role="viewer")
    token = as_.create_token("bob@example.com", expires_at="2099-01-01")
    assert len(token) == 32

    result = as_.lookup_token(token)
    assert result is not None
    assert result["email"] == "bob@example.com"
    assert result["role"] == "viewer"


def test_revoked_token_not_found(isolated_auth):
    as_ = isolated_auth
    as_.create_user("carol@example.com", role="viewer")
    token = as_.create_token("carol@example.com")
    as_.revoke_token(token)
    assert as_.lookup_token(token) is None


def test_expired_token_not_found(isolated_auth):
    as_ = isolated_auth
    as_.create_user("dave@example.com", role="viewer")
    token = as_.create_token("dave@example.com", expires_at="2020-01-01")
    assert as_.lookup_token(token) is None


def test_list_tokens_for_user(isolated_auth):
    as_ = isolated_auth
    as_.create_user("eve@example.com", role="viewer")
    t1 = as_.create_token("eve@example.com")
    t2 = as_.create_token("eve@example.com")
    tokens = as_.list_tokens("eve@example.com")
    assert len(tokens) == 2


def test_delete_user_cascades_tokens(isolated_auth):
    as_ = isolated_auth
    as_.create_user("frank@example.com", role="viewer")
    token = as_.create_token("frank@example.com")
    as_.delete_user("frank@example.com")
    assert as_.get_user("frank@example.com") is None
    assert as_.lookup_token(token) is None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd org-wiki && venv/bin/pytest tests/test_auth_store.py -v 2>&1 | head -15
```

Expected: `ModuleNotFoundError: No module named 'backend.auth_store'`

- [ ] **Step 3: Create `backend/auth_store.py`**

```python
"""
SQLite-backed user and token store.

DB at raw/auth/auth.sqlite. Two tables:
  users(email, role, created_at, created_by)
  tokens(token, user_email, created_at, expires_at, revoked)

lookup_token() returns None for revoked or expired tokens.
All callers are responsible for hashing/salting tokens before passing in —
tokens are stored as-is (SHA-256 hex digest is already non-reversible).
"""
from __future__ import annotations

import secrets
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from backend.config import RAW_DIR

AUTH_DIR = RAW_DIR / "auth"
AUTH_DB = AUTH_DIR / "auth.sqlite"

_SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    email       TEXT PRIMARY KEY,
    role        TEXT NOT NULL DEFAULT 'viewer',
    created_at  TEXT NOT NULL,
    created_by  TEXT
);

CREATE TABLE IF NOT EXISTS tokens (
    token       TEXT PRIMARY KEY,
    user_email  TEXT NOT NULL REFERENCES users(email) ON DELETE CASCADE,
    created_at  TEXT NOT NULL,
    expires_at  TEXT,
    revoked     INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_tokens_email   ON tokens(user_email);
CREATE INDEX IF NOT EXISTS idx_tokens_revoked ON tokens(revoked, expires_at);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@contextmanager
def _connect() -> Iterator[sqlite3.Connection]:
    AUTH_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(AUTH_DB), isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def init_schema() -> None:
    with _connect() as conn:
        conn.executescript(_SCHEMA)


# ── Users ─────────────────────────────────────────────────────────────────────

def create_user(
    email: str,
    role: str = "viewer",
    created_by: str | None = None,
) -> dict[str, Any]:
    init_schema()
    now = _now()
    with _connect() as conn:
        conn.execute(
            "INSERT INTO users (email, role, created_at, created_by) VALUES (?, ?, ?, ?)",
            (email, role, now, created_by),
        )
    return {"email": email, "role": role, "created_at": now, "created_by": created_by}


def get_user(email: str) -> dict[str, Any] | None:
    init_schema()
    with _connect() as conn:
        row = conn.execute(
            "SELECT email, role, created_at, created_by FROM users WHERE email = ?",
            (email,),
        ).fetchone()
    return dict(row) if row else None


def list_users() -> list[dict[str, Any]]:
    init_schema()
    with _connect() as conn:
        rows = conn.execute(
            "SELECT email, role, created_at, created_by FROM users ORDER BY created_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def delete_user(email: str) -> bool:
    init_schema()
    with _connect() as conn:
        cur = conn.execute("DELETE FROM users WHERE email = ?", (email,))
        return cur.rowcount > 0


# ── Tokens ────────────────────────────────────────────────────────────────────

def create_token(user_email: str, expires_at: str | None = None) -> str:
    """Generate a 32-char hex token and store it. Returns the raw token."""
    init_schema()
    token = secrets.token_hex(16)  # 32 hex chars
    now = _now()
    with _connect() as conn:
        conn.execute(
            "INSERT INTO tokens (token, user_email, created_at, expires_at, revoked) "
            "VALUES (?, ?, ?, ?, 0)",
            (token, user_email, now, expires_at),
        )
    return token


def lookup_token(token: str) -> dict[str, Any] | None:
    """Return user dict if token is valid (not revoked, not expired). Else None."""
    init_schema()
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT u.email, u.role, t.expires_at
            FROM tokens t
            JOIN users u ON t.user_email = u.email
            WHERE t.token = ? AND t.revoked = 0
            """,
            (token,),
        ).fetchone()
    if not row:
        return None
    expires = row["expires_at"]
    if expires:
        try:
            if date.fromisoformat(str(expires)) < date.today():
                return None
        except ValueError:
            pass
    return {"email": row["email"], "role": row["role"], "token": token}


def revoke_token(token: str) -> bool:
    init_schema()
    with _connect() as conn:
        cur = conn.execute(
            "UPDATE tokens SET revoked = 1 WHERE token = ?", (token,)
        )
        return cur.rowcount > 0


def list_tokens(user_email: str) -> list[dict[str, Any]]:
    init_schema()
    with _connect() as conn:
        rows = conn.execute(
            "SELECT token, user_email, created_at, expires_at, revoked "
            "FROM tokens WHERE user_email = ? ORDER BY created_at DESC",
            (user_email,),
        ).fetchall()
    return [dict(r) for r in rows]
```

- [ ] **Step 4: Create `migrations/002_auth_store.sql`** (DDL reference only — applied by auth_store.py)

```sql
-- Layer 2: auth store (applied automatically by backend/auth_store.py at startup)
-- This file is a reference copy only — do NOT run it manually.

CREATE TABLE IF NOT EXISTS users (
    email       TEXT PRIMARY KEY,
    role        TEXT NOT NULL DEFAULT 'viewer',
    created_at  TEXT NOT NULL,
    created_by  TEXT
);

CREATE TABLE IF NOT EXISTS tokens (
    token       TEXT PRIMARY KEY,
    user_email  TEXT NOT NULL REFERENCES users(email) ON DELETE CASCADE,
    created_at  TEXT NOT NULL,
    expires_at  TEXT,
    revoked     INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_tokens_email   ON tokens(user_email);
CREATE INDEX IF NOT EXISTS idx_tokens_revoked ON tokens(revoked, expires_at);
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
venv/bin/pytest tests/test_auth_store.py -v
```

Expected: all 7 tests PASS

- [ ] **Step 6: Commit**

```bash
git add backend/auth_store.py migrations/002_auth_store.sql tests/test_auth_store.py
git commit -m "feat(auth-store): SQLite-backed user and token management"
```

---

## Task 2: Thread auth_store into `lookup_user_by_token()`

**Files:**
- Modify: `backend/config.py`
- Modify: `tests/test_auth.py`

- [ ] **Step 1: Write failing test**

Add to `tests/test_auth.py`:

```python
def test_lookup_prefers_auth_store_over_toml(tmp_path, monkeypatch):
    """When auth.sqlite has a valid token, TOML is not consulted."""
    import importlib
    import backend.auth_store as auth_module
    auth_dir = tmp_path / "raw" / "auth"
    auth_dir.mkdir(parents=True)
    db = auth_dir / "auth.sqlite"
    monkeypatch.setattr(auth_module, "AUTH_DB", db, raising=False)
    monkeypatch.setattr(auth_module, "AUTH_DIR", auth_dir, raising=False)
    importlib.reload(auth_module)

    auth_module.create_user("store_user@example.com", role="viewer")
    token = auth_module.create_token("store_user@example.com")

    # TOML has no such token
    with patch("backend.config._load_users", return_value={}):
        result = lookup_user_by_token(token)

    assert result is not None
    assert result["email"] == "store_user@example.com"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
venv/bin/pytest tests/test_auth.py::test_lookup_prefers_auth_store_over_toml -v
```

Expected: FAIL — `lookup_user_by_token` returns `None` because auth_store is not consulted

- [ ] **Step 3: Update `lookup_user_by_token()` in `backend/config.py`**

Replace the existing `lookup_user_by_token()` function with a version that checks auth_store first:

```python
def lookup_user_by_token(token: str) -> dict | None:
    # Check SQLite auth store first (Layer 2 users)
    try:
        from backend import auth_store
        result = auth_store.lookup_token(token)
        if result is not None:
            return result
    except Exception:
        pass  # auth_store unavailable or DB not yet initialized — fall through to TOML

    # Fall back to TOML (Layer 1 / migration compatibility)
    for _name, user in _load_users().items():
        if user.get("token") != token:
            continue
        expires = user.get("expires_at")
        if expires:
            try:
                if date.fromisoformat(str(expires)) < date.today():
                    return None
            except ValueError:
                pass
        return user
    return None
```

- [ ] **Step 4: Run all auth tests**

```bash
venv/bin/pytest tests/test_auth.py tests/test_auth_store.py -v
```

Expected: all tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/config.py tests/test_auth.py
git commit -m "feat(config): lookup_user_by_token checks auth_store first, TOML fallback"
```

---

## Task 3: Conversation context threading in `DeepQueryProvider`

**Files:**
- Modify: `backend/providers/deep_query.py`

- [ ] **Step 1: Update `generate_with_tools()` to accept prior messages**

In `backend/providers/deep_query.py`, update the method signature and the first line that builds `messages`:

Current:
```python
def generate_with_tools(
    self,
    system_prompt: str,
    user_message: str,
    tool_registry: ToolRegistry,
    max_rounds: int = _MAX_ROUNDS_ABSOLUTE,
) -> DeepProviderResult:
    max_rounds = min(max_rounds, _MAX_ROUNDS_ABSOLUTE)
    messages: list[dict] = [{"role": "user", "content": user_message}]
```

Replace with:
```python
def generate_with_tools(
    self,
    system_prompt: str,
    user_message: str,
    tool_registry: ToolRegistry,
    max_rounds: int = _MAX_ROUNDS_ABSOLUTE,
    prior_messages: list[dict] | None = None,
) -> DeepProviderResult:
    max_rounds = min(max_rounds, _MAX_ROUNDS_ABSOLUTE)
    messages: list[dict] = list(prior_messages or []) + [
        {"role": "user", "content": user_message}
    ]
```

Everything else in the method is unchanged.

- [ ] **Step 2: Run existing tests to confirm nothing broke**

```bash
venv/bin/pytest tests/ -v -q
```

Expected: all tests pass

- [ ] **Step 3: Commit**

```bash
git add backend/providers/deep_query.py
git commit -m "feat(deep-query): add prior_messages param to generate_with_tools for conversation threading"
```

---

## Task 4: Load conversation context in `orchestrator.run_deep()`

**Files:**
- Modify: `backend/orchestrator.py`

- [ ] **Step 1: Add `_load_conversation_context()` helper and wire into `run_deep()`**

In `backend/orchestrator.py`, add the helper function after the imports and before `run()`:

```python
def _load_conversation_context(conversation_id: str, max_turns: int = 6) -> list[dict]:
    """Return last N user+assistant message pairs from conversation history.

    Capped at max_turns * 2 messages so context stays within ~12K tokens.
    """
    conv = conversation_store.get_conversation(conversation_id)
    if not conv:
        return []
    msgs = [m for m in conv.get("messages", []) if m["role"] in ("user", "assistant")]
    tail = msgs[-(max_turns * 2):]
    return [{"role": m["role"], "content": m["content"]} for m in tail]
```

In `run_deep()`, add `conversation_id: str | None = None` to the signature (after `role: str | None = None`):

```python
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
    user_role: str = "viewer",
    conversation_id: str | None = None,    # ← add this
) -> OrchestratorResult:
```

In the body of `run_deep()`, load prior context before calling `provider.generate_with_tools()`:

```python
# Load prior conversation context (max 6 turns = 12 messages)
history = _load_conversation_context(conversation_id) if conversation_id else []

# Pass history to the tool loop
deep_result = provider.generate_with_tools(
    system_prompt=system_prompt,
    user_message=user_message,
    tool_registry=registry,
    prior_messages=history,
)
```

Also update `run()` to pass `conversation_id` through to `run_deep()`. Add it to the `run()` signature:

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
    user_role: str = "viewer",
    conversation_id: str | None = None,    # ← add this
) -> OrchestratorResult:
    if mode == "claude-code":
        result = run_single_shot(question, mode, None, server, buid, functional_area, user_role)
        result.deep_search_used = False
        return result
    return run_deep(
        question, mode, claude_api_key, server, buid, functional_area,
        service, officeid, roomid, role, user_role, conversation_id,
    )
```

- [ ] **Step 2: Update `/query` in `api.py` to pass `conversation_id` to orchestrator**

In `backend/api.py`, update the `orchestrator.run()` call inside `query()` to pass `conversation_id`:

```python
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
    conversation_id=conversation_id,    # ← add this
)
```

- [ ] **Step 3: Run existing tests to confirm nothing broke**

```bash
venv/bin/pytest tests/ -v -q
```

Expected: all tests pass

- [ ] **Step 4: Manual smoke test (requires running backend)**

Start the backend and send two queries:

```bash
# Query 1 — get a conversation_id
curl -s -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <TOKEN>" \
  -d '{"question": "What is visitor management?", "mode": "api", "server": "com"}' \
  | python -m json.tool | grep conversation_id
# Note the conversation_id from the response

# Query 2 — follow-up in the same conversation
curl -s -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <TOKEN>" \
  -d '{"question": "What are the known issues with OTP?", "mode": "api", "server": "com", "conversation_id": "<ID from above>"}' \
  | python -m json.tool | grep answer_text
# The answer should reference visitor management OTP context from the prior turn
```

- [ ] **Step 5: Commit**

```bash
git add backend/orchestrator.py backend/api.py
git commit -m "feat(orchestrator): load prior conversation turns into deep-search tool loop"
```

---

## Task 5: Admin token provisioning endpoints

**Files:**
- Modify: `backend/api.py`
- Modify: `tests/test_conversations.py` (REST endpoint tests for new routes)

- [ ] **Step 1: Write failing tests for the new endpoints**

Add a new test file `tests/test_admin_users.py`:

```python
# tests/test_admin_users.py
import importlib
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch


@pytest.fixture
def admin_client(tmp_path, monkeypatch):
    """TestClient with admin auth and fresh auth_store."""
    import backend.auth_store as auth_module
    auth_dir = tmp_path / "raw" / "auth"
    auth_dir.mkdir(parents=True)
    monkeypatch.setattr(auth_module, "AUTH_DB", auth_dir / "auth.sqlite", raising=False)
    monkeypatch.setattr(auth_module, "AUTH_DIR", auth_dir, raising=False)
    importlib.reload(auth_module)

    # Patch lookup_user_by_token so admin Bearer token works
    admin_user = {"email": "admin@example.com", "role": "admin", "token": "admin-token"}
    from backend import api as api_module
    importlib.reload(api_module)
    client = TestClient(api_module.app)

    # Patch _get_user to return admin for "admin-token"
    with patch("backend.config.lookup_user_by_token") as mock_lookup:
        mock_lookup.side_effect = lambda t: admin_user if t == "admin-token" else None
        yield client, auth_module


def test_create_user_and_token(admin_client):
    client, _ = admin_client
    r = client.post(
        "/admin/users",
        json={"email": "newuser@example.com", "role": "contributor"},
        headers={"Authorization": "Bearer admin-token"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["email"] == "newuser@example.com"
    assert "token" in data


def test_list_users(admin_client):
    client, as_ = admin_client
    as_.create_user("user1@example.com", role="viewer")
    r = client.get("/admin/users", headers={"Authorization": "Bearer admin-token"})
    assert r.status_code == 200
    assert any(u["email"] == "user1@example.com" for u in r.json()["users"])


def test_delete_user(admin_client):
    client, as_ = admin_client
    as_.create_user("todelete@example.com", role="viewer")
    r = client.delete(
        "/admin/users/todelete@example.com",
        headers={"Authorization": "Bearer admin-token"},
    )
    assert r.status_code == 200
    assert r.json()["deleted"] is True


def test_revoke_token(admin_client):
    client, as_ = admin_client
    as_.create_user("trevoke@example.com", role="viewer")
    token = as_.create_token("trevoke@example.com")
    r = client.delete(
        f"/admin/tokens/{token}",
        headers={"Authorization": "Bearer admin-token"},
    )
    assert r.status_code == 200
    assert as_.lookup_token(token) is None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
venv/bin/pytest tests/test_admin_users.py -v 2>&1 | head -20
```

Expected: `404 Not Found` for `/admin/users` endpoint

- [ ] **Step 3: Add admin user management endpoints to `backend/api.py`**

Add these Pydantic models near the other models in `api.py`:

```python
class CreateUserRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=200)
    role: Literal["viewer", "contributor", "admin"] = "viewer"
    expires_at: str | None = Field(default=None)


class RevokeTokenRequest(BaseModel):
    token: str
```

Add these endpoints (place with the other `/admin/*` endpoints):

```python
@app.post("/admin/users")
def admin_create_user(
    req: CreateUserRequest,
    _admin: dict = Depends(_require_admin),
):
    """Create a user and issue their first token. Returns the token once (not stored in plaintext)."""
    from backend import auth_store
    # Idempotent: if user already exists, just issue a new token
    if not auth_store.get_user(req.email):
        auth_store.create_user(
            req.email,
            role=req.role,
            created_by=_admin.get("email"),
        )
    token = auth_store.create_token(req.email, expires_at=req.expires_at)
    return {
        "email": req.email,
        "role": req.role,
        "token": token,
        "expires_at": req.expires_at,
        "note": "Store this token securely — it will not be shown again.",
    }


@app.get("/admin/users")
def admin_list_users(_admin: dict = Depends(_require_admin)):
    from backend import auth_store
    return {"users": auth_store.list_users()}


@app.delete("/admin/users/{email:path}")
def admin_delete_user(email: str, _admin: dict = Depends(_require_admin)):
    from backend import auth_store
    deleted = auth_store.delete_user(email)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"User not found: {email}")
    return {"deleted": True, "email": email}


@app.delete("/admin/tokens/{token}")
def admin_revoke_token(token: str, _admin: dict = Depends(_require_admin)):
    from backend import auth_store
    revoked = auth_store.revoke_token(token)
    if not revoked:
        raise HTTPException(status_code=404, detail="Token not found")
    return {"revoked": True}
```

- [ ] **Step 4: Run all tests**

```bash
venv/bin/pytest tests/ -v -q
```

Expected: all tests pass

- [ ] **Step 5: Add `.gitignore` entry for auth.sqlite**

```bash
echo "raw/auth/" >> .gitignore
git add .gitignore
```

- [ ] **Step 6: Commit**

```bash
git add backend/api.py tests/test_admin_users.py .gitignore
git commit -m "feat(api): admin user/token provisioning endpoints — POST /admin/users, DELETE /admin/users/{email}, DELETE /admin/tokens/{token}"
```

---

## Task 6: Layer 2 verification

- [ ] **Step 1: Run full test suite**

```bash
venv/bin/pytest tests/ -v
```

Expected: all tests pass

- [ ] **Step 2: Security checklist**

Manually verify:
- [ ] `POST /admin/users` returns 403 for a contributor-role token
- [ ] Deleting a user in auth_store makes their token return 401 immediately (token revoked via cascade)
- [ ] `raw/auth/auth.sqlite` is in `.gitignore` — confirm with `git status`
- [ ] Multi-turn test (eval question 20): "What is visitor management?" → follow-up "What are the known issues with OTP?" — second answer references context from first

- [ ] **Step 3: Final Layer 2 commit**

```bash
git add -A
git commit -m "feat(layer2): Layer 2 complete — conversation threading + SQLite token provisioning"
```
