# Conwo Multi-User API Product — Design Spec
_Date: 2026-05-21 | Status: draft_

---

## Context

Convert the local, Claude-Code-driven Conwo knowledge system into a multi-user internal
product for WorkInSync support, CSM, and product teams. The system already has a FastAPI
backend (`backend/api.py`), an Angular frontend (`frontend/`), and a working agentic
deep-search tool loop (`backend/providers/deep_query.py`, 9 tools, all tests passing).

The primary blockers for expanding beyond the original admin user are:
1. Every `/query` call requires the user to supply their own Anthropic API key in the request body
2. PMS tools (`pms_runtime_values`, `pms_default_properties`) have no role enforcement
3. The Claude Code stream endpoint (`/query/stream`) is reachable by any bearer-token holder
4. Conversation history is not scoped to users and not threaded into the tool loop
5. Auth is a flat-file TOML with no token expiry or self-service provisioning
6. Jira sync and Drive sync run manually; no automation

---

## Approach: Option C — Hybrid Layered

Ship in three independent layers. Each layer is valuable on its own and deploys without
breaking the current system. Keep SQLite throughout (WAL mode; adequate for <100 concurrent
users). No Postgres required for the pilot.

**Layer 1 (Week 1–2):** Server-side API key + role enforcement + auth hardening
**Layer 2 (Week 3–4):** Conversation context threading + self-service token provisioning
**Layer 3 (Week 5–6):** Sync automation (Jira + Drive crons) + wiki edit approval queue

---

## Open Questions — Resolved

| Question | Decision |
|----------|----------|
| Jira sync automation | Set up VM cron as part of this work (Week 5) |
| Atlassian MCP on shared VM | Acceptable for admin users |
| Who gets pms_debug role? | All authenticated users — no pms_debug gating |
| Drive sync automation | Automated: daily cron + admin-triggered on-demand (Week 5) |

---

## 1. Tool Registry

### Existing tools — unchanged schemas

All 9 tools in `backend/tools/` keep their current schemas. Changes are in dispatch only.

| Tool | File | Min role | Change |
|------|------|----------|--------|
| `wiki_search` | `wiki_tools.py` | any | None |
| `wiki_read_page` | `wiki_tools.py` | any | None |
| `jira_search_ranked` | `jira_tools.py` | any | None |
| `jira_get_ticket` | `jira_tools.py` | any | None |
| `jira_named_query` | `jira_tools.py` | any | None |
| `config_lookup` | `config_tools.py` | any | None |
| `feedback_record` | `feedback_tools.py` | any | Populate `reviewer` from user email |
| `pms_default_properties` | `pms_tools.py` | any (all authenticated) | Role check in registry |
| `pms_runtime_values` | `pms_tools.py` | any (all authenticated) | Role check in registry |

### Role enforcement in `ToolRegistry`

**File: `backend/tools/registry.py`**

Add `user_role: str = "viewer"` to `__init__`. Add `_TOOL_PERMISSIONS` dict and role check
in `execute()`:

```python
# Role hierarchy
_ROLE_ORDER = {"viewer": 0, "contributor": 1, "admin": 2}
_TOOL_PERMISSIONS: dict[str, str] = {}  # empty = all tools available to all roles
# (pms tools require any authenticated user, so no entry needed)

class ToolRegistry:
    def __init__(self, user_role: str = "viewer") -> None:
        self._user_role = user_role
        self._handlers: dict[str, Callable] = {}
        self._schemas: list[dict] = []

    def execute(self, name, tool_input, round_num):
        required = _TOOL_PERMISSIONS.get(name, "viewer")
        if _ROLE_ORDER.get(self._user_role, 0) < _ROLE_ORDER.get(required, 0):
            result = json.dumps({"error": f"Role '{self._user_role}' cannot call '{name}'",
                                 "code": "permission_denied"})
            entry = ToolTraceEntry(round=round_num, tool_name=name,
                                   input={}, output_summary=result[:300])
            return result, entry
        # ... existing dispatch logic unchanged
```

**File: `backend/tools/__init__.py`**

```python
def build_registry(user_role: str = "viewer") -> ToolRegistry:
    r = ToolRegistry(user_role=user_role)
    # ... existing registrations unchanged
```

**File: `backend/orchestrator.py`**

`run_deep()` and `run_single_shot()` gain a `user_role: str = "viewer"` parameter.
`run()` passes it through from the API layer.

