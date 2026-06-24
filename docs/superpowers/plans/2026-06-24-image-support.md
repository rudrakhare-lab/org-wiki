# Image Support Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add image ingestion (PNG/JPG/WEBP/GIF → Claude Vision → wiki pages) and query-time image attachment (paste/attach in composer, stored in DB, replayed to Claude on every turn).

**Architecture:** Images at ingest-time are extracted via Claude Vision into structured text, then fed into the unchanged ingest pipeline. Images at query-time are stored as raw bytes in a new `image_data` column on the `messages` table and replayed as Anthropic content blocks in conversation history.

**Tech Stack:** Python/FastAPI backend, Anthropic SDK (`anthropic`), PostgreSQL (psycopg3), Angular 21 frontend, Angular `HttpClient` for multipart form upload.

## Global Constraints

- Branch off `bitbucket/main` — never commit directly to main
- No secrets in code — `ANTHROPIC_API_KEY` already set in env
- All throwaway scripts go in `/tmp/`, never in the repo
- Backend `.py` file writes stop the uvicorn `--reload` watcher — stop backend before editing `.py` files if running locally
- Migration files are numbered sequentially — check `migrations/postgres/` for the latest number before naming a new one
- Existing `QueryResponse` shape must not change — image is additional input, not a new output field
- `add_message()` changes must remain backwards-compatible — all existing callers omit the new params

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `backend/document_extractor.py` | Modify | Add `extract_image()` — calls Claude Vision, returns `{"text": ..., "title": ...}` |
| `backend/ingest_api.py` | Modify | Add image extensions to `SUPPORTED_EXTENSIONS`, route to `extract_image()` |
| `frontend/src/app/features/ingest/upload-step.ts` | Modify | Add image extensions to `accept=` and `typeError` message |
| `frontend/src/app/features/ingest/ingest.html` | Modify | Add image extensions to bulk upload `accept=` |
| `migrations/postgres/130_messages_image.sql` | Create | Add `image_data BYTEA` and `image_media_type TEXT` to `messages` |
| `backend/conversation_store.py` | Modify | `add_message()` new params + `_row_to_message()` reads image columns |
| `backend/orchestrator.py` | Modify | `_load_conversation_context()` builds content blocks when image present |
| `backend/api.py` | Modify | `/query` accepts multipart, extracts image, passes to orchestrator |
| `backend/orchestrator.py` | Modify | `run_orchestrator()` accepts `image_data`/`image_media_type`, passes to first user message |
| `frontend/src/app/core/api.service.ts` | Modify | Add `image_data_url` to `ChatMessage`, add `queryWithImage()` method |
| `frontend/src/app/features/ask/ask.ts` | Modify | Attach button, paste handler, thumbnail preview, FormData send |
| `frontend/src/app/features/ask/ask.scss` | Modify | Thumbnail preview styles |

---

## Task 1: `extract_image()` in document_extractor.py

**Files:**
- Modify: `backend/document_extractor.py`
- Test: `tests/test_document_extractor.py` (create if not exists)

**Interfaces:**
- Produces: `extract_image(file_path: str) -> dict` — returns `{"text": str, "title": str, "char_count": int, "truncated": bool}`
- Consumed by: Task 2 (`ingest_api.py`)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_document_extractor.py
import pathlib, base64
from unittest.mock import patch, MagicMock

def test_extract_image_returns_text_and_title(tmp_path):
    # Create a tiny 1x1 PNG (valid PNG header)
    png = bytes([
        0x89,0x50,0x4E,0x47,0x0D,0x0A,0x1A,0x0A,  # PNG signature
        0x00,0x00,0x00,0x0D,0x49,0x48,0x44,0x52,  # IHDR chunk
        0x00,0x00,0x00,0x01,0x00,0x00,0x00,0x01,
        0x08,0x02,0x00,0x00,0x00,0x90,0x77,0x53,
        0xDE,0x00,0x00,0x00,0x0C,0x49,0x44,0x41,
        0x54,0x08,0xD7,0x63,0xF8,0xCF,0xC0,0x00,
        0x00,0x00,0x02,0x00,0x01,0xE2,0x21,0xBC,
        0x33,0x00,0x00,0x00,0x00,0x49,0x45,0x4E,
        0x44,0xAE,0x42,0x60,0x82,
    ])
    img_path = tmp_path / "diagram.png"
    img_path.write_bytes(png)

    mock_client = MagicMock()
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text="## Architecture\nService A calls Service B.")]
    )

    with patch("backend.document_extractor._get_anthropic_client", return_value=mock_client):
        result = extract_image(str(img_path))

    assert "text" in result
    assert "title" in result
    assert "Architecture" in result["text"]
    assert result["char_count"] > 0
    assert result["truncated"] is False


