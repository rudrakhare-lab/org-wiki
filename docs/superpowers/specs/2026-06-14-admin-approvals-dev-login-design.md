# Admin Approvals/Users split + dev-only email login

_Date: 2026-06-14_
_Status: approved (pending spec review)_
_Environment scope: dev-focused, but ships with prod-safety guarantees_

## Problem

Two gaps surfaced while testing the new RBAC + approval feature in the dev environment:

1. **Approval flow is invisible in dev.** The backend approval + role-assignment is
   fully implemented (`POST /admin/users/{email}/approve`, `PATCH /admin/users/{email}/role`,
   `GET /admin/users`) and the admin dashboard already renders a combined "Users" section
   with a role dropdown, approval status, and an Approve button. But the dev DB has only
   2 users, both already `admin` + `approved` (the 070 migration backfilled existing users
   as approved), so there are no pending users to see — making it look unimplemented.
   The user wants the approval surface split into a dedicated **Approvals** view separate
   from a **Users** management view.

2. **No way to test the 3 roles end-to-end.** Login is Google OAuth only, locked to the
   `@moveinsync.com` hosted domain (`backend/google_auth.py` rejects any other `hd`).
   An admin sees everything, so there's no way to experience the developer / general
   role-scoped UI, or to exercise the approval gate, without real secondary Google accounts.

## Decisions (from brainstorming)

- **Admin split:** Option B — a dedicated **Approvals** tab (pending only) + a separate
  **Users** tab (approved only).
- **Role testing:** dev-only **email login** guarded by an env flag (option A). No
  self-impersonation switcher (rejected — risk of admin locking themselves out), no
  always-on email login (rejected — permanent prod auth bypass).
- **First dev-login behavior:** Option (a) — identical to a real first-time Google
  sign-up: created as `general` + `approved=false`. No role-picker at the login box;
  approval + role assignment happens through the admin Approvals tab. This exercises the
  full flow end-to-end.

## Feature 1 — Split admin into "Approvals" and "Users"

### Behavior
- **Approvals view** — lists ONLY pending users (`approved = false`). Each row: email,
  signup time, a **role-picker** (admin / developer / general), and an **Approve** button.
  Approving applies the chosen role AND sets `approved = true` in one user action. Once
  approved, the row leaves this view.
- **Users view** — lists ONLY already-approved users (`approved = true`) for ongoing
  management: change role later, delete/revoke.

### Implementation
- Primarily a frontend reorganization of `frontend/src/app/features/admin/admin-dashboard.ts`:
  split the existing single Users table into two sections/tabs, filtered client-side by the
  `approved` field already returned by `GET /admin/users`.
- **Atomic approve-with-role:** to avoid a two-call race (set role, then approve), add a
  combined backend endpoint `POST /admin/users/{email}/approve` that accepts an optional
  `role` in the body and, when present, sets the role and approval in a single DB write
  (one `UPDATE users SET role = %s, approved = TRUE WHERE email = %s`). The frontend
  Approvals action sends the picked role to this endpoint. Existing `PATCH .../role` stays
  for the Users tab's later role changes.
- Backend role validation continues to restrict to `{admin, developer, general}`.

### Out of scope
- No change to the approval *gate* logic (already enforced on `/query` + `/query/stream`).
- No change to per-user history filtering (already owner-scoped).

## Feature 2 — Dev-only email login (env-flag gated)

### Backend
- New env flag `CONWO_DEV_LOGIN` read in `backend/config.py` (default off). Set `true`
  only in local `.env`; never set in prod.
- New endpoint `POST /auth/dev-login`:
  - Returns 403 (or 404) immediately if `CONWO_DEV_LOGIN` is not true — provably inert
    in prod.
  - Validates the submitted email ends with `@moveinsync.com`.
  - Runs the SAME provisioning path as Google login: if the user does not exist, create
    as `role="general"`, `approved=false`. Mint and return a session token plus
    `{email, role, approved}` (mirrors `GoogleLoginResponse`).
  - Does NOT auto-approve. Does NOT accept a role from the caller.
- New public endpoint `GET /auth/config` returning `{ "dev_login": <bool> }` (reads the
  same flag) so the frontend can decide whether to render the dev-login box. No auth
  required; returns only the boolean.

### Frontend
- Login page (`frontend/src/app/features/login/login.ts`) calls `GET /auth/config` on load.
  When `dev_login` is true, render an **email input + "Dev sign in" button** below the
  Google button. When false (prod), the box is never rendered.
- Submitting posts to `/auth/dev-login`, stores the returned token + user info in
  localStorage using the SAME keys as Google login (`conwo_token`, `conwo_user_email`,
  `conwo_user_name`, `conwo_user_role`, `conwo_user_approved`), then routes normally.
  An unapproved test user therefore lands on the existing `/pending` screen, exactly like
  a real first-time sign-up.

### Safety properties
- **Prod:** flag off → `/auth/dev-login` rejects all calls AND `/auth/config` reports
  `dev_login=false` so the box never renders → only Google login works. The dev path is
  inert.
- **Dev:** type `general-test@moveinsync.com` → `/pending` → approve with a chosen role
  from the admin Approvals tab → sign in again → role-scoped experience. Exercises the
  approval gate, Approvals tab, role assignment, and role guards end-to-end.

## End-to-end test walkthrough (dev)

1. With `CONWO_DEV_LOGIN=true`, open an incognito window → login page shows the dev email box.
2. Dev-sign-in as `general-test@moveinsync.com` → created general+unapproved → lands on `/pending`.
3. In the admin window → **Approvals** tab shows `general-test@…` pending → pick `developer` → Approve.
4. Back in incognito → sign in again as `general-test@…` → now approved as developer →
   sidebar shows Ask / Search / Ingest / Graph only; Dashboard / Traces / Admin hidden;
   typing those URLs is blocked by the role guard; `/query` works (approved).
5. Repeat with `general-test2@…` approved as `general` to verify the general-scoped UI.

## Testing

- Backend:
  - `/auth/dev-login` returns 403 when `CONWO_DEV_LOGIN` is unset/false.
  - `/auth/dev-login` with flag on: creates a general+unapproved user, returns a working token.
  - `/auth/dev-login` rejects a non-`@moveinsync.com` email.
  - `/auth/config` reports the flag correctly for both states.
  - Combined approve-with-role endpoint: sets role + approved in one write; rejects an
    invalid role; 404 on unknown email.
- Frontend: build-verified; dev-login box renders only when `dev_login=true`.

## Constraints / operational notes

- Backend runs locally with `--reload`; the backend MUST be stopped before editing any
  `.py` files (project rule — a `.py` write triggers a uvicorn reload that rebuilds the
  in-memory wiki index).
- `CONWO_DEV_LOGIN` must be documented as dev-only in `docs/postgres-cutover.md` / the
  deploy env list so it is never set in prod.
- No new migration required (Feature 1 uses existing columns; Feature 2 adds no schema).
