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

# Generic agents need three tool families to run the full ingest pipeline the same
# way Conwo does:
#   - extract_* : the plan phase is tool-driven (planner is handed a file path and
#     MUST call an extract_* tool to read the doc) — see migration 101.
#   - wiki_create_page/edit/append/update_frontmatter/rebuild_index : the EXECUTE
#     phase writes pages directly (build_execute_registry only registers these
#     direct-write tools). Without them the executor has nothing to write with and
#     ingest produces zero pages — see migration 102.
#   - wiki_propose_* : the CHAT path (agent suggesting wiki edits → admin approval).
# These mirror the tools granted to the infosec reference agent.
_GENERIC_TOOLS = ["extract_pdf", "extract_docx", "extract_xlsx", "extract_text_file",
                  "wiki_create_page", "wiki_edit_page", "wiki_append_section",
                  "wiki_update_frontmatter", "wiki_rebuild_index",
                  "wiki_search", "wiki_read_page", "wiki_grep", "wiki_list_pages",
                  "wiki_check_duplicate", "wiki_propose_new", "wiki_propose_edit",
                  "wiki_propose_append", "wiki_propose_multi_edit", "feedback_record"]


def _claude_md_template(name: str, identity: str) -> str:
    return (f"# CLAUDE.md — {name} Agent (auto-generated)\n\n"
            f"{identity}\n\n"
            "Wiki-only agent. Knowledge comes solely from documents ingested into "
            f"`agents/{slugify(name)}/wiki/`. Uses the shared generic wiki methodology "
            "(sources/concepts/entities/relationships/decisions/topics). No Jira/PMS.\n")


def create_agent(name: str, created_by: str):
    from backend import agent_registry, db, wiki_retriever, wiki_schema
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
        _cats = wiki_schema.for_kind("generic").categories
        _sections = "\n".join(f"- **{c.replace('-', ' ').title()}** — `{c}/`" for c in _cats)
        (wiki_abs / "index.md").write_text(
            f"# {name} Wiki Index\n_Total pages: 0_\n\n"
            f"Empty knowledge base — ingest documents to populate it. Page categories:\n\n"
            f"{_sections}\n",
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


PROTECTED = {"conwo", "infosec"}


def update_agent(agent_id: str, *, display_name: str | None = None, identity: str | None = None):
    from backend import db, agent_registry
    sets, params = [], []
    if display_name is not None: sets.append("display_name=%s"); params.append(display_name)
    if identity is not None:     sets.append("identity=%s");     params.append(identity)
    if not sets:
        return
    params.append(agent_id)
    with db.connection() as c:
        c.execute(f"UPDATE agents SET {', '.join(sets)} WHERE id=%s", tuple(params))
    agent_registry.invalidate_cache()


def archive_agent(agent_id: str):
    if agent_id in PROTECTED:
        raise AgentError(f"'{agent_id}' is a built-in agent and cannot be removed")
    from backend import db, agent_registry
    with db.connection() as c:
        c.execute("UPDATE agents SET status='archived' WHERE id=%s", (agent_id,))
    agent_registry.invalidate_cache()
