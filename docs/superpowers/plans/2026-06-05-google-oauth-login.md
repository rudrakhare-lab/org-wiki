# Google OAuth Login + Per-User Chat Isolation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the token-paste login with Google Sign-In for any `@moveinsync.com` account, and fix the stream endpoint so stream-mode conversations are owned by the logged-in user.

**Architecture:** Frontend renders a Google Sign-In button using Google Identity Services (GSI). On click, Google delivers a signed ID token JWT directly to a JS callback (no redirect). The frontend POSTs it to `POST /auth/google`; the backend verifies the JWT cryptographically, auto-provisions the user in `auth_store` if new (role: `viewer`), and returns a random 32-hex session token. The existing Bearer-token session mechanism and all downstream auth code are unchanged.

**Tech Stack:** Python `google-auth>=2.29.0`, FastAPI, Angular 17, Google Identity Services JS SDK, SQLite (`auth_store`)

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Modify | `requirements-backend.txt` | Add `google-auth` dependency |
| Modify | `.env` | Add `GOOGLE_CLIENT_ID=` entry |
| **Create** | `backend/google_auth.py` | JWT verification + domain enforcement |
| **Create** | `tests/test_google_auth.py` | Unit tests for `google_auth.py` |
| Modify | `backend/api.py` | Add `POST /auth/google` endpoint; fix stream user_email bug |
| **Create** | `tests/test_google_auth_endpoint.py` | Integration tests for the new endpoint |
| **Create** | `tests/test_stream_user_email.py` | Test stream endpoint passes user_email |
| Modify | `frontend/src/index.html` | Load GSI script synchronously |
| Modify | `frontend/src/app/core/api.service.ts` | Add `setUserEmail` / `getUserEmail` helpers |
| Modify | `frontend/src/app/features/login/login.ts` | Replace token form with Google Sign-In button |
| Modify | `frontend/src/app/app.ts` | Read stored email; expose `userEmail` signal |
| Modify | `frontend/src/app/app.html` | Show logged-in email chip in nav |

---

## Task 1: Add `google-auth` dependency + `GOOGLE_CLIENT_ID` env var

**Files:**
- Modify: `requirements-backend.txt`
- Modify: `.env`

- [ ] **Step 1: Add the dependency**

Open `requirements-backend.txt` and append:
```
google-auth>=2.29.0
```

- [ ] **Step 2: Install it**

```bash
cd /Users/rudrakhare/Desktop/my-wiki/org-wiki
venv/bin/pip install "google-auth>=2.29.0"
```

Expected output: `Successfully installed google-auth-X.Y.Z ...`

- [ ] **Step 3: Verify the import works**

```bash
venv/bin/python -c "from google.oauth2 import id_token; from google.auth.transport import requests; print('OK')"
```

Expected: `OK`

- [ ] **Step 4: Add env var placeholder to `.env`**

Add these two lines to `.env` (after the existing `ANTHROPIC_API_KEY` line):

```
# Google OAuth (for Sign in with Google)
GOOGLE_CLIENT_ID=
```

**Note to implementor:** You must fill in `GOOGLE_CLIENT_ID` from Google Cloud Console before the feature will work. Steps:
1. Go to console.cloud.google.com → APIs & Services → Credentials
2. Create OAuth 2.0 Client ID → Web application
3. Add `http://localhost:4200` to Authorized JavaScript origins
4. Copy the Client ID (ends in `.apps.googleusercontent.com`) and paste as the value

- [ ] **Step 5: Commit**

```bash
git add requirements-backend.txt .env
git commit -m "chore: add google-auth dependency and GOOGLE_CLIENT_ID env var"
```

---

## Task 2: Create `backend/google_auth.py` (TDD)

**Files:**
- Create: `tests/test_google_auth.py`
- Create: `backend/google_auth.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_google_auth.py`:

