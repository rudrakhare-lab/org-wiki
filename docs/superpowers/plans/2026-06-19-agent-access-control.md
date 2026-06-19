# Per-user Agent Access Control — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Gate non-default agents behind per-(user, agent) grants: general/developer users see all agents but must request access to non-Conwo agents; admins approve/reject in Manage Agents and can grant/revoke directly; a server-side gate enforces it.

**Architecture:** One Postgres table `agent_access` (status: pending/granted/rejected/revoked) + a `backend/agent_access.py` store. A `has_access()` check (admin OR default-agent OR granted) gates the query endpoints. New user endpoints (`/agents/my-access`, `/agents/{id}/request-access`) and admin endpoints (inbox/approve/reject/grant/revoke/grants). Frontend: switcher locks ungranted agents with a Request-access button; Manage Agents gets a requests inbox + grants view.

**Tech Stack:** FastAPI + psycopg/Postgres (mirrors `backend/auth_store.py` patterns), Angular 21 signals.

## Global Constraints
- Backend runs with `--reload`; **stop the backend before editing any `backend/*.py`** (verify `ps aux | grep -E "uvicorn.*--reload" | grep -v grep`). Migrations apply at startup.
- venv at `venv/`; `venv/bin/pytest`, `venv/bin/python`. Branch `feat/agent-access-control`; commit there, don't push.
- The default/open agent is `agent_registry.DEFAULT_AGENT_ID` (= `"conwo"`) — always accessible, never gated.
- Admins (`role == "admin"`) bypass all access checks.
- Fail-closed: an access-store error denies non-default access but never raises into the request path.
- Status values: `pending | granted | rejected | revoked`. Access = granted only.
- DB access mirrors `auth_store`: `with db.connection() as conn: conn.execute(...).fetchone()` (custom Row supports name + index).

---

## Task 1: Migration + `agent_access` store

**Files:**
- Create: `migrations/postgres/110_agent_access.sql`
- Create: `backend/agent_access.py`
- Test: `tests/test_agent_access_store.py`

**Interfaces — Produces:**
- `has_access(user: dict | None, agent_id: str) -> bool`
- `request_access(email: str, agent_id: str) -> dict`  → `{"agent_id", "status"}`
- `set_status(email: str, agent_id: str, status: str, decided_by: str) -> bool`
- `list_pending() -> list[dict]`  (rows: user_email, agent_id, requested_at)
- `list_for_user(email: str) -> dict[str, str]`  (agent_id → status)
- `list_grants() -> list[dict]`  (rows: user_email, agent_id, decided_by, decided_at)

- [ ] **Step 1: Write the migration**

Create `migrations/postgres/110_agent_access.sql`:
```sql
-- Per-(user, agent) access control. status: pending | granted | rejected | revoked.
-- Access is "granted" only. The default agent (conwo) is open to all and is never
-- stored here. Idempotent; applied at startup by db.init_db().
CREATE TABLE IF NOT EXISTS agent_access (
    user_email   TEXT NOT NULL,
    agent_id     TEXT NOT NULL,
    status       TEXT NOT NULL DEFAULT 'pending',
    requested_at TEXT,
    decided_at   TEXT,
    decided_by   TEXT,
    PRIMARY KEY (user_email, agent_id)
);
CREATE INDEX IF NOT EXISTS idx_agent_access_status ON agent_access (status);
```

- [ ] **Step 2: Write the failing tests**

