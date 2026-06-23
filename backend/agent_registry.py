"""Agent registry — loads AgentSpec objects from the `agents` Postgres table.

Replaces the static config/agents.toml. A short-TTL cache makes a create on one
replica visible on all replicas within the window. Paths resolve under
CONWO_DATA_DIR (PVC) via backend.config._BASE, exactly as before.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from threading import RLock

from backend.config import _BASE  # honors CONWO_DATA_DIR

DEFAULT_AGENT_ID = "conwo"
_CACHE_TTL_SECONDS = 30


@dataclass(frozen=True)
class AgentSpec:
    id: str
    display_name: str
    identity: str
    accent: str
    theme_base: str          # 'light' | 'dark'
    schema_kind: str         # 'generic' | 'workinsync'
    wiki_dir: Path
    raw_dir: Path
    claude_md: Path
    prompt_sections: tuple[int, ...]
    tools: tuple[str, ...]
    modes: tuple[str, ...]
    has_jira: bool
    has_pms: bool
    status: str = "active"
    description: str = ""    # back-compat alias for any caller; mirrors identity

    def tool_allowed(self, name: str) -> bool:
        return "*" in self.tools or name in self.tools

    def mode_allowed(self, mode: str) -> bool:
        return mode in self.modes


def _resolve(p: str) -> Path:
    path = Path(p)
    return path if path.is_absolute() else (_BASE / path)


_CONWO_FALLBACK = AgentSpec(
    id="conwo", display_name="Conwo",
    identity="You are Conwo, an AI assistant that answers product, config, and debugging questions about WorkInSync.",
    accent="#1e293b", theme_base="light", schema_kind="workinsync",
    wiki_dir=_resolve("wiki"), raw_dir=_resolve("raw"), claude_md=_resolve("CLAUDE.md"),
    prompt_sections=(5, 9, 12), tools=("*",), modes=("api", "agent"),
    has_jira=True, has_pms=True, description="",
)

_lock = RLock()
_cache: dict[str, AgentSpec] | None = None
_cache_at: float = 0.0


def _row_to_spec(r) -> AgentSpec:
    return AgentSpec(
        id=r["id"], display_name=r["display_name"], identity=r["identity"],
        accent=r["accent"], theme_base=r["theme_base"], schema_kind=r["schema_kind"],
        wiki_dir=_resolve(r["wiki_dir"]), raw_dir=_resolve(r["raw_dir"]),
        claude_md=_resolve(r["claude_md"]),
        prompt_sections=tuple(r["prompt_sections"] or ()),
        tools=tuple(r["tools"] or ()), modes=tuple(r["modes"] or ("api",)),
        has_jira=bool(r["has_jira"]), has_pms=bool(r["has_pms"]),
        status=r["status"], description=(r["description"] or r["identity"]),
    )


def _load() -> dict[str, AgentSpec]:
    global _cache, _cache_at
    with _lock:
        if _cache is not None and (time.monotonic() - _cache_at) < _CACHE_TTL_SECONDS:
            return _cache
        try:
            from backend import db
            with db.connection() as c:
                rows = c.execute("SELECT * FROM agents WHERE status = 'active'").fetchall()
            specs = {r["id"]: _row_to_spec(r) for r in rows}
            if DEFAULT_AGENT_ID not in specs:
                specs[DEFAULT_AGENT_ID] = _CONWO_FALLBACK
            _cache = specs
            _cache_at = time.monotonic()
        except Exception:
            # DB unavailable — return last good cache (or fallback); do NOT
            # update _cache_at so the next call retries immediately.
            if _cache is None:
                _cache = {DEFAULT_AGENT_ID: _CONWO_FALLBACK}
                # _cache_at stays 0 — will retry on next call
        return _cache


def all() -> list[AgentSpec]:
    return list(_load().values())


def get(agent_id: str | None) -> AgentSpec:
    agents = _load()
    return agents.get(agent_id or "", agents[DEFAULT_AGENT_ID])


def default() -> AgentSpec:
    return _load()[DEFAULT_AGENT_ID]


def invalidate_cache() -> None:
    global _cache, _cache_at
    with _lock:
        _cache = None
        _cache_at = 0.0
