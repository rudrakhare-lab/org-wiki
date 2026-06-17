from fastapi.testclient import TestClient
from backend.api import app, _get_user


def _admin():
    return {"email": "admin@x.com", "role": "admin", "approved": True}


def test_create_agent_endpoint(clean_db, tmp_path, monkeypatch):
    from backend import config, agent_registry
    monkeypatch.setattr(config, "_BASE", tmp_path, raising=False)
    monkeypatch.setattr(agent_registry, "_BASE", tmp_path, raising=False)
    # Purge any non-builtin agents (clean_db does not truncate the agents table).
    from backend import db
    with db.connection() as c:
        c.execute("DELETE FROM agents WHERE id NOT IN ('conwo', 'infosec')")
    agent_registry.invalidate_cache()
    app.dependency_overrides[_get_user] = _admin
    try:
        c = TestClient(app)
        r = c.post("/admin/agents", json={"name": "Legal"})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["id"] == "legal" and body["accent"].startswith("#")
        # Now visible in the public list
        ids = {a["id"] for a in c.get("/agents").json()}
        assert "legal" in ids
        # Duplicate → 409
        assert c.post("/admin/agents", json={"name": "legal"}).status_code == 409
    finally:
        app.dependency_overrides.clear()
        with db.connection() as conn:
            conn.execute("DELETE FROM agents WHERE id NOT IN ('conwo', 'infosec')")
        agent_registry.invalidate_cache()


def test_created_agent_is_fully_provisioned_and_isolated(clean_db, tmp_path, monkeypatch):
    """E2E milestone check: an agent created through the admin endpoint gets its
    own accent, a generic wiki-only spec, and an isolated, near-empty wiki graph
    — all inherited from shared code, with no Conwo content leaking in."""
    import asyncio
    from backend import config, agent_registry, agent_context, db
    import backend.wiki_graph_api as wg

    monkeypatch.setattr(config, "_BASE", tmp_path, raising=False)
    monkeypatch.setattr(agent_registry, "_BASE", tmp_path, raising=False)
    with db.connection() as c:
        c.execute("DELETE FROM agents WHERE id NOT IN ('conwo', 'infosec')")
    agent_registry.invalidate_cache()

    app.dependency_overrides[_get_user] = _admin
    try:
        client = TestClient(app)
        r = client.post("/admin/agents", json={"name": "Legal"})
        assert r.status_code == 200, r.text

        # /agents exposes accent + theme_base so the frontend can theme.
        legal = {a["id"]: a for a in client.get("/agents").json()}["legal"]
        assert legal["accent"].startswith("#") and legal["theme_base"] == "dark"

        # The provisioned spec is generic + wiki-only (no Jira/PMS) — Conwo's brain
        # methodology, no WorkInSync domain skin.
        spec = agent_registry.get("legal")
        assert spec.schema_kind == "generic" and spec.has_jira is False and spec.has_pms is False
        assert (spec.wiki_dir / "index.md").is_file()

        # It can actually ingest: the plan registry must include the extract tools
        # (extraction is tool-driven) plus wiki tools, but never jira/pms.
        from backend.ingest_service import build_plan_registry
        plan_tools = {s["name"] for s in build_plan_registry(agent=spec).schemas}
        assert {"extract_pdf", "extract_docx", "wiki_search"} <= plan_tools
        assert "jira_search_ranked" not in plan_tools
        assert not any(n.startswith("pms_") for n in plan_tools)

        # Its wiki graph is isolated + near-empty (only the seeded index page),
        # and contains none of Conwo's module pages.
        token = agent_context.set_current_agent("legal")
        try:
            graph = asyncio.new_event_loop().run_until_complete(wg.wiki_graph(include_configs=False))
        finally:
            agent_context.reset_current_agent(token)
        assert isinstance(graph.get("nodes"), list) and len(graph["nodes"]) <= 3
        labels = " ".join(n.get("label", "") for n in graph["nodes"]).lower()
        assert "visitor" not in labels and "desk" not in labels  # no Conwo leakage

        # Conwo's own spec is untouched by the new agent.
        conwo = agent_registry.get("conwo")
        assert conwo.schema_kind == "workinsync" and conwo.has_jira is True
    finally:
        app.dependency_overrides.clear()
        with db.connection() as conn:
            conn.execute("DELETE FROM agents WHERE id NOT IN ('conwo', 'infosec')")
        agent_registry.invalidate_cache()