```python
import pytest
from unittest.mock import patch, MagicMock
from backend.google_auth import verify_google_credential


def _make_id_info(**overrides):
    base = {
        "email": "rudra.khare@moveinsync.com",
        "name": "Rudra Khare",
        "picture": "https://lh3.googleusercontent.com/photo.jpg",
        "hd": "moveinsync.com",
        "email_verified": True,
    }
    base.update(overrides)
    return base


def test_verify_returns_user_info_for_valid_company_token():
    with patch("backend.google_auth.id_token.verify_oauth2_token") as mock_verify:
        mock_verify.return_value = _make_id_info()
        result = verify_google_credential("fake-credential", "fake-client-id")
    assert result["email"] == "rudra.khare@moveinsync.com"
    assert result["name"] == "Rudra Khare"
    assert result["picture"] == "https://lh3.googleusercontent.com/photo.jpg"


def test_verify_raises_for_non_moveinsync_domain():
    with patch("backend.google_auth.id_token.verify_oauth2_token") as mock_verify:
        mock_verify.return_value = _make_id_info(hd="gmail.com", email="attacker@gmail.com")
        with pytest.raises(ValueError, match="not allowed"):
            verify_google_credential("fake-credential", "fake-client-id")


def test_verify_raises_when_hd_missing():
    with patch("backend.google_auth.id_token.verify_oauth2_token") as mock_verify:
        mock_verify.return_value = _make_id_info(hd=None, email="personal@gmail.com")
        # Remove the hd key entirely
        info = _make_id_info()
        del info["hd"]
        mock_verify.return_value = info
        with pytest.raises(ValueError, match="not allowed"):
            verify_google_credential("fake-credential", "fake-client-id")


def test_verify_raises_on_google_error():
    with patch("backend.google_auth.id_token.verify_oauth2_token") as mock_verify:
        mock_verify.side_effect = ValueError("Token expired")
        with pytest.raises(ValueError):
            verify_google_credential("bad-credential", "fake-client-id")
```

- [ ] **Step 2: Run tests — expect FAIL**

```bash
cd /Users/rudrakhare/Desktop/my-wiki/org-wiki
venv/bin/pytest tests/test_google_auth.py -v
```

Expected: `ModuleNotFoundError: No module named 'backend.google_auth'`

- [ ] **Step 3: Implement `backend/google_auth.py`**

Create `backend/google_auth.py`:

```python
"""
Google Identity Services token verification.

verify_google_credential() accepts a Google ID token (credential from the
GSI JS callback), verifies it against Google's public keys, enforces the
@moveinsync.com hosted domain, and returns {email, name, picture}.

Raises ValueError for any invalid or non-company token.
"""
from __future__ import annotations

from google.oauth2 import id_token
from google.auth.transport import requests as google_requests


def verify_google_credential(credential: str, client_id: str) -> dict:
    """Verify a Google ID token and return user info.

    Args:
        credential: The raw ID token string from the GSI JS callback.
        client_id: The OAuth 2.0 client ID to verify against.

    Returns:
        dict with keys: email, name, picture

    Raises:
        ValueError: If the token is invalid, expired, or from outside moveinsync.com.
    """
    id_info = id_token.verify_oauth2_token(
        credential,
        google_requests.Request(),
        client_id,
    )
    if id_info.get("hd") != "moveinsync.com":
        raise ValueError(
            f"Domain '{id_info.get('hd')}' not allowed. "
            "Only @moveinsync.com accounts can sign in."
        )
    return {
        "email": id_info["email"],
        "name": id_info.get("name", id_info["email"]),
        "picture": id_info.get("picture", ""),
    }
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
venv/bin/pytest tests/test_google_auth.py -v
```

Expected:
```
PASSED tests/test_google_auth.py::test_verify_returns_user_info_for_valid_company_token
PASSED tests/test_google_auth.py::test_verify_raises_for_non_moveinsync_domain
PASSED tests/test_google_auth.py::test_verify_raises_when_hd_missing
PASSED tests/test_google_auth.py::test_verify_raises_on_google_error
4 passed
```

- [ ] **Step 5: Commit**

```bash
git add backend/google_auth.py tests/test_google_auth.py
git commit -m "feat: add google credential verification module"
```

---

## Task 3: Add `POST /auth/google` endpoint (TDD)

