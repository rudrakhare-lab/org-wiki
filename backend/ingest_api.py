"""Ingest API — three endpoints for document ingestion.

POST /api/ingest/upload  — save uploaded file
POST /api/ingest/plan    — Phase 1 agent: read-only, returns JSON plan
POST /api/ingest/execute — Phase 2 agent: write tools, SSE streaming (Task 6)

Auth: applied at include_router() time in api.py — this module imports
nothing from backend.api to avoid circular imports.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import pathlib
import secrets
import time

import anthropic
from fastapi import APIRouter, Form, HTTPException, UploadFile
from pydantic import BaseModel

from backend import ingest_service

router = APIRouter(prefix="/api/ingest")
_LOG = logging.getLogger("ingest")

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

    size_kb = len(content) / 1024
    _LOG.info("[upload] %s → upload_id=%s  size=%.1f KB  hint=%r",
              file.filename, upload_id, size_kb, target_slug or "auto-detect")
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
async def plan_ingest(req: PlanRequest):
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

        _LOG.info("[plan] starting  file=%s  upload_id=%s", filename, req.upload_id)

        # Compose the user message
        hint = f"\nUser hint — target module: {req.target_slug}" if req.target_slug else ""
        context = f"\nUser context: {req.notes}" if req.notes else ""
        user_message = (
            f"Ingest the document at: {file_path}{hint}{context}\n\n"
            "Produce the JSON plan as your final response."
        )

        registry = ingest_service.build_plan_registry()
        api_client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))

        messages: list[dict] = [{"role": "user", "content": user_message}]
        plan_json: dict = {}

        # Run tool-use loop until agent returns end_turn
        for _ in range(20):  # max 20 rounds
            response = await api_client.messages.create(
                model=MODEL,
                max_tokens=4096,
                system=PLAN_SYSTEM_PROMPT,
                tools=registry.schemas,
                messages=messages,
            )

            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    _LOG.info("[plan]   tool → %s(%s)", block.name,
                              ", ".join(f"{k}={v!r}" for k, v in (block.input or {}).items())[:120])
                    result_str, _ = await asyncio.to_thread(
                        registry.execute, block.name, block.input, 0
                    )
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

        if not plan_json:
            _LOG.error("[plan] agent returned no parseable JSON  file=%s", filename)
            raise HTTPException(status_code=500, detail="Agent returned no parseable plan. Try again.")

        # Detect slug from plan
        slug = plan_json.get("target_slug") or req.target_slug or "unknown"
        ops = plan_json.get("operations", [])
        _LOG.info("[plan] done  slug=%s  ops=%d  warnings=%d",
                  slug, len(ops), len(plan_json.get("warnings", [])))

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


# ── Execute endpoint ──────────────────────────────────────────────────────────

class ExecuteRequest(BaseModel):
    session_id: str


async def _run_ingest_job(session: ingest_service.IngestSession, job: ingest_service.IngestJob) -> None:
    """Background coroutine — runs the Phase 2 agent. No HTTP connection required."""
    _LOG.info("[execute] job=%s  file=%s  slug=%s  ops=%d",
              job.job_id[:8], session.filename, session.slug,
              len(session.plan.get("operations", [])))
    try:
        registry = ingest_service.build_execute_registry()
        api_client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))

        plan = session.plan
        operations = plan.get("operations", [])
        total = len(operations) + 1  # +1 for rebuild_index

        user_msg = (
            f"Execute this approved ingestion plan for file '{session.filename}':\n\n"
            f"{json.dumps(plan, indent=2)}"
        )
        messages: list[dict] = [{"role": "user", "content": user_msg}]
        completed = 0

        for _ in range(30):  # max 30 rounds
            response = await api_client.messages.create(
                model=MODEL,
                max_tokens=4096,
                system=EXECUTE_SYSTEM_PROMPT,
                tools=registry.schemas,
                messages=messages,
            )

            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    path = (block.input or {}).get("path", "")
                    _LOG.info("[execute]   %d/%d  %s  %s",
                              completed + 1, total, block.name, path or "")
                    result_str, _ = await asyncio.to_thread(
                        registry.execute, block.name, block.input, 0
                    )
                    result = json.loads(result_str)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result_str,
                    })
                    completed += 1

                    # Track created vs modified
                    if block.name == "wiki_create_page" and result.get("created"):
                        job.files_created.append(path)
                        _LOG.info("[execute]   ✓ created  %s", path)
                    elif block.name in {"wiki_edit_page", "wiki_append_section", "wiki_update_frontmatter"}:
                        if path and path not in job.files_modified:
                            job.files_modified.append(path)
                        _LOG.info("[execute]   ✓ edited   %s", path)
                    elif block.name == "wiki_rebuild_index":
                        _LOG.info("[execute]   ✓ index rebuilt  pages=%s",
                                  result.get("pages_indexed", "?"))

                    # Determine status label
                    if "error" in result:
                        status_label = "error"
                        _LOG.error("[execute]   ✗ tool error  %s: %s",
                                   block.name, result["error"])
                    elif block.name == "wiki_create_page":
                        status_label = "created"
                    elif block.name == "wiki_rebuild_index":
                        status_label = "rebuilt"
                    else:
                        status_label = "edited"

                    event = {
                        "type": "progress",
                        "tool": block.name,
                        "path": path,
                        "status": status_label,
                        "result": result,
                        "completed": completed,
                        "total": total,
                    }
                    job.events.append(event)

                    if "error" in result:
                        job.status = "error"
                        job.error_msg = result["error"]
                        return

            if response.stop_reason == "end_turn":
                break

            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})

        # Move uploaded file to proper raw/modules/{slug}/ location
        src = pathlib.Path(session.original_path)
        if src.exists():
            dest_dir = pathlib.Path(UPLOAD_DIR).parent / session.slug
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest = dest_dir / session.filename
            src.rename(dest)
            _LOG.info("[execute]   file moved → raw/modules/%s/%s", session.slug, session.filename)
            try:
                src.parent.rmdir()
            except OSError:
                pass

        job.links = [p.replace("wiki/", "").replace(".md", "") for p in job.files_created]
        job.status = "complete"
        _LOG.info("[execute] DONE  job=%s  created=%d  modified=%d",
                  job.job_id[:8], len(job.files_created), len(job.files_modified))

    except Exception as exc:
        job.status = "error"
        job.error_msg = str(exc)
        _LOG.exception("[execute] FAILED  job=%s  error=%s", job.job_id[:8], exc)
    finally:
        ingest_service.release_lock()
        _LOG.info("[execute] lock released  job=%s", job.job_id[:8])


@router.post("/execute")
async def execute_ingest(req: ExecuteRequest):
    session = ingest_service.get_session(req.session_id)
    if session is None:
        raise HTTPException(
            status_code=410,
            detail="Plan expired or not found. Please re-upload and re-plan.",
        )

    if not ingest_service.acquire_lock():
        raise HTTPException(
            status_code=409,
            detail="Another ingestion is in progress. Try again in a moment.",
        )

    job_id = ingest_service.new_session_id()
    job = ingest_service.create_job(job_id)

    # Store task reference to prevent GC killing it mid-run
    task = asyncio.create_task(_run_ingest_job(session, job))
    job._task = task

    _LOG.info("[execute] job started  job=%s  file=%s  slug=%s",
              job_id[:8], session.filename, session.slug)
    return {"job_id": job_id, "status": "running"}


@router.get("/job/{job_id}")
async def get_job_status(job_id: str):
    job = ingest_service.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found or expired.")
    return {
        "job_id": job_id,
        "status": job.status,
        "events": job.events,
        "files_created": job.files_created,
        "files_modified": job.files_modified,
        "links": job.links,
        "error_msg": job.error_msg,
    }
