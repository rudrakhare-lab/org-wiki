"""Runtime agent provisioning — create/rename/archive agents from the UI."""
from __future__ import annotations

import hashlib
import re
import colorsys

RESERVED_SLUGS = {"conwo", "infosec", "admin", "api", "agents", "health", "auth",
                  "query", "search", "wiki", "status", "traces", "dashboard", "ingest"}


def slugify(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (name or "").strip().lower()).strip("-")
    return s


def accent_for_slug(slug: str) -> str:
    """Deterministic, pleasant hex from the slug (stable hue, fixed S/L for dark bg)."""
    h = int(hashlib.sha1(slug.encode()).hexdigest(), 16)
    hue = (h % 360) / 360.0
    r, g, b = colorsys.hls_to_rgb(hue, 0.68, 0.62)  # light, saturated → readable on dark
    return "#%02x%02x%02x" % (int(r * 255), int(g * 255), int(b * 255))


def _llm_identity(name: str) -> str | None:
    """One Anthropic call to draft the agent identity. Returns None on any failure."""
    try:
        from backend.config import resolve_api_key
        from backend.providers.anthropic_api import AnthropicAPIProvider
        provider = AnthropicAPIProvider(resolve_api_key())
        sys = ("Write a single 1-2 sentence identity line for an internal company "
               "knowledge assistant. It answers ONLY from documents later ingested into "
               "its wiki. Output ONLY the sentence(s), no preamble.")
        res = provider.generate(sys, f"The assistant is named: {name}")
        if not res.ok:
            return None
        text = (res.raw_answer or "").strip()
        if not (10 <= len(text) <= 400):
            return None
        return text
    except Exception:
        return None


def generate_identity(name: str) -> str:
    out = _llm_identity(name)
    if out:
        return out
    return (f"You are the {name} assistant, answering questions from the "
            f"organization's {name} knowledge base. Answer only from ingested documents.")


class AgentError(Exception): ...
class AgentExists(AgentError): ...
class InvalidAgentName(AgentError): ...

_GENERIC_TOOLS = ["wiki_search", "wiki_read_page", "wiki_grep", "wiki_list_pages",
                  "wiki_check_duplicate", "wiki_propose_new", "wiki_propose_edit",
                  "wiki_propose_append", "wiki_propose_multi_edit", "feedback_record"]


def _claude_md_template(name: str, identity: str) -> str:
    return (f"# CLAUDE.md — {name} Agent (auto-generated)\n\n"
            f"{identity}\n\n"
            "Wiki-only agent. Knowledge comes solely from documents ingested into "
            f"`agents/{slugify(name)}/wiki/`. Uses the shared generic wiki methodology "
            "(sources/concepts/entities/relationships/decisions/topics). No Jira/PMS.\n")


def create_agent(name: str, created_by: str):
    from backend import agent_registry, db, wiki_retriever
    from backend.config import _BASE

    slug = slugify(name)
    if not slug:
        raise InvalidAgentName(f"Cannot derive a slug from {name!r}")
    if slug in RESERVED_SLUGS:
        raise AgentExists(f"'{slug}' is reserved")
    with db.connection() as c:
        if c.execute("SELECT 1 FROM agents WHERE id=%s", (slug,)).fetchone():
            raise AgentExists(f"Agent '{slug}' already exists")

    accent = accent_for_slug(slug)
    identity = generate_identity(name)
    wiki_rel, raw_rel, claude_rel = (f"agents/{slug}/wiki", f"agents/{slug}/raw",
                                     f"agents/{slug}/CLAUDE.md")
    wiki_abs = _BASE / wiki_rel
    created_paths = []
    try:
        (wiki_abs / "concepts").mkdir(parents=True, exist_ok=True)
        (_BASE / raw_rel).mkdir(parents=True, exist_ok=True)
        created_paths.append(_BASE / "agents" / slug)
        (wiki_abs / "index.md").write_text(
            f"# {name} Wiki Index\n_Total pages: 0_\n\n(Empty — ingest documents to populate.)\n",
            encoding="utf-8")
        (_BASE / claude_rel).write_text(_claude_md_template(name, identity), encoding="utf-8")

        with db.connection() as c:
            c.execute(
                "INSERT INTO agents (id, display_name, identity, accent, theme_base, "
                "schema_kind, modes, tools, has_jira, has_pms, wiki_dir, raw_dir, "
                "claude_md, prompt_sections, status, created_by) VALUES "
                "(%s,%s,%s,%s,'dark','generic','{api}',%s,false,false,%s,%s,%s,'{}','active',%s)",
                (slug, name.strip(), identity, accent, _GENERIC_TOOLS,
                 wiki_rel, raw_rel, claude_rel, created_by),
            )
    except Exception:
        # Rollback: remove dirs + any row so no half-created agent remains.
        import shutil
        for p in created_paths:
            shutil.rmtree(p, ignore_errors=True)
        try:
            with db.connection() as c:
                c.execute("DELETE FROM agents WHERE id=%s", (slug,))
        except Exception:
            pass
        raise

    agent_registry.invalidate_cache()
    try:
        wiki_retriever.build_index(slug)
    except Exception:
        pass  # index builds lazily on first use anyway
    return agent_registry.get(slug)
