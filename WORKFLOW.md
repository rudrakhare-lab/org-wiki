# How to Add Docs to the WorkInSync Wiki

---

## TL;DR — The 3-Step Loop

```
1. Sync new files from Drive:    python scripts/sync_drive.py --source <drive-path>
2. Ingest a feature:              ingest all docs in raw/modules/<slug>/
3. Ask questions naturally:       "How does X connect to Y?"
```

For the manual approach (drag-and-drop), see [Manual upload](#manual-upload-fallback)
below. For full Drive setup, read [`scripts/SETUP_DRIVE.md`](scripts/SETUP_DRIVE.md).

---

## Auto-Sync from Drive (recommended)

Because docs are still being added to the team Drive, you should pull new files
automatically rather than re-downloading manually.

### One-time setup
Pick one of three Drive-access options (Drive Desktop / rclone / manual zip)
in [`scripts/SETUP_DRIVE.md`](scripts/SETUP_DRIVE.md). Easiest is **Google Drive
for Desktop** — install once, sign in, done.

### Routine workflow

```bash
cd /Users/rudrakhare/Desktop/my-wiki/org-wiki

# 1. Pull new/changed files from Drive into raw/modules/<slug>/
python scripts/sync_drive.py \
  --source "$HOME/Library/CloudStorage/GoogleDrive-<email>/My Drive/Conwo WorkInSync Docs"

# 2. See what's queued up for ingest
python scripts/list_pending.py
```

The script:
- **Slugifies** Drive folder names → matching `raw/modules/<slug>/` (e.g.
  `"Floor Kiosk (Kavya)"` → `floor-kiosk`)
- **Auto-creates** new feature folders if Drive gets a new folder we don't know about
- **Skips duplicates** by content hash — safe to re-run any time
- **Reports** new files per feature and **suggests** the exact `ingest` commands

### Then in Cursor chat, ingest each feature with new content
```
ingest all new docs in raw/modules/sso/
ingest all new docs in raw/modules/desk-management/
```

---

## Where to Put Each Type of Doc

### Feature / Module Docs (the main case)

Each feature in your "Conwo WorkInSync Docs" Drive maps **1-to-1** to a folder in `raw/modules/`:

| Drive folder | Local path |
|---|---|
| Access management | `raw/modules/access-management/` |
| Admin Experience | `raw/modules/admin-experience/` |
| Create Employee form | `raw/modules/create-employee-form/` |
| Delegation (KAVYA) | `raw/modules/delegation/` |
| Desk Management | `raw/modules/desk-management/` |
| Digital Wayfinding | `raw/modules/digital-wayfinding/` |
| Employee experience | `raw/modules/employee-experience/` |
| Employee Provisioning | `raw/modules/employee-provisioning/` |
| ESG Dashboard | `raw/modules/esg-dashboard/` |
| Floor Kiosk (Kavya) | `raw/modules/floor-kiosk/` |
| Guard app + kiosks | `raw/modules/guard-app-kiosks/` |
| Implementation | `raw/modules/implementation/` |
| Meal Management | `raw/modules/meal-management/` |
| Meeting Rooms (KAVYA) | `raw/modules/meeting-rooms/` |
| Mobile App (Kavya) | `raw/modules/mobile-app/` |
| MS Teams Integration | `raw/modules/ms-teams-integration/` |
| Parking Management | `raw/modules/parking-management/` |
| Safe Reach (Vaishnavi) | `raw/modules/safe-reach/` |
| SSO (Mohit) | `raw/modules/sso/` |
| Tags - desk + parking | `raw/modules/tags-desk-parking/` |
| Third-party | `raw/modules/third-party/` |
| Visitor Management | `raw/modules/visitor-management/` |

### Other Doc Types
| Doc Type | Folder | Naming Convention |
|----------|--------|-------------------|
| Meeting transcripts / standups | `raw/meetings/` | `YYYY-MM-DD-<topic>.md` |
| PRDs | `raw/prds/` | `<feature>-prd.md` |
| Design specs / Figma exports | `raw/design/` | `<feature>-design.md` |
| API specs / OpenAPI YAML | `raw/api/` | `<module>-api.md` (or `.yaml`) |
| Anything else | `raw/misc/` | descriptive name |

---

## Manual upload (fallback)

If you don't want to run the sync script, you can still drag-and-drop:

### Step 1 — Download PDFs from Google Drive

1. Open your Drive folder: `Conwo WorkInSync Docs > <feature folder>`
2. Select all PDFs in that feature folder.
3. Right-click → **Download** (Drive will zip them).
4. Unzip the download.
5. Drag-and-drop the PDFs into the matching `raw/modules/<feature>/` folder in Finder.

> **Tip:** Drag a feature folder at a time, not all 22 at once. Ingest is more accurate when done one feature at a time.

> **PDFs vs Markdown:** PDFs are fine — Cursor will read them. If a PDF is huge (>50 MB) or a scanned image, you may want to convert it to text first (export to plain `.txt` from Drive), but most text-based PDFs work directly.

---

## Step 2 — Ingest in Cursor

Open Cursor in the `org-wiki/` folder. In the chat, type **one** of these:

### Single file
```
ingest raw/modules/desk-management/desk-mgmt-spec-v1.pdf
```

### All files in one feature folder (recommended)
```
ingest all docs in raw/modules/desk-management/
```
The AI will process each file in order, asking you to confirm the summary before writing wiki pages for each.

### What happens during ingest
1. AI reads the source completely.
2. AI summarizes 5–8 key takeaways → **you confirm**.
3. AI creates/updates:
   - `wiki/sources/<filename>.md` — source summary
   - `wiki/modules/<feature>.md` — full module page (or stub)
   - `wiki/entities/*.md` — for any data models found
   - `wiki/cross-module/*.md` — when modules interact
   - `wiki/decisions/*.md` — for any architectural choices
   - Updates `wiki/glossary.md`, `wiki/index.md`, `wiki/log.md`

---

## Step 3 — Ask Questions

After ingesting some docs, ask anything in plain English:

```
How does Desk Management connect to Parking Management?
What entities does the Visitor Management module own?
Which modules use SSO?
What was decided about MS Teams Integration auth?
Show me all modules owned by Kavya's team.
```

The AI reads `wiki/index.md` and the relevant wiki pages (NOT the raw PDFs) and answers with citations like `(see [[modules/desk-management]])`.

**To save the answer permanently:** say `save this as a wiki page`.

---

## Recommended First-Run Order

For best cross-module linking, ingest **foundational features first**, then their consumers:

1. **Foundation layer** (no dependencies on others):
   - `sso` — auth foundation, used by everything
   - `employee-provisioning` — creates the User entity everyone references
   - `access-management` — permissions layer
2. **Core domain modules** (depend on foundation):
   - `desk-management`
   - `meeting-rooms`
   - `parking-management`
   - `visitor-management`
   - `meal-management`
3. **UX / surfaces**:
   - `mobile-app`
   - `floor-kiosk`
   - `digital-wayfinding`
   - `admin-experience`
   - `employee-experience`
4. **Integrations & extensions**:
   - `ms-teams-integration`
   - `third-party`
   - `safe-reach`
   - `guard-app-kiosks`
   - `esg-dashboard`
   - `tags-desk-parking`
   - `delegation`
   - `create-employee-form`
   - `implementation`

This order means by the time you ingest `desk-management`, the AI already knows what `sso` is, so it can build proper cross-links automatically.

---

## Health Check

Every 10–15 ingests run:
```
lint the wiki
```
This finds broken links, orphan pages, contradictions, and stubs that need filling in.

---

## Rules for Contributors

1. **Never edit `wiki/` directly** — let the AI maintain it.
2. **Never edit `wiki/log.md`** — append-only, AI-managed.
3. **Raw docs are permanent** — once a PDF is in `raw/`, don't rename or move it (the wiki cites it by path).
4. **Stubs are fine** — if a feature is referenced before its own doc is ingested, the AI creates a stub. It will be filled in automatically when you ingest that feature's docs.
