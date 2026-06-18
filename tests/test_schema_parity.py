from backend import wiki_schema as ws


def test_workinsync_categories_match_legacy():
    assert ws.for_kind("workinsync").categories == (
        "modules", "entities", "sources", "concepts", "decisions",
        "cross-module", "configs", "integrations", "persons", "patterns",
    )


def test_generic_categories():
    g = ws.for_kind("generic").categories
    assert "concepts" in g and "relationships" in g and "topics" in g and "sources" in g


def test_all_categories_is_union():
    assert "topics" in ws.ALL_CATEGORIES and "relationships" in ws.ALL_CATEGORIES
    assert "modules" in ws.ALL_CATEGORIES and "configs" in ws.ALL_CATEGORIES


def test_unknown_kind_defaults_to_workinsync():
    assert ws.for_kind("banana").kind == "workinsync"


def test_page_type_prefers_type_then_category():
    assert ws.page_type("---\ntype: module\n---\n# x") == "module"
    assert ws.page_type("---\ncategory: concepts\n---\n# x") == "concepts"
    assert ws.page_type("# no frontmatter") == "unknown"


def test_scalar_fields_include_category():
    assert "category" in ws.SCALAR_FRONTMATTER_FIELDS
    assert {"type", "status", "owner"} <= ws.SCALAR_FRONTMATTER_FIELDS


def test_generic_propose_allowlist_has_relationships_topics_entities():
    al = ws.for_kind("generic").propose_allowlist
    assert "relationships/" in al and "topics/" in al and "entities/" in al


def test_workinsync_propose_allowlist_excludes_generic_only_types():
    al = ws.for_kind("workinsync").propose_allowlist
    assert "topics/" not in al and "relationships/" not in al


def test_graph_page_type_reads_category():
    import backend.wiki_graph_api as wg
    assert wg._page_type("---\ncategory: relationships\nslug: a-b\n---\n# x") == "relationships"
    assert wg._page_type("---\ntype: module\n---\n# x") == "module"


def test_check_duplicate_is_agent_scoped_and_knows_generic_categories(tmp_path, monkeypatch):
    import types
    from backend import agent_context
    import backend.tools.wiki_read_tools as rt

    wiki = tmp_path / "wiki"
    (wiki / "relationships").mkdir(parents=True)
    (wiki / "relationships" / "a-b.md").write_text("---\ncategory: relationships\n---\n# x")

    fake = types.SimpleNamespace(id="legal", schema_kind="generic", wiki_dir=wiki)
    monkeypatch.setattr(agent_context, "get_current_agent", lambda: fake, raising=False)

    hit = rt._wiki_check_duplicate_handler({"slug": "a-b", "category": "relationships"})
    assert hit.get("exists") is True
    miss = rt._wiki_check_duplicate_handler({"slug": "nope", "category": "topics"})
    assert miss.get("exists") is False and "code" not in miss


def test_propose_new_allows_generic_paths(monkeypatch):
    import types
    from backend import agent_context
    import backend.tools.wiki_propose_tools as pt
    fake = types.SimpleNamespace(id="legal", schema_kind="generic", wiki_dir=None)
    monkeypatch.setattr(agent_context, "get_current_agent", lambda: fake, raising=False)
    al = pt._allowed_new_prefixes()
    assert "relationships/" in al and "topics/" in al


def test_write_tools_scalar_fields_include_category():
    import backend.tools.wiki_write_tools as wt
    assert "category" in wt._SCALAR_FIELDS
    assert {"type", "status", "owner"} <= wt._SCALAR_FIELDS
