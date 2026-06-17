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
