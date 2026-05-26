"""
Conwo Backend API — FastAPI app.

Endpoints:
  POST /query           → AI-synthesized answer
                          mode="api":         requires Bearer token; uses server-side ANTHROPIC_API_KEY
                          mode="claude-code":  requires Bearer token; uses admin session
  POST /search          → Retrieval-only (wiki + Jira, no API key needed)
  GET  /wiki/{path}     → Full content of a wiki page
  POST /feedback        → Record user feedback
  GET  /health          → Service liveness + wiki page count
  GET  /health/claude-code → Whether the claude CLI is available on this server
  GET  /admin/sync-status      → Last sync timestamps (admin only)
  POST /admin/trigger-sync     → Start incremental Jira sync (admin only)
  GET  /admin/ingest-queue     → List unprocessed files (admin only)
  GET  /admin/feedback          → List pending feedback (admin only)
  POST /admin/feedback/{id}/patch-plan → Dry-run patch preview (admin only)
  POST /admin/feedback/{id}/apply     → Apply patch to wiki (admin only)
  GET  /admin/wiki/proposals    → List wiki proposals (admin only)
  POST /admin/wiki/proposals/{id}/apply         → Apply a typed proposal (admin only)
  POST /admin/wiki/proposals/{id}/mark-applied  → Mark legacy_text proposal applied after manual edit (admin only)
  POST /admin/wiki/proposals/{id}/reject        → Reject a proposal (admin only)
  POST /admin/trigger-drive-sync → Trigger Drive sync (admin only)

Auth (Phase 1):
  Bearer token in Authorization header, validated against config/allowed_users.toml.
  Admin endpoints additionally require role=admin.
  mode="claude-code" requires any valid Bearer token (any role).
"""
from __future__ import annotations

import json
from contextlib import asynccontextmanager
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, HTTPException, Header, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from backend import admin_api, conversation_store, orchestrator, wiki_proposals, wiki_retriever
from backend import config as _config
from backend.config import local_claude_code_enabled
from backend.feedback_service import log_answer, record_feedback
from backend.operational_context import _age_hours
from backend.providers.claude_code_agent import claude_available, stream_claude_code


# ---------------------------------------------------------------------------
# Lifespan — build the wiki index once at startup
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    wiki_retriever.build_index()
    # Single-key deployment check — api-mode queries will return 503 until the
    # operator sets ANTHROPIC_API_KEY. Don't crash; the server must still come
    # up for admin endpoints and conversation CRUD even without an LLM key.
    import logging, os
    if not os.getenv("ANTHROPIC_API_KEY", "").strip():
        logging.getLogger("uvicorn.error").warning(
            "ANTHROPIC_API_KEY is not set. api-mode `/query` requests will fail "
            "with 503 until you configure it. Non-LLM endpoints (admin, "
            "conversations, status) will continue to work."
        )
    if local_claude_code_enabled():
        # Surface the bypass loudly so it can't be enabled by accident in prod.
        logging.getLogger("uvicorn.error").warning(
            "CONWO_LOCAL_CLAUDE_CODE=true → Claude Code endpoints accept "
            "unauthenticated requests. Local-dev only. Do not deploy with this set."
        )
    # Track A: surface count of pre-Track-A free-text proposals still pending.
    # The new admin apply handler (Sub-pass C / G07) cannot apply them
    # automatically; admins need to drain them manually.
    # Defensive: a broken proposal store must not crash startup — the server
    # should still come up to serve queries even if the proposal queue is
    # unreadable (e.g. corrupt JSONL, missing permissions).
    try:
        from backend import wiki_proposals
        wiki_proposals.warn_if_legacy_pending()
    except Exception as exc:
        import logging
        logging.getLogger("uvicorn.error").warning(
            "Track A startup check failed (wiki_proposals.warn_if_legacy_pending): %s. "
            "Server is starting anyway; the proposal queue may need manual inspection.",
            exc,
        )
    yield


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Conwo API",
    description="WorkInSync knowledge query backend",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200", "http://localhost:4201", "http://127.0.0.1:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def _get_user(authorization: str | None = Header(default=None)) -> dict | None:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization[7:].strip()
    return _config.lookup_user_by_token(token)


