# Admin Approvals/Users split + dev-only email login — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split the admin Users panel into a pending-only "Approvals" view and an approved-only "Users" view (approve sets role in one action), and add a dev-only email-login path gated by `CONWO_DEV_LOGIN` so the three roles + approval flow can be tested without real Google accounts.

**Architecture:** Backend adds (1) a `dev_login_enabled()` flag in `config.py`, (2) a combined approve-with-role on the existing `POST /admin/users/{email}/approve`, (3) `POST /auth/dev-login` + `GET /auth/config`, all mirroring existing patterns. Frontend reorganizes `admin-dashboard.ts` into two filtered sections and adds a dev-login box to `login.ts` shown only when `/auth/config` reports `dev_login=true`. No DB migration (uses existing `approved`/`role` columns; adds no schema).

**Tech Stack:** FastAPI + Pydantic (backend), psycopg/Postgres (`auth_store`), Angular 21 standalone components + signals (frontend), pytest with the `clean_db`/`rbac` fixtures (tests).

---

## CRITICAL PRE-FLIGHT (do before any Python edit)

The backend runs with `--reload`; a `.py` write triggers a uvicorn reload that rebuilds
the in-memory wiki index and can destroy state (project rule). **Confirm the backend is
stopped before editing any `backend/*.py` file.**

- [ ] **Step 0: Confirm backend stopped**

Run: `ps aux | grep -E "uvicorn|--reload" | grep -v grep || echo "STOPPED"`
Expected: `STOPPED` (no uvicorn process). If a process is shown, stop it before continuing.

---

## Task 1: Backend — `dev_login_enabled()` flag in config

**Files:**
- Modify: `backend/config.py` (add function near `local_claude_code_enabled`, after line ~135)
- Test: `tests/test_dev_login.py` (create)

- [ ] **Step 1: Write the failing test**

Create `tests/test_dev_login.py`:

```python
"""Dev-only email-login path: flag gating, provisioning, and prod-inert behavior."""
import importlib
import pytest
from fastapi.testclient import TestClient


def test_dev_login_enabled_flag(monkeypatch):
    import backend.config as config
    monkeypatch.delenv("CONWO_DEV_LOGIN", raising=False)
    importlib.reload(config)
    assert config.dev_login_enabled() is False
    monkeypatch.setenv("CONWO_DEV_LOGIN", "true")
    assert config.dev_login_enabled() is True
    monkeypatch.setenv("CONWO_DEV_LOGIN", "off")
    assert config.dev_login_enabled() is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv/bin/pytest tests/test_dev_login.py::test_dev_login_enabled_flag -v`
Expected: FAIL with `AttributeError: module 'backend.config' has no attribute 'dev_login_enabled'`

- [ ] **Step 3: Add the function**

In `backend/config.py`, after the `local_claude_code_enabled()` function (~line 135), add:

```python
def dev_login_enabled() -> bool:
    """
    True when the operator has explicitly enabled the dev-only email-login path
    via the CONWO_DEV_LOGIN env var.

    Lets test users sign in by typing an @moveinsync.com email (no Google), so the
    three roles and the approval flow can be exercised in dev. Must NOT be set on
    production — anyone who can reach the backend could mint a session for any
    @moveinsync.com email. Google OAuth remains the only prod login path.
    """
    return os.getenv("CONWO_DEV_LOGIN", "").strip().lower() in {
        "1", "true", "yes", "on"
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `venv/bin/pytest tests/test_dev_login.py::test_dev_login_enabled_flag -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/config.py tests/test_dev_login.py
git commit -m "feat(auth): add dev_login_enabled() config flag"
```

---

## Task 2: Backend — `GET /auth/config` (public) + `POST /auth/dev-login`

**Files:**
- Modify: `backend/api.py` (add models near `GoogleLoginResponse` ~line 359; add endpoints right after `google_login`/before `auth_me` ~line 1052)
- Test: `tests/test_dev_login.py` (extend)

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_dev_login.py`:

