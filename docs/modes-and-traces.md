# Conwo modes, execution trace, and chat history

This doc explains what each query mode does, what the execution trace shows
(and what it deliberately does NOT show), and how chat history is stored.

---

## Query modes — what the user sees

The Ask page exposes **two** modes:

### 1. Deep Search  *(default — recommended for everyone)*

- Uses the **Anthropic API** with the user's API key.
- Runs an **agentic tool loop** (up to 8 rounds) against 9 controlled backend tools:
  `wiki_search`, `wiki_read_page`, `jira_search_ranked`, `jira_get_ticket`,
  `jira_named_query`, `pms_default_properties`, `pms_runtime_values`,
  `config_lookup`, `feedback_record`.
- **Billing** goes to the user's API key.
- **Returns a tool trace** (round, tool, sanitized input, output summary) that
  is shown in a collapsible "Evidence gathering" panel after the answer.
- Best for: normal users asking product / config / Jira-history questions.

### 2. Claude Code  *(runs the CLI on the BACKEND machine)*

- Spawns a **headless Claude Code subprocess** (`claude -p <question>
  --output-format=stream-json --verbose`) in the repo root.
- Has **full agentic capabilities** because cwd = repo root: it auto-loads
  `CLAUDE.md`, `.claude/settings.local.json`, `.mcp.json`, and all your skills.
  Full toolset: Read, Write, Edit, Bash, Grep, Glob, WebFetch, plus any MCP
  servers configured for that Claude Code installation (e.g. atlassian).
- **Streams live tool-use events** over Server-Sent Events. The UI renders
  each tool call as a card with input summary and status (running / done / error).
- **Auth/billing follows the BACKEND machine, not the browser.** If the
  backend is your laptop, it uses *your* Claude session and *your* repo. If
  the backend is a shared VM, it uses the session of whoever ran
  `claude login` on that VM.
- Best for: cross-repo investigations, ad-hoc Bash / grep / sqlite3 queries,
  agentic exploration where the 9-tool surface is insufficient.

#### Auth — local-dev vs deployed

Claude Code mode is gated by a Bearer token by default, because the endpoint
hands the caller a near-unrestricted shell on the backend machine. The token
is **our app's** auth, not Claude Code's — Claude Code itself authenticates
via `claude login` independently.

| Scenario | What to do | Auth behavior |
|----------|-----------|---------------|
| Backend runs on your own laptop, only you reach it on `localhost` | `export CONWO_LOCAL_CLAUDE_CODE=true` before starting `uvicorn` | Claude Code endpoints accept unauthenticated requests. UI hides the "token required" banner. Startup logs a `LOCAL-DEV` warning. |
| Backend deployed on a shared server / VM | **Do not set the env var.** Issue Bearer tokens via `config/allowed_users.toml`. | Default. Every Claude Code request must carry a valid `Authorization: Bearer …` header. |

**Never set `CONWO_LOCAL_CLAUDE_CODE` on a shared deployment.** Anyone who
can reach the backend would be able to drive the server's Claude Code
session — read files, run shell commands, push to MCP integrations.

The bypass is scoped to Claude Code endpoints only:
- `POST /query/stream`
- `POST /agent/log-answer`
- `POST /query` when `mode='claude-code'` (legacy single-shot)

Admin endpoints (`/admin/sync-status`, `/admin/feedback/*`, etc.) **still
require an admin token** regardless of `CONWO_LOCAL_CLAUDE_CODE`.

Frontend behavior:
- The Ask page hits `GET /health/claude-code` on load. The response now
  includes `local_dev_unauthenticated: true|false`.
- When true, the composer shows a "Local-dev mode" info notice instead of
  the "Bearer token required" banner, and the mode pill reads
  *"local · headless"*.
- When false (default), the existing "Bearer token required" banner stays.

### Legacy mode kept for backwards compatibility

There is a **legacy single-shot Claude Code endpoint** (the `mode=claude-code`
path on `/query`) that bundles wiki + Jira context into one prompt and runs
`claude -p` once with no tool loop. It is **hidden from the UI** because the
agentic Claude Code mode supersedes it. The backend endpoint remains so old
integrations don't break.

---

## Execution trace — what is shown

After every Deep Search answer, an **Evidence gathering** panel becomes
available below the answer. It is **collapsed by default** so the answer is
the first thing the user reads.

Each step in the trace shows:

| Field | Source |
|-------|--------|
| Round number | `entry.round` |
| Tool name | `entry.tool_name` |
| Source-type badge | derived from tool name (Wiki / Jira / PMS / Config / Feedback) |
| Sanitized input | `entry.input` (already secret-stripped by `ToolRegistry`) |
| Output summary | first 300 chars of the tool's JSON result |
| Status | success / error inferred from `entry.output_summary` |

The Claude Code (agent) mode renders a **live transcript** instead: each
streamed `tool_use` event becomes a card that flips from "running" to "done"
when the matching `tool_result` arrives.

## What the trace deliberately does NOT show

- **No hidden reasoning / chain-of-thought.** Only observable tool calls.
- **No secrets**: Bearer tokens, JWTs, and 40+ character hex strings are
  stripped by `backend/tools/registry.py::_sanitize_str` before they enter
  the trace.
- **No PMS auth tokens or cookies** (`pms_tools.py` reads them from env
  variables and never includes them in tool output).
- **No raw stdout from arbitrary shell commands** (Deep Search has no Bash
  tool; only the 9 whitelisted tools).
- **No filesystem reads outside `wiki/`** (`wiki_read_page` rejects `..`,
  leading `/`, and any path that resolves outside `WIKI_DIR`).
- **No arbitrary SQL** (only the 4 named queries in `jira_named_query`).

The Claude Code (agent) mode has wider tool access by design (Read, Write,
Edit, Bash, etc.), so its trace surfaces those tool inputs verbatim from
Claude Code's `stream-json` output. **It requires an admin Bearer token and
should only be granted to power users.** The trace still respects the
same secret-stripping for any secrets that happen to appear in tool outputs.

---

## Chat history — how conversations are stored

### Storage

- SQLite database at `raw/conversations/conversations.sqlite` — **not
  committed to git** (added to `.gitignore`).
- Tables:
  - `conversations(id, title, created_at, updated_at)`
  - `messages(id, conversation_id, role, content, created_at, mode, server,
    buid, answer_id, confidence, sources_json, tool_trace_json,
    missing_context_json)`
- `role` ∈ {user, assistant, system}.
- Foreign-key `ON DELETE CASCADE` so deleting a conversation removes its
  messages atomically.

### What's persisted in a message

A user message stores only `content` (the verbatim question) and the
ambient scope (`server`, `buid`, etc.).

An assistant message stores everything the answer card needs to re-render
identically when the chat is reopened:
- `content` (the answer text)
- `answer_id` (links to `feedback_service.log_answer` records)
- `confidence`, `mode`
- `sources_json` (wiki/jira/pms — same shape as `SourceInfo`)
- `tool_trace_json` (already sanitized by `ToolRegistry`)
- `missing_context_json`

### What's never persisted

- **Anthropic API keys.** The user provides their API key per-request via
  `claude_api_key` in the `/query` body. It is never stored in the
  conversation DB or echoed back. (Frontend keeps it in browser
  `localStorage` only — same as before.)
- **PMS tokens / cookies.** They live in env vars on the server and never
  enter trace output (see `pms_tools.py::_get_tokens`).
- **Admin Bearer tokens.** Auth is checked per-request from the
  `Authorization` header; tokens are not written to the conversation DB.
- **Hidden reasoning / thinking blocks.** Only the final answer text and
  the observable tool trace are saved.

### API

| Method | Path | What it does |
|--------|------|--------------|
| `POST` | `/conversations` | Create a new empty conversation with optional title |
| `GET` | `/conversations` | List all conversations (id, title, timestamps, message count) |
| `GET` | `/conversations/{id}` | Return full conversation including all messages |
| `PATCH` | `/conversations/{id}` | Update title |
| `DELETE` | `/conversations/{id}` | Delete conversation and all its messages |
| `POST` | `/query` | Accepts optional `conversation_id`. If absent, a new conversation is created and its id is returned in the response. User + assistant messages are saved. |

### Clearing chat history

To purge all conversations:

```bash
rm /Users/<you>/Desktop/my-wiki/org-wiki/raw/conversations/conversations.sqlite
# next request will recreate the file with an empty schema
```

To delete one chat: `DELETE /conversations/{id}` via the API, or click the
trash icon next to the chat in the sidebar.

---

## Mode picker UI helper text

The mode selector shows short helper text:

- **Deep Search** — "Anthropic API · 9 backend tools · shows evidence trail"
- **Claude Code** — "Server's Claude Code session · admin only · full agent"

Normal users only see Deep Search unless they have an admin token configured;
the Claude Code option is dimmed otherwise.
