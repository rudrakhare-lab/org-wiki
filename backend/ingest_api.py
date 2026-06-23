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
from fastapi import APIRouter, Depends, Form, HTTPException, Request, UploadFile
from pydantic import BaseModel

from backend import agent_registry, ingest_service

router = APIRouter(prefix="/api/ingest")
_LOG = logging.getLogger("ingest")

# Strong-reference set for fire-and-forget bulk tasks; prevents GC mid-batch.
_BULK_TASKS: set = set()

MAX_UPLOAD_BYTES = 100 * 1024 * 1024  # 100 MB
SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".xlsx", ".md", ".txt", ".rtf"}

# Where uploads land before being moved to raw/modules/{slug}/.
# Uses RAW_DIR so it honors CONWO_DATA_DIR (the mounted PVC) in prod.
# UPLOAD_DIR is kept as a module-level string for test patchability (tests patch this).
from backend.config import RAW_DIR as _RAW_DIR
UPLOAD_DIR = str(_RAW_DIR / "modules" / "_uploads")


def _get_agent(request: Request) -> agent_registry.AgentSpec:
    """Resolve the active agent from middleware-set request.state.agent_id.

    Replicated locally from api._get_agent to avoid a circular import
    (ingest_api.py must not import from api.py).
    """
    return agent_registry.get(getattr(request.state, "agent_id", "conwo"))


def _uploads_root(agent: agent_registry.AgentSpec) -> pathlib.Path:
    """Return the upload staging dir for the active agent.

    For conwo (or when UPLOAD_DIR has been patched in tests), uses the
    module-level UPLOAD_DIR constant so existing tests continue to work.
    For any other agent, resolves under that agent's raw_dir.
    """
    if agent.id == agent_registry.DEFAULT_AGENT_ID:
        return pathlib.Path(UPLOAD_DIR)
    return agent.raw_dir / "modules" / "_uploads"


def _regenerate_index_md(agent: agent_registry.AgentSpec) -> None:
    """Rebuild the agent's index.md as a live table of contents grouped by category.
    Conwo (schema_kind='workinsync') keeps its hand-curated index — skip it."""
    if agent.schema_kind == "workinsync":
        return
    from backend.wiki_retriever import _extract_title
    wiki_dir = agent.wiki_dir
    by_cat: dict[str, list[tuple[str, str]]] = {}
    total = 0
    for p in sorted(wiki_dir.rglob("*.md")):
        rel = str(p.relative_to(wiki_dir)).replace("\\", "/")
        if rel == "index.md":
            continue
        total += 1
        cat = rel.split("/", 1)[0] if "/" in rel else "other"
        try:
            title = _extract_title(p.read_text(encoding="utf-8"), p.stem.replace("-", " ").title())
        except OSError:
            title = p.stem.replace("-", " ").title()
        by_cat.setdefault(cat, []).append((title, rel))
    lines = [f"# {agent.display_name} Wiki Index", f"_Total pages: {total}_", ""]
    if total == 0:
        lines.append("Empty knowledge base — ingest documents to populate it.")
    else:
        for cat in sorted(by_cat):
            lines.append(f"## {cat.replace('-', ' ').title()}")
            for title, rel in sorted(by_cat[cat]):
                lines.append(f"- [{title}]({rel})")
            lines.append("")
    try:
        (wiki_dir / "index.md").write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    except OSError:
        pass

# ── System prompts ────────────────────────────────────────────────────────────

_WIKI_STRUCTURE_WORKINSYNC = """\
WIKI STRUCTURE:
- wiki/sources/<slug>.md       — every ingested doc gets one
- wiki/modules/<slug>.md       — product modules
- wiki/entities/<slug>.md      — data models / domain objects
- wiki/cross-module/<a>-<b>.md — when two modules connect
- wiki/decisions/<date>-<title>.md — architecture decisions
- wiki/configs/<slug>.md       — PMS config tables"""

_WIKI_STRUCTURE_GENERIC = """\
WIKI STRUCTURE:
- wiki/sources/<slug>.md        — every ingested doc gets one
- wiki/concepts/<slug>.md       — a concept, term, or topic
- wiki/entities/<slug>.md       — data models / domain objects
- wiki/relationships/<a>-<b>.md — when two topics connect
- wiki/decisions/<date>-<title>.md — decisions/rationale
- wiki/topics/<slug>.md         — a subject area that groups concepts"""