def test_extract_image_unsupported_extension(tmp_path):
    p = tmp_path / "file.bmp"
    p.write_bytes(b"fake")
    from backend.document_extractor import UnsupportedFileType
    with pytest.raises(UnsupportedFileType):
        extract_image(str(p))
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /path/to/org-wiki
venv/bin/pytest tests/test_document_extractor.py -v
```
Expected: `ImportError` or `AttributeError` — `extract_image` not yet defined.

- [ ] **Step 3: Implement `extract_image()`**

Add to `backend/document_extractor.py` after the existing imports:

```python
import base64
import os

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}

_VISION_PROMPT = """\
You are analyzing an image uploaded to a knowledge base.
Describe every component, relationship, data flow, decision, and label visible.
Output structured text (headings, bullet points) suitable for a wiki page.
Include: what the diagram shows, every named component, every arrow/connection and what it means,
any labels, annotations, or decision points. Be exhaustive — nothing visible should be omitted.\
"""

def _get_anthropic_client():
    import anthropic
    return anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))


def extract_image(file_path: str) -> dict:
    ext = pathlib.Path(file_path).suffix.lower()
    if ext not in IMAGE_EXTENSIONS:
        raise UnsupportedFileType(f"Unsupported image type: {ext!r}")

    media_type_map = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".gif": "image/gif",
    }
    media_type = media_type_map[ext]
    raw = pathlib.Path(file_path).read_bytes()
    b64 = base64.standard_b64encode(raw).decode()

    client = _get_anthropic_client()
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": b64}},
                {"type": "text", "text": _VISION_PROMPT},
            ],
        }],
    )
    text = response.content[0].text
    # Use first heading as title, or fall back to filename
    title = pathlib.Path(file_path).stem
    for line in text.splitlines():
        stripped = line.lstrip("#").strip()
        if stripped:
            title = stripped
            break

    truncated = len(text) > MAX_CHARS
    return {
        "text": text[:MAX_CHARS],
        "title": title,
        "char_count": len(text),
        "truncated": truncated,
    }
```

Also update `SUPPORTED_EXTENSIONS` in `document_extractor.py`:

```python
SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".xlsx", ".md", ".txt", ".rtf",
                        ".png", ".jpg", ".jpeg", ".webp", ".gif"}
```

- [ ] **Step 4: Run tests**

```bash
venv/bin/pytest tests/test_document_extractor.py -v
```
Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/document_extractor.py tests/test_document_extractor.py
git commit -m "feat(ingest): extract_image() via Claude Vision"
```

---

## Task 2: Wire image extraction into ingest pipeline

**Files:**
- Modify: `backend/ingest_api.py`
- Modify: `frontend/src/app/features/ingest/upload-step.ts`
- Modify: `frontend/src/app/features/ingest/ingest.html`

**Interfaces:**
- Consumes: `extract_image(file_path: str) -> dict` from Task 1
- Produces: image uploads routed through Vision extraction, then existing ingest agent unchanged

- [ ] **Step 1: Add image extensions to `ingest_api.py`**

In `backend/ingest_api.py`, find:
```python
SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".xlsx", ".md", ".txt", ".rtf"}
```
Replace with:
```python
SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".xlsx", ".md", ".txt", ".rtf",
                        ".png", ".jpg", ".jpeg", ".webp", ".gif"}
```

- [ ] **Step 2: Route image extensions to `extract_image()`**

In `backend/ingest_api.py`, find the block that calls `extract_document`. It looks like:

```python
from backend.document_extractor import extract_document, UnsupportedFileType
```

Add the image import and routing. Find the section where the file is extracted (search for `extract_document`) and add image routing before the existing call:

```python
from backend.document_extractor import (
    extract_document, extract_image, UnsupportedFileType,
    IMAGE_EXTENSIONS,
)

# In the extraction block:
if ext in IMAGE_EXTENSIONS:
    extracted = extract_image(str(dest_file))
    # Normalise to the shape extract_document returns for text files
    doc_text = extracted.get("text", "")
    doc_title = extracted.get("title", dest_file.stem)
else:
    extracted = extract_document(str(dest_file))
    doc_text = extracted.get("text") or extracted.get("text_repr", "")
    doc_title = dest_file.stem
```

- [ ] **Step 3: Update frontend upload-step accept= and error message**

In `frontend/src/app/features/ingest/upload-step.ts`, find:
```typescript
accept=".pdf,.docx,.doc,.xlsx,.xls,.md,.txt,.rtf"
```
Replace with:
```typescript
accept=".pdf,.docx,.doc,.xlsx,.xls,.md,.txt,.rtf,.png,.jpg,.jpeg,.webp,.gif"
```

Find the typeError message:
```typescript
this.typeError.set(`Unsupported file type: ${ext}. Allowed: PDF, DOCX, XLSX, MD, TXT`);
```
Replace with:
```typescript
this.typeError.set(`Unsupported file type: ${ext}. Allowed: PDF, DOCX, XLSX, MD, TXT, PNG, JPG, WEBP, GIF`);
```

