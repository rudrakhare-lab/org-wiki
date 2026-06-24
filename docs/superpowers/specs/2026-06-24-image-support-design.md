# Image Support for Conwo — Design Spec
_Date: 2026-06-24_

---

## Overview

Add image support to Conwo in two places:

1. **Ingest-time** — users can upload PNG/JPG/WEBP/GIF files via the ingest UI. Claude Vision describes the image as structured text, which then flows through the existing ingest pipeline unchanged, producing wiki pages (modules, entities, decisions, etc.) just like a PDF or PRD would.

2. **Query-time** — users can attach or paste an image in the chat composer. The image is stored as part of the message in the conversation DB and replayed to Claude on every subsequent turn in the session — same behaviour as Claude.ai and ChatGPT.

---

## Ingest-time Design

### Approach

Add image extraction as a drop-in step in the existing pipeline. The existing ingest agent sees structured text — no changes needed beyond the extraction step.

### Changes

**`backend/document_extractor.py`**
- Add `extract_image(file_path: str) -> dict` function
- Reads file, base64-encodes it, calls Claude Vision via the Anthropic SDK
- Prompt instructs Claude to describe every component, relationship, flow, and decision visible — output as structured text suitable for a wiki page
- Returns `{"text": "...", "title": "..."}` — same shape as `extract_pdf()` and `extract_docx()`

**`backend/ingest_api.py`**
- Add `{".png", ".jpg", ".jpeg", ".webp", ".gif"}` to `SUPPORTED_EXTENSIONS`
- In the file-type routing block, route image extensions to `extract_image()`
- Everything downstream (ingest agent reads text → writes wiki pages) is unchanged

**Frontend ingest UI**
- Add image extensions to the file picker `accept=` attribute
- No other UI changes

### Data flow

```
User uploads diagram.png
        │
        ▼
extract_image() → Claude Vision → structured text description
        │
        ▼
Existing ingest agent (unchanged)
        │
        ▼
wiki/sources/diagram-png.md + module/entity/decision pages
```

### Output

Same wiki output as ingesting a PRD:
- `wiki/sources/<slug>.md` — source summary page
- Module, entity, decision pages extracted from the diagram content
- All pages indexed and searchable immediately

---

## Query-time Design

### Approach

Store images as part of message rows in the conversation DB. Replay them to Claude as structured content blocks on every subsequent turn — no separate image session management needed.

### Database migration

Add two columns to the `messages` table:

```sql
ALTER TABLE messages ADD COLUMN image_data    BYTEA;
ALTER TABLE messages ADD COLUMN image_media_type TEXT;
```

Image bytes and MIME type stored directly in the message row. Null for text-only messages.

### Backend — `/query` endpoint (`backend/api.py`)

- Accept both `multipart/form-data` (question + image file) and `application/json` (text only)
- When multipart: extract `question` field + optional `image` file, base64-encode the image bytes, pass to orchestrator
- When JSON: existing path unchanged

### Backend — conversation history replay (`backend/orchestrator.py`)

`_load_conversation_context()` updated to handle image-bearing messages:

```python
# Text-only message (today — unchanged)
{"role": "user", "content": "what does this show?"}

# Message with image (new)
{"role": "user", "content": [
    {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": "image/png",
            "data": "<b64_string>"
        }
    },
    {"type": "text", "text": "what does this show?"}
]}
```

When a prior message has `image_data`, its `content` becomes a list of content blocks. Claude sees the image on every turn automatically.

### Backend — message storage (`backend/conversation_store.py`)

`add_message()` gets two new optional params: `image_data: bytes | None` and `image_media_type: str | None`. These are written to the new columns. `_row_to_message()` reads them back and includes them when building history.

### Frontend — composer (`frontend/src/app/features/ask/ask.ts`)

**Attach button:**
- Paperclip icon added next to the send button
- Triggers `<input type="file" accept="image/png,image/jpeg,image/webp,image/gif">` (hidden)

**Paste support:**
- `(paste)` event listener on the textarea
- If `event.clipboardData.files[0]` is an image, capture it — same as clicking attach

**Preview:**
- Thumbnail preview renders above the composer after attach/paste
- ✕ button removes the image before sending
- Thumbnail is a `<img>` with `object-fit: cover`, 80px tall

**Sending:**
- If image attached: build `FormData{ question, image_file }`, POST as multipart
- If no image: existing `JSON.stringify` path — unchanged

**Chat history rendering:**
- User messages with an image render the thumbnail inline above the text bubble
- Image stored as a data URL in the `ChatMessage` for display (not re-fetched from server)

### Response format

Unchanged — `QueryResponse` shape is identical. The intent classifier and response formatter run as always; the image is additional context for Claude, not a signal that changes the response schema.

### Tool-use loop

Unchanged — the tool loop runs fully on every query. The image is passed as part of the first user message content block; Claude can reason over it while also calling `config_lookup`, `jira_search`, `wiki_read_page`, etc.

---

## What is explicitly out of scope

- Image editing or annotation in the UI
- Storing images as separate files / object storage (bytes go directly in the DB for now)
- Image support in the agent (Claude Code) mode — text only for now
- OCR of scanned documents — that's a separate feature

---

## Files touched

| File | Change |
|---|---|
| `backend/document_extractor.py` | Add `extract_image()` |
| `backend/ingest_api.py` | Add image extensions + routing |
| `backend/api.py` | Accept multipart on `/query` |
| `backend/orchestrator.py` | Replay image content blocks in history |
| `backend/conversation_store.py` | `add_message()` image params + `_row_to_message()` |
| `migrations/postgres/XXX_messages_image.sql` | Add `image_data`, `image_media_type` columns |
| `frontend/src/app/features/ask/ask.ts` | Attach button, paste handler, preview, FormData send |
| `frontend/src/app/features/ask/ask.scss` | Thumbnail preview styles |
| `frontend/src/app/core/api.service.ts` | `ChatMessage` image fields, multipart query method |

---

## Open questions

- Should large images be resized/compressed client-side before upload to keep message history payloads manageable? (Recommend: yes, cap at 1MB / 1024px longest side via Canvas API)
- Should image data be included when replaying very long conversation histories (e.g. 20+ turns)? Base64 images are large — may need to cap image replay to the last N turns only.
