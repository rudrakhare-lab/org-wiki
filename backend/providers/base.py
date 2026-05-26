"""
Provider abstraction for the query LLM backend.

Two concrete providers:
  AnthropicAPIProvider  — calls Anthropic API with the user's own api_key.
  ClaudeCodeProvider    — calls `claude -p` subprocess using the admin's
                          enterprise Claude Code session (no api_key required).

Both expose the same generate() interface so orchestrator.py can dispatch
to either without caring about the underlying transport.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass
class ProviderResult:
    raw_answer: str
    error: str = ""

    @property
    def ok(self) -> bool:
        return not self.error and bool(self.raw_answer)


@runtime_checkable
class QueryProvider(Protocol):
    def generate(self, system_prompt: str, user_message: str) -> ProviderResult: ...
