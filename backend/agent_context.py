"""Request-scoped active-agent context.

The orchestrator receives the AgentSpec explicitly, but leaf code that today
reads the module-global WIKI_DIR (wiki_retriever, wiki tools) reads the active
agent from this ContextVar instead. Set/reset per request in middleware.
"""
from __future__ import annotations

from contextvars import ContextVar, Token

from backend import agent_registry
from backend.agent_registry import AgentSpec

_current: ContextVar[str] = ContextVar("current_agent", default="conwo")


def set_current_agent(agent_id: str | None) -> Token:
    return _current.set(agent_id or "conwo")


def reset_current_agent(token: Token) -> None:
    _current.reset(token)


def get_current_agent_id() -> str:
    return _current.get()


def get_current_agent() -> AgentSpec:
    return agent_registry.get(_current.get())
