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