**Files:**
- Create: `tests/test_google_auth_endpoint.py`
- Modify: `backend/api.py` (imports section + new endpoint section)

- [ ] **Step 1: Write the failing tests**

Create `tests/test_google_auth_endpoint.py`:

```python
import importlib
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Fresh TestClient with isolated auth_store and GOOGLE_CLIENT_ID configured."""
    import backend.auth_store as auth_module
    auth_dir = tmp_path / "raw" / "auth"
    auth_dir.mkdir(parents=True)
    monkeypatch.setattr(auth_module, "AUTH_DB", auth_dir / "auth.sqlite", raising=False)
    monkeypatch.setattr(auth_module, "AUTH_DIR", auth_dir, raising=False)
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client-id.apps.googleusercontent.com")
    from backend import api as api_module
    importlib.reload(api_module)
    return TestClient(api_module.app), auth_module


def _mock_verify(email="rudra.khare@moveinsync.com", name="Rudra Khare"):
    return {"email": email, "name": name, "picture": "https://example.com/pic.jpg"}


def test_google_login_provisions_new_user_and_returns_token(client):
    test_client, auth_module = client
    with patch("backend.api.verify_google_credential", return_value=_mock_verify()):
        resp = test_client.post("/auth/google", json={"credential": "fake-id-token"})
    assert resp.status_code == 200
    body = resp.json()
    assert "token" in body
    assert body["email"] == "rudra.khare@moveinsync.com"
    assert body["name"] == "Rudra Khare"
    assert len(body["token"]) == 32
    # User should be in auth_store
    user = auth_module.get_user("rudra.khare@moveinsync.com")
    assert user is not None
    assert user["role"] == "viewer"


def test_google_login_returns_token_for_existing_user(client):
    test_client, auth_module = client
    # Pre-provision the user
    auth_module.create_user("existing@moveinsync.com", role="viewer")
    with patch("backend.api.verify_google_credential",
               return_value=_mock_verify(email="existing@moveinsync.com", name="Existing")):
        resp = test_client.post("/auth/google", json={"credential": "fake-id-token"})
    assert resp.status_code == 200
    assert resp.json()["email"] == "existing@moveinsync.com"


def test_google_login_rejects_wrong_domain(client):
    test_client, _ = client
    with patch("backend.api.verify_google_credential",
               side_effect=ValueError("Domain 'gmail.com' not allowed")):
        resp = test_client.post("/auth/google", json={"credential": "outsider-token"})
    assert resp.status_code == 403
    assert "not allowed" in resp.json()["detail"]


def test_google_login_rejects_invalid_token(client):
    test_client, _ = client
    with patch("backend.api.verify_google_credential",
               side_effect=ValueError("Token signature invalid")):
        resp = test_client.post("/auth/google", json={"credential": "garbage"})
    assert resp.status_code == 403


def test_google_login_returns_500_when_client_id_not_configured(tmp_path, monkeypatch):
    import backend.auth_store as auth_module
    auth_dir = tmp_path / "raw" / "auth"
    auth_dir.mkdir(parents=True)
    monkeypatch.setattr(auth_module, "AUTH_DB", auth_dir / "auth.sqlite", raising=False)
    monkeypatch.setattr(auth_module, "AUTH_DIR", auth_dir, raising=False)
    monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)
    from backend import api as api_module
    importlib.reload(api_module)
    test_client = TestClient(api_module.app)
    resp = test_client.post("/auth/google", json={"credential": "any"})
    assert resp.status_code == 500
    assert "GOOGLE_CLIENT_ID" in resp.json()["detail"]
```

- [ ] **Step 2: Run tests — expect FAIL**

```bash
venv/bin/pytest tests/test_google_auth_endpoint.py -v
```

Expected: tests fail because the endpoint doesn't exist yet.

- [ ] **Step 3: Add import to `backend/api.py`**

In `backend/api.py`, find the imports block (around line 53–58). Add after the existing `from backend...` imports:

```python
from backend.google_auth import verify_google_credential
```

- [ ] **Step 4: Add the request model to `backend/api.py`**

