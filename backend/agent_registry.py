"""Agent registry — loads config/agents.toml into immutable AgentSpec objects.

One AgentSpec per selectable AI agent. Paths resolve under CONWO_DATA_DIR (PVC)
or repo root, exactly like backend.config, so an agent's wiki/raw/CLAUDE.md live
wherever Conwo's data lives.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # py<3.11
    import tomli as tomllib  # type: ignore

from backend.config import ROOT, _BASE  # _BASE honors CONWO_DATA_DIR

_AGENTS_TOML = ROOT / "config" / "agents.toml"
DEFAULT_AGENT_ID = "conwo"


@dataclass(frozen=True)
class AgentSpec:
    id: str
    display_name: str
    description: str
    wiki_dir: Path
    raw_dir: Path
    claude_md: Path
    prompt_sections: tuple[int, ...]
    tools: tuple[str, ...]
    modes: tuple[str, ...]
    has_jira: bool
    has_pms: bool
    identity: str

    def tool_allowed(self, name: str) -> bool:
        return "*" in self.tools or name in self.tools

    def mode_allowed(self, mode: str) -> bool:
        return mode in self.modes


def _resolve(p: str) -> Path:
    path = Path(p)
    return path if path.is_absolute() else (_BASE / path)


@lru_cache(maxsize=1)
def _load() -> dict[str, AgentSpec]:
    with _AGENTS_TOML.open("rb") as f:
        data = tomllib.load(f)
    out: dict[str, AgentSpec] = {}
    for agent_id, cfg in data.get("agents", {}).items():
        out[agent_id] = AgentSpec(
            id=agent_id,
            display_name=cfg["display_name"],
            description=cfg.get("description", ""),
            wiki_dir=_resolve(cfg["wiki_dir"]),
            raw_dir=_resolve(cfg["raw_dir"]),
            claude_md=_resolve(cfg["claude_md"]),
            prompt_sections=tuple(cfg.get("prompt_sections", [])),
            tools=tuple(cfg.get("tools", ["*"])),
            modes=tuple(cfg.get("modes", ["api"])),
            has_jira=bool(cfg.get("has_jira", False)),
            has_pms=bool(cfg.get("has_pms", False)),
            identity=cfg.get("identity", ""),
        )
    if DEFAULT_AGENT_ID not in out:
        raise RuntimeError(f"agents.toml must define [agents.{DEFAULT_AGENT_ID}]")
    return out


def all() -> list[AgentSpec]:
    return list(_load().values())


def get(agent_id: str | None) -> AgentSpec:
    """Return the AgentSpec for agent_id, falling back to conwo on unknown/None."""
    agents = _load()
    return agents.get(agent_id or "", agents[DEFAULT_AGENT_ID])


def default() -> AgentSpec:
    return _load()[DEFAULT_AGENT_ID]


def invalidate_cache() -> None:
    _load.cache_clear()
