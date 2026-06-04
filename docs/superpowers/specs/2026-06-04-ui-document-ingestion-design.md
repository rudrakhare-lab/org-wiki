# UI Document Ingestion — Design Spec
_Date: 2026-06-04_

## Context

Document ingestion currently requires Claude Code running locally in a terminal. An operator reads a raw file from `raw/modules/<slug>/`, follows the 9-step CLAUDE.md §4 workflow, and writes 5–15 wiki pages using filesystem tools (Read, Write, Edit, Bash). This works but is bottlenecked on terminal access.

**Goal:** Expose the same ingestion capability in the web UI so any authenticated user can upload a document and have the wiki updated — with a human review gate before any file is written. No Claude Code subprocess. Anthropic API only, matching how the rest of the product works.

---

## Scope (v1 constraints)

**In scope:**
- Single file upload (PDF, DOCX, XLSX, MD, TXT)
- Two-phase ingestion: Plan (read-only agent) → Human approval → Execute (write agent)
- All authenticated users can access `/ingest`
- One concurrent ingestion at a time (mutex)
- Streaming progress during execute phase
- File moved to canonical `raw/modules/{slug}/` location on success

**Out of scope (v1):**
- Bulk upload / batch ingestion
- Git commit per ingestion
- Partial-write rollback / atomic transactions
- Re-ingest of existing docs (if slug matches, plan warns and recommends abort)
- Ingestion history page
- Edit-the-plan before approving (approve or cancel only)
- Diff visualization (show operations as a list, not full diffs)

---

## Architecture: Two-Phase

```
Upload → Extract → Plan agent (read-only) → Human reviews → Approve → Execute agent (write) → Done
```

**Why two separate agent runs:**
The approval gate sits between two API calls — a natural pause requiring no long-polling or PTY tricks. Phase 1 agent physically cannot write (write tools are not registered for it). Phase 2 agent receives the plan as a strict instruction and executes literally — no re-classification.

**Session state:** Plan stored in-memory, keyed by `session_id`, 10-minute TTL. On backend restart sessions are lost — user re-uploads (fast since extraction reruns).

---

## Backend

### New files

```
backend/
├── ingest_api.py          # 3 endpoints, authenticated (not admin-gated)
├── ingest_service.py      # mutex, session state, phase orchestration
├── document_extractor.py  # pdfplumber / python-docx / openpyxl wrappers
└── tools/
    └── wiki_write_tools.py  # 5 write tools (registered only in Phase 2)
```

### Endpoints

| Endpoint | Method | Auth | What it does |
|---|---|---|---|
| `/api/ingest/upload` | POST multipart | Any user | Validates file type, saves to `raw/modules/_uploads/{uuid}/{filename}`, returns `upload_id` |
| `/api/ingest/plan` | POST JSON | Any user | Runs Phase 1 agent, returns `session_id` + structured JSON plan. `409` if mutex held. |
| `/api/ingest/execute` | POST SSE | Any user | Runs Phase 2 agent, streams per-file events. `410` if session expired. Moves file on success. |

### Extraction tools (Phase 1 only)

- `extract_pdf(file_path)` — pdfplumber, concatenates all pages, truncates at 50k chars, returns `{text, page_count, char_count}`
- `extract_docx(file_path)` — python-docx, iterates paragraphs + tables, returns `{text, char_count, has_tables}`
- `extract_xlsx(file_path)` — openpyxl, iterates sheets/rows/cells, returns `{sheets: [{name, rows}]}` — each sheet treated separately for config XLSXs

### Wiki write tools (Phase 2 only)

- `wiki_create_page(path, frontmatter, body)` — creates new `.md` file. Validates path is inside `wiki/`. Refuses with error if file already exists (no silent overwrite).
- `wiki_edit_page(path, old_str, new_str)` — targeted string replacement. Errors if `old_str` not found or appears more than once.
- `wiki_append_section(path, heading, content)` — appends new `## heading` section at end of file. Errors if heading already exists.
- `wiki_update_frontmatter(path, field, value)` — appends `value` to a list field (`depends_on`, `used_by`) without duplicating. Errors on unknown fields.
- `wiki_rebuild_index()` — calls `wiki_retriever.build_index()` in-process. Does NOT touch `backend/api.py` — no reload race, no wiki-destruction risk.

