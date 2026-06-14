import importlib
import json
import pytest
from pathlib import Path


# ── Wiki index per-agent scoping tests ───────────────────────────────────────


def test_wiki_index_is_per_agent(tmp_path):
    import backend.wiki_retriever as wr
    from backend import agent_context

    # Build a tiny infosec wiki on disk and index it via the explicit wiki_dir
    # arg (AgentSpec is frozen, so we pass the dir directly rather than patching).
    info_wiki = tmp_path / "infosec_wiki"
    info_wiki.mkdir()
    (info_wiki / "phishing.md").write_text("---\ntype: concept\n---\n# Phishing\nEmail attacks.")

    wr.build_index("infosec", wiki_dir=info_wiki)   # build that agent's index
    token = agent_context.set_current_agent("infosec")
    try:
        paths = [p.path for p in wr.search("phishing", top_n=5)]
    finally:
        agent_context.reset_current_agent(token)
    assert any("phishing" in p for p in paths)


# ── Proposals agent-scoping tests ────────────────────────────────────────────


@pytest.fixture
def isolated_wp(tmp_path, monkeypatch):
    """Point wiki_proposals at a fresh JSONL under tmp_path."""
    import backend.wiki_proposals as wp_module
    importlib.reload(wp_module)
    feedback_dir = tmp_path / "raw" / "feedback"
    feedback_dir.mkdir(parents=True)
    proposals_file = feedback_dir / "wiki_proposals.jsonl"
    monkeypatch.setattr(wp_module, "PROPOSALS_FILE", proposals_file, raising=False)
    monkeypatch.setattr(wp_module, "FEEDBACK_DIR", feedback_dir, raising=False)
    return wp_module


def test_proposals_carry_agent_id(isolated_wp):
    """A proposal created with agent_id='infosec' stores the field."""
    wp = isolated_wp
    pid = wp.create_proposal(
        page_path="modules/vis.md",
        proposed_change="some change",
        submitter_email="a@b.com",
        agent_id="infosec",
    )
    rec = wp.get_proposal(pid)
    assert rec is not None
    assert rec.get("agent_id") == "infosec"


def test_proposals_filtered_by_agent_id(isolated_wp):
    """list_proposals(agent_id=) returns only records for that agent."""
    wp = isolated_wp
    pid_infosec = wp.create_proposal(
        page_path="modules/vis.md",
        proposed_change="infosec change",
        submitter_email="a@b.com",
        agent_id="infosec",
    )
    pid_conwo = wp.create_proposal(
        page_path="modules/meeting.md",
        proposed_change="conwo change",
        submitter_email="b@b.com",
        agent_id="conwo",
    )

    infosec_list = wp.list_proposals(agent_id="infosec")
    conwo_list = wp.list_proposals(agent_id="conwo")

    assert [p["id"] for p in infosec_list] == [pid_infosec]
    assert [p["id"] for p in conwo_list] == [pid_conwo]


def test_proposals_infosec_not_in_conwo_list(isolated_wp):
    """An infosec proposal must NOT appear in a conwo list."""
    wp = isolated_wp
    wp.create_proposal(
        page_path="modules/vis.md",
        proposed_change="infosec only",
        submitter_email="a@b.com",
        agent_id="infosec",
    )
    conwo_list = wp.list_proposals(agent_id="conwo")
    assert conwo_list == []


def test_proposals_legacy_records_treated_as_conwo(isolated_wp, tmp_path):
    """Records lacking agent_id are treated as 'conwo' when filtering."""
    wp = isolated_wp
    # Write a legacy record (no agent_id) directly to the file
    legacy = {
        "id": "prop_legacy01",
        "submitter_email": "old@b.com",
        "answer_id": None,
        "reason": "",
        "validation_log": [],
        "suggested_companion_edit": None,
        "status": "pending",
        "admin_note": None,
        "created_at": "2024-01-01T00:00:00+00:00",
        "resolved_at": None,
        "applied_at": None,
        "applied_by": None,
        "proposal_type": "legacy_text",
        "page_path": "modules/old.md",
        "proposed_change": "old change",
        # NOTE: no agent_id field
    }
    with wp.PROPOSALS_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(legacy) + "\n")

    conwo_list = wp.list_proposals(agent_id="conwo")
    infosec_list = wp.list_proposals(agent_id="infosec")

    conwo_ids = [p["id"] for p in conwo_list]
    assert "prop_legacy01" in conwo_ids
    infosec_ids = [p["id"] for p in infosec_list]
    assert "prop_legacy01" not in infosec_ids


def test_new_proposal_default_agent_id_is_conwo(isolated_wp):
    """When agent_id is not specified, it defaults to 'conwo'."""
    wp = isolated_wp
    pid = wp.create_proposal(
        page_path="modules/foo.md",
        proposed_change="something",
        submitter_email="x@y.com",
    )
    rec = wp.get_proposal(pid)
    assert rec.get("agent_id") == "conwo"
    # Also appears in conwo list
    assert any(p["id"] == pid for p in wp.list_proposals(agent_id="conwo"))