Find the request/response models section (around line 184). Add after `AgentToolCall`:

```python
class GoogleLoginRequest(BaseModel):
    credential: str


class GoogleLoginResponse(BaseModel):
    token: str
    email: str
    name: str
```

- [ ] **Step 5: Add the endpoint to `backend/api.py`**

Find the line `# Admin endpoints (require admin Bearer token)` (around line 817). Insert this block **above** it (i.e., before the admin section):

```python
# ---------------------------------------------------------------------------
# Auth — Google Sign-In
# ---------------------------------------------------------------------------

@app.post("/auth/google", response_model=GoogleLoginResponse)
def google_login(req: GoogleLoginRequest) -> GoogleLoginResponse:
    """Exchange a Google ID token for a Conwo session token.

    Verifies the Google credential, enforces @moveinsync.com domain,
    auto-provisions the user on first login (role: viewer), and returns
    a random session token stored in auth_store.
    """
    import os
    client_id = os.getenv("GOOGLE_CLIENT_ID", "").strip()
    if not client_id:
        raise HTTPException(
            status_code=500,
            detail="GOOGLE_CLIENT_ID is not configured on the server.",
        )
    try:
        user_info = verify_google_credential(req.credential, client_id)
    except ValueError as exc:
        raise HTTPException(status_code=403, detail=str(exc))

    email = user_info["email"]
    from backend import auth_store
    if not auth_store.get_user(email):
        auth_store.create_user(email, role="viewer")
    token = auth_store.create_token(email)
    return GoogleLoginResponse(token=token, email=email, name=user_info["name"])

```

- [ ] **Step 6: Run tests — expect PASS**

```bash
venv/bin/pytest tests/test_google_auth_endpoint.py -v
```

Expected:
```
PASSED tests/test_google_auth_endpoint.py::test_google_login_provisions_new_user_and_returns_token
PASSED tests/test_google_auth_endpoint.py::test_google_login_returns_token_for_existing_user
PASSED tests/test_google_auth_endpoint.py::test_google_login_rejects_wrong_domain
PASSED tests/test_google_auth_endpoint.py::test_google_login_rejects_invalid_token
PASSED tests/test_google_auth_endpoint.py::test_google_login_returns_500_when_client_id_not_configured
5 passed
```

- [ ] **Step 7: Run full test suite to check for regressions**

```bash
venv/bin/pytest tests/ -v --ignore=tests/test_local_claude_code.py -x
```

Expected: all previously passing tests still pass.

- [ ] **Step 8: Commit**

```bash
git add backend/api.py tests/test_google_auth_endpoint.py
git commit -m "feat: add POST /auth/google endpoint with auto-provisioning"
```

---

## Task 4: Fix stream endpoint missing `user_email` bug

**Files:**
- Modify: `backend/api.py` (lines ~519–528)

- [ ] **Step 1: Write the failing test**

Add a new file `tests/test_stream_user_email.py`:

