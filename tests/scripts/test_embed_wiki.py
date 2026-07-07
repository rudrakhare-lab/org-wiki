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


def _chunk(text, path="p", idx=0):
    from backend.retrieval.wiki_v2.chunker import Chunk
    return Chunk(page_path=path, page_title="T", section_anchor="s",
                 section_title="S", page_type="", chunk_index=idx,
                 chunk_text=text)


def test_nonempty_chunks_drops_empty_and_whitespace_only():
    real = _chunk("real content", idx=0)
    empty = _chunk("", idx=1)
    whitespace = _chunk("   \n\t  ", idx=2)
    kept = embed_wiki.nonempty_chunks([real, empty, whitespace])
    assert kept == [real]


def test_nonempty_chunks_keeps_all_when_all_real():
    chunks = [_chunk("a", idx=0), _chunk("b", idx=1)]
    assert embed_wiki.nonempty_chunks(chunks) == chunks


def test_run_skips_page_whose_chunks_are_all_whitespace(monkeypatch):
    """A page chunking entirely to whitespace must never reach embed_documents
    nor execute DELETE/INSERT — run() skips it via nonempty_chunks()."""
    executed = []
    embed_calls = []

    class FakeCur:
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def execute(self, sql, params=None):
            executed.append((" ".join(sql.split()), params))

    class FakeConn:
        def cursor(self): return FakeCur()
        def commit(self): executed.append(("COMMIT", None))

    from contextlib import contextmanager

    @contextmanager
    def fake_connection():
        yield FakeConn()

    def fake_split_page(path, text, page_type="", last_updated=None):
        if path == "modules/blank.md":
            return [_chunk("   \n\t  ", path=path)]
        return [_chunk("real content", path=path)]

    monkeypatch.setattr(embed_wiki, "discover_pages",
                        lambda wiki_dir: {"modules/blank.md": "# Blank",
                                          "modules/real.md": "# Real\n\nbody"})
    monkeypatch.setattr(embed_wiki, "db_hashes", lambda conn, agent_id: {})
    monkeypatch.setattr(embed_wiki, "split_page", fake_split_page)
    monkeypatch.setattr(embed_wiki, "embed_documents",
                        lambda texts: embed_calls.append(list(texts))
                        or [[0.0] * 768] * len(texts))
    monkeypatch.setattr(embed_wiki.db, "connection", fake_connection)

    rc = embed_wiki.run("full", "conwo", Path("unused"))
    assert rc == 0

    # embed_documents called exactly once — only for the real page's chunk.
    assert len(embed_calls) == 1
    assert all("real content" in t for t in embed_calls[0])

    # No DELETE/INSERT ever mentions the blank page; the real page has both.
    def _paths(params):
        if params is None:
            return []
        if isinstance(params, dict):
            return [params.get("page_path")]
        return list(params)

    touched = [p for _, params in executed for p in _paths(params)]
    assert "modules/blank.md" not in touched
    assert "modules/real.md" in touched
    sqls = [s for s, _ in executed]
    assert any(s.startswith("DELETE FROM wiki_chunks") for s in sqls)
    assert any(s.startswith("INSERT INTO wiki_chunks") for s in sqls)