def _require_user(user: dict | None = Depends(_get_user)) -> dict:
    """Any valid authenticated user (any role)."""
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Provide a valid Bearer token.",
        )
    return user


def _require_user_or_local_dev(user: dict | None = Depends(_get_user)) -> dict:
    """
    Gate Claude Code endpoints.

    Normally requires a valid Bearer token (same as `_require_user`), but if
    the operator has explicitly set CONWO_LOCAL_CLAUDE_CODE=true the request
    is allowed through without a token. The bypass is for local-dev only
    where the backend runs on the user's own laptop. See
    `docs/modes-and-traces.md` for the rationale and security notes.
    """
    if user:
        return user
    if local_claude_code_enabled():
        return {"email": "local-dev", "role": "local-dev"}
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=(
            "Authentication required for Claude Code mode. "
            "Provide a valid Bearer token, or set CONWO_LOCAL_CLAUDE_CODE=true "
            "for local-dev (single-user, localhost-only)."
        ),
    )


def _require_admin(user: dict | None = Depends(_get_user)) -> dict:
    if not user or user.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class QueryRequest(BaseModel):
    # Single-key deployment: the server-side ANTHROPIC_API_KEY is the only key
    # source. Callers do NOT send claude_api_key — any extra field on the body
    # is rejected outright (see model_config).
    model_config = {"extra": "forbid"}

    question: str = Field(..., min_length=3, max_length=2000)
    mode: Literal["api", "claude-code"] = "api"
    server: str = Field(default="com", pattern=r"^(com|in)$")
    buid: str | None = None
    functional_area: str | None = None
    service: str | None = None
    officeid: str | None = None
    roomid: str | None = None
    role: str | None = None
    conversation_id: str | None = None


class QueryResponse(BaseModel):
    answer_id: str
    answer_text: str
    confidence: str
    sources: dict
    retrieval: dict
    mode: str = "api"
    error: str = ""
    tool_trace: list[dict] = []
    missing_context: list[str] = []
    deep_search_used: bool = False
    conversation_id: str | None = None


class AgentStreamRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=2000)
    conversation_id: str | None = None
    server: str = Field(default="com", pattern=r"^(com|in)$")
    buid: str | None = None


class AgentToolCall(BaseModel):
    name: str
    input: dict = {}


class AgentLogRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    answer_text: str = Field(default="")
    tool_calls: list[AgentToolCall] = []
    conversation_id: str | None = None
    mode: str = "claude-code-agent"
    server: str | None = None
    buid: str | None = None


class ConversationCreateRequest(BaseModel):
    title: str | None = Field(default=None, max_length=200)


class ConversationPatchRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)


class SearchRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=2000)
    server: str = Field(default="com", pattern=r"^(com|in)$")


class FeedbackRequest(BaseModel):
    answer_id: str
    question: str
    score: int = Field(..., ge=1, le=5)
    label: str
    correction: str = ""
    expected_answer: str = ""
    sources: list[str] = []
    affected: list[str] = []
    reviewer: str = ""


class CreateUserRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=200)
    role: Literal["viewer", "contributor", "admin"] = "viewer"
    expires_at: str | None = Field(default=None)


class WikiProposalRejectRequest(BaseModel):
    admin_note: str = ""


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    import os
    return {
        "status": "ok",
        "wiki_pages": wiki_retriever.page_count(),
        "has_server_key": bool(os.getenv("ANTHROPIC_API_KEY", "").strip()),
    }


@app.get("/health/claude-code")
def health_claude_code():
    available = orchestrator.claude_code_available()
    local_dev = local_claude_code_enabled()
    if not available:
        note = (
            "Claude Code CLI not found on the backend machine. Install Claude Code "
            "(and run `claude login`) on the machine running this server."
        )
    elif local_dev:
        note = (
            "Claude Code is available and running in LOCAL-DEV mode "
            "(CONWO_LOCAL_CLAUDE_CODE is set). Anyone who can reach this backend can "
            "drive its Claude Code session — do not enable this on shared deployments."
        )
    else:
        note = (
            "Claude Code is available. Requests use the Claude session logged in on "
            "the backend machine. A Bearer token is required to gate access."
        )
    return {
        "available": available,
        "local_dev_unauthenticated": available and local_dev,
        "note": note,
    }


