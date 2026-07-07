"""
Wiki retriever — in-memory keyword index over wiki/**/*.md.

Built at startup via build_index(). Provides search() returning the top
matching pages (full text, not excerpts) for use in the orchestrator context.

Design notes:
- Simple TF-weighted inverted index. No embeddings needed for Phase 1.
- Always includes wiki/configs/<service>.md when the query names a known service.
- Excludes wiki/log.md (append-only, too large, no structured content).
- Call rebuild_index() if wiki files change (e.g., after apply_feedback.py --apply).
"""
from __future__ import annotations

import logging
import re
import threading
from dataclasses import dataclass, field
from pathlib import Path

import frontmatter  # python-frontmatter — same library used by wiki_propose_tools
import yaml         # for yaml.YAMLError catch in _parse_frontmatter

from backend.config import WIKI_DIR, WIKI_INDEX_EXCLUDE

_LOG = logging.getLogger("wiki_retriever")

_STOPWORDS = {
    "a", "an", "the", "is", "in", "on", "at", "to", "for", "of", "and", "or",
    "not", "with", "what", "how", "why", "when", "where", "which", "does",
    "do", "can", "will", "should", "would", "could", "has", "have", "this",
    "that", "it", "be", "are", "was", "were", "by", "from", "its", "their",
}

# Known PMS service names → config page slug
_SERVICE_SLUGS = {
    "meeting-rooms", "meeting_rooms", "meetingrooms",
    "visitor-management", "visitor_management", "vms",
    "guard-app", "guard_app", "guardapp",
    "meal-management", "meal_management",
    "employee-experience", "emp-experience",
    "desk-management", "seat-booking", "wis-seat-booking",
    "pms", "booking-rule-engine", "app-server-config",
}


# Track A: Obsidian leaves "Untitled.md" and dated daily notes at the vault
# root when notes are created without a name. They have no schema and add
# noise to wiki_search / wiki_grep. We filter them at index build time and
# only at wiki root — dated files in subdirs (decisions/, log entries) are
# legitimate.
_DATED_FILENAME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}\.md$")


def _is_obsidian_artifact_at_root(rel: Path) -> bool:
    """Return True if `rel` (relative to wiki/) is an Obsidian artifact we
    should skip. Only filters AT THE ROOT — decisions/2026-05-13-foo.md is
    a legitimate page and is NOT filtered."""
    if rel.parent != Path("."):
        return False
    name = rel.name
    if name.startswith("Untitled"):
        return True
    if _DATED_FILENAME_RE.match(name):
        return True
    return False


@dataclass
class WikiPage:
    path: str          # relative to wiki/, e.g. "modules/meeting-rooms.md"
    title: str
    full_text: str
    tokens: list[str] = field(default_factory=list, repr=False)
    frontmatter: dict = field(default_factory=dict, repr=False)  # parsed YAML frontmatter

    def excerpt(self, max_chars: int = 400) -> str:
        lines = [l for l in self.full_text.splitlines() if l.strip() and not l.startswith("#")]
        text = " ".join(lines)
        return text[:max_chars] + ("…" if len(text) > max_chars else "")


class WikiIndex:
    def __init__(self) -> None:
        self._pages: dict[str, WikiPage] = {}          # path → WikiPage
        self._index: dict[str, list[str]] = {}         # token → [paths]
        self._lock = threading.RLock()

    def build(self, wiki_dir: Path = WIKI_DIR) -> None:
        pages: dict[str, WikiPage] = {}
        index: dict[str, list[str]] = {}

        for md_file in sorted(wiki_dir.rglob("*.md")):
            rel = md_file.relative_to(wiki_dir)
            rel_str = str(rel)
            if rel.name in WIKI_INDEX_EXCLUDE:
                continue
            if _is_obsidian_artifact_at_root(rel):
                # Track A: skip Obsidian junk at wiki/ root (Untitled*, dated
                # daily notes). Dated files in subdirs (e.g.
                # decisions/2026-05-13-foo.md) are legitimate and indexed.
                continue
            text = md_file.read_text(encoding="utf-8", errors="replace")
            title = _extract_title(text, rel.stem)
            tokens = _tokenize(text)
            fm = _parse_frontmatter(text)
            page = WikiPage(path=rel_str, title=title, full_text=text, tokens=tokens, frontmatter=fm)
            pages[rel_str] = page
            for tok in set(tokens):
                index.setdefault(tok, []).append(rel_str)

        with self._lock:
            self._pages = pages
            self._index = index

    # NOTE (multi-worker safety, Track A): the index above is purely in-memory
    # and lives per FastAPI worker. Under multi-worker uvicorn, after a wiki
    # write only the writing worker's index reflects the change until each
    # other worker independently calls rebuild_index(). Pilot is single-worker
    # so this is currently moot; if you ever set --workers > 1, switch to a
    # file-watcher trigger (watchdog package) or a shared Redis cache.

    def search(self, question: str, top_n: int = 5) -> list[WikiPage]:
        query_tokens = set(_tokenize(question))
        with self._lock:
            if not self._pages:
                return []
            scores: dict[str, float] = {}
            for tok in query_tokens:
                postings = self._index.get(tok, [])
                idf = 1.0 / (1 + len(postings))
                for path in postings:
                    page = self._pages[path]
                    tf = page.tokens.count(tok) / max(len(page.tokens), 1)
                    scores[path] = scores.get(path, 0.0) + tf * idf

            # Boost config pages if service name is mentioned
            mentioned_services = _mentioned_services(question)
            for svc in mentioned_services:
                config_path = f"configs/{svc}.md"
                if config_path in self._pages:
                    scores[config_path] = scores.get(config_path, 0.0) + 2.0

            ranked = sorted(scores, key=lambda p: scores[p], reverse=True)
            result = [self._pages[p] for p in ranked[:top_n] if p in self._pages]

            # Always include exact config pages for any mentioned service (even if low score)
            for svc in mentioned_services:
                config_path = f"configs/{svc}.md"
                if config_path in self._pages and not any(p.path == config_path for p in result):
                    result.append(self._pages[config_path])

            return result[:top_n]

    def get_page(self, rel_path: str) -> WikiPage | None:
        base = rel_path.removeprefix("wiki/")
        with self._lock:
            for key in (rel_path, f"{rel_path}.md", base, f"{base}.md"):
                p = self._pages.get(key)
                if p:
                    return p
        return None

    def all_paths(self) -> list[str]:
        with self._lock:
            return list(self._pages.keys())

    def pages(self) -> dict[str, WikiPage]:
        with self._lock:
            return dict(self._pages)

    @property
    def page_count(self) -> int:
        with self._lock:
            return len(self._pages)