### Read tools available in Phase 1

Reuse existing registry tools: `wiki_search`, `wiki_read_page`, `wiki_list_pages` (new), `wiki_check_duplicate` (new), plus the extraction tools above.

### Mutex and session

```python
# ingest_service.py
_ingest_lock = threading.Lock()   # one ingestion at a time
_sessions: dict[str, IngestSession] = {}  # session_id → plan + TTL

@dataclass
class IngestSession:
    session_id: str
    upload_id: str
    plan: dict
    created_at: float   # TTL: 600 seconds
    slug: str
    filename: str
    original_path: str  # raw/modules/_uploads/{uuid}/{filename}
```

### File lifecycle

1. Upload → `raw/modules/_uploads/{uuid}/{original_filename}`
2. Execute success → moved to `raw/modules/{slug}/{original_filename}`
3. `raw_path` frontmatter in `wiki/sources/<slug>.md` points to final location
4. `audit_ingest.py` finds it correctly on next session start

---

## System Prompts

### Phase 1 — Ingestion Planner (~1,400 chars)

```
You are an ingestion planner for the WorkInSync org wiki.
A document has been uploaded. Your job: read it, classify it,
identify cross-references with the existing wiki, and produce
a structured JSON plan. You MUST NOT write anything — you have
no write tools.

WIKI STRUCTURE:
- wiki/sources/<slug>.md       — every ingested doc gets one
- wiki/modules/<slug>.md       — product modules
- wiki/entities/<slug>.md      — data models / domain objects
- wiki/cross-module/<a>-<b>.md — when two modules connect
- wiki/decisions/<date>-<title>.md — architecture decisions
- wiki/configs/<slug>.md       — PMS config tables

SLUG RULES: lowercase-hyphenated, match the module folder name.
Always call wiki_check_duplicate before proposing a new slug.

BIDIRECTIONALITY: if module A depends_on B, then B must have
used_by A. Flag any asymmetry as a warning in your plan.

CLASSIFICATION ORDER:
1. Folder context — raw/modules/<slug>/ tells you the module
2. Doc type from content (PRD, SOP, spec, config sheet)
3. Entity definitions (fields + types → entity pages)
4. Dependency language ("calls X API") → cross-module pages
5. Decision language ("we chose X because") → decision pages
6. Config tables (property + description columns) → config pages

MANDATORY STEPS:
1. Extract the document (use extract_pdf / extract_docx / extract_xlsx)
2. Call wiki_list_pages to see what already exists
3. Read 3–5 most relevant existing wiki pages for context
4. Output your final answer as JSON only — no prose outside JSON

OUTPUT SCHEMA:
{
  "summary_bullets": ["string", ...],          // 5–8 bullets
  "classification": "module|entity|config|...",
  "target_slug": "visitor-management",
  "operations": [
    {
      "type": "create|edit|append|update_frontmatter",
      "path": "wiki/...",
      "frontmatter": {},        // for create only
      "preview": "...",         // first 200 chars of body, for create
      "change_description": ""  // for edit/append/update_frontmatter
    }
  ],
  "cross_references": ["wiki/cross-module/..."],
  "warnings": ["..."],
  "agent_reasoning": "..."
}
```

### Phase 2 — Ingestion Executor (~500 chars)

```
You are an ingestion executor. Execute the approved plan EXACTLY
as specified. Do not re-classify. Do not add or remove operations.

For each operation:
- "create"             → wiki_create_page
- "edit"               → wiki_edit_page
- "append"             → wiki_append_section
- "update_frontmatter" → wiki_update_frontmatter

After all operations complete: call wiki_rebuild_index.

If any tool call fails, stop immediately and report the error.
Do not attempt workarounds or skip steps.
```

