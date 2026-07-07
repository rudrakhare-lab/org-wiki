"""Preflight wiki v2 wiring — flag dispatch, fallback + visible degradation."""
from backend.retrieval.wiki_v2.pipeline import ChunkHit, WikiV2Unavailable


def _hit(path="modules/a.md", anchor="overview", via=None):
    return ChunkHit(page_path=path, section_anchor=anchor,
                    section_title=anchor.title(), page_type="module",
                    chunk_text="Section content here.", last_updated="2026-06-01",
                    score=0.9, related_via=via)


def test_flag_off_uses_keyword_path(monkeypatch):
    monkeypatch.setenv("CONWO_WIKI_RETRIEVAL_V2", "off")
    from backend.retrieval.wiki_v2 import pipeline
    assert pipeline.wiki_v2_enabled() is False


def test_flag_default_on(monkeypatch):
    monkeypatch.delenv("CONWO_WIKI_RETRIEVAL_V2", raising=False)
    from backend.retrieval.wiki_v2 import pipeline
    assert pipeline.wiki_v2_enabled() is True


def test_format_wiki_chunks_for_seed_carries_anchors_and_tags():
    from backend import preflight
    text = preflight.format_wiki_chunks_for_seed(
        [_hit(), _hit("configs/a.md", "config-comparison",
                      via="modules/a.md —config_of→ configs/a.md")])
    assert "`modules/a.md#overview`" in text
    assert "`configs/a.md#config-comparison`" in text
    assert "related via" in text


def test_unavailable_falls_back_and_notes_degradation(monkeypatch):
    from backend import preflight

    def boom(question, **kw):
        raise WikiV2Unavailable("backfill pending")
    monkeypatch.setattr(preflight, "_wiki_v2_search", boom)

    class FakePage:
        path, title, full_text = "modules/a.md", "A", "text"
        def excerpt(self, n): return "kw excerpt"
    monkeypatch.setattr(preflight.wiki_retriever, "search",
                        lambda q, top_n=3: [FakePage()])

    pages, chunks, note = preflight._fetch_seed_wiki("q", 3, intent="GENERAL",
                                                     rewrite=None)
    assert chunks == [] and pages and note and "keyword" in note.lower()


def test_build_seed_message_renders_chunks_when_v2_served():
    """When seed_wiki_chunks is populated (the live v2-success path), both
    seed builders must render via format_wiki_chunks_for_seed, not the
    keyword formatter — this is the path production runs by default."""
    from backend.preflight import PreflightBundle, build_seed_message

    bundle = PreflightBundle(seed_wiki_chunks=[
        _hit(),
        _hit("configs/a.md", "config-comparison",
             via="modules/a.md —config_of→ configs/a.md"),
    ])
    out = build_seed_message("q", "scope", bundle, summary="")
    assert "`modules/a.md#overview`" in out
    assert "`configs/a.md#config-comparison`" in out
    assert "related via" in out
    assert "2 sections" in out


def test_build_agent_preamble_renders_chunks_when_v2_served():
    from backend.preflight import PreflightBundle, build_agent_preamble

    bundle = PreflightBundle(seed_wiki_chunks=[
        _hit(),
        _hit("configs/a.md", "config-comparison",
             via="modules/a.md —config_of→ configs/a.md"),
    ])
    out = build_agent_preamble(bundle)
    assert "`modules/a.md#overview`" in out
    assert "`configs/a.md#config-comparison`" in out
    assert "related via" in out
    assert "2 sections" in out


def test_build_seed_message_shows_degradation_note_when_present():
    from backend.preflight import PreflightBundle, build_seed_message

    bundle = PreflightBundle(degradations=[
        "wiki semantic search unavailable (backfill pending) — "
        "fell back to keyword search; results may be less complete."])
    out = build_seed_message("q", "scope", bundle, summary="")
    assert "## Degradation notes" in out
    assert "⚠️" in out
    assert "backfill pending" in out


# ── Reviewer gap-closure: production-default (v2-success) path coverage ─────