- [ ] **Step 4: Update bulk upload accept= in ingest.html**

In `frontend/src/app/features/ingest/ingest.html`, find:
```html
accept=".pdf,.docx,.xlsx,.md,.txt,.rtf"
```
Replace with:
```html
accept=".pdf,.docx,.xlsx,.md,.txt,.rtf,.png,.jpg,.jpeg,.webp,.gif"
```

- [ ] **Step 5: Manual smoke test**

Start the backend. Upload a PNG screenshot via the ingest UI. Verify:
- No 422 error
- Ingest job starts
- Wiki page is created referencing the image content

- [ ] **Step 6: Commit**

```bash
git add backend/ingest_api.py \
        frontend/src/app/features/ingest/upload-step.ts \
        frontend/src/app/features/ingest/ingest.html
git commit -m "feat(ingest): accept image uploads, route through Vision extraction"
```

---

## Task 3: DB migration — image columns on messages

**Files:**
- Create: `migrations/postgres/130_messages_image.sql`

**Interfaces:**
- Produces: `messages.image_data BYTEA`, `messages.image_media_type TEXT` — both nullable, default NULL

- [ ] **Step 1: Check latest migration number**

```bash
ls migrations/postgres/ | sort | tail -3
```
Expected: `120_ingest_batches.sql` is the latest. Use `130` for the new migration.

- [ ] **Step 2: Create the migration file**

Create `migrations/postgres/130_messages_image.sql`:

```sql
-- Add image storage columns to messages.
-- Both are nullable — existing rows remain unaffected.
ALTER TABLE messages
    ADD COLUMN IF NOT EXISTS image_data       BYTEA,
    ADD COLUMN IF NOT EXISTS image_media_type TEXT;
```

- [ ] **Step 3: Apply the migration**

The migration runs automatically on backend startup (FastAPI lifespan reads and applies all `.sql` files in order). Restart the backend and verify:

```bash
psql $DATABASE_URL -c "\d messages" | grep image
```
Expected output:
```
 image_data        | bytea   |
 image_media_type  | text    |
```

- [ ] **Step 4: Commit**

```bash
git add migrations/postgres/130_messages_image.sql
git commit -m "feat(db): add image_data and image_media_type columns to messages"
```

---

## Task 4: conversation_store.py — store and retrieve image data

**Files:**
- Modify: `backend/conversation_store.py`
- Test: `tests/test_conversation_store.py` (add new tests)

**Interfaces:**
- Produces:
  - `add_message(..., image_data: bytes | None = None, image_media_type: str | None = None) -> dict`
  - `_row_to_message(row)` now returns `image_data: bytes | None` and `image_media_type: str | None` in the dict

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_conversation_store.py`:

```python
def test_add_message_stores_image_data(db_conversation):
    """add_message persists image bytes and media type."""
    from backend import conversation_store
    conv_id = db_conversation  # fixture that creates a conversation and yields its id
    img_bytes = b"\x89PNG\r\n\x1a\n"  # PNG magic bytes
    msg = conversation_store.add_message(
        conv_id, "user", "what is this diagram?",
        image_data=img_bytes,
        image_media_type="image/png",
    )
    assert msg["image_data"] == img_bytes
    assert msg["image_media_type"] == "image/png"


def test_get_conversation_includes_image_data(db_conversation):
    """get_conversation returns image_data on messages that have it."""
    from backend import conversation_store
    conv_id = db_conversation
    img_bytes = b"\x89PNG\r\n\x1a\n"
    conversation_store.add_message(
        conv_id, "user", "describe this",
        image_data=img_bytes,
        image_media_type="image/png",
    )
    conv = conversation_store.get_conversation(conv_id)
    msg = conv["messages"][0]
    assert msg["image_data"] == img_bytes
    assert msg["image_media_type"] == "image/png"


def test_add_message_without_image_keeps_columns_null(db_conversation):
    """add_message without image leaves image columns as None."""
    from backend import conversation_store
    conv_id = db_conversation
    msg = conversation_store.add_message(conv_id, "user", "no image here")
    assert msg["image_data"] is None
    assert msg["image_media_type"] is None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