```python
@pytest.fixture
def dev_client(clean_db, monkeypatch):
    """TestClient with dev-login ON, against the isolated test DB."""
    monkeypatch.setenv("CONWO_DEV_LOGIN", "true")
    from backend import api as api_module
    from backend import auth_store
    client = TestClient(api_module.app, raise_server_exceptions=False)
    return client, auth_store


def test_auth_config_reports_flag(dev_client):
    client, _ = dev_client
    assert client.get("/auth/config").json() == {"dev_login": True}


def test_dev_login_provisions_general_unapproved(dev_client):
    client, auth = dev_client
    r = client.post("/auth/dev-login", json={"email": "general-test@moveinsync.com"})
    assert r.status_code == 200
    body = r.json()
    assert body["email"] == "general-test@moveinsync.com"
    assert body["role"] == "general"
    assert body["approved"] is False
    assert len(body["token"]) == 32
    u = auth.get_user("general-test@moveinsync.com")
    assert u["role"] == "general" and u["approved"] is False


def test_dev_login_rejects_non_domain_email(dev_client):
    client, _ = dev_client
    r = client.post("/auth/dev-login", json={"email": "outsider@gmail.com"})
    assert r.status_code == 403


def test_dev_login_disabled_returns_403(clean_db, monkeypatch):
    monkeypatch.delenv("CONWO_DEV_LOGIN", raising=False)
    from backend import api as api_module
    client = TestClient(api_module.app, raise_server_exceptions=False)
    assert client.get("/auth/config").json() == {"dev_login": False}
    r = client.post("/auth/dev-login", json={"email": "x@moveinsync.com"})
    assert r.status_code == 403
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `venv/bin/pytest tests/test_dev_login.py -v`
Expected: the 4 new tests FAIL (404 for `/auth/config` and `/auth/dev-login` — routes not defined)

- [ ] **Step 3: Add the request model**

In `backend/api.py`, immediately after the `GoogleLoginResponse` class (ends ~line 363), add:

```python
class DevLoginRequest(BaseModel):
    email: str
```

- [ ] **Step 4: Add the endpoints**

In `backend/api.py`, immediately after the `google_login` function (just before `@app.get("/auth/me")`, ~line 1052), add:

```python
@app.get("/auth/config")
def auth_config():
    """Public, unauthenticated. Tells the frontend whether the dev email-login box
    should render. False on prod (CONWO_DEV_LOGIN unset) — Google is the only path."""
    from backend import config
    return {"dev_login": config.dev_login_enabled()}


@app.post("/auth/dev-login", response_model=GoogleLoginResponse)
def dev_login(req: DevLoginRequest):
    """Dev-only email login, gated by CONWO_DEV_LOGIN. Mirrors google_login's
    provisioning exactly: a new email is created as general + unapproved, then must be
    approved by an admin. Returns 403 (inert) when the flag is off, so this route is
    a no-op in production."""
    from backend import config, auth_store
    if not config.dev_login_enabled():
        raise HTTPException(status_code=403, detail="Dev login is disabled.")
    email = req.email.strip().lower()
    if not email.endswith("@moveinsync.com"):
        raise HTTPException(
            status_code=403,
            detail="Only @moveinsync.com accounts can sign in.",
        )
    if not auth_store.get_user(email):
        auth_store.create_user(email, role="general", approved=False)
    user = auth_store.get_user(email)
    token = auth_store.create_token(email)
    return GoogleLoginResponse(
        token=token,
        email=email,
        name=email.split("@")[0],
        role=(user or {}).get("role", "general"),
        approved=bool((user or {}).get("approved", False)),
    )
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `venv/bin/pytest tests/test_dev_login.py -v`
Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add backend/api.py tests/test_dev_login.py
git commit -m "feat(auth): add GET /auth/config and dev-only POST /auth/dev-login"
```

---

## Task 3: Backend — combined approve-with-role

**Files:**
- Modify: `backend/api.py` (`admin_approve_user`, ~line 1151)
- Test: `tests/test_rbac_approval.py` (extend)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_rbac_approval.py`:

```python
def test_approve_with_role_sets_both(rbac):
    client, auth = rbac
    auth.create_user("admin@moveinsync.com", role="admin", approved=True)
    admin_tok = auth.create_token("admin@moveinsync.com")
    auth.create_user("p@moveinsync.com", role="general", approved=False)
    r = client.post("/admin/users/p@moveinsync.com/approve",
                    json={"role": "developer"}, headers=_bearer(admin_tok))
    assert r.status_code == 200
    u = auth.get_user("p@moveinsync.com")
    assert u["approved"] is True
    assert u["role"] == "developer"


def test_approve_without_role_keeps_role(rbac):
    client, auth = rbac
    auth.create_user("admin2@moveinsync.com", role="admin", approved=True)
    admin_tok = auth.create_token("admin2@moveinsync.com")
    auth.create_user("q@moveinsync.com", role="general", approved=False)
    r = client.post("/admin/users/q@moveinsync.com/approve",
                    json={}, headers=_bearer(admin_tok))
    assert r.status_code == 200
    u = auth.get_user("q@moveinsync.com")
    assert u["approved"] is True
    assert u["role"] == "general"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `venv/bin/pytest tests/test_rbac_approval.py::test_approve_with_role_sets_both tests/test_rbac_approval.py::test_approve_without_role_keeps_role -v`
Expected: `test_approve_with_role_sets_both` FAILS (role stays `general` — body ignored)

- [ ] **Step 3: Add the request model and update the endpoint**

In `backend/api.py`, just before the `admin_approve_user` function (~line 1150), add a model:

```python
class ApproveUserRequest(BaseModel):
    role: Literal["general", "developer", "admin"] | None = None
