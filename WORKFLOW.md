# How to Add Docs to the Wiki

---

## Quick Reference

| Task | Command |
|------|---------|
| Add a module spec | `ingest raw/modules/<module-name>/<filename>` |
| Add a meeting transcript | `ingest raw/meetings/<filename>` |
| Add a PRD | `ingest raw/prds/<filename>` |
| Add a design doc | `ingest raw/design/<filename>` |
| Add an API spec | `ingest raw/api/<filename>` |
| Ask a question | Just type naturally |
| Health check | `lint the wiki` |

---

## Adding a New Feature Module Doc

1. Save your doc (Markdown, PDF, or plain text) to `raw/modules/<module-name>/`
   - Example: `raw/modules/payments/payments-spec-v2.md`
2. Open Cursor in the `org-wiki/` folder
3. Type: `ingest raw/modules/payments/payments-spec-v2.md`
4. The AI will summarize 5–8 key takeaways and ask you to confirm before writing anything.
5. Review the summary. Guide the AI on what to emphasize or what to skip.
6. After confirmation, the AI writes all wiki pages — module page, entity pages, cross-module pages, etc.
7. Open Obsidian — new pages appear immediately. Hit `Cmd+G` to see the updated graph.

---

## Adding a Meeting Transcript

1. Save the transcript to `raw/meetings/<YYYY-MM-DD>-<topic>.md`
   - Example: `raw/meetings/2026-04-27-auth-design-review.md`
2. Type: `ingest raw/meetings/2026-04-27-auth-design-review.md`
3. The AI will extract: decisions made, modules discussed, entities mentioned, action items.

---

## Adding a PRD

1. Save to `raw/prds/<feature-name>-prd.md`
   - Example: `raw/prds/passkeys-prd.md`
2. Type: `ingest raw/prds/passkeys-prd.md`
3. The AI will create or update module pages, add new entities if introduced,
   and extract any architectural decisions documented in the PRD.

---

## Adding a Design Doc

1. Save to `raw/design/<feature-name>-design.md`
2. Type: `ingest raw/design/<filename>`
3. Figma exports work best as annotated Markdown or plain text — export description
   text and component specs, not the raw Figma JSON.

---

## Adding an API Spec

1. Save to `raw/api/<service-or-module>-api.md` (or `.yaml` for OpenAPI)
2. Type: `ingest raw/api/<filename>`
3. The AI will populate the API Endpoints section of the relevant module page
   and flag any undocumented endpoints or auth mismatches.

---

## Asking a Question About Modules

Just type naturally — no special command needed:

```
How does the Auth module connect to Payments?
What entities does the Notifications module use?
Which modules have a dependency on Auth?
What was decided about JWT token expiry?
```

The AI reads `wiki/index.md` and the relevant wiki pages (not raw docs) and answers
with citations like `(see [[modules/auth]])`.

**To save the answer as a permanent wiki page**, tell the AI:
```
Save this as a wiki page.
```
It will create the page at `wiki/concepts/<topic>.md` or `wiki/cross-module/<topic>.md`
and update the index.

---

## Running a Wiki Health Check

Do this every 10–15 ingests to keep the wiki clean:

```
lint the wiki
```

The AI will check for:
- Broken dependency links (module A depends on B but B has no page)
- Orphan pages (no other page links to them)
- Missing cross-module pages (two modules share an entity but no cross-module page exists)
- Contradictions (same entity described differently on two pages)
- Stubs (pages with `status: stub` and suggestions for how to fill them)
- Stale pages (sources ingested 30+ days ago with no updates since)

The AI will **report everything first** before changing anything. You choose what to fix.

---

## Session Start Convention

Every Cursor session opens with the AI reading:
1. `CLAUDE.md` — the AI's rulebook
2. `wiki/index.md` — current wiki state
3. `wiki/log.md` (last 10 entries) — what was recently done
4. `wiki/overview.md` — big picture

The AI will then tell you the current state (module count, recent ingests, open flags)
and ask what you want to do.

---

## File Naming Conventions

| Type | Location | Naming |
|------|---------|--------|
| Module spec | `raw/modules/<module>/` | `<module>-spec-v<N>.md` |
| Meeting transcript | `raw/meetings/` | `YYYY-MM-DD-<topic>.md` |
| PRD | `raw/prds/` | `<feature>-prd.md` |
| Design doc | `raw/design/` | `<feature>-design.md` |
| API spec | `raw/api/` | `<module>-api.md` |

---

## Rules for Contributors

1. **Never edit `wiki/` directly** — let the AI maintain it. Manual edits will be
   overwritten on the next ingest and won't be tracked in the log.
2. **Never edit `wiki/log.md`** — it is append-only. The AI manages it.
3. **Raw docs are permanent** — once a doc is in `raw/`, don't rename or move it.
   The wiki pages cite their sources by path. Renaming breaks the audit trail.
4. **When in doubt, create a stub** — it's better to have a stub with open questions
   than to have a module mentioned in cross-references with no page at all.