# ── Answer-log agent-scoping tests ────────────────────────────────────────────


@pytest.fixture
def isolated_feedback(tmp_path, monkeypatch):
    """Point feedback_service at fresh JSONL files under tmp_path."""
    import backend.feedback_service as fs_module
    importlib.reload(fs_module)
    feedback_dir = tmp_path / "raw" / "feedback"
    feedback_dir.mkdir(parents=True)
    answer_log = feedback_dir / "answer_log.jsonl"
    monkeypatch.setattr(fs_module, "ANSWER_LOG", answer_log, raising=False)
    return fs_module, answer_log


def test_log_answer_carries_agent_id(isolated_feedback):
    """log_answer stores agent_id in the written JSONL record."""
    fs, answer_log = isolated_feedback
    fs.log_answer(
        question="What is X?",
        answer_text="X is Y.",
        confidence="High",
        agent_id="infosec",
    )
    lines = answer_log.read_text().strip().splitlines()
    assert len(lines) == 1
    rec = json.loads(lines[0])
    assert rec.get("agent_id") == "infosec"


def test_log_answer_default_agent_id_is_conwo(isolated_feedback):
    """When agent_id is omitted from log_answer, it defaults to 'conwo'."""
    fs, answer_log = isolated_feedback
    fs.log_answer(
        question="What is Z?",
        answer_text="Z is W.",
        confidence="Medium",
    )
    lines = answer_log.read_text().strip().splitlines()
    rec = json.loads(lines[0])
    assert rec.get("agent_id") == "conwo"


# ── Tool registry scoping tests ───────────────────────────────────────────────


def test_registry_filters_tools_for_infosec():
    from backend.tools import build_registry
    from backend import agent_registry

    info = build_registry(user_role="admin", agent=agent_registry.get("infosec"))
    names = {s["name"] for s in info.schemas}
    assert "wiki_search" in names
    assert "jira_search_ranked" not in names
    assert not any(n.startswith("pms_") for n in names)

    conwo = build_registry(user_role="admin", agent=agent_registry.get("conwo"))
    cnames = {s["name"] for s in conwo.schemas}
    assert "jira_search_ranked" in cnames and "wiki_search" in cnames


# ── DB-backed tests (existing) ────────────────────────────────────────────────


def test_migration_adds_agent_id_columns(clean_db):
    from backend import db
    for table in ("conversations", "messages", "trace_sessions"):
        with db.connection() as conn:
            cols = {
                r[0]
                for r in conn.execute(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name = %s",
                    (table,),
                ).fetchall()
            }
        assert "agent_id" in cols, f"{table} missing agent_id"


def test_conversations_scoped_by_agent(isolated_store):
    cs = isolated_store
    c1 = cs.create_conversation("conwo chat", user_email="u@x.com", agent_id="conwo")
    c2 = cs.create_conversation("infosec chat", user_email="u@x.com", agent_id="infosec")

    conwo_list = cs.list_conversations(user_email="u@x.com", agent_id="conwo")
    infosec_list = cs.list_conversations(user_email="u@x.com", agent_id="infosec")

    assert [c["id"] for c in conwo_list] == [c1["id"]]
    assert [c["id"] for c in infosec_list] == [c2["id"]]


def test_add_message_carries_agent_id(isolated_store):
    cs = isolated_store
    conv = cs.create_conversation("c", user_email="u@x.com", agent_id="infosec")
    msg = cs.add_message(conv["id"], "user", "hello", agent_id="infosec")
    assert msg["agent_id"] == "infosec"


def test_trace_sessions_scoped_by_agent(clean_db):
    from backend import trace_store, db
    trace_store.start_session("t-conwo", mode="api", question="q1", agent_id="conwo")
    trace_store.start_session("t-info", mode="api", question="q2", agent_id="infosec")
    with db.connection() as conn:
        n_info = conn.execute(
            "SELECT COUNT(*) FROM trace_sessions WHERE agent_id = %s", ("infosec",)
        ).fetchone()[0]
        n_conwo = conn.execute(
            "SELECT COUNT(*) FROM trace_sessions WHERE agent_id = %s", ("conwo",)
        ).fetchone()[0]
    assert n_info == 1 and n_conwo == 1


# ── System prompt agent-scoping tests ────────────────────────────────────────


def test_system_prompt_uses_agent_identity():
    from backend import system_prompt
    p = system_prompt.load_system_prompt("conwo")
    assert "Conwo" in p
    # The query-workflow sections (5/9/12) should be present for conwo.
    assert "QUERY" in p or "Jira" in p


