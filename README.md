# Conwo — WorkInSync Knowledge Agent

An AI-powered knowledge base and query agent for the WorkInSync product team. Ask questions about features, PMS configs, Jira tickets, and architecture — and get synthesised answers backed by source evidence.

---

## What This Is

| Layer | What it does |
|-------|-------------|
| **`raw/`** | Source of truth — PDFs, specs, transcripts, Jira SQLite mirror. AI reads, never writes. |
| **`wiki/`** | AI-maintained structured markdown pages. Browsable in Obsidian. |
| **`backend/`** | FastAPI server — query engine, auth, conversation history, Jira search, PMS live config. |
| **`frontend/`** | Angular 17 web app — Ask, Search, Dashboard, Traces, Ingest, Admin. |
| **`CLAUDE.md`** | The AI's rulebook for wiki maintenance and query answering. |

---

## Features

- **Ask** — AI-synthesised answers combining wiki pages + Jira tickets + PMS live config values
- **Search** — retrieval-only wiki + Jira search (no LLM call)
- **Conversation history** — per-user chat threads, persisted in SQLite
- **Document ingest** — upload PDFs/docs from the browser; AI extracts and writes wiki pages
- **Traces & Dashboard** — observability for every query (latency, cost, token usage)
- **Admin panel** — user management, wiki proposals, feedback review, Jira sync triggers
- **PMS live config debug** — fetch and compare actual property values from `.com` / `.in` servers for a given BUID

---

## Authentication

Users sign in with their **@moveinsync.com Google account** — no token sharing needed.

- Any `@moveinsync.com` account is auto-approved on first sign-in (role: `viewer`)
- Admin role is managed via `config/allowed_users.toml` or `POST /admin/users`
- Sessions are stored in `raw/auth/auth.sqlite`; revocable via the Admin panel

---

## Setup

### Prerequisites

- Python 3.11+ with a venv at `venv/`
- Node.js 18+ for the frontend
- A Google Cloud OAuth 2.0 Client ID (Web application type)
- An Anthropic API key

### Backend

```bash
# Install dependencies
pip install -r requirements-backend.txt

# Copy and fill in credentials
cp .env.example .env   # add ANTHROPIC_API_KEY, GOOGLE_CLIENT_ID, PMS tokens

# Start
venv/bin/uvicorn backend.api:app --reload --port 8000
```

The backend auto-loads `.env` on startup.

### Frontend

```bash
cd frontend

# Set your Google Client ID in:
# src/app/features/login/login.ts → const GOOGLE_CLIENT_ID = '...'

npm install
npm start          # dev server at http://localhost:4200
npm run build      # production build → dist/
```

### First run

1. Start both servers
2. Open `http://localhost:4200`
3. Sign in with your `@moveinsync.com` Google account
4. You're in

---

## Project Structure

```
org-wiki/
├── backend/
│   ├── api.py               # FastAPI app — all endpoints
│   ├── auth_store.py        # SQLite user + token store
│   ├── google_auth.py       # Google ID token verification
│   ├── conversation_store.py
│   ├── wiki_retriever.py
│   ├── orchestrator.py      # Query engine (wiki + Jira + LLM)
│   └── ...
├── frontend/
│   └── src/app/
│       ├── features/ask/    # Main query UI
│       ├── features/login/  # Google Sign-In
│       ├── features/admin/  # Admin dashboard
│       ├── features/traces/ # Observability
│       └── core/            # Auth guard, interceptor, API service
├── wiki/                    # AI-maintained markdown pages
├── raw/                     # Source documents (gitignored: jira sqlite, .env)
├── config/
│   └── allowed_users.toml   # Admin user + legacy token config
├── tests/                   # pytest suite
├── scripts/                 # CLI utilities (Jira sync, PMS debug, feedback)
├── docs/
│   └── superpowers/         # Design specs and implementation plans
└── CLAUDE.md                # AI session instructions
```

---

## API Endpoints

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| `POST` | `/auth/google` | Exchange Google ID token for session token | Public |
| `POST` | `/query` | AI-synthesised answer (API mode) | Bearer |
| `POST` | `/query/stream` | Streaming Claude Code agent answer | Bearer |
| `POST` | `/search` | Retrieval-only wiki + Jira | Bearer |
| `GET` | `/conversations` | List user's chat history | Bearer |
| `GET` | `/status` | Operational status | Bearer |
| `GET` | `/health` | Liveness + wiki page count | Public |
| `GET/POST` | `/admin/*` | Admin operations | Admin Bearer |
| `GET` | `/api/traces/*` | Query traces + cost dashboard | Bearer |

---

## Running Tests

```bash
venv/bin/pytest tests/ --ignore=tests/test_local_claude_code.py -v
```

~260 tests covering auth, query engine, conversation store, wiki tools, Jira search, and PMS config.
