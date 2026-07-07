"""Chunk + embed wiki pages into wiki_chunks (spec §5.2).

Modes:
  --mode full   re-chunk + re-embed every page (hash updated).
  --mode delta  only pages whose content hash differs from DB / missing.

Page-level atomic: each page's chunks are DELETEd + INSERTed in one
transaction, so an interruption never leaves a page half-indexed —
re-running picks up cleanly (resumable by construction).
"""
from __future__ import annotations
import argparse
import hashlib
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend import db  # noqa: E402
from backend.retrieval.v2.embed import embed_documents  # noqa: E402
from backend.retrieval.wiki_v2.chunker import split_page, page_type_from_path, Chunk  # noqa: E402

BATCH = 32

INSERT_SQL = """
    INSERT INTO wiki_chunks (agent_id, page_path, section_anchor, section_title,
        page_type, chunk_index, chunk_text, last_updated, content_hash, embedding)
    VALUES (%(agent_id)s, %(page_path)s, %(section_anchor)s, %(section_title)s,
        %(page_type)s, %(chunk_index)s, %(chunk_text)s, %(last_updated)s,
        %(content_hash)s, %(embedding)s::vector)
"""


def page_hash(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def discover_pages(wiki_dir: Path) -> dict[str, str]:
    """{rel_path: text} for every indexable page (reuses retriever filters)."""
    from backend.config import WIKI_INDEX_EXCLUDE
    from backend.wiki_retriever import _is_obsidian_artifact_at_root
    out: dict[str, str] = {}
    for f in sorted(wiki_dir.rglob("*.md")):
        rel = f.relative_to(wiki_dir)
        if rel.name in WIKI_INDEX_EXCLUDE or _is_obsidian_artifact_at_root(rel):
            continue
        out[str(rel)] = f.read_text(encoding="utf-8", errors="replace")
    return out


def db_hashes(conn, agent_id: str) -> dict[str, str]:
    cur = conn.execute(
        "SELECT DISTINCT page_path, content_hash FROM wiki_chunks WHERE agent_id = %s",
        (agent_id,))
    return {r[0]: r[1] for r in cur.fetchall()}


def pages_needing_embed(disk: dict[str, str], hashes: dict[str, str],
                        mode: str) -> list[str]:
    if mode == "full":
        return list(disk)
    return [p for p, text in disk.items() if hashes.get(p) != page_hash(text)]


def nonempty_chunks(chunks: list[Chunk]) -> list[Chunk]:
    """Drop chunks whose text is empty or whitespace-only — never embed them."""
    return [c for c in chunks if c.chunk_text.strip()]


def embed_chunks(chunks: list[Chunk]) -> list[list[float]]:
    texts = [c.embed_text for c in chunks]
    vecs: list[list[float]] = []
    for i in range(0, len(texts), BATCH):
        vecs.extend(embed_documents(texts[i:i + BATCH]))
    return vecs


def replace_page_chunks(conn, agent_id: str, page_path: str, content_hash: str,
                        chunks: list[Chunk], vecs: list[list[float]]) -> None:
    with conn.cursor() as cur:
        cur.execute("DELETE FROM wiki_chunks WHERE agent_id = %s AND page_path = %s",
                    (agent_id, page_path))
        for c, v in zip(chunks, vecs):
            cur.execute(INSERT_SQL, {
                "agent_id": agent_id, "page_path": c.page_path,
                "section_anchor": c.section_anchor, "section_title": c.section_title,
                "page_type": c.page_type, "chunk_index": c.chunk_index,
                "chunk_text": c.chunk_text, "last_updated": c.last_updated,
                "content_hash": content_hash,
                "embedding": "[" + ",".join(f"{x:.7f}" for x in v) + "]",
            })
    conn.commit()


def _frontmatter_last_updated(text: str) -> str | None:
    from backend.wiki_retriever import _parse_frontmatter
    v = _parse_frontmatter(text).get("last_updated")
    return str(v) if v else None


def run(mode: str, agent_id: str, wiki_dir: Path) -> int:
    disk = discover_pages(wiki_dir)
    with db.connection() as conn:
        todo = pages_needing_embed(disk, db_hashes(conn, agent_id), mode)
        print(f"embed_wiki: {len(todo)}/{len(disk)} pages to (re)embed "
              f"(mode={mode}, agent={agent_id})", flush=True)
        done = 0
        for path in todo:
            text = disk[path]
            chunks = split_page(path, text,
                                page_type=page_type_from_path(path),
                                last_updated=_frontmatter_last_updated(text))
            chunks = nonempty_chunks(chunks)
            if not chunks:
                continue
            t0 = time.perf_counter()
            vecs = embed_chunks(chunks)
            replace_page_chunks(conn, agent_id, path, page_hash(text), chunks, vecs)
            done += 1
            print(f"  [{done}/{len(todo)}] {path}: {len(chunks)} chunks "
                  f"({time.perf_counter() - t0:.1f}s)", flush=True)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=("full", "delta"), default="delta")
    ap.add_argument("--agent", default="conwo")
    ap.add_argument("--wiki-dir", default=str(ROOT / "wiki"))
    args = ap.parse_args()
    return run(args.mode, args.agent, Path(args.wiki_dir))


if __name__ == "__main__":
    raise SystemExit(main())
