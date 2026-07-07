"""Chunker tests — section splits, anchors, row-group tables, prose caps."""
from backend.retrieval.wiki_v2 import chunker

MODULE_PAGE = """---
type: module
status: active
last_updated: 2026-06-01
---

# Desk Management

Handles desk booking end to end.

## Overview

Desk booking for employees across offices.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
""" + "\n".join(
    f"| GET | /desks/{i} | endpoint {i} |" for i in range(40)
) + """

## Open Questions

- Who owns rate limits?
"""


def test_split_page_creates_preamble_and_section_chunks():
    chunks = chunker.split_page("modules/desk-management.md", MODULE_PAGE,
                                page_type="module", last_updated="2026-06-01")
    anchors = [c.section_anchor for c in chunks]
    assert "" in anchors                      # preamble (title + intro)
    assert "overview" in anchors
    assert "open-questions" in anchors
    pre = next(c for c in chunks if c.section_anchor == "")
    assert "Desk booking" not in pre.chunk_text  # preamble stops at first ##
    assert "type: module" not in pre.chunk_text  # frontmatter stripped


def test_big_table_splits_into_row_groups_with_repeated_header():
    chunks = chunker.split_page("modules/desk-management.md", MODULE_PAGE,
                                page_type="module")
    api = [c for c in chunks if c.section_anchor == "api-endpoints"]
    assert len(api) >= 3          # 40 rows / 15 per chunk
    for c in api:
        assert "| Method | Path | Description |" in c.chunk_text  # header repeated
    assert [c.chunk_index for c in api] == list(range(len(api)))


def test_long_prose_splits_at_paragraph_boundaries():
    long_section = "## Notes\n\n" + "\n\n".join(f"Paragraph {i}. " + "x" * 300
                                                for i in range(8))
    text = "# T\n\nintro\n\n" + long_section
    chunks = chunker.split_page("concepts/t.md", text)
    notes = [c for c in chunks if c.section_anchor == "notes"]
    assert len(notes) >= 2
    assert all(len(c.chunk_text) <= chunker.MAX_PROSE_CHARS + 400 for c in notes)


def test_embed_text_carries_page_and_section_titles():
    chunks = chunker.split_page("modules/desk-management.md", MODULE_PAGE)
    ov = next(c for c in chunks if c.section_anchor == "overview")
    assert ov.embed_text.startswith("Desk Management — Overview\n")


def test_slugify_matches_github_style():
    assert chunker.slugify("API Endpoints") == "api-endpoints"
    assert chunker.slugify("Config Comparison (.in vs .com)") == "config-comparison-in-vs-com"


def test_page_type_from_path():
    assert chunker.page_type_from_path("modules/x.md") == "module"
    assert chunker.page_type_from_path("configs/x.md") == "config"
    assert chunker.page_type_from_path("history/release-notes-2026.md") == "history"
    assert chunker.page_type_from_path("overview.md") == ""


def test_empty_sections_are_skipped():
    text = "# T\n\n## Empty\n\n## Real\n\ncontent here"
    chunks = chunker.split_page("concepts/t.md", text)
    anchors = [c.section_anchor for c in chunks]
    assert "real" in anchors and "empty" not in anchors