### New tool — Layer 3: `wiki_propose_edit`

**File: `backend/tools/wiki_tools.py`** (added to existing file)

```python
WIKI_PROPOSE_EDIT_SCHEMA = {
    "name": "wiki_propose_edit",
    "description": (
        "Submit a proposed correction to a wiki page for admin review. "
        "Use when tool results contradict existing wiki content. "
        "Does NOT write directly — creates a proposal requiring admin approval."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "page_path": {"type": "string",
                          "description": "Relative path e.g. 'modules/visitor-management.md'"},
            "proposed_change": {"type": "string",
                                "description": "What is incorrect and what it should say"},
            "answer_id": {"type": "string", "description": "The answer_id this proposal is based on"},
        },
        "required": ["page_path", "proposed_change"]
    }
}
# Handler writes to raw/feedback/wiki_proposals.jsonl — never to wiki/ directly
# Registered only when build_registry() caller has role contributor or admin
```

---

## 2. System Prompt Strategy

### Deep search prompt — unchanged through Layer 2

`backend/deep_system_prompt.py` stays as-is. It is already well-scoped (~2KB) and
correctly excludes wiki-authoring workflows (CLAUDE.md Sections 4, 6, 7, 8, 11).

### What must NOT enter the system prompt

- INGEST workflow (Sections 4, 7, 8, 11 of CLAUDE.md) — wiki authoring is Claude Code only
- LINT workflow (Section 6) — maintenance/admin only
- Session start checklist (Section 8) — irrelevant per-request
- Server architecture table (Section 1) — factual; belongs in wiki/configs/ pages

### Layer 2 — conversation context threading

The system prompt does not change. The `messages[]` array passed to the Anthropic API gains
prior conversation turns.

**File: `backend/orchestrator.py`** — add helper:

```python
def _load_conversation_context(conversation_id: str, max_turns: int = 6) -> list[dict]:
    """Return last N user+assistant message pairs from conversation history."""
    conv = conversation_store.get_conversation(conversation_id)
    if not conv:
        return []
    msgs = [m for m in conv["messages"] if m["role"] in ("user", "assistant")]
    # Take last max_turns * 2 messages (N user + N assistant)
    tail = msgs[-(max_turns * 2):]
    return [{"role": m["role"], "content": m["content"]} for m in tail]
```

In `run_deep()`:
```python
history = _load_conversation_context(conversation_id, max_turns=6) if conversation_id else []
messages = history + [{"role": "user", "content": user_message}]
```

Cap: 6 prior turns (~12K tokens). If the conversation is long enough that the full history
would exceed this, older messages are silently truncated (FIFO). This is safe because the
answer structure (Answer/Sources/Confidence) is self-contained per turn.

---

## 3. Hard-Coded Guardrails

Enforced in code, not in the system prompt.

