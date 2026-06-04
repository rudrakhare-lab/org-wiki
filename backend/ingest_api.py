"""Ingest API — three endpoints for document ingestion.

POST /api/ingest/upload  — save uploaded file
POST /api/ingest/plan    — Phase 1 agent: read-only, returns JSON plan
POST /api/ingest/execute — Phase 2 agent: write tools, SSE streaming (Task 6)

Auth: applied at include_router() time in api.py — this module imports
nothing from backend.api to avoid circular imports.
"""
from __future__ import annotations

import json
import os
import pathlib
import secrets
import time
from typing import AsyncGenerator

import anthropic
from fastapi import APIRouter, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend import ingest_service

router = APIRouter(prefix="/api/ingest")

MAX_UPLOAD_BYTES = 100 * 1024 * 1024  # 100 MB
SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".xlsx", ".md", ".txt", ".rtf"}

# Where uploads land before being moved to raw/modules/{slug}/
UPLOAD_DIR = str(pathlib.Path(__file__).resolve().parent.parent / "raw" / "modules" / "_uploads")

# ── System prompts ────────────────────────────────────────────────────────────

PLAN_SYSTEM_PROMPT = """\
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
1. Extract the document using extract_pdf / extract_docx / extract_xlsx / extract_text_file
2. Call wiki_list_pages to see what already exists
3. Read 3-5 most relevant existing wiki pages for context
4. Output your final answer as JSON only — no prose outside the JSON

OUTPUT: a single JSON object with this structure:
{
  "summary_bullets": ["string", ...],
  "classification": "module|entity|config|source|concept|decision|cross-module",
  "target_slug": "visitor-management",
  "operations": [
    {
      "type": "create|edit|append|update_frontmatter",
      "path": "wiki/...",
      "frontmatter": {},
      "preview": "first 200 chars of planned body",
      "change_description": "what this change does"
    }
  ],
  "cross_references": ["wiki/cross-module/..."],
  "warnings": ["string", ...],
  "agent_reasoning": "one paragraph explaining classification"
}
"""

EXECUTE_SYSTEM_PROMPT = """\
You are an ingestion executor. Execute the approved plan EXACTLY
as specified. Do not re-classify. Do not add or remove operations.

For each operation in the plan:
- "create"             → call wiki_create_page
- "edit"               → call wiki_edit_page
- "append"             → call wiki_append_section
- "update_frontmatter" → call wiki_update_frontmatter

After ALL operations complete successfully, call wiki_rebuild_index.

If any tool call returns an error, stop immediately and do not
continue. Report the error clearly.
"""

MODEL = "claude-sonnet-4-6"


# ── Upload endpoint ───────────────────────────────────────────────────────────

@router.post("/upload")
async def upload_file(
    file: UploadFile,
    notes: str = Form(""),
    target_slug: str = Form(""),
):
    ext = pathlib.Path(file.filename or "").suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type {ext!r}. Allowed: {', '.join(sorted(SUPPORTED_EXTENSIONS))}",
        )

    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File exceeds 100 MB limit")

    upload_id = secrets.token_hex(8)
    dest_dir = pathlib.Path(UPLOAD_DIR) / upload_id
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_file = dest_dir / (file.filename or "upload" + ext)
    dest_file.write_bytes(content)

    return {
        "upload_id": upload_id,
        "filename": file.filename,
        "size": len(content),
        "file_path": str(dest_file),
        "notes": notes,
        "target_slug": target_slug or None,
    }


# ── Plan endpoint ─────────────────────────────────────────────────────────────

class PlanRequest(BaseModel):
    upload_id: str
    notes: str = ""
    target_slug: str = ""


@router.post("/plan")
def plan_ingest(req: PlanRequest):
    if not ingest_service.acquire_lock():
        raise HTTPException(
            status_code=409,
            detail="Another ingestion is in progress. Try again in a moment.",
        )

    try:
        # Locate the uploaded file
        upload_dir = pathlib.Path(UPLOAD_DIR) / req.upload_id
        if not upload_dir.exists():
            raise HTTPException(status_code=404, detail=f"Upload {req.upload_id!r} not found")

        files = [f for f in upload_dir.iterdir() if f.is_file()]
        if not files:
            raise HTTPException(status_code=404, detail="Upload directory is empty")
        file_path = str(files[0])
        filename = files[0].name

        # Compose the user message
        hint = f"\nUser hint — target module: {req.target_slug}" if req.target_slug else ""
        context = f"\nUser context: {req.notes}" if req.notes else ""
        user_message = (
            f"Ingest the document at: {file_path}{hint}{context}\n\n"
            "Produce the JSON plan as your final response."
        )

        registry = ingest_service.build_plan_registry()
        api_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))

        messages: list[dict] = [{"role": "user", "content": user_message}]
        plan_json: dict = {}

        # Run tool-use loop until agent returns end_turn
        for _ in range(20):  # max 20 rounds
            response = api_client.messages.create(
                model=MODEL,
                max_tokens=4096,
                system=PLAN_SYSTEM_PROMPT,
                tools=registry.schemas,
                messages=messages,
            )

            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result_str, _ = registry.execute(block.name, block.input, round_num=0)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result_str,
                    })

            if response.stop_reason == "end_turn":
                # Extract JSON from the final text block
                for block in response.content:
                    if hasattr(block, "text"):
                        text = block.text.strip()
                        # Strip markdown code fences if present
                        if "```" in text:
                            parts = text.split("```")
                            for i, part in enumerate(parts):
                                if i % 2 == 1:  # inside a code fence
                                    if part.startswith("json"):
                                        part = part[4:]
                                    try:
                                        plan_json = json.loads(part.strip())
                                        break
                                    except json.JSONDecodeError:
                                        continue
                        else:
                            try:
                                plan_json = json.loads(text)
                            except json.JSONDecodeError:
                                pass
                break

            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})

        # Detect slug from plan
        slug = plan_json.get("target_slug") or req.target_slug or "unknown"

        session_id = ingest_service.new_session_id()
        session = ingest_service.IngestSession(
            session_id=session_id,
            upload_id=req.upload_id,
            plan=plan_json,
            created_at=time.time(),
            slug=slug,
            filename=filename,
            original_path=file_path,
        )
        ingest_service.store_session(session)

        return {"session_id": session_id, "plan": plan_json}

    finally:
        ingest_service.release_lock()