```

Then replace the body of `admin_approve_user` with:

```python
@app.post("/admin/users/{email:path}/approve")
def admin_approve_user(
    email: str,
    req: ApproveUserRequest | None = None,
    _admin: dict = Depends(_require_admin),
):
    """Approve a pending user so they can run queries. If a role is supplied, set it
    in the same action (used by the Approvals tab's role-picker)."""
    from backend import auth_store
    if req is not None and req.role is not None:
        if not auth_store.set_user_role(email, req.role):
            raise HTTPException(status_code=404, detail=f"User not found: {email}")
    if not auth_store.set_user_approved(email, True):
        raise HTTPException(status_code=404, detail=f"User not found: {email}")
    return {"email": email, "approved": True,
            "role": (auth_store.get_user(email) or {}).get("role")}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `venv/bin/pytest tests/test_rbac_approval.py -v`
Expected: all PASS (existing approve tests still green — body is optional)

- [ ] **Step 5: Commit**

```bash
git add backend/api.py tests/test_rbac_approval.py
git commit -m "feat(admin): approve endpoint accepts optional role (approve-with-role)"
```

---

## Task 4: Frontend — api.service: `getAuthConfig`, `devLogin`, `approveUser(role?)`

**Files:**
- Modify: `frontend/src/app/core/api.service.ts` (approveUser ~line 867; add two methods near it)

- [ ] **Step 1: Update `approveUser` to pass an optional role**

In `frontend/src/app/core/api.service.ts`, replace the `approveUser` method (~line 867) with:

```typescript
  approveUser(email: string, role?: string): Observable<{ email: string; approved: boolean; role: string }> {
    return this.http.post<{ email: string; approved: boolean; role: string }>(
      `${API_BASE}/admin/users/${encodeURIComponent(email)}/approve`,
      role ? { role } : {},
      { headers: this.adminHeaders() });
  }
```

- [ ] **Step 2: Add `getAuthConfig` and `devLogin` (public, no admin header)**

In `frontend/src/app/core/api.service.ts`, immediately after the `approveUser` method, add:

```typescript
  getAuthConfig(): Observable<{ dev_login: boolean }> {
    return this.http.get<{ dev_login: boolean }>(`${API_BASE}/auth/config`);
  }

  devLogin(email: string): Observable<{ token: string; email: string; name: string; role: string; approved: boolean }> {
    return this.http.post<{ token: string; email: string; name: string; role: string; approved: boolean }>(
      `${API_BASE}/auth/dev-login`, { email });
  }
```

- [ ] **Step 3: Verify the build compiles**

Run: `cd frontend && npx ng build 2>&1 | tail -5`
Expected: build succeeds (pre-existing budget warnings OK; no TS errors)

- [ ] **Step 4: Commit**

```bash
git add frontend/src/app/core/api.service.ts
git commit -m "feat(frontend): api methods for auth config, dev login, approve-with-role"
```

---

## Task 5: Frontend — dev-login box on the login page

**Files:**
- Modify: `frontend/src/app/features/login/login.ts` (template ~line 30; class ~line 131-180)

- [ ] **Step 1: Add the dev-login box to the template**

In `frontend/src/app/features/login/login.ts`, inside the `.login-card` div, immediately after the `signin-btn-wrap` div (after line 31 `</div>` that closes it), add:

```html
          @if (devLoginEnabled()) {
            <div class="dev-login">
              <div class="dev-login-divider">dev only</div>
              <input
                class="dev-login-input"
                type="email"
                placeholder="you@moveinsync.com"
                [(ngModel)]="devEmail"
                [disabled]="busy()"
              />
              <button class="dev-login-btn" (click)="devSignIn()" [disabled]="busy() || !devEmail">
                Dev sign in
              </button>
            </div>
          }
```

- [ ] **Step 2: Add `FormsModule` + signals + methods to the component**

In `frontend/src/app/features/login/login.ts`:

(a) Ensure `FormsModule` is imported and in `imports`. At the top with the other imports add:
```typescript
import { FormsModule } from '@angular/forms';
```
and add `FormsModule` to the component's `imports: [...]` array.

(b) Inside the `Login` class, add these fields near the other signals:
```typescript
  devLoginEnabled = signal(false);
  devEmail = '';
```

(c) In `ngAfterViewInit` (or the existing init), after the Google button setup, add:
```typescript
    this.api.getAuthConfig().subscribe({
      next: (c) => this.devLoginEnabled.set(!!c.dev_login),
      error: () => this.devLoginEnabled.set(false),
    });
```

(d) Add a `devSignIn` method (mirrors `handleCredential`'s success handling):
```typescript
  devSignIn() {
    const email = this.devEmail.trim();
    if (!email) return;
    this.busy.set(true);
    this.error.set('');
    this.api.devLogin(email).subscribe({
      next: (res) => {
        this.api.setAdminToken(res.token);
        this.api.setUserInfo(res.email, res.name, res.role, res.approved);
        this.busy.set(false);
        this.router.navigateByUrl(res.approved ? '/ask' : '/pending');
      },
      error: (err) => {
        this.busy.set(false);
        this.error.set(err?.status === 403
          ? 'Only @moveinsync.com accounts can sign in.'
          : `Dev login failed (${err?.status ?? 'network error'}).`);
      },
    });
  }
```

Confirm `signal` is already imported in this file (it is used by `error`/`busy`); if not, add it to the `@angular/core` import.

- [ ] **Step 3: Verify the build compiles**

Run: `cd frontend && npx ng build 2>&1 | tail -5`
Expected: build succeeds, a `login` chunk emitted, no TS errors

- [ ] **Step 4: Commit**

```bash
git add frontend/src/app/features/login/login.ts
git commit -m "feat(frontend): dev-only email login box (shown when /auth/config dev_login=true)"
```

---

## Task 6: Frontend — split admin into Approvals + Users sections

**Files:**
- Modify: `frontend/src/app/features/admin/admin-dashboard.ts` (template Users section ~lines 17-69; class computed/methods ~lines 191-230)

- [ ] **Step 1: Replace the single Users section with two filtered sections**

In `frontend/src/app/features/admin/admin-dashboard.ts`, replace the entire `<!-- Users (approval + roles) -->` `<section>...</section>` block (lines ~17-69) with:

```html
      <!-- Approvals (pending only) -->
      <section class="admin-section">
        <div class="section-header">
          <h2>Approvals</h2>
          <button class="refresh-btn" (click)="loadUsers()">↻ Refresh</button>
        </div>
        @if (usersError()) {
          <div class="empty-state">{{ usersError() }}</div>
        } @else if (pendingUsers().length === 0) {
          <div class="empty-state">✓ No pending approvals</div>
        } @else {
          <table class="admin-table">
            <thead>
              <tr><th>Email</th><th>Role to grant</th><th>Action</th></tr>
            </thead>
            <tbody>
              @for (u of pendingUsers(); track u.email) {
                <tr class="pending-row">
                  <td class="path-cell">{{ u.email }}</td>
                  <td>
                    <select class="role-select" [(ngModel)]="pendingRole[u.email]"
                            [disabled]="savingEmail() === u.email">
                      <option value="general">general</option>
                      <option value="developer">developer</option>
                      <option value="admin">admin</option>
                    </select>
                  </td>
                  <td>
                    <button class="apply-btn" (click)="approve(u)" [disabled]="savingEmail() === u.email">
                      {{ savingEmail() === u.email ? 'Approving…' : 'Approve' }}
                    </button>
                  </td>
                </tr>
              }
            </tbody>
          </table>
        }
      </section>

      <!-- Users (approved only) -->
      <section class="admin-section">
        <div class="section-header">
          <h2>Users</h2>
          <button class="refresh-btn" (click)="loadUsers()">↻ Refresh</button>
        </div>
        @if (approvedUsers().length === 0) {
          <div class="empty-state">No approved users yet.</div>
        } @else {
          <table class="admin-table">
            <thead>
              <tr><th>Email</th><th>Role</th><th>Status</th></tr>
            </thead>
            <tbody>
              @for (u of approvedUsers(); track u.email) {
                <tr>
                  <td class="path-cell">{{ u.email }}</td>
                  <td>
                    <select class="role-select" [ngModel]="u.role"
                            (ngModelChange)="changeRole(u, $event)"
                            [disabled]="savingEmail() === u.email">
                      <option value="general">general</option>
                      <option value="developer">developer</option>
                      <option value="admin">admin</option>
                    </select>
                  </td>
                  <td><span class="status-ok">✓ Approved</span></td>
                </tr>
              }
            </tbody>
          </table>
        }
      </section>
```

- [ ] **Step 2: Add computed lists, the pending-role map, and update `approve`**

In `frontend/src/app/features/admin/admin-dashboard.ts`:

(a) Add `computed` to the `@angular/core` import (line 1):
```typescript
import { Component, signal, computed, inject, OnInit } from '@angular/core';
```

(b) After the `users = signal<AdminUser[]>([]);` line (~line 191), add:
```typescript
  pendingUsers = computed(() => this.users().filter(u => !u.approved));
  approvedUsers = computed(() => this.users().filter(u => u.approved));
  pendingRole: Record<string, string> = {};
```

(c) Replace the `approve(u)` method (~line 224) with one that sends the picked role and
moves the row into the approved list:
```typescript
  approve(u: AdminUser) {
    const role = this.pendingRole[u.email] || 'general';
    this.savingEmail.set(u.email);
    this.api.approveUser(u.email, role).subscribe({
      next: () => {
        u.approved = true;
        u.role = role;
        this.users.set([...this.users()]); // re-trigger computed split
        this.savingEmail.set('');
      },
      error: () => { this.savingEmail.set(''); this.usersError.set(`Failed to approve ${u.email}.`); },
    });
  }
```

(d) In `loadUsers()`, seed default picker values so each pending row starts at `general`.
Replace the `next` handler (~line 218) with:
```typescript
      next: r => {
        this.users.set(r.users);
        for (const u of r.users) {
          if (!u.approved && !(u.email in this.pendingRole)) this.pendingRole[u.email] = 'general';
        }
      },
```

- [ ] **Step 3: Verify the build compiles**

Run: `cd frontend && npx ng build 2>&1 | tail -5`
Expected: build succeeds, no TS errors

- [ ] **Step 4: Commit**

```bash
git add frontend/src/app/features/admin/admin-dashboard.ts
git commit -m "feat(admin): split Users panel into Approvals (pending) + Users (approved)"
```

---

## Task 7: Full verification

- [ ] **Step 1: Run the backend test suites touched here**

Run: `venv/bin/pytest tests/test_dev_login.py tests/test_rbac_approval.py tests/test_google_auth_endpoint.py -v`
Expected: all PASS (no regressions in the existing google-auth tests)

- [ ] **Step 2: Frontend production build**

Run: `cd frontend && npx ng build 2>&1 | tail -8`
Expected: build succeeds; only pre-existing budget warnings, no errors

- [ ] **Step 3: Manual end-to-end smoke (dev)**

1. In local `.env` set `CONWO_DEV_LOGIN=true`; start backend + frontend.
2. Incognito → login page shows the "Dev sign in" box.
3. Dev-sign-in `general-test@moveinsync.com` → lands on `/pending`.
4. Admin window → **Approvals** shows it → pick `developer` → Approve → row moves to **Users**.
5. Incognito → dev-sign-in again as `general-test@moveinsync.com` → now approved as developer:
   sidebar shows Ask / Search / Ingest / Graph only; Dashboard / Traces / Admin hidden; `/query` works.
6. Set `CONWO_DEV_LOGIN` unset → restart backend → login page shows NO dev box; `POST /auth/dev-login` → 403.

- [ ] **Step 4: Update the deploy env doc (dev-only flag warning)**

Add a line to `docs/postgres-cutover.md` noting `CONWO_DEV_LOGIN` is **dev-only — never set in prod**.

Run: `git add docs/postgres-cutover.md && git commit -m "docs: note CONWO_DEV_LOGIN is dev-only"`

---

## Self-Review notes (for the implementer)

- **Spec coverage:** Feature 1 → Tasks 3 (backend approve-with-role) + 6 (split UI). Feature 2 → Tasks 1 (flag) + 2 (endpoints) + 4/5 (frontend). Safety (prod-inert) → Task 2 (`test_dev_login_disabled_returns_403`) + Task 7 step 3.6.
- **No new migration:** confirmed — `approved`/`role` already exist (070).
- **Type consistency:** `approveUser(email, role?)` (Task 4) matches the Approvals call (Task 6) and the backend `ApproveUserRequest.role` optional (Task 3). `GoogleLoginResponse` reused for dev-login keeps the frontend response shape identical to Google login (Task 2 ↔ Task 5).
- **Reload safety:** Step 0 gate before Python edits (Tasks 1-3).