def test_fetch_seed_wiki_v2_success_returns_chunks_no_note(monkeypatch):
    """GAP 2a — the success dispatch: flag on + pipeline serves → chunks
    populated, pages empty, no degradation note; keyword path never runs."""
    from backend import preflight

    monkeypatch.delenv("CONWO_WIKI_RETRIEVAL_V2", raising=False)
    served = [_hit(), _hit("configs/a.md", "config-comparison")]
    monkeypatch.setattr(preflight, "_wiki_v2_search",
                        lambda question, **kw: served)

    def _keyword_must_not_run(*a, **kw):
        raise AssertionError("keyword path must not run when v2 serves")
    monkeypatch.setattr(preflight.wiki_retriever, "search",
                        _keyword_must_not_run)

    pages, chunks, note = preflight._fetch_seed_wiki(
        "q", 3, intent="GENERAL", rewrite=None)
    assert pages == [] and chunks == served and note is None


def test_run_preflight_derives_module_slugs_from_chunk_hits(monkeypatch):
    """GAP 1 — v2-success path through run_preflight: module-tagged Jira
    fetch must key off CHUNK page paths (seed_wiki is empty on this path)."""
    import backend.preflight as pf
    from backend import agent_registry, jira_retriever, wiki_graph

    monkeypatch.delenv("CONWO_WIKI_RETRIEVAL_V2", raising=False)
    monkeypatch.setattr(pf, "_wiki_v2_search", lambda question, **kw: [
        _hit("modules/desk-management.md", "overview"),
        _hit("configs/desk.md", "config-comparison"),  # non-module: skipped
    ])
    monkeypatch.setattr(jira_retriever, "search",
                        lambda *a, **kw: {"buckets": {}})

    by_module_calls: list[str] = []

    def _fake_by_module(slug, query=None, limit=5):
        by_module_calls.append(slug)
        return [{"key": f"TS-{slug}", "summary": "fake"}]
    monkeypatch.setattr(jira_retriever, "by_module", _fake_by_module)

    class _FakeGraph:
        def neighbors(self, path, types=None, limit=None):
            return []
    monkeypatch.setattr(wiki_graph, "get_graph", lambda *a, **kw: _FakeGraph())

    class _StubRegistry:
        def execute(self, **kw):  # pragma: no cover — latest_keys is empty
            raise AssertionError("registry.execute should not be called")

    bundle = pf.run_preflight("desk booking question",
                              registry=_StubRegistry(),
                              agent=agent_registry.get("conwo"))

    assert bundle.seed_wiki == []            # v2 served — keyword list empty
    assert bundle.seed_wiki_chunks           # chunks populated
    assert by_module_calls == ["desk-management"]
    assert [t["key"] for t in bundle.module_tagged_jira] == ["TS-desk-management"]
    assert bundle.module_tagged_jira[0]["_preflight_module"] == "desk-management"
    assert bundle.module_tagged_jira[0]["_preflight_source"] == "direct"


def test_wiki_search_handler_v2_and_fallback(monkeypatch):
    """GAP 2b — tool handler: v2 branch shape + engine tag, and
    WikiV2Unavailable falls through to keyword rendering."""
    from backend.retrieval.wiki_v2 import pipeline
    from backend.tools import wiki_tools

    monkeypatch.delenv("CONWO_WIKI_RETRIEVAL_V2", raising=False)

    # v2 success branch
    monkeypatch.setattr(pipeline, "search", lambda q, **kw: [
        _hit(via="modules/a.md —config_of→ configs/a.md")])
    out = wiki_tools._wiki_search_handler({"query": "desk"})
    assert out["engine"] == "v2"
    (r,) = out["results"]
    assert r["path"] == "modules/a.md"
    assert r["anchor"] == "modules/a.md#overview"
    assert r["section"] == "Overview"
    assert r["type"] == "module"
    assert r["excerpt"] == "Section content here."
    assert r["related_via"] == "modules/a.md —config_of→ configs/a.md"
    assert r["score"] == 0.9

    # WikiV2Unavailable → keyword fallback branch
    def _boom(q, **kw):
        raise WikiV2Unavailable("backfill pending")
    monkeypatch.setattr(pipeline, "search", _boom)

    class FakePage:
        path, title = "modules/a.md", "A"
        def excerpt(self, n): return "kw excerpt"
    monkeypatch.setattr(wiki_tools.wiki_retriever, "search",
                        lambda q, top_n=5: [FakePage()])
    out = wiki_tools._wiki_search_handler({"query": "desk"})
    assert out["engine"] == "keyword-fallback"
    assert out["results"] == [{"path": "modules/a.md", "title": "A",
                               "excerpt": "kw excerpt"}]
    assert out["total"] == 1