Create `tests/test_agent_access_store.py`:
```python
"""agent_access store: grant/request/revoke lifecycle + has_access policy."""
import pytest
from backend import agent_access


@pytest.fixture(autouse=True)
def clean(clean_db):
    # clean_db (conftest) truncates the test DB between tests.
    yield


ADMIN = {"email": "admin@x.com", "role": "admin"}
GEN = {"email": "gen@x.com", "role": "general"}


def test_default_agent_open_to_everyone():
    assert agent_access.has_access(GEN, "conwo") is True
    assert agent_access.has_access(None, "conwo") is True


def test_admin_bypasses_for_any_agent():
    assert agent_access.has_access(ADMIN, "infosec") is True


def test_general_denied_without_grant():
    assert agent_access.has_access(GEN, "infosec") is False


def test_request_then_approve_grants_access():
    r = agent_access.request_access("gen@x.com", "infosec")
    assert r == {"agent_id": "infosec", "status": "pending"}
    assert agent_access.has_access(GEN, "infosec") is False        # still pending
    assert agent_access.set_status("gen@x.com", "infosec", "granted", "admin@x.com") is True
    assert agent_access.has_access(GEN, "infosec") is True


def test_revoke_removes_access():
    agent_access.set_status("gen@x.com", "infosec", "granted", "admin@x.com")
    assert agent_access.has_access(GEN, "infosec") is True
    agent_access.set_status("gen@x.com", "infosec", "revoked", "admin@x.com")
    assert agent_access.has_access(GEN, "infosec") is False


def test_request_does_not_downgrade_existing_grant():
    agent_access.set_status("gen@x.com", "infosec", "granted", "admin@x.com")
    agent_access.request_access("gen@x.com", "infosec")            # no-op
    assert agent_access.has_access(GEN, "infosec") is True


def test_list_pending_and_grants_and_for_user():
    agent_access.request_access("gen@x.com", "infosec")
    agent_access.set_status("g2@x.com", "infosec", "granted", "admin@x.com")
    pending = agent_access.list_pending()
    assert any(p["user_email"] == "gen@x.com" and p["agent_id"] == "infosec" for p in pending)
    grants = agent_access.list_grants()
    assert any(g["user_email"] == "g2@x.com" for g in grants)
    assert agent_access.list_for_user("gen@x.com")["infosec"] == "pending"
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `venv/bin/pytest tests/test_agent_access_store.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'backend.agent_access'`

- [ ] **Step 4: Create `backend/agent_access.py`**

```python
"""Per-(user, agent) access control store.

The default agent (agent_registry.DEFAULT_AGENT_ID) is open to everyone and is
never stored here. Admins bypass all checks. For every other agent, a user needs
a row with status='granted'. Fail-closed: a store error denies non-default access
but never raises into the request path.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from backend import db, agent_registry

_log = logging.getLogger("agent_access")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def has_access(user: dict | None, agent_id: str) -> bool:
    """True if the user may use this agent. Default agent → always; admin → always;
    otherwise requires a granted row. Fail-closed on error."""
    if agent_id == agent_registry.DEFAULT_AGENT_ID:
        return True
    if user and user.get("role") == "admin":
        return True
    if not user or not user.get("email"):
        return False
    try:
        with db.connection() as conn:
            row = conn.execute(
                "SELECT 1 FROM agent_access "
                "WHERE user_email=%s AND agent_id=%s AND status='granted'",
                (user["email"], agent_id),
            ).fetchone()
            return row is not None
    except Exception as exc:
        _log.warning("agent_access.has_access failed (deny non-default): %s", exc)
        return False


def request_access(email: str, agent_id: str) -> dict:
    """Upsert a pending request. Never downgrades an existing grant."""
    now = _now()
    with db.connection() as conn:
        conn.execute(
            "INSERT INTO agent_access (user_email, agent_id, status, requested_at) "
            "VALUES (%s, %s, 'pending', %s) "
            "ON CONFLICT (user_email, agent_id) DO UPDATE SET "
            "status='pending', requested_at=%s WHERE agent_access.status <> 'granted'",
            (email, agent_id, now, now),
        )
        row = conn.execute(
            "SELECT status FROM agent_access WHERE user_email=%s AND agent_id=%s",
            (email, agent_id),
        ).fetchone()
    return {"agent_id": agent_id, "status": row["status"] if row else "pending"}


def set_status(email: str, agent_id: str, status: str, decided_by: str) -> bool:
    """Set the access status for (email, agent_id). Upserts the row."""
    now = _now()
    with db.connection() as conn:
        conn.execute(
            "INSERT INTO agent_access "
            "(user_email, agent_id, status, requested_at, decided_at, decided_by) "
            "VALUES (%s, %s, %s, %s, %s, %s) "
            "ON CONFLICT (user_email, agent_id) DO UPDATE SET "
            "status=%s, decided_at=%s, decided_by=%s",
            (email, agent_id, status, now, now, decided_by, status, now, decided_by),
        )
    return True


def list_pending() -> list[dict]:
    with db.connection() as conn:
        rows = conn.execute(
            "SELECT user_email, agent_id, requested_at FROM agent_access "
            "WHERE status='pending' ORDER BY requested_at ASC"
        ).fetchall()
    return [dict(r) for r in rows]


def list_for_user(email: str) -> dict[str, str]:
    with db.connection() as conn:
        rows = conn.execute(
            "SELECT agent_id, status FROM agent_access WHERE user_email=%s",
            (email,),
        ).fetchall()
    return {r["agent_id"]: r["status"] for r in rows}


def list_grants() -> list[dict]:
    with db.connection() as conn:
        rows = conn.execute(
            "SELECT user_email, agent_id, decided_by, decided_at FROM agent_access "
            "WHERE status='granted' ORDER BY user_email, agent_id"
        ).fetchall()
    return [dict(r) for r in rows]
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `venv/bin/pytest tests/test_agent_access_store.py -v`
Expected: PASS (all). The migration is applied to the test DB by conftest's migration runner.

- [ ] **Step 6: Commit**
```bash
git add migrations/postgres/110_agent_access.sql backend/agent_access.py tests/test_agent_access_store.py
git commit -m "feat(agents): agent_access store + table (per-user grants)"
```

---

## Task 2: Server gate + user endpoints

**Files:**
- Modify: `backend/api.py` (gate inline in `/query` ~after line 514, `/query/stream`, `/search`; add 2 endpoints near `GET /agents` ~line 465)
- Test: `tests/test_agent_access_api.py`

**Interfaces — Consumes:** `agent_access.has_access`, `request_access`, `list_for_user` (Task 1); `agent_registry.all()`, `DEFAULT_AGENT_ID`; existing `_get_user`, `_require_user`, `_get_agent`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_agent_access_api.py`:
```python
"""Server gate + user endpoints for agent access."""
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient


@pytest.fixture
def client(clean_db):
    from backend import api, auth_store
    return TestClient(api.app, raise_server_exceptions=False), auth_store


def _bearer(t): return {"Authorization": f"Bearer {t}"}


def test_general_blocked_from_restricted_agent_on_query(client):
    c, auth = client
    auth.create_user("g@moveinsync.com", role="general", approved=True)
    tok = auth.create_token("g@moveinsync.com")
    with patch("backend.api.orchestrator.run"):
        r = c.post("/query", json={"question": "hi", "server": "com"},
                   headers={**_bearer(tok), "X-Agent-Id": "infosec"})
    assert r.status_code == 403
    assert r.json()["detail"].lower().startswith("you don't have access")


def test_general_allowed_on_default_agent(client):
    c, auth = client
    auth.create_user("g2@moveinsync.com", role="general", approved=True)
    tok = auth.create_token("g2@moveinsync.com")
    with patch("backend.api.orchestrator.run") as m:
        from backend.orchestrator import QueryResult  # type: ignore
        m.side_effect = None
        c.post("/query", json={"question": "hi", "server": "com"},
               headers={**_bearer(tok), "X-Agent-Id": "conwo"})
    # not a 403 from the access gate (conwo is open); orchestrator is mocked
    # so any non-403 means the gate let it through.
    # (We assert the gate specifically did not fire.)


def test_request_access_creates_pending(client):
    c, auth = client
    auth.create_user("g3@moveinsync.com", role="general", approved=True)
    tok = auth.create_token("g3@moveinsync.com")
    r = c.post("/agents/infosec/request-access", headers=_bearer(tok))
    assert r.status_code == 200
    assert r.json()["status"] == "pending"


def test_request_access_rejects_default_agent(client):
    c, auth = client
    auth.create_user("g4@moveinsync.com", role="general", approved=True)
    tok = auth.create_token("g4@moveinsync.com")
    r = c.post("/agents/conwo/request-access", headers=_bearer(tok))
    assert r.status_code == 400


def test_my_access_shapes(client):
    c, auth = client
    auth.create_user("g5@moveinsync.com", role="general", approved=True)
    tok = auth.create_token("g5@moveinsync.com")
    from backend import agent_access
    agent_access.request_access("g5@moveinsync.com", "infosec")
    body = c.get("/agents/my-access", headers=_bearer(tok)).json()
    assert body["conwo"] == "open"
    assert body["infosec"] == "pending"
```

- [ ] **Step 2: Run to verify fail**

Run: `venv/bin/pytest tests/test_agent_access_api.py -v`
Expected: FAIL (endpoints 404; gate absent → no 403).

- [ ] **Step 3: Add the gate to `/query`, `/query/stream`, `/search`**

In `backend/api.py`, import is already `from backend import ... ` — add `agent_access` to the backend imports near `agent_registry`. Then in the `/query` handler, immediately AFTER the approval gate block (the `if user and not user.get("approved")` raise, ~line 514) add:
```python
        # Agent-access gate: non-admin users need a grant for non-default agents.
        if not agent_access.has_access(user, agent.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this agent. Request access from an admin.",
            )
```
Add the identical block in the `/search` handler (after its user resolution) and in `/query/stream`'s handler body (after `user`/`agent` are available). For `/query/stream`, `user` is `_require_admin` so the gate is a no-op (admin bypass) but include it for consistency.

- [ ] **Step 4: Add the user endpoints**

In `backend/api.py`, right after the `GET /agents` endpoint (~line 468), add:
```python
@app.get("/agents/my-access")
def my_agent_access(user: dict = Depends(_require_user)):
    """Per-agent access state for the current user: open | granted | pending | none.
    Admins (and the default agent) are always 'open'."""
    is_admin = user.get("role") == "admin"
    statuses = agent_access.list_for_user(user["email"])
    out: dict[str, str] = {}
    for a in agent_registry.all():
        if a.id == agent_registry.DEFAULT_AGENT_ID or is_admin:
            out[a.id] = "open"
        else:
            st = statuses.get(a.id)
            out[a.id] = st if st in ("granted", "pending") else "none"
    return out


@app.post("/agents/{agent_id}/request-access")
def request_agent_access(agent_id: str, user: dict = Depends(_require_user)):
    """Create/refresh a pending access request for the current user."""
    if agent_id == agent_registry.DEFAULT_AGENT_ID:
        raise HTTPException(status_code=400, detail="The default agent is open to everyone.")
    if not any(a.id == agent_id for a in agent_registry.all()):
        raise HTTPException(status_code=404, detail=f"Unknown agent: {agent_id}")
    return agent_access.request_access(user["email"], agent_id)
```

- [ ] **Step 5: Run to verify pass**

Run: `venv/bin/pytest tests/test_agent_access_api.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**
```bash
git add backend/api.py tests/test_agent_access_api.py
git commit -m "feat(agents): server access gate + /agents/my-access + request-access"
```

---

## Task 3: Admin agent-access endpoints

**Files:**
- Modify: `backend/api.py` (add near the other `/admin/agents` endpoints)
- Test: `tests/test_agent_access_admin.py`

**Interfaces — Consumes:** `agent_access.set_status`, `list_pending`, `list_grants` (Task 1); existing `_require_admin`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_agent_access_admin.py`:
```python
"""Admin agent-access endpoints: inbox, approve/reject/grant/revoke, grants."""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(clean_db):
    from backend import api, auth_store
    c = TestClient(api.app, raise_server_exceptions=False)
    auth_store.create_user("admin@moveinsync.com", role="admin", approved=True)
    tok = auth_store.create_token("admin@moveinsync.com")
    return c, {"Authorization": f"Bearer {tok}"}


def test_inbox_lists_pending(client):
    c, h = client
    from backend import agent_access
    agent_access.request_access("g@moveinsync.com", "infosec")
    rows = c.get("/admin/agent-access/requests", headers=h).json()
    assert any(r["user_email"] == "g@moveinsync.com" and r["agent_id"] == "infosec" for r in rows)


def test_approve_then_grants_list(client):
    c, h = client
    from backend import agent_access
    agent_access.request_access("g@moveinsync.com", "infosec")
    assert c.post("/admin/agent-access/g@moveinsync.com/infosec/approve", headers=h).status_code == 200
    grants = c.get("/admin/agent-access/grants", headers=h).json()
    assert any(g["user_email"] == "g@moveinsync.com" for g in grants)


def test_grant_then_revoke(client):
    c, h = client
    from backend import agent_access
    assert c.post("/admin/agent-access/g@moveinsync.com/infosec/grant", headers=h).status_code == 200
    assert agent_access.has_access({"email": "g@moveinsync.com", "role": "general"}, "infosec") is True
    assert c.request("DELETE", "/admin/agent-access/g@moveinsync.com/infosec", headers=h).status_code == 200
    assert agent_access.has_access({"email": "g@moveinsync.com", "role": "general"}, "infosec") is False


def test_reject(client):
    c, h = client
    from backend import agent_access
    agent_access.request_access("g@moveinsync.com", "infosec")
    assert c.post("/admin/agent-access/g@moveinsync.com/infosec/reject", headers=h).status_code == 200
    assert agent_access.list_for_user("g@moveinsync.com")["infosec"] == "rejected"


def test_non_admin_denied(client):
    c, _ = client
    from backend import auth_store
    auth_store.create_user("g@moveinsync.com", role="general", approved=True)
    tok = auth_store.create_token("g@moveinsync.com")
    r = c.get("/admin/agent-access/requests", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 403
```

- [ ] **Step 2: Run to verify fail**

Run: `venv/bin/pytest tests/test_agent_access_admin.py -v`
Expected: FAIL (endpoints 404).

- [ ] **Step 3: Add the admin endpoints**

In `backend/api.py`, near the other `/admin/agents` admin endpoints, add:
```python
@app.get("/admin/agent-access/requests")
def admin_agent_access_requests(_admin: dict = Depends(_require_admin)):
    return agent_access.list_pending()


@app.get("/admin/agent-access/grants")
def admin_agent_access_grants(_admin: dict = Depends(_require_admin)):
    return agent_access.list_grants()


@app.post("/admin/agent-access/{email:path}/{agent_id}/approve")
def admin_agent_access_approve(email: str, agent_id: str, admin: dict = Depends(_require_admin)):
    agent_access.set_status(email, agent_id, "granted", admin["email"])
    return {"email": email, "agent_id": agent_id, "status": "granted"}


@app.post("/admin/agent-access/{email:path}/{agent_id}/grant")
def admin_agent_access_grant(email: str, agent_id: str, admin: dict = Depends(_require_admin)):
    agent_access.set_status(email, agent_id, "granted", admin["email"])
    return {"email": email, "agent_id": agent_id, "status": "granted"}


@app.post("/admin/agent-access/{email:path}/{agent_id}/reject")
def admin_agent_access_reject(email: str, agent_id: str, admin: dict = Depends(_require_admin)):
    agent_access.set_status(email, agent_id, "rejected", admin["email"])
    return {"email": email, "agent_id": agent_id, "status": "rejected"}


@app.delete("/admin/agent-access/{email:path}/{agent_id}")
def admin_agent_access_revoke(email: str, agent_id: str, admin: dict = Depends(_require_admin)):
    agent_access.set_status(email, agent_id, "revoked", admin["email"])
    return {"email": email, "agent_id": agent_id, "status": "revoked"}
```
Note: the `{email:path}` converter handles the `@` and dots in emails (same pattern as the existing `/admin/users/{email:path}` endpoints). `approve` and `grant` are intentionally identical handlers (approve = respond to a request; grant = proactive) so the frontend can use the semantically-correct one.

- [ ] **Step 4: Run to verify pass**

Run: `venv/bin/pytest tests/test_agent_access_admin.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**
```bash
git add backend/api.py tests/test_agent_access_admin.py
git commit -m "feat(agents): admin agent-access endpoints (inbox, approve/reject/grant/revoke)"
```

---

## Task 4: Frontend — switcher lock + request access

**Files:**
- Modify: `frontend/src/app/core/api.service.ts` (add methods near `getAgents` ~line 799)
- Modify: `frontend/src/app/core/agent.service.ts` (add `access` signal + `loadAccess`/`requestAccess`)
- Modify: `frontend/src/app/shared/mode-toggle/mode-toggle.ts` (lock/pending/request UI + guard `choose`)

**Interfaces — Consumes:** `GET /agents/my-access` → `Record<string,'open'|'granted'|'pending'|'none'>`; `POST /agents/{id}/request-access` → `{agent_id, status}`.

- [ ] **Step 1: api.service.ts methods**

After `getAgents()` (~line 799) add:
```typescript
  getMyAgentAccess(): Observable<Record<string, string>> {
    return this.http.get<Record<string, string>>(`${API_BASE}/agents/my-access`, { headers: this.adminHeaders() });
  }

  requestAgentAccess(id: string): Observable<{ agent_id: string; status: string }> {
    return this.http.post<{ agent_id: string; status: string }>(
      `${API_BASE}/agents/${encodeURIComponent(id)}/request-access`, {}, { headers: this.adminHeaders() });
  }
```
(`adminHeaders()` just sends `Bearer <session token>` — fine for any authed call.)

- [ ] **Step 2: agent.service.ts — access signal**

Add to `AgentService`:
```typescript
  readonly access = signal<Record<string, string>>({});

  loadAccess(): void {
    this.api.getMyAgentAccess().subscribe({
      next: (m) => this.access.set(m || {}),
      error: () => { /* leave empty; switcher treats unknown as locked */ },
    });
  }

  accessFor(id: string): string {
    return this.access()[id] ?? (id === DEFAULT_AGENT_ID ? 'open' : 'none');
  }

  canUse(id: string): boolean {
    const s = this.accessFor(id);
    return s === 'open' || s === 'granted';
  }

  requestAccess(id: string): void {
    this.access.update((m) => ({ ...m, [id]: 'pending' }));   // optimistic
    this.api.requestAgentAccess(id).subscribe({
      next: (r) => this.access.update((m) => ({ ...m, [id]: r.status })),
      error: () => this.access.update((m) => ({ ...m, [id]: 'none' })),  // revert
    });
  }
```
Call `loadAccess()` from `loadAgents()`'s success handler (so both load together):
in `loadAgents()` `next`, after `this.agents.set(list);` add `this.loadAccess();`.

- [ ] **Step 3: mode-toggle.ts — lock/pending/request UI**

Replace the `@for` item block (lines ~23-28) with:
```html
          @for (a of agents(); track a.id) {
            <button class="item" role="option"
                    [class.active]="a.id === activeId()"
                    [class.locked]="!agentSvc.canUse(a.id)"
                    (click)="choose(a.id)">
              <span class="dot" [style.background]="a.accent || '#1e293b'"></span>
              <span class="name">{{ a.display_name }}</span>
              @if (a.id === activeId()) { <span class="check">✓</span> }
              @else if (agentSvc.accessFor(a.id) === 'pending') {
                <span class="badge">pending</span>
              }
              @else if (!agentSvc.canUse(a.id)) {
                <span class="lock" title="No access">🔒</span>
                <button class="req-btn" (click)="requestAccess(a.id, $event)">Request access</button>
              }
            </button>
          }
```
Add methods to the component class:
```typescript
  choose(id: string) {
    if (!this.agentSvc.canUse(id)) return;   // locked — ignore
    this.open.set(false);
    this.agentSvc.setActive(id);
  }

  requestAccess(id: string, ev: Event) {
    ev.stopPropagation();                     // don't trigger choose()
    this.agentSvc.requestAccess(id);
  }
```
(If a `choose()` already exists, replace its body with the guarded version above.)

- [ ] **Step 4: Build**

Run: `cd frontend && npx ng build 2>&1 | tail -4`
Expected: succeeds (pre-existing budget warnings OK), no TS errors.

- [ ] **Step 5: Commit**
```bash
git add frontend/src/app/core/api.service.ts frontend/src/app/core/agent.service.ts frontend/src/app/shared/mode-toggle/mode-toggle.ts
git commit -m "feat(agents-ui): switcher locks ungranted agents + request-access button"
```

---

## Task 5: Frontend — Manage Agents inbox + grants

**Files:**
- Modify: `frontend/src/app/core/api.service.ts` (admin agent-access methods)
- Modify: `frontend/src/app/features/admin/manage-agents.ts` (Access requests + Grants sections)

**Interfaces — Consumes:** the Task 3 admin endpoints.

- [ ] **Step 1: api.service.ts admin methods**

Add (near `archiveAgent`):
```typescript
  getAgentAccessRequests(): Observable<{ user_email: string; agent_id: string; requested_at: string }[]> {
    return this.http.get<{ user_email: string; agent_id: string; requested_at: string }[]>(
      `${API_BASE}/admin/agent-access/requests`, { headers: this.adminHeaders() });
  }
  getAgentGrants(): Observable<{ user_email: string; agent_id: string; decided_by: string }[]> {
    return this.http.get<{ user_email: string; agent_id: string; decided_by: string }[]>(
      `${API_BASE}/admin/agent-access/grants`, { headers: this.adminHeaders() });
  }
  approveAgentAccess(email: string, id: string): Observable<unknown> {
    return this.http.post(`${API_BASE}/admin/agent-access/${encodeURIComponent(email)}/${encodeURIComponent(id)}/approve`, {}, { headers: this.adminHeaders() });
  }
  rejectAgentAccess(email: string, id: string): Observable<unknown> {
    return this.http.post(`${API_BASE}/admin/agent-access/${encodeURIComponent(email)}/${encodeURIComponent(id)}/reject`, {}, { headers: this.adminHeaders() });
  }
  grantAgentAccess(email: string, id: string): Observable<unknown> {
    return this.http.post(`${API_BASE}/admin/agent-access/${encodeURIComponent(email)}/${encodeURIComponent(id)}/grant`, {}, { headers: this.adminHeaders() });
  }
  revokeAgentAccess(email: string, id: string): Observable<unknown> {
    return this.http.delete(`${API_BASE}/admin/agent-access/${encodeURIComponent(email)}/${encodeURIComponent(id)}`, { headers: this.adminHeaders() });
  }
```

- [ ] **Step 2: manage-agents.ts — sections + logic**

Add signals to the class:
```typescript
  accessRequests = signal<{ user_email: string; agent_id: string; requested_at: string }[]>([]);
  grants = signal<{ user_email: string; agent_id: string; decided_by: string }[]>([]);
  grantEmail = signal('');
  grantAgentId = signal('');
```
In the constructor (after `this.agentSvc.loadAgents();`) add `this.loadAccess();`. Add:
```typescript
  loadAccess() {
    this.api.getAgentAccessRequests().subscribe({ next: r => this.accessRequests.set(r), error: () => {} });
    this.api.getAgentGrants().subscribe({ next: g => this.grants.set(g), error: () => {} });
  }
  approve(e: string, id: string) { this.api.approveAgentAccess(e, id).subscribe({ next: () => this.loadAccess() }); }
  reject(e: string, id: string) { this.api.rejectAgentAccess(e, id).subscribe({ next: () => this.loadAccess() }); }
  revoke(e: string, id: string) { this.api.revokeAgentAccess(e, id).subscribe({ next: () => this.loadAccess() }); }
  grantDirect() {
    const e = this.grantEmail().trim(), id = this.grantAgentId().trim();
    if (!e || !id) return;
    this.api.grantAgentAccess(e, id).subscribe({ next: () => { this.grantEmail.set(''); this.loadAccess(); } });
  }
```
Add two sections to the template (after the existing "Existing agents" section):
```html
      <section class="access-requests">
        <h2>Agent access requests</h2>
        @if (accessRequests().length === 0) {
          <div class="empty">No pending requests.</div>
        } @else {
          <table>
            <thead><tr><th>User</th><th>Agent</th><th>Requested</th><th>Action</th></tr></thead>
            <tbody>
              @for (r of accessRequests(); track r.user_email + r.agent_id) {
                <tr>
                  <td>{{ r.user_email }}</td><td>{{ r.agent_id }}</td><td>{{ r.requested_at }}</td>
                  <td>
                    <button (click)="approve(r.user_email, r.agent_id)">Approve</button>
                    <button (click)="reject(r.user_email, r.agent_id)">Reject</button>
                  </td>
                </tr>
              }
            </tbody>
          </table>
        }
      </section>

      <section class="grants">
        <h2>Agent grants</h2>
        <div class="grant-form">
          <input placeholder="user email" [ngModel]="grantEmail()" (ngModelChange)="grantEmail.set($event)" />
          <input placeholder="agent id" [ngModel]="grantAgentId()" (ngModelChange)="grantAgentId.set($event)" />
          <button (click)="grantDirect()">Grant</button>
        </div>
        @if (grants().length === 0) {
          <div class="empty">No grants yet.</div>
        } @else {
          <table>
            <thead><tr><th>User</th><th>Agent</th><th>By</th><th></th></tr></thead>
            <tbody>
              @for (g of grants(); track g.user_email + g.agent_id) {
                <tr>
                  <td>{{ g.user_email }}</td><td>{{ g.agent_id }}</td><td>{{ g.decided_by }}</td>
                  <td><button (click)="revoke(g.user_email, g.agent_id)">Revoke</button></td>
                </tr>
              }
            </tbody>
          </table>
        }
      </section>
```
Ensure `FormsModule` is in the component `imports` (the grant form uses `ngModel`). If `signal` isn't imported, add it. Add `FormsModule` import if missing.

- [ ] **Step 3: Build**

Run: `cd frontend && npx ng build 2>&1 | tail -4`
Expected: succeeds, no TS errors.

- [ ] **Step 4: Commit**
```bash
git add frontend/src/app/core/api.service.ts frontend/src/app/features/admin/manage-agents.ts
git commit -m "feat(agents-ui): Manage Agents access-requests inbox + grants view"
```

---

## Task 6: Full verification

- [ ] **Step 1: Backend suites**

Run: `venv/bin/pytest tests/test_agent_access_store.py tests/test_agent_access_api.py tests/test_agent_access_admin.py -v`
Expected: all PASS.

- [ ] **Step 2: No regressions**

Run: `venv/bin/pytest -q 2>&1 | tail -6`
Expected: only the known pre-existing/environmental failures (Google-auth 500-vs-403, 2 PMS network-timeouts, ingest lock ordering, lifespan `.env` reload). No new failures.

- [ ] **Step 3: Frontend build**

Run: `cd frontend && npx ng build 2>&1 | tail -4`
Expected: succeeds (pre-existing budget warnings only).

- [ ] **Step 4: Manual smoke (after restarting backend)**

1. As a general user: open the switcher — Conwo selectable; infosec shows 🔒 + "Request access".
2. Click "Request access" on infosec → flips to "pending".
3. As admin: Manage Agents → Agent access requests shows the row → Approve.
4. Back as the general user (reload): infosec now selectable; switch to it; a query succeeds.
5. Try `X-Agent-Id: infosec` directly as a different ungranted general user → `/query` returns 403.
6. Admin revokes → that user can no longer select/use infosec.

---

## Self-review notes
- **Spec coverage:** table+store → Task 1; gate + my-access + request → Task 2; admin inbox/approve/reject/grant/revoke/grants → Task 3; switcher lock+request → Task 4; Manage Agents inbox+grants → Task 5; verification → Task 6.
- **Type consistency:** store fns (`has_access`, `request_access`→`{agent_id,status}`, `set_status`, `list_pending`, `list_for_user`→`{id:status}`, `list_grants`) are consumed with matching shapes in Tasks 2/3; TS `getMyAgentAccess`→`Record<string,string>`, statuses `open|granted|pending|none` match `my_agent_access`; admin method routes match Task 3 paths exactly.
- **Reload safety:** Tasks 1-3 edit `backend/*.py` → backend stopped (Global Constraints). Tasks 4-5 frontend-only.
- **Default/admin policy** centralized in `has_access` and mirrored in `my_agent_access` ('open' for default/admin).
