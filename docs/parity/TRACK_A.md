# Track A — Wiki Editing Capability

> Status: ✅ COMPLETE (Sub-passes A, B, C, D shipped 2026-05-22). This document is the durable reference for the wiki-editing pipeline. It's written for someone who hasn't been in the design conversation; read it top-to-bottom before changing any file under `backend/wiki_*`.

## What Track A is

Track A is the capability for the **agent (LLM)** to **propose** changes to `wiki/` and the **admin** to **apply** them. The agent never writes to the wiki directly. Every change goes through a structured proposal queue, and the admin's `/apply` endpoint is the only path that actually mutates files on disk.

This was decision **D1 = YES** ("wiki editing is in scope"). The alternatives we rejected:
- **Direct edit by agent (Model A):** unsafe — one bad LLM call corrupts the source of truth.
- **Auto-approve some paths (Model C / hybrid):** future direction once trust is built. Not yet.

We chose **Model B (proposal-only):** safer, auditable, and the friction is acceptable at pilot scale (1 admin).

## High-level architecture

```
┌────────────┐   wiki_propose_*   ┌──────────────────┐
│            │ ─────────────────▶ │  proposal queue  │
│   Agent    │                    │  (JSONL store)   │
│  (LLM)     │ ◀──────────────────│                  │
└────────────┘   proposal_id +    └──────────────────┘
                "pending" response          │
                                            │ /admin/wiki/proposals/{id}/apply
                                            ▼
                                  ┌──────────────────┐
                                  │  apply layer     │
                                  │  (writers under  │
                                  │   fcntl flock)   │
                                  └────────┬─────────┘
                                           │ writes
                                           ▼
                                  ┌──────────────────┐
                                  │   wiki/ on disk  │
                                  │  (the SoT for    │
                                  │   180+ pages)    │
                                  └────────┬─────────┘
                                           │ rebuild_index
                                           ▼
                                  ┌──────────────────┐
                                  │  wiki_retriever  │
                                  │  (in-memory)     │
                                  └──────────────────┘
```

## The four propose tools (what the agent calls)

All four live in `backend/tools/wiki_propose_tools.py`. All four queue a structured proposal record into `raw/feedback/wiki_proposals.jsonl` and return `{proposal_id, status: "pending", message: "Pending admin review..."}`. None of them touch `wiki/` on disk.

| Tool | Use case | Required role |
|------|----------|----------------|
| `wiki_propose_new(page_path, content, reason, answer_id?)` | "Save this answer as a wiki page." Path allowlist: `concepts/`, `cross-module/`, `decisions/`, `answers/`, `sources/`. Modules/entities/configs stay admin-only. | contributor |
| `wiki_propose_edit(page_path, old_string, new_string, reason, answer_id?)` | "Fix this incorrect statement on the wiki." `old_string` must be uniquely present at propose time and at apply time. Cannot overlap `<!-- BEGIN AUTO:X -->` blocks. | contributor |
| `wiki_propose_append(page_path, content, reason, answer_id?)` | Append-only updates. Currently allowlisted to `log.md`. Content for `log.md` must start with `## [YYYY-MM-DD HH:MM] <op> | <title>` per CLAUDE.md §3. | contributor |
| `wiki_propose_multi_edit(edits[], reason, answer_id?)` | Atomic multi-file edit. Use for bidirectional-link updates: edit page A's `depends_on` AND page B's `used_by` in one proposal. All-or-none at apply time. | contributor |

The agent's response template tells the user the change is queued, not applied:
> "I've queued this as a proposal (ID `prop_abc123`). The wiki has not been changed yet — an admin will review and apply."

## Proposal record schema

```json
{
  "id": "prop_<12-hex>",
  "proposal_type": "new" | "edit" | "append" | "multi_edit" | "legacy_text",
  "page_path": "concepts/meal-cutoff-ref.md",
  "content":   "...",                  // for "new" and "append"
  "old_string": "...",                  // for "edit"
  "new_string": "...",                  // for "edit"
  "edits":     [{path, old, new}, ...], // for "multi_edit"
  "proposed_change": "...",             // for "legacy_text" (free-text)

  "submitter_email": "agent",
  "answer_id":       null | "abc123def456",
  "reason":          "Q3 correction",
  "validation_log":  ["frontmatter parsed OK (3 keys)", "..."],
  "suggested_companion_edit": null | { "kind": "bidirectional_link", "field": ..., "edits": [...], "note": "..." },

  "status":      "pending" | "applied" | "rejected",
  "admin_note":  null | "stale",
  "applied_by":  null | "admin@example.com",
  "applied_at":  null | "2026-05-22T14:00:00+00:00",
  "created_at":  "2026-05-22T13:30:00+00:00",
  "resolved_at": null | "..."
}
```