venv/bin/pytest tests/test_conversation_store.py -k "image" -v
```
Expected: FAIL — `add_message` does not accept `image_data` param yet.

- [ ] **Step 3: Update `add_message()`**

In `backend/conversation_store.py`, update the function signature:

```python
def add_message(
    conversation_id: str,
    role: str,
    content: str,
    *,
    mode: str | None = None,
    server: str | None = None,
    buid: str | None = None,
    answer_id: str | None = None,
    confidence: str | None = None,
    sources: dict | None = None,
    tool_trace: list[dict] | None = None,
    missing_context: list[str] | None = None,
    agent_id: str = "conwo",
    cost_inr: float | None = None,
    image_data: bytes | None = None,
    image_media_type: str | None = None,
) -> dict[str, Any]:
```

Update the `INSERT` statement to include the new columns:

```python
conn.execute(
    """
    INSERT INTO messages (
        id, conversation_id, role, content, created_at, mode, server, buid,
        answer_id, confidence, sources_json, tool_trace_json, missing_context_json,
        agent_id, cost_inr, image_data, image_media_type
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """,
    (
        mid, conversation_id, role, content, now, mode, server, buid,
        answer_id, confidence,
        json.dumps(sources) if sources is not None else None,
        json.dumps(tool_trace) if tool_trace is not None else None,
        json.dumps(missing_context) if missing_context is not None else None,
        agent_id, cost_inr,
        image_data, image_media_type,
    ),
)
```

Update the return dict at the end of `add_message()` to include the new fields:

```python
return {
    "id": mid,
    "conversation_id": conversation_id,
    "role": role,
    "content": content,
    "created_at": now,
    # ... existing fields ...
    "image_data": image_data,
    "image_media_type": image_media_type,
}
```

- [ ] **Step 4: Update `_row_to_message()`**

```python
def _row_to_message(row: Any) -> dict[str, Any]:
    return {
        "id": row["id"],
        "conversation_id": row["conversation_id"],
        "role": row["role"],
        "content": row["content"],
        "created_at": row["created_at"],
        "mode": row["mode"],
        "server": row["server"],
        "buid": row["buid"],
        "answer_id": row["answer_id"],
        "confidence": row["confidence"],
        "sources": _safe_json(row["sources_json"]),
        "tool_trace": _safe_json(row["tool_trace_json"]),
        "missing_context": _safe_json(row["missing_context_json"]),
        "cost_inr": float(row["cost_inr"]) if row["cost_inr"] is not None else None,
        "image_data": bytes(row["image_data"]) if row["image_data"] is not None else None,
        "image_media_type": row["image_media_type"],
    }
```

Also update the `SELECT` in `get_conversation()` to include the new columns:

```python
SELECT id, conversation_id, role, content, created_at, mode, server, buid,
       answer_id, confidence, sources_json, tool_trace_json, missing_context_json,
       cost_inr, image_data, image_media_type
FROM messages
WHERE conversation_id = %s
ORDER BY created_at ASC
```

- [ ] **Step 5: Run tests**

```bash
venv/bin/pytest tests/test_conversation_store.py -k "image" -v
```
Expected: all 3 PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/conversation_store.py tests/test_conversation_store.py
git commit -m "feat(store): persist image_data and image_media_type on messages"
```

---

## Task 5: orchestrator.py — replay images in conversation history

**Files:**
- Modify: `backend/orchestrator.py`
- Test: `tests/test_orchestrator.py` (add new tests)

**Interfaces:**
- Consumes: `_row_to_message()` now returns `image_data: bytes | None` and `image_media_type: str | None` (Task 4)
- Produces:
  - `_load_conversation_context()` returns content blocks (list) for image messages, plain string for text-only
  - `run_orchestrator(..., image_data: bytes | None = None, image_media_type: str | None = None)` — new optional params

- [ ] **Step 1: Write failing tests**

Add to `tests/test_orchestrator.py`:

```python
def test_load_conversation_context_includes_image_blocks():
    """Messages with image_data produce content block lists, not plain strings."""
    from backend.orchestrator import _load_conversation_context
    from unittest.mock import patch

    img_bytes = b"\x89PNG\r\n\x1a\n"
    fake_conv = {
        "messages": [
            {"role": "user", "content": "describe this",
             "image_data": img_bytes, "image_media_type": "image/png"},
            {"role": "assistant", "content": "It shows a flowchart.",
             "image_data": None, "image_media_type": None},
        ]
    }
    with patch("backend.orchestrator.conversation_store.get_conversation",
               return_value=fake_conv):
        history = _load_conversation_context("fake-id")

    assert len(history) == 0  # last user message is dropped; only assistant remains
    # Re-test with 2 prior + 1 current to get a pair
    fake_conv2 = {
        "messages": [
            {"role": "user", "content": "hi", "image_data": None, "image_media_type": None},
            {"role": "assistant", "content": "hello", "image_data": None, "image_media_type": None},
            {"role": "user", "content": "describe this",
             "image_data": img_bytes, "image_media_type": "image/png"},
        ]
    }
    with patch("backend.orchestrator.conversation_store.get_conversation",
               return_value=fake_conv2):
        history = _load_conversation_context("fake-id")

    # First pair: text-only user → content is a plain string
    assert history[0]["role"] == "user"
    assert isinstance(history[0]["content"], str)
    assert history[0]["content"] == "hi"


def test_load_conversation_context_image_message_becomes_blocks():
    from backend.orchestrator import _load_conversation_context
    from unittest.mock import patch
    import base64

    img_bytes = b"\x89PNG\r\n\x1a\n"
    b64 = base64.standard_b64encode(img_bytes).decode()

    fake_conv = {
        "messages": [
            {"role": "user", "content": "what is this?",
             "image_data": img_bytes, "image_media_type": "image/png"},
            {"role": "assistant", "content": "A diagram.",
             "image_data": None, "image_media_type": None},
            # current turn (will be dropped)
            {"role": "user", "content": "tell me more",
             "image_data": None, "image_media_type": None},
        ]
    }
    with patch("backend.orchestrator.conversation_store.get_conversation",
               return_value=fake_conv):
        history = _load_conversation_context("fake-id")

    # First message had image → content must be a list of blocks
    user_msg = history[0]
    assert user_msg["role"] == "user"
    assert isinstance(user_msg["content"], list)
    assert user_msg["content"][0]["type"] == "image"
    assert user_msg["content"][0]["source"]["data"] == b64
    assert user_msg["content"][1]["type"] == "text"
    assert user_msg["content"][1]["text"] == "what is this?"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
venv/bin/pytest tests/test_orchestrator.py -k "image" -v
```
Expected: FAIL.