---

## Frontend

### New files

```
frontend/src/app/features/ingest/
├── ingest.ts            # routed page component — manages step state
├── ingest.scss
├── upload-step.ts       # step 1: drag-drop zone + notes + module hint
├── plan-step.ts         # step 2: plan review + approve/cancel
└── execute-step.ts      # step 3: SSE streaming progress + result links
```

### Route

Added to `app.routes.ts`:
```typescript
{ path: 'ingest', component: IngestPage, canActivate: [AuthGuard] }
```

Sidebar nav entry added alongside `ask`, `search`, `traces`.

### Step 1: Upload

- Drag-and-drop zone + click-to-browse
- Accepted types: `.pdf`, `.docx`, `.xlsx`, `.md`, `.txt`
- Optional free-text notes field (context for the AI)
- Optional module slug hint (dropdown of known slugs from `wiki/index.md`)
- "Upload & Analyse" button → POST `/api/ingest/upload`, then immediately POST `/api/ingest/plan` (shows spinner)

### Step 2: Plan Review

Displays the JSON plan returned from Phase 1:
- Document summary (5–8 bullets)
- Classification badges (type, target module, action: create vs update)
- "Files to create" list with path + 200-char body preview
- "Files to modify" list with path + change description
- "Cross-references to create" list
- Warnings section (⚠ shown prominently if non-empty)
- Cancel button → discards session, nothing written
- "Approve & Execute" button → POST `/api/ingest/execute` (opens SSE stream)

### Step 3: Execute (SSE streaming)

- Per-operation progress: `✅ Created wiki/sources/X.md` or `⏳ Updating...` or `❌ Error: ...`
- Progress bar based on completed/total operations
- On complete: success panel with links to created/modified pages + "Ingest another doc" button
- On error: error message + "Go back and retry" button
- "Do not close this tab" warning while in progress

### SSE event format

```json
{ "type": "progress", "operation_index": 3, "total": 10, "path": "wiki/sources/vms-prd-v2.md", "status": "created" }
{ "type": "progress", "operation_index": 4, "total": 10, "path": "wiki/modules/visitor-management.md", "status": "edited" }
{ "type": "complete", "files_created": 3, "files_modified": 5, "links": ["wiki/modules/visitor-management", ...] }
{ "type": "error", "operation_index": 5, "message": "wiki_create_page: file already exists at wiki/entities/visitor-invite.md" }
```

---

## Error Handling

| Scenario | Response |
|---|---|
| Unsupported file type | `400` on upload — nothing saved |
| File > 100 MB | `413` on upload |
| Mutex held (concurrent upload) | `409` on `/plan` — "Ingestion in progress, try again shortly" |
| Session expired (>10 min) | `410` on `/execute` — "Plan expired, please re-upload" |
| Phase 1 classification uncertain | Plan returned with `warnings` — user still decides to approve or cancel |
| Phase 2 tool call fails | SSE `error` event — execution stops, partial writes remain, user notified |
| `wiki_create_page` on existing file | Tool error → agent stops → SSE error event shown in UI |
| Backend restart mid-execute | Session lost — user re-uploads |

---

## Verification

End-to-end test with a real document:

1. Start backend (`uvicorn backend.api:app --reload`)
2. Open `/ingest` in browser, log in as any authenticated user
3. Upload `raw/modules/visitor-management/` — any PDF present there
4. Verify Phase 1 returns a valid plan with correct `target_slug: visitor-management`
5. Approve → verify SSE events stream and files appear in `wiki/`
6. Run `python scripts/audit_ingest.py` — verify file shows as "ingested", not "not ingested"
7. Run `curl localhost:8000/health` — verify `wiki_pages` count increased
8. Check `wiki/log.md` — verify new entry appended
9. Test 409: open second browser tab, try to upload while first is executing
10. Test 410: start a plan, wait 11 minutes, try to execute — verify "Plan expired" error