## The apply layer (what the admin endpoint does)

`backend/wiki_apply.py` exports 4 writer functions + a legacy refusal:

| Function | What it does |
|---|---|
| `apply_new(proposal)` | Refuses if file already exists at apply time (`code: stale_proposal`). Otherwise writes the content under `locked_write`. |
| `apply_edit(proposal)` | Reads current file under `locked_read_write`. Re-validates `old_string` uniqueness against current content. If not unique or not found → `stale_proposal`. Otherwise replaces and writes. |
| `apply_append(proposal)` | Reads current under `locked_read_write`, ensures proper newline separation, appends content, writes. |
| `apply_multi_edit(proposal)` | Two-pass atomic write — see below. |
| `refuse_legacy_text(proposal)` | Returns `{code: legacy_text_refused, ...}` with a pointer to `/mark-applied`. |

### Multi-edit atomicity (the hardest part)

`apply_multi_edit` runs in two passes:

**Pass 1 (no locks):** for each edit, read the current file content from disk, verify `old_string` is uniquely present. If any edit fails validation, return without writing anything. Snapshot pre-edit content of each file.

**Pass 2 (locks):** sort all targets by resolved path (deadlock prevention — guarantees consistent acquisition order if two multi_edit proposals share files). For each target in order:
1. Acquire `flock` via `locked_read_write`.
2. Re-read the file. If the content differs from the Pass 1 snapshot, raise `_StaleUnderLock` → trigger rollback.
3. Write the new content.

**Rollback:** if any write fails (IO error) or any inside-lock re-read finds a stale file, restore each already-written file from its pre-edit snapshot. Returns `rollback_status: clean | partial | failed`.

Stress test (`tests/manual/track_a_stress.py`) verifies: 100 iterations of a 5-file multi_edit with mid-stream write failure → 100/100 clean rollbacks.

## The advisory pattern (Q1 — `suggested_companion_edit`)