_CLASSIFICATION_ORDER_WORKINSYNC = """\
CLASSIFICATION ORDER:
1. Folder context — raw/modules/<slug>/ tells you the module
2. Doc type from content (PRD, SOP, spec, config sheet)
3. Entity definitions (fields + types → entity pages)
4. Dependency language ("calls X API") → cross-module pages
5. Decision language ("we chose X because") → decision pages
6. Config tables (property + description columns) → config pages"""

_CLASSIFICATION_ORDER_GENERIC = """\
CLASSIFICATION ORDER:
1. Doc type from content (report, spec, guide, reference)
2. Core concepts, terms, or topics introduced → concept pages
3. Entity definitions (fields + types → entity pages)
4. Relationship language ("X relates to / depends on Y") → relationship pages
5. Decision language ("we chose X because") → decision pages
6. Broad subject areas that group several concepts → topic pages"""


def _wiki_structure(agent: agent_registry.AgentSpec) -> str:
    return (
        _WIKI_STRUCTURE_WORKINSYNC
        if agent.schema_kind == "workinsync"
        else _WIKI_STRUCTURE_GENERIC
    )


def _classification_order(agent: agent_registry.AgentSpec) -> str:
    return (
        _CLASSIFICATION_ORDER_WORKINSYNC
        if agent.schema_kind == "workinsync"
        else _CLASSIFICATION_ORDER_GENERIC
    )


def _classification_kinds(agent: agent_registry.AgentSpec) -> str:
    return (
        "module|entity|config|source|concept|decision|cross-module"
        if agent.schema_kind == "workinsync"
        else "concept|entity|topic|source|decision|relationship"
    )


def _cross_ref_example(agent: agent_registry.AgentSpec) -> str:
    return (
        "wiki/cross-module/..."
        if agent.schema_kind == "workinsync"
        else "wiki/relationships/..."
    )


def _schema_guidance(agent: agent_registry.AgentSpec) -> str:
    if agent.schema_kind == "workinsync":
        return (
            "SLUG RULES: lowercase-hyphenated, match the module folder name.\n"
            "BIDIRECTIONALITY: if module A depends_on B, then B must have used_by A. "
            "Flag any asymmetry as a warning in your plan.\n"
            "Folder context — raw/modules/<slug>/ tells you the module."
        )
    return (
        "SLUG RULES: lowercase-hyphenated, derived from the concept/topic name.\n"
        "RELATIONSHIPS: when two concepts relate, create a relationships/<a>-<b>.md page "
        "whose frontmatter names party_a and party_b (page paths); cite the source via "
        "sourced_from. Do not invent module/config structure.\n"
        "Classify by concept, entity, topic, relationship, decision, or source."
    )


def _render_plan_prompt(agent: agent_registry.AgentSpec) -> str:
    """Return the Phase 1 system prompt, parameterized for the active agent."""
    return f"""\
You are an ingestion planner for the {agent.display_name} wiki.
{agent.identity}
A document has been uploaded. Your job: read it, classify it,
identify cross-references with the existing wiki, and produce
a structured JSON plan. You MUST NOT write anything — you have
no write tools.

{_wiki_structure(agent)}

{_schema_guidance(agent)}
NEVER include wiki/index.md in your operations — the index/home page is generated automatically.
Always call wiki_check_duplicate before proposing a new slug.

{_classification_order(agent)}

MANDATORY STEPS:
1. Extract the document using extract_pdf / extract_docx / extract_xlsx / extract_text_file
2. Call wiki_list_pages to see what already exists
3. Read 3-5 most relevant existing wiki pages for context
4. Output your final answer as JSON only — no prose outside the JSON

OUTPUT: a single JSON object with this structure:
{{
  "summary_bullets": ["string", ...],
  "classification": "{_classification_kinds(agent)}",
  "target_slug": "visitor-management",
  "operations": [
    {{
      "type": "create|edit|append|update_frontmatter",
      "path": "wiki/...",
      "frontmatter": {{}},
      "preview": "first 200 chars of planned body",
      "change_description": "what this change does"
    }}
  ],
  "cross_references": ["{_cross_ref_example(agent)}"],
  "warnings": ["string", ...],
  "agent_reasoning": "one paragraph explaining classification"
}}
"""