| Guardrail | Status today | Layer 1 fix | File |
|-----------|-------------|-------------|------|
| SELECT-only on Jira SQLite | ✅ `mode=ro&immutable=1` | — | `jira_retriever.py` |
| No arbitrary SQL | ✅ Named query whitelist | — | `jira_tools.py` |
| Wiki path traversal block | ✅ `..` + `resolve()` check | — | `wiki_tools.py` |
| Secrets stripped from trace | ✅ `_SECRET_RE` sanitizer | — | `registry.py` |
| PMS tokens never in output | ✅ env-only credential read | — | `pms_tools.py` |
| Claude Code stream — admin only | ❌ any bearer token | Change to `_require_admin` | `api.py` |
| Server-side API key | ❌ required in request body | `resolve_api_key()` checks env first | `api.py`, `config.py` |
| Conversation ownership | ❌ any user sees all convs | Filter by `user_email` | `conversation_store.py` |
| Token expiry | ❌ tokens never expire | Add `expires_at` to TOML lookup | `config.py` |
| Wiki index stale after apply | ❌ not wired | Call `rebuild_index()` in `apply_patch()` | `admin_api.py` |
| Rate limiting per user | ❌ none | 30 queries/day for viewer/contributor (in-memory counter per token, resets midnight UTC), unlimited for admin | `api.py` middleware |
| Wiki propose-edit — no direct write | ❌ (tool doesn't exist) | Handler writes to JSONL only | `wiki_tools.py` (L3) |

---

## 4. State Model

### Keep SQLite throughout

SQLite with WAL mode handles the expected load (<100 concurrent users, <30 queries/min peak).
No Postgres required for the pilot.

### Layer 1 — conversation ownership

**Migration: `migrations/001_add_user_email_to_conversations.sql`**

```sql
ALTER TABLE conversations ADD COLUMN user_email TEXT;
UPDATE conversations SET user_email = 'rudra.khare@moveinsync.com'
WHERE user_email IS NULL;
```

`conversation_store.create_conversation()` gains `user_email: str | None = None` param.
`list_conversations()` gains `user_email: str | None = None` filter — when set, returns only
that user's conversations; when None (admin call), returns all.

### Layer 1 — token expiry in TOML

Add `expires_at` field (ISO date string, optional) to `config/allowed_users.toml`:

```toml
[users.alice]
email = "alice@moveinsync.com"
role = "contributor"
token = "..."
expires_at = "2026-12-01"  # omit for no-expiry (admin only)
```

`config.py::lookup_user_by_token()`:

```python
def lookup_user_by_token(token: str) -> dict | None:
    for _name, user in _load_users().items():
        if user.get("token") != token:
            continue
        expires = user.get("expires_at")
        if expires and date.fromisoformat(expires) < date.today():
            return None   # expired
        return user
    return None
```

### Layer 2 — auth SQLite

New file: `backend/auth_store.py`. New DB at `raw/auth/auth.sqlite`.

```sql
CREATE TABLE users (
    email       TEXT PRIMARY KEY,
    role        TEXT NOT NULL DEFAULT 'viewer',
    created_at  TEXT NOT NULL,
    created_by  TEXT
);

CREATE TABLE tokens (
    token       TEXT PRIMARY KEY,
    user_email  TEXT NOT NULL REFERENCES users(email) ON DELETE CASCADE,
    created_at  TEXT NOT NULL,
    expires_at  TEXT,           -- NULL = no expiry
    revoked     INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX idx_tokens_email ON tokens(user_email);
CREATE INDEX idx_tokens_revoked ON tokens(revoked, expires_at);
```

`config.py::lookup_user_by_token()` checks `auth.sqlite` first; falls back to TOML for
migration compatibility. TOML users continue to work until migrated.

### Existing stores — unchanged schemas

- `raw/jira/tickets.sqlite` — no changes
- `raw/conversations/conversations.sqlite` — schema migration only (Week 1)
- `raw/feedback/answer_log.jsonl` — no changes
- `raw/feedback/answer_feedback.jsonl` — no changes

---

## 5. Sandboxing Plan

### Layer 1 — minimum viable (2 line changes)

In `backend/api.py`, change `/query/stream` and `/agent/log-answer` from:
```python
user: dict = Depends(_require_user_or_local_dev)
```
to:
```python
user: dict = Depends(_require_admin)
```

The subprocess still runs on the host with full tool access. Only admins can trigger it.
This is acceptable for the pilot where admin = Rudra only.

### Layer 3 — container sandbox (if Claude Code agent is opened to more users)

The subprocess today runs `claude -p <question> --output-format=stream-json` with
`cwd=REPO_ROOT` and `env={**os.environ}`. What it legitimately needs:

- Read `wiki/`, `raw/jira/tickets.sqlite`, `raw/modules/`, `scripts/`, `docs/`, `CLAUDE.md`
- Run `sqlite3` read-only queries, `python scripts/query_jira_ranked.py`
- Network to Atlassian MCP (Jira read) + PMS API (`wis.moveinsync.com/in`)
- No writes to `config/`, `backend/`, `raw/feedback/`, git remote

Container spec (if needed post-pilot):
```
Image:      python:3.12-slim + claude CLI
Mounts:     wiki/ → /repo/wiki (ro)
            raw/jira/tickets.sqlite → /repo/raw/jira/tickets.sqlite (ro)
            raw/modules/ → /repo/raw/modules (ro)
            scripts/ → /repo/scripts (ro)
            docs/ → /repo/docs (ro)
            CLAUDE.md → /repo/CLAUDE.md (ro)
Network:    egress to *.atlassian.net + *.moveinsync.com only
User:       uid 1000 (non-root)
Timeout:    120s
Memory:     512MB
Env:        JIRA_*, PMS_TOKEN_*, ANTHROPIC_API_KEY
```

---

## 6. Permission and Approval Flow

### Role hierarchy

```
viewer  <  contributor  <  admin
```

All three roles can trigger PMS tools (pms_debug is not a separate gate; any authenticated
user can call `pms_default_properties` and `pms_runtime_values`).

### Per-role capability table

| Capability | viewer | contributor | admin |
|-----------|--------|-------------|-------|
| POST /query (deep search, server key) | ✅ | ✅ | ✅ |
| POST /search | ✅ | ✅ | ✅ |
| GET /wiki/{path} | ✅ | ✅ | ✅ |
| GET /conversations (own) | ✅ | ✅ | ✅ |
| GET /conversations (all) | ❌ | ❌ | ✅ |
| POST /feedback | ✅ | ✅ | ✅ |
| pms_default_properties tool | ✅ | ✅ | ✅ |
| pms_runtime_values tool | ✅ | ✅ | ✅ |
| wiki_propose_edit tool (L3) | ❌ | ✅ | ✅ |
| POST /query/stream (agent) | ❌ | ❌ | ✅ |
| GET/POST /admin/* | ❌ | ❌ | ✅ |
| POST /admin/users (L2) | ❌ | ❌ | ✅ |
| GET /admin/wiki/proposals (L3) | ❌ | ❌ | ✅ |

### Server-side API key

`backend/config.py`:
```python
def resolve_api_key(request_key: str | None) -> str:
    server_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if server_key:
        return server_key         # server key wins; caller key is ignored
    if request_key:
        return request_key        # fallback: caller-supplied (local dev / testing)
    raise ValueError("No Anthropic API key. Set ANTHROPIC_API_KEY on server or pass claude_api_key in request.")
```

`GET /health` response adds `"has_server_key": bool(os.getenv("ANTHROPIC_API_KEY"))`.
Frontend hides the API key input field when this is `true`.

### Layer 3 — wiki edit approval flow

```
1. Contributor submits low-score feedback (score ≤ 2, correction non-empty)
   → feedback_service.record_feedback() runs as today
   → backend auto-creates a wiki_proposal record (page_path from affected[],
      proposed_change from correction text, submitter email)

2. Admin sees proposal in GET /admin/wiki/proposals (new endpoint)
   → Shows: page_path, proposed_change, answer_id, submitter, created_at, status

3. Admin calls POST /admin/wiki/proposals/{id}/apply
   → Runs apply_feedback.py --feedback-id {fid} --apply
   → Calls wiki_retriever.rebuild_index()
   → Updates proposal status to "applied"

   OR POST /admin/wiki/proposals/{id}/reject
   → Updates proposal status to "rejected" with optional admin note
```

No new frontend tab required until Layer 3. The existing admin panel at
`frontend/src/app/features/admin/` is extended with a Proposals section.

---

## 7. Migration Path

### Files reused unchanged

`backend/tools/wiki_tools.py`, `jira_tools.py`, `config_tools.py`, `feedback_tools.py`,
`backend/jira_retriever.py`, `backend/wiki_retriever.py`, `backend/preflight.py`,
`backend/deep_system_prompt.py`, `backend/feedback_service.py`,
`backend/providers/deep_query.py`, `backend/providers/anthropic_api.py`,
`backend/providers/claude_code_agent.py`,
`scripts/jira_sync.py`, `scripts/sync_drive.py`, `scripts/apply_feedback.py`,
all other scripts.

### Files modified

| File | Layer | What changes |
|------|-------|-------------|
| `backend/api.py` | L1 | `resolve_api_key()`, `_require_admin` on stream endpoints, user_email into create_conversation, `has_server_key` in /health, rate-limit middleware |
| `backend/config.py` | L1 | `resolve_api_key()`, `expires_at` check in `lookup_user_by_token()` |
| `backend/tools/registry.py` | L1 | `user_role` param, `_TOOL_PERMISSIONS`, role check in `execute()` |
| `backend/tools/__init__.py` | L1 | `build_registry(user_role=)` |
| `backend/orchestrator.py` | L1+L2 | Thread `user_role` to registry; L2: `_load_conversation_context()` |
| `backend/admin_api.py` | L1 | Call `wiki_retriever.rebuild_index()` after `apply_patch()` |
| `backend/conversation_store.py` | L1 | `user_email` column + filter in `list_conversations()` |
| `config/allowed_users.toml` | L1 | Add `expires_at` field per user |
| `backend/tools/wiki_tools.py` | L3 | Add `wiki_propose_edit` schema + handler |
| `backend/tools/__init__.py` | L3 | Register `wiki_propose_edit` |
| `backend/admin_api.py` | L3 | `get_wiki_proposals()`, `apply_wiki_proposal()`, `reject_wiki_proposal()`, `trigger_drive_sync()` |
| `frontend/src/app/features/admin/` | L3 | Drive sync button, Proposals tab |

### Files added (net new)

| File | Layer | Purpose |
|------|-------|---------|
| `migrations/001_add_user_email_to_conversations.sql` | L1 | ALTER TABLE conversations |
| `backend/auth_store.py` | L2 | SQLite-backed user + token management |
| `migrations/002_auth_store.sql` | L2 | users + tokens tables |
| `backend/wiki_proposals.py` | L3 | Proposal store (JSONL) + CRUD helpers |
| `deploy/crontab.example` | L3 | Jira + Drive cron schedule for VM deployment |

### Files deleted

None. The legacy `mode=claude-code` single-shot path and `system_prompt.py` stay for
backwards compatibility.

---

## 8. Week-by-Week Build Plan

| Week | Deliverable | DoD |
|------|-------------|-----|
| 1 | Server-side key + role enforcement on stream endpoints + index rebuild on apply | Support user can query without API key; admin-only stream; wiki index refreshes after apply |
| 2 | Token expiry + conversation ownership scoping | Expired tokens return 401; users see only own conversations |
| 3 | Conversation context threading (max 6 turns) | Follow-up question in same conversation uses prior answer context |
| 4 | Self-service token provisioning via `POST /admin/users` | Admin onboards new user in <30s via API call; DELETE revokes immediately |
| 5 | Jira + Drive cron automation + admin-triggered sync | At 02:00 daily Jira refreshes; 03:00 Drive syncs; admin can force either |
| 6 | Wiki edit approval queue + Drive sync UI | Contributor feedback auto-creates proposal; admin applies or rejects from UI |

---

## 9. Eval Set (20 questions)

The system must answer all 20 correctly for the pilot to be considered successful.

### Config property lookups

1. "What does `kioskRequireOTPBeforeRegister` do and what is its default value?"
2. "What is the difference between `showEmployeeProfileOfficeOnly` on .com vs .in?"
3. "What does `mealCutoffInMinutes` control and where does it apply?"
4. "Is `hideBookingTimeMealOnly` a visitor management or desk management config?"
5. "What PMS configs exist for the Guard App service?"
6. "What does `indemnifyOfficeBookingTransport` do?" _(ETS — not in config sheets, Jira only)_

### Feature behavior

7. "How does visitor management OTP verification work end-to-end?"
8. "What is the difference between floor kiosk and guard app kiosk registration?"
9. "How does SSO provisioning connect to access management?"
10. "What happens when a meeting room booking is cancelled — is the slot immediately available?"
11. "How does the mobile app handle offline mode for desk booking?"

### Live config debug

12. "Why might a config change at BUID level not take effect for a specific office?"
13. "What is the config hierarchy for PMS properties — which level wins?"
14. "If `pms_runtime_values` returns `credentials_required`, what should I do?"

### Jira-heavy

15. "What are the most recently resolved issues in WF-empexp?"
16. "What Jira tickets mention `showCabs` or ETS transport config?"
17. "Has there been any recent change to how kiosk OTP works? Show me the evidence."

### Cross-module

18. "How does desk management relate to parking management for combined bookings?"
19. "Which modules depend on employee provisioning?"

### Multi-turn (requires Week 3)

20. "What is visitor management?" → (follow-up) "What are the known issues with OTP in visitor management?"

---

## 10. Security Checklist (per layer)

**Layer 1:**
- [ ] `ANTHROPIC_API_KEY` not logged, not returned in any API response
- [ ] `/query/stream` returns 403 for non-admin bearer tokens
- [ ] `pms_default_properties` and `pms_runtime_values` work correctly for `viewer` role (all authenticated users have access — confirm no false permission_denied in tests)
- [ ] Expired tokens return 401, not 403

**Layer 2:**
- [ ] `POST /admin/users` accessible only to admin role
- [ ] Token rotation invalidates old token immediately
- [ ] `raw/auth/auth.sqlite` added to `.gitignore`

**Layer 3:**
- [ ] `wiki_propose_edit` writes to JSONL, never to `wiki/`
- [ ] Drive sync cron uses read-only Drive API scope
- [ ] `crontab.example` does not contain real credentials
