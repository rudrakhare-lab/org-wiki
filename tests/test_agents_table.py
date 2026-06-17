def test_agents_table_seeded(clean_db):
    from backend import db
    with db.connection() as c:
        rows = {r["id"]: r for r in c.execute(
            "SELECT id, display_name, has_jira, schema_kind, theme_base FROM agents").fetchall()}
    assert {"conwo", "infosec"} <= set(rows)
    assert rows["conwo"]["has_jira"] is True
    assert rows["conwo"]["schema_kind"] == "workinsync"
    assert rows["infosec"]["has_jira"] is False
    assert rows["infosec"]["schema_kind"] == "generic"
    assert rows["infosec"]["theme_base"] == "dark"


def test_registry_loads_from_db(clean_db):
    from backend import agent_registry
    agent_registry.invalidate_cache()
    ids = {a.id for a in agent_registry.all()}
    assert {"conwo", "infosec"} <= ids
    conwo = agent_registry.get("conwo")
    assert conwo.accent == "#1e293b" and conwo.theme_base == "light"
    assert conwo.schema_kind == "workinsync" and conwo.has_jira is True
    assert conwo.tool_allowed("jira_search_ranked") is True   # tools = {*}
    info = agent_registry.get("infosec")
    assert info.accent == "#a78bfa" and info.theme_base == "dark"
    assert info.schema_kind == "generic" and info.has_jira is False
    assert info.tool_allowed("jira_search_ranked") is False
    assert agent_registry.get("nope").id == "conwo"   # fallback preserved


def test_ingest_schema_is_generic_for_non_conwo():
    import backend.ingest_api as ing
    from backend import agent_registry
    conwo_prompt = ing._render_plan_prompt(agent_registry.get("conwo"))
    info_prompt = ing._render_plan_prompt(agent_registry.get("infosec"))
    # Conwo keeps the WorkInSync schema; generic agents must NOT mention modules/configs.
    assert "wiki/modules/" in conwo_prompt and "wiki/configs/" in conwo_prompt
    assert "wiki/modules/" not in info_prompt and "wiki/configs/" not in info_prompt
    assert "wiki/concepts/" in info_prompt and "wiki/sources/" in info_prompt