@app.post("/query", response_model=QueryResponse)
def query(
    req: QueryRequest,
    user: dict | None = Depends(_get_user),
):
    # claude-code (legacy single-shot) mode: require Bearer token unless the
    # operator has explicitly enabled local-dev mode.
    if req.mode == "claude-code" and not user and not local_claude_code_enabled():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=(
                "Claude Code mode requires authentication. "
                "Provide a valid Bearer token, or set CONWO_LOCAL_CLAUDE_CODE=true "
                "for local-dev."
            ),
        )

    # API mode: always require authentication. The server's ANTHROPIC_API_KEY is
    # the only key source (single-key deployment), so anonymous callers would
    # otherwise burn the org's Anthropic quota with no per-user rate limit.
    if req.mode == "api" and not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Sign in to send queries.",
        )

    user_email = (user or {}).get("email")
    user_role = (user or {}).get("role", "viewer")

    # Rate limit check before any DB writes (skip for unauthenticated users).
    if user:
        from backend.rate_limit import check_rate_limit
        # Use token as key; fall back to email when token is absent/empty.
        rate_key = user.get("token") or user.get("email", "")
        if not check_rate_limit(rate_key, user_role):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Daily query limit reached (30/day). Resets at midnight UTC.",
            )

    # Resolve / create conversation up front so we can persist the user message
    # even if the orchestrator fails downstream.
    conversation_id = req.conversation_id
    if conversation_id:
        if not conversation_store.get_conversation(conversation_id):
            conversation_id = None  # treat missing id as "start fresh"
    if not conversation_id:
        conv = conversation_store.create_conversation(
            title=conversation_store.auto_title_from_question(req.question),
            user_email=user_email,
        )
        conversation_id = conv["id"]

    conversation_store.add_message(
        conversation_id=conversation_id,
        role="user",
        content=req.question,
        mode=req.mode,
        server=req.server,
        buid=req.buid,
    )

    from backend.config import resolve_api_key
    try:
        resolved_key = resolve_api_key()
    except ValueError as e:
        # Server isn't configured with an API key — return the user-facing
        # message the frontend renders verbatim.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="This deployment is missing an API key. Contact your admin.",
        ) from e

    result = orchestrator.run(
        question=req.question,
        mode=req.mode,
        claude_api_key=resolved_key,
        server=req.server,
        buid=req.buid,
        functional_area=req.functional_area,
        service=req.service,
        officeid=req.officeid,
        roomid=req.roomid,
        role=req.role,
        user_role=user_role,
        conversation_id=conversation_id,
    )

    # Persist the assistant message — even on error we save something so the
    # conversation reflects the attempt.
    assistant_content = result.answer_text or (f"[error] {result.error}" if result.error else "")
    conversation_store.add_message(
        conversation_id=conversation_id,
        role="assistant",
        content=assistant_content,
        mode=result.mode,
        server=req.server,
        buid=req.buid,
        answer_id=result.answer_id or None,
        confidence=result.confidence,
        sources={
            "wiki_pages": result.sources.wiki_pages,
            "jira_keys": result.sources.jira_keys,
            "pms_configs": result.sources.pms_configs,
        },
        tool_trace=result.tool_trace,
        missing_context=result.missing_context,
    )

    return QueryResponse(
        answer_id=result.answer_id,
        answer_text=result.answer_text,
        confidence=result.confidence,
        sources={
            "wiki_pages": result.sources.wiki_pages,
            "jira_keys": result.sources.jira_keys,
            "pms_configs": result.sources.pms_configs,
        },
        retrieval=result.retrieval,
        mode=result.mode,
        error=result.error,
        tool_trace=result.tool_trace,
        missing_context=result.missing_context,
        deep_search_used=result.deep_search_used,
        conversation_id=conversation_id,
    )