- [ ] **Step 3: Update `_load_conversation_context()`**

```python
import base64 as _b64

def _load_conversation_context(conversation_id: str, max_turns: int = 6) -> list[dict]:
    conv = conversation_store.get_conversation(conversation_id)
    if not conv:
        return []
    msgs = [m for m in conv.get("messages", []) if m["role"] in ("user", "assistant")]
    if msgs and msgs[-1]["role"] == "user":
        msgs = msgs[:-1]
    tail = msgs[-(max_turns * 2):]
    if len(tail) % 2 != 0:
        tail = tail[1:]

    result = []
    for m in tail:
        img = m.get("image_data")
        if img and m["role"] == "user":
            b64 = _b64.standard_b64encode(img).decode()
            content = [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": m.get("image_media_type", "image/png"),
                        "data": b64,
                    },
                },
                {"type": "text", "text": m["content"]},
            ]
        else:
            content = m["content"]
        result.append({"role": m["role"], "content": content})
    return result
```

- [ ] **Step 4: Update `run_orchestrator()` signature**

Find the `run_orchestrator` function definition. Add two optional params:

```python
def run_orchestrator(
    question: str,
    *,
    # ... existing params ...
    image_data: bytes | None = None,
    image_media_type: str | None = None,
) -> OrchestratorResult:
```

Inside `run_orchestrator`, find where `user_message` is built and passed to `provider.generate_with_tools`. The `user_message` is a string built by `build_seed_message()`. When an image is present, wrap it in content blocks:

```python
# After: user_message = build_seed_message(...)
if image_data:
    b64 = _b64.standard_b64encode(image_data).decode()
    user_message_content = [
        {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": image_media_type or "image/png",
                "data": b64,
            },
        },
        {"type": "text", "text": user_message},
    ]
else:
    user_message_content = user_message

deep_result = provider.generate_with_tools(
    system_prompt=system_prompt,
    user_message=user_message_content,   # was: user_message
    tool_registry=registry,
    prior_messages=history,
    trace_id=trace_id,
)
```

- [ ] **Step 5: Run tests**

```bash
venv/bin/pytest tests/test_orchestrator.py -k "image" -v
```
Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/orchestrator.py tests/test_orchestrator.py
git commit -m "feat(orchestrator): replay image content blocks in conversation history"
```

---

## Task 6: api.py — accept multipart on /query

**Files:**
- Modify: `backend/api.py`
- Test: `tests/test_api_image.py` (create)

**Interfaces:**
- Consumes: `run_orchestrator(..., image_data=..., image_media_type=...)` from Task 5
- Produces: `/query` accepts both `application/json` and `multipart/form-data`; image bytes extracted and passed to orchestrator; user message saved with `image_data`

- [ ] **Step 1: Write failing tests**

Create `tests/test_api_image.py`:

```python
import io
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

def test_query_with_image_multipart(authed_client):
    """POST /query with multipart form data including an image succeeds."""
    png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 50
    mock_result = MagicMock(
        answer_id="abc123", answer_text="It shows a flowchart.",
        confidence="Medium", sources=MagicMock(wiki_pages=[], jira_keys=[], pms_configs=[]),
        retrieval={}, mode="api", error="", tool_trace=[], missing_context=[],
        deep_search_used=True, conversation_id="conv-1",
        intent="GENERAL", rewritten_query="", intent_confidence=0.0,
        cost_usd=0.0, cost_inr=0.0,
    )
    with patch("backend.api.run_orchestrator", return_value=mock_result):
        resp = authed_client.post(
            "/query",
            data={"question": "what is this diagram?", "mode": "api", "server": "com"},
            files={"image": ("diagram.png", io.BytesIO(png), "image/png")},
        )
    assert resp.status_code == 200
    assert resp.json()["answer_text"] == "It shows a flowchart."


