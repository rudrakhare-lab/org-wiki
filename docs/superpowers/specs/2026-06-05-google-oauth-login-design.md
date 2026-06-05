# Google OAuth Login + Per-User Chat Isolation

**Date:** 2026-06-05
**Status:** Approved
**Scope:** Replace token-paste login with Google Sign-In; fix stream-query chat ownership; surface logged-in user in nav

---

## Problem

The current login requires users to paste a 32-char hex token that an admin generates and shares out-of-band. Layer 1 tokens (TOML) are derived from `SHA256(email)` — guessable by anyone who knows the email. There is no self-service login. Additionally, the `/query/stream` endpoint does not attach `user_email` when creating conversations, so stream-mode chats have no owner and are invisible to non-admin users.

---

## Goals

1. Any `@moveinsync.com` Google account can sign in without admin intervention.
2. Users only see their own conversation history.
3. The existing Bearer-token session mechanism is unchanged — only the identity verification step is replaced.

---

## Non-Goals

- SSO via SAML / Okta (Phase 5 plan item — out of scope here)
- Mobile / native app support
- Refresh-token rotation (session tokens are long-lived; revocation via admin API is sufficient for now)

---

## Architecture

```
User clicks "Sign in with Google"
  → Google Identity Services popup (no page redirect)
  → Google returns a signed ID token (JWT) directly to the JS callback
  → Frontend POSTs { credential: "<id_token>" } to POST /auth/google
  → Backend verifies JWT signature against Google's public keys
  → Checks hd (hosted domain) == "moveinsync.com" — rejects all others with 403
  → Auto-provisions user in auth_store (role: "viewer") if first login
  → Creates cryptographically random session token via auth_store.create_token()
  → Returns { token, email, name }
  → Frontend stores token in localStorage["conwo_admin_token"]
  → All subsequent requests use it as Bearer (existing interceptor unchanged)
```

### Roles

| Role | Who | Conversations visible |
|------|-----|-----------------------|
| `admin` | `rudra.khare@moveinsync.com` (TOML) | All users |
| `viewer` | All Google-authed users | Own only |

Auto-provisioned Google users get `viewer` role. Admins can promote via `POST /admin/users`.

### Prerequisite (manual, one-time)

Create an OAuth 2.0 Client ID in Google Cloud Console:
- Application type: **Web application**
- Authorized JavaScript origins: `http://localhost:4200` (dev) + production URL when deployed
- Copy the Client ID into `.env` as `GOOGLE_CLIENT_ID=<your-client-id>`

---

## Backend Changes

### New file: `backend/google_auth.py`

Single public function:

```python
def verify_google_credential(credential: str, client_id: str) -> dict:
    """Verify a Google ID token. Returns {email, name, picture, hd}.
    Raises ValueError on invalid token or wrong hosted domain."""
```

- Uses `google.oauth2.id_token.verify_oauth2_token()` with `google.auth.transport.requests.Request()`
- Asserts `id_info["hd"] == "moveinsync.com"` — rejects all non-company accounts
- Returns the relevant claims dict

### New endpoint: `POST /auth/google` in `api.py`

```
Request:  { "credential": "<google-id-token>" }
Response: { "token": "<32-hex-session-token>", "email": "...", "name": "..." }
Errors:   400 (missing credential), 403 (wrong domain / invalid token)
```

Logic:
1. Call `verify_google_credential(req.credential, GOOGLE_CLIENT_ID)`
2. `auth_store.get_user(email)` — if None, call `auth_store.create_user(email, role="viewer")`
3. `token = auth_store.create_token(email)` — returns new random 32-hex token
4. Return `{token, email, name}`

### Bug fix: stream endpoint

In `api.py` `/query/stream`, when calling `conversation_store.create_conversation()`, pass `user_email` extracted from the authenticated user (same as the non-stream `/query` endpoint already does).

### New dependency

Add to `requirements.txt`:
```
google-auth>=2.29.0
```

### New env var

Add to `.env` and `.env.example`:
```
GOOGLE_CLIENT_ID=
```

---

## Frontend Changes

### `frontend/src/index.html`

Add before `</head>`:
```html
<script src="https://accounts.google.com/gsi/client" async defer></script>
```

### `frontend/src/environments/environment.ts` (and `.prod.ts`)

Add:
```typescript
googleClientId: '<your-client-id>'
```

### `frontend/src/app/features/login/login.ts`

Replace the token-paste form entirely. New template:
- Conwo logo / title
- Google Sign-In button (rendered via `google.accounts.id.renderButton`)
- Error message slot for 403 (not approved) or network errors
- Hint: "Only @moveinsync.com accounts are allowed"

Logic:
1. On component init: call `google.accounts.id.initialize({ client_id, callback: handleCredential })`
2. `handleCredential(response)`: POST `{ credential: response.credential }` to `POST /auth/google`
3. On success: `api.setAdminToken(token)` → `router.navigateByUrl('/ask')`
4. On 403: show "Your account isn't approved. Contact the admin."

### `frontend/src/app/app.ts` (nav bar)

- Read `email` from `api.getAdminToken()` (decode it from the `/status` response or store separately)
- Show logged-in email and a **Sign out** button
- Sign out: clear `localStorage["conwo_admin_token"]`, navigate to `/login`

### No changes needed

- `auth.interceptor.ts` — already attaches Bearer token from localStorage
- `auth.guard.ts` — already checks localStorage for token presence
- All conversation endpoints — already enforce per-user isolation

---

## Chat Isolation (current state + fix)

| Endpoint | Before | After |
|----------|--------|-------|
| `GET /conversations` | ✅ filters by user_email | ✅ unchanged |
| `GET /conversations/:id` | ✅ ownership check | ✅ unchanged |
| `POST /query` (non-stream) | ✅ passes user_email | ✅ unchanged |
| `POST /query/stream` | ❌ no user_email on create | ✅ fixed |

---

## Error Handling

| Scenario | Backend response | Frontend message |
|----------|-----------------|-----------------|
| Invalid / expired Google token | 403 | "Sign-in failed. Try again." |
| Non-moveinsync.com account | 403 | "Only @moveinsync.com accounts are allowed." |
| `GOOGLE_CLIENT_ID` not configured | 500 | "Server configuration error." |
| Network error | — | "Could not reach the server." |

---

## What is NOT changing

- The TOML admin account (`rudra.khare@moveinsync.com`) continues to work as-is — no migration needed
- Existing session tokens in `auth_store` remain valid
- All other API endpoints, guards, and interceptors are untouched