```python
"""
Test that the /query/stream endpoint passes user_email to create_conversation.

The stream endpoint calls claude_available() BEFORE creating a conversation, so
we must mock it to True and stub out the downstream subprocess and preflight to
avoid spawning a real claude process.
"""
import importlib
import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture
def stream_client(tmp_path, monkeypatch):
    import backend.auth_store as auth_module
    import backend.conversation_store as cs
    auth_dir = tmp_path / "raw" / "auth"
    auth_dir.mkdir(parents=True)
    monkeypatch.setattr(auth_module, "AUTH_DB", auth_dir / "auth.sqlite", raising=False)
    monkeypatch.setattr(auth_module, "AUTH_DIR", auth_dir, raising=False)
    monkeypatch.setattr(cs, "CONVERSATIONS_DB", tmp_path / "c.sqlite", raising=False)
    monkeypatch.setattr(cs, "CONVERSATIONS_DIR", tmp_path, raising=False)
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-id")
    auth_module.create_user("stream@moveinsync.com", role="admin")
    token = auth_module.create_token("stream@moveinsync.com")
    return tmp_path, monkeypatch, auth_module, cs, token


def test_stream_conversation_is_owned_by_user(stream_client):
    tmp_path, monkeypatch, auth_module, cs, token = stream_client

    captured_email = {}
    original_create = cs.create_conversation

    def spy_create(title=None, user_email=None):
        captured_email["value"] = user_email
        return original_create(title=title, user_email=user_email)

    preflight_mock = MagicMock()
    preflight_mock.preflight_tickets = []

    with patch("backend.api.claude_available", return_value=True), \
         patch("backend.api.conversation_store.create_conversation",
               side_effect=spy_create), \
         patch("backend.api.run_preflight", return_value=preflight_mock), \
         patch("backend.api.build_agent_preamble", return_value=""):

        from backend import api as api_module
        importlib.reload(api_module)
        from fastapi.testclient import TestClient

        # Patch the SSE generator so it closes immediately without spawning claude
        async def empty_stream(*args, **kwargs):
            return
            yield  # makes it an async generator

        with patch.object(api_module, "query_stream",
                          wraps=api_module.query_stream):
            test_client = TestClient(api_module.app, raise_server_exceptions=False)
            test_client.post(
                "/query/stream",
                json={"question": "hello world"},
                headers={"Authorization": f"Bearer {token}"},
            )

    assert captured_email.get("value") == "stream@moveinsync.com", (
        f"Expected user_email='stream@moveinsync.com' but got: {captured_email.get('value')!r}"
    )
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
venv/bin/pytest tests/test_stream_user_email.py -v
```

Expected: FAIL — `captured_email["value"]` is `None` because `user_email` isn't passed yet.

- [ ] **Step 3: Apply the fix in `backend/api.py`**

Find this block in `api.py` (around line 519–528):

```python
    # Resolve / create conversation, save the user message before the stream
    # so it appears in history even if the stream is cancelled.
    conversation_id = req.conversation_id
    if conversation_id and not conversation_store.get_conversation(conversation_id):
        conversation_id = None
    if not conversation_id:
        conv = conversation_store.create_conversation(
            title=conversation_store.auto_title_from_question(req.question)
        )
        conversation_id = conv["id"]
```

Replace with:

```python
    # Resolve / create conversation, save the user message before the stream
    # so it appears in history even if the stream is cancelled.
    conversation_id = req.conversation_id
    if conversation_id and not conversation_store.get_conversation(conversation_id):
        conversation_id = None
    if not conversation_id:
        conv = conversation_store.create_conversation(
            title=conversation_store.auto_title_from_question(req.question),
            user_email=user.get("email"),
        )
        conversation_id = conv["id"]
```

- [ ] **Step 4: Run test — expect PASS**

```bash
venv/bin/pytest tests/test_stream_user_email.py -v
```

Expected: PASS — `captured_email["value"]` is `"stream@moveinsync.com"`.

- [ ] **Step 5: Run the full test suite**

```bash
venv/bin/pytest tests/ -v --ignore=tests/test_local_claude_code.py -x
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add backend/api.py tests/test_stream_user_email.py
git commit -m "fix: attach user_email to stream-mode conversations"
```

---

## Task 5: Frontend — load GSI script + add `getUserEmail`/`setUserEmail` to `ApiService`

**Files:**
- Modify: `frontend/src/index.html`
- Modify: `frontend/src/app/core/api.service.ts`

- [ ] **Step 1: Add GSI script to `index.html`**

In `frontend/src/index.html`, add **before `</head>`** (no `async`/`defer` — must be synchronous so `google` is available when Angular boots):

```html
  <script src="https://accounts.google.com/gsi/client"></script>
```

Full resulting `<head>`:
```html
<head>
  <meta charset="utf-8">
  <title>Conwo</title>
  <base href="/">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="icon" type="image/x-icon" href="favicon.ico">
  <script src="https://accounts.google.com/gsi/client"></script>
</head>
```

- [ ] **Step 2: Add email storage helpers to `api.service.ts`**

In `frontend/src/app/core/api.service.ts`, find the constant `const ADMIN_TOKEN_KEY = 'conwo_admin_token';` (line ~473). Add a new constant below it:

