# Per-user Agent Access Control + Request/Approve Flow

_Date: 2026-06-19_
_Status: approved (pending spec review)_

## Context
Conwo is a multi-agent platform: admins create agents (e.g. `conwo`, `infosec`, and
new ones at runtime). Today `GET /agents` returns **all** agents to everyone with no
auth, the switcher lists all, and any user can use any agent by setting `X-Agent-Id`.
There is no per-user access control.

We want: general/developer users do NOT automatically get every agent. They still **see**
all agents in the switcher, but agents they can't use are locked with a **"Request access"**
action. The request lands in the admin's **Manage Agents** inbox; when the admin approves
a (user, agent) request, that user can use that agent. Admins can also grant/revoke
directly. This mirrors the existing user-approval pattern.

## Decisions (confirmed with user)
- **Default-open agent:** the default agent (`agent_registry.default()`, i.e. `conwo`) is
  usable by everyone, no grant needed. Every *other* agent is gated.
- **Admins:** access all agents always (no grant check). Gating applies to general + developer.
- **Admin capability:** both approve/reject incoming requests AND directly grant/revoke any
  (user, agent).
- **Enforcement:** show all agents in the switcher; lock ungranted ones with "Request access";
  AND a server-side gate (essential — `X-Agent-Id` is otherwise trivially spoofable).

## Data model
Single table `agent_access`, PK `(user_email, agent_id)`:
```
user_email   TEXT
agent_id     TEXT
status       TEXT   -- pending | granted | rejected | revoked
requested_at TEXT
decided_at   TEXT
decided_by   TEXT   -- admin email who approved/rejected/granted/revoked
PRIMARY KEY (user_email, agent_id)
```
- Request access → upsert row `status='pending'`.
- Approve / direct grant → `granted`. Reject → `rejected`. Revoke → `revoked`.
- **Access check** (`has_access(user, agent_id)`): `True` if user role == `admin`
  OR `agent_id == agent_registry.default().id` OR a row exists with `status='granted'`.
- Inbox = rows with `status='pending'`.
- New idempotent migration `migrations/postgres/110_agent_access.sql` (applied at startup).

## Backend
- **`backend/agent_access.py`** (new) — all fail-safe (an access-store error denies
  non-default access but never raises into the request path):
  - `has_access(user: dict, agent_id: str) -> bool`
  - `request_access(email, agent_id) -> dict`  (upsert pending; no-op if already granted)
  - `set_status(email, agent_id, status, decided_by) -> bool`
  - `list_pending() -> list[dict]`            (admin inbox)
  - `list_for_user(email) -> dict[str,str]`    (agent_id → status, for the switcher)
  - `list_all_grants() -> list[dict]`          (admin grants view)
- **Server gate** — a FastAPI dependency `_require_agent_access` used on the agent-scoped
  query endpoints (`/query`, `/query/stream`, `/search`): resolves the active agent
  (`X-Agent-Id` via existing middleware) and the user; if `not has_access(user, agent_id)`
  → `HTTPException(403, detail="You don't have access to this agent. Request access from an admin.")`,
  `code="agent_access_required"`. Mirrors the existing approval gate; runs after auth.
- **Endpoints:**
  - `GET /agents/my-access` (authed) → `{ <agent_id>: "open"|"granted"|"pending"|"none" }`
    for the current user (admins: all `"open"`).
  - `POST /agents/{agent_id}/request-access` (authed) → creates/refreshes a pending request;
    rejects unknown/archived agent ids and the default agent (already open).
  - `GET /admin/agent-access/requests` (admin) → pending inbox (email, agent_id, requested_at).
  - `POST /admin/agent-access/{email}/{agent_id}/approve` (admin) → grant.
  - `POST /admin/agent-access/{email}/{agent_id}/reject` (admin) → reject.
  - `POST /admin/agent-access/{email}/{agent_id}/grant` (admin) → direct grant (no prior request).
  - `DELETE /admin/agent-access/{email}/{agent_id}` (admin) → revoke.
  - `GET /admin/agent-access/grants` (admin) → all granted (email, agent_id, decided_by).
- `GET /agents` stays public metadata (unchanged); access state is a separate authed call.

## Frontend
- **Switcher (`shared/mode-toggle/mode-toggle.ts`)** — on load also fetch `my-access`
  (via a signal in `AgentService`). Per agent:
  - `open` / `granted` → selectable (current behavior).
  - `pending` → shown with "Requested — pending", not selectable.
  - `none` → 🔒 + a **"Request access"** button → `POST /agents/{id}/request-access`
    → optimistic flip to `pending`.
  - Selecting a locked agent is prevented in `choose()`.
- **`core/agent.service.ts`** — add `access` signal (`agent_id → status`), `loadAccess()`,
  `requestAccess(id)`, and use access state to gate `setActive`.
- **Manage Agents (`features/admin/manage-agents.ts`)** — add two sections:
  - **Access requests** inbox: pending (email, agent) rows with Approve / Reject.
  - **Grants**: list granted (email, agent) with Revoke; a small form to grant a
    (email, agent) directly.
- **`core/api.service.ts`** — methods for all new endpoints.

## Edge cases
- Default agent always open even if a stale row exists; admin bypasses all checks.
- Revoking the user's active agent: their next request hits the 403 gate; the frontend
  catches `agent_access_required` and falls back to the default agent (resets `X-Agent-Id`).
- Re-request after reject: allowed (status returns to `pending`).
- Archived/deleted agent: `request-access` rejects unknown ids; `has_access` returns False
  for non-default unknown agents; orphan rows are harmless (ignored).
- Fail-safe: access-store/db error → non-default access denied (closed), request still
  returns normally; never crashes the endpoint.

## Testing
- Backend (mock/seed users + agents; real test DB):
  - general user, restricted agent, no grant → `/query` 403 `agent_access_required`.
  - same user, default agent (conwo) → allowed.
  - admin → any agent allowed (bypass).
  - request → approve → access now allowed; revoke → access denied again; reject → denied.
  - `my-access` returns correct per-agent status (open/granted/pending/none).
  - fail-safe: store error denies non-default, default still open.
- Frontend: `ng build` clean; switcher renders locked/pending/granted states.

## Out of scope
- Per-agent "open to all" admin flag (we hardcode the default agent as the only open one).
- Role-based bulk grants (e.g. "all developers get agent X") — per-(user, agent) only for now.
- Email/notification on request or approval (in-app inbox only).
