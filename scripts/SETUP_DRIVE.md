# Drive → raw/ Sync Setup

You have **three options** for getting Drive files onto your Mac so the sync script
can pick them up. Choose the one that fits your workflow.

| Option | Best for | Re-sync effort | Setup time |
|--------|---------|----------------|------------|
| **A. Google Drive Desktop** (recommended) | macOS team, mostly read-only browsing | Auto (background) | 5 min |
| **B. rclone** | CLI-first, scriptable, cron-able | One command | 10 min |
| **C. Manual download** | One-off, no cloud-sync setup | Re-download every time | 0 min |

The sync script (`sync_drive.py`) is **source-agnostic** — once your Drive is locally
accessible by any of these methods, the script handles the rest.

---

## Option A — Google Drive for Desktop (Recommended)

### One-time setup

1. Download from <https://www.google.com/drive/download/>.
2. Install and sign in with your Google account.
3. In Drive Desktop preferences → **Google Drive** tab → make sure
   **"Stream files"** or **"Mirror files"** is enabled for "My Drive" (either works).
4. Find the local mount path. On macOS it is typically:
   ```
   ~/Library/CloudStorage/GoogleDrive-<your-email>/My Drive/
   ```
5. Confirm the WorkInSync folder is visible:
   ```bash
   ls "$HOME/Library/CloudStorage/GoogleDrive-"*/My\ Drive/Conwo*WorkInSync*
   ```

### Run the sync

```bash
cd /Users/rudrakhare/Desktop/my-wiki/org-wiki

python scripts/sync_drive.py \
  --source "$HOME/Library/CloudStorage/GoogleDrive-<your-email>/My Drive/Conwo WorkInSync Docs"
```

> Replace `<your-email>` with the actual folder name on your machine.
> If the path has spaces, keep it quoted.

### When new files appear in Drive
Drive Desktop syncs them automatically in the background. Just re-run the
`sync_drive.py` command above — it will pick up only the new/changed files.

---

## Option B — rclone (CLI-first, fully scriptable)

### One-time setup

1. Install rclone:
   ```bash
   brew install rclone
   ```

2. Configure a remote called `gdrive`:
   ```bash
   rclone config
   ```
   Walkthrough:
   - `n` (new remote)
   - name: `gdrive`
   - Storage: `drive` (Google Drive)
   - `client_id` / `client_secret`: leave blank (use rclone's defaults)
   - scope: `1` (full access) or `2` (read-only — recommended)
   - Service account: leave blank
   - Edit advanced config: `n`
   - Use auto config: `y` (browser opens for OAuth)
   - Configure as a Shared Drive: `n` unless WorkInSync lives in a Shared Drive
   - Confirm: `y`, then `q` to quit.

3. Test access:
   ```bash
   rclone lsd "gdrive:Conwo WorkInSync Docs"
   ```
   You should see the 22 feature folders.

### Run the sync

The simplest pattern: rclone first downloads to a staging folder, then our script
mirrors it into `raw/modules/` with slugified names.

```bash
cd /Users/rudrakhare/Desktop/my-wiki/org-wiki

# Step 1: pull from Drive into a local staging directory (idempotent)
rclone sync "gdrive:Conwo WorkInSync Docs" ./raw/_drive_staging \
  --progress --create-empty-src-dirs

# Step 2: mirror staging into raw/modules/<slug>/ with our naming + dedup
python scripts/sync_drive.py --source ./raw/_drive_staging
```

The staging folder is gitignored (see `.gitignore`).

### Optional: wrap in a one-liner

Add this alias to your shell profile:
```bash
alias wiki-sync='cd /Users/rudrakhare/Desktop/my-wiki/org-wiki && \
  rclone sync "gdrive:Conwo WorkInSync Docs" ./raw/_drive_staging --progress && \
  python scripts/sync_drive.py --source ./raw/_drive_staging'
```

Then any time you want to refresh: `wiki-sync`.

---

## Option C — Manual download (one-off / fallback)

1. In Drive web UI, open `Conwo WorkInSync Docs`.
2. Select all 22 feature folders.
3. Right-click → **Download** (Drive zips them).
4. Unzip — you'll get something like `~/Downloads/Conwo WorkInSync Docs/`.
5. Run:
   ```bash
   python scripts/sync_drive.py --source ~/Downloads/Conwo\ WorkInSync\ Docs
   ```

This is fine for a one-time bootstrap, but tedious if files are added regularly.

---

## What the Script Does

For every top-level folder in `--source`:

1. **Slugify** name → kebab-case
   ```
   "Floor Kiosk (Kavya)"   → floor-kiosk
   "MS Teams Integration"  → ms-teams-integration
   "Tags - desk + parking" → tags-desk-parking
   "SSO (Mohit)"           → sso
   ```

2. **Mirror** files into `raw/modules/<slug>/` (preserves any subfolder structure inside).

3. **Dedup**: skip files that already exist with identical content (size + SHA-256).

4. **Auto-create new feature folders** when Drive has a folder we don't know about.

5. **Report** at the end:
   ```
   Per-feature counts:
     feature                          new  upd unch skip
     --------------------------------  ---- ---- ---- ----
     * new-feature-from-drive          4    0    0    0
       desk-management                 2    1    7    0
       sso                             0    0    3    0
   ```
   `*` marks new features that didn't exist before this sync.

6. **Suggest ingest commands** for features with new content:
   ```
   Next: in Cursor chat, ingest each feature with new content:
     ingest all new docs in raw/modules/desk-management/
     ingest all new docs in raw/modules/new-feature-from-drive/
   ```

7. **Write a manifest** to `raw/.sync_manifest.json` (gitignored) recording the
   last sync time, source path, and per-feature counts.

---

## Common Workflow After Initial Setup

```bash
# 1. Refresh from Drive (whichever option you chose)
python scripts/sync_drive.py --source <your-drive-path>

# 2. See what's queued up for ingest
python scripts/list_pending.py

# 3. In Cursor chat, ingest one feature at a time:
#    ingest all docs in raw/modules/sso/
#    (review the AI's summary, confirm, repeat for next feature)

# 4. Verify the wiki state:
#    Open wiki/index.md or run a query in Cursor.
```

---

## Troubleshooting

**"source is not a directory"**
The `--source` path is wrong. Use absolute paths and quote any path containing spaces.

**Google native files (.gdoc/.gsheet) get skipped**
That's by design — they don't have raw bytes the script can read. Either:
- Open the doc in Drive, File → Download → PDF, then re-sync, OR
- Use rclone with export converters: `rclone sync ... --drive-export-formats pdf`

**Files keep showing as "updated" every run**
This usually means Drive is changing the file mtime even when content is identical.
The script falls back to SHA-256 comparison so it won't actually re-copy — but the
mtime mismatch means it has to read the file. This is expected and harmless.

**I want to force a fresh re-download**
Delete `raw/modules/<slug>/<file>` and re-run sync. The script will treat it as new.

**A feature folder slug doesn't match my expectation**
Check the `slugify()` function in `sync_drive.py`. It strips parenthetical
annotations and converts to kebab-case. If you want a different slug, rename
the Drive folder OR add a manual mapping (let me know — easy to extend).