```typescript
const USER_EMAIL_KEY = 'conwo_user_email';
const USER_NAME_KEY = 'conwo_user_name';
```

Then find the `setAdminToken` method and add these two new methods directly after it:

```typescript
  setUserInfo(email: string, name: string): void {
    localStorage.setItem(USER_EMAIL_KEY, email);
    localStorage.setItem(USER_NAME_KEY, name);
  }

  getUserEmail(): string {
    return localStorage.getItem(USER_EMAIL_KEY) ?? '';
  }

  getUserName(): string {
    return localStorage.getItem(USER_NAME_KEY) ?? '';
  }

  clearUserInfo(): void {
    localStorage.removeItem(USER_EMAIL_KEY);
    localStorage.removeItem(USER_NAME_KEY);
  }
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/index.html frontend/src/app/core/api.service.ts
git commit -m "feat: load GSI script and add user info storage helpers"
```

---

## Task 6: Replace login form with Google Sign-In button

**Files:**
- Modify: `frontend/src/app/features/login/login.ts`

- [ ] **Step 1: Replace the entire contents of `login.ts`**

> **Note to implementor:** Fill in `GOOGLE_CLIENT_ID` with the value from Google Cloud Console before building. It ends in `.apps.googleusercontent.com`.

```typescript
import { AfterViewInit, Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { ApiService } from '../../core/api.service';

declare const google: any;

const API_BASE = 'http://localhost:8000';
// Fill this in from Google Cloud Console → APIs & Services → Credentials
// It ends in .apps.googleusercontent.com
const GOOGLE_CLIENT_ID = '';

@Component({
  selector: 'app-login',
  imports: [CommonModule],
  template: `
    <div class="login-shell">
      <div class="login-card">
        <h1 class="login-title">Sign in to Conwo</h1>
        <p class="login-sub">Use your @moveinsync.com Google account.</p>

        <div class="signin-btn-wrap">
          <div id="google-signin-btn"></div>
        </div>

        @if (error()) {
          <div class="login-error" role="alert">{{ error() }}</div>
        }

        @if (busy()) {
          <div class="login-busy">Signing in…</div>
        }
      </div>
    </div>
  `,
  styles: [`
    .login-shell {
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 70vh;
      padding: 24px;
    }
    .login-card {
      width: 100%;
      max-width: 380px;
      padding: 32px 28px;
      background: var(--bg-elevated, var(--bg));
      border: 1px solid var(--border);
      border-radius: 12px;
      box-shadow: 0 4px 24px rgba(0, 0, 0, 0.04);
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 20px;
    }
    .login-title { margin: 0; font-size: 1.4rem; }
    .login-sub { margin: 0; color: var(--text-muted); font-size: 0.9rem; text-align: center; }
    .signin-btn-wrap { margin: 8px 0; }
    .login-error {
      width: 100%;
      padding: 8px 12px;
      background: rgba(239, 68, 68, 0.1);
      border: 1px solid rgba(239, 68, 68, 0.3);
      color: var(--error, rgb(180, 50, 50));
      border-radius: 6px;
      font-size: 0.85rem;
      text-align: center;
    }
    .login-busy {
      color: var(--text-muted);
      font-size: 0.9rem;
    }
  `]
})
export class Login implements AfterViewInit {
  private api = inject(ApiService);
  private router = inject(Router);
  private http = inject(HttpClient);

  busy = signal(false);
  error = signal('');

  ngAfterViewInit() {
    if (!GOOGLE_CLIENT_ID) {
      this.error.set('Server configuration error: GOOGLE_CLIENT_ID is not set.');
      return;
    }
    google.accounts.id.initialize({
      client_id: GOOGLE_CLIENT_ID,
      callback: (response: any) => this.handleCredential(response),
    });
    google.accounts.id.renderButton(
      document.getElementById('google-signin-btn')!,
      { theme: 'outline', size: 'large', width: 320 }
    );
  }

  private handleCredential(response: any) {
    this.busy.set(true);
    this.error.set('');
    const headers = new HttpHeaders({ 'Content-Type': 'application/json' });
    this.http.post<{ token: string; email: string; name: string }>(
      `${API_BASE}/auth/google`,
      { credential: response.credential },
      { headers }
    ).subscribe({
      next: (res) => {
        this.api.setAdminToken(res.token);
        this.api.setUserInfo(res.email, res.name);
        this.busy.set(false);
        this.router.navigateByUrl('/ask');
      },
      error: (err) => {
        this.busy.set(false);
        if (err?.status === 403) {
          this.error.set('Access denied — only @moveinsync.com accounts are allowed.');
        } else if (err?.status === 500) {
          this.error.set('Server configuration error. Contact the admin.');
        } else {
          this.error.set(`Could not reach the server (${err?.status ?? 'network error'}).`);
        }
      },
    });
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/app/features/login/login.ts
git commit -m "feat: replace token-paste login with Google Sign-In button"
```

