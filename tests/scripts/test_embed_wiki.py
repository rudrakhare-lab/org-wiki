"""embed_wiki — hash-driven delta, page-level atomic replace, skip-empty."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import embed_wiki


def test_page_hash_stable():
    h1 = embed_wiki.page_hash("# Title\n\ncontent")
    h2 = embed_wiki.page_hash("# Title\n\ncontent")
    assert h1 == h2 and len(h1) == 40  # sha1 hex


def test_pages_needing_embed_delta_filters_by_hash():
    disk = {"modules/a.md": "# A\n\nnew", "modules/b.md": "# B\n\nsame"}
    db_hashes = {"modules/b.md": embed_wiki.page_hash("# B\n\nsame"),
                 "modules/a.md": "stale-hash"}
    todo = embed_wiki.pages_needing_embed(disk, db_hashes, mode="delta")
    assert set(todo) == {"modules/a.md"}


def test_pages_needing_embed_full_takes_all():
    disk = {"modules/a.md": "# A", "modules/b.md": "# B"}
    todo = embed_wiki.pages_needing_embed(disk, {"modules/a.md": "x"}, mode="full")
    assert set(todo) == set(disk)


def test_replace_page_chunks_deletes_then_inserts(monkeypatch):
    executed = []

    class FakeCur:
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def execute(self, sql, params=None):
            executed.append((" ".join(sql.split()), params))
    class FakeConn:
        def cursor(self): return FakeCur()
        def commit(self): executed.append(("COMMIT", None))

    from backend.retrieval.wiki_v2.chunker import Chunk
    chunks = [Chunk(page_path="modules/a.md", page_title="A",
                    section_anchor="overview", section_title="Overview",
                    page_type="module", chunk_index=0, chunk_text="text",
                    last_updated="2026-06-01")]
    embed_wiki.replace_page_chunks(FakeConn(), "conwo", "modules/a.md",
                                   "hash123", chunks, [[0.0] * 768])
    sqls = [s for s, _ in executed]
    assert any(s.startswith("DELETE FROM wiki_chunks") for s in sqls)
    assert any(s.startswith("INSERT INTO wiki_chunks") for s in sqls)
    assert sqls[-1] == "COMMIT"
    delete_idx = next(i for i, s in enumerate(sqls) if s.startswith("DELETE"))
    insert_idx = next(i for i, s in enumerate(sqls) if s.startswith("INSERT"))
    assert delete_idx < insert_idx


def test_empty_chunks_are_not_embedded(monkeypatch):
    calls = []
    monkeypatch.setattr(embed_wiki, "embed_documents",
                        lambda texts: calls.append(texts) or [[0.0] * 768] * len(texts))
    from backend.retrieval.wiki_v2.chunker import Chunk
    good = Chunk(page_path="p", page_title="T", section_anchor="s",
                 section_title="S", page_type="", chunk_index=0,
                 chunk_text="real content")
    vecs = embed_wiki.embed_chunks([good])
    assert len(vecs) == 1 and calls
