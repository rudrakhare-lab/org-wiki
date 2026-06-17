"""Ingest service — mutex, session state, and per-phase tool registry builders.

Single global mutex: only one ingestion may run at a time.
Session TTL: 600 seconds (10 minutes) between plan and execute.
"""
from __future__ import annotations

import secrets
import threading
import time
from dataclasses import dataclass, field

SESSION_TTL = 600  # seconds

# ── mutex ────────────────────────────────────────────────────────────────────

_lock = threading.Lock()


def acquire_lock() -> bool:
    """Try to acquire the ingest mutex. Returns True if acquired, False if already held."""
    return _lock.acquire(blocking=False)


def release_lock() -> None:
    try:
        _lock.release()
    except RuntimeError:
        pass  # already released


def is_locked() -> bool:
    acquired = _lock.acquire(blocking=False)
    if acquired:
        _lock.release()
        return False
    return True


# ── session state ─────────────────────────────────────────────────────────────

@dataclass
class IngestSession:
    session_id: str
    upload_id: str
    plan: dict
    created_at: float
    slug: str
    filename: str
    original_path: str
    agent_id: str = "conwo"

    @property
    def expired(self) -> bool:
        return (time.time() - self.created_at) > SESSION_TTL


_sessions: dict[str, IngestSession] = {}


def store_session(session: IngestSession) -> None:
    _sessions[session.session_id] = session


def get_session(session_id: str) -> IngestSession | None:
    s = _sessions.get(session_id)
    if s is None:
        return None
    if s.expired:
        del _sessions[session_id]
        return None
    return s


def new_session_id() -> str:
    return secrets.token_hex(12)


# ── tool registries ───────────────────────────────────────────────────────────

def build_plan_registry(agent=None):
    """Phase 1: read-only tools for extraction and wiki lookup. NO write tools.

    Tools are filtered to the agent's allowlist. agent=None defaults to conwo
    (tools=["*"]) which registers all tools — behaviour identical to pre-agent version.
    """
    if agent is None:
        from backend import agent_registry
        agent = agent_registry.default()

    from backend.tools.registry import ToolRegistry
    from backend.tools.wiki_tools import (
        WIKI_SEARCH_SCHEMA, _wiki_search_handler,
        WIKI_READ_PAGE_SCHEMA, _wiki_read_page_handler,
    )
    from backend.tools.wiki_read_tools import (
        WIKI_LIST_PAGES_SCHEMA, _wiki_list_pages_handler,
        WIKI_CHECK_DUPLICATE_SCHEMA, _wiki_check_duplicate_handler,
    )
    from backend.document_extractor import (
        extract_pdf, extract_docx, extract_xlsx, extract_text_file,
    )

    r = ToolRegistry(user_role="contributor")

    def reg(schema, fn):
        if agent.tool_allowed(schema["name"]):
            r.register(schema, fn)

    # Extraction tools
    reg(
        {
            "name": "extract_pdf",
            "description": "Extract text from a PDF file at the given path. Returns {text, page_count, char_count, truncated}.",
            "input_schema": {
                "type": "object",
                "properties": {"file_path": {"type": "string"}},
                "required": ["file_path"],
            },
        },
        lambda inp: extract_pdf(inp["file_path"]),
    )
    reg(
        {
            "name": "extract_docx",
            "description": "Extract text from a DOCX file. Returns {text, char_count, has_tables, truncated}.",
            "input_schema": {
                "type": "object",
                "properties": {"file_path": {"type": "string"}},
                "required": ["file_path"],
            },
        },
        lambda inp: extract_docx(inp["file_path"]),
    )
    reg(
        {
            "name": "extract_xlsx",
            "description": "Extract sheets and text from an XLSX file. Returns {sheets, text_repr, char_count, truncated}.",
            "input_schema": {
                "type": "object",
                "properties": {"file_path": {"type": "string"}},
                "required": ["file_path"],
            },
        },
        lambda inp: extract_xlsx(inp["file_path"]),
    )
    reg(
        {
            "name": "extract_text_file",
            "description": "Extract text from a plain-text file (MD, TXT, RTF). Returns {text, char_count, truncated}.",
            "input_schema": {
                "type": "object",
                "properties": {"file_path": {"type": "string"}},
                "required": ["file_path"],
            },
        },
        lambda inp: extract_text_file(inp["file_path"]),
    )

    # Wiki read tools
    reg(WIKI_SEARCH_SCHEMA, _wiki_search_handler)
    reg(WIKI_READ_PAGE_SCHEMA, _wiki_read_page_handler)
    reg(WIKI_LIST_PAGES_SCHEMA, _wiki_list_pages_handler)
    reg(WIKI_CHECK_DUPLICATE_SCHEMA, _wiki_check_duplicate_handler)

    return r


# ── job store ─────────────────────────────────────────────────────────────────

