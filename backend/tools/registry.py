"""
ToolRegistry — dispatch layer between the Anthropic tool_use loop and backend tool handlers.

Every tool call from Claude goes through execute():
  - If the tool name is unknown → structured JSON error (never raises)
  - If the handler raises → structured JSON error (never raises)
  - Secrets in tool inputs/outputs are sanitized before writing to the trace

The registry is the trust boundary. Nothing outside it needs to handle tool errors.
"""
from __future__ import annotations

import json
import re
import time
from typing import Callable, TypedDict

from backend import trace_store

_SECRET_RE = re.compile(
    r"("
    r"Bearer\s+[A-Za-z0-9\-_\.=]+"        # Bearer tokens
    r"|eyJ[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+"  # JWTs
    r"|[A-Za-z0-9]{40,}"                    # generic long tokens / API keys
    r")"
)

# Role hierarchy — viewer < contributor < admin
_ROLE_ORDER = {"viewer": 0, "contributor": 1, "admin": 2}

# Map tool name → minimum role required. Empty = all authenticated users.
_TOOL_PERMISSIONS: dict[str, str] = {
    # Track A: all wiki_propose_* tools queue changes that admins later apply.
    # Viewer role is read-only and must not be able to write to the proposal
    # queue (it's audit-relevant state).
    "wiki_propose_new": "contributor",
    "wiki_propose_edit": "contributor",
    "wiki_propose_append": "contributor",
    "wiki_propose_multi_edit": "contributor",
    # Step 8: trigger_jira_sync spends real money ($0.04/delta, ~$37/full).
    # Admin-only so casual contributors can't accidentally trigger a $37 run.
    "trigger_jira_sync": "admin",
}


class ToolTraceEntry(TypedDict):
    round: int
    tool_name: str
    input: dict           # sanitized
    output_summary: str   # first 300 chars of result JSON


def _status_from_result(result: str) -> str:
    """Map a tool's JSON result string to a trace status. Never raises."""
    try:
        obj = json.loads(result)
        if isinstance(obj, dict):
            if obj.get("status") == "credentials_required":
                return "credentials_required"
            if obj.get("code") or obj.get("error"):
                return "error"
    except Exception:
        pass
    return "ok"


class ToolRegistry:
    def __init__(self, user_role: str = "viewer") -> None:
        self._user_role = user_role
        self._handlers: dict[str, Callable] = {}
        self._schemas: list[dict] = []

    def register(self, schema: dict, fn: Callable) -> None:
        self._handlers[schema["name"]] = fn
        self._schemas.append(schema)

    @property
    def schemas(self) -> list[dict]:
        return list(self._schemas)

    def execute(
        self,
        name: str,
        tool_input: dict,
        round_num: int,
        trace_id: str | None = None,
    ) -> tuple[str, ToolTraceEntry]:
        """
        Run a tool by name. Returns (json_result_string, trace_entry).
        Never raises — errors are returned as JSON error objects so the tool
        loop can continue without crashing.

        If trace_id is provided, a fail-open `tool_call` event is recorded for
        this execution (timing + status). trace_id=None → no-op (back-compat).
        """
        _t0 = time.perf_counter()

        def _emit(entry: ToolTraceEntry, result: str) -> None:
            # Fail-open tool_call event. entry["input"]/["output_summary"] are
            # ALREADY sanitized above — pass them straight through.
            trace_store.record_event(
                trace_id, component="tool_execution", event_type="tool_call",
                duration_ms=int((time.perf_counter() - _t0) * 1000),
                round_num=round_num, tool_name=name,
                tool_input_json=json.dumps(entry["input"], default=str),
                tool_output_summary=entry["output_summary"],
                status=_status_from_result(result),
            )

        # Permission check before dispatch
        required_role = _TOOL_PERMISSIONS.get(name, "viewer")
        if _ROLE_ORDER.get(self._user_role, 0) < _ROLE_ORDER.get(required_role, 0):
            result = json.dumps({
                "error": f"Role '{self._user_role}' cannot call '{name}'",
                "code": "permission_denied",
            })
            entry: ToolTraceEntry = {
                "round": round_num,
                "tool_name": name,
                "input": self._sanitize_dict(tool_input),
                "output_summary": self._sanitize_str(result)[:300],
            }
            _emit(entry, result)
            return result, entry

        # Layer 2 guardrail: block destructive tool calls before dispatch
        from backend.guardrail import is_destructive_tool_call, log_blocked
        block_reason = is_destructive_tool_call(name, tool_input)
        if block_reason:
            from backend.guardrail import REFUSAL_MESSAGE
            result = json.dumps({
                "error": REFUSAL_MESSAGE,
                "code": "guardrail_blocked",
                "detail": block_reason,
            })
            entry: ToolTraceEntry = {
                "round": round_num,
                "tool_name": name,
                "input": self._sanitize_dict(tool_input),
                "output_summary": self._sanitize_str(result)[:300],
            }
            log_blocked(user_email=None, question=str(tool_input)[:300],
                        trigger=block_reason, where=f"tool_call:{name}")
            _emit(entry, result)
            return result, entry

        handler = self._handlers.get(name)
        if handler is None:
            result = json.dumps({"error": f"Unknown tool: {name!r}", "code": "unknown_tool"})
        else:
            try:
                output = handler(tool_input)
                result = json.dumps(output, ensure_ascii=False, default=str)
            except Exception as exc:
                result = json.dumps({"error": str(exc), "code": "tool_exception"})

        entry: ToolTraceEntry = {
            "round": round_num,
            "tool_name": name,
            "input": self._sanitize_dict(tool_input),
            "output_summary": self._sanitize_str(result)[:300],
        }
        _emit(entry, result)
        return result, entry

    # ── Sanitizers ────────────────────────────────────────────────────────────

    def _sanitize_dict(self, d: dict) -> dict:
        try:
            return json.loads(self._sanitize_str(json.dumps(d, default=str)))
        except Exception:
            return {}

    def _sanitize_str(self, s: str) -> str:
        return _SECRET_RE.sub("[REDACTED]", s)