---

## Task 7: Show logged-in user's email in nav + clear on sign-out

**Files:**
- Modify: `frontend/src/app/app.ts`
- Modify: `frontend/src/app/app.html`

- [ ] **Step 1: Update `app.ts` to expose `userEmail` and clear info on sign-out**

Replace the entire contents of `frontend/src/app/app.ts`:

```typescript
import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterOutlet, RouterLink, RouterLinkActive, Router, NavigationEnd } from '@angular/router';
import { filter } from 'rxjs/operators';
import { ApiService } from './core/api.service';

const ADMIN_TOKEN_KEY = 'conwo_admin_token';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, RouterLink, RouterLinkActive, CommonModule],
  templateUrl: './app.html',
  styleUrl: './app.scss'
})
export class App {
  readonly title = 'Conwo';
  private router = inject(Router);
  private api = inject(ApiService);

  currentUrl = signal<string>(this.router.url);
  signedIn = signal<boolean>(this.readToken().length > 0);
  userEmail = signal<string>(this.api.getUserEmail());

  constructor() {
    this.router.events
      .pipe(filter(e => e instanceof NavigationEnd))
      .subscribe(e => {
        this.currentUrl.set((e as NavigationEnd).urlAfterRedirects);
        this.signedIn.set(this.readToken().length > 0);
        this.userEmail.set(this.api.getUserEmail());
      });
  }

  showHeaderNav(): boolean {
    return !this.currentUrl().startsWith('/login') && this.signedIn();
  }

  signOut() {
    try {
      localStorage.removeItem(ADMIN_TOKEN_KEY);
    } catch { /* private mode */ }
    this.api.clearUserInfo();
    this.signedIn.set(false);
    this.userEmail.set('');
    this.router.navigateByUrl('/login');
  }

  private readToken(): string {
    try {
      return localStorage.getItem(ADMIN_TOKEN_KEY) ?? '';
    } catch {
      return '';
    }
  }
}
```

- [ ] **Step 2: Add email chip to nav in `app.html`**

Replace the contents of `frontend/src/app/app.html`:

```html
<header class="top-bar">
  <a routerLink="/ask" class="brand" aria-label="Conwo — home">
    <span class="brand-name">Conwo</span>
  </a>
  <div class="top-center">
    <span class="agent-title">WorkInSync Agent</span>
  </div>
  @if (showHeaderNav()) {
    <nav class="top-nav" aria-label="Primary">
      <a routerLink="/ask" routerLinkActive="active" class="nav-link">Ask</a>
      <a routerLink="/search" routerLinkActive="active" class="nav-link">Search</a>
      <a routerLink="/dashboard" routerLinkActive="active" class="nav-link">Dashboard</a>
      <a routerLink="/traces" routerLinkActive="active" class="nav-link">Traces</a>
      <a routerLink="/ingest" routerLinkActive="active" class="nav-link">Ingest</a>
      <a routerLink="/admin" routerLinkActive="active" class="nav-link">Admin</a>
      @if (userEmail()) {
        <span class="nav-user-email">{{ userEmail() }}</span>
      }
      <button type="button" class="nav-link nav-signout" (click)="signOut()">Sign out</button>
    </nav>
  }
</header>

<main class="app-main">
  <router-outlet />
</main>
```