def test_deep_prompt_omits_jira_for_wiki_only_agent():
    from backend.deep_system_prompt import load_deep_system_prompt
    from backend import agent_registry
    info = load_deep_system_prompt(agent_registry.get("infosec"))
    assert "Infosec" in info
    assert "Jira" not in info and "PMS" not in info
    conwo = load_deep_system_prompt(agent_registry.get("conwo"))
    assert "Jira" in conwo


def test_preflight_skips_jira_for_wiki_only_agent(monkeypatch):
    import backend.preflight as pf
    from backend import agent_registry, jira_retriever

    called = {"jira": False}
    def _fake_search(*a, **k):
        called["jira"] = True
        return {"buckets": {}}
    monkeypatch.setattr(jira_retriever, "search", _fake_search)

    bundle = pf.run_preflight("any security question", agent=agent_registry.get("infosec"))
    assert called["jira"] is False
    # seed_jira must be empty-ish (no buckets populated)
    assert not bundle.seed_jira.get("buckets")


def test_preflight_runs_jira_for_conwo(monkeypatch):
    import backend.preflight as pf
    from backend import agent_registry, jira_retriever
    called = {"jira": False}
    real = jira_retriever.search
    def _spy(*a, **k):
        called["jira"] = True
        return real(*a, **k)
    monkeypatch.setattr(jira_retriever, "search", _spy)
    pf.run_preflight("desk booking", agent=agent_registry.get("conwo"))
    assert called["jira"] is True


# ── Orchestrator agent-threading tests ───────────────────────────────────────


def test_orchestrator_rejects_disallowed_mode():
    from backend import orchestrator, agent_registry
    with pytest.raises(ValueError):
        orchestrator.run("q", mode="agent", agent=agent_registry.get("infosec"))


def test_orchestrator_run_accepts_agent_kwarg(monkeypatch):
    # run(mode="api") must accept agent= and not raise on signature.
    from backend import orchestrator, agent_registry
    # Stub run_deep so we don't make a real LLM call — just assert it's invoked with the agent.
    captured = {}
    def _fake_run_deep(*args, **kwargs):
        captured["agent"] = kwargs.get("agent")
        from backend.orchestrator import OrchestratorResult, SourceInfo
        return OrchestratorResult(answer_id="x", answer_text="", confidence="Low",
                                  sources=SourceInfo(), retrieval={}, mode="api")
    monkeypatch.setattr(orchestrator, "run_deep", _fake_run_deep)
    orchestrator.run("q", mode="api", agent=agent_registry.get("infosec"))
    assert captured["agent"].id == "infosec"


# ── HTTP endpoint mode-gate tests ────────────────────────────────────────────


def test_infosec_query_rejects_agent_mode():
    from fastapi.testclient import TestClient
    from backend.api import app as _app

    client = TestClient(_app)
    r = client.post("/query", json={"question": "x", "mode": "agent", "server": "com"},
                    headers={"X-Agent-Id": "infosec", "Authorization": "Bearer dev-nonexistent"})
    # Must NEVER 200 into a Conwo subprocess for infosec. Acceptable: 400 (mode gate)
    # or 401/403 (auth short-circuit in bare test env).
    assert r.status_code in (400, 401, 403, 422)


# ── Conversation endpoints agent-scoping tests ────────────────────────────────


def test_conversation_endpoints_scoped_by_agent_header(monkeypatch, clean_db):
    from fastapi.testclient import TestClient
    from backend.api import app, _get_user
    # Stub auth so we have an approved user without real tokens.
    app.dependency_overrides[_get_user] = lambda: {"email": "u@x.com", "role": "general", "approved": True}
    try:
        client = TestClient(app)
        # Create one conversation under each agent via the header.
        rc = client.post("/conversations", json={}, headers={"X-Agent-Id": "conwo"})
        ri = client.post("/conversations", json={}, headers={"X-Agent-Id": "infosec"})
        assert rc.status_code == 200 and ri.status_code == 200
        conwo_id = rc.json()["id"]; infosec_id = ri.json()["id"]

        # List under infosec → only the infosec conversation.
        lst = client.get("/conversations", headers={"X-Agent-Id": "infosec"}).json()
        ids = {c["id"] for c in lst["conversations"]}
        assert infosec_id in ids and conwo_id not in ids

        # Cross-agent GET is forbidden: fetching the conwo conv under infosec header → 404.
        assert client.get(f"/conversations/{conwo_id}", headers={"X-Agent-Id": "infosec"}).status_code == 404
        # Same-agent GET works.
        assert client.get(f"/conversations/{conwo_id}", headers={"X-Agent-Id": "conwo"}).status_code == 200
    finally:
        app.dependency_overrides.clear()


# ── Ingest registry agent-scoping tests ──────────────────────────────────────