CLAUDE.md §7 line 536 says: "If A's frontmatter has `depends_on: [B]`, B's frontmatter MUST have `used_by: [A]`." In practice the existing wiki has bidirectional-link violations (e.g. `parking-management.md` doesn't include `visitor-management` in its `used_by`). So we can't strictly enforce reciprocity without first auditing every page.

The compromise: when `wiki_propose_edit` modifies a `depends_on` or `used_by` field on a module page, the handler computes what the reciprocal change *would* be on the linked page and attaches it as `suggested_companion_edit`. The admin sees the suggestion at apply time and decides whether to:
- Apply only the original proposal (one-sided update — preserved as a temporary violation)
- Manually propose the companion edit too (with `wiki_propose_multi_edit` for atomicity)

The advisory is **best-effort**: any error in the computation logs a warning and returns `None`. The propose call never fails because of an advisory failure.

**Known gap (G34):** the advisory regex only matches inline YAML lists (`depends_on: [a, b]`). Block-style lists (`depends_on:\n  - a\n  - b`) silently produce no advisory. Real wiki pages use inline today, but block-style support is a 1-hour future task.

## Protections

| Protection | What it stops |
|---|---|
| **Path traversal guards** | `..`, absolute paths, symlink escapes. Two-layer check (string + `Path.resolve()` containment). |
| **YAML well-formedness** at propose time | `wiki_propose_new` refuses content with malformed frontmatter (Q4 = permissive on fields, strict on YAML lexing). |
| **`old_string` uniqueness** | At propose time AND at apply time. Defeats race conditions where the file changed under the proposal. |
| **AUTO marker block refusal** | Edits whose `old_string` falls inside `<!-- BEGIN AUTO:X --> ... <!-- END AUTO:X -->` are refused with an error naming the script that owns the block (e.g. `scripts/enrich_modules.py`). |
| **Path allowlist for new pages** | `wiki_propose_new` restricted to `concepts/`, `cross-module/`, `decisions/`, `answers/`, `sources/`. Modules / entities / configs require admin-only creation. |
| **`fcntl.flock` (POSIX)** | Serializes concurrent writes to the same file. Stress test verified: 20-thread contention → 1 success, 19 stale_proposal, 0 exceptions. |
| **Idempotency** | Re-applying an already-applied proposal returns `code: already_applied` without touching disk. Verified by file-mtime check. |
| **Stale-proposal detection** | If the file changed between propose and apply, the writer detects it via the `old_string` re-uniqueness check (edit) or the pre-edit content snapshot comparison (multi_edit). |
| **Append-only enforcement** | `wiki_propose_append` is restricted to `log.md`. The agent cannot use it to clobber other files. |
| **Reserved marker refusal** | Content containing `<!-- feedback:ID -->` markers is the apply_feedback.py script's territory; the agent's tools refuse to produce these. (Currently a soft prohibition — no automated check; rely on the AUTO-block test which catches the documented patterns.) |

## The apply contract (HTTP / response shape)

`POST /admin/wiki/proposals/{id}/apply` returns a structured dict:

```json
{
  "success": true | false,
  "code":    null | "not_found" | "stale_proposal" | "legacy_text_refused"
                 | "write_io_error" | "already_applied" | "path_traversal"
                 | "missing_input" | "unknown_proposal_type",
  "message": "...human-readable...",
  "proposal_id":    "...",
  "proposal_type":  "new" | "edit" | "append" | "multi_edit" | "legacy_text",
  "files_written":  ["concepts/x.md", ...],
  "rollback_status": null | "clean" | "partial" | "failed",
  "index_rebuilt":  true | false,
  "index_error":    "...",          // when index_rebuilt is false
  "suggested_companion_edit": null | { ... },
  "proposal":       { ...updated proposal record... }
}
```

HTTP status codes map to `code` semantically:
- 200 OK — `success=true` (including `already_applied`)
- 404 Not Found — `code=not_found`
- 409 Conflict — `code=stale_proposal`
- 422 Unprocessable Entity — `code=legacy_text_refused`
- 500 Server Error — `code=write_io_error` or other unexpected

`POST /admin/wiki/proposals/{id}/mark-applied`:
- 200 OK — legacy_text proposal marked applied (after manual edit) + index rebuild
- 400 Bad Request — `code=not_legacy_text` (use `/apply` for structured proposals)
- 404 Not Found — `code=not_found`

## Legacy proposals (pre-Track-A)

Free-text proposals created by the old `wiki_propose_edit` tool (before Sub-pass B) auto-load with `proposal_type: "legacy_text"`. They CANNOT be applied automatically — the structured fields the writers need aren't there. The flow for legacy proposals:

1. Admin reads the `proposed_change` field (free text describing what to change).
2. Admin manually edits the wiki page.
3. Admin calls `/admin/wiki/proposals/{id}/mark-applied` to record the apply in the audit trail.

A startup WARN (`backend.wiki_proposals.warn_if_legacy_pending()`) counts how many pending legacy proposals exist and surfaces it in the lifespan log, so admins know to drain them.

## Proposal lifecycle (ASCII diagram)

```
                  ┌───────────────────────────────────────────┐
                  │   1. agent calls wiki_propose_*           │
                  │      → proposal queued as "pending"       │
                  └────────────────────┬──────────────────────┘
                                       │
                                       ▼
                  ┌───────────────────────────────────────────┐
                  │   2. admin reviews /admin/wiki/proposals  │
                  └──┬───────────────┬───────────────────┬────┘
                     │               │                   │
              "Apply"│         "Mark Applied"      "Reject"│
                     │               │                   │
                     ▼               ▼                   ▼
   ┌────────────────────────┐  ┌─────────────────┐  ┌──────────────┐
   │ apply_wiki_proposal()  │  │ legacy_text     │  │ status →     │
   │ dispatches to writer   │  │ only — admin    │  │ "rejected"   │
   │ under fcntl flock      │  │ already edited  │  │ admin_note   │
   └───────────┬────────────┘  │ manually        │  └──────────────┘
               │               └────────┬────────┘
       success │ failure                │
               │  │                     │
               ▼  ▼                     ▼
   ┌────────────────────────┐  ┌─────────────────┐
   │ status → "applied"     │  │ status →        │
   │ stamps applied_by /    │  │ "applied"       │
   │ applied_at             │  │ stamps          │
   │ rebuild_index()        │  │ rebuild_index() │
   └────────────────────────┘  └─────────────────┘
```

## Known limitations and where to look

| Limitation | Gap ID | Detail |
|---|---|---|
| Multi-admin contention on multi_edit | G36 | `apply_multi_edit` releases per-file locks between files. Two concurrent multi_edits with overlapping files could interleave on the second-through-Nth file. Pilot is 1 admin, so latent. Fix: acquire ALL locks via `ExitStack` before any write. ~2h. |
| Q1 advisory misses block-style YAML | G34 | Regex only matches inline `depends_on: [a, b]`. Block-style produces no companion advisory. ~1h to extend. |
| Frontmatter parser fragile on `---` separators | G35 | Current `_extract_frontmatter` splits on `\n---\n`; collides with markdown horizontal rules in body. Today returns correct result by `parts[0]` selection but accident-prone. Fix: switch to `python-frontmatter`. ~2h. |
| In-memory index is per-worker | (doc-only) | Multi-worker uvicorn would have coherence drift. Pilot is single-worker so moot. If you ever set `--workers > 1`, add a file-watcher (`watchdog`) or shared cache. Comment lives in `wiki_retriever.py:build`. |
| AUTO marker block check is regex-based | (doc-only) | Only catches markers matching `<!--\s*BEGIN\s+AUTO:([A-Z_]+)\s*-->`. Custom-cased markers like `<!-- begin auto:X -->` would slip through. The two existing auto-marker producers (`apply_feedback.py`, `enrich_modules.py`) use the standard form. |
| Agent identity is hardcoded as `"agent"` | (legacy TODO, since G06) | All propose tools use `submitter_email="agent"`. Per-user identity threading via ToolRegistry is a separate cleanup. Documented as TODO in code. |

## What's NOT in Track A

- **INGEST workflow** — out of scope per D3. Admins use `claude` CLI for ingest.
- **LINT workflow** — out of scope per D3.
- **Wiki delete** — not implemented. Deletion is admin-only and rare; out of scope for initial pass.
- **`wiki_edit_marker_block`** — editing INSIDE `<!-- BEGIN AUTO:X -->` blocks is reserved for scripts. The agent's tools refuse.
- **`wiki_save_answer` convenience tool** — the agent can call `wiki_propose_new` directly; a wrapper is unnecessary.
- **Auto-commit to git on apply** — explicitly NOT done (Q2 = NO). The audit trail is the proposal JSONL + `log.md` entries.

## Files touched by Track A

```
backend/
  wiki_proposals.py            (typed proposal store + legacy normalization)
  wiki_apply.py                (new — 4 writers + rollback helper)
  file_locks.py                (new — POSIX flock context managers)
  wiki_retriever.py            (Obsidian artifact filter)
  admin_api.py                 (apply_wiki_proposal rewrite + mark_wiki_proposal_applied)
  api.py                       (apply endpoint code mapping + /mark-applied endpoint)
  tools/
    wiki_propose_tools.py      (new — 4 propose tools)
    wiki_tools.py              (disk-fallback in wiki_read_page; old free-text propose_edit removed)
    __init__.py                (registry 16 → 19 tools)
    registry.py                (contributor role for all 4 wiki_propose_*)
  deep_system_prompt.py        (propose tool guidance)

tests/
  test_track_a_foundations.py  (new — Sub-pass A tests, 13)
  test_wiki_propose_tools.py   (new — Sub-pass B tests, 21)
  test_wiki_apply.py           (new — Sub-pass C tests, 23)
  test_admin_wiki_proposals.py (updated — apply endpoint codes, mark-applied + reindex)
  test_tools.py                (updated — expected 19 tools)
  manual/
    track_a_verify.py          (new — end-to-end harness, 6 scenarios)
    track_a_stress.py          (new — concurrency + rollback stress)

docs/parity/
  GAPS.md                      (G07/G14/G16 closed; G34/G35/G36/G37 filed)
  PROGRESS.md                  (Track A rows)
  PLAN.md                      (Decisions Log header)
  TRACK_A.md                   (this document)

wiki/
  (3 Obsidian artifacts deleted — Untitled.md, Untitled.base, 2026-05-13.md)
```

## How to make changes to Track A safely

1. **Read this document.**
2. **Never bypass the propose queue.** If you find yourself writing to `wiki/` from anywhere other than `backend/wiki_apply.py`, you're introducing a hole in the audit trail.
3. **Run the manual harnesses** (`track_a_verify.py`, `track_a_stress.py`) after non-trivial changes. They catch what unit tests miss.
4. **If you touch `apply_multi_edit` rollback**, also update the comment in `test_apply_multi_edit_rollback_on_write_failure` — that test's `Path.write_text` patching has a known fragility (see comment in the test).
5. **If you touch `_compute_companion_edit`**, run it against real frontmatter from `wiki/modules/*.md` — the regex's edge cases are easy to miss in tests.

## Reading order for a new contributor

1. CLAUDE.md §3 (log.md append-only), §4 (INGEST — for context, even though out of scope), §7 (bidirectional links).
2. This document.
3. `backend/wiki_proposals.py` (the data model).
4. `backend/wiki_apply.py` (the only mutator).
5. `backend/tools/wiki_propose_tools.py` (the agent-facing surface).
6. `tests/test_wiki_apply.py` (covers the writers' edge cases — easier to read than the production code).
7. `tests/manual/track_a_verify.py` (end-to-end scenarios make the lifecycle concrete).