def _extract_title(text: str, fallback: str) -> str:
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("# "):
            return line[2:].strip()
        if line.startswith("title:"):
            return line.split(":", 1)[1].strip().strip('"')
    return fallback.replace("-", " ").title()


def _parse_frontmatter(text: str) -> dict:
    """
    Best-effort YAML frontmatter parser. Returns parsed dict on success, or
    empty dict on any failure mode (no frontmatter block, malformed YAML,
    non-mapping payload). Never raises.

    Uses python-frontmatter so in-body `---` separators (horizontal rules)
    don't confuse parsing — same as wiki_propose_tools._extract_frontmatter.
    """
    if not text.startswith("---"):
        return {}
    try:
        post = frontmatter.loads(text)
    except yaml.YAMLError as exc:
        _LOG.warning("malformed frontmatter — returning empty dict: %s", exc)
        return {}
    except Exception as exc:
        _LOG.warning("unexpected frontmatter parse error: %s", exc)
        return {}
    if isinstance(post.metadata, dict):
        return post.metadata
    return {}


def _tokenize(text: str) -> list[str]:
    raw = re.findall(r"[a-zA-Z]{3,}", text.lower())
    return [t for t in raw if t not in _STOPWORDS]


def _mentioned_services(question: str) -> list[str]:
    q_lower = question.lower().replace(" ", "-")
    found: list[str] = []
    for svc in _SERVICE_SLUGS:
        if svc in q_lower:
            # Map alias to canonical slug used in wiki/configs/
            canonical = {
                "vms": "visitor-management",
                "guardapp": "guard-app",
                "meetingrooms": "meeting-rooms",
                "visitor_management": "visitor-management",
                "meeting_rooms": "meeting-rooms",
                "guard_app": "guard-app",
                "meal_management": "meal-management",
                "emp-experience": "employee-experience",
                "seat-booking": "wis-seat-booking",
                "wis-seat-booking": "wis-seat-booking",
            }.get(svc, svc)
            if canonical not in found:
                found.append(canonical)
    return found


# Per-agent index registry — replaces the module-level singleton.
# Keys are agent IDs (e.g. "conwo", "infosec"). Callers never touch this dict
# directly; they go through search()/get_page()/all_paths()/page_count(), which
# resolve the active agent from the current_agent ContextVar via get_index().
_INDICES: dict[str, WikiIndex] = {}
_indices_lock = threading.RLock()


def build_index(agent_id: str | None = None, wiki_dir: Path | None = None) -> WikiIndex:
    """Build (or rebuild) one agent's index.

    agent_id=None  → defaults to the active agent from the ContextVar (or "conwo").
    wiki_dir=None  → resolved from agent_registry; pass explicitly to override
                     (useful in tests where an AgentSpec may not exist).
    """
    from backend import agent_context, agent_registry
    aid = agent_id or agent_context.get_current_agent_id()
    if wiki_dir is None:
        spec = agent_registry.get(aid)
        wiki_dir = spec.wiki_dir
    idx = WikiIndex()
    idx.build(wiki_dir)
    with _indices_lock:
        _INDICES[aid] = idx
    from backend import wiki_graph as _wg
    _wg.invalidate(aid)
    return idx


def get_index(agent_id: str | None = None) -> WikiIndex:
    """Return the index for the given (or active) agent, building it on demand."""
    from backend import agent_context
    aid = agent_id or agent_context.get_current_agent_id()
    with _indices_lock:
        idx = _INDICES.get(aid)
    if idx is None:
        idx = build_index(aid)
    return idx


def rebuild_index(agent_id: str | None = None) -> WikiIndex:
    """Alias for build_index — forces a full re-scan for the active/named agent."""
    return build_index(agent_id)


def search(question: str, top_n: int = 5) -> list[WikiPage]:
    return get_index().search(question, top_n)


def get_page(rel_path: str) -> WikiPage | None:
    page = get_index().get_page(rel_path)
    if page:
        return page
    # Disk fallback: survives a stale/missing in-memory index (e.g. a different
    # replica, or before the agent's index is built). Reads from the active agent's
    # wiki dir on the shared volume.
    try:
        from backend import agent_context
        wd = agent_context.get_current_agent().wiki_dir
        base = rel_path.removeprefix("wiki/")
        for cand in (base, f"{base}.md"):
            f = wd / cand
            if f.is_file():
                text = f.read_text(encoding="utf-8")
                rel = str(f.relative_to(wd)).replace("\\", "/")
                return WikiPage(path=rel, title=_extract_title(text, f.stem), full_text=text)
    except Exception:
        pass
    return None


def all_paths() -> list[str]:
    return get_index().all_paths()


def page_count() -> int:
    return get_index().page_count
