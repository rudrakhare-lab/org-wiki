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

import re
from dataclasses import dataclass, field

import anthropic
from anthropic.types import ToolUseBlock

from backend.tools.registry import ToolRegistry, ToolTraceEntry

_MODEL = "claude-sonnet-4-6"
_MAX_TOKENS = 4096
_MAX_ROUNDS_ABSOLUTE = 8

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

                resp = self._client.messages.create(
                    model=_MODEL,
                    max_tokens=_MAX_TOKENS,
                    system=system_prompt,
                    tools=tool_registry.schemas,
                    messages=messages,
                )

                # MUST append full content list before processing tool calls
                messages.append({"role": "assistant", "content": resp.content})

                stop_reason = resp.stop_reason

                if stop_reason in ("end_turn", "stop_sequence"):
                    result.raw_answer = _extract_text(resp.content)
                    break

                if stop_reason == "max_tokens":
                    result.error = "Response truncated (max_tokens). Try a more specific question."
                    result.raw_answer = _extract_text(resp.content)
                    break

                if stop_reason == "tool_use":
                    tool_use_blocks = [b for b in resp.content if isinstance(b, ToolUseBlock)]
                    tool_result_contents = []

                    for block in tool_use_blocks:
                        json_output, trace_entry = tool_registry.execute(
                            name=block.name,
                            tool_input=dict(block.input) if block.input else {},
                            round_num=round_num,
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
                        final_resp = self._client.messages.create(
                            model=_MODEL,
                            max_tokens=_MAX_TOKENS,
                            system=system_prompt,
                            tools=tool_registry.schemas,
                            messages=messages,
                        )
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