@app.post("/query/stream")
async def query_stream(
    req: AgentStreamRequest,
    user: dict = Depends(_require_admin),
):
    """
    Stream a Claude Code agent session over SSE.

    ⚠️  NAMING NOTE (G25): despite the generic `/query/stream` path, this
    endpoint streams ONLY the `mode="claude-code"` subprocess. The default
    `mode="api"` (Anthropic SDK tool-use loop) is NOT streamed by this
    endpoint — `/query` returns it as a single response after all tool
    rounds complete.

    Frontend (`frontend/src/app/core/api.service.ts:324`) hardcodes this
    path, so renaming would be a coordinated cross-stack change. Kept the
    name; clarified the semantics here.

    TODO (G02, gated on API key arrival, D2 = YES): when api-mode streaming
    lands, split this into two endpoints — `/query/stream-claude-code`
    (this one, current behavior) and `/query/stream-api` (the new SSE
    bridge for the Anthropic streaming tool-use loop) — and update the
    frontend to dispatch to the right one based on mode.

    Spawns `claude -p <question>` in the repo root with full tool access
    (Read, Write, Edit, Bash, Grep, MCP, etc. — same as terminal Claude Code).
    Each NDJSON event from the subprocess is forwarded as an SSE `data: ...`
    frame. The stream ends with an `event: done` frame or `event: error` frame.

    Auth: any authenticated user (any role). The subprocess inherits the
    server's Claude Code session — billing follows whoever ran `claude login`.
    """
    if not claude_available():
        raise HTTPException(
            status_code=503,
            detail="Claude Code CLI not installed on this server.",
        )

    # Resolve / create conversation, save the user message before the stream
    # so it appears in history even if the stream is cancelled.
    conversation_id = req.conversation_id
    if conversation_id and not conversation_store.get_conversation(conversation_id):
        conversation_id = None
    if not conversation_id:
        conv = conversation_store.create_conversation(
            title=conversation_store.auto_title_from_question(req.question)
        )
        conversation_id = conv["id"]

    conversation_store.add_message(
        conversation_id=conversation_id,
        role="user",
        content=req.question,
        mode="claude-code-agent",
        server=req.server,
        buid=req.buid,
    )

    # Deterministic preflight: run the SAME wiki+Jira+ticket retrieval we do
    # for Deep Search, then prepend the result to the question we hand to
    # Claude Code. This guarantees the agent never starts blind, regardless
    # of whether it chooses to invoke its own tools.
    # Disable with CONWO_AGENT_PREFLIGHT=false if you want raw behavior.
    import os
    from backend.preflight import build_agent_preamble, run_preflight

    preflight_enabled = os.getenv("CONWO_AGENT_PREFLIGHT", "true").strip().lower() not in {
        "0", "false", "no", "off"
    }
    if preflight_enabled:
        bundle = run_preflight(req.question)
        augmented_question = build_agent_preamble(bundle) + f"**User question:** {req.question}"
        preflight_keys = [t.get("key") for t in bundle.preflight_tickets if t.get("key")]
    else:
        bundle = None
        augmented_question = req.question
        preflight_keys = []

    async def event_source():
        # Front-load events the client uses to wire up state.
        yield (
            f"event: conversation\n"
            f"data: {json.dumps({'conversation_id': conversation_id})}\n\n"
        )
        if preflight_enabled and bundle is not None:
            yield (
                f"event: preflight\n"
                f"data: {json.dumps({'tickets': preflight_keys, **bundle.stats()})}\n\n"
            )
        try:
            async for event in stream_claude_code(augmented_question):
                yield f"data: {json.dumps(event)}\n\n"
            yield "event: done\ndata: {}\n\n"
        except Exception as exc:
            yield f"event: error\ndata: {json.dumps({'error': str(exc)})}\n\n"

    return StreamingResponse(
        event_source(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@app.post("/agent/log-answer")
def log_agent_answer(req: AgentLogRequest, user: dict = Depends(_require_admin)):
    """
    Log a Claude Code agent answer for feedback linkage.

    Extracts wiki paths from Read tool calls, Jira keys from the answer text,
    and confidence from the answer text if formatted. Returns an answer_id
    suitable for /feedback.
    """
    import re

    wiki_paths: list[str] = []
    for call in req.tool_calls:
        if call.name != "Read":
            continue
        fp = str((call.input or {}).get("file_path", ""))
        # Use rsplit so absolute paths under "/Users/.../my-wiki/org-wiki/wiki/..."
        # don't match the outer "my-wiki/" segment.
        if "wiki/" in fp:
            rel = "wiki/" + fp.rsplit("wiki/", 1)[1]
            if rel not in wiki_paths:
                wiki_paths.append(rel)

    jira_keys = list(dict.fromkeys(re.findall(r"\b([A-Z]{2,}-\d+)\b", req.answer_text)))[:10]

    m = re.search(
        r"\*{0,2}Confidence[:\s*]+\*{0,2}(High|Medium|Low)",
        req.answer_text,
        re.IGNORECASE,
    )
    confidence = m.group(1).capitalize() if m else "Medium"

    answer_id = log_answer(
        question=req.question,
        answer_text=req.answer_text,
        confidence=confidence,
        wiki_pages=wiki_paths[:10],
        jira_keys=jira_keys,
        pms_configs=[],
        retrieval_notes=f"agent_mode tools={len(req.tool_calls)}",
    )

    # Persist the assistant message into the conversation if one was supplied.
    # The user message was already persisted at /query/stream open.
    if req.conversation_id and conversation_store.get_conversation(req.conversation_id):
        # Tool calls from Claude Code's stream-json may include absolute paths;
        # we keep them as-is (already free of secrets per the registry policy).
        sanitized_trace = [
            {
                "round": i + 1,
                "tool_name": call.name,
                "input": call.input or {},
                "output_summary": "",
            }
            for i, call in enumerate(req.tool_calls[:50])
        ]
        conversation_store.add_message(
            conversation_id=req.conversation_id,
            role="assistant",
            content=req.answer_text,
            mode=req.mode,
            server=req.server,
            buid=req.buid,
            answer_id=answer_id,
            confidence=confidence,
            sources={"wiki_pages": wiki_paths[:10], "jira_keys": jira_keys, "pms_configs": []},
            tool_trace=sanitized_trace,
            missing_context=[],
        )

    return {
        "answer_id": answer_id,
        "confidence": confidence,
        "wiki_pages": wiki_paths[:10],
        "jira_keys": jira_keys,
    }


@app.post("/search")
def search(req: SearchRequest):
    return orchestrator.search_only(req.question, server=req.server)


@app.get("/wiki/{path:path}")
def get_wiki_page(path: str):
    page = wiki_retriever.get_page(path)
    if not page:
        raise HTTPException(status_code=404, detail=f"Wiki page not found: {path}")
    return {"path": page.path, "title": page.title, "content": page.full_text}


# ---------------------------------------------------------------------------
# Conversations — chat history CRUD
# ---------------------------------------------------------------------------

def _check_conversation_access(conversation_id: str, user: dict) -> dict:
    """Load conversation and verify the user can access it. Returns the conversation.

    Non-admin users can only see their own conversations; returns 404 (not 403)
    for both missing and unauthorized IDs to avoid leaking existence to third parties.
    """
    conv = conversation_store.get_conversation(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if user.get("role") != "admin" and conv.get("user_email") != user.get("email"):
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv


@app.post("/conversations")
def create_conversation(req: ConversationCreateRequest, user: dict | None = Depends(_get_user)):
    user_email = (user or {}).get("email")
    return conversation_store.create_conversation(title=req.title, user_email=user_email)


@app.get("/conversations")
def list_conversations(limit: int = 200, user: dict = Depends(_require_user)):
    if limit < 1:
        limit = 1
    if limit > 500:
        limit = 500
    # Admins see all conversations; everyone else sees only their own
    user_email = None if user.get("role") == "admin" else user.get("email")
    return {"conversations": conversation_store.list_conversations(limit=limit, user_email=user_email)}


@app.get("/conversations/{conversation_id}")
def get_conversation(conversation_id: str, user: dict = Depends(_require_user)):
    conv = _check_conversation_access(conversation_id, user)
    return conv


@app.patch("/conversations/{conversation_id}")
def patch_conversation(
    conversation_id: str,
    req: ConversationPatchRequest,
    user: dict = Depends(_require_user),
):
    _check_conversation_access(conversation_id, user)
    ok = conversation_store.update_conversation_title(conversation_id, req.title)
    if not ok:
        raise HTTPException(status_code=404, detail="Conversation not found")
    conv = conversation_store.get_conversation(conversation_id)
    return {"id": conv["id"], "title": conv["title"], "updated_at": conv["updated_at"]}


@app.delete("/conversations/{conversation_id}")
def delete_conversation(conversation_id: str, user: dict = Depends(_require_user)):
    _check_conversation_access(conversation_id, user)
    ok = conversation_store.delete_conversation(conversation_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"deleted": True, "id": conversation_id}


@app.post("/feedback")
def feedback(req: FeedbackRequest):
    valid_labels = {
        "correct", "partially_correct", "wrong", "incomplete", "outdated",
        "conflicting_evidence", "wrong_config", "wrong_scope", "missing_jira",
        "missing_pms_runtime", "missing_runtime_context", "unclear",
    }
    if req.label not in valid_labels:
        raise HTTPException(status_code=400, detail=f"Invalid label: {req.label}")

    feedback_id = record_feedback(
        answer_id=req.answer_id,
        question=req.question,
        score=req.score,
        label=req.label,
        correction=req.correction,
        expected_answer=req.expected_answer,
        sources=req.sources,
        affected=req.affected,
        reviewer=req.reviewer,
    )
    return {"feedback_id": feedback_id, "status": "recorded"}


# ---------------------------------------------------------------------------
# Operational status (any authenticated user — drives the chat-page banner)
# ---------------------------------------------------------------------------

@app.get("/status")
def public_status(user: dict = Depends(_require_user)):
    """Lightweight freshness signals every signed-in user can see — Jira mirror
    age, wiki page count, and (admins only) the wiki-proposal review queue
    count. The chat page polls this on load to warn about stale data."""
    sync = admin_api.get_sync_status()
    jira = sync.get("jira", {}) or {}
    success_ts = jira.get("most_recent_successful_sync") or ""
    age_h = _age_hours(success_ts) if success_ts else None

    result: dict = {
        "jira_mirror_age_hours": age_h,
        "last_successful_sync": success_ts or None,
        "wiki_page_count": wiki_retriever.page_count(),
        "pending_admin_review_count": 0,
    }
    if user.get("role") == "admin":
        try:
            pending = wiki_proposals.list_proposals(status="pending")
            result["pending_admin_review_count"] = len(pending)
        except Exception:
            pass  # admin-only field; degrade silently rather than 500 the endpoint
    return result


# ---------------------------------------------------------------------------
# Admin endpoints (require admin Bearer token)
# ---------------------------------------------------------------------------

@app.get("/admin/sync-status")
def sync_status(admin: dict = Depends(_require_admin)):
    return admin_api.get_sync_status()


@app.post("/admin/trigger-sync")
def trigger_sync(admin: dict = Depends(_require_admin)):
    return admin_api.trigger_jira_sync()


@app.get("/admin/ingest-queue")
def ingest_queue(admin: dict = Depends(_require_admin)):
    return admin_api.get_ingest_queue()


@app.get("/admin/feedback")
def admin_feedback(
    status: str = "pending",
    limit: int = 50,
    admin: dict = Depends(_require_admin),
):
    return admin_api.get_feedback_list(status=status, limit=limit)


@app.post("/admin/feedback/{feedback_id}/patch-plan")
def patch_plan(feedback_id: str, admin: dict = Depends(_require_admin)):
    return admin_api.get_patch_plan(feedback_id)


@app.post("/admin/feedback/{feedback_id}/apply")
def apply_feedback_patch(feedback_id: str, admin: dict = Depends(_require_admin)):
    result = admin_api.apply_patch(feedback_id)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result)
    return result


@app.post("/admin/users")
def admin_create_user(
    req: CreateUserRequest,
    _admin: dict = Depends(_require_admin),
):
    """Create a user and issue their first token. Returns the token once (not stored in plaintext)."""
    from backend import auth_store
    # Idempotent: if user already exists, just issue a new token
    if not auth_store.get_user(req.email):
        auth_store.create_user(
            req.email,
            role=req.role,
            created_by=_admin.get("email"),
        )
    token = auth_store.create_token(req.email, expires_at=req.expires_at)
    return {
        "email": req.email,
        "role": req.role,
        "token": token,
        "expires_at": req.expires_at,
        "note": "Store this token securely — it will not be shown again.",
    }


@app.get("/admin/users")
def admin_list_users(_admin: dict = Depends(_require_admin)):
    from backend import auth_store
    return {"users": auth_store.list_users()}


@app.delete("/admin/users/{email:path}")
def admin_delete_user(email: str, _admin: dict = Depends(_require_admin)):
    from backend import auth_store
    deleted = auth_store.delete_user(email)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"User not found: {email}")
    return {"deleted": True, "email": email}


@app.delete("/admin/tokens/{token}")
def admin_revoke_token(token: str, _admin: dict = Depends(_require_admin)):
    from backend import auth_store
    revoked = auth_store.revoke_token(token)
    if not revoked:
        raise HTTPException(status_code=404, detail="Token not found")
    return {"revoked": True}


_VALID_PROPOSAL_ID = __import__("re").compile(r"^[a-zA-Z0-9_\-]{8,64}$")


def _validate_proposal_id(proposal_id: str) -> None:
    if not _VALID_PROPOSAL_ID.match(proposal_id):
        raise HTTPException(status_code=400, detail="Invalid proposal_id")


@app.get("/admin/wiki/proposals")
def admin_list_wiki_proposals(
    status: Literal["pending", "applied", "rejected"] | None = None,
    _admin: dict = Depends(_require_admin),
):
    return {"proposals": admin_api.get_wiki_proposals(status=status)}


@app.post("/admin/wiki/proposals/{proposal_id}/apply")
def admin_apply_wiki_proposal(
    proposal_id: str,
    _admin: dict = Depends(_require_admin),
):
    """Apply a typed proposal (Track A Sub-pass C). Dispatches by proposal_type
    in admin_api.apply_wiki_proposal. The HTTP status mirrors the result's
    `code` so the admin UI can distinguish 404 (not_found), 409 (already_applied
    / stale_proposal), 422 (legacy_text_refused), and 500 (write_io_error etc.)."""
    _validate_proposal_id(proposal_id)
    applied_by = _admin.get("email", "admin")
    result = admin_api.apply_wiki_proposal(proposal_id, applied_by=applied_by)
    if not result.get("success"):
        code = result.get("code", "")
        if code == "not_found":
            status_code = 404
        elif code in ("already_applied",):
            status_code = 200  # idempotent — already_applied success path
        elif code in ("stale_proposal",):
            status_code = 409
        elif code == "legacy_text_refused":
            status_code = 422
        else:
            status_code = 500
        raise HTTPException(status_code=status_code, detail=result)
    return result


@app.post("/admin/wiki/proposals/{proposal_id}/mark-applied")
def admin_mark_wiki_proposal_applied(
    proposal_id: str,
    _admin: dict = Depends(_require_admin),
):
    """Mark a LEGACY_TEXT proposal as applied after the admin has manually
    edited the wiki page. Returns 400 if called on a structured proposal
    (those must use /apply, which dispatches to the writer)."""
    _validate_proposal_id(proposal_id)
    applied_by = _admin.get("email", "admin")
    result = admin_api.mark_wiki_proposal_applied(proposal_id, applied_by=applied_by)
    if not result.get("success"):
        code = result.get("code", "")
        status_code = 404 if code == "not_found" else 400
        raise HTTPException(status_code=status_code, detail=result)
    return result


@app.post("/admin/wiki/proposals/{proposal_id}/reject")
def admin_reject_wiki_proposal(
    proposal_id: str,
    req: WikiProposalRejectRequest,
    _admin: dict = Depends(_require_admin),
):
    _validate_proposal_id(proposal_id)
    result = admin_api.reject_wiki_proposal(proposal_id, admin_note=req.admin_note)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", "Reject failed"))
    return result


@app.post("/admin/trigger-drive-sync")
def trigger_drive_sync(_admin: dict = Depends(_require_admin)):
    return admin_api.trigger_drive_sync()
