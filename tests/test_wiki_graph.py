"""wiki_graph — typed edge extraction + neighbors API."""
from backend import wiki_graph
from backend.wiki_retriever import WikiPage


def _page(path, text, fm=None):
    return WikiPage(path=path, title=path, full_text=text,
                    tokens=[], frontmatter=fm or {})


PAGES = {
    "modules/desk-management.md": _page(
        "modules/desk-management.md",
        "# Desk\n\nSee [[modules/parking-management]] and [[concepts/booking]].",
        fm={"depends_on": ["sso"], "used_by": ["employee-experience"]}),
    "modules/sso.md": _page("modules/sso.md", "# SSO"),
    "modules/employee-experience.md": _page("modules/employee-experience.md", "# EE"),
    "modules/parking-management.md": _page("modules/parking-management.md", "# P"),
    "concepts/booking.md": _page("concepts/booking.md", "# B"),
    "configs/desk-management.md": _page(
        "configs/desk-management.md", "# Cfg", fm={"module": "desk-management"}),
    "runbooks/desk-setup.md": _page(
        "runbooks/desk-setup.md", "# RB", fm={"module": "desk-management"}),
    "decisions/2026-01-01-desk-policy.md": _page(
        "decisions/2026-01-01-desk-policy.md", "# D",
        fm={"modules": ["desk-management"]}),
}


def _graph():
    return wiki_graph.build_graph(PAGES)


def test_frontmatter_dependency_edges():
    g = _graph()
    types = {(d, t) for d, t in g.neighbors("modules/desk-management.md")}
    assert ("modules/sso.md", "depends_on") in types
    assert ("modules/employee-experience.md", "used_by") in types


def test_structural_edges_config_runbook_decision():
    g = _graph()
    n = dict(g.neighbors("modules/desk-management.md"))
    assert n.get("configs/desk-management.md") == "config_of"
    assert n.get("runbooks/desk-setup.md") == "runbook_of"
    assert n.get("decisions/2026-01-01-desk-policy.md") == "decision_for"


def test_wikilink_edges_resolve_paths():
    g = _graph()
    n = dict(g.neighbors("modules/desk-management.md"))
    assert n.get("modules/parking-management.md") == "wikilink"
    assert n.get("concepts/booking.md") == "wikilink"


def test_neighbors_ordered_by_edge_priority_and_limited():
    g = _graph()
    ordered = g.neighbors("modules/desk-management.md", limit=3)
    assert len(ordered) == 3
    prios = [wiki_graph.EDGE_PRIORITY[t] for _, t in ordered]
    assert prios == sorted(prios)  # curated/structural before wikilink


def test_neighbors_bidirectional():
    g = _graph()
    back = dict(g.neighbors("modules/sso.md"))
    assert back.get("modules/desk-management.md") == "depends_on"


def test_type_filter():
    g = _graph()
    only = g.neighbors("modules/desk-management.md", types=("depends_on", "used_by"))
    assert all(t in ("depends_on", "used_by") for _, t in only)