import asyncio as _asyncio

JOB_TTL = 3600  # 1 hour

@dataclass
class IngestJob:
    job_id: str
    status: str           # "running" | "complete" | "error"
    events: list          # progress dicts appended as each tool runs
    files_created: list
    files_modified: list
    links: list
    error_msg: str
    created_at: float
    agent_id: str = "conwo"
    _task: object = None  # asyncio.Task — kept to prevent GC


_jobs: dict[str, "IngestJob"] = {}


def create_job(job_id: str, agent_id: str = "conwo") -> "IngestJob":
    job = IngestJob(
        job_id=job_id,
        status="running",
        events=[],
        files_created=[],
        files_modified=[],
        links=[],
        error_msg="",
        created_at=time.time(),
        agent_id=agent_id,
    )
    _jobs[job_id] = job
    return job


def get_job(job_id: str) -> "IngestJob | None":
    job = _jobs.get(job_id)
    if job is None:
        return None
    if time.time() - job.created_at > JOB_TTL:
        del _jobs[job_id]
        return None
    return job


# ── plan job store ─────────────────────────────────────────────────────────────

@dataclass
class IngestPlanJob:
    plan_job_id: str
    upload_id: str
    status: str          # "running" | "done" | "error"
    session_id: str      # set when done
    plan: dict           # set when done
    error_msg: str
    created_at: float
    agent_id: str = "conwo"
    _task: object = None  # asyncio.Task — prevents GC


_plan_jobs: dict[str, "IngestPlanJob"] = {}


def create_plan_job(plan_job_id: str, upload_id: str, agent_id: str = "conwo") -> "IngestPlanJob":
    job = IngestPlanJob(
        plan_job_id=plan_job_id,
        upload_id=upload_id,
        status="running",
        session_id="",
        plan={},
        error_msg="",
        created_at=time.time(),
        agent_id=agent_id,
    )
    _plan_jobs[plan_job_id] = job
    return job


def get_plan_job(plan_job_id: str) -> "IngestPlanJob | None":
    job = _plan_jobs.get(plan_job_id)
    if job is None:
        return None
    if time.time() - job.created_at > JOB_TTL:
        del _plan_jobs[plan_job_id]
        return None
    return job


def get_running_plan_job_for_upload(upload_id: str) -> "IngestPlanJob | None":
    """Return an existing running plan job for this upload_id, if any."""
    for job in _plan_jobs.values():
        if job.upload_id == upload_id and job.status == "running":
            return job
    return None


# ── tool registries ───────────────────────────────────────────────────────────

def build_execute_registry(agent=None):
    """Phase 2: write tools plus read access for self-verification. No extraction tools.

    Tools are filtered to the agent's allowlist. agent=None defaults to conwo
    (tools=["*"]) which registers all tools — behaviour identical to pre-agent version.
    """
    if agent is None:
        from backend import agent_registry
        agent = agent_registry.default()

    from backend.tools.registry import ToolRegistry
    from backend.tools.wiki_write_tools import (
        WIKI_CREATE_PAGE_SCHEMA, _wiki_create_page_handler,
        WIKI_EDIT_PAGE_SCHEMA, _wiki_edit_page_handler,
        WIKI_APPEND_SECTION_SCHEMA, _wiki_append_section_handler,
        WIKI_UPDATE_FRONTMATTER_SCHEMA, _wiki_update_frontmatter_handler,
        WIKI_REBUILD_INDEX_SCHEMA, _wiki_rebuild_index_handler,
    )
    from backend.tools.wiki_tools import (
        WIKI_READ_PAGE_SCHEMA, _wiki_read_page_handler,
    )

    # allow_writes=True: this is the admin-gated ingest EXECUTE registry — wiki write
    # tools are its whole purpose. The Layer 2 guardrail otherwise blocks them (it
    # exists to keep the chat/query loop read-only). Writes are scoped to the active
    # agent's wiki dir via agent_context, so an ingest never touches another agent.
    r = ToolRegistry(user_role="contributor", allow_writes=True)

    def reg(schema, fn):
        if agent.tool_allowed(schema["name"]):
            r.register(schema, fn)

    reg(WIKI_CREATE_PAGE_SCHEMA, _wiki_create_page_handler)
    reg(WIKI_EDIT_PAGE_SCHEMA, _wiki_edit_page_handler)
    reg(WIKI_APPEND_SECTION_SCHEMA, _wiki_append_section_handler)
    reg(WIKI_UPDATE_FRONTMATTER_SCHEMA, _wiki_update_frontmatter_handler)
    reg(WIKI_REBUILD_INDEX_SCHEMA, _wiki_rebuild_index_handler)
    # Allow reading pages so the agent can verify its own writes
    reg(WIKI_READ_PAGE_SCHEMA, _wiki_read_page_handler)
    return r