def _render_execute_prompt(agent: agent_registry.AgentSpec) -> str:
    """Return the Phase 2 system prompt, parameterized for the active agent."""
    return f"""\
You are an ingestion executor for the {agent.display_name} wiki.
{agent.identity}
Execute the approved plan EXACTLY as specified. Do not re-classify.
Do not add or remove operations.

For each operation in the plan:
- "create"             → call wiki_create_page
- "edit"               → call wiki_edit_page
- "append"             → call wiki_append_section
- "update_frontmatter" → call wiki_update_frontmatter

Never create, edit, or update_frontmatter on wiki/index.md — it is generated
automatically; skip any operation that targets it.

After the operations, call wiki_rebuild_index.

If a tool call returns an error, note it and CONTINUE with the remaining
operations — do not abort the run.
"""

MODEL = "claude-sonnet-4-6"


# ── Upload endpoint ───────────────────────────────────────────────────────────

@router.post("/upload")
async def upload_file(
    request: Request,
    file: UploadFile,
    notes: str = Form(""),
    target_slug: str = Form(""),
    agent: agent_registry.AgentSpec = Depends(_get_agent),
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
    dest_dir = _uploads_root(agent) / upload_id
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_file = dest_dir / (file.filename or "upload" + ext)
    dest_file.write_bytes(content)

    size_kb = len(content) / 1024
    _LOG.info("[upload] %s → upload_id=%s  size=%.1f KB  hint=%r  agent=%s",
              file.filename, upload_id, size_kb, target_slug or "auto-detect", agent.id)
    return {
        "upload_id": upload_id,
        "filename": file.filename,
        "size": len(content),
        "file_path": str(dest_file),
        "notes": notes,
        "target_slug": target_slug or None,
    }


# ── Plan endpoint (background job) ───────────────────────────────────────────

class PlanRequest(BaseModel):
    upload_id: str
    notes: str = ""
    target_slug: str = ""


async def _run_plan_job(
    job: ingest_service.IngestPlanJob,
    file_path: str,
    filename: str,
    notes: str,
    target_slug: str,
) -> None:
    """Background coroutine — runs the Phase 1 planner agent. Releases lock when done.

    Re-establishes the agent ContextVar at the top of the job.  asyncio.create_task
    copies the ContextVar context at task-creation time, but the middleware resets it
    after the request handler returns (which may be before this coroutine runs).
    Explicitly setting it here guarantees wiki tools resolve the correct agent.
    """
    from backend import agent_context as _agent_ctx
    _ctx_token = _agent_ctx.set_current_agent(job.agent_id)
    _LOG.info("[plan_job] job=%s  file=%s  agent=%s", job.plan_job_id[:8], filename, job.agent_id)
    try:
        agent = agent_registry.get(job.agent_id)
        hint = f"\nUser hint — target module: {target_slug}" if target_slug else ""
        context = f"\nUser context: {notes}" if notes else ""
        user_message = (
            f"Ingest the document at: {file_path}{hint}{context}\n\n"
            "Produce the JSON plan as your final response."
        )

        registry = ingest_service.build_plan_registry(agent)
        api_client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))
        messages: list[dict] = [{"role": "user", "content": user_message}]
        plan_json: dict = {}

        for _ in range(20):
            response = await api_client.messages.create(
                model=MODEL,
                max_tokens=8192,
                system=_render_plan_prompt(agent),
                tools=registry.schemas,
                messages=messages,
            )

            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    _LOG.info("[plan_job]   tool → %s(%s)", block.name,
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
                for block in response.content:
                    if hasattr(block, "text"):
                        text = block.text.strip()
                        if "```" in text:
                            parts = text.split("```")
                            for i, part in enumerate(parts):
                                if i % 2 == 1:
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
            if tool_results:
                messages.append({"role": "user", "content": tool_results})
            else:
                # No tool calls and not end_turn (e.g. max_tokens truncation mid-output).
                # Sending an empty user message would 400 ("non-empty content"); nudge the
                # model to finish instead.
                messages.append({"role": "user", "content": (
                    "Continue. When finished, output ONLY the final JSON plan as a single "
                    "```json code block.")})

        if not plan_json:
            _LOG.error("[plan_job] agent returned no parseable JSON  file=%s  job=%s",
                       filename, job.plan_job_id[:8])
            job.error_msg = "Agent returned no parseable plan. Try again."
            job.status = "error"
            return

        slug = plan_json.get("target_slug") or target_slug or "unknown"
        ops = plan_json.get("operations", [])
        _LOG.info("[plan_job] done  slug=%s  ops=%d  warnings=%d  job=%s",
                  slug, len(ops), len(plan_json.get("warnings", [])), job.plan_job_id[:8])

        session_id = ingest_service.new_session_id()
        session = ingest_service.IngestSession(
            session_id=session_id,
            upload_id=job.upload_id,
            plan=plan_json,
            created_at=time.time(),
            slug=slug,
            filename=filename,
            original_path=file_path,
            agent_id=job.agent_id,
        )
        ingest_service.store_session(session)

        job.session_id = session_id
        job.plan = plan_json
        job.status = "done"

    except Exception as exc:
        job.status = "error"
        job.error_msg = str(exc)
        _LOG.exception("[plan_job] FAILED  job=%s  error=%s", job.plan_job_id[:8], exc)
    finally:
        _agent_ctx.reset_current_agent(_ctx_token)
        ingest_service.release_lock()
        _LOG.info("[plan_job] lock released  job=%s", job.plan_job_id[:8])


@router.post("/plan")
async def plan_ingest(
    req: PlanRequest,
    request: Request,
    agent: agent_registry.AgentSpec = Depends(_get_agent),
):
    # Idempotent: reuse any running plan job for this upload_id
    existing = ingest_service.get_running_plan_job_for_upload(req.upload_id)
    if existing:
        _LOG.info("[plan] reusing existing job=%s for upload_id=%s",
                  existing.plan_job_id[:8], req.upload_id)
        return {"plan_job_id": existing.plan_job_id, "status": "running"}

    # Locate upload before acquiring the lock
    upload_dir = _uploads_root(agent) / req.upload_id
    if not upload_dir.exists():
        raise HTTPException(status_code=404, detail=f"Upload {req.upload_id!r} not found")
    files = [f for f in upload_dir.iterdir() if f.is_file()]
    if not files:
        raise HTTPException(status_code=404, detail="Upload directory is empty")
    file_path = str(files[0])
    filename = files[0].name

    if not ingest_service.acquire_lock():
        raise HTTPException(
            status_code=409,
            detail="Another ingestion is in progress. Try again in a moment.",
        )

    plan_job_id = ingest_service.new_session_id()
    job = ingest_service.create_plan_job(plan_job_id, req.upload_id, agent_id=agent.id)

    task = asyncio.create_task(
        _run_plan_job(job, file_path, filename, req.notes, req.target_slug)
    )
    job._task = task

    _LOG.info("[plan] job started  job=%s  file=%s  upload_id=%s  agent=%s",
              plan_job_id[:8], filename, req.upload_id, agent.id)
    return {"plan_job_id": plan_job_id, "status": "running"}


@router.get("/plan_job/{plan_job_id}")
async def get_plan_job_status(plan_job_id: str):
    job = ingest_service.get_plan_job(plan_job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Plan job not found or expired.")
    return {
        "plan_job_id": plan_job_id,
        "status": job.status,
        "session_id": job.session_id,
        "plan": job.plan,
        "error_msg": job.error_msg,
    }


# ── Execute endpoint ──────────────────────────────────────────────────────────

class ExecuteRequest(BaseModel):
    session_id: str


async def _run_ingest_job(
    session: ingest_service.IngestSession,
    job: ingest_service.IngestJob,
) -> None:
    """Background coroutine — runs the Phase 2 agent. No HTTP connection required.

    Re-establishes the agent ContextVar at the top of the job so that wiki write
    tools (_wiki_dir, _safe_path) resolve the correct agent's wiki directory.
    The session's agent_id is canonical — use it even if the request's agent
    differed (the plan was produced for this agent's wiki).
    """
    from backend import agent_context as _agent_ctx, wiki_retriever
    aid = session.agent_id
    _ctx_token = _agent_ctx.set_current_agent(aid)
    _LOG.info("[execute] job=%s  file=%s  slug=%s  ops=%d  agent=%s",
              job.job_id[:8], session.filename, session.slug,
              len(session.plan.get("operations", [])), aid)
    try:
        agent = agent_registry.get(aid)
        registry = ingest_service.build_execute_registry(agent)
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
                max_tokens=8192,
                system=_render_execute_prompt(agent),
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
                        job.warnings.append(f"{block.name} {path}: {result['error']}".strip())

            if response.stop_reason == "end_turn":
                break

            messages.append({"role": "assistant", "content": response.content})
            if tool_results:
                messages.append({"role": "user", "content": tool_results})
            else:
                # No tool calls and not end_turn (e.g. max_tokens truncation). Avoid an
                # empty user message (→ 400); nudge the model to continue executing.
                messages.append({"role": "user", "content": (
                    "Continue executing the remaining operations with the wiki tools. "
                    "When every operation is done, stop.")})

        # Move uploaded file to proper raw/{slug}/ location under agent's raw_dir
        src = pathlib.Path(session.original_path)
        if src.exists():
            dest_dir = agent.raw_dir / "modules" / session.slug
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest = dest_dir / session.filename
            src.rename(dest)
            _LOG.info("[execute]   file moved → %s/%s/%s",
                      agent.raw_dir, session.slug, session.filename)
            try:
                src.parent.rmdir()
            except OSError:
                pass

        # Explicitly rebuild this agent's wiki index — more reliable than relying
        # on the LLM to call wiki_rebuild_index at the right moment.
        try:
            wiki_retriever.build_index(aid)
            _LOG.info("[execute]   index rebuilt  agent=%s", aid)
        except Exception as idx_exc:
            _LOG.warning("[execute]   index rebuild failed  agent=%s  error=%s", aid, idx_exc)

        # Regenerate index.md as a live table of contents (created agents only;
        # Conwo's hand-curated index is left untouched). Never fail the job.
        try:
            _regenerate_index_md(agent)
        except Exception:
            pass

        job.links = [p.replace("wiki/", "").replace(".md", "") for p in job.files_created]
        if not job.files_created and not job.files_modified and job.warnings:
            job.status = "error"
            job.error_msg = job.warnings[-1]
        else:
            job.status = "complete"
        _LOG.info("[execute] DONE  job=%s  status=%s  created=%d  modified=%d  warnings=%d  agent=%s",
                  job.job_id[:8], job.status, len(job.files_created), len(job.files_modified),
                  len(job.warnings), aid)

    except Exception as exc:
        job.status = "error"
        job.error_msg = str(exc)
        _LOG.exception("[execute] FAILED  job=%s  error=%s", job.job_id[:8], exc)
    finally:
        _agent_ctx.reset_current_agent(_ctx_token)
        ingest_service.release_lock()
        _LOG.info("[execute] lock released  job=%s", job.job_id[:8])


@router.post("/execute")
async def execute_ingest(
    req: ExecuteRequest,
    request: Request,
    agent: agent_registry.AgentSpec = Depends(_get_agent),
):
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

    # Use the session's agent_id for the job — the plan was produced for that
    # agent's wiki, so we stay consistent even if the request came from a
    # different agent context.
    job_id = ingest_service.new_session_id()
    job = ingest_service.create_job(job_id, agent_id=session.agent_id)

    # Store task reference to prevent GC killing it mid-run
    task = asyncio.create_task(_run_ingest_job(session, job))
    job._task = task

    _LOG.info("[execute] job started  job=%s  file=%s  slug=%s  agent=%s",
              job_id[:8], session.filename, session.slug, session.agent_id)
    return {"job_id": job_id, "status": "running"}


class BulkIngestRequest(BaseModel):
    upload_ids: list[str]


@router.post("/bulk")
async def start_bulk_ingest(req: BulkIngestRequest, request: Request):
    """Create a bulk batch from already-uploaded files and start the serial runner.
    Each upload_id must exist under the active agent's uploads root."""
    from backend import ingest_batch
    agent = _get_agent(request)
    if not req.upload_ids:
        raise HTTPException(status_code=400, detail="upload_ids must not be empty")
    root = _uploads_root(agent)
    items: list[dict] = []
    for uid in req.upload_ids:
        updir = root / uid
        files = [p for p in updir.iterdir() if p.is_file()] if updir.is_dir() else []
        if not files:
            raise HTTPException(status_code=400, detail=f"unknown or empty upload: {uid}")
        f = files[0]
        items.append({"upload_id": uid, "filename": f.name, "file_path": str(f)})
    created_by = getattr(request.state, "user_email", None)
    result = ingest_batch.create_batch(agent.id, created_by, items)
    task = asyncio.create_task(ingest_batch.run_batch(result["batch_id"]))
    _BULK_TASKS.add(task)
    task.add_done_callback(_BULK_TASKS.discard)
    return result


@router.get("/bulk/{batch_id}")
async def get_bulk_status(batch_id: str, request: Request):
    from backend import ingest_batch
    agent = _get_agent(request)
    got = ingest_batch.get_batch(batch_id)
    if got is None or got["batch"].get("agent_id") != agent.id:
        raise HTTPException(status_code=404, detail="batch not found")
    return got


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
        "warnings": job.warnings,
    }