def test_query_json_still_works(authed_client):
    """Existing JSON POST /query is unchanged."""
    mock_result = MagicMock(
        answer_id="xyz", answer_text="Normal answer.",
        confidence="High", sources=MagicMock(wiki_pages=[], jira_keys=[], pms_configs=[]),
        retrieval={}, mode="api", error="", tool_trace=[], missing_context=[],
        deep_search_used=True, conversation_id="conv-2",
        intent="GENERAL", rewritten_query="", intent_confidence=0.0,
        cost_usd=0.0, cost_inr=0.0,
    )
    with patch("backend.api.run_orchestrator", return_value=mock_result):
        resp = authed_client.post(
            "/query",
            json={"question": "how does visitor management work?", "mode": "api", "server": "com"},
        )
    assert resp.status_code == 200
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
venv/bin/pytest tests/test_api_image.py -v
```
Expected: FAIL — `/query` does not accept multipart.

- [ ] **Step 3: Update `/query` to accept multipart**

In `backend/api.py`, find the `/query` endpoint. It currently accepts `req: QueryRequest`. Replace the handler signature to support both content types:

```python
from fastapi import Form, UploadFile, File
from typing import Optional

@app.post("/query", response_model=QueryResponse)
async def query_endpoint(
    request: Request,
    user: dict = Depends(_require_user),
):
    content_type = request.headers.get("content-type", "")

    if "multipart/form-data" in content_type:
        form = await request.form()
        question = form.get("question", "")
        mode = form.get("mode", "api")
        server = form.get("server", "com")
        buid = form.get("buid") or None
        service = form.get("service") or None
        officeid = form.get("officeid") or None
        roomid = form.get("roomid") or None
        role = form.get("role") or None
        conversation_id = form.get("conversation_id") or None
        image_file = form.get("image")
        if image_file and hasattr(image_file, "read"):
            image_bytes = await image_file.read()
            image_media_type = image_file.content_type or "image/png"
        else:
            image_bytes = None
            image_media_type = None
        # Validate manually (model_config extra=forbid is for JSON only)
        if not question or len(question) < 1:
            raise HTTPException(status_code=422, detail="question is required")
        if len(question) > 2000:
            raise HTTPException(status_code=422, detail="question too long")
        if server not in ("com", "in"):
            raise HTTPException(status_code=422, detail="server must be 'com' or 'in'")
    else:
        body = await request.json()
        req = QueryRequest(**body)
        question = req.question
        mode = req.mode
        server = req.server
        buid = req.buid
        service = req.service
        officeid = req.officeid
        roomid = req.roomid
        role = req.role
        conversation_id = req.conversation_id
        image_bytes = None
        image_media_type = None
```

Then update the call to `run_orchestrator` to pass image params, and the `add_message` call for the user message to pass image data:

```python
# In the add_message call for user turn:
conversation_store.add_message(
    conversation_id,
    "user",
    question,
    mode=mode,
    server=server,
    buid=buid,
    agent_id=agent.id,
    image_data=image_bytes,
    image_media_type=image_media_type,
)

# In the run_orchestrator call:
result = run_orchestrator(
    question,
    # ... existing params ...
    image_data=image_bytes,
    image_media_type=image_media_type,
)
```

- [ ] **Step 4: Run tests**

```bash
venv/bin/pytest tests/test_api_image.py -v
```
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/api.py tests/test_api_image.py
git commit -m "feat(api): accept multipart/form-data on /query for image upload"
```

---

## Task 7: Frontend — api.service.ts

**Files:**
- Modify: `frontend/src/app/core/api.service.ts`

**Interfaces:**
- Produces:
  - `ChatMessage` gets `image_data_url?: string | null` field
  - New method: `queryWithImage(req: QueryRequest, image: File): Observable<QueryResponse>`

- [ ] **Step 1: Add `image_data_url` to `ChatMessage`**

In `frontend/src/app/core/api.service.ts`, find the `ChatMessage` interface and add:

```typescript
export interface ChatMessage {
  // ... existing fields ...
  image_data_url?: string | null;  // data URL for display only — not from server
}
```

- [ ] **Step 2: Add `queryWithImage()` method**

In the `ApiService` class, after the existing `query()` method:

```typescript
queryWithImage(req: QueryRequest, image: File): Observable<QueryResponse> {
  const token = this.getAdminToken();
  const headers = token
    ? new HttpHeaders({ Authorization: `Bearer ${token}` })
    : new HttpHeaders();

  const form = new FormData();
  form.append('question', req.question);
  form.append('mode', req.mode ?? 'api');
  form.append('server', req.server ?? 'com');
  if (req.buid)           form.append('buid', req.buid);
  if (req.service)        form.append('service', req.service);
  if (req.officeid)       form.append('officeid', req.officeid);
  if (req.roomid)         form.append('roomid', req.roomid);
  if (req.role)           form.append('role', req.role);
  if (req.conversation_id) form.append('conversation_id', req.conversation_id);
  form.append('image', image);

  return this.http.post<QueryResponse>(`${API_BASE}/query`, form, { headers });
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/app/core/api.service.ts
git commit -m "feat(api-service): add image_data_url to ChatMessage + queryWithImage()"
```