- [ ] **Step 3: Add the `.nav-user-email` style to `app.scss`**

Open `frontend/src/app/app.scss` and append:

```scss
.nav-user-email {
  font-size: 0.8rem;
  color: var(--text-muted);
  padding: 4px 8px;
  border: 1px solid var(--border);
  border-radius: 4px;
  max-width: 180px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/app/app.ts frontend/src/app/app.html frontend/src/app/app.scss
git commit -m "feat: show logged-in user email in nav and clear on sign-out"
```

---

## Task 8: Build frontend and smoke-test end-to-end

**Files:** none (verification only)

- [ ] **Step 1: Run the full backend test suite**

```bash
cd /Users/rudrakhare/Desktop/my-wiki/org-wiki
venv/bin/pytest tests/ -v --ignore=tests/test_local_claude_code.py -x
```

Expected: all tests pass.

- [ ] **Step 2: Build the frontend**

```bash
cd /Users/rudrakhare/Desktop/my-wiki/org-wiki/frontend
npm run build
```

Expected: build succeeds with no errors. TypeScript errors indicate a problem — fix before proceeding.

- [ ] **Step 3: Fill in `GOOGLE_CLIENT_ID`**

In `frontend/src/app/features/login/login.ts`, replace the empty string:
```typescript
const GOOGLE_CLIENT_ID = '';
```
with the Client ID from Google Cloud Console (ends in `.apps.googleusercontent.com`).

Rebuild after filling it in:
```bash
npm run build
```

- [ ] **Step 4: Start backend and frontend**

Terminal 1 (backend):
```bash
cd /Users/rudrakhare/Desktop/my-wiki/org-wiki
venv/bin/uvicorn backend.api:app --reload --port 8000
```

Terminal 2 (frontend):
```bash
cd /Users/rudrakhare/Desktop/my-wiki/org-wiki/frontend
npm start
```

- [ ] **Step 5: Smoke-test in browser**

Open `http://localhost:4200`.

Expected flow:
1. Redirected to `/login` — see "Sign in to Conwo" with a Google button
2. Click Google button → Google account picker popup
3. Select a `@moveinsync.com` account
4. Redirected to `/ask` — logged in
5. Logged-in email visible in the top-right nav
6. Ask a question in both API mode and Claude Code mode — confirm conversations appear in the sidebar
7. Sign out → redirected to `/login`, email cleared from nav
8. Sign back in → only your own conversations are visible

- [ ] **Step 6: Verify a non-`@moveinsync.com` account is rejected**

If you have a personal Gmail account:
1. Click Sign in with Google
2. Select the personal account
3. Expected: error message "Access denied — only @moveinsync.com accounts are allowed."

- [ ] **Step 7: Final commit**

```bash
cd /Users/rudrakhare/Desktop/my-wiki/org-wiki
git add frontend/src/app/features/login/login.ts  # with GOOGLE_CLIENT_ID filled in
git commit -m "feat: complete Google OAuth login — fill GOOGLE_CLIENT_ID"
```

---

## Summary of Changes

| File | What changed |
|------|-------------|
| `requirements-backend.txt` | `google-auth>=2.29.0` added |
| `.env` | `GOOGLE_CLIENT_ID=` placeholder |
| `backend/google_auth.py` | New — JWT verification + domain enforcement |
| `backend/api.py` | New `POST /auth/google` endpoint; stream bug fix |
| `tests/test_google_auth.py` | New — unit tests for `google_auth.py` |
| `tests/test_google_auth_endpoint.py` | New — integration tests for endpoint + stream fix |
| `frontend/src/index.html` | GSI script tag added |
| `frontend/src/app/core/api.service.ts` | `setUserInfo` / `getUserEmail` / `clearUserInfo` helpers |
| `frontend/src/app/features/login/login.ts` | Replaced token form with Google Sign-In button |
| `frontend/src/app/app.ts` | `userEmail` signal + `clearUserInfo` on sign-out |
| `frontend/src/app/app.html` | Email chip in nav |
| `frontend/src/app/app.scss` | `.nav-user-email` style |
