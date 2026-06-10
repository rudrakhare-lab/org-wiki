"""
DeepQueryProvider — runs the Anthropic tool_use loop for agentic deep search.

Each call to generate_with_tools():
  1. Sends the user message + tool definitions to Claude
  2. If Claude requests tool calls → dispatches all tool_use blocks in the turn
  3. Sends all tool_result blocks back as one user message
  4. Repeats until stop_reason is end_turn, or max_rounds is exhausted
  5. On exhaustion, sends a forced-synthesis user message for one final Claude call

Critical protocol notes (Anthropic tool_use message format):
  - The full resp.content list (not just text) MUST be appended as the assistant message
    before processing tool calls, or the conversation will be malformed.
  - All tool_use blocks in a single assistant turn must produce one user message
    containing ALL their tool_result dicts — never one message per block.
  - tool_result content must be a string (JSON-serialized), not a dict.

Secrets are never included in the tool_trace — see ToolRegistry._sanitize_str().
"""
from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass, field

import anthropic
from anthropic.types import ToolUseBlock

from backend import trace_store
from backend.tools.registry import ToolRegistry, ToolTraceEntry

# G24: model id configurable via env so we can swap without redeploy.
_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
_MAX_TOKENS = int(os.getenv("MAX_OUTPUT_TOKENS", "8192"))
# G10: round cap configurable via env so we can tune in production without
# redeploy. Default 12 (bumped from 8) — complex PMS-debug queries can need
# DEFAULT + BUID + 3 OFFICEID + wiki_read + jira_search etc. Needs eval
# validation when API key arrives.
_MAX_ROUNDS_ABSOLUTE = int(os.getenv("MAX_TOOL_ROUNDS", "12"))

_FORCE_SYNTHESIS = (
    "You have reached the maximum number of tool-use rounds. "
    "Synthesize a complete final answer from the evidence gathered so far. "
    "If critical information is still missing, list it under a 'Missing context:' heading."
)

_MISSING_CTX_RE = re.compile(
    r"Missing context[:\s]+(.+?)(?:\n\n|\Z)", re.IGNORECASE | re.DOTALL
)


@dataclass
class DeepProviderResult:
    raw_answer: str = ""
    tool_trace: list[ToolTraceEntry] = field(default_factory=list)
    missing_context: list[str] = field(default_factory=list)
    error: str = ""
    rounds_used: int = 0

    @property
    def ok(self) -> bool:
        return not self.error and bool(self.raw_answer)


class DeepQueryProvider:
    """Runs a multi-round Anthropic tool_use loop for deep evidence gathering."""

    def __init__(self, api_key: str) -> None:
        self._client = anthropic.Anthropic(api_key=api_key)

    def generate_with_tools(
        self,
        system_prompt: str,
        user_message: str,
        tool_registry: ToolRegistry,
        max_rounds: int = _MAX_ROUNDS_ABSOLUTE,
        prior_messages: list[dict] | None = None,
        trace_id: str | None = None,
    ) -> DeepProviderResult:
        max_rounds = min(max_rounds, _MAX_ROUNDS_ABSOLUTE)
        messages: list[dict] = list(prior_messages or []) + [
            {"role": "user", "content": user_message}
        ]
        tool_trace: list[ToolTraceEntry] = []
        result = DeepProviderResult()
        round_num = 0

        try:
            while round_num < max_rounds:
                round_num += 1

                _t0 = time.perf_counter()
                resp = self._client.messages.create(
                    model=_MODEL,
                    max_tokens=_MAX_TOKENS,
                    system=system_prompt,
                    tools=tool_registry.schemas,
                    messages=messages,
                )
                _record_llm(trace_id, resp, round_num,
                            int((time.perf_counter() - _t0) * 1000), is_synthesis=False)

                # MUST append full content list before processing tool calls
                messages.append({"role": "assistant", "content": resp.content})

                stop_reason = resp.stop_reason

                if stop_reason in ("end_turn", "stop_sequence"):
                    result.raw_answer = _extract_text(resp.content)
                    break

                if stop_reason == "max_tokens":
                    # Return whatever was generated rather than failing.
                    # Append a soft warning so the user knows the answer may be incomplete.
                    result.raw_answer = (
                        _extract_text(resp.content)
                        + "\n\n---\n_Note: response reached the maximum output length and may be incomplete. "
                        "Try asking about a specific section for more detail._"
                    )
                    break

                if stop_reason == "tool_use":
                    tool_use_blocks = [b for b in resp.content if isinstance(b, ToolUseBlock)]
                    tool_result_contents = []

                    for block in tool_use_blocks:
                        json_output, trace_entry = tool_registry.execute(
                            name=block.name,
                            tool_input=dict(block.input) if block.input else {},
                            round_num=round_num,
                            trace_id=trace_id,
                        )
                        tool_trace.append(trace_entry)
                        tool_result_contents.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json_output,
                        })

                    # One user message with ALL tool_results
                    messages.append({"role": "user", "content": tool_result_contents})

                    # If this was the last allowed round, force synthesis
                    if round_num >= max_rounds:
                        messages.append({"role": "user", "content": _FORCE_SYNTHESIS})
                        _t0 = time.perf_counter()
                        final_resp = self._client.messages.create(
                            model=_MODEL,
                            max_tokens=_MAX_TOKENS,
                            system=system_prompt,
                            tools=tool_registry.schemas,
                            messages=messages,
                        )
                        _record_llm(trace_id, final_resp, round_num,
                                    int((time.perf_counter() - _t0) * 1000), is_synthesis=True)
                        result.raw_answer = _extract_text(final_resp.content)
                        break

        except anthropic.AuthenticationError:
            result.error = "Invalid Anthropic API key. Please check your key and try again."
        except anthropic.RateLimitError:
            result.error = "Anthropic API rate limit reached. Please wait a moment and retry."
        except Exception as exc:
            result.error = f"Deep search error: {exc}"

        result.tool_trace = tool_trace
        result.rounds_used = round_num
        result.missing_context = _extract_missing_context(result.raw_answer)
        return result


# ── Helpers ───────────────────────────────────────────────────────────────────

def _record_llm(trace_id, resp, round_num, duration_ms, is_synthesis):
    """Fail-open llm_response trace event. Tolerates missing/changed resp.usage shape."""
    u = getattr(resp, "usage", None)
    trace_store.record_event(
        trace_id, component="llm_call", event_type="llm_response",
        duration_ms=duration_ms, round_num=round_num, status="ok",
        metadata={
            "model": getattr(resp, "model", _MODEL),
            "input_tokens": getattr(u, "input_tokens", 0),
            "output_tokens": getattr(u, "output_tokens", 0),
            "cache_read_input_tokens": getattr(u, "cache_read_input_tokens", 0),
            "cache_creation_input_tokens": getattr(u, "cache_creation_input_tokens", 0),
            "stop_reason": getattr(resp, "stop_reason", None),
            "is_synthesis": is_synthesis,
        })


def _extract_text(content: list) -> str:
    parts = []
    for block in content:
        if hasattr(block, "text") and isinstance(block.text, str):
            parts.append(block.text)
    return "\n".join(parts).strip()


def _extract_missing_context(text: str) -> list[str]:
    if not text:
        return []
    m = _MISSING_CTX_RE.search(text)
    if not m:
        return []
    lines = [ln.strip().lstrip("•-* ") for ln in m.group(1).splitlines() if ln.strip()]
    return [ln for ln in lines if ln]