def test_ingest_plan_registry_conwo_has_all_tools():
    """conwo (tools=["*"]) gets all plan tools including extract_* and wiki tools."""
    from backend.ingest_service import build_plan_registry
    from backend import agent_registry

    registry = build_plan_registry(agent=agent_registry.get("conwo"))
    names = {s["name"] for s in registry.schemas}
    # Extraction tools must be present for conwo
    assert "extract_pdf" in names
    assert "extract_docx" in names
    assert "extract_xlsx" in names
    assert "extract_text_file" in names
    # Wiki read tools must be present
    assert "wiki_search" in names
    assert "wiki_read_page" in names
    assert "wiki_list_pages" in names
    assert "wiki_check_duplicate" in names


def test_ingest_execute_registry_conwo_has_write_tools():
    """conwo (tools=["*"]) gets all execute tools including wiki_create_page."""
    from backend.ingest_service import build_execute_registry
    from backend import agent_registry

    registry = build_execute_registry(agent=agent_registry.get("conwo"))
    names = {s["name"] for s in registry.schemas}
    assert "wiki_create_page" in names
    assert "wiki_edit_page" in names
    assert "wiki_append_section" in names
    assert "wiki_update_frontmatter" in names
    assert "wiki_rebuild_index" in names
    assert "wiki_read_page" in names
    # No jira/pms tools in execute registry
    assert "jira_search_ranked" not in names
    assert not any(n.startswith("pms_") for n in names)


def test_ingest_plan_registry_infosec_has_wiki_tools_no_jira_pms():
    """infosec allowlist excludes extract_* and jira/pms tools from plan registry."""
    from backend.ingest_service import build_plan_registry
    from backend import agent_registry

    registry = build_plan_registry(agent=agent_registry.get("infosec"))
    names = {s["name"] for s in registry.schemas}
    # infosec has wiki_search + wiki_read_page in its allowlist
    assert "wiki_search" in names
    assert "wiki_read_page" in names
    # extract_* tools are NOT in infosec allowlist
    assert "extract_pdf" not in names
    assert "extract_docx" not in names
    # No jira or pms tools
    assert "jira_search_ranked" not in names
    assert not any(n.startswith("pms_") for n in names)


def test_ingest_execute_registry_infosec_has_no_direct_write_tools():
    """infosec allowlist has wiki_propose_* but NOT wiki_create_page/edit/append."""
    from backend.ingest_service import build_execute_registry
    from backend import agent_registry

    registry = build_execute_registry(agent=agent_registry.get("infosec"))
    names = {s["name"] for s in registry.schemas}
    # Direct write tools are NOT in infosec allowlist
    assert "wiki_create_page" not in names
    assert "wiki_edit_page" not in names
    assert "wiki_append_section" not in names
    assert "wiki_rebuild_index" not in names
    # wiki_read_page IS in infosec allowlist
    assert "wiki_read_page" in names


def test_ingest_upload_dir_conwo_uses_module_constant(tmp_path):
    """For conwo, _uploads_root uses the module-level UPLOAD_DIR constant."""
    import backend.ingest_api as api_module
    from backend import agent_registry

    original_upload_dir = api_module.UPLOAD_DIR
    patched = str(tmp_path / "custom_uploads")
    # Simulate test patching UPLOAD_DIR as existing tests do
    api_module.UPLOAD_DIR = patched
    try:
        conwo = agent_registry.get("conwo")
        result = api_module._uploads_root(conwo)
        assert str(result) == patched
    finally:
        api_module.UPLOAD_DIR = original_upload_dir


def test_ingest_upload_dir_infosec_uses_agent_raw_dir():
    """For infosec, _uploads_root resolves under agent.raw_dir — not the global UPLOAD_DIR."""
    import backend.ingest_api as api_module
    from backend import agent_registry

    infosec = agent_registry.get("infosec")
    result = api_module._uploads_root(infosec)
    expected = infosec.raw_dir / "modules" / "_uploads"
    assert result == expected
    # Must NOT be the same as the conwo path
    conwo_path = api_module._uploads_root(agent_registry.get("conwo"))
    assert result != conwo_path


def test_ingest_plan_registry_no_agent_defaults_to_conwo():
    """build_plan_registry() with no agent defaults to conwo — all tools registered."""
    from backend.ingest_service import build_plan_registry

    registry = build_plan_registry()
    names = {s["name"] for s in registry.schemas}
    assert "extract_pdf" in names
    assert "wiki_search" in names


def test_ingest_execute_registry_no_agent_defaults_to_conwo():
    """build_execute_registry() with no agent defaults to conwo — all tools registered."""
    from backend.ingest_service import build_execute_registry

    registry = build_execute_registry()
    names = {s["name"] for s in registry.schemas}
    assert "wiki_create_page" in names
    assert "wiki_rebuild_index" in names
