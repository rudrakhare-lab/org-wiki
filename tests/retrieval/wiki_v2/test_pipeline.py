"""wiki_v2 pipeline — expansion leash, tags, soft boosts, degradation."""
import pytest
from backend.retrieval.wiki_v2 import pipeline as wp


def _chunk_row(path, anchor="overview", ptype="module", score=0.02):
    return {"id": hash((path, anchor)) % 10_000, "page_path": path,
            "section_anchor": anchor, "section_title": anchor.title(),
            "page_type": ptype, "chunk_index": 0,
            "chunk_text": f"text of {path}#{anchor}",
            "last_updated": "2026-06-01", "fused_score": score}


@pytest.fixture
def wired(monkeypatch):
    """Wire pipeline internals to fakes; returns dict of knobs tests mutate."""
    knobs = {
        "hybrid": [_chunk_row("modules/desk-management.md")],
        "neighbors": [("configs/desk-management.md", "config_of"),
                      ("modules/sso.md", "depends_on"),
                      ("concepts/booking.md", "wikilink")],
        "best_chunks": {"configs/desk-management.md":
                        _chunk_row("configs/desk-management.md", "config-comparison", "config"),
                        "modules/sso.md":
                        _chunk_row("modules/sso.md", "overview", "module"),
                        "concepts/booking.md":
                        _chunk_row("concepts/booking.md", "definition", "concept")},
    }
    monkeypatch.setattr(wp, "embed_query", lambda q: [0.0] * 768)
    monkeypatch.setattr(wp, "hybrid_chunks",
                        lambda conn, sq, qv, aid, expansions=None, limit=24: knobs["hybrid"])

    class FakeGraph:
        def neighbors(self, path, types=None, limit=None):
            n = knobs["neighbors"]
            return n[:limit] if limit else n
    monkeypatch.setattr(wp, "_graph_for", lambda aid: FakeGraph())
    monkeypatch.setattr(wp, "_best_chunk_for_page",
                        lambda conn, aid, page, qvec: knobs["best_chunks"].get(page))
    # rerank: score by inverse text length (deterministic, [0,1])
    monkeypatch.setattr(
        wp, "rerank_score",
        lambda q, cands: sorted(((c, 0.9) for c in cands),
                                key=lambda x: x[0]["page_path"]))

    class FakeConn:
        def __enter__(self): return self
        def __exit__(self, *a): pass
    monkeypatch.setattr(wp, "_connection", lambda: FakeConn())
    return knobs


def test_expanded_chunks_are_tagged_never_direct(wired):
    hits = wp.search("desk booking", agent_id="conwo")
    direct = [h for h in hits if h.related_via is None]
    related = [h for h in hits if h.related_via is not None]
    assert direct and related
    assert any("config_of" in h.related_via for h in related)


def test_neighbor_cap_respected(wired):
    wired["neighbors"] = [(f"modules/m{i}.md", "wikilink") for i in range(20)]
    wired["best_chunks"] = {f"modules/m{i}.md": _chunk_row(f"modules/m{i}.md")
                            for i in range(20)}
    hits = wp.search("q", agent_id="conwo", top_k=50)
    related = [h for h in hits if h.related_via]
    assert len({h.page_path for h in related}) <= wp.NEIGHBOR_CAP


def test_intent_boost_is_soft_never_zero(wired):
    for intent, mults in wp.TYPE_BOOSTS.items():
        for v in mults.values():
            assert 0.6 <= v <= 1.4, f"{intent} multiplier {v} breaks soft-routing"


def test_configuration_intent_ranks_config_chunk_higher(wired, monkeypatch):
    monkeypatch.setattr(
        wp, "rerank_score",
        lambda q, cands: [(c, 0.8) for c in cands])  # equal base scores
    hits = wp.search("q", agent_id="conwo", intent="CONFIGURATION")
    types = [h.page_type for h in hits]
    assert types.index("config") < types.index("concept")


def test_history_downranked_for_current_state_intent(wired, monkeypatch):
    wired["hybrid"] = [_chunk_row("history/release-notes-2026.md", "rn-1", "history"),
                       _chunk_row("modules/desk-management.md")]
    monkeypatch.setattr(wp, "rerank_score", lambda q, c: [(x, 0.8) for x in c])
    hits = wp.search("q", agent_id="conwo", intent="CONFIGURATION")
    paths = [h.page_path for h in hits]
    assert paths.index("modules/desk-management.md") < paths.index(
        "history/release-notes-2026.md")


def test_temporal_question_boosts_history_even_with_other_intent(wired, monkeypatch):
    wired["hybrid"] = [_chunk_row("history/release-notes-2026.md", "rn-1", "history"),
                       _chunk_row("modules/desk-management.md")]
    monkeypatch.setattr(wp, "rerank_score", lambda q, c: [(x, 0.8) for x in c])
    hits = wp.search("when did desk booking change?", agent_id="conwo",
                     intent="CONFIGURATION")
    paths = [h.page_path for h in hits]
    assert paths.index("history/release-notes-2026.md") < paths.index(
        "modules/desk-management.md")


def test_empty_chunk_table_raises_unavailable(wired):
    wired["hybrid"] = []
    with pytest.raises(wp.WikiV2Unavailable):
        wp.search("q", agent_id="conwo")


def test_embed_failure_raises_unavailable(wired, monkeypatch):
    def boom(q):
        raise RuntimeError("gemini down")
    monkeypatch.setattr(wp, "embed_query", boom)
    with pytest.raises(wp.WikiV2Unavailable):
        wp.search("q", agent_id="conwo")


def test_direct_page_never_duplicated_as_expanded(wired):
    # Page B sits at direct rank 11 — outside the top-10 expansion frontier
    # but inside the merged direct results. It is also a neighbor of the
    # top-ranked page. It must appear exactly once, as a DIRECT hit.
    direct = [_chunk_row(f"modules/d{i}.md") for i in range(10)]
    b = _chunk_row("modules/b.md")
    wired["hybrid"] = direct + [b]  # b at rank 11
    wired["neighbors"] = [("modules/b.md", "wikilink")]
    wired["best_chunks"] = {"modules/b.md": _chunk_row("modules/b.md")}
    hits = wp.search("q", agent_id="conwo", top_k=50)
    b_hits = [h for h in hits if h.page_path == "modules/b.md"]
    assert len(b_hits) == 1
    assert b_hits[0].related_via is None


def test_expansion_failure_degrades_to_direct_only(wired, monkeypatch):
    def boom(aid):
        raise RuntimeError("graph build failed")
    monkeypatch.setattr(wp, "_graph_for", boom)
    hits = wp.search("q", agent_id="conwo")
    assert hits  # direct hits still served, no exception raised
    assert all(h.related_via is None for h in hits)


def test_anchor_property():
    h = wp.ChunkHit(page_path="modules/a.md", section_anchor="overview",
                    section_title="Overview", page_type="module",
                    chunk_text="t", last_updated=None, score=0.5,
                    related_via=None)
    assert h.anchor == "modules/a.md#overview"