---

## Task 8: Frontend — ask.ts composer (attach + paste + preview + send)

**Files:**
- Modify: `frontend/src/app/features/ask/ask.ts`
- Modify: `frontend/src/app/features/ask/ask.scss`

**Interfaces:**
- Consumes: `api.queryWithImage(req, image)` from Task 7

- [ ] **Step 1: Add image state and file input to ask.ts**

In the `Ask` class, add after `needInputDraft = ''`:

```typescript
attachedImage = signal<File | null>(null);
attachedImageUrl = signal<string | null>(null);

attachImage(file: File | null) {
  if (!file) return;
  this.attachedImage.set(file);
  const reader = new FileReader();
  reader.onload = e => this.attachedImageUrl.set(e.target?.result as string);
  reader.readAsDataURL(file);
}

removeImage() {
  this.attachedImage.set(null);
  this.attachedImageUrl.set(null);
}
```

- [ ] **Step 2: Add paste handler to the textarea**

In the template, find the `<textarea>` and add:

```html
<textarea
  ...existing attributes...
  (paste)="onComposerPaste($event)"
></textarea>
```

Add the handler in the class:

```typescript
onComposerPaste(event: ClipboardEvent) {
  const file = event.clipboardData?.files?.[0];
  if (file && file.type.startsWith('image/')) {
    event.preventDefault();
    this.attachImage(file);
  }
}
```

- [ ] **Step 3: Add hidden file input + attach button + preview to template**

In the composer, just before the `<textarea>`, add the preview block:

```html
@if (attachedImageUrl()) {
  <div class="image-preview">
    <img [src]="attachedImageUrl()" alt="Attached image" class="image-thumb" />
    <button type="button" class="image-remove" (click)="removeImage()" aria-label="Remove image">×</button>
  </div>
}
```

Inside the `composer-input-wrap`, before the send button, add:

```html
<input
  #fileInput
  type="file"
  accept="image/png,image/jpeg,image/webp,image/gif"
  style="display:none"
  (change)="onFileInputChange($event)"
/>
<button
  type="button"
  class="attach-btn"
  (click)="fileInput.click()"
  [disabled]="loading() || agentActive()"
  aria-label="Attach image"
  title="Attach image"
>
  <svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true" fill="none"
       stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
    <path d="M13.5 8.5l-5.5 5.5a4 4 0 01-5.657-5.657l6.364-6.364a2.5 2.5 0 013.535 3.535L6.5 11.5a1 1 0 01-1.414-1.414L10.5 4.5"/>
  </svg>
</button>
```

Add the file input handler:

```typescript
onFileInputChange(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0] ?? null;
  this.attachImage(file);
  (event.target as HTMLInputElement).value = '';  // allow re-selecting same file
}
```

- [ ] **Step 4: Update `runDeepSearch()` to use `queryWithImage()` when image attached**

Find `runDeepSearch()` and update:

```typescript
private runDeepSearch(q: string) {
  this.loading.set(true);

  const payload = {
    question: q,
    mode: 'api' as QueryMode,
    server: this.server,
    buid: this.buid || undefined,
    service: this.service || undefined,
    officeid: this.officeid || undefined,
    roomid: this.roomid || undefined,
    role: this.role || undefined,
    conversation_id: this.conversationId() ?? undefined,
  };

  const image = this.attachedImage();
  const imageUrl = this.attachedImageUrl();
  this.removeImage();  // clear before send

  const request$ = image
    ? this.api.queryWithImage(payload, image)
    : this.api.query(payload);

  request$.subscribe({
    next: res => {
      this.loading.set(false);
      if (res.error) { this.error.set(res.error); return; }
      if (res.conversation_id) {
        this.conversationId.set(res.conversation_id);
        this.store.setActive(res.conversation_id);
      }
      this.appendAssistantFromResponse(res);
      this.store.refresh();
    },
    error: err => {
      this.loading.set(false);
      const detail = err?.error?.detail;
      const msg = Array.isArray(detail)
        ? detail.map((e: { msg?: string }) => e.msg ?? JSON.stringify(e)).join('; ')
        : (typeof detail === 'string' ? detail : 'Request failed. Could not reach the backend.');
      this.error.set(msg);
    },
  });
}
```

Also update `appendAssistantFromResponse` — the optimistic user message already stores `imageUrl`. Update `optimisticUser` in `ask()` to include it:

```typescript
const optimisticUser: ChatMessage = {
  // ... existing fields ...
  image_data_url: imageUrl,
};
```

Wait — `imageUrl` is captured in `runDeepSearch` after `ask()` has already built `optimisticUser`. Fix by capturing image before calling `runDeepSearch`. Update `ask()`:

```typescript
ask() {
  const q = this.question.trim();
  if (!q || !this.canAsk()) return;
  // ... existing guards ...

  this.error.set('');
  this.question = '';

  const imageUrl = this.attachedImageUrl();  // capture before removeImage

  const optimisticUser: ChatMessage = {
    id: `local-${Date.now()}`,
    conversation_id: this.conversationId() ?? '',
    role: 'user',
    content: q,
    created_at: new Date().toISOString(),
    mode: this.mode(),
    server: this.server,
    buid: this.buid || undefined,
    image_data_url: imageUrl,
  };
  this.messages.update(arr => [...arr, optimisticUser]);

  if (this.mode() === 'agent') { this.runAgent(q); return; }
  this.runDeepSearch(q);
}
```

And remove the duplicate `imageUrl` capture from `runDeepSearch` (it's now captured in `ask()`). Instead pass it as a parameter:

```typescript
private runDeepSearch(q: string, imageUrl: string | null = null) {
  // ... imageUrl already captured, removeImage called here
```

Update `ask()` call:
```typescript
this.runDeepSearch(q, imageUrl);
```

- [ ] **Step 5: Render image thumbnail in user message bubbles**

In the template, find the user message rendering block:

```html
@if (m.role === 'user') {
  <article class="message message-user">
    <div class="message-meta">You</div>
    <div class="message-bubble">{{ m.content }}</div>
  </article>
}
```

Update to:

```html
@if (m.role === 'user') {
  <article class="message message-user">
    <div class="message-meta">You</div>
    @if (m.image_data_url) {
      <div class="message-image">
        <img [src]="m.image_data_url" alt="Attached image" class="message-image-thumb" />
      </div>
    }
    <div class="message-bubble">{{ m.content }}</div>
  </article>
}
```

- [ ] **Step 6: Add styles to ask.scss**

```scss
// Image attachment preview above composer
.image-preview {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: var(--surface-2, #f5f5f5);
  border-radius: 8px;
  margin-bottom: 6px;

  .image-thumb {
    height: 80px;
    width: 80px;
    object-fit: cover;
    border-radius: 6px;
    border: 1px solid var(--border, #e0e0e0);
  }

  .image-remove {
    background: none;
    border: none;
    font-size: 18px;
    cursor: pointer;
    color: var(--text-muted, #888);
    line-height: 1;
    padding: 2px 6px;
    border-radius: 4px;
    &:hover { background: var(--surface-3, #eee); }
  }
}

// Attach button in composer
.attach-btn {
  background: none;
  border: none;
  cursor: pointer;
  padding: 6px;
  color: var(--text-muted, #888);
  border-radius: 6px;
  display: flex;
  align-items: center;
  &:hover { background: var(--surface-2, #f5f5f5); color: var(--text, #333); }
  &:disabled { opacity: 0.4; cursor: not-allowed; }
}

// Image in user message bubble
.message-image {
  margin-bottom: 6px;
  .message-image-thumb {
    max-height: 240px;
    max-width: 100%;
    border-radius: 8px;
    display: block;
  }
}
```

- [ ] **Step 7: Manual end-to-end test**

1. Start frontend + backend
2. Open Conwo in browser
3. Paste a screenshot into the composer — verify thumbnail appears
4. Click attach button — verify file picker opens, selecting an image shows thumbnail
5. Click ✕ — verify thumbnail clears
6. Attach an architecture diagram PNG and ask "describe this" — verify response is about the diagram
7. Send a follow-up "what modules are involved?" without attaching a new image — verify Claude still knows about the diagram

- [ ] **Step 8: Commit**

```bash
git add frontend/src/app/features/ask/ask.ts \
        frontend/src/app/features/ask/ask.scss
git commit -m "feat(ask): image attach button, paste, preview, FormData send, history rendering"
```

---

## Task 9: Push PR

- [ ] **Step 1: Push branch**

```bash
git push bitbucket HEAD
```

- [ ] **Step 2: Open PR**

URL from push output → open in browser. Title: `feat: image support — ingest via Vision + query-time attach/paste`

Body:
```
## Summary
- Images (PNG/JPG/WEBP/GIF) can now be uploaded at ingest time — Claude Vision
  describes them as structured text, then the existing ingest pipeline creates wiki pages.
- At query time, users can attach or paste images into the composer. Images are stored
  in the messages table and replayed to Claude on every subsequent turn (same as Claude.ai).

## Test plan
- [ ] Upload a PNG architecture diagram via ingest UI — wiki page created
- [ ] Attach an image in chat and ask "describe this" — relevant answer returned
- [ ] Follow-up question without new image — Claude still references the diagram
- [ ] Paste image from clipboard into composer — thumbnail appears
- [ ] JSON /query (no image) still works — existing tests pass
- [ ] `pytest tests/test_document_extractor.py tests/test_conversation_store.py tests/test_orchestrator.py tests/test_api_image.py`
```
