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
